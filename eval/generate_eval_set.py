"""Synthesizes a reusable eval query set from whatever's currently ingested. Run from
the repo root: `python -m eval.generate_eval_set`. Idempotent — refuses to overwrite
an existing eval_queries.json (delete it manually to regenerate).

There's no human-curated ground truth available for this dataset, so "ground truth"
here is itself LLM-generated: useful for regression-testing pipeline changes, not an
independent quality bar (see the plan's Risks section on this exact tradeoff).
"""

import asyncio
import json
import random
import sys
from pathlib import Path

# backend/app's own modules import each other as `from app.xxx import yyy` (absolute,
# resolved against backend/ being on sys.path — true when backend's own scripts run
# with cwd=backend/). This script runs from the repo root instead, so backend/ has to
# be added to sys.path explicitly before any of those imports will resolve.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select

from app.db.models import Article, ParentChunk
from app.db.session import SessionLocal
from app.generation.provider_router import ProviderRouter
from app.utils.rate_limiter import RateLimiter
from app.utils.winloop import use_selector_event_loop_on_windows

use_selector_event_loop_on_windows()

EVAL_SET_PATH = Path(__file__).resolve().parent / "eval_queries.json"
SAMPLE_SIZE = 40

_QUESTION_PROMPT = (
    "Read the following excerpt from an article and write ONE specific question that "
    "can be answered using only this excerpt. Output ONLY the question — no preamble, "
    "no quotes.\n\nExcerpt:\n{excerpt}"
)


async def generate_eval_set() -> None:
    if EVAL_SET_PATH.exists():
        print(f"{EVAL_SET_PATH} already exists — delete it manually to regenerate.")
        return

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(ParentChunk.id, ParentChunk.text, ParentChunk.article_id, Article.title).join(
                    Article, Article.id == ParentChunk.article_id
                )
            )
        ).all()

    if not rows:
        print("No ingested parent chunks found — run ingestion before generating the eval set.")
        return

    sample = random.sample(rows, min(SAMPLE_SIZE, len(rows)))

    generator = ProviderRouter()
    # Same rate-limiter class as the scraper (app.utils.rate_limiter) — a different
    # instance/config, not a new implementation, per the plan's shared-utility design.
    rate_limiter = RateLimiter(rate_per_minute=10, burst=1)

    eval_set = []
    for i, row in enumerate(sample, start=1):
        await rate_limiter.acquire()
        question = await generator.complete(
            [{"role": "user", "content": _QUESTION_PROMPT.format(excerpt=row.text[:2000])}]
        )
        eval_set.append(
            {
                "question": question.strip(),
                "ground_truth_article_id": row.article_id,
                "ground_truth_context": row.text,
            }
        )
        print(f"generated {i}/{len(sample)}")

    EVAL_SET_PATH.write_text(json.dumps(eval_set, indent=2), encoding="utf-8")
    print(f"wrote {len(eval_set)} questions to {EVAL_SET_PATH}")


if __name__ == "__main__":
    asyncio.run(generate_eval_set())
