import asyncio

from fastapi import APIRouter
from sqlalchemy import select

from app.db.models import EvalRun
from app.db.session import SessionLocal
from app.schemas.eval import EvalRunResult, EvalRunTriggeredResponse, RagasScores, RetrievalMetrics

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run", response_model=EvalRunTriggeredResponse)
async def trigger_eval() -> EvalRunTriggeredResponse:
    # Lazy import: eval/ is a top-level package (sibling to backend/), not part of
    # this app package. Also needs the repo root on sys.path first — this process
    # runs with cwd=backend/, so the parent directory isn't there by default (the
    # mirror image of eval/run_eval.py needing backend/ added to ITS sys.path).
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from eval.run_eval import run_evaluation

    asyncio.create_task(run_evaluation())
    return EvalRunTriggeredResponse(status="running")


@router.get("/results", response_model=list[EvalRunResult])
async def eval_results() -> list[EvalRunResult]:
    async with SessionLocal() as session:
        rows = (await session.execute(select(EvalRun).order_by(EvalRun.run_at.desc()).limit(20))).scalars().all()

    return [
        EvalRunResult(
            id=row.id,
            run_at=row.run_at,
            ragas_scores=RagasScores(**row.ragas_scores),
            retrieval_metrics=RetrievalMetrics(**row.retrieval_metrics),
        )
        for row in rows
    ]
