"""Run retrieval evaluation against a labeled dataset — Week 2 Day 4."""

import json
from pathlib import Path
from typing import Callable

from evaluation.metrics import aggregate_metrics
from app.exceptions import EvaluationError


def load_benchmark(path: Path) -> list[dict]:
    if not path.exists():
        raise EvaluationError(f"Benchmark file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise EvaluationError("Benchmark must be a JSON array of query objects")
    return data


def run_retrieval_evaluation(
    benchmark: list[dict],
    retrieve_fn: Callable[[str, int], list],
    *,
    k_values: list[int] | None = None,
    default_top_k: int = 10,
) -> dict:
    """
    Each benchmark item:
      {"query": "...", "relevant_chunk_ids": ["id1", ...]}
    retrieve_fn(query, top_k) -> list of objects with .chunk_id
    """
    k_values = k_values or [1, 3, 5]
    max_k = max(max(k_values), default_top_k)
    pairs: list[tuple[set[str], list[str]]] = []
    per_query: list[dict] = []

    for item in benchmark:
        query = item.get("query")
        relevant = set(item.get("relevant_chunk_ids") or [])
        if not query:
            raise EvaluationError("Benchmark item missing 'query'")
        hits = retrieve_fn(query, max_k)
        retrieved_ids = [h.chunk_id for h in hits]
        pairs.append((relevant, retrieved_ids))
        per_query.append(
            {
                "query": query,
                "relevant_count": len(relevant),
                "retrieved_top_ids": retrieved_ids[: max(k_values)],
                "hit@1": relevant & set(retrieved_ids[:1]) != set() if relevant else False,
            }
        )

    metrics = aggregate_metrics(pairs, k_values)
    return {
        "metrics": metrics,
        "per_query": per_query,
        "k_values": k_values,
    }
