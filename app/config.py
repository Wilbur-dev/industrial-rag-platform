"""Centralized configuration — Day 1."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "industrial-rag-platform"
    app_env: str = "development"
    log_level: str = "INFO"

    chunk_size: int = 512
    chunk_overlap: int = 64
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    top_k: int = 5
    score_threshold: float | None = None
    min_grounding_score: float = 0.0
    prompt_version: str = "v1_grounded"
    eval_k_values: str = "1,3,5"
    eval_benchmark_path: str = "data/eval/retrieval_benchmark.json"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def eval_k_list(self) -> list[int]:
        return [int(x.strip()) for x in self.eval_k_values.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
