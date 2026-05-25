"""Embedding model with batch inference — Day 4."""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import get_settings
from app.logging_config import get_logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = get_logger(__name__)


@lru_cache
def _load_model(model_name: str) -> "SentenceTransformer":
    import torch
    from sentence_transformers import SentenceTransformer

    logger.info("loading_embedding_model", model=model_name)
    model = SentenceTransformer(model_name)
    model.eval()
    return model


class EmbeddingService:
    def __init__(self) -> None:
        settings = get_settings()
        self._model_name = settings.embedding_model
        self._batch_size = settings.embedding_batch_size
        self._model = _load_model(self._model_name)

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        import torch

        if not texts:
            return []
        all_vectors: list[list[float]] = []
        with torch.no_grad():
            for i in range(0, len(texts), self._batch_size):
                batch = texts[i : i + self._batch_size]
                vectors = self._model.encode(
                    batch,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
                all_vectors.extend(vectors.tolist())
        return all_vectors

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
