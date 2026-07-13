"""
S5 · Rubric 生成
对通过质检的 query: query + reference + answer_key -> GDPval 累加式 rubric
(objective 客观项 + judgment 判断项(answer_key 软支撑) + gdpval_dim 维度项 + required 守门)。

产出: outputs/rubrics.jsonl  (Rubric)
"""
from __future__ import annotations

import util
import schema
from providers import base


def _author():
    return base.get_provider(util.cfg("models")["roles"]["author"])


def gen_one(provider, q: dict) -> schema.Rubric:
    domain = q["domain"]
    sys_prompt = util.load_prompt("rubric_gen", domain)
    ref = util.bundle_reference(q["reference_files"])
    key = util.bundle_answer_key(q["reference_files"])
    user = (
        f"领域: {domain} | 职业: {q['occupation']} | 交付物: {q['deliverable_type']}\n\n"
        f"[任务 prompt]\n{q['prompt']}\n\n[子任务]\n" + "\n".join(q.get("subtasks", [])) +
        f"\n\n[format_spec]\n{q.get('format_spec','')}\n\n"
        f"[reference 数据]\n{ref}\n\n[answer_key 专家结论(judgment 项软锚点)]\n{key}\n\n"
        f"产出 rubric。覆盖每个子任务; 三类条目都要有; 三大失败模式各设 required 守门。只输出 JSON。"
    )
    out = provider.chat_json(
        [{"role": "system", "content": sys_prompt},
         {"role": "user", "content": user}],
        schema=schema.RUBRIC_SCHEMA, temperature=0.3, max_tokens=16000)  # 思考模式会占额度, 给足输出

    items = []
    for i, it in enumerate(out.get("items", [])):
        try:
            score = int(it["score"])
        except Exception:
            continue
        items.append(schema.RubricItem(
            rubric_item_id=f"{q['query_id']}_r{i}",
            score=score, criterion=it.get("criterion", ""),
            kind=it.get("kind", "objective"),
            gdpval_dim=it.get("gdpval_dim"),
            anchor_ref=it.get("anchor_ref"),
            required=bool(it.get("required", False))).__dict__)
    rub = schema.Rubric(query_id=q["query_id"], items=items,
                        max_score=sum(x["score"] for x in items))
    return rub


def run(limit=None):
    provider = _author()
    passed_path = util.path("queries").parent / "queries_passed.jsonl"
    queries = util.read_jsonl(passed_path)
    if limit:
        queries = queries[:limit]

    def _rub(q):
        try:
            rub = gen_one(provider, q)
        except Exception as e:                        # noqa
            print(f"  [S5] {q['query_id']} rubric 失败: {e}")
            return None
        if not rub.items:                             # 空 rubric 视为失败, 不落盘
            print(f"  [S5] {q['query_id']} rubric 为空, 跳过")
            return None
        d = rub.__dict__.copy()
        d["rubric_pretty"] = rub.render_pretty()
        kinds = {}
        for it in rub.items:
            kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
        print(f"  [S5] {q['query_id']} -> {len(rub.items)} 条 (max={rub.max_score}) kinds={kinds}")
        return d

    workers = util.cfg("pipeline").get("grading", {}).get("workers", 8)
    rubrics = [r for r in util.pmap(_rub, queries, workers=workers) if r]

    util.write_jsonl(util.path("queries").parent / "rubrics.jsonl", rubrics)
    print(f"[S5] 完成 {len(rubrics)} rubrics")
    return rubrics
