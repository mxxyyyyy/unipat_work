"""
emit.py · 汇总落盘为 GDPval schema 超集 items.jsonl
把 passed query + rubric + deliverables + scores 组装成 Item;
把 reference 复制进 outputs/reference_files/<task_hash>/。answer_key 保持隐藏 (仅 ref 路径)。
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

import util
import schema


def run():
    queries = {q["query_id"]: q for q in util.read_jsonl(util.path("queries").parent / "queries_passed.jsonl")}
    rubrics = {r["query_id"]: r for r in util.read_jsonl(util.path("queries").parent / "rubrics.jsonl")}
    delivs = util.read_jsonl(util.path("queries").parent / "deliverables.jsonl")
    scores = util.read_jsonl(util.path("scores"))

    d_by_q, s_by_id = {}, {}
    for d in delivs:
        d_by_q.setdefault(d["query_id"], []).append(d)
    for s in scores:
        s_by_id[s["deliverable_id"]] = s

    idx = util.cleaned_index()
    ref_root = util.path("reference_files")
    items = []
    for qid, q in queries.items():
        rub = rubrics.get(qid)
        if not rub:
            continue
        task_hash = schema.stable_id("task", qid)

        # 复制 reference 文件
        rf_dir = ref_root / task_hash
        rf_dir.mkdir(parents=True, exist_ok=True)
        ref_paths = []
        for fid in q["reference_files"]:
            cd = idx.get(fid)
            if not cd:
                continue
            fp = rf_dir / f"{fid}.md"
            fp.write_text(f"# {cd['title']}\n\n{cd['reference_text']}")
            ref_paths.append(str(fp.relative_to(util.ROOT)))

        # 交付物 + 分数 (保留完整 Score 契约; best_idx 与 S8 的 is_best 一致)
        dfiles, sc_list, best_idx, best_total = [], [], None, -1.0
        for i, d in enumerate(sorted(d_by_q.get(qid, []), key=lambda x: (x["generator"], x["rollout_idx"]))):
            dfiles.append(d["path"] and str(Path(d["path"]).relative_to(util.ROOT)))
            sc = s_by_id.get(d["deliverable_id"])
            if sc:
                sc_full = dict(sc)                      # 完整 Score 字段, 不裁剪
                sc_full["generator"] = d["generator"]
                sc_list.append(sc_full)
                if sc.get("is_best"):                   # 以 S8 标定的 best 为准
                    best_idx, best_total = i, sc["total"]
                elif best_idx is None and sc["total"] > best_total:
                    best_total = sc["total"]            # 无 is_best 标记时的 argmax 兜底
        if best_idx is None:                            # 兜底: 取分最高
            cand = [(i, s_by_id.get(d["deliverable_id"], {}).get("total", -1.0))
                    for i, d in enumerate(sorted(d_by_q.get(qid, []), key=lambda x: (x["generator"], x["rollout_idx"])))]
            if cand:
                best_idx = max(cand, key=lambda t: t[1])[0]

        ak_refs = [str((util.path("answer_keys") / f"{fid}.md").relative_to(util.ROOT))
                   for fid in q["reference_files"]]
        sources = [{"doc_id": fid, **(idx[fid].get("provenance", {}))}
                   for fid in q["reference_files"] if fid in idx]
        item = schema.Item(
            task_id=qid, domain=q["domain"], occupation=q["occupation"],
            deliverable_type=q["deliverable_type"], prompt=q["prompt"],
            reference_files=ref_paths, reference_file_urls=[],
            deliverable_files=dfiles,
            rubric_pretty=rub.get("rubric_pretty", ""),
            rubric_json=rub["items"],
            answer_key_refs=ak_refs,
            provenance={"bundle_id": q["bundle_id"], "reference_docs": q["reference_files"],
                        "sources": sources},
            qc=q.get("qc", {}), scores=sc_list, best_idx=best_idx).__dict__
        items.append(item)
        print(f"  [emit] {qid} | refs={len(ref_paths)} delivs={len(dfiles)} best_idx={best_idx}")

    util.write_jsonl(util.path("items"), items)
    print(f"[emit] {len(items)} items -> {util.path('items')}")
    return items
