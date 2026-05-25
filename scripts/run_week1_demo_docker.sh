#!/usr/bin/env bash
# Week 1 demo when API runs in Docker (use upload, not host path).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${BASE_URL:-http://127.0.0.1:8000}"

echo "==> Health"
curl -s "${BASE}/api/v1/health" | python3 -m json.tool

echo "==> Ingest sample (upload)"
curl -s -X POST "${BASE}/api/v1/ingest/upload" \
  -F "file=@${ROOT}/data/sample/rag_overview.md" | python3 -m json.tool

echo "==> Retrieve"
curl -s -X POST "${BASE}/api/v1/retrieve" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is cosine similarity used for?"}' | python3 -m json.tool

echo "==> Query"
curl -s -X POST "${BASE}/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why do we use chunk overlap?"}' | python3 -m json.tool

echo "==> Qdrant health"
curl -s "${BASE}/api/v1/health/qdrant" | python3 -m json.tool
