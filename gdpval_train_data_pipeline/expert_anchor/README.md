# expert_anchor/ — 专家锚点（选型的真值基准）

管线的两处选型（S4 选质检模型、S6 选 output/grader 模型）都靠「与专家标注的一致性」。本目录放**专家真值标注**，
**真人专家可直接覆盖目录下两个 `.jsonl`**，

抽样量默认每领域 10 条（见 `config/domains.yaml` 的 `sampling`）。

---

## 1. `qc_labels.jsonl` — 质检基准（选 S4 质检模型用）

每行 = 对**一条 query** 按 8 项硬门槛给出的专家真值判定（0/1）+ 理由。字段：

```jsonc
{
  "query_id": "4783b0dc3c092aa7",
  "gates": {                       // 8 项硬门槛，各 0 或 1
    "solvable": 0, "zero_leakage": 1, "on_domain": 1, "has_deliverable": 1,
    "non_trivial": 1, "unambiguous": 1, "representative": 1, "coherent": 1
  },
  "reasons": { "solvable": "……为何判 0/1……", "...": "..." }   // 逐项理由（可只写关键项）
}
```

- `query_id` 对应 `outputs/queries.jsonl` 里的 id。
- 8 门槛定义见 `config/domains.yaml` 的 `qc_hard_gates`。
- **示例中的 `4783b0dc` 是一个「专家与质检模型不一致」的案例**：模型判 `solvable=1`，但该任务要求提取具体通胀率并拆分核心分项，
  而 Fed/ECB 报告的这些数值在图表里、从 PDF 抽出的叙述文本并不含——专家判 `solvable=0`。**这类分歧正是锚点的价值**：
  据它选出更严格、更贴合专家的质检模型。

**怎么用**：候选质检模型对这批 `query_id` 各自打 8 门槛 → 与本文件逐门槛比一致率 → 选一致率最高者做全量质检。

---

## 2. `output_ranks.jsonl` — 交付物排序基准（选 S6 的 output/grader 模型用）

每行 = 对**一条 query 的多份候选交付物**的专家盲排序 + 两两比较 + 理由。字段：

```jsonc
{
  "query_id": "f5b3e3a775663582",
  "ranking": ["bc4aace3b58b2f94", "846e9ca2332de6f6", "e585aab278d1eb6a"],  // 交付物 id 从优到劣
  "pairwise": [ {"a": "…", "b": "…", "winner": "…", "reason": "…"} ],        // 关键两两比较
  "reasons": { "bc4aace3b58b2f94": "为何最佳……", "...": "..." }
}
```

- `query_id` 与各 `deliverable_id` 对应 `outputs/deliverables.jsonl` / `outputs/items.jsonl`。
- 示例是哈萨克斯坦 Article IV 简报的 3 份 rollout：专家排序据**结构完整度 + 篇幅是否贴合 1500-2500 词要求 + 分析质量**，
  最佳一份并非最长的那份（最长的超篇幅、指令遵循欠佳）。

**怎么用**：
- 选 **output 模型**：各候选模型产同一批交付物 → 按本排序比其平均名次 → 选最优。
- 选 **grader 模型**：各候选 grader 对这批交付物打分并排序 → 与本排序比一致性 → 选最一致者。

---

## 生成/更新

- 真人专家：直接编辑/覆盖这两个 `.jsonl` 即可（格式同上），管线自动用此标注。
