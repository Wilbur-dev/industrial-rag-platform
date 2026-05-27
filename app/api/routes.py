"""API routes — health, ingest, retrieve, query, evaluation (Week 2)."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_pipeline
from app.api.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    ExperimentRequest,
    ExperimentResponse,
    ExperimentRun,
    GroundingReport,
    HealthResponse,
    IngestResponse,
    PromptVersionInfo,
    QueryRequest,
    QueryResponse,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
)
from app.config import get_settings
from app.exceptions import IngestionError, NotFoundError, RetrievalError
from app.rag.pipeline import RAGPipeline
from app.rag.prompts import PromptBuilder
from app.rag.vector_store import VectorStore
from evaluation.runner import load_benchmark, run_retrieval_evaluation

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
        raise RetrievalError(
            "Qdrant unavailable",
            details={"error": str(exc)},
        ) from exc


@router.get("/prompts", response_model=list[PromptVersionInfo])
def list_prompts() -> list[PromptVersionInfo]:
    return [PromptVersionInfo(**v) for v in PromptBuilder.list_versions()]


@router.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> IngestResponse:
    data = await file.read()
    if not file.filename:
        raise IngestionError("Missing filename")
    try:
        result = pipeline.index_upload(file.filename, data)
    except ValueError as exc:
        raise IngestionError(str(exc)) from exc
    return IngestResponse(**result)


@router.post("/ingest/path", response_model=IngestResponse)
def ingest_path(
    path: str,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> IngestResponse:
    p = Path(path)
    if not p.exists():
        raise NotFoundError(f"File not found: {path}")
    try:
        result = pipeline.index_file(p)
    except ValueError as exc:
        raise IngestionError(str(exc)) from exc
    return IngestResponse(**result)


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(
    body: RetrieveRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> RetrieveResponse:
    hits = pipeline.retrieve(
        body.query,
        body.top_k,
        score_threshold=body.score_threshold,
    )
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
    result = pipeline.query(
        body.question,
        body.top_k,
        score_threshold=body.score_threshold,
        prompt_version=body.prompt_version,
    )
    g = result.pop("grounding")
    return QueryResponse(
        **result,
        grounding=GroundingReport(
            grounded=g["grounded"],
            reason=g["reason"],
            top_score=g["top_score"],
            is_refusal=g["is_refusal"],
        ),
    )


@router.post("/experiments/retrieval", response_model=ExperimentResponse)
def retrieval_experiment(
    body: ExperimentRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> ExperimentResponse:
    result = pipeline.run_retrieval_experiment(
        body.query,
        top_k_values=body.top_k_values,
        score_thresholds=body.score_thresholds,
    )
    return ExperimentResponse(
        query=result["query"],
        runs=[ExperimentRun(**r) for r in result["runs"]],
    )


@router.post("/evaluate/retrieval", response_model=EvaluateResponse)
def evaluate_retrieval(
    body: EvaluateRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> EvaluateResponse:
    settings = get_settings()
    bench_path = Path(body.benchmark_path or settings.eval_benchmark_path)
    benchmark = load_benchmark(bench_path)
    k_values = body.k_values or settings.eval_k_list
    collection = body.collection_name or settings.topk_eval_collection
    eval_pipeline = (
        pipeline
        if pipeline._store.collection_name == collection
        else RAGPipeline(collection_name=collection)
    )

    def retrieve_fn(q: str, k: int):
        return eval_pipeline.retrieve(q, k)

    report = run_retrieval_evaluation(
        benchmark,
        retrieve_fn,
        k_values=k_values,
        default_top_k=body.top_k,
    )
    return EvaluateResponse(
        metrics=report["metrics"],
        k_values=report["k_values"],
        per_query=report["per_query"],
        benchmark_path=str(bench_path),
        collection_name=collection,
    )
