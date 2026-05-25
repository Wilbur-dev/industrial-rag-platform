"""Citation validation and hallucination control — Week 2 Day 2."""

import re

from app.rag.models import RetrievedChunk

_CITATION_RE = re.compile(r"\[(\d+)\]")
_REFUSAL_PHRASES = (
    "don't know",
    "do not know",
    "cannot answer",
    "can't answer",
    "not enough information",
    "no relevant",
    "insufficient context",
    "no context",
)


def extract_citation_indices(answer: str) -> list[int]:
    return [int(m) for m in _CITATION_RE.findall(answer)]


def validate_citations(
    answer: str,
    chunk_count: int,
) -> dict:
    """Check that cited indices refer to retrieved chunks."""
    cited = extract_citation_indices(answer)
    if not cited:
        return {
            "valid": chunk_count == 0,
            "cited_indices": [],
            "invalid_indices": [],
            "has_citations": False,
        }
    invalid = [i for i in cited if i < 1 or i > chunk_count]
    return {
        "valid": len(invalid) == 0,
        "cited_indices": cited,
        "invalid_indices": invalid,
        "has_citations": True,
    }


def is_refusal_answer(answer: str) -> bool:
    lower = answer.lower()
    return any(phrase in lower for phrase in _REFUSAL_PHRASES)


def filter_by_score_threshold(
    chunks: list[RetrievedChunk],
    threshold: float | None,
) -> list[RetrievedChunk]:
    if threshold is None:
        return chunks
    return [c for c in chunks if c.score >= threshold]


def assess_grounding(
    answer: str,
    chunks: list[RetrievedChunk],
    *,
    min_top_score: float = 0.0,
) -> dict:
    """
    Post-generation grounding check for production guardrails.
    """
    if not chunks:
        return {
            "grounded": is_refusal_answer(answer),
            "reason": "no_retrieval",
            "citation_check": validate_citations(answer, 0),
            "top_score": 0.0,
        }

    top_score = max(c.score for c in chunks)
    citation_check = validate_citations(answer, len(chunks))
    refusal = is_refusal_answer(answer)

    if top_score < min_top_score:
        grounded = refusal
        reason = "low_retrieval_confidence"
    elif not citation_check["has_citations"] and not refusal:
        grounded = False
        reason = "missing_citations"
    elif citation_check["invalid_indices"]:
        grounded = False
        reason = "invalid_citation_index"
    else:
        grounded = True
        reason = "ok" if citation_check["has_citations"] or refusal else "weak_citations"

    return {
        "grounded": grounded,
        "reason": reason,
        "citation_check": citation_check,
        "top_score": round(top_score, 4),
        "is_refusal": refusal,
    }
