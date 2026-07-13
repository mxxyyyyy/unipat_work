
ref_dir = 'reference'

with open(f'{ref_dir}/0d6e93f812c6716d.md', 'r') as f:
    rpt_jun = f.read()

with open(f'{ref_dir}/1a38052123e9e954.md', 'r') as f:
    rpt_feb = f.read()

# Extract all data-rich passages
search_terms = [
    'percent', 'unemployment', 'job openings', 'JOLTS', 'wage', 'Wage', 'ECI', 
    'Average hourly', 'Atlanta', 'employment cost', 'Summary of Economic',
    'SEP', 'median', 'central tendency', 'PCE inflation',
    'participation', 'labor force', 'Employment-to-population',
    'core goods', 'core services', 'nonhousing', 'housing services',
    'market-based', 'non-market-based', 'trimmed mean',
    'ECB', 'euro', 'Euro area', 'foreign', 'Foreign',
]

# Print all unique data points from June 2025 report
print("="*80)
print("JUNE 2025 FULL REPORT - KEY DATA SECTIONS")
print("="*80)

# Print the main domestic developments section
idx_start = rpt_jun.find('Recent Economic and Financial')
idx_end = rpt_jun.find('Financial Developments', idx_start + 100)
if idx_start >= 0:
    print(rpt_jun[idx_start:idx_start+8000])
