"""End-to-end RAG pipeline — Day 6."""

import time

import httpx

from app.config import get_settings
from app.logging_config import get_logger
from app.rag.chunking import chunk_document
from app.rag.embedding import EmbeddingService
from app.rag.ingestion import ingest_file, ingest_upload
from app.rag.models import Document, RetrievedChunk
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)


class RAGPipeline:
    def __init__(self, collection_name: str | None = None) -> None:
        self._embedder = EmbeddingService()
        self._store = VectorStore(collection_name=collection_name)
        self._store.ensure_collection(self._embedder.dimension)

    def index_document(self, doc: Document) -> dict:
        t0 = time.perf_counter()
        chunks = chunk_document(doc)
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

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        settings = get_settings()
        k = top_k or settings.top_k
        t0 = time.perf_counter()
        qvec = self._embedder.embed_query(query)
        results = self._store.search(qvec, k)
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "retrieval_complete",
            query_len=len(query),
            hits=len(results),
            latency_ms=round(latency_ms, 2),
        )
        return results

    def query(self, question: str, top_k: int | None = None) -> dict:
        """Retrieve context and produce a grounded answer."""
        t0 = time.perf_counter()
        chunks = self.retrieve(question, top_k)
        context = _format_context(chunks)
        answer, mode = _generate_answer(question, context, chunks)
        total_ms = (time.perf_counter() - t0) * 1000
        return {
            "question": question,
            "answer": answer,
            "generation_mode": mode,
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
            "latency_ms": round(total_ms, 2),
        }


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
) -> tuple[str, str]:
    settings = get_settings()
    if not chunks:
        return (
            "No relevant documents found. Please ingest documents first.",
            "no_context",
        )

    if settings.openai_api_key:
        return _openai_generate(question, context), "openai"

    # Grounded template without external LLM — still cites retrieval
    top = chunks[0]
    return (
        f"Based on retrieved context (top score={top.score:.3f}):\n\n"
        f"{top.text}\n\n"
        f"(Set OPENAI_API_KEY in .env for full LLM synthesis.)",
        "retrieval_only",
    )


def _openai_generate(question: str, context: str) -> str:
    settings = get_settings()
    system = (
        "Answer ONLY using the provided context. "
        "If the context is insufficient, say you don't know. "
        "Cite chunk numbers like [1], [2]."
    )
    user = f"Context:\n{context}\n\nQuestion: {question}"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
