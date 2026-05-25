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


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Citation(BaseModel):
    chunk_id: str
    score: float
    source: str
    excerpt: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    generation_mode: str
    citations: list[Citation]
    retrieval_count: int
    latency_ms: float


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class RetrieveHit(BaseModel):
    chunk_id: str
    text: str
    score: float
    metadata: dict


class RetrieveResponse(BaseModel):
    query: str
    hits: list[RetrieveHit]
    count: int
