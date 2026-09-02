from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, not relative: a relative ".env" resolves against the process's cwd, which
# differs between running backend scripts (cwd=backend/) and eval/ scripts (cwd=repo
# root, needed for `from backend.app...` imports) — a relative path would silently
# load the unrelated project's .env sitting at the repo root instead of this one.
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_PATH, extra="ignore")

    # Postgres
    DATABASE_URL: str

    # Gemini (chat generation only — embeddings moved to Cohere, see below)
    GOOGLE_API_KEY: str
    GEMINI_CHAT_MODEL: str = "gemini-3.5-flash-lite"

    # OpenRouter (fallback generation only)
    OPENROUTER_API_KEY: str
    OPENROUTER_FALLBACK_MODEL: str = "z-ai/glm-5.2:free"
    PROVIDER_FAILOVER_COOLDOWN_SECONDS: int = 300

    # Cohere (rerank + all embeddings — separate allowances on the trial key)
    COHERE_API_KEY: str
    COHERE_EVAL_RPM: int = 5
    RERANK_ABSTAIN_THRESHOLD: float = 0.3
    EMBEDDING_MODEL: str = "embed-v4.0"
    EMBEDDING_DIMS: int = 1536
    EMBEDDING_RPM: int = 20

    # Scraping
    SCRAPE_CONCURRENCY: int = 2
    SCRAPE_RATE_LIMIT_DELAY_MS: int = 1500
    SCRAPE_TIMEOUT_SECONDS: int = 15
    MIN_TEXT_LENGTH: int = 500

    # Chunking
    CHILD_CHUNK_SIZE: int = 512
    PARENT_CHUNK_SIZE: int = 2048
    CHILD_CHUNK_OVERLAP: int = 128

    # Artifacts
    BM25_INDEX_PATH: str = "artifacts/bm25_index.pkl"
    SCRAPE_CACHE_PATH: str = "artifacts/scrape_cache.sqlite3"
    TITLE_INDEX_PATH: str = "artifacts/title_index.pkl"
    TITLE_SUGGEST_THRESHOLD: float = 0.25


settings = Settings()
