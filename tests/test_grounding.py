from app.rag.grounding import (
    assess_grounding,
    extract_citation_indices,
    filter_by_score_threshold,
    is_refusal_answer,
    validate_citations,
)
from app.rag.models import RetrievedChunk


def test_extract_citations():
    assert extract_citation_indices("Fact [1] and [2].") == [1, 2]


def test_validate_citations_invalid_index():
    result = validate_citations("See [9]", chunk_count=2)
    assert result["valid"] is False
    assert 9 in result["invalid_indices"]


def test_filter_by_threshold():
    chunks = [
        RetrievedChunk("a", "text", 0.9, {}),
        RetrievedChunk("b", "text", 0.2, {}),
    ]
    filtered = filter_by_score_threshold(chunks, 0.5)
    assert len(filtered) == 1
    assert filtered[0].chunk_id == "a"


def test_refusal_detection():
    assert is_refusal_answer("I don't know based on context.")
    assert not is_refusal_answer("RAG combines retrieval [1].")


def test_assess_grounding_no_chunks():
    g = assess_grounding("I don't know.", [])
    assert g["reason"] == "no_retrieval"
    assert g["is_refusal"] is True
    assert g["grounded"] is True


def test_assess_grounding_no_chunks_pipeline_refusal():
    answer = (
        "I don't have enough information in the knowledge base to answer this question."
    )
    g = assess_grounding(answer, [])
    assert g["is_refusal"] is True
    assert g["grounded"] is True
