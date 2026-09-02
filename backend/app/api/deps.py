"""Real singletons, constructed once per process at import time (this module is
imported exactly once by main.py) and exposed via FastAPI's Depends() — not
constructed fresh per-request. A bad DB URL or missing API key fails at import
(startup), not on the first request."""

from app.config import settings
from app.db.session import SessionLocal
from app.generation.provider_router import ProviderRouter
from app.ingestion.embedder import Embedder
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.progress import ProgressTracker
from app.ingestion.scrape_cache import ScrapeCache
from app.ingestion.scraper import Scraper
from app.retrieval.bm25_store import BM25Store
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.title_index import TitleIndex

_embedder = Embedder()
_scrape_cache = ScrapeCache(settings.SCRAPE_CACHE_PATH)
_scraper = Scraper()
_bm25_store = BM25Store(settings.BM25_INDEX_PATH)
_title_index = TitleIndex(settings.TITLE_INDEX_PATH)
_progress = ProgressTracker()
_provider_router = ProviderRouter()

_ingestion_pipeline = IngestionPipeline(
    session_factory=SessionLocal,
    scrape_cache=_scrape_cache,
    embedder=_embedder,
    scraper=_scraper,
    bm25_store=_bm25_store,
    progress=_progress,
)

_retrieval_pipeline = RetrievalPipeline(
    session_factory=SessionLocal,
    bm25_store=_bm25_store,
    embedder=_embedder,
)


def get_ingestion_pipeline() -> IngestionPipeline:
    return _ingestion_pipeline


def get_retrieval_pipeline() -> RetrievalPipeline:
    return _retrieval_pipeline


def get_provider_router() -> ProviderRouter:
    return _provider_router


def get_embedder() -> Embedder:
    return _embedder


def get_title_index() -> TitleIndex:
    return _title_index


def get_progress_tracker() -> ProgressTracker:
    return _progress


async def shutdown() -> None:
    """Called from main.py's lifespan on shutdown — the scraper's httpx client is
    long-lived across ingestion runs (see pipeline.py) and needs an explicit close
    somewhere; app shutdown is that place."""
    await _scraper.aclose()
