from evaluation.metrics import (
    aggregate_metrics,
    hit_at_k,
    mean_reciprocal_rank,
    recall_at_k,
    reciprocal_rank,
)


def test_hit_at_k():
    assert hit_at_k({"a", "b"}, ["x", "a", "y"], k=3) == 1.0
    assert hit_at_k({"a"}, ["x", "y"], k=2) == 0.0


def test_recall_at_k():
    assert recall_at_k({"a", "b"}, ["a", "x", "b"], k=3) == 1.0
    assert recall_at_k({"a", "b"}, ["a"], k=1) == 0.5


def test_mrr():
    assert reciprocal_rank({"b"}, ["a", "b", "c"]) == 0.5
    assert reciprocal_rank({"z"}, ["a", "b"]) == 0.0
    assert mean_reciprocal_rank([({"a"}, ["a"]), ({"b"}, ["x", "b"])]) == 0.75


def test_aggregate_metrics():
    queries = [
        ({"c1"}, ["c1", "x"]),
        ({"c2"}, ["x", "c2"]),
    ]
    m = aggregate_metrics(queries, [1, 3])
    assert m["hit@1"] == 0.5
    assert m["mrr"] == 0.75
    assert m["num_queries"] == 2.0
