import asyncio
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CacheEntry:
    status: str  # "success" | "failed"
    text: str | None
    reason: str | None


class ScrapeCache:
    """Persistent success/failed cache keyed by article id, so re-running ingestion
    never re-fetches a URL whose outcome (success OR permanent-looking failure) is
    already known. A brief synchronous SQLite write per entry is fine here — this is
    ingestion-time only, never on the query path."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scrape_cache (
                article_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                text TEXT,
                reason TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self._conn.commit()

    async def get(self, article_id: str) -> CacheEntry | None:
        async with self._lock:
            row = self._conn.execute(
                "SELECT status, text, reason FROM scrape_cache WHERE article_id = ?",
                (article_id,),
            ).fetchone()
        return None if row is None else CacheEntry(status=row[0], text=row[1], reason=row[2])

    async def put_success(self, article_id: str, url: str, text: str) -> None:
        await self._write(article_id, url, "success", text, None)

    async def put_failed(self, article_id: str, url: str, reason: str) -> None:
        await self._write(article_id, url, "failed", None, reason)

    async def _write(
        self, article_id: str, url: str, status: str, text: str | None, reason: str | None
    ) -> None:
        async with self._lock:
            self._conn.execute(
                """
                INSERT INTO scrape_cache (article_id, url, status, text, reason, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(article_id) DO UPDATE SET
                    status = excluded.status,
                    text = excluded.text,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (article_id, url, status, text, reason),
            )
            self._conn.commit()
