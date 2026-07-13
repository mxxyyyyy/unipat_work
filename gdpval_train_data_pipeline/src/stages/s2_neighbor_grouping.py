"""
S2 · 领域内近邻成组 (neighbor_grouping) —— 非划分式聚类。
以每个 cleaned doc 为种子, 取同领域内阈值(领域相似度分位数)内最近邻, 上限 cap=3,
组成可重叠 bundle; 去重相同/子集; 孤立 doc -> 单文件 bundle。
门控标注每个 bundle 支持的交付物类型 (has_tables -> data_xlsx)。

产出: outputs/bundles.jsonl
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

import util
import schema


def _load_cleaned() -> list:
    docs = []
    for f in sorted(util.path("cleaned").glob("*.json")):
        docs.append(json.loads(f.read_text()))
    return docs


def _supported_deliverables(bundle_docs) -> list:
    dt = util.cfg("domains")["deliverable_types"]
    prose = [k for k, v in dt.items() if not v["requires"]["tabular_data"]]
    types = list(prose)
    if any(d.get("has_tables") for d in bundle_docs):
        types += [k for k, v in dt.items() if v["requires"]["tabular_data"]]
    return types


def _group_one_domain(docs, cap, min_sim, domain=""):
    """返回 bundle 的 files(doc_id) 列表 (已去重)。
    阈值 = 绝对余弦下限 min_sim (可调): 每个种子 doc 取 sim>=min_sim 的最近 <=cap-1 个邻居。
    (修复: 原先用 75 分位数做下限, 在小/紧凑领域会把近乎等相似的 doc 误判为不相关 -> 全是单文件。)"""
    if len(docs) == 1:
        return [[docs[0]["doc_id"]]]
    texts = [d["reference_text"][:8000] or d["title"] for d in docs]
    from providers import embedding
    V = embedding.embed(texts)                         # (n,d) 归一化
    S = V @ V.T                                         # 余弦相似度
    n = len(docs)
    thr = float(min_sim)
    iu = np.triu_indices(n, k=1)
    pairs = S[iu]
    if pairs.size:
        print(f"     [{domain}] 成对相似度 min={pairs.min():.3f} max={pairs.max():.3f} "
              f"mean={pairs.mean():.3f} | 阈值={thr:.3f}")

    bundles = set()
    for i in range(n):
        sims = [(j, float(S[i, j])) for j in range(n) if j != i and S[i, j] >= thr]
        sims.sort(key=lambda x: -x[1])
        neigh = [docs[j]["doc_id"] for j, _ in sims[:cap - 1]]
        members = tuple(sorted(set([docs[i]["doc_id"]] + neigh)))
        bundles.add(members)

    # 去重: 丢弃是其他 bundle 真子集的
    blist = [set(b) for b in bundles]
    kept = []
    for b in blist:
        if any(b < other for other in blist):          # 真子集
            continue
        if b not in kept:
            kept.append(b)
    # 保持稳定顺序
    return [sorted(b) for b in sorted(kept, key=lambda s: sorted(s))]


def run():
    cfg_ng = util.cfg("domains")["neighbor_grouping"]
    cap = cfg_ng["cap"]
    min_sim = cfg_ng.get("min_similarity", 0.45)

    docs = _load_cleaned()
    if not docs:
        print("[S2] 无 cleaned 文档, 先跑 S1。")
        return []
    by_domain = {}
    for d in docs:
        by_domain.setdefault(d["domain"], []).append(d)

    id2doc = {d["doc_id"]: d for d in docs}
    out = []
    for domain, dd in by_domain.items():
        groups = _group_one_domain(dd, cap, min_sim, domain=domain)
        for files in groups:
            bundle_docs = [id2doc[f] for f in files]
            b = schema.Bundle(
                bundle_id=schema.stable_id(domain, *files),
                domain=domain, seed=files[0], files=files,
                supported_deliverables=_supported_deliverables(bundle_docs))
            out.append(b.__dict__)
        print(f"[S2] {domain}: {len(dd)} docs -> {len(groups)} bundles")

    util.write_jsonl(util.path("bundles"), out)
    print(f"[S2] 完成 {len(out)} bundles -> {util.path('bundles')}")
    return out
