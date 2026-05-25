# Week 2 Learning Journal — Retrieval Quality & Evaluation

> 按 PDF 要求：每天写代码、做实验、保存截图。截图建议放在 `evidence/screenshots/week2/`。

## Day 1 — Prompt Builder + versioning

| 项目 | 记录 |
|------|------|
| 完成内容 | `app/rag/prompts.py`，`GET /api/v1/prompts`，`query` 支持 `prompt_version` |
| 理解 | Prompt 是线上逻辑，版本化便于 A/B 与回滚 |
| 截图 | `day2-prompts-list.png` |

## Day 2 — Citation + hallucination control

| 项目 | 记录 |
|------|------|
| 完成内容 | `app/rag/grounding.py`，`QueryResponse.grounding` |
| 实验 | 无文档 query 是否 `is_refusal=true` |
| 截图 | `day2-grounding-report.png` |

## Day 3 — top-k / chunk_size / threshold 实验

| 项目 | 记录 |
|------|------|
| 完成内容 | `POST /api/v1/experiments/retrieval`，`score_threshold` on retrieve/query |
| 实验 | 对比 top_k=1,3,5 与 threshold=0.3 |
| 截图 | `day3-experiment-matrix.png` |

## Day 4 — Hit@K / Recall@K / MRR

| 项目 | 记录 |
|------|------|
| 完成内容 | `evaluation/metrics.py`，`POST /api/v1/evaluate/retrieval` |
| 命令 | `python scripts/build_eval_benchmark.py` 后调用 evaluate |
| 截图 | `day4-eval-metrics.png` |

## Day 5 — Structured error handling

| 项目 | 记录 |
|------|------|
| 完成内容 | `app/exceptions.py`，`app/api/error_handlers.py` |
| 验证 | `ingest/path` 404 返回 `error_code: not_found` |
| 截图 | `day5-error-json.png` |

## Day 6 — Unit tests + API tests

| 项目 | 记录 |
|------|------|
| 命令 | `pytest tests/ -v` |
| 新增 | `test_metrics`, `test_prompts`, `test_grounding`, `test_api_week2` |
| 截图 | `day6-pytest-green.png` |

## Day 7 — Retrieval design report

| 项目 | 记录 |
|------|------|
| 交付 | `docs/retrieval_design_report.md` |
| 面试自测 | 见 README Week 2 追问 |
