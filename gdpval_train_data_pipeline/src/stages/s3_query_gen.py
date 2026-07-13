"""
S3 · Query 生成
每个 bundle × 每种受支持的交付物类型 -> 一条 GDPval 式 query (领域专家 prompt)。
LLM 从该领域职业清单里挑最贴合的职业。

产出: outputs/queries.jsonl  (Query, 未质检)
"""
from __future__ import annotations

import util
import schema
from providers import base


def _author():
    return base.get_provider(util.cfg("models")["roles"]["author"])


def _occupations(domain) -> list:
    return util.domain_by_key(domain)["occupations"]


def run(limit_bundles=None, workers=8):
    provider = _author()
    bundles = util.read_jsonl(util.path("bundles"))
    if limit_bundles:
        bundles = bundles[:limit_bundles]

    xlsx_cap = util.cfg("domains").get("pilot_deliverable_mix", {}).get("xlsx_cap", 10)

    # 每个 bundle 预备上下文 (避免 worker 内重复计算)
    ctx = {}
    for b in bundles:
        occs = _occupations(b["domain"])
        ctx[b["bundle_id"]] = {
            "ref_text": util.bundle_reference(b["files"]),
            "occ_desc": "\n".join(f'- {o["id"]}: {o["zh"]} (产物: {", ".join(o["products"])})' for o in occs),
            "occ0": occs[0]["id"],
            "sys": util.load_prompt("query_gen", b["domain"]),
        }

    # 任务列表 (bundle × dtype); xlsx 按 cap 提前截断, 以 prose 为主
    tasks, xlsx_seen = [], 0
    for b in bundles:
        for dtype in b["supported_deliverables"]:
            if dtype == "data_xlsx":
                if xlsx_seen >= xlsx_cap:
                    continue
                xlsx_seen += 1
            tasks.append((b, dtype))

    def _gen(task):
        b, dtype = task
        c = ctx[b["bundle_id"]]
        user = (
            f"领域: {b['domain']}\n可选职业(挑最贴合本次任务的一个, 用其 id):\n{c['occ_desc']}\n\n"
            f"目标交付物类型: {dtype}\n\n参考数据文件(只含数据层):\n{c['ref_text']}\n\n"
            f"按要求产出一条任务。只输出 JSON (occupation/deliverable_type/prompt/subtasks/format_spec)。"
        )
        try:
            out = provider.chat_json(
                [{"role": "system", "content": c["sys"]},
                 {"role": "user", "content": user}],
                schema=schema.QUERY_GEN_SCHEMA, temperature=0.7, max_tokens=8000)
        except Exception as e:                        # noqa
            print(f"  [S3] bundle={b['bundle_id']} {dtype} 生成失败: {e}")
            return None
        occ = out.get("occupation", c["occ0"])
        q = schema.Query(
            query_id=schema.stable_id(b["bundle_id"], dtype, occ),
            bundle_id=b["bundle_id"], domain=b["domain"],
            occupation=occ, deliverable_type=out.get("deliverable_type", dtype),
            prompt=out.get("prompt", ""), subtasks=out.get("subtasks", []),
            format_spec=out.get("format_spec", ""), reference_files=b["files"])
        print(f"  [S3] {b['domain']}/{dtype}/{occ} -> {q.query_id} ({len(q.prompt)} chars)")
        return q.__dict__

    queries = [q for q in util.pmap(_gen, tasks, workers=workers) if q]
    util.write_jsonl(util.path("queries"), queries)
    print(f"[S3] 完成 {len(queries)} queries -> {util.path('queries')}")
    return queries
