"""Thin FastAPI-facing re-export. Route handlers depend on this name via
api/deps.py rather than importing RetrievalPipeline from retrieval/pipeline.py
directly, so the dependency wiring has one obvious place to look."""

from app.retrieval.pipeline import RetrievalPipeline

__all__ = ["RetrievalPipeline"]
