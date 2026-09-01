from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class GeneratorProtocol(Protocol):
    """Contract satisfied by generation.provider_router.ProviderRouter — the only
    component in this codebase with two real, swappable implementations (Gemini,
    OpenRouter) today. No EmbedderProtocol/RerankerProtocol: each of those has exactly
    one implementation, so a protocol there would be indirection with no current need.
    """

    async def complete(self, messages: list[dict[str, str]]) -> str:
        """Non-streaming call — used for query rewriting and the RAGAS judge."""
        ...

    async def try_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """Streaming call. This is a coroutine, not an async generator: it must be
        awaited to completion — including fetching and buffering the first chunk from
        the underlying provider — before it returns the async iterator a caller then
        consumes. That ordering is what makes provider failover possible at all:
        failing over means catching an error during THIS await, flipping provider, and
        retrying the await — never something a caller can do once it starts iterating
        the returned generator. A failure after that point is not retried.
        """
        ...
