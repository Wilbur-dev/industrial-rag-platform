from functools import lru_cache

from app.rag.pipeline import RAGPipeline


@lru_cache
def get_pipeline() -> RAGPipeline:
    return RAGPipeline()
