from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_ingestion_pipeline, get_progress_tracker
from app.config import settings
from app.db.models import Article, Chunk, IngestionRun
from app.db.session import get_session
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.progress import ProgressTracker
from app.schemas.ingestion import (
    IngestionRunRequest,
    IngestionRunStartedResponse,
    IngestionStatsResponse,
    IngestionStatusResponse,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run", response_model=IngestionRunStartedResponse)
async def start_ingestion(
    request: IngestionRunRequest, pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)
) -> IngestionRunStartedResponse:
    # IngestionAlreadyRunningError (409) is handled globally — see
    # middleware/error_handlers.py — not caught here.
    run_id = await pipeline.run(force_rescrape=request.force_rescrape)
    return IngestionRunStartedResponse(run_id=run_id, status="running")


@router.get("/status", response_model=IngestionStatusResponse)
async def ingestion_status(progress: ProgressTracker = Depends(get_progress_tracker)) -> IngestionStatusResponse:
    snap = await progress.snapshot()
    return IngestionStatusResponse(
        run_id=snap.run_id,
        status=snap.status,
        current_stage=snap.current_stage,
        articles_total=snap.articles_total,
        articles_processed=snap.articles_processed,
        articles_scraped_ok=snap.articles_scraped_ok,
        articles_skipped=snap.articles_skipped,
        cleaner_rejected_count=snap.cleaner_rejected_count,
        chunks_created=snap.chunks_created,
        started_at=snap.started_at,
        finished_at=snap.finished_at,
        error=snap.error,
    )


@router.get("/stats", response_model=IngestionStatsResponse)
async def ingestion_stats(session: AsyncSession = Depends(get_session)) -> IngestionStatsResponse:
    total_articles = await session.scalar(select(func.count()).select_from(Article))
    total_chunks = await session.scalar(select(func.count()).select_from(Chunk))
    last_run = await session.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))

    return IngestionStatsResponse(
        total_articles_ingested=total_articles or 0,
        total_chunks=total_chunks or 0,
        last_run_at=last_run.started_at if last_run else None,
        last_run_status=last_run.status if last_run else None,
        bm25_index_present=Path(settings.BM25_INDEX_PATH).exists(),
    )
