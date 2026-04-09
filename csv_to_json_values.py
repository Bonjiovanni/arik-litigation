"""Convert the body comparison CSV to a JSON 2D array for Excel MCP."""
import csv, json

SRC = r"C:\Users\arika\Repo-for-Claude-android\body_comparison_data.csv"
OUT = r"C:\Users\arika\Repo-for-Claude-android\body_comparison_data.json"

rows = []
with open(SRC, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        # Truncate body columns (cols 1-4) to 500 chars to avoid Excel cell limits
        truncated = [row[0]]  # message ID
        for val in row[1:5]:  # 4 body columns
            if len(val) > 500:
                truncated.append(val[:500] + "...[truncated]")
            else:
                truncated.append(val)
        truncated.extend(row[5:])  # match code, result, len cols
        rows.append(truncated)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f)

print(f"Wrote {len(rows)} rows ({len(rows[0])} cols) to {OUT}")
print(f"File size: {len(open(OUT,'rb').read())/1e6:.1f} MB")
