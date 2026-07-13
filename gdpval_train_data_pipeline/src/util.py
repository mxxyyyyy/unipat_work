"""
util.py — 配置加载 / prompt 拼接 / PDF 抽取 / jsonl IO。所有 stage 共用。
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional
import yaml

ROOT = Path(__file__).resolve().parents[1]        # final/
CONFIG = ROOT / "config"
PROMPTS = ROOT / "prompts"


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
_cfg_cache: dict = {}


def cfg(name: str) -> dict:
    if name not in _cfg_cache:
        _cfg_cache[name] = yaml.safe_load((CONFIG / f"{name}.yaml").read_text())
    return _cfg_cache[name]


def domains() -> list:
    return cfg("domains")["domains"]


def domain_by_key(key: str) -> dict:
    for d in domains():
        if d["key"] == key:
            return d
    raise KeyError(f"未知领域: {key}")


def path(key: str) -> Path:
    """pipeline.yaml paths.<key> -> 绝对路径。"""
    p = cfg("pipeline")["paths"][key]
    return (ROOT / p) if not Path(p).is_absolute() else Path(p)


# ---------------------------------------------------------------------------
# prompt 拼接: _shared.md + <domain>.md
# ---------------------------------------------------------------------------
def load_prompt(stage: str, domain: Optional[str] = None) -> str:
    shared = PROMPTS / stage / "_shared.md"
    parts = []
    if shared.exists():
        parts.append(shared.read_text())
    if domain:
        dfile = PROMPTS / stage / f"{domain}.md"
        if dfile.exists():
            parts.append("\n\n---\n" + dfile.read_text())
    if not parts:
        raise FileNotFoundError(f"无 prompt: stage={stage} domain={domain}")
    return "\n".join(parts)


def load_anchor_prompt(name: str) -> str:
    return (PROMPTS / "expert_anchor" / f"{name}.md").read_text()


# ---------------------------------------------------------------------------
# jsonl IO
# ---------------------------------------------------------------------------
def pmap(fn, items, workers: int = 8) -> list:
    """并发 map (LLM/agent 均 IO 密集, 线程即可)。保持输入顺序。"""
    from concurrent.futures import ThreadPoolExecutor
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as ex:
        return list(ex.map(fn, items))


def read_jsonl(p) -> list:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def write_jsonl(p, rows) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def append_jsonl(p, row) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# PDF 抽取 (pymupdf)
# ---------------------------------------------------------------------------
def pdf_paragraphs(pdf_path, min_chars: int = 40) -> list:
    """返回段落列表 [{text, page}]。按 block 抽取, 合并过短碎块。"""
    import fitz
    doc = fitz.open(str(pdf_path))
    paras = []
    for pno in range(doc.page_count):
        page = doc[pno]
        blocks = page.get_text("blocks")           # (x0,y0,x1,y1,text,bno,btype)
        blocks.sort(key=lambda b: (round(b[1]), b[0]))
        for b in blocks:
            txt = re.sub(r"[ \t]+", " ", (b[4] or "")).strip()
            txt = re.sub(r"\n{2,}", "\n", txt)
            if len(txt) >= min_chars and not _is_boilerplate(txt):
                paras.append({"text": txt, "page": pno + 1})
    doc.close()
    return paras


_BOILER = re.compile(r"^(page \d+|\d+\s*$|copyright|all rights reserved|www\.|https?://)", re.I)


def _is_boilerplate(t: str) -> bool:
    return bool(_BOILER.match(t.strip())) or len(t) < 3


_cleaned_idx: dict = {}


def cleaned_index() -> dict:
    """{doc_id: CleanedDoc dict}, 缓存。"""
    global _cleaned_idx
    if not _cleaned_idx:
        for f in sorted(path("cleaned").glob("*.json")):
            d = json.loads(f.read_text())
            _cleaned_idx[d["doc_id"]] = d
    return _cleaned_idx


def bundle_reference(files, total_budget: int = 18000) -> str:
    """把 bundle 全部文件的 reference 拼进来; 预算**按文件均分**, 保证每个文件都被呈现
    (修复: 之前 per-file + 下游再截断 -> 多文件 bundle 只看到第一份)。"""
    idx = cleaned_index()
    docs = [idx[f] for f in files if f in idx]
    if not docs:
        return ""
    per = max(1500, total_budget // len(docs))
    parts = [f"### 参考文件 {d['doc_id']} · {d['title']}\n{d['reference_text'][:per]}" for d in docs]
    return "\n\n".join(parts)


def bundle_answer_key(files, total_budget: int = 12000) -> str:
    idx = cleaned_index()
    docs = [idx[f] for f in files if f in idx and idx[f].get("answer_key_text")]
    if not docs:
        return ""
    per = max(1000, total_budget // len(docs))
    parts = [f"### {d['doc_id']} 结论锚点\n{d['answer_key_text'][:per]}" for d in docs]
    return "\n\n".join(parts)


def corpus_manifest() -> list:
    """读 data/corpus/CORPUS.json (若有), 否则扫 pdf。返回 [{source,name,pdf,domain?}]。
    统一补 name (WB 用 country, 其余用 pdf stem)。"""
    cj = path("corpus") / "CORPUS.json"
    if cj.exists():
        entries = json.loads(cj.read_text())
    else:
        entries = [{"source": pdf.parent.name, "pdf": f"data/corpus/{pdf.parent.name}/{pdf.name}"}
                   for pdf in path("corpus").rglob("*.pdf")]
    for m in entries:
        if not m.get("name"):
            m["name"] = m.get("country") or Path(m.get("pdf", "x.pdf")).stem
    return entries


# ---------------------------------------------------------------------------
# 源 -> 领域 映射 (doc 级单一归属)。可被 CORPUS.json 里的 domain 覆盖。
# ---------------------------------------------------------------------------
SOURCE_DOMAIN = {
    "worldbank": "sovereign",
    "bis": "monetary",              # BIS 多主题, 主归 monetary (季度/年报)
    "fed": "monetary",              # 默认; FSR 由 name 细分见下
    "ecb": "monetary",
    "eba": "banking", "fdic": "banking", "imf_fsap": "banking",
    "bis_stats": "cross_border", "imf_bop": "cross_border", "iif": "cross_border",
}


def infer_domain(source: str, name: str) -> str:
    n = (name or "").lower()
    if "financial_stability" in n or "fsr" in n or "stability" in n:
        return "fin_stability"
    return SOURCE_DOMAIN.get(source, "monetary")
