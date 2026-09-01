import asyncio
import random

import httpx
import trafilatura
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.rate_limiter import RateLimiter

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
]


class ScrapeError(Exception):
    pass


class Scraper:
    """Low concurrency + rate-limited + rotating User-Agent, on purpose: Medium sits
    behind Cloudflare and high-concurrency scraping gets an IP blocked within the
    first ~50 requests. This is meant to take hours over the full dataset, not
    minutes."""

    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.SCRAPE_CONCURRENCY)
        self._rate_limiter = RateLimiter(rate_per_minute=60_000 / settings.SCRAPE_RATE_LIMIT_DELAY_MS, burst=1)
        self._client = httpx.AsyncClient(timeout=settings.SCRAPE_TIMEOUT_SECONDS, follow_redirects=True)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def fetch_text(self, url: str) -> str:
        async with self._semaphore:
            await self._rate_limiter.acquire()
            await asyncio.sleep(random.uniform(0.2, 0.8))  # extra jitter against fixed-interval detection
            raw_html = await self._fetch_html(url)

        text = trafilatura.extract(raw_html, include_comments=False, include_tables=False)
        if not text:
            raise ScrapeError("trafilatura extracted no content")
        return text

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        reraise=True,
    )
    async def _fetch_html(self, url: str) -> str:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = await self._client.get(url, headers=headers)
        response.raise_for_status()
        return response.text
