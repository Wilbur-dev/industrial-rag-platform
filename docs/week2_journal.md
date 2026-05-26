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

| 项目 | 记录 |
|------|------|
| 完成内容 | `app/exceptions.py`，`app/api/error_handlers.py` |
| 验证 | `ingest/path` 404 返回 `error_code: not_found` |
| 截图 | `week2-day5-error-json.png` |

## Day 6 — Unit tests + API tests

| 项目 | 记录 |
|------|------|
| 命令 | `pytest tests/ -v` |
| 新增 | `test_metrics`, `test_prompts`, `test_grounding`, `test_api_week2` |
| 截图 | `week2-day6-pytest-green.png` |

## Day 7 — Retrieval design report

| 项目 | 记录 |
|------|------|
| 交付 | `docs/retrieval_design_report.md` |
| 面试自测 | 见 README Week 2 追问 |
