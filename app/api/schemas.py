from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app_name: str
    app_env: str


class IngestResponse(BaseModel):
    doc_id: str
    source: str
    chunks_indexed: int
    latency_ms: float


class PromptVersionInfo(BaseModel):
    version: str
    description: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    prompt_version: str | None = Field(
        default=None,
        description="v1_grounded | v2_strict_citations | v3_refusal_aware",
    )


class Citation(BaseModel):
    chunk_id: str
    score: float
    source: str
    excerpt: str


class GroundingReport(BaseModel):
    grounded: bool
    reason: str
    top_score: float
    is_refusal: bool


class QueryResponse(BaseModel):
    question: str
    answer: str
    generation_mode: str
    prompt_version: str
    citations: list[Citation]
    retrieval_count: int
    grounding: GroundingReport
    latency_ms: float


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class RetrieveHit(BaseModel):
    chunk_id: str
    text: str
    score: float
    metadata: dict


class RetrieveResponse(BaseModel):
    query: str
    hits: list[RetrieveHit]
    count: int


class ExperimentRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k_values: list[int] | None = Field(default=None)
    score_thresholds: list[float | None] | None = Field(default=None)


class ExperimentRun(BaseModel):
    top_k: int
    score_threshold: float | None
    hit_count: int
    top_score: float | None
    latency_ms: float


class ExperimentResponse(BaseModel):
    query: str
    runs: list[ExperimentRun]


class EvaluateRequest(BaseModel):
    benchmark_path: str | None = None
    k_values: list[int] | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    collection_name: str | None = Field(
        default=None,
        description="Qdrant collection for eval; default topk_eval_collection (not rag_overview index)",
    )


class EvaluateResponse(BaseModel):
    metrics: dict[str, float]
    k_values: list[int]
    per_query: list[dict]
    benchmark_path: str
    collection_name: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict | None = None
