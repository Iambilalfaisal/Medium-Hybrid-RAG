from datetime import datetime

from pydantic import BaseModel


class RagasScores(BaseModel):
    faithfulness: float
    context_precision: float
    context_recall: float
    answer_relevancy: float


class RetrievalMetrics(BaseModel):
    precision_at_k: float
    recall_at_k: float
    f1_at_k: float
    k: int


class EvalRunResult(BaseModel):
    id: int
    run_at: datetime
    ragas_scores: RagasScores
    retrieval_metrics: RetrievalMetrics


class EvalRunTriggeredResponse(BaseModel):
    status: str
