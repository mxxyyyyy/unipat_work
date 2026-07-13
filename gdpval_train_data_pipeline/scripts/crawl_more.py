"""定向补爬 (可预测 URL 的公开机构 PDF)。下载到 data/corpus/<source>/, 重建 CORPUS.json。
每个条目带显式 domain。失败优雅跳过。"""
import json, sys, time
from pathlib import Path
import requests
import fitz

CORPUS = "data" / "corpus"

# (source_dir, name, url, domain)
TARGETS = []
# --- ECB Economic Bulletin eb{YYYYNN}, NN=01..08 -> monetary ---
for yy in ("2025", "2024"):
    for nn in ("01", "02", "03", "04", "05", "06"):
        TARGETS.append(("ecb", f"ecb_economic_bulletin_{yy}_{nn}",
                        f"https://www.ecb.europa.eu/pub/pdf/ecbu/eb{yy}{nn}.en.pdf", "monetary"))
# --- BIS Quarterly Review r_qt{YYMM} -> monetary ---
for ym in ("2506", "2406", "2403", "2312", "2309", "2306"):
    TARGETS.append(("bis", f"bis_quarterly_review_{ym}",
                    f"https://www.bis.org/publ/qtrpdf/r_qt{ym}.pdf", "monetary"))
# --- BIS Annual Economic Report -> monetary ---
for yr in ("2023", "2022"):
    TARGETS.append(("bis", f"bis_annual_economic_report_{yr}",
                    f"https://www.bis.org/publ/arpdf/ar{yr}e.pdf", "monetary"))
# --- Fed Financial Stability Report -> fin_stability ---
for d in ("20241122", "20240419", "20231020", "20230508", "20221104"):
    TARGETS.append(("fed", f"fed_financial_stability_report_{d}",
                    f"https://www.federalreserve.gov/publications/files/financial-stability-report-{d}.pdf",
                    "fin_stability"))
# --- Fed Monetary Policy Report -> monetary ---
for d in ("20240301", "20230303", "20220617", "20210219"):
    TARGETS.append(("fed", f"fed_monetary_policy_report_{d}",
                    f"https://www.federalreserve.gov/monetarypolicy/files/{d}_mprfullreport.pdf", "monetary"))
# --- Fed Supervision & Regulation Report -> banking ---
for ym in ("202411", "202405", "202311", "202305", "202211"):
    TARGETS.append(("fed_sr", f"fed_supervision_regulation_report_{ym}",
                    f"https://www.federalreserve.gov/publications/files/{ym}-supervision-and-regulation-report.pdf",
                    "banking"))
# --- cross_border 尝试: BIS US-dollar/global-liquidity 类 CGFS/评论 (不确定, 尽力) ---
CROSS = [
    ("bis_stats", "bis_global_liquidity_indicators_note",
     "https://www.bis.org/statistics/gli/gli2508.pdf", "cross_border"),
]
TARGETS += CROSS

HEADERS = {"User-Agent": "Mozilla/5.0 (research corpus builder)"}


def fetch(url, dest):
    try:
        r = requests.get(url, headers=HEADERS, timeout=40)
        if r.status_code != 200 or not r.content[:5].startswith(b"%PDF"):
            return f"skip ({r.status_code}, not pdf)"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return "ok"
    except Exception as e:
        return f"err {type(e).__name__}"


def meta(pdf, source, name, domain):
    try:
        doc = fitz.open(str(pdf))
        pages = doc.page_count
        chars = sum(len(doc[i].get_text()) for i in range(min(pages, 30))) * pages // max(1, min(pages, 30))
        doc.close()
    except Exception:
        pages, chars = 0, 0
    title = name.replace("_", " ")
    return {"source": source, "name": name, "domain": domain, "pages": pages,
            "chars": chars, "pdf": f"data/corpus/{source}/{name}.pdf",
            "src_url": None}


def main():
    existing = []
    cj = CORPUS / "CORPUS.json"
    if cj.exists():
        existing = json.loads(cj.read_text())
    have = {(e.get("source"), e.get("name")) for e in existing}
    added = []
    for source, name, url, domain in TARGETS:
        if (source, name) in have:
            print(f"[have] {name}"); continue
        dest = CORPUS / source / f"{name}.pdf"
        if dest.exists():
            print(f"[exists] {name}")
        else:
            st = fetch(url, dest)
            print(f"[{st}] {name} <- {url}")
            if st != "ok":
                continue
            time.sleep(0.5)
        m = meta(dest, source, name, domain)
        m["src_url"] = url
        added.append(m)
    if added:
        allentries = existing + added
        cj.write_text(json.dumps(allentries, ensure_ascii=False, indent=1))
        print(f"\n[crawl] 新增 {len(added)} 篇, CORPUS.json 共 {len(allentries)} 篇")
    else:
        print("\n[crawl] 无新增")
    # 按 domain 统计
    from collections import Counter
    c = Counter(e.get("domain") or "?" for e in (existing + added))
    print("domain 分布:", dict(c))


if __name__ == "__main__":
    main()
