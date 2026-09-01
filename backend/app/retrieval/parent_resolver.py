from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk
from app.schemas.retrieval import FusedResults, ResolvedParent, ResolvedParents


async def resolve_parents(session: AsyncSession, fused: FusedResults) -> ResolvedParents:
    if not fused.hits:
        return ResolvedParents(parents=[])

    chunk_ids = [hit.chunk_id for hit in fused.hits]
    rows = (await session.execute(select(Chunk.id, Chunk.parent_id).where(Chunk.id.in_(chunk_ids)))).all()
    parent_by_chunk = {row.id: row.parent_id for row in rows}

    best_score: dict[int, float] = {}
    children_by_parent: dict[int, list[int]] = defaultdict(list)

    for hit in fused.hits:
        parent_id = parent_by_chunk.get(hit.chunk_id)
        if parent_id is None:
            continue
        children_by_parent[parent_id].append(hit.chunk_id)
        # MAX, not sum: a parent matched by several children must not be artificially
        # boosted ahead of a genuinely more relevant single-match parent.
        best_score[parent_id] = max(best_score.get(parent_id, hit.rrf_score), hit.rrf_score)

    parents = sorted(
        (
            ResolvedParent(parent_chunk_id=pid, max_rrf_score=score, child_chunk_ids=children_by_parent[pid])
            for pid, score in best_score.items()
        ),
        key=lambda p: p.max_rrf_score,
        reverse=True,
    )
    return ResolvedParents(parents=parents)
