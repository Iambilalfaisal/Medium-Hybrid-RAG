from dataclasses import dataclass, field
from datetime import date


@dataclass
class FilterClause:
    """Output of RetrievalPipeline.resolve_filters: the eligible chunk-id set computed
    ONCE from the metadata filter (a single SQL query joining chunks->articles), then
    reused as-is by both dense (`WHERE chunk.id IN (...)`) and sparse (in-memory
    id-map filtering) search — guaranteeing they score an identical candidate set
    instead of two independently-derived filter expressions that could drift."""

    eligible_chunk_ids: set[int] | None  # None means "no filter — every chunk eligible"


@dataclass
class ScoredChunk:
    chunk_id: int
    score: float


@dataclass
class DenseResults:
    hits: list[ScoredChunk]


@dataclass
class SparseResults:
    hits: list[ScoredChunk]


@dataclass
class FusedHit:
    chunk_id: int
    rrf_score: float


@dataclass
class FusedResults:
    hits: list[FusedHit]


@dataclass
class ResolvedParent:
    parent_chunk_id: int
    max_rrf_score: float
    child_chunk_ids: list[int] = field(default_factory=list)


@dataclass
class ResolvedParents:
    parents: list[ResolvedParent]


@dataclass
class RankedParent:
    parent_chunk_id: int
    rerank_score: float
    text: str
    article_id: str
    title: str
    url: str
    publication: str | None
    published_date: date | None
    claps: int | None


@dataclass
class RankedParents:
    parents: list[RankedParent]


@dataclass
class Abstain:
    reason: str


# What RetrievalPipeline.run() ultimately returns — callers pattern-match on type.
RetrievalResult = RankedParents | Abstain
