"""API routes — health, ingest, retrieve, query."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_pipeline
from app.api.schemas import (
    HealthResponse,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
)
from app.config import get_settings
from app.rag.pipeline import RAGPipeline
from app.rag.vector_store import VectorStore

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_env=settings.app_env,
    )


@router.get("/health/qdrant")
def health_qdrant() -> dict:
    try:
        store = VectorStore()
        settings = get_settings()
        if not store._client.collection_exists(settings.qdrant_collection):
            return {"qdrant": "up", "collection": "not_created_yet"}
        return {"qdrant": "up", **store.collection_info()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Qdrant unavailable: {exc}") from exc


@router.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> IngestResponse:
    data = await file.read()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    try:
        result = pipeline.index_upload(file.filename, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IngestResponse(**result)


@router.post("/ingest/path", response_model=IngestResponse)
def ingest_path(
    path: str,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> IngestResponse:
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        result = pipeline.index_file(p)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IngestResponse(**result)


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(
    body: RetrieveRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> RetrieveResponse:
    hits = pipeline.retrieve(body.query, body.top_k)
    return RetrieveResponse(
        query=body.query,
        hits=[
            RetrieveHit(
                chunk_id=h.chunk_id,
                text=h.text,
                score=h.score,
                metadata=h.metadata,
            )
            for h in hits
        ],
        count=len(hits),
    )


@router.post("/query", response_model=QueryResponse)
def query(
    body: QueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> QueryResponse:
    result = pipeline.query(body.question, body.top_k)
    return QueryResponse(**result)
