#!/usr/bin/env python3
"""
Week 2 Day 3 — retrieval parameter experiments (terminal tables for screenshots).

- Part A: top_k × score_threshold on corpus_topk.md in topk_eval_collection (default documents_topk).
- Part B: chunk_size_sweep.md into {QDRANT_COLLECTION}_cs128/_cs256/_cs512.
- rag_overview.md stays in QDRANT_COLLECTION (documents) via normal API ingest — not mixed with Part A.

Requires Qdrant (e.g. docker compose up). Re-running skips ingest when source already exists
in the target collection.

Usage:
  python scripts/run_retrieval_experiments.py
  python scripts/run_retrieval_experiments.py --skip-ingest
  python scripts/run_retrieval_experiments.py --part topk
  python scripts/run_retrieval_experiments.py --part chunk
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.rag.chunking import chunk_document  # noqa: E402
from app.rag.ingestion import ingest_file  # noqa: E402
from app.rag.pipeline import RAGPipeline  # noqa: E402

SAMPLE_DIR = ROOT / "data" / "sample"
CORPUS_TOPK = SAMPLE_DIR / "corpus_topk.md"
CHUNK_SIZE_SWEEP = SAMPLE_DIR / "chunk_size_sweep.md"
CHUNK_SIZE_VALUES = [128, 256, 512]

TOPK_QUERY = "How should teams log hits and hits_after_threshold when tuning score threshold?"

CHUNK_SWEEP_QUERIES = [
    "What overlap policy does the chunk size sweep document use?",
    "How does smaller chunk_size affect precision versus fragmentation?",
    "What approximate chunk counts are listed for chunk_size 256?",
]

TOP_K_VALUES = [1, 3, 5, 10]
SCORE_THRESHOLDS: list[float | None] = [None, 0.3]
CHUNK_OVERLAP = 64
RETRIEVE_K = 5


def _collection_for_chunk_size(chunk_size: int) -> str:
    base = get_settings().qdrant_collection
    return f"{base}_cs{chunk_size}"


def _print_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells: list[str]) -> str:
        return " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    sep = "-+-".join("-" * w for w in widths)
    print()
    print(title)
    print(fmt_row(headers))
    print(sep)
    for row in rows:
        print(fmt_row(row))
    print()


def _th_label(th: float | None) -> str:
    return "none" if th is None else f"{th:.2f}"


def ensure_ingested(
    pipeline: RAGPipeline,
    path: Path,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int = CHUNK_OVERLAP,
    skip_ingest: bool,
) -> dict:
    source = path.name
    store = pipeline._store
    existing = store.count_by_source(source)

    if skip_ingest and existing == 0:
        print(
            f"  WARN: --skip-ingest but {source} not in "
            f"`{store.collection_name}` ({existing} points)"
        )
    elif existing > 0:
        print(
            f"  skip ingest: {source} already in `{store.collection_name}` "
            f"({existing} point(s))"
        )
        return {
            "source": source,
            "chunks_indexed": existing,
            "skipped": True,
            "chunk_size": chunk_size,
            "collection": store.collection_name,
        }

    if skip_ingest:
        return {
            "source": source,
            "chunks_indexed": 0,
            "skipped": True,
            "collection": store.collection_name,
        }

    doc = ingest_file(path)
    planned = len(
        chunk_document(
            doc,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    )
    result = pipeline.index_document(
        doc,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    result["planned_chunks"] = planned
    result["skipped"] = False
    result["collection"] = store.collection_name
    print(
        f"  ingested: {source} -> `{store.collection_name}` "
        f"{result['chunks_indexed']} chunks "
        f"(chunk_size={chunk_size}, planned={planned})"
    )
    return result


def run_topk_threshold_matrix(pipeline: RAGPipeline) -> None:
    result = pipeline.run_retrieval_experiment(
        TOPK_QUERY,
        top_k_values=TOP_K_VALUES,
        score_thresholds=SCORE_THRESHOLDS,
    )
    rows: list[list[str]] = []
    for run in result["runs"]:
        rows.append(
            [
                str(run["top_k"]),
                _th_label(run["score_threshold"]),
                str(run["hit_count"]),
                "" if run["top_score"] is None else f"{run['top_score']:.4f}",
                f"{run['latency_ms']:.1f}",
            ]
        )
    _print_table(
        f"Part A — top_k × score_threshold (collection: {pipeline._store.collection_name})",
        ["top_k", "threshold", "hit_count", "top_score", "latency_ms"],
        rows,
    )
    info = pipeline._store.collection_info()
    print(f"Collection `{info['name']}` points_count={info['points_count']}")


def run_chunk_size_comparison(skip_ingest: bool) -> None:
    if not CHUNK_SIZE_SWEEP.exists():
        sys.exit(f"Missing {CHUNK_SIZE_SWEEP}")

    rows: list[list[str]] = []
    for chunk_size in CHUNK_SIZE_VALUES:
        coll = _collection_for_chunk_size(chunk_size)
        pipeline = RAGPipeline(collection_name=coll)
        ensure_ingested(
            pipeline,
            CHUNK_SIZE_SWEEP,
            chunk_size=chunk_size,
            skip_ingest=skip_ingest,
        )
        points = pipeline._store.collection_info()["points_count"]

        for query in CHUNK_SWEEP_QUERIES:
            hits = pipeline.retrieve(query, top_k=RETRIEVE_K, score_threshold=None)
            top = hits[0].score if hits else None
            rows.append(
                [
                    str(chunk_size),
                    coll,
                    str(points),
                    str(len(hits)),
                    "" if top is None else f"{top:.4f}",
                    query[:52] + ("…" if len(query) > 52 else ""),
                ]
            )

    _print_table(
        "Part B — chunk_size (same document, isolated collections; fixed queries)",
        [
            "chunk_size",
            "collection",
            "points_count",
            f"hits@k={RETRIEVE_K}",
            "top_score",
            "query",
        ],
        rows,
    )
    settings = get_settings()
    print(
        f"`{settings.qdrant_collection}` (e.g. rag_overview.md) is untouched. "
        f"Part A uses `{settings.topk_eval_collection}`; Part B uses `_cs*` collections."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Week 2 Day 3 retrieval experiment tables")
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Do not ingest; only run retrieval tables (requires prior ingest)",
    )
    parser.add_argument(
        "--part",
        choices=("all", "topk", "chunk"),
        default="all",
        help="Which experiment section to run",
    )
    args = parser.parse_args()

    if not CORPUS_TOPK.exists():
        sys.exit(f"Missing {CORPUS_TOPK}")

    settings = get_settings()
    print("Week 2 Day 3 — retrieval experiments")
    print(
        f"Part A: {CORPUS_TOPK.name} -> `{settings.topk_eval_collection}` "
        f"(overview uses `{settings.qdrant_collection}` only)"
    )
    print(
        f"Part B: {CHUNK_SIZE_SWEEP.name} -> "
        f"`{settings.qdrant_collection}_cs{{128,256,512}}`"
    )

    if args.part in ("all", "topk"):
        print("\n--- Part A ---")
        topk_pipeline = RAGPipeline(collection_name=settings.topk_eval_collection)
        ensure_ingested(topk_pipeline, CORPUS_TOPK, skip_ingest=args.skip_ingest)
        run_topk_threshold_matrix(topk_pipeline)

    if args.part in ("all", "chunk"):
        print("\n--- Part B ---")
        run_chunk_size_comparison(skip_ingest=args.skip_ingest)

    print("\nDone.")


if __name__ == "__main__":
    main()
