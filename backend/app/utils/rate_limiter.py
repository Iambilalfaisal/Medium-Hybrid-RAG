import asyncio
import time


class RateLimiter:
    """Async token bucket. One instance per call site with real, independent pacing
    needs (the scraper's inter-request delay, the eval loop's Cohere pacing) — same
    class, different configs, instead of three ad hoc sleep/retry implementations."""

    def __init__(self, rate_per_minute: float, burst: int | None = None):
        self._rate_per_second = rate_per_minute / 60.0
        self._capacity = burst if burst is not None else max(1, int(rate_per_minute))
        self._tokens = float(self._capacity)
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._updated_at
                self._updated_at = now
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate_per_second)

                if self._tokens >= 1:
                    self._tokens -= 1
                    return

                wait_for = (1 - self._tokens) / self._rate_per_second
                await asyncio.sleep(wait_for)
