#!/usr/bin/env bash
# Week 1 end-to-end demo — run after: docker compose up -d && pip install -r requirements.txt
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Health"
curl -s "http://127.0.0.1:8000/api/v1/health" | python3 -m json.tool

echo "==> Ingest sample markdown"
# Relative path avoids URL-encoding issues when ROOT contains spaces (e.g. "liweihao 1").
# Requires API started from project root (same as: cd "$ROOT" && uvicorn ...).
curl -s -X POST "http://127.0.0.1:8000/api/v1/ingest/path?path=data/sample/rag_overview.md" | python3 -m json.tool

echo "==> Retrieve"
curl -s -X POST "http://127.0.0.1:8000/api/v1/retrieve" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is cosine similarity used for?"}' | python3 -m json.tool

echo "==> Query (grounded)"
curl -s -X POST "http://127.0.0.1:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why do we use chunk overlap?"}' | python3 -m json.tool

echo "==> Qdrant health"
curl -s "http://127.0.0.1:8000/api/v1/health/qdrant" | python3 -m json.tool
