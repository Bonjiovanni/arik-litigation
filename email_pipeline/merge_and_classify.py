"""
merge_and_classify.py
---------------------
Reads one, two, or three Aid4Mail JSON exports, merges and deduplicates them,
classifies each record with a strip_method, writes body_clean, and outputs
combined_repository.json + merge_report.json.

At startup, prompts for each input file via a file picker (remembers last folder).
Also prompts for output filename with overwrite protection.
"""

import json
import re
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timezone
from pathlib import Path
from strippers import get_body_clean

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR        = Path(__file__).parent
DEFAULT_EXPORT_DIR = SCRIPT_DIR.parent / "Aid4Mail Exports" / "Aid4 ti json 2dtime"
CONFIG_FILE       = SCRIPT_DIR / "Email_Body_Processing_Config.json"

# ---------------------------------------------------------------------------
# Persistent config (remembers last-used folders and output path)
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

def pick_input_file(label: str, last_dir: str) -> Path | None:
    """Ask Y/N, then open a file picker if yes. Returns Path or None."""
    answer = input(f"\nDo you have a {label} export to include? [y/n]: ").strip().lower()
    if not answer.startswith("y"):
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    chosen = filedialog.askopenfilename(
        title=f"Select {label} export file",
        initialdir=last_dir,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        parent=root,
    )
    root.destroy()

    if not chosen:
        print(f"  No file selected for {label} — skipping.")
        return None
    return Path(chosen)


def pick_output_file(last_path: str) -> Path:
    """Prompt for output filename via file picker, warn if it already exists."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    last = Path(last_path) if last_path else SCRIPT_DIR / "combined_repository.json"

    while True:
        chosen = filedialog.asksaveasfilename(
            title="Save combined_repository as...",
            initialdir=str(last.parent),
            initialfile=last.name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            confirmoverwrite=False,   # we handle the warning ourselves
            parent=root,
        )
        if not chosen:
            # User cancelled — ask if they want to abort
            abort = input("\nNo output file selected. Abort? [y/n]: ").strip().lower()
            if abort == "y":
                root.destroy()
                return None
            continue  # re-open picker

        out_path = Path(chosen)
        if out_path.exists():
            answer = input(
                f"\n  WARNING: '{out_path.name}' already exists.\n"
                f"  Overwrite it? [y = overwrite / n = pick a new name]: "
            ).strip().lower()
            if answer == "y":
                break
            # else loop back and re-open picker
        else:
            break

    root.destroy()
    return out_path

# ---------------------------------------------------------------------------
# Strip method classification
# ---------------------------------------------------------------------------

def get_strip_method(e: dict) -> str:
    body    = e.get("Body.SenderText", "") or ""
    html    = e.get("Body.HTML", "")       or ""
    subject = (e.get("Header.Subject", "") or "").strip()
    in_reply = (e.get("Header.In-Reply-To", "") or "").strip()

    first = re.match(r'^(re|fw|fwd)\s*[:\-]', subject, re.IGNORECASE)
    is_forward = first and first.group(1).lower() in ("fw", "fwd")

    if re.search(r'\binline\b', body, re.IGNORECASE):
        return "Inline"
    if is_forward:
        return "Forward"
    if "gmail_quote" in html.lower():
        return "Gmail"
    if "MsoNormal" in html:
        return "Outlook"
    if re.search(r'^>', body, re.MULTILINE):
        return "GT_Prefix"
    if 'dir="auto"' in html and in_reply:
        return "iOS"
    if re.search(r'^-{3,}.*original message.*-{3,}', body, re.IGNORECASE | re.MULTILINE):
        return "Outlook_Plain"
    if re.search(r'^From:\s.+\n(Subject|Date|Sent):', body, re.MULTILINE | re.IGNORECASE):
        return "Outlook_Plain"
    if re.search(r'On .{5,100} wrote:', body, re.IGNORECASE):
        return "OnWrote"
    if not in_reply:
        return "Original"
    return "Clean_Reply"


# ---------------------------------------------------------------------------
# Source type classification (informational)
# ---------------------------------------------------------------------------

def classify_source(e: dict) -> str:
    if e.get("Header.X-GM-THRID", "").strip():
        return "GMAIL_API"
    src = (e.get("Source.FileName", "") or e.get("Source.File", "") or "")
    if src.lower().endswith(".msg"):
        return "MSG_FILE"
    return "EML_FILE"


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def normalize_message_id(mid: str) -> str:
    mid = mid.strip().lower()
    if mid.startswith("<"):
        mid = mid[1:]
    if mid.endswith(">"):
        mid = mid[:-1]
    return mid


def score_record(e: dict) -> tuple:
    """Higher score = preferred winner.
    EML_FILE and MSG_FILE always beat GMAIL_API — file-based exports are
    the forensically authoritative copy."""
    src          = e.get("_input_source", "")
    src_priority = 2 if src in ("EML_FILE", "MSG_FILE") else 1
    has_filename = 1 if (e.get("Source.FileName", "") or e.get("Source.File", "")).strip() else 0
    body_size    = len(e.get("Body.Text", "") or "") + len(e.get("Body.HTML", "") or "")
    has_header   = 1 if e.get("Email.Header", "").strip() else 0
    run_date     = e.get("Session.RunDate", "9999-99-99")
    return (src_priority, has_filename, body_size, has_header, run_date)


def pick_winner(group: list) -> tuple:
    scored = sorted(group, key=score_record, reverse=True)
    return scored[0], scored[1:]


# ---------------------------------------------------------------------------
# Load a single JSON export file
# ---------------------------------------------------------------------------

def load_export(path: Path, source_label: str) -> list:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "emails" not in data or not isinstance(data["emails"], list):
        raise ValueError(f"Missing or invalid 'emails' array in {path}")
    records = data["emails"]
    for r in records:
        r["_input_source"] = source_label
    print(f"  Loaded {len(records):>5} records from {path.name}")
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("merge_and_classify.py")
    print(f"Run: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    cfg = load_config()
    default_dir = str(DEFAULT_EXPORT_DIR)

    # --- Prompt for input files ---
    print("\n[1] Select input files")

    sources = [
        ("Gmail",  "GMAIL_API", "last_gmail_dir"),
        ("EML",    "EML_FILE",  "last_eml_dir"),
        ("MSG",    "MSG_FILE",  "last_msg_dir"),
    ]

    selected_inputs = {}   # label → Path
    for display_name, label, cfg_key in sources:
        last_dir = cfg.get(cfg_key, default_dir)
        path = pick_input_file(display_name, last_dir)
        if path:
            selected_inputs[label] = path
            cfg[cfg_key] = str(path.parent)

    if not selected_inputs:
        print("\n  ERROR: No input files selected. Halting.")
        return

    # --- Prompt for output file ---
    print("\n[2] Select output file")
    last_output = cfg.get("last_output_path", str(SCRIPT_DIR / "combined_repository.json"))
    output_file = pick_output_file(last_output)
    if output_file is None:
        print("\n  Aborted.")
        return
    cfg["last_output_path"] = str(output_file)
    report_file = output_file.with_name(output_file.stem + "_report.json")

    save_config(cfg)

    # --- Load records ---
    print("\n[3] Loading exports...")
    all_records = []
    counts_per_file = {}
    for label, path in selected_inputs.items():
        records = load_export(path, label)
        counts_per_file[label] = len(records)
        all_records.extend(records)

    total_before = len(all_records)
    if total_before == 0:
        print("\n  ERROR: No records loaded. Halting.")
        return
    print(f"\n  Total before dedup: {total_before}")

    # --- Deduplicate ---
    print("\n[4] Deduplicating...")
    sha256_groups  = {}
    msgid_groups   = {}
    no_key_records = []
    sha256_dupe_count = 0
    msgid_dupe_count  = 0

    for r in all_records:
        sha = (r.get("Email.HashSHA256", "") or "").strip()
        mid = normalize_message_id(r.get("Header.Message-ID", "") or "")

        if sha:
            sha256_groups.setdefault(sha, []).append(r)
        elif mid:
            msgid_groups.setdefault(mid, []).append(r)
        else:
            no_key_records.append(r)

    winners  = []
    dupe_log = []

    for sha, group in sha256_groups.items():
        winner, losers = pick_winner(group)
        if losers:
            sha256_dupe_count += 1
            winner["Merge.DuplicateSessions"] = [r.get("Session.Id", "") for r in group]
            dupe_log.append({
                "key_type":       "SHA256",
                "key":            sha,
                "winner_session": winner.get("Session.Id", ""),
                "loser_sessions": [l.get("Session.Id", "") for l in losers],
                "sources":        [r.get("_input_source", "") for r in group],
            })
        winners.append(winner)

    for mid, group in msgid_groups.items():
        winner, losers = pick_winner(group)
        if losers:
            msgid_dupe_count += 1
            winner["Merge.DuplicateSessions"] = [r.get("Session.Id", "") for r in group]
            dupe_log.append({
                "key_type":       "Message-ID",
                "key":            mid,
                "winner_session": winner.get("Session.Id", ""),
                "loser_sessions": [l.get("Session.Id", "") for l in losers],
                "sources":        [r.get("_input_source", "") for r in group],
            })
        winners.append(winner)

    winners.extend(no_key_records)

    total_after = len(winners)
    print(f"  SHA256 dupe groups resolved:     {sha256_dupe_count}")
    print(f"  Message-ID dupe groups resolved: {msgid_dupe_count}")
    print(f"  Records with no key (kept all):  {len(no_key_records)}")
    print(f"  Total after dedup:               {total_after}")

    # --- Sort ---
    print("\n[5] Sorting by Header.Date...")
    winners.sort(key=lambda r: r.get("Header.Date", "") or r.get("Date.Display", "") or "")

    # --- Classify ---
    print("\n[6] Classifying strip method and writing body_clean...")
    method_counts = {}
    for r in winners:
        method = get_strip_method(r)
        r["strip_method"] = method
        r["body_clean"]   = get_body_clean(r, method)
        r.pop("_input_source", None)
        method_counts[method] = method_counts.get(method, 0) + 1

    print("\n  Strip method breakdown:")
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"    {method:<15} {count:>5}  ({count/total_after*100:.1f}%)")

    # --- Write output ---
    print(f"\n[7] Writing {output_file.name}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"emails": winners}, f, ensure_ascii=False, indent=2)
    print(f"  Written: {total_after} records")

    print(f"\n[8] Writing {report_file.name}...")
    report = {
        "run_timestamp":         datetime.now(timezone.utc).isoformat(),
        "output_file":           str(output_file),
        "counts_per_input_file": counts_per_file,
        "total_before_dedup":    total_before,
        "total_after_dedup":     total_after,
        "duplicates_removed":    total_before - total_after,
        "sha256_dupe_groups":    sha256_dupe_count,
        "msgid_fallback_groups": msgid_dupe_count,
        "records_with_no_key":   len(no_key_records),
        "strip_method_counts":   method_counts,
        "duplicate_groups":      dupe_log,
    }
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Written: {report_file.name}")

    print("\n" + "=" * 60)
    print("Done.")
    print("=" * 60)
    print(f"\nNEXT STEP: Export {output_file.name} to Excel.")
    answer = input(f"Export '{output_file.name}' to .xlsx now? [y/n]: ").strip().lower()
    if answer.startswith("y"):
        import subprocess, sys
        subprocess.run([sys.executable, str(SCRIPT_DIR / "export_all_emails.py"), str(output_file)], check=True)
    else:
        print("  Skipped. Run export_all_emails.py manually when ready.")
    print("=" * 60)


if __name__ == "__main__":
    main()
