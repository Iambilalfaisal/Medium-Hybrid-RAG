from datetime import datetime

from pydantic import BaseModel


class IngestionRunRequest(BaseModel):
    force_rescrape: bool = False


class IngestionRunStartedResponse(BaseModel):
    run_id: int
    status: str


class IngestionAlreadyRunningResponse(BaseModel):
    detail: str = "An ingestion run is already in progress"
    active_run_id: int


class IngestionStatusResponse(BaseModel):
    run_id: int | None
    status: str
    current_stage: str
    articles_total: int
    articles_processed: int
    articles_scraped_ok: int
    articles_skipped: int
    cleaner_rejected_count: int
    chunks_created: int
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None


class IngestionStatsResponse(BaseModel):
    total_articles_ingested: int
    total_chunks: int
    last_run_at: datetime | None
    last_run_status: str | None
    bm25_index_present: bool
