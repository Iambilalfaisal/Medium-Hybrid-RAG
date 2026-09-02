import json
import re
from typing import AsyncIterator

from app.config import settings
from app.generation.prompt import build_messages
from app.generation.provider_router import ProviderRouter
from app.generation.query_rewrite import rewrite_query
from app.ingestion.embedder import Embedder
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.title_index import TitleIndex, TitleMatch
from app.schemas.filters import FilterParams
from app.schemas.retrieval import Abstain, RankedParents

_DESCRIBE_PROMPT = """For each of the following article titles, write ONE short sentence \
(under 20 words) guessing what it covers and why it might help answer the question — \
based on the title alone, since the article itself hasn't been read.

Question: {query}

Titles:
{numbered_titles}

Respond with ONLY a JSON array of strings, one per title, same order, no markdown fences.
"""


async def _describe_suggestions(generator: ProviderRouter, query: str, matches: list[TitleMatch]) -> list[str]:
    numbered_titles = "\n".join(f"{i}. {m.title}" for i, m in enumerate(matches, start=1))
    raw = await generator.complete(
        [{"role": "user", "content": _DESCRIBE_PROMPT.format(query=query, numbered_titles=numbered_titles)}]
    )
    try:
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        descriptions = json.loads(cleaned)
        if isinstance(descriptions, list) and len(descriptions) == len(matches):
            return [str(d) for d in descriptions]
    except (json.JSONDecodeError, TypeError):
        pass
    return [""] * len(matches)  # description is a nice-to-have — never block suggestions on a parse failure


async def run_chat(
    retrieval: RetrievalPipeline,
    generator: ProviderRouter,
    messages: list[dict[str, str]],
    filters: FilterParams | None,
    top_k: int,
    embedder: Embedder | None = None,
    title_index: TitleIndex | None = None,
) -> AsyncIterator[dict]:
    """Yields SSE-ready event dicts:
    {"event": "sources"|"token"|"done"|"abstain"|"suggestions"|"error", "data": {...}}.
    The API layer (routes_chat.py) is responsible for serializing these as SSE — kept
    out of this module so the chat logic itself stays transport-agnostic.
    `embedder`/`title_index` are optional so callers that don't need the title-search
    fallback (eval harness) don't have to supply them."""
    rewritten_query = await rewrite_query(generator, messages)

    try:
        result = await retrieval.run(rewritten_query, filters, top_k)
    except Exception as exc:  # noqa: BLE001 - surfaced to the client as an SSE error, not a 500
        yield {"event": "error", "data": {"message": f"retrieval failed: {exc}"}}
        return

    if isinstance(result, Abstain):
        if embedder is not None and title_index is not None and title_index.is_ready:
            query_vec = await embedder.embed_query(rewritten_query)
            matches = [
                m for m in title_index.search(query_vec, top_n=5) if m.score >= settings.TITLE_SUGGEST_THRESHOLD
            ]
            if matches:
                descriptions = await _describe_suggestions(generator, rewritten_query, matches)
                yield {
                    "event": "suggestions",
                    "data": {
                        "reason": result.reason,
                        "suggestions": [
                            {"title": m.title, "url": m.url, "score": m.score, "description": d}
                            for m, d in zip(matches, descriptions)
                        ],
                    },
                }
                return

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
