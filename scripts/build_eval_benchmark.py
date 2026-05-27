#!/usr/bin/env python3
"""
Build or preview retrieval_benchmark.json labels from documents_topk.

Auto top-2 labels are a starting point only — many queries need manual gold chunk_ids
(e.g. 'threshold cliff' vs chunks that only mention 'threshold').
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.rag.pipeline import RAGPipeline  # noqa: E402

QUERIES = [
    "Why should teams log both hits and hits_after_threshold?",
    "What does top_k control in the retrieval pipeline?",
    "What failure mode is called a threshold cliff?",
    "How do operators sweep score_threshold after a new embedding model?",
]

BENCHMARK_PATH = ROOT / "data" / "eval" / "retrieval_benchmark.json"
CORPUS_SOURCE = "corpus_topk.md"


def _preview(pipeline: RAGPipeline, top_k: int) -> None:
    print(f"\nPreview top-{top_k} hits (verify text before trusting labels):\n")
    for q in QUERIES:
        print(f"Q: {q}")
        hits = pipeline.retrieve(q, top_k=top_k)
        if not hits:
            print("  (no hits)\n")
            continue
        for i, h in enumerate(hits, 1):
            snippet = h.text.replace("\n", " ")[:100]
            print(f"  {i}. {h.chunk_id}  score={h.score:.4f}")
            print(f"     {snippet}...")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build retrieval benchmark labels")
    parser.add_argument(
        "--benchmark-path",
        type=Path,
        default=BENCHMARK_PATH,
        help="Output JSON path",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Retrieve this many hits for preview / auto label",
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Print top-k snippets for manual labeling; do not write JSON",
    )
    parser.add_argument(
        "--auto-write",
        action="store_true",
        help="Write JSON using top-2 ids (not recommended without manual review)",
    )
    args = parser.parse_args()

    settings = get_settings()
    collection = settings.topk_eval_collection
    pipeline = RAGPipeline(collection_name=collection)

    if pipeline._store.count_by_source(CORPUS_SOURCE) == 0:
        print(
            f"ERROR: `{CORPUS_SOURCE}` not found in collection `{collection}`.\n"
            f"Run: python scripts/run_retrieval_experiments.py --part topk",
            file=sys.stderr,
        )
        sys.exit(1)

    _preview(pipeline, args.top_k)

    if args.preview_only:
        print(
            "Edit data/eval/retrieval_benchmark.json by hand, then run evaluate.\n"
            "Do not use --auto-write for production-like labels."
        )
        return

    if not args.auto_write:
        print(
            "No file written. Use --auto-write to overwrite with top-2 auto labels,\n"
            "or edit retrieval_benchmark.json manually after reviewing preview above."
        )
        return

    items = []
    for q in QUERIES:
        hits = pipeline.retrieve(q, top_k=args.top_k)
        items.append(
            {
                "query": q,
                "relevant_chunk_ids": [h.chunk_id for h in hits[:2]],
                "notes": f"AUTO top-2 from `{collection}` — manual review required",
            }
        )

    args.benchmark_path.parent.mkdir(parents=True, exist_ok=True)
    with args.benchmark_path.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    print(f"Wrote {args.benchmark_path} (auto top-2). Review and fix relevant_chunk_ids.")


if __name__ == "__main__":
    main()
