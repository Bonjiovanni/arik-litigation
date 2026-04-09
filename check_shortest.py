import openpyxl

wb = openpyxl.load_workbook(r"C:\Users\arika\OneDrive\Documents\body_column_comparison.xlsx", read_only=True, data_only=True)
ws = wb.active

cols = ["body_clean.1", "Body.HTML", "Body.SenderText", "Body.Text"]
shortest_wins = [0, 0, 0, 0]
longest_wins = [0, 0, 0, 0]
total = 0
avg_lens = [0, 0, 0, 0]
counts = [0, 0, 0, 0]

for row in ws.iter_rows(min_row=2, values_only=True):
    lens = [row[7] or 0, row[8] or 0, row[9] or 0, row[10] or 0]
    nz = [(i, v) for i, v in enumerate(lens) if v > 0]
    if not nz:
        continue
    total += 1
    for i, v in nz:
        avg_lens[i] += v
        counts[i] += 1
    mn = min(v for _, v in nz)
    mx = max(v for _, v in nz)
    for i, v in nz:
        if v == mn:
            shortest_wins[i] += 1
        if v == mx:
            longest_wins[i] += 1

print(f"Total rows with at least one non-empty body: {total}\n")
print("SHORTEST column per row:")
for i in range(4):
    print(f"  {cols[i]}: shortest in {shortest_wins[i]} rows ({100*shortest_wins[i]/total:.1f}%)")
print(f"\nLONGEST column per row:")
for i in range(4):
    print(f"  {cols[i]}: longest in {longest_wins[i]} rows ({100*longest_wins[i]/total:.1f}%)")
print(f"\nAVERAGE stripped char count (when non-empty):")
for i in range(4):
    avg = avg_lens[i] / counts[i] if counts[i] else 0
    print(f"  {cols[i]}: avg {avg:.0f} chars ({counts[i]} non-empty rows)")
