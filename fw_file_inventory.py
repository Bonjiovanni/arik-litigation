"""
fw_file_inventory.py
--------------------
File Inventory Scanner — parallel edition.

Scans specified directories using parallel PowerShell processes for maximum
speed and outputs a flat CSV of every file with key metadata.

Speed strategy:
  Each root is expanded to its immediate subdirectories. One PowerShell process
  is launched per subdirectory simultaneously. On an SSD this saturates I/O
  bandwidth far better than a single recursive scan.

Output: file_inventory.csv
  full_path, directory, filename, extension, size_bytes, modified_date

Usage:
  python fw_file_inventory.py --paths "C:\\Users\\arika\\OneDrive\\Litigation"
  python fw_file_inventory.py --paths "C:\\Users,C:\\Data" --exclude "C:\\Users\\AppData"
  python fw_file_inventory.py --paths "C:\\Users" --workers 16 --output my_files.csv

Arguments:
  --paths    Comma-separated root paths to scan (required)
  --exclude  Comma-separated paths to exclude (optional)
  --output   Output CSV path (default: file_inventory.csv)
  --workers  Max parallel PowerShell processes (default: 8)

Platform: Windows 10
Python:   3.11+
No pip deps beyond stdlib.
"""

import argparse
import csv
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a file inventory CSV with metadata."
    )
    parser.add_argument("--paths",   required=True,
                        help="Comma-separated root paths to scan")
    parser.add_argument("--exclude", default="",
                        help="Comma-separated paths to exclude")
    parser.add_argument("--output",  default="file_inventory.csv",
                        help="Output CSV path (default: file_inventory.csv)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Max parallel PowerShell processes (default: 8)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------

def normalize(p: str) -> str:
    return str(Path(p.strip()).resolve())


def is_excluded(path_str: str, excludes: list[str]) -> bool:
    p = path_str.lower()
    return any(p == ex.lower() or p.startswith(ex.lower() + os.sep) for ex in excludes if ex)


def expand_to_subdirs(roots: list[str], excludes: list[str]) -> list[str]:
    """
    Expand each root to its immediate subdirectories for parallelism.
    The root itself is kept as a unit so files sitting directly in it
    are not missed.
    """
    units = []
    for root in roots:
        if is_excluded(root, excludes):
            continue
        try:
            subdirs = [
                os.path.join(root, name)
                for name in os.listdir(root)
                if os.path.isdir(os.path.join(root, name))
                   and not is_excluded(os.path.join(root, name), excludes)
            ]
        except PermissionError:
            subdirs = []

        if subdirs:
            units.extend(subdirs)
            units.append(root + "|shallow")   # catch files directly in root
        else:
            units.append(root)

    return units


# ---------------------------------------------------------------------------
# PowerShell enumeration (single scan unit)
# ---------------------------------------------------------------------------

def _ps_scan_unit(scan_target: str, tmpdir: str, index: int) -> str:
    """Run PowerShell for one scan unit; return path to temp CSV."""
    shallow = scan_target.endswith("|shallow")
    root    = scan_target.replace("|shallow", "")
    temp    = os.path.join(tmpdir, f"files_{index:04d}.csv")

    recurse_flag = "" if shallow else "-Recurse"

    script = f"""
Get-ChildItem -LiteralPath "{root}" {recurse_flag} -File -Force -ErrorAction SilentlyContinue |
    Select-Object FullName,
                  @{{n='DirectoryName'; e={{$_.DirectoryName}}}},
                  Name,
                  Extension,
                  Length,
                  @{{n='LastWriteDate';  e={{$_.LastWriteTime.ToString('yyyy-MM-dd')}}}} |
    Export-Csv -LiteralPath "{temp}" -NoTypeInformation -Encoding UTF8
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True
    )
    return temp


def run_parallel_dumps(scan_units: list[str], tmpdir: str, max_workers: int) -> list[str]:
    """Launch parallel PowerShell scans; return list of temp CSV paths."""
    temp_files = []
    print(f"  Launching {len(scan_units)} parallel scans (workers={max_workers})...")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_ps_scan_unit, unit, tmpdir, i): unit
            for i, unit in enumerate(scan_units)
        }
        done = 0
        for future in as_completed(futures):
            temp_files.append(future.result())
            done += 1
            if done % 10 == 0 or done == len(scan_units):
                print(f"  Scans complete: {done}/{len(scan_units)}")

    return temp_files


# ---------------------------------------------------------------------------
# Merge and write
# ---------------------------------------------------------------------------

FIELDNAMES = ["full_path", "directory", "filename", "extension", "size_bytes", "modified_date"]


def merge_and_write(temp_files: list[str], excludes: list[str], output_path: str):
    count = 0
    seen  = set()   # deduplicate in case subdirs overlap

    with open(output_path, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for temp in temp_files:
            if not os.path.exists(temp):
                continue
            with open(temp, encoding="utf-8-sig") as in_f:
                for row in csv.DictReader(in_f):
                    fp = row.get("FullName", "").strip()
                    if not fp:
                        continue
                    fp = str(Path(fp))
                    if is_excluded(fp, excludes):
                        continue
                    fp_lower = fp.lower()
                    if fp_lower in seen:
                        continue
                    seen.add(fp_lower)

                    try:
                        size = int(row.get("Length", "0").strip() or "0")
                    except ValueError:
                        size = 0

                    writer.writerow({
                        "full_path":     fp,
                        "directory":     str(Path(fp).parent),
                        "filename":      row.get("Name", "").strip(),
                        "extension":     row.get("Extension", "").strip().lower(),
                        "size_bytes":    size,
                        "modified_date": row.get("LastWriteDate", "").strip(),
                    })
                    count += 1

    print(f"  Written {count:,} file records → {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args     = parse_args()
    roots    = [normalize(p) for p in args.paths.split(",")   if p.strip()]
    excludes = [normalize(p) for p in args.exclude.split(",") if p.strip()]

    if not roots:
        print("Error: --paths is required.")
        sys.exit(1)

    print(f"fw_file_inventory  started  {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  Roots   : {', '.join(roots)}")
    if excludes:
        print(f"  Exclude : {', '.join(excludes)}")

    scan_units = expand_to_subdirs(roots, excludes)
    print(f"  Expanded to {len(scan_units)} parallel scan units")

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_files = run_parallel_dumps(scan_units, tmpdir, args.workers)
        print("  Merging results...")
        merge_and_write(temp_files, excludes, args.output)

    print(f"fw_file_inventory  done     {datetime.now():%Y-%m-%d %H:%M:%S}")


if __name__ == "__main__":
    main()
