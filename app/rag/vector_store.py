"""Qdrant vector store — Day 5."""

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import get_settings
from app.logging_config import get_logger
from app.rag.models import Chunk, RetrievedChunk

logger = get_logger(__name__)


class VectorStore:
    def __init__(self, collection_name: str | None = None) -> None:
        settings = get_settings()
        self._collection = collection_name or settings.qdrant_collection
        self._client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )

    @property
    def collection_name(self) -> str:
        return self._collection

    def ensure_collection(self, vector_size: int) -> None:
        exists = self._client.collection_exists(self._collection)
        if not exists:
            logger.info("creating_qdrant_collection", collection=self._collection)
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> int:
        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append(
                qmodels.PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "doc_id": chunk.doc_id,
                        "text": chunk.text,
                        "index": chunk.index,
                        **chunk.metadata,
                    },
                )
            )
        self._client.upsert(collection_name=self._collection, points=points)
        return len(points)

    def search(
        self,
        query_vector: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        # qdrant-client >=1.14 removed .search(); use query_points (1.18+) or legacy search.
        if hasattr(self._client, "search"):
            hits = self._client.search(
                collection_name=self._collection,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )
        else:
            response = self._client.query_points(
                collection_name=self._collection,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )
            hits = response.points
        results: list[RetrievedChunk] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                RetrievedChunk(
                    chunk_id=str(payload.get("chunk_id", hit.id)),
                    text=str(payload.get("text", "")),
                    score=float(hit.score),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k not in {"text", "chunk_id"}
                    },
                )
            )
        return results

    def count_by_source(self, source: str) -> int:
        """Count indexed points whose payload source matches (for idempotent ingest)."""
        result = self._client.count(
            collection_name=self._collection,
            count_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="source",
                        match=qmodels.MatchValue(value=source),
                    )
                ]
            ),
            exact=True,
        )
        return int(result.count)

    def collection_info(self) -> dict:
        info = self._client.get_collection(self._collection)
        return {
            "name": self._collection,
            "points_count": info.points_count,
            "status": str(info.status),
        }
