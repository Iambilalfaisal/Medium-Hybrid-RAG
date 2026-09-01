from app.schemas.retrieval import RankedParents

_SYSTEM_PROMPT = (
    "You are a research assistant answering questions using ONLY the excerpts below, "
    "drawn from Medium articles. For every claim, cite its source inline using the "
    "format (Title, Publication, Year) taken from that excerpt's metadata. If the "
    "excerpts don't contain enough information to answer the question, say so "
    "plainly instead of guessing or using outside knowledge."
)


def _format_context(ranked: RankedParents) -> str:
    blocks = []
    for i, parent in enumerate(ranked.parents, start=1):
        year = parent.published_date.year if parent.published_date else "n.d."
        blocks.append(
            f"[Excerpt {i}] Title: {parent.title} | Publication: {parent.publication or 'Unknown'} | "
            f"Year: {year} | Claps: {parent.claps if parent.claps is not None else 'n/a'}\n{parent.text}"
        )
    return "\n\n".join(blocks)


def build_messages(query: str, ranked: RankedParents, history: list[dict[str, str]]) -> list[dict[str, str]]:
    """`history` is the prior chat turns (not including the current query) — included
    so follow-up answers stay consistent with what was already said, even though
    retrieval itself only runs against the (already rewritten) current query."""
    context = _format_context(ranked)
    user_turn = f"Context:\n{context}\n\nQuestion: {query}"
    return [{"role": "system", "content": _SYSTEM_PROMPT}, *history, {"role": "user", "content": user_turn}]
