
import os

path = "Kazakhstan_ArticleIV_Brief.md"
size = os.path.getsize(path)
print(f"File size: {size:,} bytes")

with open(path, 'r') as f:
    content = f.read()
    
words = content.split()
print(f"Word count: {len(words)}")
print(f"Character count: {len(content)}")

# Count sections
sections = [line for line in content.split('\n') if line.startswith('## ')]
print(f"\nSections found ({len(sections)}):")
for s in sections:
    print(f"  {s}")

# Check for required subsections
required = ['Macroeconomic Overview', 'Fiscal and External Sustainability', 
            'Debt Sustainability Assessment', 'Risks and Policy']
for r in required:
    found = any(r.lower() in s.lower() for s in sections)
    print(f"  {'✓' if found else '✗'} Contains: {r}")
