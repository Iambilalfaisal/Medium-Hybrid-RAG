from app.schemas.retrieval import DenseResults, FusedHit, FusedResults, SparseResults

RRF_K = 60


def reciprocal_rank_fusion(dense: DenseResults, sparse: SparseResults) -> FusedResults:
    scores: dict[int, float] = {}

    for rank, hit in enumerate(sorted(dense.hits, key=lambda h: h.score, reverse=True)):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    for rank, hit in enumerate(sorted(sparse.hits, key=lambda h: h.score, reverse=True)):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    fused = sorted(
        (FusedHit(chunk_id=cid, rrf_score=score) for cid, score in scores.items()),
        key=lambda h: h.rrf_score,
        reverse=True,
    )
    return FusedResults(hits=fused)
