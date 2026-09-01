import asyncio
import os
import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.schemas.retrieval import ScoredChunk

_TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class ChunkMeta:
    chunk_id: int
    article_id: str


class BM25Store:
    """Owns the in-memory BM25Okapi index + its parallel id map, and the on-disk
    pickle mirroring both. An asyncio.Lock guards the in-memory swap and the atomic
    on-disk replace TOGETHER — two rebuilds racing, or a query racing a swap, must
    never observe a half-updated index. Query-path scoring reads the in-memory
    objects WITHOUT the lock: a brief stale read during a swap window is acceptable;
    blocking every query on every rebuild is not.
    """

    def __init__(self, index_path: str):
        self._path = Path(index_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._bm25: BM25Okapi | None = None
        self._id_map: list[ChunkMeta] = []
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self._path.exists():
            return
        with open(self._path, "rb") as f:
            data = pickle.load(f)
        self._bm25 = data["bm25"]
        self._id_map = data["id_map"]

    @property
    def is_ready(self) -> bool:
        return self._bm25 is not None

    async def rebuild(self, rows) -> None:
        """`rows` are SQLAlchemy Row objects with `.id` (chunk id), `.text`,
        `.article_id` — the rest of IngestionPipeline's join columns are ignored here
        since eligibility filtering happens via `eligible_chunk_ids`, not by
        re-deriving metadata conditions inside BM25Store."""
        loop = asyncio.get_running_loop()
        bm25, id_map = await loop.run_in_executor(None, self._build_index, rows)

        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        await loop.run_in_executor(None, self._write_pickle, tmp_path, bm25, id_map)

        async with self._lock:
            os.replace(tmp_path, self._path)
            self._bm25 = bm25
            self._id_map = id_map

    @staticmethod
    def _build_index(rows) -> tuple[BM25Okapi | None, list[ChunkMeta]]:
        corpus = [_tokenize(row.text) for row in rows]
        id_map = [ChunkMeta(chunk_id=row.id, article_id=row.article_id) for row in rows]
        bm25 = BM25Okapi(corpus) if corpus else None
        return bm25, id_map

    @staticmethod
    def _write_pickle(path: Path, bm25, id_map) -> None:
        with open(path, "wb") as f:
            pickle.dump({"bm25": bm25, "id_map": id_map}, f)

    async def score(self, query: str, eligible_chunk_ids: set[int] | None, top_k: int) -> list[ScoredChunk]:
        # Snapshot without the lock on purpose — see class docstring.
        bm25, id_map = self._bm25, self._id_map
        if bm25 is None:
            return []

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._score_sync, bm25, id_map, query, eligible_chunk_ids, top_k)

    @staticmethod
    def _score_sync(bm25: BM25Okapi, id_map: list[ChunkMeta], query: str, eligible_chunk_ids: set[int] | None, top_k: int) -> list[ScoredChunk]:
        # rank_bm25 scores the whole corpus in one vectorized call regardless (its
        # IDF stats are global by construction) — filtering happens by selecting
        # which of those scores we keep, not by avoiding the computation itself.
        scores = bm25.get_scores(_tokenize(query))

        scored = [
            (meta.chunk_id, scores[i])
            for i, meta in enumerate(id_map)
            if eligible_chunk_ids is None or meta.chunk_id in eligible_chunk_ids
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [ScoredChunk(chunk_id=cid, score=score) for cid, score in scored[:top_k]]
