本项目把 [GDPval](https://openai.com/index/gdpval/)(评测 AI 在真实、经济价值知识工作上的能力)落到**国际金融/开放宏观**领域,产出 **GDPval 风格**的高价值任务数据。它由**两部分**组成:

| 目录 | 是什么  |
|---|---|
| **`gdpval_train_data_pipeline/`** | 自动化**训练数据生产管线**  |
| **`GDPval_evaluation_query/`** | 一道**手写的 GDPval 评测样例** |

---

# 一、`gdpval_train_data_pipeline/` — 训练数据生产管线

从真实金融文档出发,自动生产 GDPval 风格数据:每条样本 = **任务(query) + 参考文件 + 评分细则(rubric) + 若干份带分交付物**。

> 管线把爬取的金融报告切成「**数据(输入) + 结论(隐藏答案锚点)**」,用数据做参考、用领域专家 prompt 生成多子任务 query,经 **8 项硬门槛质检**后,用切出的结论当 answer-key 生成**可客观打分**的 rubric,再用**多轮 agent + 沙箱**让模型产出多格式交付物(md/pdf/docx/xlsx),最后由**跨家族 grader** 参照 rubric 与 answer-key 打分。

## 1.1 方法:8 个阶段(S1→S8 + emit)

```
S1 partition   每篇报告切三层: 数据 / 分析 / 结论
               → 数据层作 reference(solver 输入); 分析+结论作 answer_key(隐藏, 仅评分用)
S2 grouping    领域内近邻成组: 每文档 + 阈值内最近邻(≤3)组成多文件 bundle(本地 Qwen3 embedding)
S3 query_gen   bundle × 交付物类型 → 一条 GDPval 式 query(领域专家 prompt: 真实职业/产物/多子任务/格式)
S4 qc          8 项二值硬门槛, 全过才留(可解 / 零泄漏 / 在领域 / 有交付物 / 非trivial / 无歧义 / 真实 / 贯通)
S5 rubric_gen  query + reference + answer_key → 累加式 rubric(客观项 + answer_key 支撑的判断项 + GDPval 维度项)
S6 model_select 从候选里选**最优单个** output 模型(据专家锚点一致性; 无锚点用默认)
S7 produce     多轮 agent + 沙箱: 选定单模型每 query 产 3 份交付物(md/pdf/docx/xlsx)
S8 grade       跨家族 grader 参照 rubric + answer_key 打分, 记 path+分, 标 best
emit           汇总为 GDPval schema 超集 items.jsonl
```

## 1.2 三个关键设计点

1. **剥掉的结论 = 免费 gold**:S1 把报告自己的分析与结论从输入中剥出、单独存为隐藏 `answer_key`,当 rubric 判断项的真值锚点——**解决"无 gold 时判断型评分无法验证"的循环,无需人工写 gold**。
2. **近邻成组替代检索扩充**:在**已剥结论**的数据上做 embedding 近邻成组(绝对余弦阈值,可调),天然不泄漏;产出重叠的多文件 bundle,支持**跨文档多材料**任务。
3. **跨家族 grader 防自偏好**:generator 与 grader 强制不同模型家族(GDPval 明确指出模型偏爱自己的输出);多 grader 时取平均并标分歧,超阈值 Claude 仲裁。

> 注:GDPval 头条评分是**盲配对人评**(非 rubric);本管线为训练集需要改用 **rubric + answer-key 锚点**,是有意的偏离。

## 1.3 目录结构(要点)

```
gdpval_train_data_pipeline/
├── config/          三个 yaml: domains.yaml(唯一真相源: 5领域/职业轴/交付物类型/8门槛/评分维度/成组参数)
│                    · models.yaml(provider适配+角色分配+本地embedding) · pipeline.yaml(路径/并发/沙箱/打分)
├── prompts/         领域专家 prompt(每 stage: _shared 骨架 + 各领域文件): partition / query_gen / qc /
│                    rubric_gen / output_agent / grader / expert_anchor(锚点标注指令)
├── expert_anchor/   专家锚点(选型真值基准): qc_labels / output_ranks + README; 已放示例 case, 真人可覆盖
├── src/
│   ├── util.py schema.py cli.py emit.py    配置/prompt拼接/PDF抽取 · 数据契约 · CLI · 汇总emit
│   ├── providers/   可插拔 LLM/embedding: base(OpenAI兼容) · glm(GLM-5.2) · deepseek(v4-pro) · embedding(本地Qwen3)
│   ├── agent/       S7 多轮 agent: loop(规划→python_exec→自检→finish) · tools(read/exec/write/finish) · sandbox(子进程+超时+denylist)
│   └── stages/      s1_partition … s8_grade(八阶段实现)
├── scripts/         crawl_more.py(补爬 ECB/BIS/Fed 公开PDF) · run_from_s3.sh(S3→emit 一键续跑)
├── data/            corpus(原始PDF+CORPUS.json) · cleaned(S1 reference) · answer_keys(S1 隐藏结论) 〔.gitignore〕
├── outputs/         bundles/queries/queries_passed/rubrics/deliverables/scores.jsonl · items.jsonl〔最终成品〕
│                    · deliverable_files/<query>/<model>_<r>/ · reference_files/<hash>/ 〔.gitignore〕
├── README.md        本管线详细说明(本项目 README 已吸收其要点)
└── requirements.txt / .env.example / .gitignore
```

## 1.4 安装 · 配置 · 运行

```bash
cd gdpval_train_data_pipeline
pip install -r requirements.txt
# 关键依赖: torch/transformers/sentence-transformers(本地embedding) · pymupdf(PDF) · openpyxl/python-docx/weasyprint/reportlab(交付物) · pyyaml/numpy/pandas
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-Embedding-0.6B', local_dir='models/Qwen3-Embedding-0.6B')"  # S2 用, ~1.2GB

cp .env.example .env        # 填 API key(名字对应 models.yaml 各 provider 的 api_key_env)
# 按需改 config/{domains,models,pipeline}.yaml; 语料放 data/corpus/<source>/ + CORPUS.json

export PYTHONPATH=src
python -m cli s1 && python -m cli s2 && python -m cli s3 && python -m cli s4 \
  && python -m cli s5 && python -m cli s7 --limit 20 && python -m cli s8 && python -m cli emit
# 便捷: S1/S2 已完成时  bash scripts/run_from_s3.sh 20   (参数=S7 处理的 query 数上限)
```

S1/S2 支持**续跑**(已处理文档自动跳过)。

## 1.5 输出格式(`outputs/items.jsonl`,GDPval schema 超集)

```jsonc
{ "task_id","domain","occupation","deliverable_type",
  "prompt",                         // 完整职场任务(含多子任务/格式要求)
  "reference_files":[...],          // solver 输入(数据层)
  "deliverable_files":[...×3],      // 单模型 3 份 rollout
  "rubric_pretty","rubric_json":[{"score","criterion","kind":"objective|judgment|gdpval_dim"}],
  // 超集: "answer_key_refs"(隐藏结论锚点) "qc"{8门槛,passed} "scores"[{generator,total,grader_model}] "best_idx" }
```

## 1.6 当前状态与已知限制

**端到端已跑通**:S1–S8 全段实测,已产出 **6 条成品 items**(22 bundles → 34 queries → 6 过质检 → 6 rubrics → 18 交付物(6×3)→ 18 分数),验证了「真实任务 → 结构化 rubric → 单模型×3 → 跨家族打分(有区分度)→ best 标定」全链路。

**专家选型锚点(已提供示例)**: `expert_anchor/` 已放示例 `qc_labels.jsonl`(质检 8 门槛真值; 含一个「专家与质检模型判定不一致」的案例) 与 `output_ranks.jsonl`(交付物盲排序真值) 及 README 格式说明。填满每领域抽样(默认 10 条/领域)后, S4 据「与专家一致性」选质检模型、S6 据此选 output/grader 模型。**当前尚未做正式选型**(默认: QC 用 author 模型、output 用默认单模型、grader用单模型)。

---

# 二、`GDPval_evaluation_query/` — 手写 GDPval 评测样例

一道**专家手工精修**的 GDPval 式评测 case:**《2026 全球共封装光学(CPO)行业投资策略》正式投研报告**。

## 2.1 结构

```
GDPval_evaluation_query/
├── items.jsonl                 一条 GDPval 超集 case(task_type=INVESTMENT_STRATEGY)
├── reference_files/            7 份输入材料:
│   ├── cpo_investment_strategy_context.md   任务背景
│   ├── 01_hyperscaler_capex.csv             四大云厂 capex(SEC EDGAR 实抓, 可验)
│   ├── 02_us_optical_comps.csv              美股光通信可比公司财务(SEC, 可验)
│   ├── 03_ashare_optical_financials.csv     A股光模块/光芯片财务(公开年报, best-effort)
│   ├── 04_optical_market_estimates.csv      光模块/CPO 市场估算(第三方, 引用)
│   ├── 05_cpo_tech_roadmap.md               CPO/可插拔/LPO 技术路线
│   └── 06_company_profiles.md               候选股票池 + 受益类型标注
└── deliverable_files/          gold 交付物(真实文件):
    ├── 2026_CPO投资策略报告.docx            正式中文投研报告(96段/13表)
    ├── 2026_CPO投资策略报告.pdf             由 DOCX 导出的一致 PDF(8 页)
    └── cpo_investment_strategy_gold.md      markdown 源
```


---

## 快速导航

- **训练数据生产pipeline** → [`gdpval_train_data_pipeline/`](gdpval_train_data_pipeline/README.md)