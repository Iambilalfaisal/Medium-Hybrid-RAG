import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils.correlation import correlation_id_var

logger = logging.getLogger("app.request")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attaches a correlation ID to every request (or reuses one the caller sent),
    so a failure anywhere in the scraper/embedder/BM25 chain during a long-running
    ingestion request can be traced back to one log line instead of grepping
    timestamps across independent log statements."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id") or uuid.uuid4().hex[:8]
        token = correlation_id_var.set(correlation_id)
        try:
            logger.info("-> %s %s", request.method, request.url.path)
            response = await call_next(request)
            response.headers["x-correlation-id"] = correlation_id
            logger.info("<- %s %s %s", request.method, request.url.path, response.status_code)
            return response
        finally:
            correlation_id_var.reset(token)
