# Industrial RAG Platform — Week 1 + Week 2

Production-grade RAG foundation + **retrieval quality & evaluation**，对应 `Full_Industrial_RAG_LLM_Execution_Guide.pdf` 第一周与第二周。

## Week 2 新增能力

| Day | 功能 | API / 模块 |
|-----|------|------------|
| 1 | Prompt Builder + 版本化 | `GET /api/v1/prompts`，`prompt_version` on query |
| 2 | Citation + 幻觉控制 | `app/rag/grounding.py`，`grounding` in query response |
| 3 | top-k / score_threshold 实验 | `POST /api/v1/experiments/retrieval` |
| 4 | Hit@K / Recall@K / MRR | `POST /api/v1/evaluate/retrieval`，`evaluation/` |
| 5 | 结构化错误 | `app/exceptions.py`，`error_code` JSON |
| 6 | 单元测试 + API 测试 | `tests/test_*week2*` |
| 7 | 检索设计报告 | `docs/retrieval_design_report.md`，`docs/week2_journal.md` |

## Week 1 能力（保留）

| Day | 功能 | API / 模块 |
|-----|------|------------|
| 1 | FastAPI 骨架、配置、日志、健康检查 | `GET /api/v1/health` |
| 2 | PDF / Markdown 入库 | `POST /api/v1/ingest/upload` |
| 3 | 分块（size + overlap） | `app/rag/chunking.py` |
| 4 | Embedding（batch + no_grad） | `app/rag/embedding.py` |
| 5 | Qdrant 向量库 | `docker compose` + `health/qdrant` |
| 6 | 检索 + grounded 回答 + 引用 | `POST /api/v1/query` |
| 7 | 文档与架构图 | `docs/`, `docs/week1_journal.md` |

## 快速开始

### Docker（推荐）

```bash
cd "/Users/liweihao 1/Downloads/recent_occupation/llm/industrial-rag-platform"
docker compose up -d --build
```

API 文档：http://127.0.0.1:8000/docs  
详见 [docs/docker.md](docs/docker.md)。混合开发（仅 Qdrant 在 Docker、API 本机热重载）：`docker compose -f docker-compose.dev.yml up -d`。

### Week 2 演示流程

```bash
# 入库
curl -X POST "http://127.0.0.1:8000/api/v1/ingest/upload" \
  -F "file=@data/sample/rag_overview.md"

# 带 grounding 的问答
curl -X POST "http://127.0.0.1:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why do we use chunk overlap?", "prompt_version": "v2_strict_citations"}'

# Day 3–4：corpus_topk 进 documents_topk（与 rag_overview 的 documents 分离）
python scripts/run_retrieval_experiments.py --part topk
python scripts/build_eval_benchmark.py
curl -X POST "http://127.0.0.1:8000/api/v1/evaluate/retrieval" \
  -H "Content-Type: application/json" \
  -d '{"top_k": 10}'

# 或一键脚本
chmod +x scripts/run_week2_demo.sh
./scripts/run_week2_demo.sh
```

### 本机 Python

```bash
source .venv/bin/activate
pip install -r requirements.txt
docker compose -f docker-compose.dev.yml up -d
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pytest tests/ -v
```

### 环境变量（Week 2）

```bash
PROMPT_VERSION=v1_grounded          # v1_grounded | v2_strict_citations | v3_refusal_aware
SCORE_THRESHOLD=                    # 可选，过滤低分 chunk
MIN_GROUNDING_SCORE=0.0
EVAL_K_VALUES=1,3,5
EVAL_BENCHMARK_PATH=data/eval/retrieval_benchmark.json
```

## 项目结构

```
industrial-rag-platform/
├── app/
│   ├── rag/prompts.py       # Week 2 prompts
│   ├── rag/grounding.py     # Week 2 grounding
│   ├── exceptions.py        # Week 2 errors
│   └── api/error_handlers.py
├── evaluation/
│   ├── metrics.py           # Hit@K, Recall@K, MRR
│   └── runner.py
├── data/eval/retrieval_benchmark.json
├── scripts/run_week2_demo.sh
├── docs/week2_journal.md
└── docs/retrieval_design_report.md
```

## 面试追问（Week 2）

1. **为什么 prompt 要版本化？** — 线上可回滚、可对比实验、与 eval 集绑定 reproducible 行为。
2. **Hit@K 和 Recall@K 区别？** — Hit：top-k 是否出现任一相关文档；Recall：相关文档被找回的比例。
3. **MRR 解决什么问题？** — 衡量第一个相关结果排名多靠前，比 Hit@1 更细。
4. **score_threshold 调太高会怎样？** — precision↑ recall↓，可能无 context 导致拒答。
5. **如何 debug retrieval 变差？** — `/experiments/retrieval` 矩阵 + `/evaluate/retrieval` 指标 + 日志 `hits_after_threshold`。

## License

MIT — 个人学习项目
