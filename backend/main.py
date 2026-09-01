from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import deps
from app.api.routes_chat import router as chat_router
from app.api.routes_eval import router as eval_router
from app.api.routes_health import router as health_router
from app.api.routes_ingestion import router as ingestion_router
from app.logging_conf import configure_logging
from app.middleware.error_handlers import register_error_handlers
from app.middleware.logging import CorrelationIdMiddleware

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await deps.shutdown()


app = FastAPI(title="Medium Hybrid RAG", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(chat_router)
app.include_router(eval_router)
