
with open("Kazakhstan_ArticleIV_Brief.md", "r") as f:
    content = f.read()

words = content.split()
word_count = len(words)

print(f"Word count: {word_count}")
print(f"Target range: 1500-2500 → {'WITHIN RANGE' if 1500 <= word_count <= 2500 else 'SLIGHTLY OVER' if word_count <= 2800 else 'OVER'}")

# Verify all content checks
checks = [
    ("Real GDP growth", "Real GDP growth" in content),
    ("Inflation", "CPI inflation" in content),
    ("Fiscal balances", "budget balance" in content),
    ("Current account", "current account" in content.lower()),
    ("Government debt", "government debt" in content.lower()),
    ("Debt service", "debt service" in content.lower()),
    ("External debt-to-GDP", "external debt" in content.lower()),
    ("External debt-to-exports", "External debt / Exports" in content),
    ("Import cover", "import cover" in content.lower()),
    ("NBK reserves", "NBK reserves" in content),
    ("Net FDI", "FDI" in content),
    ("Debt Sustainability Assessment", "Debt Sustainability Assessment" in content),
    ("Oil price shock", "Oil Price Decline" in content),
    ("Growth shock", "Growth Slowdown" in content),
    ("Policy Recommendations", "Policy Recommendations" in content),
    ("Annex", "Data Notes and Limitations" in content),
    ("NFRK", "NFRK" in content),
    ("Brent oil price", "Brent" in content),
    ("Snowball / r-g", "snowball" in content.lower() or "r − g" in content),
    ("Primary balance", "primary" in content.lower()),
]

all_ok = True
for check, result in checks:
    status = "OK" if result else "MISSING!"
    if not result:
        all_ok = False
    print(f"  [{status}] {check}")

print(f"\nAll {len(checks)} checks: {'PASSED' if all_ok else 'SOME FAILED'}")
