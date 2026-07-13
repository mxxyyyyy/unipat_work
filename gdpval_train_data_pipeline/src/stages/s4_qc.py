"""
S4 · 质检 (8 项二值硬门槛, 全 pass 才留)
- select_qc_model: 若有 expert_anchor/qc_labels.jsonl, 选与锚点一致性最高的候选模型; 否则用 author。
- score: 逐题 8 门槛 0/1; QCResult.finalize() 全 1 才 passed。

产出:
  outputs/queries.jsonl        (原地加 qc 字段)
  outputs/queries_passed.jsonl (仅通过)
"""
from __future__ import annotations
from pathlib import Path

import util
import schema
from providers import base

ANCHOR = util.ROOT / "expert_anchor" / "qc_labels.jsonl"


def _to01(v) -> int:
    """把模型返回的门槛值稳健地归一到 0/1 (容 '1'/'yes'/true/1.0 等)。"""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return 1 if v >= 1 else 0
    s = str(v).strip().lower()
    return 1 if s in ("1", "true", "yes", "y", "pass", "通过") else 0


def _qc_once(provider, q: dict) -> schema.QCResult:
    domain = q["domain"]
    sys_prompt = util.load_prompt("qc", domain)
    ref = util.bundle_reference(q["reference_files"])
    key = util.bundle_answer_key(q["reference_files"])
    user = (
        f"领域: {domain} | 职业: {q['occupation']} | 交付物: {q['deliverable_type']}\n\n"
        f"[任务 prompt]\n{q['prompt']}\n\n[子任务]\n" + "\n".join(q.get("subtasks", [])) +
        f"\n\n[format_spec]\n{q.get('format_spec','')}\n\n"
        f"[reference 数据]\n{ref}\n\n[answer_key 隐藏结论(对照查泄漏/可解)]\n{key}\n\n"
        f"逐项判 8 门槛 0/1 + reasons。只输出 JSON。"
    )
    out = provider.chat_json(
        [{"role": "system", "content": sys_prompt},
         {"role": "user", "content": user}],
        schema=schema.QC_SCHEMA, temperature=0.0)
    gates = {g: _to01(out.get("gates", {}).get(g, 0)) for g in schema.QC_GATES}
    return schema.QCResult(query_id=q["query_id"], gates=gates,
                           reasons=out.get("reasons", {}),
                           grader_model=provider.name).finalize()


def select_qc_model() -> str:
    """用锚点选一致性最高的候选 QC 模型。无锚点 -> author。"""
    cands = util.cfg("models")["roles"]["qc_candidates"]
    anchors = {r["query_id"]: r for r in util.read_jsonl(ANCHOR)}
    if not anchors:
        author = util.cfg("models")["roles"]["author"]
        print(f"[S4] 无 qc_labels 锚点, 暂用 author={author} 做 QC (选型待锚点)。")
        return author
    queries = {q["query_id"]: q for q in util.read_jsonl(util.path("queries"))}
    best, best_agree = None, -1.0
    for cand in cands:
        prov = base.get_provider(cand)
        agrees = []
        for qid, a in anchors.items():
            q = queries.get(qid)
            if not q:
                continue
            try:
                pred = _qc_once(prov, q)
            except Exception as e:
                print(f"  [S4-select] {cand} {qid} 失败: {e}")
                continue
            a_gates = a.get("gates", {})
            match = sum(1 for g in schema.QC_GATES
                        if _to01(pred.gates.get(g, 0)) == _to01(a_gates.get(g, 0))) / len(schema.QC_GATES)
            agrees.append(match)
        agree = sum(agrees) / len(agrees) if agrees else 0.0
        print(f"[S4] 候选 QC 模型 {cand}: 与锚点一致性 = {agree:.3f} (n={len(agrees)})")
        if agree > best_agree:
            best, best_agree = cand, agree
    print(f"[S4] 选定 QC 模型: {best} (一致性 {best_agree:.3f})")
    return best


def run(model=None, limit=None):
    qc_model = model or select_qc_model()
    provider = base.get_provider(qc_model)
    queries = util.read_jsonl(util.path("queries"))
    if limit:
        queries = queries[:limit]

    def _qc(q):
        try:
            res = _qc_once(provider, q)
        except Exception as e:                        # noqa
            print(f"  [S4] {q['query_id']} QC 失败: {e}")
            q["qc"] = {"passed": False, "error": str(e)}
            return q
        q["qc"] = res.__dict__
        fails = [g for g in schema.QC_GATES if res.gates[g] == 0]
        print(f"  [S4] {q['query_id']} [{'PASS' if res.passed else 'reject'}]"
              + (f" fails={fails}" if fails else ""))
        return q

    workers = util.cfg("pipeline").get("qc", {}).get("workers", 8)
    queries = util.pmap(_qc, queries, workers=workers)
    passed = [q for q in queries if q.get("qc", {}).get("passed")]

    util.write_jsonl(util.path("queries"), queries)
    passed_path = util.path("queries").parent / "queries_passed.jsonl"
    util.write_jsonl(passed_path, passed)
    print(f"[S4] {len(passed)}/{len(queries)} 通过 -> {passed_path}")
    return passed
