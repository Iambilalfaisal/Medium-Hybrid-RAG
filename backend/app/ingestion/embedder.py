import cohere
from cohere.errors import TooManyRequestsError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.rate_limiter import RateLimiter

_BATCH_SIZE = 96  # Cohere embed's hard per-call batch limit


class Embedder:
    """Single concrete implementation (Cohere) — no EmbedderProtocol; see
    protocols/generator.py for why only the generator has a protocol today. Went
    through Gemini (daily embed quota exhausted) and OpenRouter free models (50
    requests/day account-wide cap, also exhausted) before landing here: Cohere's
    trial key has a separate embed allowance (1000 calls/month) from its rerank
    allowance, with real headroom left. Cohere embeddings are asymmetric like
    Gemini's were (search_document vs search_query input_type) for better
    retrieval quality."""

    def __init__(self):
        self._client = cohere.AsyncClientV2(api_key=settings.COHERE_API_KEY)
        self._model = settings.EMBEDDING_MODEL
        self._rate_limiter = RateLimiter(rate_per_minute=settings.EMBEDDING_RPM, burst=1)

    async def embed_texts(self, texts: list[str], input_type: str = "search_document") -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            await self._rate_limiter.acquire()
            response = await self._embed_batch(batch, input_type)
            vectors.extend(response.embeddings.float_)
        return vectors

    @retry(
        retry=retry_if_exception_type(TooManyRequestsError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        reraise=True,
    )
    async def _embed_batch(self, batch: list[str], input_type: str):
        return await self._client.embed(
            texts=batch, model=self._model, input_type=input_type, embedding_types=["float"]
        )

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text], input_type="search_query")
        return vectors[0]
