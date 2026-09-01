from app.protocols.generator import GeneratorProtocol

_SYSTEM_PROMPT = (
    "Rewrite the user's latest message into a single, standalone search query that "
    "captures their intent, using the conversation history for context. Output ONLY "
    "the rewritten query — no explanation, no quotes, no preamble."
)


async def rewrite_query(generator: GeneratorProtocol, messages: list[dict[str, str]]) -> str:
    """No-op on the first turn — there's no ambiguity to resolve yet. `messages`
    follows the OpenAI role convention: [{"role": "user"|"assistant", "content": ...}, ...].
    """
    if len(messages) <= 1:
        return messages[-1]["content"]

    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    rewritten = await generator.complete(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": history_text},
        ]
    )
    return rewritten.strip() or messages[-1]["content"]
