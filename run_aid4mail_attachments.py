"""
run_aid4mail_attachments.py
---------------------------
CLI wrapper for running the Aid4Mail attachment extraction session with
Message-ID filtering (v16). Shows config, explains settings, asks Y/N,
then launches Aid4Mail.

Usage:
    python run_aid4mail_attachments.py
    python run_aid4mail_attachments.py --yes   (skip confirmation — for automation)
"""

import os
import sys
import csv
import subprocess
import configparser

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

AID4MAIL_EXE = r"C:\Program Files\Aid4Mail 6\Aid4Mail.exe"

SESSION_FILE = (
    r"C:\Users\arika\OneDrive\Documents\Aid4Mail\Projects"
    r"\Aid4Mail - get the clean data"
    r"\gmail to json attachments for integration w cloudhq python.settings.ini"
)

CONFIG_XLSX = r"C:\Users\arika\OneDrive\Documents\Aid4Mail\Attachment_Config_Aid4mail.xlsx"

SCRIPT_SETTINGS_INI = r"C:\Users\arika\AppData\Roaming\Aid4Mail6\Scripts\ScriptSettings.ini"

V16_SECTION = "attachment_manifest_v16_msgid_filter.flt.py"
DEFAULT_CSV = r"C:\Users\arika\OneDrive\Litigation\Pipeline\message_ids.csv"


# ---------------------------------------------------------------------------
# Read config
# ---------------------------------------------------------------------------

def read_attachment_config():
    """Read Attachment_Config_Aid4mail.xlsx and return (run_mode, prior_csv_names).

    run_mode: "fresh", "accumulate", or "incremental"
    """
    try:
        import openpyxl
        wb = openpyxl.load_workbook(CONFIG_XLSX, read_only=True, data_only=True)
        ws = wb.active
        data = {}
        for row in ws.iter_rows(values_only=True):
            if row[0] is not None and row[1] is not None:
                data[str(row[0]).strip().lower()] = str(row[1]).strip()
        wb.close()
    except Exception as exc:
        print(f"  WARNING: Could not read config workbook: {exc}")
        print(f"  Path: {CONFIG_XLSX}")
        return "fresh", []

    # New run_mode key takes precedence over legacy fresh_run
    explicit_mode = data.get("run_mode", "").strip().lower()
    if explicit_mode in ("fresh", "accumulate", "incremental"):
        run_mode = explicit_mode
    else:
        fresh = data.get("fresh_run", "true").lower() not in ("false", "0", "no")
        run_mode = "fresh" if fresh else "accumulate"

    names = []
    if run_mode in ("accumulate", "incremental"):
        i = 1
        while True:
            key = f"prior_csv_{i}"
            if key not in data:
                break
            n = data[key].strip()
            if n:
                names.append(n)
            i += 1
    return run_mode, names


def read_msgid_csv_path():
    """Read CSV_FILE from ScriptSettings.ini for v16."""
    csv_path = DEFAULT_CSV
    try:
        config = configparser.ConfigParser()
        config.read(SCRIPT_SETTINGS_INI, encoding="utf-8")
        val = config.get(V16_SECTION, "CSV_FILE", fallback=DEFAULT_CSV).strip()
        if val:
            csv_path = val
    except Exception:
        pass
    return csv_path


def count_msgids(csv_path):
    """Count valid Message-IDs in the CSV."""
    if not os.path.exists(csv_path):
        return 0, False
    count = 0
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, start=1):
                if not row:
                    continue
                val = row[0].strip()
                if not val or val.startswith("#") or val.startswith(";"):
                    continue
                if row_num == 1 and "message" in val.lower():
                    continue
                count += 1
    except Exception:
        return 0, False
    return count, True


# ---------------------------------------------------------------------------
# Display and confirm
# ---------------------------------------------------------------------------

def display_config():
    """Show all config with explanations. Returns True if user confirms."""
    print("=" * 70)
    print("Aid4Mail Attachment Extraction — v16 Message-ID Filter")
    print("=" * 70)

    # Session
    print(f"\nSession file:")
    print(f"  {SESSION_FILE}")
    if not os.path.exists(SESSION_FILE):
        print("  *** FILE NOT FOUND ***")

    # Attachment config
    print(f"\nAttachment config workbook:")
    print(f"  {CONFIG_XLSX}")
    run_mode, prior_csv_names = read_attachment_config()

    print(f"\n  run_mode = {run_mode}")
    if run_mode == "fresh":
        print("    -> Starting clean. Dedup maps will be EMPTY.")
        print("       Will NOT detect files already on disk from prior runs.")
        print("       Manifest will contain ONLY this run's rows.")
    elif run_mode == "incremental":
        print("    -> INCREMENTAL (straggler) run.")
        print("       Prior manifests loaded for dedup awareness ONLY.")
        print("       Output manifest contains ONLY new rows from this run.")
        print("       Attachment files deduped correctly against prior corpus.")
        print("       Use this for straggler/update runs.")
    else:  # accumulate
        print("    -> ACCUMULATE (full merge) run.")
        print("       Prior manifest rows copied into output + dedup maps seeded.")
        print("       Output manifest contains prior + new rows (complete corpus).")
        print("       Use this when merging multiple source formats (Gmail + EML + MSG).")

    print()
    if prior_csv_names:
        print("  Prior CSVs to load (must exist in Aid4Mail DataFolder):")
        for i, name in enumerate(prior_csv_names, 1):
            print(f"    prior_csv_{i} = {name}")
    else:
        print("  prior_csv_1 = (empty)")
        print("  prior_csv_2 = (empty)")
        if run_mode in ("accumulate", "incremental"):
            print(f"    *** WARNING: run_mode={run_mode} but no prior CSVs listed! ***")
            print("    Dedup maps will be empty — same as fresh.")

    # Message-ID filter
    csv_path = read_msgid_csv_path()
    id_count, csv_exists = count_msgids(csv_path)

    print(f"\nMessage-ID filter CSV:")
    print(f"  {csv_path}")
    if not csv_exists:
        print("  *** FILE NOT FOUND ***")
    elif id_count == 0:
        print("  *** CSV IS EMPTY — no Message-IDs to filter ***")
    else:
        print(f"  {id_count} Message-IDs loaded")

    # Warnings
    print()
    if not csv_exists or id_count == 0:
        print("*** CANNOT PROCEED — Message-ID CSV is missing or empty ***")
        return False

    print("=" * 70)
    return True


def confirm():
    """Ask Y/N."""
    while True:
        answer = input("\nProceed with this configuration? [Y/N]: ").strip().upper()
        if answer == "Y":
            return True
        if answer == "N":
            print("Aborted.")
            return False
        print("Please enter Y or N.")


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

def launch_aid4mail():
    """Launch Aid4Mail with /run /minimized /exit."""
    cmd = [AID4MAIL_EXE, "/run", SESSION_FILE, "/minimized", "/exit"]
    print(f"\nLaunching Aid4Mail...")
    print(f"  {' '.join(cmd)}")
    subprocess.Popen(cmd)
    print("Aid4Mail started. It will exit automatically when done.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config_ok = display_config()
    if not config_ok:
        sys.exit(1)

    if "--yes" in sys.argv:
        print("\n--yes flag: skipping confirmation.")
    else:
        if not confirm():
            sys.exit(0)

    launch_aid4mail()


if __name__ == "__main__":
    main()
