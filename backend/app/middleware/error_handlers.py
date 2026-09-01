import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.ingestion.pipeline import IngestionAlreadyRunningError

logger = logging.getLogger("app.errors")


async def ingestion_already_running_handler(request: Request, exc: IngestionAlreadyRunningError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "An ingestion run is already in progress", "active_run_id": exc.active_run_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IngestionAlreadyRunningError, ingestion_already_running_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
