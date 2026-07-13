#  金融领域 GDPval 式训练集生产管线

从真实金融文档出发，自动生产 **[GDPval](https://arxiv.org/abs/2509.xxxxx) 风格**的高价值任务数据：
每条样本 = **任务(query) + 参考文件 + 评分细则(rubric) + 若干份带分交付物**，可直接用于 SFT / 拒采 / RL / 奖励模型等下游训练。

> 管线把爬取的金融报告切成「数据(输入) + 结论(隐藏答案锚点)」，用数据做参考、用领域专家 prompt 生成多子任务
> query，经 8 项硬门槛质检后，用切出的结论当 answer-key 生成**可客观打分**的 rubric，再用**多轮 agent + 沙箱**
> 让模型产出多格式交付物（md/pdf/docx/xlsx），最后由**跨家族 grader** 参照 rubric 与 answer-key 打分。

---

## 目录

- [一、方法与流程](#一方法与流程)
- [二、目录结构与文件说明](#二目录结构与文件说明)
- [三、安装](#三安装)
- [四、配置](#四配置)
- [五、运行](#五运行)
- [六、输出格式](#六输出格式)
- [七、当前状态与已知限制](#七当前状态与已知限制)

---

## 一、方法与流程

### 8 个阶段（S1→S8 + emit）

```
S1 partition   每篇报告切成三层: 数据 / 分析 / 结论。
               → 数据层作 reference (solver 输入); 分析+结论作 answer_key (隐藏, 仅评分用)
S2 grouping    领域内近邻成组: 每个文档 + 阈值内最近邻 (≤3) 组成多文件 bundle (本地 Qwen3 embedding)
S3 query_gen   bundle × 交付物类型 → 一条 GDPval 式 query (领域专家 prompt; 真实职业/产物/多子任务/格式)
S4 qc          8 项二值硬门槛, 全过才留 (可解/零泄漏/在领域/有交付物/非trivial/无歧义/真实/贯通)
S5 rubric_gen  query + reference + answer_key → 累加式 rubric (客观项 + answer_key 支撑的判断项 + GDPval 维度项)
S6 model_select 从候选模型选**最优的单个** output 模型 (据专家锚点一致性; 无锚点用默认)
S7 produce     多轮 agent + 沙箱: 选定的单模型每 query 产 3 份交付物 (md/pdf/docx/xlsx)
S8 grade       跨家族 grader 参照 rubric + answer_key 打分, 记 path+分, 标 best
emit           汇总为 GDPval schema 超集 items.jsonl
```

### 三个关键设计点

1. **剥掉的结论 = 免费 gold**：S1 把报告自己的分析与结论从输入中剥出、单独存为隐藏 `answer_key`，用作 rubric
   判断项的真值锚点——解决了「无 gold 时判断型评分无法验证」的循环，无需人工撰写 gold。
2. **近邻成组替代检索扩充**：在**已剥结论**的数据上做 embedding 近邻成组（绝对余弦阈值，可调），天然不泄漏；
   产出重叠的多文件 bundle，支持跨文档任务。
3. **跨家族 grader 防自偏好**：generator 与 grader 强制不同模型家族（GDPval 明确指出模型偏爱自己的输出）；
   有多个跨族 grader 时取平均并标记分歧。

细节：GDPval 头条评分是**盲配对人评**（非 rubric）；本管线为训练集需要而改用 rubric + answer-key 锚点，是有意的偏离。

---

## 二、目录结构与文件说明

```
final/
├── README.md              本文件 (总说明)
├── requirements.txt       Python 依赖
├── .env.example           API key 模板 (复制为 .env 填真实 key)
├── .gitignore             忽略 .env / 语料 / 产物 / 缓存
│
├── config/                ── 配置 (三个 yaml) ──
│   ├── domains.yaml        【唯一真相源】5 领域定义(职业轴/交付物类型/语料源) + 交付物类型定义
│   │                       + S4 八项硬门槛 + S5 GDPval 评分维度 + S2 近邻成组参数 + 抽样量 + S7 rollout 配置
│   ├── models.yaml         provider 适配(glm/deepseek 端点/模型/key 环境变量/思考参数) + 角色分配
│   │                       (author/generators/graders/qc_candidates/arbiter) + 本地 embedding 配置
│   └── pipeline.yaml       路径 + 规模目标 + partition(并发/段落上限) + agent 沙箱 + grading + 各阶段并发数
│
├── prompts/               ── 领域专家 prompt (每 stage: _shared 骨架 + 各领域文件, 运行时拼接) ──
│   ├── partition/_shared.md          三层信息判别 (data/analysis/conclusion), 跨领域
│   ├── query_gen/                    任务生成: _shared.md + {sovereign,monetary,fin_stability,banking,cross_border}.md
│   ├── qc/                           八门槛质检: _shared.md + 5 个领域文件
│   ├── rubric_gen/                   评分细则生成: _shared.md + 5 个领域文件
│   ├── output_agent/                 交付物生成 agent 系统 prompt: _shared.md + 5 个领域文件
│   ├── grader/                       交付物评分: _shared.md + 5 个领域文件
│   └── expert_anchor/                专家锚点标注指令 (Claude 现产 / 真人可替换)
│       ├── qc_label.md               质检基准标注 (用于选 QC 模型)
│       └── output_rank.md            交付物排序基准 (用于选 generator/grader 模型)
│
├── expert_anchor/         ── 专家锚点产物 (现为空占位; 跑选型步时生成) ──
│   ├── qc_labels.jsonl               每领域若干条 QC 真值标注
│   └── output_ranks.jsonl            每领域若干条交付物盲排序
│
├── src/                   ── 代码 ──
│   ├── util.py             配置加载 · prompt 拼接 · PDF 段落抽取(pymupdf) · jsonl 读写 · 近邻数据访问 · 并发 map(pmap)
│   ├── schema.py           数据契约: dataclass(CleanedDoc/Bundle/Query/QCResult/RubricItem/Rubric/Deliverable/Score/Item)
│   │                       + 各 LLM 步的输出 JSON Schema (保证跨领域一致、下游可直接消费)
│   ├── cli.py              命令行入口: `python -m cli s1|s2|...|s8|emit|all`
│   ├── emit.py             汇总 passed query + rubric + deliverables + scores → GDPval schema 超集 items.jsonl;
│   │                       复制参考文件进 outputs/reference_files/, answer_key 保持隐藏
│   ├── providers/          ── 可插拔 LLM / embedding provider ──
│   │   ├── base.py         OpenAI 兼容 provider: chat / chat_json(容错解析) / chat_messages(工具调用);
│   │   │                   .env 加载 · 按角色取 provider · 按 family 判跨族 · per-call 关思考开关
│   │   ├── glm.py          GLM-5.2 适配 (继承 base; 端点/模型见 models.yaml)
│   │   ├── deepseek.py     DeepSeek-v4-pro 适配 (继承 base)
│   │   └── embedding.py    本地 Qwen3-Embedding-0.6B (sentence-transformers; 无权重则明确报错不静默降级)
│   ├── agent/             ── S7 多轮 agent 框架 ──
│   │   ├── loop.py         多轮循环: 读参考→规划→python_exec 计算/建文件→自检→finish (OpenAI function calling)
│   │   ├── tools.py        工具定义与执行器: read_file / python_exec / write_file / finish
│   │   └── sandbox.py      子进程沙箱: 超时 + 内存限 + 危险调用 denylist (pilot 级, 非强隔离; 加固走 Docker)
│   └── stages/            ── 八个阶段 ──
│       ├── s1_partition.py         PDF→段落→LLM 判三层→reference + answer_key (并行分块/续跑/段落上限/零泄漏自检)
│       ├── s2_neighbor_grouping.py 领域内近邻成组 (ε-邻域+kNN 上限, 重叠 ego-邻域, 去重, 门控交付物类型)
│       ├── s3_query_gen.py         bundle × 交付物类型 → query (领域专家 prompt; xlsx 限量; 并发)
│       ├── s4_qc.py                八门槛质检 + QC 模型选型(据锚点一致性; 无锚点用默认); 并发
│       ├── s5_rubric_gen.py        query+reference+answer_key → rubric; 空 rubric 视为失败; 并发
│       ├── s6_model_select.py      选最优单个 output 模型 + grader (据 output_ranks 锚点; 无则默认)
│       ├── s7_produce.py           单模型 × 3 rollout 跑 agent 产交付物 (并发; 记 path 与 trace)
│       └── s8_grade.py             跨家族 grader 按 rubric+answer_key 打分, 每 query 标 best (并发)
│
├── scripts/
│   ├── crawl_more.py       定向补爬公开机构 PDF (ECB Bulletin/BIS/Fed FSR&MPR/Fed 监管报告), 重建 CORPUS.json
│   └── run_from_s3.sh      S1/S2 完成后一键续跑 S3→emit; 参数=S7 处理的 query 数上限
│
├── data/                  ── 语料与 S1 产物 (均在 .gitignore) ──
│   ├── corpus/             原始 PDF + CORPUS.json 清单 (本地为软链; 用 crawl_more.py 重建)
│   ├── cleaned/            S1 产: <doc_id>.json (reference 数据层 + 元信息)
│   └── answer_keys/        S1 产: <doc_id>.md (隐藏结论锚点)
│
├── outputs/               ── 产物 (在 .gitignore) ──
│   ├── bundles.jsonl       S2 产: 每个 bundle 的领域/成员文件/支持的交付物类型
│   ├── queries.jsonl       S3 产 (含 S4 写入的 qc 结果)
│   ├── queries_passed.jsonl S4 通过的 query
│   ├── rubrics.jsonl       S5 产: 每条 query 的 rubric
│   ├── deliverables.jsonl  S7 产: 每份交付物的路径/模型/trace
│   ├── scores.jsonl        S8 产: 每份交付物的分数/维度分/best
│   ├── items.jsonl         【最终成品】GDPval schema 超集, 每行一条 case
│   ├── deliverable_files/<query_id>/<model>_<r>/  交付物文件 + _trace.json (agent 过程)
│   └── reference_files/<hash>/                     emit 复制的参考文件
│
└── tests/                 (占位; 单测待补)
```

---

## 三、安装

```bash
# 1) 建环境
conda create -n fingdpval python=3.12 -y && conda activate fingdpval

# 2) 装依赖
pip install -r requirements.txt
```

`requirements.txt` 关键依赖（开发验证版本）：`torch 2.9.1(+cu129)`、`transformers 4.57`、
`sentence-transformers 5.6`（本地 embedding）、`pymupdf 1.28`（PDF 抽取）、`requests`、`pyyaml`、`numpy`、
`pandas`、`openpyxl`（xlsx）、`python-docx`（docx）、`weasyprint`（pdf, 需系统库 pango/cairo）、`reportlab`（pdf 兜底）、
`matplotlib`、`jinja2`。

```bash
# 3) 下载本地 embedding 权重 (S2 近邻成组用; ~1.2GB)
python -c "from huggingface_hub import snapshot_download; \
  snapshot_download('Qwen/Qwen3-Embedding-0.6B', local_dir='models/Qwen3-Embedding-0.6B')"
# 然后把 config/models.yaml 的 embedding.model 指向该路径
```

---

## 四、配置（跑起来要设什么）

1. **API key** — 复制 `.env.example` 为 `.env`，填入真实 key：
   ```bash
   cp .env.example .env       # 然后编辑 .env
   ```
   `.env` 已被 `.gitignore` 忽略。key 名与 `config/models.yaml` 各 provider 的 `api_key_env` 对应。

2. **模型端点/角色** — `config/models.yaml`：
   - `providers.*`：各模型的 `base_url` / `model` / `api_key_env`（GLM、DeepSeek 均 OpenAI 兼容；Gemini/GPT 注释待启用）。
   - `roles`：`author`（管线内 LLM 步）、`generators`/`graders`/`qc_candidates` 候选、`arbiter`。
   - `embedding.model`：本地 Qwen3-Embedding 权重路径。

3. **领域与规模** — `config/domains.yaml`（唯一真相源）：领域列表、每领域职业轴、交付物类型、
   S2 成组阈值 `min_similarity`、S7 `rollout.n_per_query` 与候选、xlsx 上限等。

4. **路径与并发** — `config/pipeline.yaml`：语料/产物路径、各阶段并发 `workers`、partition 段落上限、agent 沙箱参数。

5. **语料** — 把 PDF 放进 `data/corpus/<source>/` 并生成 `data/corpus/CORPUS.json`（可用 `scripts/crawl_more.py`
   补爬公开机构报告；或自备）。每条清单项建议带显式 `domain`。

---

## 五、运行

```bash
cd final
export PYTHONPATH=src

# 全量 (从原始语料到成品)
python -m cli s1                 # 切分/清洗
python -m cli s2                 # 近邻成组
python -m cli s3                 # query 生成
python -m cli s4                 # 质检
python -m cli s5                 # rubric 生成
python -m cli s7 --limit 20      # 交付物生成 (前 20 条 query)
python -m cli s8                 # 打分
python -m cli emit               # 落盘 items.jsonl

# 便捷: S1/S2 已完成时一键续跑 S3→emit
bash scripts/run_from_s3.sh 20   # 参数 = S7 处理的 query 数上限
```

S1/S2 支持**续跑**（已处理的文档自动跳过），中断可直接重跑。

---

## 六、输出格式

`outputs/items.jsonl` 每行一条 case，对齐 **GDPval schema** 并加超集字段：

```jsonc
{
  "task_id": "…", "domain": "sovereign", "occupation": "country_desk_economist",
  "deliverable_type": "prose_md",
  "prompt": "You are an IMF country desk economist …",   // 完整任务 (含多子任务/格式要求)
  "reference_files": ["outputs/reference_files/<hash>/<doc>.md", …],  // solver 输入 (数据层)
  "deliverable_files": ["…/deepseek_0/X.md", "…/deepseek_1/X.md", "…/deepseek_2/X.md"],  // 3 份 rollout
  "rubric_pretty": "[+1] …\n[+2] …",                     // 人读版
  "rubric_json": [{"score":2,"criterion":"…","kind":"objective|judgment|gdpval_dim", …}],
  // ---- 超集字段 ----
  "answer_key_refs": ["data/answer_keys/<doc>.md", …],   // 隐藏结论锚点 (不进 solver 输入)
  "qc": {"gates": {8 项 0/1}, "passed": true},
  "scores": [{"generator":"deepseek","total":36.0,"max_score":40,"grader_model":"glm", …}],
  "best_idx": 2                                          // 最佳交付物下标
}
```

---

## 七、当前状态与已知限制

**端到端已跑通并产出成品**：S1–S8 全段实测；首批样本验证了「真实任务 → 结构化 rubric → 单模型 ×3 → 跨家族打分(分数有区分度) → best 标定」全链路。

**已知限制 / 路线图**：
- **语料抽取**：Fed/ECB 报告的数值多在图表里，pymupdf 只抽出叙述文字，导致数值型任务的可解性质检通过率偏低
  （世行国别报告含内联表格，通过率高）。改进：query-gen 按参考内容出题（叙述源出定性任务）、结构化抽取真表格。
- **cross_border 领域**：公开渠道语料受阻（IMF Cloudflare、BIS 统计非报告式 PDF），当前无料。
- **专家锚点**：`expert_anchor/*.jsonl` 现为空；补齐后启用 QC/generator/grader 的一致性选型。
- **跨家族评分**：补 GPT/Gemini key 后评分更强、更中立。
- **agent 稳定性**：少数交付物触多轮上限未完成；可调 `pipeline.yaml` 的 `agent.max_turns` 或优化提示。
- **沙箱**：pilot 为子进程 + denylist（非强隔离）；生产建议接 Docker。
- **单测**：`tests/` 待补。

> 设计取舍与逐步决策的完整记录见 git 历史。本管线为训练集生产而设计，产物是 `(task, reference, rubric,
> 交付物, 分数)` 超集，下游可自取用于 SFT / 拒采 / RL / 奖励模型。
