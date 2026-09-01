import asyncio
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProgressSnapshot:
    run_id: int | None = None
    status: str = "idle"  # idle | running | completed | failed
    current_stage: str = ""
    articles_total: int = 0
    articles_processed: int = 0
    articles_scraped_ok: int = 0
    articles_skipped: int = 0
    cleaner_rejected_count: int = 0
    chunks_created: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class ProgressTracker:
    """In-memory live view of the current/most recent ingestion run, read by
    GET /ingestion/status without a DB round trip. The ingestion_runs table remains
    the durable source of truth (and the concurrency guard); this is purely a fast,
    frequently-updated mirror of the currently running pipeline's counters."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._snapshot = ProgressSnapshot()

    async def start(self, run_id: int, articles_total: int) -> None:
        async with self._lock:
            self._snapshot = ProgressSnapshot(
                run_id=run_id,
                status="running",
                current_stage="scraping",
                articles_total=articles_total,
                started_at=datetime.utcnow(),
            )

    async def update(self, **kwargs) -> None:
        async with self._lock:
            for key, value in kwargs.items():
                setattr(self._snapshot, key, value)

    async def increment(self, **kwargs) -> None:
        async with self._lock:
            for key, delta in kwargs.items():
                setattr(self._snapshot, key, getattr(self._snapshot, key) + delta)

    async def finish(self, status: str, error: str | None = None) -> None:
        async with self._lock:
            self._snapshot.status = status
            self._snapshot.current_stage = ""
            self._snapshot.finished_at = datetime.utcnow()
            self._snapshot.error = error

    async def snapshot(self) -> ProgressSnapshot:
        async with self._lock:
            return ProgressSnapshot(**vars(self._snapshot))
