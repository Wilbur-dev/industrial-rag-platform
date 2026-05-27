"""Retrieval evaluation metrics — Week 2 Day 4."""

from typing import Sequence


def hit_at_k(relevant_ids: set[str], retrieved_ids: Sequence[str], k: int) -> float:
    """1.0 if any relevant doc appears in top-k, else 0.0."""
    if not relevant_ids:
        return 0.0
    top = retrieved_ids[:k]
    return 1.0 if any(rid in relevant_ids for rid in top) else 0.0


def recall_at_k(relevant_ids: set[str], retrieved_ids: Sequence[str], k: int) -> float:
    """Fraction of relevant ids found in top-k."""
    if not relevant_ids:
        return 0.0
    top = set(retrieved_ids[:k])
    return len(relevant_ids & top) / len(relevant_ids)


def reciprocal_rank(relevant_ids: set[str], retrieved_ids: Sequence[str]) -> float:
    """MRR component for one query: 1/rank of first relevant hit, else 0."""
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(
    queries: list[tuple[set[str], list[str]]],
) -> float:
    if not queries:
        return 0.0
    scores = [reciprocal_rank(rel, ret) for rel, ret in queries]
    return sum(scores) / len(scores)


def aggregate_metrics(
    queries: list[tuple[set[str], list[str]]],
    k_values: list[int],
) -> dict[str, float]:
    if not queries:
        return {f"hit@{k}": 0.0 for k in k_values} | {
            f"recall@{k}": 0.0 for k in k_values
        } | {"mrr": 0.0, "num_queries": 0}

    result: dict[str, float] = {"num_queries": float(len(queries))}
    for k in k_values:
        hits = [hit_at_k(rel, ret, k) for rel, ret in queries]
        recalls = [recall_at_k(rel, ret, k) for rel, ret in queries]
        result[f"hit@{k}"] = round(sum(hits) / len(hits), 4)
        result[f"recall@{k}"] = round(sum(recalls) / len(recalls), 4)
    result["mrr"] = round(mean_reciprocal_rank(queries), 4)
    return result
