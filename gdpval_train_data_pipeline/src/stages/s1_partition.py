"""
S1 · 切分/清洗
PDF -> 段落 -> LLM 判 data/analysis/conclusion -> reference(数据层) + answer_key(隐藏结论)。

产出:
  data/cleaned/<doc_id>.json     (CleanedDoc)
  data/answer_keys/<doc_id>.md   (analysis+conclusion, 隐藏锚点)
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import util
import schema
from providers import base


def _author():
    return base.get_provider(util.cfg("models")["roles"]["author"])


def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


_NUM = re.compile(r"[-+]?\d[\d,\.]*%?")


def _looks_tabular(paras) -> bool:
    """启发式: 数据表/时间序列存在 -> 该 doc 可支持 xlsx 任务。"""
    dense = 0
    for p in paras:
        nums = _NUM.findall(p["text"])
        if len(nums) >= 6:
            dense += 1
    return dense >= 3


def _label_chunk(provider, chunk, source, title, domain) -> dict:
    """返回 {块内 index(str): label}。partition 关闭深度思考(简单分类)提速。"""
    sys_prompt = util.load_prompt("partition")
    listing = "\n".join(f'[{i}] {p["text"][:600]}' for i, p in enumerate(chunk))
    user = (f"报告: {title} (source={source}, domain={domain})\n"
            f"给每段判 data/analysis/conclusion。段落:\n{listing}\n\n"
            f'只输出 JSON: {{"segments":[{{"text_id":"0","label":"data"}}]}}')
    labmap = {}
    try:
        out = provider.chat_json(
            [{"role": "system", "content": sys_prompt},
             {"role": "user", "content": user}],
            schema=schema.PARTITION_SCHEMA, temperature=0.0, think=False, max_tokens=4096)
        for seg in out.get("segments", []):
            labmap[str(seg.get("text_id"))] = seg.get("label")
    except Exception as e:
        print(f"  [partition] chunk 失败, 保守剥离: {e}")
    return labmap


def process_doc(entry: dict, provider, max_workers: int = 16, max_paras: int = 600) -> schema.CleanedDoc:
    from concurrent.futures import ThreadPoolExecutor

    pdf = entry.get("pdf")
    pdf_path = (util.ROOT / pdf) if pdf and not Path(pdf).is_absolute() else Path(pdf)
    source = entry.get("source", pdf_path.parent.name)
    name = entry.get("name") or pdf_path.stem
    domain = entry.get("domain") or util.infer_domain(source, name)
    title = entry.get("title", name.replace("_", " "))

    paras = util.pdf_paragraphs(pdf_path)
    if max_paras and len(paras) > max_paras:          # 超大文档截断, 保留前部主体章节 (含核心数据表)
        paras = paras[:max_paras]
    doc_id = schema.stable_id(source, name)

    chunks = list(_chunk(paras, 30))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        labmaps = list(ex.map(lambda c: _label_chunk(provider, c, source, title, domain), chunks))

    ref_parts, key_parts = [], []
    for chunk, labmap in zip(chunks, labmaps):
        for i, p in enumerate(chunk):
            lab = labmap.get(str(i), "analysis")       # 未判到 -> 保守剥离
            (ref_parts if lab == "data" else key_parts).append(p["text"])

    reference_text = "\n\n".join(ref_parts)
    answer_key_text = "\n\n".join(key_parts)

    cd = schema.CleanedDoc(
        doc_id=doc_id, domain=domain, source=source, title=title,
        reference_text=reference_text, answer_key_text=answer_key_text,
        has_tables=_looks_tabular(paras),
        provenance={"pdf": str(pdf_path), "pages": entry.get("pages"),
                    "n_paras": len(paras), "n_data": len(ref_parts),
                    "n_key": len(key_parts)},
    )
    return cd


def leakage_check(cd: schema.CleanedDoc) -> list:
    """粗查: answer_key 的长句是否原样出现在 reference (应为 0)。"""
    hits = []
    ref = cd.reference_text
    for sent in re.split(r"[。.!?\n]", cd.answer_key_text):
        s = sent.strip()
        if len(s) >= 60 and s in ref:
            hits.append(s[:80])
    return hits


def run(limit=None, domain=None, only=None, resume=True):
    provider = _author()
    pcfg = util.cfg("pipeline").get("partition", {})
    workers = pcfg.get("workers", 16)
    max_paras = pcfg.get("max_paras", 600)
    manifest = util.corpus_manifest()
    if domain:
        manifest = [m for m in manifest
                    if (m.get("domain") or util.infer_domain(m.get("source", ""), m.get("name", ""))) == domain]
    if only:
        manifest = [m for m in manifest if m.get("name") == only]
    if limit:
        manifest = manifest[:limit]

    cleaned_dir = util.path("cleaned")
    key_dir = util.path("answer_keys")
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    key_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for entry in manifest:
        name = entry.get("name") or Path(entry.get("pdf", "x")).stem
        source = entry.get("source", "")
        doc_id = schema.stable_id(source, name)
        if resume and (cleaned_dir / f"{doc_id}.json").exists():   # 已切分过 -> 跳过 (可续跑)
            results.append(doc_id)
            continue
        print(f"[S1] {name} ...")
        try:
            cd = process_doc(entry, provider, max_workers=workers, max_paras=max_paras)
        except Exception as e:                       # 单篇失败不拖垮整批 (放量鲁棒)
            print(f"  ✗ 跳过 {name}: {type(e).__name__}: {e}")
            continue
        if not cd.reference_text.strip():
            print(f"  ⚠ {name} reference 为空 (可能是扫描件/无文本层), 跳过。")
            continue
        leaks = leakage_check(cd)
        if leaks:
            print(f"  ⚠ 疑似泄漏 {len(leaks)} 处 (answer_key 句现于 reference): {leaks[:1]}")
        (cleaned_dir / f"{cd.doc_id}.json").write_text(
            json.dumps(cd.__dict__, ensure_ascii=False, indent=1))
        (key_dir / f"{cd.doc_id}.md").write_text(cd.answer_key_text)
        print(f"  -> {cd.doc_id} | domain={cd.domain} | data段={cd.provenance['n_data']} "
              f"key段={cd.provenance['n_key']} has_tables={cd.has_tables}")
        results.append(cd.doc_id)
    print(f"[S1] 完成 {len(results)} 篇 -> {cleaned_dir}")
    return results
