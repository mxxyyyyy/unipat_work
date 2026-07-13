
import os

path = "Kazakhstan_ArticleIV_Brief.md"
size = os.path.getsize(path)
print(f"File size: {size:,} bytes")

with open(path, 'r') as f:
    content = f.read()

# Word count
words = content.split()
print(f"Word count: {len(words)}")

# Line count
lines = content.split('\n')
print(f"Line count: {len(lines)}")

# Check all required sections present
required_sections = [
    "Macroeconomic Overview",
    "Fiscal and External Sustainability",
    "Debt Sustainability Assessment",
    "Risks and Policy Recommendations"
]

for section in required_sections:
    if section in content:
        print(f"✓ Section found: '{section}'")
    else:
        print(f"✗ MISSING section: '{section}'")

# Check key metrics are present
key_metrics = [
    "debt service",
    "import cover",
    "external debt-to-exports",
    "snowball",
    "primary balance",
    "r − g",
    "current account",
    "FDI",
    "NFRK",
    "NBK reserves"
]

for metric in key_metrics:
    if metric.lower() in content.lower():
        print(f"✓ Metric found: '{metric}'")
    else:
        print(f"✗ MISSING metric: '{metric}'")
