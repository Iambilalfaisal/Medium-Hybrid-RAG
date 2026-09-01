import asyncio

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, settings
from app.db.models import Article, Chunk
from app.ingestion.embedder import Embedder
from app.retrieval import dense as dense_module
from app.retrieval import fusion as fusion_module
from app.retrieval import parent_resolver as parent_resolver_module
from app.retrieval import reranker as reranker_module
from app.retrieval.bm25_store import BM25Store
from app.retrieval.sparse_bm25 import sparse_search
from app.schemas.filters import FilterParams
from app.schemas.retrieval import (
    Abstain,
    DenseResults,
    FilterClause,
    FusedResults,
    RankedParents,
    ResolvedParents,
    RetrievalResult,
    SparseResults,
)


class RetrievalPipeline:
    """Named, independently callable steps operating on the typed intermediates in
    schemas/retrieval.py — each stage can be smoke-tested with fixed inputs before
    the full chain is wired (see plan build-order step 5.5). run() wires them with
    dense+sparse search running concurrently via asyncio.gather."""

    def __init__(self, session_factory, bm25_store: BM25Store, embedder: Embedder, config: Settings = settings):
        self._session_factory = session_factory
        self._bm25_store = bm25_store
        self._embedder = embedder
        self._config = config

    async def resolve_filters(self, session: AsyncSession, filters: FilterParams | None) -> FilterClause:
        if filters is None or filters.is_empty():
            return FilterClause(eligible_chunk_ids=None)

        conditions = []
        if filters.claps_min is not None:
            conditions.append(Article.claps >= filters.claps_min)
        if filters.claps_max is not None:
            conditions.append(Article.claps <= filters.claps_max)
        if filters.publication:
            conditions.append(Article.publication.in_(filters.publication))
        if filters.date_from is not None:
            conditions.append(Article.published_date >= filters.date_from)
        if filters.date_to is not None:
            conditions.append(Article.published_date <= filters.date_to)
        if filters.reading_time_min is not None:
            conditions.append(Article.reading_time >= filters.reading_time_min)
        if filters.reading_time_max is not None:
            conditions.append(Article.reading_time <= filters.reading_time_max)

        stmt = select(Chunk.id).join(Article, Article.id == Chunk.article_id).where(and_(*conditions))
        ids = (await session.execute(stmt)).scalars().all()
        return FilterClause(eligible_chunk_ids=set(ids))

    async def dense_search(self, session: AsyncSession, query_vec: list[float], clause: FilterClause, top_k: int) -> DenseResults:
        return await dense_module.dense_search(session, query_vec, clause.eligible_chunk_ids, top_k)

    async def sparse_search_step(self, query_text: str, clause: FilterClause, top_k: int) -> SparseResults:
        return await sparse_search(self._bm25_store, query_text, clause.eligible_chunk_ids, top_k)

    def fuse(self, dense: DenseResults, sparse: SparseResults) -> FusedResults:
        return fusion_module.reciprocal_rank_fusion(dense, sparse)

    async def resolve_parents(self, session: AsyncSession, fused: FusedResults) -> ResolvedParents:
        return await parent_resolver_module.resolve_parents(session, fused)

    async def rerank(self, session: AsyncSession, query: str, resolved: ResolvedParents, top_k: int) -> RankedParents:
        return await reranker_module.rerank(session, query, resolved, top_k)

    def apply_abstention(self, ranked: RankedParents) -> RetrievalResult:
        if not ranked.parents:
            return Abstain(reason="no candidates survived retrieval")
        top_score = ranked.parents[0].rerank_score
        if top_score < self._config.RERANK_ABSTAIN_THRESHOLD:
            return Abstain(reason=f"top rerank score {top_score:.3f} below threshold {self._config.RERANK_ABSTAIN_THRESHOLD}")
        return ranked

    async def run(self, query: str, filters: FilterParams | None, top_k: int = 5) -> RetrievalResult:
        async with self._session_factory() as session:
            clause = await self.resolve_filters(session, filters)
            query_vec = await self._embedder.embed_query(query)

            dense, sparse = await asyncio.gather(
                self.dense_search(session, query_vec, clause, top_k * 3),
                self.sparse_search_step(query, clause, top_k * 3),
            )

            fused = self.fuse(dense, sparse)
            resolved = await self.resolve_parents(session, fused)

            try:
                ranked = await self.rerank(session, query, resolved, top_k)
            except reranker_module.RerankerError:
                return Abstain(reason="reranker unavailable")

            return self.apply_abstention(ranked)
