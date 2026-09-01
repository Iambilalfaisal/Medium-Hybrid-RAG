"""Runs the persisted eval set through the real retrieval+generation pipeline and
scores it. Run from the repo root: `python -m eval.run_eval`.

RAGAS metrics are NOT computed via the `ragas` package: the only version on PyPI
(0.4.3) fails to import at all in this environment — `ragas.llms.base` unconditionally
imports `ChatVertexAI` from a `langchain_community` submodule that no longer exists in
current `langchain-community`, and pinning around it breaks langchain-core version
requirements for langgraph/langchain-openai/langchain-classic elsewhere in this venv
(confirmed by trying it). Instead, the four RAGAS-style metrics (faithfulness,
context precision/recall, answer relevancy) are computed with a single LLM-judge call
per query through the same ProviderRouter used for chat — one extra provider call per
query rather than four. Precision/recall/F1@k are computed independently and
objectively: each synthetic question's source article is the one known-relevant
document, so a "hit" is just whether that article appears in the top-K results.
"""

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# See generate_eval_set.py's comment: backend/app's internal imports are
# `from app.xxx import yyy`, resolved against backend/ being on sys.path — this
# script runs from the repo root, so backend/ must be added explicitly first.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.api import deps
from app.config import settings
from app.db.models import EvalRun
from app.db.session import SessionLocal
from app.generation.chain import run_chat
from app.retrieval.pipeline import RetrievalPipeline
from app.schemas.eval import RagasScores, RetrievalMetrics
from app.schemas.retrieval import Abstain, RankedParents
from app.utils.rate_limiter import RateLimiter
from app.utils.winloop import use_selector_event_loop_on_windows

use_selector_event_loop_on_windows()

EVAL_SET_PATH = Path(__file__).resolve().parent / "eval_queries.json"
TOP_K = 5

_JUDGE_PROMPT = """You are evaluating a RAG system's output. Score each of the following from 0.0 to 1.0:

- faithfulness: does every claim in the answer follow from the retrieved context (not outside knowledge)?
- context_precision: what fraction of the retrieved context excerpts are actually relevant to the question?
- context_recall: does the retrieved context contain the information from the reference context needed to answer the question?
- answer_relevancy: does the answer directly address the question asked?

Question: {question}

Retrieved context:
{contexts}

Reference context:
{ground_truth_context}

Generated answer:
{answer}

Respond with ONLY a JSON object, no markdown fences: {{"faithfulness": <float>, "context_precision": <float>, "context_recall": <float>, "answer_relevancy": <float>}}
"""


def _parse_judge_json(raw: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


async def _run_single_query(retrieval: RetrievalPipeline, generator, item: dict, cohere_limiter: RateLimiter) -> dict:
    question = item["question"]
    ground_truth_article_id = item["ground_truth_article_id"]
    ground_truth_context = item["ground_truth_context"]

    await cohere_limiter.acquire()  # reranker (Cohere) is called inside retrieval.run()
    result = await retrieval.run(question, filters=None, top_k=TOP_K)

    if isinstance(result, Abstain):
        return {
            "question": question,
            "retrieval_metrics": {"precision_at_k": 0.0, "recall_at_k": 0.0, "f1_at_k": 0.0, "k": TOP_K},
            "ragas_scores": None,
        }

    ranked: RankedParents = result
    hit = any(p.article_id == ground_truth_article_id for p in ranked.parents)
    precision = (1.0 if hit else 0.0) / TOP_K
    recall = 1.0 if hit else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Reuse chain.py's generation logic directly instead of re-implementing prompt
    # building: consume its SSE-event generator and concatenate tokens into one
    # string — eval doesn't need streaming, just the final answer text.
    answer_parts = []
    async for event in run_chat(retrieval, generator, [{"role": "user", "content": question}], None, TOP_K):
        if event["event"] == "token":
            answer_parts.append(event["data"]["text"])
    answer = "".join(answer_parts)

    contexts_text = "\n---\n".join(p.text for p in ranked.parents)
    judge_response = await generator.complete(
        [
            {
                "role": "user",
                "content": _JUDGE_PROMPT.format(
                    question=question,
                    contexts=contexts_text[:4000],
                    ground_truth_context=ground_truth_context[:2000],
                    answer=answer,
                ),
            }
        ]
    )

    try:
        scores = _parse_judge_json(judge_response)
    except (json.JSONDecodeError, KeyError):
        scores = None

    return {
        "question": question,
        "retrieval_metrics": {"precision_at_k": precision, "recall_at_k": recall, "f1_at_k": f1, "k": TOP_K},
        "ragas_scores": scores,
    }


def _average(dicts: list[dict], key: str) -> float:
    return sum(d[key] for d in dicts) / len(dicts) if dicts else 0.0


async def run_evaluation() -> None:
    if not EVAL_SET_PATH.exists():
        print(f"{EVAL_SET_PATH} not found — run `python -m eval.generate_eval_set` first.")
        return

    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))

    retrieval = deps.get_retrieval_pipeline()
    generator = deps.get_provider_router()
    # Same RateLimiter class as the scraper — a different instance/config, pacing
    # Cohere calls specifically, since a tight loop over 30-50 queries can hit its
    # free-tier RPM even though a single chat turn never does.
    cohere_limiter = RateLimiter(rate_per_minute=settings.COHERE_EVAL_RPM, burst=1)

    results = []
    for i, item in enumerate(eval_set, start=1):
        try:
            result = await _run_single_query(retrieval, generator, item, cohere_limiter)
            results.append(result)
        except Exception as exc:  # noqa: BLE001 - one bad query shouldn't kill the whole run
            print(f"[{i}/{len(eval_set)}] failed: {exc}")
            continue
        print(f"[{i}/{len(eval_set)}] done")

    valid_ragas = [r["ragas_scores"] for r in results if r["ragas_scores"]]
    ragas_avg = RagasScores(
        faithfulness=_average(valid_ragas, "faithfulness"),
        context_precision=_average(valid_ragas, "context_precision"),
        context_recall=_average(valid_ragas, "context_recall"),
        answer_relevancy=_average(valid_ragas, "answer_relevancy"),
    )

    retrieval_metrics_list = [r["retrieval_metrics"] for r in results]
    retrieval_avg = RetrievalMetrics(
        precision_at_k=_average(retrieval_metrics_list, "precision_at_k"),
        recall_at_k=_average(retrieval_metrics_list, "recall_at_k"),
        f1_at_k=_average(retrieval_metrics_list, "f1_at_k"),
        k=TOP_K,
    )

    async with SessionLocal() as session:
        session.add(
            EvalRun(
                run_at=datetime.now(timezone.utc),
                ragas_scores=ragas_avg.model_dump(),
                retrieval_metrics=retrieval_avg.model_dump(),
            )
        )
        await session.commit()

    print(f"Eval run complete: {len(results)}/{len(eval_set)} queries scored.")
    print(ragas_avg)
    print(retrieval_avg)


if __name__ == "__main__":
    asyncio.run(run_evaluation())
