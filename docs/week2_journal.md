# Week 2 Learning Journal — Retrieval Quality & Evaluation

> 按 PDF 要求：每天写代码、做实验、保存截图。截图建议放在 `evidence/screenshots/week2/`。

## Day 1 — Prompt Builder + versioning

### 完成内容与代码位置

| 项目 | 记录 |
|------|------|
| 核心模块 | `app/rag/prompts.py` — `PromptVersion`、`PROMPT_REGISTRY`、`PromptBuilder.build_messages()` |
| API 列表 | `GET /api/v1/prompts` → `routes.list_prompts` |
| API 问答 | `POST /api/v1/query` 请求体可选 `prompt_version`；响应含 `prompt_version` 字段 |
| 接入生成 | `pipeline.query()` → `_openai_generate()` 使用 `PromptBuilder`（无 API Key 时为 `retrieval_only` 占位，仍回显版本名） |
| 配置默认 | `app/config.py`：`prompt_version=v1_grounded`；`.env` 中 `PROMPT_VERSION` |
| 单元测试 | `tests/test_prompts.py` |

### 三个 prompt 版本（注册表）

| version | 用途（description） |
|---------|---------------------|
| `v1_grounded` | 仅用 context 回答；不够就说不知道；引用 `[1]`、`[2]` |
| `v2_strict_citations` | 每句事实必须以 `[n]` 结尾；无法回答时用固定拒答句 |
| `v3_refusal_aware` | context 弱/空时明确拒答；短答 + 引用 |

请求里的 `prompt_version` **优先于** `.env` 默认值。

### 命令（实验顺序）

```bash
# 1. 服务已启动；Week 1 语料在 documents（示例：rag_overview.md 已 ingest）
curl -s http://127.0.0.1:8000/api/v1/prompts | python3 -m json.tool

# 2. 单元测试
pytest tests/test_prompts.py -v

# 3. 指定版本提问（需库里有检索结果；无 OPENAI_API_KEY 时为 retrieval_only 占位答案）
curl -s -X POST "http://127.0.0.1:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why do we use chunk overlap?", "prompt_version": "v2_strict_citations", "top_k": 3}' \
  | python3 -m json.tool
```

也可在 http://127.0.0.1:8000/docs 中试 `GET /prompts` 与 `POST /query`。

### 请求链路（Day 1 新增部分）

```text
POST /query { question, prompt_version? }
  → pipeline.retrieve()           # Week 1 已有
  → _format_context()             # [1]、[2] 编号块
  → prompt_version = 请求体 || settings
  → PromptBuilder(version).build_messages()   # 有 OpenAI Key 时
  → 响应 answer + prompt_version + citations
```

### 截图对应（`evidence/screenshots/week2/`）

| 文件 | 应对内容 |
|------|----------|
| `week2-day1-prompts-list.png` | `GET /prompts` 返回 3 个 version + description |
| `week2-day1-prompts-pytest.png` | `pytest tests/test_prompts.py -v` 通过 |
| `week2-day1-query.png` | `POST /query` 带 `prompt_version`（如 v2）；可见 `prompt_version` 字段与检索引用 |

### 理解（记一句）

Prompt 是**线上可变更的业务逻辑**，用版本字符串管理便于 A/B、回滚，并与评估 / 日志中的 `prompt_version` 字段对齐，保证行为可复现。

### 与后续天的关系

- **Day 2**：在生成结果上增加 `grounding`（与 prompt 正交）。
- **Day 3+**：检索参数（`top_k`、`score_threshold`）与 prompt 版本可组合实验。

## Day 2 — Citation + hallucination control

### 完成内容与代码位置

| 项目 | 记录 |
|------|------|
| 核心模块 | `app/rag/grounding.py` — 引用解析、`assess_grounding()`、`filter_by_score_threshold()` |
| 接入 | `pipeline.query()` 生成答案后调用 `assess_grounding()` |
| API 响应 | `QueryResponse.grounding`：`grounded`、`reason`、`top_score`、`is_refusal` |
| 单元测试 | `tests/test_grounding.py`（6 条）；API 侧见 `tests/test_api_week2.py` |

### `grounding` 字段含义（与 Day 1 分工）

| 字段 | 含义 |
|------|------|
| `is_refusal` | 答案**文本**是否像拒答（关键词匹配 `_REFUSAL_PHRASES`） |
| `grounded` | **护栏结论**：无检索时要拒答才算通过；有检索时引用合法、或合理拒答 |
| `reason` | `no_retrieval` / `missing_citations` / `invalid_citation_index` / `ok` 等 |
| `top_score` | 当前检索结果最高分（无 chunk 时为 0） |

Day 1 的 `prompt_version` 管**怎么生成**；Day 2 管**生成后是否可信**（与 prompt 正交）。

### `assess_grounding` 决策（简图）

```text
无 chunks → reason=no_retrieval，is_refusal=是否拒答话术，grounded 与 is_refusal 一致
有 chunks → 检查 top_score、答案里 [n] 是否越界、是否缺引用（非拒答时）
```

与 Day 1 **v2_strict_citations** 联动：无 `[n]` 且非拒答 → `reason=missing_citations`，`grounded=false`。

### 实验 A — 有文档（正常检索）

```bash
# 需 documents 中已有 rag_overview.md（或其它已 ingest 语料）
curl -s -X POST "http://127.0.0.1:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why do we use chunk overlap?", "prompt_version": "v2_strict_citations", "top_k": 3}' \
  | python3 -m json.tool
```

**预期（无 OPENAI_API_KEY 时）**：`retrieval_count > 0`，`generation_mode=retrieval_only`，答案常带 `[1]`；`grounding.is_refusal=false`，`reason` 多为 `ok`（或占位答案下 `missing_citations`，视正文而定）。

→ 截图 **`week2-day2-grounding-report-refusal-false.png`**（有检索、非拒答场景）。

### 实验 B — 无文档（模拟空检索）

用 Day 3 会正式用到的手段：**极高 `score_threshold`** 滤掉所有 chunk（不必清空 Qdrant）：

```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is quantum gravity on Mars?", "top_k": 5, "score_threshold": 0.99}' \
  | python3 -m json.tool
```

**预期**：`retrieval_count=0`，`generation_mode=no_context`，固定拒答句；`grounding.reason=no_retrieval`，**`is_refusal=true`**，`grounded=true`。

→ 截图 **`week2-day2-grounding-report-refusal-true.png`**（`grounding` 整块清晰可见）。

```bash
pytest tests/test_grounding.py -v
```

→ 截图 **`week2-day2-grounding-pytest.png`**。

### 学习过程中的思考与排查（互动记录）

1. **第一次跑无文档实验报错**  
   `score_threshold=0.99` 时 API 返回 `internal_error`，日志为 `KeyError: 'is_refusal'`（`routes.py` 读 `g["is_refusal"]`，但 `chunks` 为空时旧版 `assess_grounding` **未返回** `is_refusal` 字段）。  
   **结论**：API protocol与实现不一致，属于真实 bug，不是实验操作错误。

2. **拒答话术与关键词不匹配**  
   pipeline 固定句为 *"I don't have enough information in the knowledge base..."*，而拒答词表原是 *"not enough information"*（子串对 **don't have** 不匹配），导致即使用户看到拒答，`is_refusal` 也可能为 false。  
   **修复思路**：无 chunk 分支补上 `is_refusal`；词表增加 `"enough information in the knowledge"`；测试覆盖 pipeline 拒答句。

3. **`grounded` vs `is_refusal` 别混**  
   - `is_refusal`：像不像拒答话。  
   - `grounded`：这条回答在护栏规则（Guardrail rules）下是否**可接受**（无检索时必须拒答；有检索时不能乱编且无非法引用）。  
   无检索且正确拒答 → 两者可同时为 true。

5. **与 Day 3 的衔接**  
   `filter_by_score_threshold` 写在 `grounding.py`，Day 3 调 `score_threshold` 时若滤到 0 条，会自然落到 Day 2 的 `no_retrieval` 路径——因此 Day 2 实验用 `score_threshold=0.99` 也是为 Day 3 埋点。

### 截图对应（`evidence/screenshots/week2/`）

| 文件 | 内容 |
|------|------|
| `week2-day2-grounding-report-refusal-false.png` | 有检索的 `query`：`grounding.is_refusal=false` |
| `week2-day2-grounding-report-refusal-true.png` | 无检索：`retrieval_count=0`，`is_refusal=true`，`reason=no_retrieval` |
| `week2-day2-grounding-pytest.png` | `pytest tests/test_grounding.py -v` 全绿 |

### 面试一句话

Grounding 是生成后的**规则引擎**（引用下标、拒答话术、检索是否为空），不替代 prompt，但能和 `v2_strict_citations` 一起构成「可上线」的最小幻觉防护。

## Day 3 — top-k / chunk_size / threshold 实验

### 完成内容与代码位置

| 项目 | 记录 |
|------|------|
| API 能力 | `POST /api/v1/experiments/retrieval`（`top_k_values` × `score_thresholds` 网格） |
| 核心逻辑 | `pipeline.run_retrieval_experiment()` + `retrieve()`（统一走 `filter_by_score_threshold`） |
| 实验脚本 | `scripts/run_retrieval_experiments.py`（打印 Part A / Part B 终端表格） |
| collection 设计 | `documents`（overview）/ `documents_topk`（Part A）/ `documents_cs*`（Part B）分离 |

### 你在 Day 3 的关键思考（互动记录）

1. **先质疑实验形态是否“美观”**  
   你提出直接用 API 跑矩阵不够直观；最终方案改为**脚本打印表格**，API 保留用于能力演示。这样截图更清晰、复现实验更稳定。

2. **发现默认样本下 `top_k=5` 可能没意义**  
   你注意到 `rag_overview.md` 默认分块只有约 4 个，追问 `top_k=5` 是否有效。这个判断是对的：当候选块数不足时，增大 `top_k` 不增加信息。  
   因此新增更长语料 `corpus_topk.md`（约 11 chunks@512）承载 Part A。

3. **坚持做 chunk_size 实验，并追问公平性**  
   你先提出“不同 document、ingest 一次、不要清库”；随后又追问“严格控制变量是否应同文档”。最终你明确选择了更严谨方案：  
   **同一文档 `chunk_size_sweep.md`，分别进不同 collection（`documents_cs128/256/512`）**，避免互相污染。

4. **明确要求隔离 Day 3 与其它语料**  
   你指出 `rag_overview.md` 与 `corpus_topk.md` 混在一个 collection 会污染结果；随后把 Part A 改到 `documents_topk`，并保留 `documents` 给 overview，分离成功。

5. **重置环境后复验结果差异**  
   你验证到：Part A 与旧结果差异明显、Part B 基本稳定。结论与设计一致：Part A 受混库影响大，Part B 因独立 collection 更稳定。

### 实验数据与 collection 映射

| 实验 | 文档 | collection | 目的 |
|------|------|------------|------|
| Part A（top_k × threshold） | `corpus_topk.md` | `documents_topk` | 避免与 `rag_overview.md` 混检索 |
| Part B（chunk_size 对比） | `chunk_size_sweep.md` | `documents_cs128` / `documents_cs256` / `documents_cs512` | 同文档控制变量，仅改变 chunk_size |
| Week1/普通 query | `rag_overview.md` | `documents` | 与 Day3/Day4 实验隔离 |

### 命令与结果（本地复跑，2026-05-27）

```bash
python scripts/run_retrieval_experiments.py --skip-ingest
```

**Part A（`documents_topk`）**

| top_k | threshold | hit_count | top_score | 观察 |
|------:|-----------|----------:|----------:|------|
| 1 | none | 1 | 0.5521 | baseline |
| 1 | 0.30 | 1 | 0.5521 | 低阈值下无变化 |
| 3 | none | 3 | 0.5521 | hit_count 随 k 增加 |
| 3 | 0.30 | 3 | 0.5521 | 仍全部保留 |
| 5 | none | 5 | 0.5521 | |
| 5 | 0.30 | 5 | 0.5521 | |
| 10 | none | 10 | 0.5521 | 覆盖更广 |
| 10 | 0.30 | 5 | 0.5521 | 阈值过滤掉低分尾部（10→5） |

补充：`documents_topk` 当前 `points_count=11`。

**Part B（同文三 collection）**

| chunk_size | collection | points_count | hits@5 | top_score 区间 |
|-----------:|------------|-------------:|-------:|---------------|
| 128 | `documents_cs128` | 44 | 5 | 0.8035 ~ 0.8984 |
| 256 | `documents_cs256` | 15 | 5 | 0.5448 ~ 0.7216 |
| 512 | `documents_cs512` | 7 | 5 | 0.5718 ~ 0.6479 |

解读：chunk 越小，索引点数越多（44→15→7）；在固定 query 下都能命中 5 条，但 top_score 分布发生变化，说明检索粒度确实影响排序与相似度。

### 本日结论

1. Day 3 最重要的是**实验可解释性**：collection 先隔离，再谈参数结论。  
2. `top_k` 的意义依赖候选块规模；语料太小时增大 `top_k` 没有信息增益。  
3. `score_threshold` 主要影响“尾部低分块是否被过滤”，在 `k` 较大时更明显。  
4. chunk_size 实验若不控制同文档/同 query，会混入语料差异，结论不可靠。

### 截图对应（`evidence/screenshots/week2/`）

| 文件 | 内容 |
|------|------|
| `week2-day3-experiment-matrix-A.png` | Part A 表格（`documents_topk`，top_k × threshold） |
| `week2-day3-experiment-matrix-B.png` | Part B 表格（`documents_cs*`，同文档 chunk_size 对比） |

### 与 Day 4 的衔接

Day 3 Part A 已固定 `documents_topk` + `corpus_topk.md`，可直接作为 Day 4 benchmark 的评估索引；避免把 `rag_overview.md` 混进同一评估池。

## Day 4 — Hit@K / Recall@K / MRR

### 完成内容与命令

| 项目 | 记录 |
|------|------|
| 代码 | `evaluation/metrics.py`，`evaluation/runner.py`，`POST /api/v1/evaluate/retrieval` |
| 数据 | `data/sample/corpus_topk.md` → Qdrant **`documents_topk`**（与 `rag_overview.md` 的 `documents` 分离） |
| 标注 | `data/eval/retrieval_benchmark.json`（4 条 query，手标 `relevant_chunk_ids`） |
| 前置 | Day 3：`python scripts/run_retrieval_experiments.py --part topk` |
| 标注辅助 | `python scripts/build_eval_benchmark.py --preview-only`（只看 top-5 片段，不自动写 gold） |
| 评估 | `curl -X POST .../api/v1/evaluate/retrieval -d '{"top_k": 10}'` |
| 截图 | `week2-day4-eval-metrics1.png`, `week2-day4-eval-metrics1.png`（`metrics` + `collection_name: documents_topk`） |

### 指标理解（本仓库定义）

| 指标 | 含义 |
|------|------|
| **Hit@K** | 对每个 query：top-K 检索结果里是否出现**至少一个** gold `chunk_id`（0 或 1，再对 query 平均） |
| **Recall@K** | 每个 query 的 gold 有多个时：top-K 命中了几个 gold / gold 总数；由于benchmark中每个 query 只有一个 gold chunk_id，因此 recall@K 等价于 hit@K |
| **MRR** | 每个 query：第一个命中 gold 的排名倒数（rank=1 → 1.0，rank=3 → 1/3），再平均 |

### 聚合结果（手标 gold，`top_k=10`，`documents_topk`，2026-05-27 本地跑）

| 指标 | 值 |
|------|-----|
| num_queries | 4 |
| hit@1 | **0.5** |
| hit@3 | **0.75** |
| hit@5 | **1.0** |
| mrr | **0.6333** |
| recall@1 / @3 / @5 | 与 hit@* 相同（每条仅 1 个 gold） |

解读：检索「沾边」不难（Hit@5=1），但 **4 个 query 中仅有 2 个的正确 chunk 排在第 1 位**（Hit@1=0.5），说明排序仍有改进空间。

### 逐条 query（手标 + 检索表现）

| Query（缩写） | Gold chunk（前缀） | 检索 rank（约） | Hit@1 |
|---------------|-------------------|-----------------|-------|
| log hits / hits_after_threshold | `0cfc2644…` | 1 | 是 |
| what does top_k control | `aeff1e10…` | ~5 | 否 |
| failure mode threshold cliff | `32f6f289…` | **3** | 否 |
| sweep score_threshold after new embedding model | `b379b817…` | 1 | 是 |

### 标注过程（未使用 auto top-2 作为最终 gold）

1. 运行 `build_eval_benchmark.py --preview-only`，对照返回片段正文。
2. 在 `retrieval_benchmark.json` 里按 **corpus_topk.md 段落** 手填 `relevant_chunk_ids`。
3. **threshold cliff** 一例：preview 时 top-1/2 为 `0cfc2644`、`0b0beadb`（只有 threshold 字样），真正含 **「Threshold cliff」** 定义的是 `32f6f289`（Failure modes 第 3 条），排在第 3 → 手标仅 `32f6f289`，故 Hit@1=0、扩大 K 后可命中。
4. **re-ingest `corpus_topk` 后必须重标**（chunk UUID 会变）。

### 与 Day 3 的关系

- Day 3 Part A：同一语料 `corpus_topk.md`、同一 collection `documents_topk`，调 `top_k` / `score_threshold`。
- Day 4：在同一索引上用 **固定 benchmark** 算 Hit@K / MRR，衡量「检索是否找回对的块」，而不是单次 query 的 `hit_count`。

### 面试一句话

Hit@K 看「有没有」；MRR 看「排第几」；gold label 必须按正文人工核对，不能把检索 top-2 直接当标准答案（cliff 题即反例）。

## Day 5 — Structured error handling

### 完成内容与代码位置

| 项目 | 记录 |
|------|------|
| 错误模型 | `app/exceptions.py`：`AppError` + `NotFoundError` / `IngestionError` / `RetrievalError` / `GenerationError` / `EvaluationError` |
| 统一处理 | `app/api/error_handlers.py`：注册 `AppError` 与兜底 `Exception` 的 JSON handler |
| 路由接入 | `app/main.py`：`register_exception_handlers(app)` |
| 触发点示例 | `app/api/routes.py`：`POST /ingest/path` 文件不存在时抛 `NotFoundError` |
| 响应约定 | `app/api/schemas.py`：`ErrorResponse`（`error_code`、`message`、`details`） |
| API 测试 | `tests/test_api_week2.py::test_structured_error_not_found` |

### 目标：把错误变成稳定协议（而不是字符串）

Day 5 的重点不是“多写几个 try/except”，而是把错误输出收敛成稳定 JSON protocal，便于前端和日志系统消费：

```json
{
  "error_code": "not_found",
  "message": "File not found: /nonexistent/file.md",
  "details": {}
}
```

其中 `error_code` 面向程序判定，`message` 面向人读，`details` 用于排障上下文。

### 验证命令（手工）

```bash
# 1) 触发 Day 5 核心场景：路径不存在
curl -s -X POST "http://127.0.0.1:8000/api/v1/ingest/path?path=/nonexistent/file.md" \
  | python3 -m json.tool
```

预期：
- HTTP 404
- body 含 `error_code: not_found`
- `message` 包含具体路径，便于定位

可选补充（验证兜底）：

```bash
# Qdrant 不可用时（或故障注入）会返回 retrieval_error
curl -s "http://127.0.0.1:8000/api/v1/health/qdrant" | python3 -m json.tool
```

### 自动化测试（Day 5 相关）

```bash
pytest tests/test_api_week2.py::test_structured_error_not_found -v
```

如果要和 Day 6 串起来，可直接跑：

```bash
pytest tests/ -v
```

### 学习过程中的思考（互动记录）

1. **为什么要有 `error_code` 而不只看 HTTP 状态码**  
   404 只说明“没找到”，但业务层仍需要知道是 `not_found`、`benchmark_missing` 还是其它场景。`error_code` 让客户端逻辑稳定，不依赖 message 文案。

2. **为什么把 handler 放在全局而不是每个路由自己 return JSON**  
   每个路由手写 JSONResponse 容易格式漂移；统一 handler 能保证全 API 响应一致，并减少重复代码。

3. **为什么保留兜底 `internal_error`**  
   未预期异常不能原样回给客户端（避免泄露栈信息）；统一转成 500 + 固定 `error_code`，日志里记录真实异常即可。

### 截图对应（`evidence/screenshots/week2/`）

| 文件 | 内容 |
|------|------|
| `week2-day5-error-json.png` | `POST /ingest/path` 使用不存在路径时，返回 404 + `error_code=not_found`（响应 JSON 清晰可见） |

### 面试一句话

Day 5 把“异常”升级成“协议”：路由只抛业务错误类型，统一 handler 输出标准 JSON（`error_code` + `message` + `details`），实现客户端可编程处理和线上可观测性。

## Day 6 — Unit tests + API tests

### 完成内容与测试文件

| 项目 | 记录 |
|------|------|
| 统一回归命令 | `pytest tests/ -v` |
| 指标测试 | `tests/test_metrics.py`（Hit@K / Recall@K / MRR） |
| Prompt 测试 | `tests/test_prompts.py`（版本注册、消息构建） |
| Grounding 测试 | `tests/test_grounding.py`（拒答检测、引用合法性、score threshold 过滤） |
| API 测试 | `tests/test_api_week2.py`（`/prompts`、`/query`、`/experiments/retrieval`、结构化错误） |
| 截图 | `week2-day6-pytest-allpass.png` |

### Day 6 的目标：把 Week 2 能力变成“可回归”

Day 1~5 已完成功能与实验；Day 6 要验证的是：后续改 prompt、改检索参数、改错误处理时，不会把已有行为悄悄改坏。  
因此测试分层为：
- **单元测试**：验证纯逻辑（metrics、grounding、prompts）；
- **API 测试**：验证接口契约（字段、状态码、错误 JSON）。

### 运行方式（建议顺序）

```bash
# 1) 一次性回归（Day 6 主命令）
pytest tests/ -v
```

按模块排查时可分别运行：

```bash
pytest tests/test_prompts.py -v
pytest tests/test_grounding.py -v
pytest tests/test_metrics.py -v
pytest tests/test_api_week2.py -v
```

### 覆盖点（本仓库 Week 2 视角）

1. **Prompt 版本化（Day 1）**  
   `test_prompts.py` 确保版本可枚举、构建消息结构稳定，避免改模板时破坏协议。

2. **Grounding 护栏（Day 2）**  
   `test_grounding.py` 覆盖 `no_retrieval`、`missing_citations`、非法引用下标、拒答识别等关键分支。

3. **检索评估指标（Day 4）**  
   `test_metrics.py` 固定 Hit@K / Recall@K / MRR 定义，防止后续重构导致指标语义漂移。

4. **Week2 API 行为（Day 1/2/3/5）**  
   `test_api_week2.py` 检查 `/prompts`、`/query`、`/experiments/retrieval` 以及 `not_found` 结构化错误返回。

### 学习过程中的思考（互动记录）

1. **为什么 Day 6 还要测 Day 1 的 prompt**  
   Prompt 是“可变业务逻辑”，最容易被迭代影响；不加测试，线上行为会难以复现。

2. **为什么 API 测试里要保留错误场景**  
   失败路径也是契约的一部分；客户端通常先依赖 `error_code` 做分支，不能只测 200 成功流。

3. **为什么主命令用 `pytest tests/ -v`**  
   这是最接近 CI 的一键回归入口，适合交付前做“总开关”验证。

### 截图对应（`evidence/screenshots/week2/`）

| 文件 | 内容 |
|------|------|
| `week2-day6-pytest-allpass.png` | 执行 `pytest tests/ -v`，显示 collected 数量与最终 `passed` 全绿结果 |
| `week2-day6-pytest-api-test.png` | 执行 `pytest tests/test_api_week2.py -v`，突出 Week2 API protocol测试通过 |


### 面试一句话

Day 6 的价值是把 Week 2 从“能跑”提升到“可回归”：用单测锁定算法与护栏语义，用 API 测试锁定接口与错误契约，保证后续迭代不破坏已验证能力。

## Day 7 — Retrieval design report

### 完成内容与交付物

| 项目 | 记录 |
|------|------|
| 最终文档 | `docs/retrieval_design_report.md` |
| 文档目标 | 汇总 Week 2 检索设计：Prompt 版本、grounding 护栏、实验入口、评估指标、故障排查 |
| 架构补充 | 报告内 mermaid 链路：`/query -> retrieve -> prompts -> LLM -> grounding` |
| 设计决策 | Prompt versioning、threshold 后过滤、grounding 与 answer 分离、benchmark 半自动构建 |
| 面试素材 | README「Week 2 面试追问」5 题（prompt 版本化、Hit/Recall、MRR、threshold、debug 路线） |

### Day 7 的目标：把 Week 2 从“实现”变成“可讲清楚的设计”

前 6 天完成了代码、实验与测试；Day 7 的核心是沉淀一份可复盘、可解释、可面试复述的设计报告。  
报告不是重复 API 文档，而是强调：
- 为什么这样设计（trade-off）；
- 出问题时如何定位（debug playbook）；
- 如何把实验结果连接到工程决策（而不是只报数字）。

### 报告主要内容（已落地）

1. **Goals**  
   明确 Week 2 目标是提升检索质量可见性，为 Week 3 reranker 做准备。

2. **Architecture additions**  
   用流程图和组件表说明新增模块职责：`prompts.py`、`grounding.py`、`metrics.py`、`exceptions.py`。

3. **Experiments section**  
   约定实验入口与填表方式（`run_week2_demo.sh` + `build_eval_benchmark.py` + `/evaluate/retrieval`）。

4. **Design decisions**  
   解释关键选择背后的理由（可回滚、低成本过滤、客户端可拦截 ungrounded、人工校正 gold）。

5. **Failure modes & debug**  
   列出常见症状与快速检查路径（Hit@K=0、chunks 全被过滤、`grounded=false`、Qdrant 故障）。

6. **Interview talking points**  
   给出可直接复述的面试短答，和 README 追问形成对应关系。

### 运行与验证（Day 7 交付前检查）

```bash
# 1) 重新跑 Week 2 演示链路（确保报告中的命令可执行）
./scripts/run_week2_demo.sh

# 2) 生成/校对 benchmark（如有重新 ingest，需要重标）
python scripts/build_eval_benchmark.py

# 3) 复算评估指标，用于填报告实验表
curl -s -X POST "http://127.0.0.1:8000/api/v1/evaluate/retrieval" \
  -H "Content-Type: application/json" \
  -d '{"top_k": 10}' | python3 -m json.tool
```

校验点：
- 报告中的路径与模块名与代码一致；
- 报告里的命令在本机可执行；
- 指标与 Day 4 口径一致（Hit@K / Recall@K / MRR 定义不漂移）。

### 学习过程中的思考（互动记录）

1. **设计报告不是“再写一遍 README”**  
   README 偏快速上手；设计报告要讲清楚“为何这样做、如何验证、如何排障”。

2. **实验数字要有上下文才有价值**  
   单独给 Hit@5=1.0 信息不足；必须配合 Hit@1、MRR、标注方式与 collection 隔离策略一起解释。

3. **可复现实验比漂亮结论更重要**  
   若 benchmark 或 collection 混用，结论会波动；报告里必须写清数据来源和复现实验命令。

### 面试一句话

Day 7 的交付是把 Week 2 工程实践抽象成一套可复用的检索设计方法：先定义指标与协议，再做参数实验和故障定位，最后沉淀为可复现、可答辩的设计报告。
