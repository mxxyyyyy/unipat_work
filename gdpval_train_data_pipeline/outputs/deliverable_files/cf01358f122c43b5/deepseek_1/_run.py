
import os

ref_dir = 'reference'

with open(os.path.join(ref_dir, 'dd5101d209697884.md'), 'r') as f:
    lines = f.readlines()

# Continue Nigeria Annex 2 - fiscal/debt area
print("=== NIGERIA - ANNEX 2 (fiscal/debt/current account area) ===")
for i in range(2019, 2195):
    if i < len(lines):
        print(f"L{i}: {lines[i].rstrip()}")
