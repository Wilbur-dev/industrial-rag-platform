# Industrial RAG Platform — Week 1

Production-grade **Minimal RAG Foundation**，对应 `Full_Industrial_RAG_LLM_Execution_Guide.pdf` 第一周（Day 1–7）。

## 你能用这个 repo 做什么

| Day | 功能 | API / 模块 |
|-----|------|------------|
| 1 | FastAPI 骨架、配置、日志、健康检查 | `GET /api/v1/health` |
| 2 | PDF / Markdown 入库 | `POST /api/v1/ingest/upload` |
| 3 | 分块（size + overlap） | `app/rag/chunking.py` |
| 4 | Embedding（batch + no_grad） | `app/rag/embedding.py` |
| 5 | Qdrant 向量库 | `docker compose` + `health/qdrant` |
| 6 | 检索 +  grounded 回答 + 引用 | `POST /api/v1/query` |
| 7 | 文档与架构图 | `docs/`, `docs/week1_journal.md` |

## 快速开始

### 方式 A：Docker 一键运行（推荐）

需要已安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

```bash
cd "/Users/liweihao 1/Downloads/recent_occupation/llm/industrial-rag-platform"
docker compose up -d --build
```

- API 文档：http://127.0.0.1:8000/docs  
- Qdrant：http://127.0.0.1:6333/dashboard  

首次 build 会下载 Python 依赖和 embedding 模型，约数分钟。

```bash
# 入库（Docker 内请用 upload，不要用本机绝对路径的 ingest/path）
curl -X POST "http://127.0.0.1:8000/api/v1/ingest/upload" \
  -F "file=@data/sample/rag_overview.md"

curl -X POST "http://127.0.0.1:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why do we use chunk overlap?"}'
```

<<<<<<< HEAD
# Day 3–4：corpus_topk 进 documents_topk（与 rag_overview 的 documents 分离）
python scripts/run_retrieval_experiments.py --part topk
python scripts/build_eval_benchmark.py
curl -X POST "http://127.0.0.1:8000/api/v1/evaluate/retrieval" \
  -H "Content-Type: application/json" \
  -d '{"top_k": 10}'
=======
详见 [docs/docker.md](docs/docker.md)。混合开发（仅 Qdrant 在 Docker、API 本机热重载）：`docker compose -f docker-compose.dev.yml up -d`。
>>>>>>> 649b579488bf5df1d97f8f33acd9276ea322a050

### 方式 B：本机 Python

### 1. 环境

```bash
cd "/Users/liweihao 1/Downloads/recent_occupation/llm/industrial-rag-platform"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. 启动 Qdrant（若未使用方式 A 全 Docker）

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 3. 启动 API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

浏览器打开：http://127.0.0.1:8000/docs

### 4. 跑通 Week 1 流程

```bash
# 入库示例文档
curl -X POST "http://127.0.0.1:8000/api/v1/ingest/path?path=data/sample/rag_overview.md"

# 检索
curl -X POST "http://127.0.0.1:8000/api/v1/retrieve" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?"}'

# 问答（带 citations）
curl -X POST "http://127.0.0.1:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why do we use chunk overlap?"}'
```

或一键脚本（需 API 已启动）：

```bash
chmod +x scripts/run_week1_demo.sh
./scripts/run_week1_demo.sh
```

### 5. 可选：OpenAI 生成

在 `.env` 中设置 `OPENAI_API_KEY`，`/query` 将使用 LLM 基于检索上下文回答。

### 6. 单元测试

```bash
pytest tests/ -v
```

## 项目结构

```
industrial-rag-platform/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 集中配置
│   ├── logging_config.py    # 结构化日志
│   ├── api/                 # HTTP 路由
│   └── rag/                 # 入库、分块、向量、pipeline
├── training/                # Week 3 占位
├── evaluation/              # Week 2 占位
├── data/sample/             # 示例文档
├── docs/                    # 架构图 + Week1 日记模板
├── docker-compose.yml       # Qdrant
└── tests/
```

## 在 Cursor 里我可以帮你做什么

- **写代码**：像本仓库一样，按 PDF 逐天实现功能
- **改 bug**：把报错贴给我，或 @ 相关文件
- **跑命令**：安装依赖、启动服务、跑测试（需你本机有 Docker / Python）
- **解释概念**：chunk overlap、cosine similarity、hallucination 等
- **面试准备**：根据 `docs/week1_journal.md` 里的追问一起练

**你需要自己做的**：按 PDF 要求每天截图、填 journal、做参数实验（我无法替你保存截图到相册）。

## 面试追问（Week 1）

1. **为什么 centralized config？** — 环境一致、可测试、避免硬编码。
2. **为什么不用更简单方案（例如内存 list）？** — 无法持久化、无法水平扩展、无相似度索引。
3. **如何 debug retrieval 变差？** — 看 log 里 `latency_ms`、`hits`；调 chunk_size / top_k；检查 embedding 是否 normalize。
4. **如何评估是否变好？** — Week 2 会加 Hit@K / MRR；Week 1 可先对比同一 query 的 citation 分数与 excerpt 相关性。

## License

MIT — 个人学习项目
