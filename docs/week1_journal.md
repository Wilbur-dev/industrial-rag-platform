# Week 1 Learning Journal (Evidence Bundle)

> 按 PDF 要求：每天写代码、做实验、保存截图、记录问题、写总结。把截图放到 `evidence/screenshots/`。

## Day 1 — Backend skeleton


| 项目                                                                                                                                      | 记录                                                                                                                                                                                                                                  |
| --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 完成内容                                                                                                                                    | FastAPI、`config`、`logging`、`/api/v1/health`                                                                                                                                                                                         |
| Latency                                                                                                                                 |                                                                                                                                                                                                                                     |
| 问题                                                                                                                                      |                                                                                                                                                                                                                                     |
| 截图                                                                                                                                      | `week1-day1-health.png`, `week1-day1-logs.png`                                                                                                                                                                                                  |
| 总结                                                                                                                                      | 为什么需要 centralized config 和 structured logging？-用 .env + get_settings()，.env 是 唯一配置源， get_settings() 是 全局统一入口，所以dev加载本地 .env，docker用 container env，prod用 K8s secrets。代码不变，避免硬编码。环境切换时，确保不同环境下行为一致，避免配置漂移（config drift），从而提高一致性和可维护性。 - log 是给“机器”看的，不是人。structured logging = 日志变机器可读的数据，从而使query，聚合，监控成为可能。它是接入 ELK、Datadog 等现代observability系统的关键基础，同时也让在大规模生产环境下的排障和问题定位成为可能。 |                                                                                                                                                                                                                                     |


## Day 2 — Ingestion


| 项目                                                                                                                                                      | 记录                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| 完成内容                                                                                                                                                    | PDF + Markdown `ingest/upload`, `ingest/path`                      |
| Retrieval quality                                                                                                                                       | N/A（尚未检索）                                                          |
| 截图                                                                                                                                                      | `week1-day2-ingest-file-response.png`, `week1-day2-ingest-upload-response.png` |
| 总结                                                                                                                                                      | metadata（source, format, page_count）为何重要？                - source 用于溯源和引用，让用户知道答案来自哪份文档。format 区分 PDF 与 Markdown 的解析与分块方式，便于调参和排错。page_count 帮助 PDF 定位与判断抽取是否完整。三者一起保证入库不只是「一段文本」，而是带上下文的知识单元，支撑 grounded 回答和后续过滤。 |                                                                    |


## Day 3 — Chunking


| 项目                                                                                                                                 | 记录                                                                                |
| ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 实验                                                                                                                                 | 改 `CHUNK_SIZE` / `CHUNK_OVERLAP`，观察 chunk 数量                                      |
| 截图                                                                                                                                 | `week1-day3-chunking-test.png`, `week1-day3-chunk-params.png`, `week1-day3-chunk-count-compare.png` |
| 总结                                                                                                                                 | chunk 太大/太小对 recall 的影响？ - chunk 太大：单块包含过多主题，embedding 被稀释，与细粒度问题的相似度下降，相关句子不易进入 top-k，recall 降低。- chunk 太小：单块上下文不足或语义不完整，答案被拆碎，边界处易漏召；overlap 过小会加剧该问题。- 实践：在文档长度和 embedding 模型上下文之间取折中，用 overlap 保证边界上下文；最终应用固定问题集对比不同 CHUNK_SIZE/CHUNK_OVERLAP 的检索命中率（Week 1 样本较短，差异可能不明显，工业场景长 PDF 更明显）。|


## Day 4 — Embedding


| 项目      | 记录                                                                                      |
| ------- | --------------------------------------------------------------------------------------- |
| 理解      | `model.eval()`, `torch.no_grad()`, batch size                                           |
| Latency | 记录 embed 一批 chunk 的 ms                                                                  |
| 截图      | `week1-day4-loading-model-log.png`, `week1-day4-embed-latency.png`, `week1-day4-embed-batch-optional.png` |


## Day 5 — Qdrant


| 项目  | 记录                                                                                                       |
| --- | -------------------------------------------------------------------------------------------------------- |
| 命令  | `docker compose up -d`                                                                                   |
| 验证  | `GET /api/v1/health/qdrant`                                                                              |
| 截图  | `week1-day5-qdrant-dashboard.png` - Qdrant dashboard `localhost:6333/dashboard`, `week1-day5-qdrant-healthcheck.png` |


## Day 6 — Query pipeline


| 项目            | 记录                                                                                                                                                      |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 实验            | 同一问题不同 `top_k`                                                                                                                                          |
| Hallucination | 无文档时是否拒绝编造？返回no context                                                                                                                                 |
| 截图            | `week1-day6-query-with-citations.png` - `/api/v1/query` 含 citations 的 JSON, `week1-day6-topk-compare-top1.png`, `week1-day6-topk-compare-top2.png`, `week1-day6-no-context.png` |


## Day 7 — Documentation


| 项目    | 记录                                          |
| ----- | ------------------------------------------- |
| 交付    | README + `docs/architecture.md` + 本 journal |
| 面试题自测 | 见 README「面试追问」                              |


