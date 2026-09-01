import cohere
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Article, ParentChunk
from app.schemas.retrieval import RankedParent, RankedParents, ResolvedParents

_client = cohere.AsyncClientV2(api_key=settings.COHERE_API_KEY)
_MODEL = "rerank-v3.5"


class RerankerError(Exception):
    """Raised on any Cohere failure (rate limit, network, bad key). Deliberately not
    swallowed here: RetrievalPipeline treats a failed rerank the same as a
    below-threshold one and abstains — no local fallback model (see plan's rejected
    F-08); guessing with unranked results would also silently disable abstention."""


async def rerank(session: AsyncSession, query: str, resolved: ResolvedParents, top_k: int) -> RankedParents:
    if not resolved.parents:
        return RankedParents(parents=[])

    parent_ids = [p.parent_chunk_id for p in resolved.parents]
    rows = (
        await session.execute(
            select(
                ParentChunk.id,
                ParentChunk.text,
                Article.id.label("article_id"),
                Article.title,
                Article.url,
                Article.publication,
                Article.published_date,
                Article.claps,
            )
            .join(Article, Article.id == ParentChunk.article_id)
            .where(ParentChunk.id.in_(parent_ids))
        )
    ).all()
    by_id = {row.id: row for row in rows}

    valid_parent_ids = [pid for pid in parent_ids if pid in by_id]
    documents = [by_id[pid].text for pid in valid_parent_ids]
    if not documents:
        return RankedParents(parents=[])

    try:
        response = await _client.rerank(
            model=_MODEL, query=query, documents=documents, top_n=min(top_k, len(documents))
        )
    except Exception as exc:
        raise RerankerError(str(exc)) from exc

    ranked = []
    for result in response.results:
        pid = valid_parent_ids[result.index]
        row = by_id[pid]
        ranked.append(
            RankedParent(
                parent_chunk_id=pid,
                rerank_score=result.relevance_score,
                text=row.text,
                article_id=row.article_id,
                title=row.title,
                url=row.url,
                publication=row.publication,
                published_date=row.published_date,
                claps=row.claps,
            )
        )
    return RankedParents(parents=ranked)
