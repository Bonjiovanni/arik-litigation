"""
export_all_emails.py
--------------------
Reads a combined_repository.json and exports all records / all fields
to an Excel file.

When run standalone: prompts for input and output files via file picker
(remembers last choices in merge_config.json).
When called from merge_and_classify.py: input path passed as argv[1],
still prompts for output file.

Uses xlsxwriter with write_string() so values starting with = are never
treated as formulas.
"""

import json
import sys
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

import xlsxwriter

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR  = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "Email_Body_Processing_Config.json"

PRIORITY_COLS = [
    "Header.Date",
    "Header.Message-ID",
    "Address.Sender",
    "Address.To",
    "Header.Subject",
    "strip_method",
    "body_clean",
    "Email.Status",
    "Header.X-Gmail-Labels",
]

MAX_CELL_LEN = 32_000


# ---------------------------------------------------------------------------
# Persistent config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------------------
# File picker helpers
# ---------------------------------------------------------------------------

def pick_input_file(last_dir: str) -> Path | None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    chosen = filedialog.askopenfilename(
        title="Select combined_repository JSON file",
        initialdir=last_dir,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        parent=root,
    )
    root.destroy()
    if not chosen:
        return None
    return Path(chosen)


def pick_output_file(last_path: str) -> Path | None:
    last = Path(last_path) if last_path else SCRIPT_DIR / "all_emails.xlsx"
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    while True:
        chosen = filedialog.asksaveasfilename(
            title="Save all_emails as...",
            initialdir=str(last.parent),
            initialfile=last.name,
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            confirmoverwrite=False,
            parent=root,
        )
        if not chosen:
            abort = input("\nNo output file selected. Abort? [y/n]: ").strip().lower()
            if abort == "y":
                root.destroy()
                return None
            continue

        out_path = Path(chosen)
        if out_path.exists():
            answer = input(
                f"\n  WARNING: '{out_path.name}' already exists.\n"
                f"  Overwrite it? [y = overwrite / n = pick a new name]: "
            ).strip().lower()
            if answer == "y":
                break
        else:
            break

    root.destroy()
    return out_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_str(v) -> str:
    if v is None:
        return ""
    s = str(v)
    if len(s) > MAX_CELL_LEN:
        s = s[:MAX_CELL_LEN]
    return "".join(
        ch for ch in s
        if ch in ("\n", "\r", "\t") or (32 <= ord(ch) <= 126) or ord(ch) > 127
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("export_all_emails.py")
    print("=" * 60)

    cfg = load_config()

    # --- Input file ---
    if len(sys.argv) > 1:
        # Called from merge_and_classify with path already provided
        input_file = Path(sys.argv[1])
        print(f"\n[1] Input: {input_file.name}  (passed from merge_and_classify)")
    else:
        # Standalone run — show picker
        last_dir = cfg.get("last_export_input_dir", str(SCRIPT_DIR))
        print("\n[1] Select input file (combined_repository JSON)")
        input_file = pick_input_file(last_dir)
        if not input_file:
            print("  No file selected. Aborting.")
            return
        cfg["last_export_input_dir"] = str(input_file.parent)

    if not input_file.exists():
        print(f"\n  ERROR: File not found: {input_file}. Aborting.")
        return

    # --- Output file ---
    last_output = cfg.get("last_export_output_path", str(SCRIPT_DIR / "all_emails.xlsx"))
    print("\n[2] Select output file")
    out_path = pick_output_file(last_output)
    if not out_path:
        print("  Aborted.")
        return
    cfg["last_export_output_path"] = str(out_path)

    save_config(cfg)

    # --- Load records ---
    print(f"\n[3] Reading {input_file.name}...")
    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)
    records = data["emails"]
    print(f"  {len(records)} records loaded.")

    # --- Build column list ---
    all_keys: set = set()
    for r in records:
        all_keys.update(r.keys())
    priority_present = [c for c in PRIORITY_COLS if c in all_keys]
    rest = sorted(all_keys - set(PRIORITY_COLS))
    columns = priority_present + rest
    print(f"  {len(columns)} columns.")

    # --- Write Excel ---
    print(f"\n[4] Writing {out_path.name}...")
    wb = xlsxwriter.Workbook(str(out_path), {
        "strings_to_formulas": False,
        "strings_to_urls":     False,
        "strings_to_numbers":  False,
    })
    ws = wb.add_worksheet("All Emails")

    hdr_fmt = wb.add_format({
        "bold":       True,
        "font_color": "#FFFFFF",
        "bg_color":   "#1F4E79",
        "valign":     "vcenter",
        "border":     0,
    })
    cell_fmt = wb.add_format({
        "valign":     "top",
        "num_format": "@",
    })

    ws.freeze_panes(1, 0)

    for col_idx, col_name in enumerate(columns):
        ws.write_string(0, col_idx, col_name, hdr_fmt)

    for row_idx, record in enumerate(records, start=1):
        for col_idx, col_name in enumerate(columns):
            ws.write_string(row_idx, col_idx, safe_str(record.get(col_name)), cell_fmt)

    print("  Setting column widths...")
    for col_idx, col_name in enumerate(columns):
        sample_vals = [col_name]
        for r in records[:200]:
            v = safe_str(r.get(col_name))
            sample_vals.append(v.split("\n")[0] if v else "")
        width = min(max(len(s) for s in sample_vals) + 2, 60)
        width = max(width, 8)
        ws.set_column(col_idx, col_idx, width)

    wb.close()

    print(f"\n  Done. {len(records)} rows x {len(columns)} columns.")
    print(f"  Output: {out_path}")
    print("\n" + "=" * 60)
    print("Done.")
    print("=" * 60)
    return out_path


if __name__ == "__main__":
    main()
