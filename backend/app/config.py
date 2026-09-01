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

    # Gemini
    GOOGLE_API_KEY: str
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_EMBEDDING_DIMS: int = 768
    GEMINI_CHAT_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_RPM: int = 5  # conservative default — real free-tier embed RPM hit 429 well below the 10M TPM figure the TPM quota alone would suggest

    # OpenRouter (fallback generation only)
    OPENROUTER_API_KEY: str
    OPENROUTER_FALLBACK_MODEL: str = "z-ai/glm-5.2:free"
    PROVIDER_FAILOVER_COOLDOWN_SECONDS: int = 300

    # Cohere Rerank
    COHERE_API_KEY: str
    COHERE_EVAL_RPM: int = 5
    RERANK_ABSTAIN_THRESHOLD: float = 0.3

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


settings = Settings()
