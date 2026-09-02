import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_embedder, get_provider_router, get_retrieval_pipeline, get_title_index
from app.db.models import Article
from app.db.session import SessionLocal
from app.generation.chain import run_chat
from app.generation.provider_router import ProviderRouter
from app.ingestion.embedder import Embedder
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.title_index import TitleIndex
from app.schemas.chat import ChatRequest
from app.schemas.filters import FilterOptionsResponse

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    retrieval: RetrievalPipeline = Depends(get_retrieval_pipeline),
    generator: ProviderRouter = Depends(get_provider_router),
    embedder: Embedder = Depends(get_embedder),
    title_index: TitleIndex = Depends(get_title_index),
) -> EventSourceResponse:
    messages = [m.model_dump() for m in request.messages]

    async def event_generator():
        async for event in run_chat(
            retrieval, generator, messages, request.filters, request.top_k, embedder, title_index
        ):
            yield {"event": event["event"], "data": json.dumps(event["data"])}

    return EventSourceResponse(event_generator())


@router.get("/filters/options", response_model=FilterOptionsResponse)
async def filters_options() -> FilterOptionsResponse:
    async with SessionLocal() as session:
        publications = (await session.execute(select(Article.publication).distinct())).scalars().all()
        row = (
            await session.execute(
                select(
                    func.min(Article.claps),
                    func.max(Article.claps),
                    func.min(Article.reading_time),
                    func.max(Article.reading_time),
                    func.min(Article.published_date),
                    func.max(Article.published_date),
                )
            )
        ).one()

    return FilterOptionsResponse(
        publications=sorted(p for p in publications if p),
        claps_min=row[0],
        claps_max=row[1],
        reading_time_min=row[2],
        reading_time_max=row[3],
        date_min=row[4],
        date_max=row[5],
    )
