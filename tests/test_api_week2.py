from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.deps import get_pipeline
from app.main import app

client = TestClient(app)


def _override_pipeline(mock_pipe: MagicMock):
    app.dependency_overrides[get_pipeline] = lambda: mock_pipe


def _clear_overrides():
    app.dependency_overrides.clear()


def test_list_prompts():
    resp = client.get("/api/v1/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert any(p["version"] == "v1_grounded" for p in data)


def test_query_no_context_grounding():
    pipe = MagicMock()
    pipe.query.return_value = {
        "question": "unknown?",
        "answer": "I don't have enough information in the knowledge base.",
        "generation_mode": "no_context",
        "prompt_version": "v1_grounded",
        "citations": [],
        "retrieval_count": 0,
        "grounding": {
            "grounded": True,
            "reason": "no_retrieval",
            "top_score": 0.0,
            "is_refusal": True,
        },
        "latency_ms": 1.0,
    }
    _override_pipeline(pipe)
    try:
        resp = client.post(
            "/api/v1/query",
            json={"question": "What is quantum gravity?"},
        )
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounding"]["is_refusal"] is True
    assert body["retrieval_count"] == 0


def test_structured_error_not_found():
    resp = client.post("/api/v1/ingest/path?path=/nonexistent/file.md")
    assert resp.status_code == 404
    data = resp.json()
    assert data["error_code"] == "not_found"


def test_retrieval_experiment_endpoint():
    pipe = MagicMock()
    pipe.run_retrieval_experiment.return_value = {
        "query": "RAG?",
        "runs": [
            {
                "top_k": 3,
                "score_threshold": None,
                "hit_count": 2,
                "top_score": 0.81,
                "latency_ms": 12.0,
            }
        ],
    }
    _override_pipeline(pipe)
    try:
        resp = client.post(
            "/api/v1/experiments/retrieval",
            json={"query": "What is RAG?"},
        )
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    assert resp.json()["runs"][0]["hit_count"] == 2
