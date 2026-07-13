# 银行体系稳健性评估与同业对标任务的编写

## 本领域职业、真实产物与典型数据形态
- `bank_credit_analyst` 银行信用分析师 — 产物：**银行体系稳健性评估**、**同业对标（peer benchmarking）**。数据形态：EBA Risk Dashboard 式的国别 KRI 面板（CET1、NPL、coverage、LCR、NSFR、ROE、cost/income、loan-to-deposit 的逐季序列，附国别离散度与分位）。
- `prudential_supervisor` 监管审查员（EBA/SSM/Fed/FDIC）— 产物：**监管审查备忘**、**CAMELS/SREP 式评估**。数据形态：某一银行体系或代表性机构的资本、资产质量、盈利、流动性指标，以及压力测试的起点与不利情景结果。
- `bank_equity_research` 银行股票研究员 — 产物：**行业信用与盈利研报**。数据形态：盈利拆解（NII、NIM、手续费收入、cost of risk、PPNR、RoRWA）、资本回报与派息空间（ROE、CET1 相对目标、buffer to MDA）。
- `asset_quality_analyst` 资产质量与拨备分析师 — 产物：**不良与拨备覆盖分析**。数据形态：NPL/NPE、IFRS 9 Stage 1/2/3（或 FDIC 口径的 noncurrent、past-due 30–89、90+）、coverage、cost of risk、net charge-off，以及按行业或组合（CRE、住房按揭、消费、SME）的敞口。

## 术语与口径（须使用行业术语，口径准确，不得混用）
**资本（Capital）**：CET1 ratio = 普通股一级资本 / RWA；Tier1、Total capital ratio；杠杆率 LR = Tier1 / 敞口计量（Basel III 下限 3%）；RWA density = RWA / 总资产。缓冲栈：CCoB 2.5% + CCyB + G-SII/O-SII/SyRB = combined buffer；**OCR = Pillar1（8%）+ P2R + combined buffer**；**buffer/headroom to MDA** = 实际 CET1 − CET1 总要求（跌入缓冲区触发 MDA 分红限制）。美国口径：**SCB（压力资本缓冲）** = max(2.5%, 严重不利情景 CET1 峰谷跌幅 + 4 季分红)。
**资产质量（Asset quality）**：NPL/NPE ratio = 不良 / 总贷款；**coverage ratio = 拨备 / 不良**；**cost of risk（CoR）** = 减值计提 / 总贷款（年化，bps）；net charge-off（NCO）rate = 净核销 / 平均贷款；forbearance ratio；IFRS 9 **Stage 2 占比**（信用风险显著上升的预警）；美式口径：noncurrent = 逾期 90+ 或非应计，**reserve coverage = ALLL/ACL / noncurrent**，**Texas ratio =（不良 + OREO）/（有形普通股权益 + 贷款损失准备）**。
**盈利（Profitability）**：ROE、ROA/RoAA、**NIM = 净利息收入 / 平均生息资产**；**cost/income（效率比）**；RoRWA；**PPNR（拨备前净收入）**（压力测试关键指标）；生息资产收益率与负债成本。
**流动性与融资（Liquidity/Funding）**：**LCR = HQLA / 30 天净现金流出（≥100%）**；**NSFR = 可用稳定资金 / 所需稳定资金（≥100%）**；loan-to-deposit（LTD）；资产质押率（asset encumbrance）；**未保险存款占比**、无息存款占比（SVB 事件后的重点关注项）。
**敏感性（Sensitivity）**：IRRBB、EVE / NII 敏感性、AFS/HTM **证券未实现损益**（利率上行时对资本的隐性侵蚀）。
**监管与压力测试（Supervisory & Stress）**：CAMELS（1–5，1 最好）；SREP score（1–4）；IMF FSAP/FSSA 的 **FSIs** 及偿付与流动性压力测试；EBA EU-wide stress test（静态资产负债表、3 年期、baseline vs adverse，起点 CET1 至不利情景 CET1 谷值与 depletion）；美国 CCAR/DFAST。

## 交付物的惯用结构（可在任务中点名要求）
- **稳健性评估 / SREP 式**：① 资本充足（水平、趋势、buffer to MDA、压力后 CET1）；② 资产质量（NPL、coverage、CoR、Stage 2、组合集中度）；③ 盈利（ROE 相对 COE、NIM、cost/income、盈利质量与可持续性）；④ 流动性与融资（LCR、NSFR、LTD、存款结构）；⑤ 综合判断、评级与关注项。
- **同业对标**：以加权平均（EBA 报告口径）为基准，给出目标体系或机构相对中位数、四分位与 5–95 分位的**分位位置**，并解释离散原因（不应仅罗列数字而不作解读）。
- **不良与拨备分析**：NPL 迁徙与流量（新增、化解、核销）、按组合的不良与 coverage、CoR 走势与拨备充足性判断、前瞻分析（Stage 2 至 Stage 3 迁徙、宏观情景敏感性）。

## 领域示例（仅示范风格，请勿照搬内容）
**示例 A（asset_quality_analyst · data_xlsx）**：
> 「你是一家欧洲投行的资产质量分析师。基于所附 EBA Risk Dashboard 的国别 KRI 面板（含 12 个欧盟成员国最近 8 个季度的 NPL ratio、coverage ratio、cost of risk 与 Stage 2 占比），为信用委员会准备一份对标工作簿。① 计算各国最新季度 NPL 与 coverage 的加权平均与四分位，标出每国所处分位；② 计算各国 NPL 的 8 季变动（bps）与 coverage 的同期变动，识别资产质量**恶化最快**的三个体系；③ 以 cost of risk 与 Stage 2 占比交叉判断，评估哪些体系的拨备可能不足以覆盖前瞻性迁徙。输出名为 `AssetQuality_Benchmark.xlsx`，含 `Data`、`Ranking`、`Summary` 三个工作表。」
> 该示例的子任务覆盖取数、计算分位与变动、交叉判断、成文；格式要求点名文件名与三个工作表。

**示例 B（prudential_supervisor · prose_pdf）**：
> 「你是 FDIC 的审查员。基于所附 Quarterly Banking Profile 的行业汇总数据（按资产规模分层的 ROA、NIM、noncurrent loan rate、net charge-off rate、reserve coverage、AFS/HTM 未实现损失、problem bank 数与 DIF reserve ratio），撰写一份 4–6 页的行业稳健性审查简报。要求覆盖资本、资产质量、盈利、流动性四支柱与利率敏感性，并按 CAMELS 框架给出对社区银行分层的关注等级及理由。输出一份 PDF。」

## 常见易错情形与泄漏风险（编写任务时须规避）
- **不得将结论写入题干**：不应出现「资本充足」「资产质量恶化」「评级下调」「拨备不足」等方向性判断或 CAMELS/SREP 评分——这些结论应由完成者自行得出。
- **不得要求材料之外的私有数据**：单笔贷款级明细、内部评级迁徙矩阵、逐笔敞口、管理层指引、未公开的监管评分等。公开语料（EBA/FDIC/IMF/压测摘要）仅含汇总、国别或机构级指标；要求上述数据会使任务不可解。
- **口径须能从数据算出**：若任务要求 buffer to MDA 或压力后 CET1，参考材料必须含 P2R、缓冲要求或压测不利情景结果，否则不可解。
- **对标须有基准来源**：同业对标的分位与加权平均必须能从所给面板算出，不应假设一个外部行业均值。
