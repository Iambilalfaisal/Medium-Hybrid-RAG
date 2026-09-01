import time
from typing import AsyncIterator

from app.config import settings
from app.generation.llm import GeminiClient, OpenRouterClient


class ProviderRouter:
    """Implements GeneratorProtocol. Gemini is tried first, OpenRouter is the
    fallback. try_stream is a coroutine — see protocols/generator.py — that must
    fully resolve, including fetching the first real content chunk, before it
    returns an iterator. That ordering is what makes failover possible only before
    the first token, never mid-stream: a failure raised inside this coroutine (during
    connection or while pulling that first chunk) is caught here and the next
    provider is tried; a failure raised while the CALLER iterates the returned
    generator is not retried or hidden — it propagates to chain.py, which is
    responsible for turning it into an SSE error event and closing the stream.
    """

    def __init__(self):
        self._clients = [GeminiClient(), OpenRouterClient()]
        self._cooldown_until: dict[str, float] = {c.name: 0.0 for c in self._clients}

    def _ordered_clients(self):
        now = time.monotonic()
        # Stable sort: clients not in cooldown come first; if everything is in
        # cooldown, original order is preserved — we still have to try something.
        return sorted(self._clients, key=lambda c: self._cooldown_until[c.name] > now)

    def _mark_failed(self, client) -> None:
        self._cooldown_until[client.name] = time.monotonic() + settings.PROVIDER_FAILOVER_COOLDOWN_SECONDS

    def _mark_recovered(self, client) -> None:
        self._cooldown_until[client.name] = 0.0

    async def complete(self, messages: list[dict[str, str]]) -> str:
        last_exc: Exception | None = None
        for client in self._ordered_clients():
            try:
                text = await client.complete(messages)
                self._mark_recovered(client)
                return text
            except Exception as exc:  # noqa: BLE001 - any provider failure triggers failover
                self._mark_failed(client)
                last_exc = exc
        raise RuntimeError(f"All generation providers failed: {last_exc}") from last_exc

    async def try_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        last_exc: Exception | None = None
        for client in self._ordered_clients():
            try:
                aiter, extract = await client.start_stream(messages)
                first_chunk = await self._first_text_chunk(aiter, extract)
                self._mark_recovered(client)
                return self._stream_from(first_chunk, aiter, extract)
            except Exception as exc:  # noqa: BLE001 - any provider failure triggers failover
                self._mark_failed(client)
                last_exc = exc
        raise RuntimeError(f"All generation providers failed to start a stream: {last_exc}") from last_exc

    @staticmethod
    async def _first_text_chunk(aiter, extract) -> str:
        """Pull raw chunks until one carries actual text (some SDKs emit
        metadata-only chunks first) or the stream ends — forces the provider to
        actually start producing before we commit to it."""
        async for raw in aiter:
            text = extract(raw)
            if text:
                return text
        return ""

    @staticmethod
    async def _stream_from(first_chunk: str, aiter, extract) -> AsyncIterator[str]:
        if first_chunk:
            yield first_chunk
        async for raw in aiter:
            text = extract(raw)
            if text:
                yield text
