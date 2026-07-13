"""
S7 · 批量生产交付物 (多轮 agent + 沙箱)
每个通过质检且有 rubric 的 query, 每个 generator 跑 per_generator 次 -> 共 6 份/query。
全部记录 path (含失败: path=None)。

产出:
  outputs/deliverable_files/<query_id>/<gen>_<r>/...
  outputs/deliverables.jsonl
"""
from __future__ import annotations
from pathlib import Path

import util
import schema
from providers import base
from agent import loop


def _selected_generator(roll) -> str:
    """S7 用**单个**选定的 output 模型 (S6 选出); 无选型结果则用默认。"""
    import json
    ms = util.path("items").parent / "model_select.json"
    if ms.exists():
        sel = json.loads(ms.read_text()).get("selected_generator")
        if sel:
            return sel
    return roll.get("default_generator") or util.cfg("models")["roles"]["generators"][0]


def run(limit=None, generator=None):
    roll = util.cfg("domains")["rollout"]
    pcfg = util.cfg("pipeline")["agent"]
    gen = generator or _selected_generator(roll)      # 单个 output 模型
    per = roll["n_per_query"]
    temp = roll.get("temperature", 0.9)
    print(f"[S7] output 模型 = {gen} (每 query {per} 份)")

    rubric_qids = {r["query_id"] for r in util.read_jsonl(util.path("queries").parent / "rubrics.jsonl")}
    queries = [q for q in util.read_jsonl(util.path("queries").parent / "queries_passed.jsonl")
               if q["query_id"] in rubric_qids]
    if limit:
        queries = queries[:limit]

    base_out = util.path("deliverable_files")
    workers = util.cfg("pipeline")["agent"].get("workers", 8)

    tasks = [(q, gen, r) for q in queries for r in range(per)]  # 单模型 × n_per_query

    def _one(task):
        q, gen, r = task
        provider = base.get_provider(gen)
        out_dir = base_out / q["query_id"] / f"{gen}_{r}"
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            res = loop.run_agent(
                provider, q, str(out_dir), max_turns=pcfg["max_turns"], temperature=temp,
                timeout=pcfg["sandbox"]["timeout_sec"], mem_mb=pcfg["sandbox"]["mem_mb"])
        except Exception as e:                       # noqa
            res = {"deliverable_path": None, "turns": 0, "trace": [{"error": str(e)}]}
        trace_path = out_dir / "_trace.json"
        util.write_jsonl(trace_path, res.get("trace", []))
        ok = "OK " + Path(res["deliverable_path"]).name if res.get("deliverable_path") else "FAIL"
        print(f"[S7] {q['query_id']} {gen}#{r} -> {ok} ({res.get('turns')}t)")
        return schema.Deliverable(
            deliverable_id=schema.stable_id(q["query_id"], gen, str(r)),
            query_id=q["query_id"], generator=gen, rollout_idx=r,
            deliverable_type=q["deliverable_type"], path=res.get("deliverable_path"),
            agent_trace_path=str(trace_path)).__dict__

    deliverables = util.pmap(_one, tasks, workers=workers)
    util.write_jsonl(util.path("queries").parent / "deliverables.jsonl", deliverables)
    got = sum(1 for d in deliverables if d["path"])
    print(f"[S7] 完成 {got}/{len(deliverables)} 份交付物")
    return deliverables
