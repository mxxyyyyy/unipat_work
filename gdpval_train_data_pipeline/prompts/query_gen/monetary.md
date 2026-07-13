# 货币政策与宏观展望：任务编写的领域指引

## 职业、真实产物与典型数据形态
- **央行研究经济学家（cb_staff_economist）**：货币政策简报、通胀展望。数据形态包括 Fed MPR / ECB Bulletin 中的 PCE 及核心 PCE、HICP 及核心 HICP 分项时间序列（能源、食品、核心商品、核心服务，以及住房与非住房服务），失业率（U-3/U-6）、非农就业、职位空缺（JOLTS、V/U 比）、工资（ECI、AHE、协商工资）、实际 GDP 及分项，以及通胀预期（密歇根调查、SPF、5y5y）。
- **买方宏观策略师（macro_strategist）**：利率路径展望、FOMC/ECB 前瞻。数据形态包括 SEP 点阵图（median / central tendency / range）、政策利率目标区间历史、OIS 与联邦基金期货隐含路径、SOFR/€STR、市场隐含的首次降息时点与全年累计 bp。
- **银行首席经济学家团队（bank_chief_economist）**：宏观季度展望。数据形态包括跨经济体的增长、通胀与政策利率对照表，金融条件指数，信贷与货币总量（M3、对居民及非金融企业信贷），银行放贷调查（SLOOS/BLS）。
- **利率交易台分析师（rates_desk_analyst）**：政策情景与曲线分析。数据形态包括国债收益率曲线（2s10s、3m10y）、期限溢价（ACM）、盈亏平衡通胀（TIPS breakeven）、实际收益率、准备金/RRP/QT runoff 上限。

## 术语与口径（须准确采用，并作为约束写入任务正文）
- **通胀口径**：区分 headline 与 core（Fed 首选 core PCE，ECB 关注 HICP 及核心 HICP）；区分 YoY 与 MoM 折年；关注 3 个月与 6 个月折年 run-rate；辅以截尾均值 PCE（Dallas）、中位数 CPI（Cleveland）；supercore 指核心服务除住房。任务须明确指定所用口径与频率。
- **政策利率**：联邦基金目标区间（上/下界）与 EFFR；ECB 三利率（DFR/MRO/MLF）；terminal rate；中性利率 r\*（longer-run dot 或单独估计）；实际政策利率 = 名义利率 − 通胀预期。
- **利率路径**：以 SEP 点阵图 median 为主要口径；市场隐含路径由 OIS 与期货反推。须明确区分「基线路径」「市场定价」「SEP」三条，不得混同。
- **就业与增长**：U-3/U-6、参与率、非农就业、JOLTS 空缺、V/U 比、辞职率、Sahm rule、NAIRU、产出缺口。
- **反应函数**：Taylor 规则、balanced-approach 规则；Fed 双重使命与 ECB 2% 对称目标；前瞻指引措辞。
- **资产负债表**：QT runoff 上限、准备金充裕度、SOMA、RRP。

## 交付物的惯用结构（据此设定子任务与格式要求）
- **货币政策简报 / 通胀展望（文字类）**：① 一句话政策判断 → ② 通胀评估（分项拆解 + run-rate）→ ③ 就业与增长 → ④ 金融条件 → ⑤ 政策立场与前瞻 → ⑥ 风险平衡（上行/下行）。
- **利率路径展望（文字类 / pdf）**：基线路径、市场隐含路径与 SEP 三方对照 → 情景设定（hawkish / base / dovish，各附触发条件）→ 曲线与期限溢价含义 → 交易与组合含义。
- **政策情景与曲线分析（数据工作簿 xlsx）**：分设「Data」（原始序列）、「Calc」（run-rate、利差、隐含路径）、「Summary」（情景矩阵）等工作表；各列须明确标注口径与单位（bp 或 %）。

## 领域示例（仅示范风格，不得照搬内容）
**示例 A（cb_staff_economist · 文字类 md）**：
> You are a central bank staff economist. Ahead of the next policy round, your division head asks you to draft an internal inflation assessment brief (Markdown, 4-6 sections) using the attached data extract.
> 1. 用月度分项序列，计算并列出 headline 与 core PCE 的最新 YoY，以及 3 个月与 6 个月折年 run-rate；
> 2. 拆解 core 的商品与服务，并单列 supercore（核心服务除住房）的走势；
> 3. 结合失业率、V/U 比与 ECI，评估劳动力市场对服务通胀的传导；
> 4. 给出对通胀动能方向与风险平衡的判断，标注上行/下行风险。
> 交付物：名为 `Inflation_Assessment.md` 的报告，含「摘要 / 通胀分项 / 劳动力市场 / 风险平衡」四节。

**示例 B（rates_desk_analyst · 数据工作簿 xlsx）**：
> You are a rates desk analyst. The desk needs a scenario workbook before the meeting.
> 1. 从收益率序列计算 2s10s、3m10y 利差及其近 3 个月变动（bp）；
> 2. 由 OIS 序列反推市场对下次会议及年末的隐含政策利率；
> 3. 构建 base / hawkish / dovish 三情景（各给触发条件与对应 terminal），并映射到曲线形态含义。
> 交付物：名为 `Rate_Scenarios.xlsx` 的工作簿，含 `Data` / `Calc` / `Scenarios` 三个工作表。

## 常见易错点与泄漏防范
- **泄漏方向判断**：不得在任务中写入「通胀已见顶」「应当降息」「曲线将走陡」等结论；只给出数据与应计算的内容，方向判断留给完成者。
- **给出既成的 SEP 或市场结论**：参考材料只应包含原始序列；不要将「点阵图 median 显示两次降息」这类既成结论写入任务。
- **依赖外部私有数据**：不要求参考材料以外的高频交易数据、非公开会议纪要或尚未公布的未来数值，否则任务不可解。
- **口径悬空**：凡涉及通胀或利率，务必点名口径与频率，否则完成者会各自采用不同口径而产生歧义。
- **流于形式的任务**：仅查取单一数值（如「最新失业率是多少」）属于 trivial，不构成真实任务；真实任务须完整走过「取数 → 计算 run-rate/利差/隐含路径 → 综合判断」的链条。
