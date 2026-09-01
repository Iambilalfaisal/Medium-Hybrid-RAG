from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String)
    claps: Mapped[int | None] = mapped_column(Integer)
    responses: Mapped[int | None] = mapped_column(Integer)
    reading_time: Mapped[float | None] = mapped_column(Numeric)
    publication: Mapped[str | None] = mapped_column(String)
    published_date: Mapped[date | None] = mapped_column(Date)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    full_text_len: Mapped[int | None] = mapped_column(Integer)

    parent_chunks: Mapped[list["ParentChunk"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_articles_publication", "publication"),
        Index("idx_articles_claps", "claps"),
        Index("idx_articles_date", "published_date"),
        Index("idx_articles_reading_time", "reading_time"),
    )


class ParentChunk(Base):
    """Larger, paragraph-scale chunk. Never embedded directly — returned as LLM
    context once one of its children is matched by dense/sparse search."""

    __tablename__ = "parent_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    article: Mapped["Article"] = relationship(back_populates="parent_chunks")
    children: Mapped[list["Chunk"]] = relationship(back_populates="parent")


class Chunk(Base):
    """Small, embedded/searched child chunk. Retrieval matches happen here; results
    are resolved back to the owning ParentChunk before reranking/generation."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("parent_chunks.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.GEMINI_EMBEDDING_DIMS))

    parent: Mapped["ParentChunk"] = relationship(back_populates="children")
    article: Mapped["Article"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_article_id", "article_id"),
        Index(
            "idx_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class IngestionRun(Base):
    """One row per ingestion run. `status='running'` also serves as the concurrent-run
    guard: IngestionPipeline refuses to start a new run while one is already `running`.
    """

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, nullable=False, default="running")
    articles_total: Mapped[int | None] = mapped_column(Integer)
    articles_scraped_ok: Mapped[int | None] = mapped_column(Integer)
    articles_skipped: Mapped[int | None] = mapped_column(Integer)
    chunks_created: Mapped[int | None] = mapped_column(Integer)
    cleaner_rejected_count: Mapped[int | None] = mapped_column(Integer)


class EvalRun(Base):
    """Shapes of ragas_scores/retrieval_metrics are locked by app/schemas/eval.py —
    run_eval.py serializes through those Pydantic models before writing here."""

    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ragas_scores: Mapped[dict] = mapped_column(JSONB)
    retrieval_metrics: Mapped[dict] = mapped_column(JSONB)
