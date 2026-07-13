
# Get the full Table 6 for Bangladesh
with open('reference/a9526b8882f2fbd1.md', 'r') as f:
    bd_content = f.read()

# Find the actual Table 6 data (not the TOC reference)
# Search for "Table 6" appearing after "Fiscal Outcomes"
idx_fiscal = bd_content.find("Table 5: Fiscal Outcomes")
# Find "Table 6" after that
idx6_actual = bd_content.find("Table 6:", idx_fiscal)
print(f"Table 6 after fiscal: {idx6_actual}")
if idx6_actual >= 0:
    print(bd_content[idx6_actual:idx6_actual+2000])

print("\n\n======")
# Also look for "Selected Macroeconomic" section heading
idx_sel = bd_content.find("Selected Macroeconomic Indicators")
print(f"Selected Macroeconomic Indicators: {idx_sel}")
# Find the data table after that
# Look for the table header
idx_data = bd_content.find("Real GDP growth, at constant market prices", idx_sel - 1000)
print(f"Table data: {idx_data}")
if idx_data >= 0:
    print(bd_content[idx_data-1000:idx_data+2500])
