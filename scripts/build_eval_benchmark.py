#!/usr/bin/env python3
"""Build retrieval_benchmark.json with relevant_chunk_ids from live Qdrant."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag.pipeline import RAGPipeline  # noqa: E402

QUERIES = [
    "What is RAG?",
    "Why do we use chunk overlap?",
    "How does hallucination control work?",
    "What distance metric does Qdrant use?",
]

BENCHMARK_PATH = ROOT / "data/eval/retrieval_benchmark.json"


def main() -> None:
    pipeline = RAGPipeline()
    items = []
    for q in QUERIES:
        hits = pipeline.retrieve(q, top_k=3)
        items.append(
            {
                "query": q,
                "relevant_chunk_ids": [h.chunk_id for h in hits[:2]],
                "notes": "Auto-generated from top-2 retrieval; refine manually for gold labels",
            }
        )
    BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BENCHMARK_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    print(f"Wrote {BENCHMARK_PATH} ({len(items)} queries)")


if __name__ == "__main__":
    main()
