from app.retrieval.bm25_store import BM25Store
from app.schemas.retrieval import SparseResults


async def sparse_search(bm25_store: BM25Store, query: str, eligible_chunk_ids: set[int] | None, top_k: int) -> SparseResults:
    hits = await bm25_store.score(query, eligible_chunk_ids, top_k)
    return SparseResults(hits=hits)
