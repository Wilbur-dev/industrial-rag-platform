#!/usr/bin/env bash
# Week 2 demo — prompts, experiments, evaluation (API must be running)
set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:8000/api/v1}"

echo "=== Prompt versions ==="
curl -s "${BASE}/prompts" | python3 -m json.tool

echo ""
echo "=== Ingest sample (if needed) ==="
curl -s -X POST "${BASE}/ingest/path?path=data/sample/rag_overview.md" | python3 -m json.tool || true

echo ""
echo "=== Query with grounding (v2_strict_citations) ==="
curl -s -X POST "${BASE}/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why do we use chunk overlap?", "prompt_version": "v2_strict_citations", "top_k": 3}' \
  | python3 -m json.tool

echo ""
echo "=== Retrieval experiment (top_k x threshold) ==="
curl -s -X POST "${BASE}/experiments/retrieval" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "top_k_values": [1, 3, 5], "score_thresholds": [null, 0.3]}' \
  | python3 -m json.tool

echo ""
echo "=== Evaluate retrieval (Hit@K / MRR) ==="
echo "Tip: run 'python scripts/build_eval_benchmark.py' after ingest to fill chunk ids"
curl -s -X POST "${BASE}/evaluate/retrieval" \
  -H "Content-Type: application/json" \
  -d '{"top_k": 10}' \
  | python3 -m json.tool

echo ""
echo "Done. Save screenshots for docs/week2_journal.md"
