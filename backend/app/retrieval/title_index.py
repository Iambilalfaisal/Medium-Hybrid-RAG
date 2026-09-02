import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.ingestion.csv_loader import load_rows
from app.ingestion.embedder import Embedder

_BATCH_SIZE = 100


@dataclass
class TitleMatch:
    article_id: str
    title: str
    url: str
    score: float


class TitleIndex:
    """Full-dataset fallback for queries the real (scraped+embedded) corpus can't
    answer yet. Titles need no scraping, so all rows can be embedded in a handful of
    batched calls instead of waiting on the per-article scrape+chunk+embed pipeline.
    Embedding similarity (not literal keyword match) is what lets a query like
    "earn 100 dollars a day" surface a differently-worded title like "From Zero to
    $100 a Day..." — see the abstain fallback in generation/chain.py."""

    def __init__(self, index_path: str):
        self._path = Path(index_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ids: list[str] = []
        self._titles: list[str] = []
        self._urls: list[str] = []
        self._vectors: np.ndarray | None = None
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self._path.exists():
            return
        with open(self._path, "rb") as f:
            data = pickle.load(f)
        self._ids = data["ids"]
        self._titles = data["titles"]
        self._urls = data["urls"]
        self._vectors = data["vectors"]

    @property
    def is_ready(self) -> bool:
        return self._vectors is not None

    def __len__(self) -> int:
        return len(self._titles)

    async def build(self, embedder: Embedder) -> None:
        rows = list(load_rows())
        ids = [r.id for r in rows]
        titles = [r.title for r in rows]
        urls = [r.url for r in rows]

        vectors: list[list[float]] = []
        for i in range(0, len(titles), _BATCH_SIZE):
            batch = titles[i : i + _BATCH_SIZE]
            vectors.extend(await embedder.embed_texts(batch))

        matrix = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.clip(norms, 1e-8, None)

        with open(self._path, "wb") as f:
            pickle.dump({"ids": ids, "titles": titles, "urls": urls, "vectors": matrix}, f)

        self._ids, self._titles, self._urls, self._vectors = ids, titles, urls, matrix

    def search(self, query_vec: list[float], top_n: int) -> list[TitleMatch]:
        if self._vectors is None:
            return []

        q = np.array(query_vec, dtype=np.float32)
        q = q / max(float(np.linalg.norm(q)), 1e-8)
        scores = self._vectors @ q  # both sides pre-normalized -> cosine similarity

        # The source CSV has duplicate rows (same article listed twice, sometimes under
        # different ids/urls) — dedup by normalized title so a repeat doesn't crowd out
        # a genuinely different suggestion in the top_n.
        matches: list[TitleMatch] = []
        seen_titles: set[str] = set()
        for i in np.argsort(-scores):
            normalized = self._titles[i].strip().lower()
            if normalized in seen_titles:
                continue
            seen_titles.add(normalized)
            matches.append(
                TitleMatch(article_id=self._ids[i], title=self._titles[i], url=self._urls[i], score=float(scores[i]))
            )
            if len(matches) >= top_n:
                break
        return matches
