# Week 1 Learning Journal (Evidence Bundle)

> 按 PDF 要求：每天写代码、做实验、保存截图、记录问题、写总结。把截图放到 `evidence/screenshots/`。

## Day 1 — Backend skeleton

### 完成内容

- 搭建 FastAPI 最小骨架。
- 实现集中配置 `app/config.py`（`.env` + `get_settings()`）。
- 实现结构化日志 `app/logging_config.py`。
- 完成健康检查 `GET /api/v1/health`。
- 补充 `tests/test_health.py` 验证接口可用。

### Latency

- 健康检查为轻量接口，体感响应接近实时。
- 本日重点是架构打底，未做系统化 latency benchmark。

### 遇到的问题

- 一开始配置分散在代码里，环境切换容易漏改。
- 日志若只输出自然语言，后续检索和聚合困难。
- 启动阶段如果日志未初始化，关键启动信息会丢失。
- 对应调整：统一走 `get_settings()`，并在 `lifespan` 中先 `setup_logging()` 再打印 `app_starting`。

### 思考与总结

- Day1 的核心不是“接口能跑就行”，而是把系统的可运维性和可扩展性提前设计好。
- 配置与日志看似基础，但会直接决定后面 Day2–Day6 的调参效率和排障成本。
- centralized config 让 dev/docker/prod 共享同一套参数入口，避免硬编码与配置漂移。
    - 用 .env + get_settings()，.env 是 唯一配置源， get_settings() 是 全局统一入口，所以dev加载本地 .env，docker用 container env，prod用 K8s secrets。代码不变，避免硬编码。环境切换时，确保不同环境下行为一致，避免配置漂移（config drift），从而提高一致性和可维护性。
- structured logging 让日志成为可检索、可聚合的数据，后续可直接接入 ELK/Datadog。
    - log 是给“机器”看的，不是人。structured logging = 日志变机器可读的数据，从而使query，聚合，监控成为可能。它是接入 ELK、Datadog 等现代observability系统的关键基础，同时也让在大规模生产环境下的排障和问题定位成为可能。
- 先把健康检查和测试补齐，等于给后续功能开发加了“回归基线”。

### 截图

- `day1-health.png`
- `day1-logs.png`


## Day 2 — Ingestion

### 完成内容

- 打通两条入库路径：`POST /api/v1/ingest/upload`（上传文件）与 `POST /api/v1/ingest/path`（本地路径）。
- 在 `app/rag/ingestion.py` 完成 PDF / Markdown 解析：
  - PDF：逐页抽取文本，写入 `metadata.format=pdf`、`metadata.page_count`。
  - Markdown：保留原始文本用于 chunking，并记录 `metadata.format=markdown`、`metadata.html_preview_len`。
- 在 API 层补齐基础错误处理：
  - `ingest/upload` 对空文件名返回 400。
  - 不支持的扩展名统一抛出 `ValueError` 并返回 400。
- 入库响应统一返回 `doc_id`、`source`、`chunks_indexed`、`latency_ms`，便于后续观察 ingest 效果。

### Retrieval quality

- N/A（尚未检索）

### 遇到的问题

- **路径与环境耦合问题**：`ingest/path` 依赖服务端可访问的文件路径。开发时如果路径写成主机绝对路径、容器内未挂载同路径，会直接失败。后续在脚本中优先示例相对路径，并在 Docker 场景推荐 `ingest/upload`。
- **文件类型边界问题**：只支持 `.pdf/.md/.markdown`，其余类型会报错。这个限制虽“严格”，但避免了把不可解析文件误入库，导致后续检索噪声。
- **输入完整性问题**：上传接口如果没有 `filename`，无法确定解析策略。已在路由层提前校验，避免进入 pipeline 后才报模糊错误。
- **文本抽取质量问题（PDF）**：部分 PDF 页可能抽取为空，虽然流程可继续，但会影响最终 chunk 质量，需要通过 `page_count` 与后续检索表现交叉判断。

### 思考与总结

- Day2 的核心不是“把文本塞进系统”，而是把文档变成“可追踪、可解释、可用于检索”的标准化输入。
- metadata（`source`, `format`, `page_count`/`html_preview_len`）的价值在于：
  - `source` 支撑溯源与引用，回答时能说清“信息来自哪里”。
  - `format` 决定解析与排障路径（PDF 和 Markdown 的问题模式不同）。
  - `page_count`/预览长度提供最小可观测性，帮助快速判断“文档是否被正确读取”。
  - 三者一起保证入库不只是「一段文本」，而是带上下文的知识单元，支撑 grounded 回答和后续过滤。
- 通过 Day2 我确认了一点：入库阶段越严格，后面 Day3–Day6（chunking、embedding、retrieval、query）的调参成本越低，系统也更稳定。

### 截图

- `day2-ingest-file-response.png`
- `day2-ingest-upload-response.png`


## Day 3 — Chunking

### 实验

- 调整 `CHUNK_SIZE` / `CHUNK_OVERLAP`，观察 chunk 数量和检索前置质量变化。
- 当前实现采用字符级滑窗分块：窗口长度为 `chunk_size`，步长为 `chunk_size - chunk_overlap`。
- 分块时把 `char_start` / `char_end` 写入 metadata，便于后续定位命中片段。
- 用固定文档重复实验，确认参数变化与 chunk 数量变化方向一致（`chunk_size` 越小，chunk 数越多）。

### 遇到的问题

- **参数合法性问题**：`chunk_overlap >= chunk_size` 会导致步长为 0 或负数，分块逻辑不可用。已在 `chunk_document` 中显式抛错：`chunk_overlap must be smaller than chunk_size`。
- **边界语义断裂问题**：如果 overlap 太小，跨边界句子容易被拆开，导致检索命中到“半句上下文”。
- **粒度权衡问题**：chunk 太大时主题混杂，向量语义被稀释；chunk 太小时上下文不足，答案信息被切碎。
- **样本规模问题**：Week1 样本文档较短，指标差异不会像长 PDF 那么明显，容易误判“参数无影响”。

### 思考与总结

- Day3 的关键认知：chunking 不是“机械切文本”，而是在召回率、语义完整性、索引规模之间做工程折中。
- 对 recall 的影响可以概括为：
  - chunk 太大：单块包含过多主题，embedding 被稀释，与细粒度问题的相似度下降，相关句子不易进入 top-k，recall 降低。
  - chunk 太小：单块上下文不足或语义不完整，答案被拆碎，边界处易漏召；overlap 过小会进一步放大边界丢失，加剧该问题。
- overlap 的价值在于“保边界语义”：用可控冗余换更稳的召回，尤其对跨句信息和长文档更明显。
- 实践：在文档长度和 embedding 模型上下文之间取折中，用 overlap 保证边界上下文；最终应用固定问题集对比不同 CHUNK_SIZE/CHUNK_OVERLAP 的检索命中率（Week 1 样本较短，差异可能不明显，工业场景长 PDF 更明显）。
- 本阶段结论不是追求某个固定参数，而是建立可复现实验方法：固定问题集 + 固定语料 + 扫描参数，对比 chunk 数量、top-k 命中与引用质量，再确定默认值。

### 截图

- `day3-chunking-test.png`
- `day3-chunk-params.png`
- `day3-chunk-count-compare.png`


## Day 4 — Embedding

### 完成内容

- 实现 `EmbeddingService`，统一提供 `embed_texts()` 和 `embed_query()` 两个入口。
- 模型加载采用 `_load_model()` + `@lru_cache`，避免重复初始化同一 embedding 模型。
- 加入 `model.eval()` 与 `torch.no_grad()`，确保推理模式稳定、减少不必要的梯度开销。
- 引入 batch 推理（`embedding_batch_size`），按批次编码文本并合并向量结果。
- 启用 `normalize_embeddings=True`，为后续 cosine 相似度检索提供更稳定的向量尺度。

### 理解

- `model.eval()`：关闭训练态行为（如 dropout），保证同一输入推理结果稳定。
- `torch.no_grad()`：禁用梯度计算，降低显存/内存和推理开销。
- batch size：核心调参杆，直接影响吞吐、延迟和资源占用平衡。

### Latency

- 记录了 embedding 阶段的时间特征：首轮会出现明显冷启动开销（模型加载与权重准备），后续同模型调用更快。
- 在固定模型下，batch 推理通常优于逐条推理；但 batch 不是越大越好，需要结合机器资源和响应时延目标取平衡。

### 遇到的问题

- **冷启动延迟问题**：首次调用需要加载模型，耗时明显高于稳态请求。
- **批大小权衡问题**：batch 过小吞吐低，batch 过大可能带来内存压力并拉高单次响应时延。
- **运行环境噪声问题**：实验过程中出现过依赖版本告警（例如客户端/服务端版本差异提示），虽不直接改变 embedding 逻辑，但会干扰性能判断，需要先区分“功能正确”与“环境告警”。

### 思考与总结

- Day4 的关键不是“把向量算出来”，而是把 embedding 过程做成可复用、可观测、可调优的基础能力。
- 我把这一天的重点放在三个工程原则上：
  - **稳定性**：`eval + no_grad` 保障推理行为一致。
  - **效率**：batch 推理 + 模型缓存减少重复开销。
  - **兼容检索**：向量归一化让后续 cosine 检索更可控。
- 结论是：embedding 阶段的性能瓶颈主要在“首次加载”和“批大小配置”，因此后续优化优先级应是先控制冷启动，再做 batch sweep，而不是盲目更换模型。

### 截图

- `day4-loading-model-log.png`
- `day4-embed-latency.png`
- `day4-embed-batch-optional.png`


## Day 5 — Qdrant

### 完成内容

- 使用 `docker compose` 启动 Qdrant，并通过 healthcheck 保证服务 ready 后再给 API 使用。
- 在 `VectorStore` 中完成 Qdrant 客户端接入（`host`/`port` 来自集中配置）。
- 实现集合初始化逻辑 `ensure_collection()`：集合不存在时自动创建，向量距离使用 `COSINE`。
- 实现向量写入与检索：
  - `upsert_chunks()` 将 chunk 向量与 metadata 一起写入。
  - `search()` 兼容不同 qdrant-client 接口（`search` 与 `query_points`）。
- 新增 `GET /api/v1/health/qdrant`，用于区分“Qdrant 不可用”和“服务可用但集合尚未创建”。

### 命令

- `docker compose up -d`

### 验证

- `GET /api/v1/health/qdrant`

### 遇到的问题

- **服务可达性问题**：API 与 Qdrant 在不同运行方式下主机名不同（本机开发常用 `localhost`，容器内需用服务名 `qdrant`），配置不一致会直接连不上。
- **初始化时序问题**：如果 API 先于 Qdrant 完全就绪启动，早期请求会报连接异常。通过 Compose 的 `depends_on + healthcheck` 缓解了这类启动竞态。
- **集合生命周期问题**：首次运行时集合尚未创建，容易被误判为故障。健康检查里明确返回 `not_created_yet`，把“未初始化”和“不可用”区分开。
- **客户端版本兼容问题**：实验中出现过 qdrant-client 与服务端版本告警，因此在检索方法上做了新旧接口兼容，降低升级带来的中断风险。

### 思考与总结

- Day5 的核心不是“接上一个数据库”，而是把向量存储做成可持久化、可诊断、可演进的基础设施层。
- 与内存存储相比，Qdrant 的价值在于：
  - 持久化：重启后数据不丢失；
  - 检索能力：原生向量索引与相似度查询；
  - 运维友好：有健康检查、仪表盘、后续过滤与扩展能力。
- 我在这一天最重要的收获是：向量库接入要优先保证“可观测性和可恢复性”（健康状态、初始化状态、兼容性处理），而不是只追求单次查询跑通。
- 结论：Day5 完成后，RAG 流水线从“本地算法组件”升级为“有状态服务系统”，为 Day6 的检索与引用回答提供了稳定底座。

### 截图

- `day5-qdrant-dashboard.png` - Qdrant dashboard `localhost:6333/dashboard`
- `day5-qdrant-healthcheck.png`


## Day 6 — Query pipeline

### 完成内容

- 打通 `POST /api/v1/query`：问题进入后先检索，再基于检索上下文生成回答。
- 返回结构化结果：`answer`、`generation_mode`、`citations`、`retrieval_count`、`latency_ms`。
- 引用信息包含 `chunk_id`、`score`、`source`、`excerpt`，确保回答可追溯。
- 实现多种生成模式：
  - 有 `OPENAI_API_KEY`：走 LLM 生成（要求仅使用上下文并给出引用）。
  - 无 key：走 `retrieval_only` 模式，直接基于 top chunk 给出 grounded 回答。
  - 无检索结果：返回 `no_context`，明确拒绝编造。
- 完成同一问题不同 `top_k` 的对比实验，并记录检索日志中的 `hits` 与 `latency_ms`。

### 实验

- 同一问题不同 `top_k`

### Hallucination

- 无文档时是否拒绝编造？返回 `no_context`

### 遇到的问题

- **top_k 权衡问题**：`top_k` 太小可能漏掉关键证据，太大则容易引入弱相关片段，影响回答聚焦并增加时延。
- **“有答案”与“有依据”不等价问题**：即使文本看起来合理，如果没有 citation 或 citation 质量低，仍不应视为高质量 RAG 回答。
- **空检索处理问题**：如果不显式处理“无命中”场景，模型容易补全常识造成幻觉。已通过 `no_context` 分支硬约束输出。
- **模式差异问题**：`openai` 与 `retrieval_only` 的表达质量不同，验证时需要先区分“检索正确性”与“生成流畅度”，避免把生成问题误判为检索问题。

### 思考与总结

- Day6 的核心是把“检索”真正接到“回答”上，并且保证回答可解释、可追责，而不是只追求自然语言看起来像对的。
- 我在这一天形成了一个判断标准：RAG 质量应优先看“是否 grounded + 是否可溯源”，其次才是语言润色。
- `top_k` 本质是召回与噪声的平衡旋钮；需要结合具体问题集反复对比，而不是设一个固定值一劳永逸。
- `no_context` 策略是生产可用性的关键：宁可明确说不知道，也不输出无法被证据支持的内容。
- 结论：Day6 完成后，系统具备了最小可用的“可引用问答闭环”，为后续 Week2 的量化评测（Hit@K / MRR）提供了可观测接口与行为基线。

### 截图

- `day6-query-with-citations.png` - `/api/v1/query` 含 citations 的 JSON
- `day6-topk-compare-top1.png`
- `day6-topk-compare-top2.png`
- `day6-no-context.png`


## Day 7 — Documentation

### 完成内容

- 完成 `README.md`，覆盖 Week1 全流程能力、两种启动方式（全 Docker / 本机 Python）、常用命令与测试入口。
- 完成 `docs/architecture.md`，补齐系统图、模块边界、Index/Query 流程和关键设计决策。
- 完成 `docs/docker.md`，明确容器场景下的运行要点（如 Docker 内优先 `ingest/upload`）。
- 维护 `docs/week1_journal.md`，把 Day1–Day7 的实验过程、截图与结论整理为可回看证据链。
- 提供 demo 脚本（`scripts/run_week1_demo.sh`、`scripts/run_week1_demo_docker.sh`）降低复现门槛，确保文档与实际接口一致。

### 交付

- README + `docs/architecture.md` + 本 journal

### 遇到的问题

- **文档与实现一致性问题**：代码迭代后，文档最容易滞后。解决方式是用 demo 脚本反向校验 README 中的命令与 API 行为，避免“文档能看不能跑”。
- **运行场景差异问题**：本机与 Docker 的路径语义不同（`ingest/path` vs `ingest/upload`），如果不写清楚，用户很容易误用导致失败。
- **信息组织问题**：Week1 涉及模块多，若只按文件罗列，读者难以形成系统理解。最终改为“流程 + 模块边界 + 设计决策”三层结构。
- **验收视角缺失问题**：只有功能说明不够，需要把“如何验证成功”也写进文档（health、ingest、retrieve、query、qdrant health），便于自测和面试展示。

### 思考与总结

- Day7 的核心不是“补文档”，而是把代码、实验和结论沉淀成可复用的工程资产。
- 我把文档目标从“说明功能”升级为“三件事”：
  - **可运行**：新同学按 README 可以完整跑通；
  - **可理解**：从 architecture 一眼看懂系统边界与数据流；
  - **可答辩**：面试追问能直接映射到真实实现与实验证据。
- 通过这一天我确认：文档质量本身就是系统质量的一部分。没有可验证文档，研发成果很难稳定复现，也难以在团队内传递。
- Week1 的最终产出不仅是一个能跑的最小 RAG 原型，更是一套“代码 + 实验 + 文档”的闭环，为 Week2 指标化评估和后续工程化迭代打下基础。

### 面试题自测

- 见 README「面试追问」


