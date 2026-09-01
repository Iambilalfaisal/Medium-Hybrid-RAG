from typing import AsyncIterator

from app.generation.prompt import build_messages
from app.generation.provider_router import ProviderRouter
from app.generation.query_rewrite import rewrite_query
from app.retrieval.pipeline import RetrievalPipeline
from app.schemas.filters import FilterParams
from app.schemas.retrieval import Abstain, RankedParents


async def run_chat(
    retrieval: RetrievalPipeline,
    generator: ProviderRouter,
    messages: list[dict[str, str]],
    filters: FilterParams | None,
    top_k: int,
) -> AsyncIterator[dict]:
    """Yields SSE-ready event dicts: {"event": "sources"|"token"|"done"|"abstain"|"error", "data": {...}}.
    The API layer (routes_chat.py) is responsible for serializing these as SSE — kept
    out of this module so the chat logic itself stays transport-agnostic."""
    rewritten_query = await rewrite_query(generator, messages)

    try:
        result = await retrieval.run(rewritten_query, filters, top_k)
    except Exception as exc:  # noqa: BLE001 - surfaced to the client as an SSE error, not a 500
        yield {"event": "error", "data": {"message": f"retrieval failed: {exc}"}}
        return

    if isinstance(result, Abstain):
        yield {"event": "abstain", "data": {"reason": result.reason}}
        return

    ranked: RankedParents = result
    sources = [
        {
            "article_id": p.article_id,
            "title": p.title,
            "url": p.url,
            "publication": p.publication,
            "claps": p.claps,
            "chunk_excerpt": p.text[:280],
        }
        for p in ranked.parents
    ]
    yield {"event": "sources", "data": {"sources": sources, "rewritten_query": rewritten_query}}

    prompt_messages = build_messages(rewritten_query, ranked, messages[:-1])

    try:
        stream = await generator.try_stream(prompt_messages)
    except Exception as exc:  # noqa: BLE001 - both providers failed before any token
        yield {"event": "error", "data": {"message": f"generation unavailable: {exc}"}}
        return

    try:
        async for token in stream:
            yield {"event": "token", "data": {"text": token}}
    except Exception as exc:  # noqa: BLE001
        # Mid-stream failure: per provider_router's contract this is never retried or
        # failed over silently — close with an explicit error event instead.
        yield {"event": "error", "data": {"message": f"stream interrupted: {exc}"}}
        return

    yield {"event": "done", "data": {}}
