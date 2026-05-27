"""End-to-end RAG pipeline — Week 1 + Week 2 retrieval quality."""

import time

import httpx

from app.config import get_settings
from app.exceptions import GenerationError, RetrievalError
from app.logging_config import get_logger
from app.rag.chunking import chunk_document
from app.rag.embedding import EmbeddingService
from app.rag.grounding import assess_grounding, filter_by_score_threshold
from app.rag.ingestion import ingest_file, ingest_upload
from app.rag.models import Document, RetrievedChunk
from app.rag.prompts import PromptBuilder
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)


class RAGPipeline:
    def __init__(self, collection_name: str | None = None) -> None:
        self._embedder = EmbeddingService()
        self._store = VectorStore(collection_name=collection_name)
        self._store.ensure_collection(self._embedder.dimension)

    def index_document(
        self,
        doc: Document,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> dict:
        t0 = time.perf_counter()
        chunks = chunk_document(
            doc,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        if not chunks:
            return {"doc_id": doc.doc_id, "chunks_indexed": 0, "latency_ms": 0}

        vectors = self._embedder.embed_texts([c.text for c in chunks])
        count = self._store.upsert_chunks(chunks, vectors)
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "document_indexed",
            doc_id=doc.doc_id,
            source=doc.source,
            chunks=count,
            latency_ms=round(latency_ms, 2),
        )
        return {
            "doc_id": doc.doc_id,
            "source": doc.source,
            "chunks_indexed": count,
            "latency_ms": round(latency_ms, 2),
        }

    def index_file(self, path) -> dict:
        doc = ingest_file(path)
        return self.index_document(doc)

    def index_upload(self, filename: str, data: bytes) -> dict:
        doc = ingest_upload(filename, data)
        return self.index_document(doc)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        *,
        score_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        settings = get_settings()
        k = top_k or settings.top_k
        threshold = (
            score_threshold
            if score_threshold is not None
            else settings.score_threshold
        )
        t0 = time.perf_counter()
        try:
            qvec = self._embedder.embed_query(query)
            results = self._store.search(qvec, k)
        except Exception as exc:
            raise RetrievalError(
                "Vector search failed",
                details={"query_len": len(query), "error": str(exc)},
            ) from exc

        filtered = filter_by_score_threshold(results, threshold)
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "retrieval_complete",
            query_len=len(query),
            hits=len(results),
            hits_after_threshold=len(filtered),
            score_threshold=threshold,
            latency_ms=round(latency_ms, 2),
        )
        return filtered

    def query(
        self,
        question: str,
        top_k: int | None = None,
        *,
        score_threshold: float | None = None,
        prompt_version: str | None = None,
    ) -> dict:
        """Retrieve context and produce a grounded answer with quality signals."""
        settings = get_settings()
        t0 = time.perf_counter()
        chunks = self.retrieve(
            question,
            top_k,
            score_threshold=score_threshold,
        )
        context = _format_context(chunks)
        version = prompt_version or settings.prompt_version
        answer, mode = _generate_answer(question, context, chunks, version)
        grounding = assess_grounding(
            answer,
            chunks,
            min_top_score=settings.min_grounding_score,
        )
        total_ms = (time.perf_counter() - t0) * 1000
        return {
            "question": question,
            "answer": answer,
            "generation_mode": mode,
            "prompt_version": version,
            "citations": [
                {
                    "chunk_id": c.chunk_id,
                    "score": round(c.score, 4),
                    "source": c.metadata.get("source", "unknown"),
                    "excerpt": c.text[:200] + ("..." if len(c.text) > 200 else ""),
                }
                for c in chunks
            ],
            "retrieval_count": len(chunks),
            "grounding": grounding,
            "latency_ms": round(total_ms, 2),
        }

    def run_retrieval_experiment(
        self,
        query: str,
        *,
        top_k_values: list[int] | None = None,
        score_thresholds: list[float | None] | None = None,
    ) -> dict:
        """Compare retrieval under different top_k and score thresholds."""
        settings = get_settings()
        k_list = top_k_values or [1, 3, 5, settings.top_k]
        thresholds = score_thresholds or [None, 0.3, 0.5]
        runs = []
        for k in k_list:
            for th in thresholds:
                t0 = time.perf_counter()
                hits = self.retrieve(query, k, score_threshold=th)
                runs.append(
                    {
                        "top_k": k,
                        "score_threshold": th,
                        "hit_count": len(hits),
                        "top_score": round(hits[0].score, 4) if hits else None,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                    }
                )
        return {"query": query, "runs": runs}


def _format_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        src = c.metadata.get("source", "doc")
        parts.append(f"[{i}] (source={src}, score={c.score:.3f})\n{c.text}")
    return "\n\n".join(parts)


def _generate_answer(
    question: str,
    context: str,
    chunks: list[RetrievedChunk],
    prompt_version: str,
) -> tuple[str, str]:
    settings = get_settings()
    if not chunks:
        return (
            "I don't have enough information in the knowledge base to answer this question.",
            "no_context",
        )

    if settings.openai_api_key:
        try:
            return _openai_generate(question, context, prompt_version), "openai"
        except httpx.HTTPError as exc:
            raise GenerationError(
                "LLM generation failed",
                details={"provider": "openai", "error": str(exc)},
            ) from exc

    top = chunks[0]
    return (
        f"Based on retrieved context [1] (score={top.score:.3f}):\n\n"
        f"{top.text}\n\n"
        f"(Set OPENAI_API_KEY in .env for full LLM synthesis with prompt {prompt_version}.)",
        "retrieval_only",
    )


def _openai_generate(
    question: str,
    context: str,
    prompt_version: str,
) -> str:
    settings = get_settings()
    builder = PromptBuilder(prompt_version)
    messages = builder.build_messages(question, context)
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "messages": messages,
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
