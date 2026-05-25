# Docker 运行说明

## 是否适合用 Docker？

**适合。** 尤其是：

- **Qdrant** 本身就应该容器化，和 API 环境解耦
- **依赖一致**：`torch`、`sentence-transformers` 在本机常因 Python 版本冲突装不上
- **接近生产**：Week 6 会专门做 Dockerfile 优化与 Compose 多服务编排；Week 1 先跑通 Compose 是合理提前量

注意：镜像会偏大（PyTorch + 模型），首次 `docker compose build` 需要网络和几分钟，属正常现象。

## PDF 后续计划里有没有 Docker？

有。**Week 6 — Docker & CI/CD** 包括：

| Day | 内容 |
|-----|------|
| Day 1 | Dockerfile optimization（镜像分层） |
| Day 2 | Docker Compose orchestration（多服务部署） |
| 后续 | CI/CD pipeline |

当前仓库提供的是 **Week 1 可用的基础版** Dockerfile + 全栈 Compose；Week 6 可在同一文件上演进（multi-stage build、非 root 用户、更小镜像等）。

## 两种运行方式

### A. 全 Docker（推荐验收 Week 1）

```bash
cd industrial-rag-platform
docker compose up -d --build
```

- API: http://127.0.0.1:8000/docs
- Qdrant UI: http://127.0.0.1:6333/dashboard

**入库请用 upload**（容器内没有你家目录路径）：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest/upload" \
  -F "file=@data/sample/rag_overview.md"
```

### B. 混合开发（热重载）

只起 Qdrant：

```bash
docker compose -f docker-compose.dev.yml up -d
```

本机跑 API（`.env` 里 `QDRANT_HOST=localhost`）：

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

## 常用命令

```bash
docker compose logs -f api
docker compose ps
docker compose down
docker compose build --no-cache api   # 依赖变更后重建
```

## 环境变量

Compose 从项目根目录 `.env` 读取（可复制 `.env.example`）。容器内 **必须** 使用 `QDRANT_HOST=qdrant`（服务名），已在 `docker-compose.yml` 中写好，无需手改。

## Week 6 可优化项（预留）

- Multi-stage：builder 装依赖，runtime 只拷贝 site-packages
- 非 root 用户运行 uvicorn
- 将模型 bake 进镜像 vs 挂载 volume 的权衡
- 添加 Redis / Prometheus 等服务到同一 Compose 网络
