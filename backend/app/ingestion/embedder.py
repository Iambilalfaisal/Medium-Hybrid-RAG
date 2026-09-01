import asyncio

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_message, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.rate_limiter import RateLimiter

_BATCH_SIZE = 100


class Embedder:
    """Single concrete implementation (Gemini) — no EmbedderProtocol; see
    protocols/generator.py for why only the generator has a protocol today.
    Rate-limited: a real ingestion run against the live API hit
    RESOURCE_EXHAUSTED on the embedding model's per-minute quota well below what the
    published token-per-minute figure alone would suggest — pacing calls here is not
    speculative hardening, it reproduced on the first real run."""

    def __init__(self):
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self._model = settings.GEMINI_EMBEDDING_MODEL
        self._dims = settings.GEMINI_EMBEDDING_DIMS
        self._rate_limiter = RateLimiter(rate_per_minute=settings.GEMINI_EMBEDDING_RPM, burst=1)

    async def embed_texts(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            await self._rate_limiter.acquire()
            response = await self._embed_batch(batch, task_type)
            vectors.extend(e.values for e in response.embeddings)
        return vectors

    @retry(
        retry=retry_if_exception_message(match=".*RESOURCE_EXHAUSTED.*"),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        reraise=True,
    )
    async def _embed_batch(self, batch: list[str], task_type: str):
        return await asyncio.to_thread(
            self._client.models.embed_content,
            model=self._model,
            contents=batch,
            config=types.EmbedContentConfig(output_dimensionality=self._dims, task_type=task_type),
        )

    async def embed_query(self, text: str) -> list[float]:
        """Gemini embeddings are asymmetric: a query embedded with RETRIEVAL_QUERY
        matches better against documents embedded with RETRIEVAL_DOCUMENT than if
        both used the same task type."""
        vectors = await self.embed_texts([text], task_type="RETRIEVAL_QUERY")
        return vectors[0]
