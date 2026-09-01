from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk
from app.schemas.retrieval import DenseResults, ScoredChunk


async def dense_search(
    session: AsyncSession, query_embedding: list[float], eligible_chunk_ids: set[int] | None, top_k: int
) -> DenseResults:
    distance = Chunk.embedding.cosine_distance(query_embedding)
    stmt = select(Chunk.id, distance.label("distance"))
    if eligible_chunk_ids is not None:
        stmt = stmt.where(Chunk.id.in_(eligible_chunk_ids))
    stmt = stmt.order_by(distance).limit(top_k)

    rows = (await session.execute(stmt)).all()
    # pgvector's <=> is cosine DISTANCE (0 = identical); flip to a similarity-style
    # score so higher-is-better matches BM25's score convention for RRF fusion.
    hits = [ScoredChunk(chunk_id=row.id, score=1 - row.distance) for row in rows]
    return DenseResults(hits=hits)
