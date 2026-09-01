from pydantic import BaseModel

from app.schemas.filters import FilterParams


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    filters: FilterParams | None = None
    top_k: int = 5


class SourceCitation(BaseModel):
    article_id: str
    title: str
    url: str
    publication: str | None
    claps: int | None
    chunk_excerpt: str
