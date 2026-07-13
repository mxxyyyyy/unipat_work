
import re

with open("briefing_note.html", 'r') as f:
    html = f.read()

# More aggressive trims
trims = [
    # Trim exec summary
    ("Both jurisdictions face elevated uncertainty, with trade policy disruptions and geopolitical risks as dominant near-term threats.",
     "Both face elevated uncertainty, with trade policy disruptions and geopolitical risks as dominant threats."),
    
    # Trim common risks section  
    ("Both institutions judge valuations stretched. The S&P 500 forward P/E is near the upper end of its historical range, the equity premium at a 20-year low, and credit spreads historically compressed.",
     "Both judge valuations stretched: S&P 500 forward P/E near its historical upper end, equity premium at a 20-year low, credit spreads historically compressed."),
    
    # Trim trade policy
    ("Both reports identify trade policy—particularly US import tariffs—as the primary near-term threat.",
     "Both identify trade policy—particularly US import tariffs—as the primary near-term threat."),
    
    # Trim NBFI
    ("Both flag NBFI as a systemic amplification channel.",
     "Both flag NBFI as an amplification channel."),
    
    # Trim corporate divergence
    ("By contrast, US business debt/GDP is at 20-year lows with subdued default forecasts.",
     "US business debt/GDP is at 20-year lows with subdued default forecasts."),
    
    # Trim household
    ("US households benefit from aggregate debt-to-GDP at 20-year lows",
     "US aggregate household debt-to-GDP is at 20-year lows"),
    
    # Trim sovereign
    ("A distinctly euro area concern.",
     "A euro area-specific concern."),
    
    # Trim cross-border
    ("The euro area's deep integration into global supply chains means US tariff actions directly transmit to euro area corporate earnings, employment, and asset quality.",
     "The euro area's deep supply-chain integration means US tariffs directly hit euro area corporate earnings, employment, and asset quality."),
    
    # Trim fire sale
    ("If a repricing event triggers redemptions from funds with liquidity mismatches—present on both sides—forced selling of common assets could propagate across markets.",
     "Redemption-driven fire sales from funds with liquidity mismatches—present on both sides—could propagate dislocations across common asset markets."),
    
    # Trim conclusion US
    ("Stretched equity valuations and compressed credit spreads leave markets vulnerable to repricing. Hedge fund and life insurer leverage build-up raises amplification concerns.",
     "Stretched equity valuations and compressed credit spreads leave markets vulnerable to repricing; hedge fund and life insurer leverage raises amplification concerns."),
]

for old, new in trims:
    if old in html:
        html = html.replace(old, new)
    else:
        print(f"WARNING: Could not find: '{old[:60]}...'")

with open("briefing_note.html", 'w') as f:
    f.write(html)

# Recount
body_match = re.search(r'<body>(.*?)</body>', html, re.DOTALL)
body = body_match.group(1)
body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', body)
text = re.sub(r'\s+', ' ', text).strip()
words = text.split()
print(f"Final word count: {len(words)}")
