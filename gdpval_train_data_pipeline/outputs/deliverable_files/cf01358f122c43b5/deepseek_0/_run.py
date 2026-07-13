
import re
import os

ref_dir = 'reference'

# BANGLADESH: Search for any GDP growth numbers mentioned in text
print("=== BANGLADESH GDP GROWTH NUMBERS ===")
with open(os.path.join(ref_dir, 'a9526b8882f2fbd1.md'), 'r') as f:
    bd_content = f.read()

# Find all mentions of GDP growth with numbers
for m in re.finditer(r'(?:GDP|economy).*?(?:grew|growth|expanded).*?(\d+\.?\d*)\s*(?:%|percent)', bd_content, re.IGNORECASE):
    context = bd_content[max(0, m.start()-150):min(len(bd_content), m.end()+150)]
    print(context[:400])
    print("---")

# Also look for FY growth numbers
for m in re.finditer(r'FY2[123].*?(\d+\.\d+)\s*%', bd_content):
    context = bd_content[max(0, m.start()-50):min(len(bd_content), m.end()+50)]
    print(f"  -> {context.strip()[:300]}")

# NIGERIA: Get the Annex data more cleanly
print("\n\n=== NIGERIA ANNEX FULL DATA ===")
with open(os.path.join(ref_dir, 'dd5101d209697884.md'), 'r') as f:
    ng_content = f.read()

# Find the section with "Real GDP growth" in the annex
annex2_idx = ng_content.find('Annex 2')
if annex2_idx >= 0:
    annex_section = ng_content[annex2_idx:]
    print(annex_section[:3000])

# Search for Nigeria GDP growth and inflation
print("\n\n=== NIGERIA GDP GROWTH & INFLATION IN MAIN TEXT ===")
for m in re.finditer(r'(?:GDP|economy).*?(?:grew|growth|expanded).*?(\d+\.?\d*)\s*(?:%|percent)', ng_content, re.IGNORECASE):
    context = ng_content[max(0, m.start()-200):min(len(ng_content), m.end()+200)]
    if not any(w in context.lower() for w in ['global', 'world', 'china', 'india', 'bangladesh', 'south africa', 'emdes', 'advanced']):
        print(context[:400])
        print("---")

# Search for inflation numbers
print("\n--- Nigeria inflation mentions ---")
for m in re.finditer(r'(?:inflation|CPI).*?(\d+\.?\d*)\s*(?:%|percent)', ng_content, re.IGNORECASE):
    context = ng_content[max(0, m.start()-150):min(len(ng_content), m.end()+150)]
    print(context[:400])
    print("---")

print("\n\nDone.")
