"""
fw_dir_tree.py
--------------
Drive Directory Tree Scanner — parallel edition.

Scans one or more root paths using parallel PowerShell processes for maximum
speed, then aggregates per-directory file counts and sizes.

Speed strategy:
  Each root is expanded to its immediate subdirectories. One PowerShell process
  is launched per subdirectory simultaneously. On an SSD this saturates I/O
  bandwidth far better than a single recursive scan.

Output: directory_tree.csv
  full_path, parent_path, dir_name, depth,
  direct_file_count, direct_size_bytes, total_file_count, total_size_bytes

  depth = levels from drive root (C:\\ = 0, C:\\Users = 1, etc.)
  direct_* = this folder only, not subdirectories
  total_*  = this folder plus all subdirectories recursively

Usage:
  python fw_dir_tree.py --paths "C:\\Users\\arika\\OneDrive"
  python fw_dir_tree.py --paths "C:\\Users,C:\\Data" --exclude "C:\\Users\\AppData"
  python fw_dir_tree.py --paths "C:\\" --exclude "C:\\Windows,C:\\Program Files" --workers 16

Arguments:
  --paths    Comma-separated root paths to scan (required)
  --exclude  Comma-separated paths to exclude (optional)
  --output   Output CSV path (default: directory_tree.csv)
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
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a directory tree CSV with file counts and sizes."
    )
    parser.add_argument("--paths",   required=True,
                        help="Comma-separated root paths to scan")
    parser.add_argument("--exclude", default="",
                        help="Comma-separated paths to exclude")
    parser.add_argument("--output",  default="directory_tree.csv",
                        help="Output CSV path (default: directory_tree.csv)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Max parallel PowerShell processes (default: 8)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------

def normalize(p: str) -> str:
    return str(Path(p.strip()).resolve())


def get_depth(path_str: str) -> int:
    """Depth from drive root: C:\\ = 0, C:\\Users = 1, etc."""
    return len(Path(path_str).parts) - 1


def is_excluded(path_str: str, excludes: list[str]) -> bool:
    p = path_str.lower()
    return any(p == ex.lower() or p.startswith(ex.lower() + os.sep) for ex in excludes if ex)


def expand_to_subdirs(roots: list[str], excludes: list[str]) -> list[str]:
    """
    Expand each root to its immediate subdirectories for parallelism.
    Roots with no accessible subdirectories are kept as-is.
    The root itself is always included as a scan unit so we don't miss
    files sitting directly in the root.
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
            # Also scan files directly in root (depth-0 files won't be in any subdir scan)
            units.append(root + "|files_only")
        else:
            units.append(root)

    return units


# ---------------------------------------------------------------------------
# PowerShell enumeration (single scan unit)
# ---------------------------------------------------------------------------

def _ps_scan_unit(scan_target: str, tmpdir: str, index: int) -> dict:
    """
    Run PowerShell to dump files (and optionally directories) for one scan unit.
    Returns dict with paths to the temp CSV files produced.
    """
    files_only = scan_target.endswith("|files_only")
    root = scan_target.replace("|files_only", "")

    temp_files = os.path.join(tmpdir, f"files_{index:04d}.csv")
    temp_dirs  = os.path.join(tmpdir, f"dirs_{index:04d}.csv")

    if files_only:
        # Shallow scan: only immediate files of the root (no recursion)
        file_script = f"""
Get-ChildItem -LiteralPath "{root}" -File -Force -ErrorAction SilentlyContinue |
    Select-Object FullName,
                  @{{n='DirectoryName';e={{$_.DirectoryName}}}},
                  Length |
    Export-Csv -LiteralPath "{temp_files}" -NoTypeInformation -Encoding UTF8
"""
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", file_script],
            capture_output=True, text=True
        )
        return {"files": temp_files, "dirs": None}

    # Full recursive scan
    file_script = f"""
Get-ChildItem -LiteralPath "{root}" -Recurse -File -Force -ErrorAction SilentlyContinue |
    Select-Object FullName,
                  @{{n='DirectoryName';e={{$_.DirectoryName}}}},
                  Length |
    Export-Csv -LiteralPath "{temp_files}" -NoTypeInformation -Encoding UTF8
"""
    dir_script = f"""
$rows = @(Get-Item -LiteralPath "{root}" -ErrorAction SilentlyContinue |
              Where-Object {{ $_.PSIsContainer }}) +
        @(Get-ChildItem -LiteralPath "{root}" -Recurse -Directory -Force -ErrorAction SilentlyContinue)
$rows | Select-Object FullName |
        Export-Csv -LiteralPath "{temp_dirs}" -NoTypeInformation -Encoding UTF8
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", file_script],
        capture_output=True, text=True
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", dir_script],
        capture_output=True, text=True
    )
    return {"files": temp_files, "dirs": temp_dirs}


def run_parallel_dumps(scan_units: list[str], tmpdir: str, max_workers: int) -> list[dict]:
    """Launch one PowerShell scan per unit in parallel; collect temp file paths."""
    results = []
    print(f"  Launching {len(scan_units)} parallel scans (workers={max_workers})...")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_ps_scan_unit, unit, tmpdir, i): unit
            for i, unit in enumerate(scan_units)
        }
        done = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            if done % 10 == 0 or done == len(scan_units):
                print(f"  Scans complete: {done}/{len(scan_units)}")

    return results


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def build_records(scan_results: list[dict], excludes: list[str]) -> list[dict]:
    """
    1. Load all directories from temp dir CSVs.
    2. Load all files from temp file CSVs; accumulate direct counts/sizes.
    3. Sort deepest-first and propagate totals upward to parents.
    4. Return sorted list of record dicts.
    """

    dirs: dict[str, str] = {}          # lower_path → canonical_path
    direct_count: dict[str, int] = defaultdict(int)
    direct_size:  dict[str, int] = defaultdict(int)

    for result in scan_results:
        # --- directories ---
        if result.get("dirs") and os.path.exists(result["dirs"]):
            with open(result["dirs"], encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    fp = row.get("FullName", "").strip()
                    if not fp:
                        continue
                    fp = str(Path(fp))
                    if not is_excluded(fp, excludes):
                        dirs[fp.lower()] = fp

        # --- files ---
        if result.get("files") and os.path.exists(result["files"]):
            with open(result["files"], encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    full_name = row.get("FullName", "").strip()
                    dir_name  = row.get("DirectoryName", "").strip()
                    length    = row.get("Length", "0").strip()

                    if not full_name or not dir_name:
                        continue
                    dir_name = str(Path(dir_name))
                    if is_excluded(full_name, excludes):
                        continue

                    try:
                        size = int(length) if length else 0
                    except ValueError:
                        size = 0

                    dk = dir_name.lower()
                    if dk not in dirs:
                        dirs[dk] = dir_name
                    direct_count[dk] += 1
                    direct_size[dk]  += size

    # --- bottom-up total aggregation ---
    all_dirs = sorted(dirs.values(), key=lambda p: len(Path(p).parts), reverse=True)

    total_count: dict[str, int] = {d.lower(): direct_count[d.lower()] for d in all_dirs}
    total_size:  dict[str, int] = {d.lower(): direct_size[d.lower()]  for d in all_dirs}

    for d in all_dirs:
        parent = Path(d).parent
        if str(parent).lower() == d.lower():   # drive root
            continue
        pk = str(parent).lower()
        if pk in total_count:
            total_count[pk] += total_count[d.lower()]
            total_size[pk]  += total_size[d.lower()]

    # --- build output records ---
    records = []
    for d in sorted(dirs.values()):
        p   = Path(d)
        par = str(p.parent)
        parent_path = "" if par.lower() == d.lower() else par
        dir_name    = p.name if p.name else d
        dk = d.lower()

        records.append({
            "full_path":          d,
            "parent_path":        parent_path,
            "dir_name":           dir_name,
            "depth":              get_depth(d),
            "direct_file_count":  direct_count[dk],
            "direct_size_bytes":  direct_size[dk],
            "total_file_count":   total_count[dk],
            "total_size_bytes":   total_size[dk],
        })

    return records


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

FIELDNAMES = [
    "full_path", "parent_path", "dir_name", "depth",
    "direct_file_count", "direct_size_bytes",
    "total_file_count",  "total_size_bytes",
]

def write_csv(records: list[dict], output_path: str):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)
    print(f"  Written {len(records):,} directory records → {output_path}")


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

    print(f"fw_dir_tree  started  {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  Roots   : {', '.join(roots)}")
    if excludes:
        print(f"  Exclude : {', '.join(excludes)}")

    scan_units = expand_to_subdirs(roots, excludes)
    print(f"  Expanded to {len(scan_units)} parallel scan units")

    with tempfile.TemporaryDirectory() as tmpdir:
        scan_results = run_parallel_dumps(scan_units, tmpdir, args.workers)
        print("  Aggregating...")
        records = build_records(scan_results, excludes)

    write_csv(records, args.output)
    print(f"fw_dir_tree  done     {datetime.now():%Y-%m-%d %H:%M:%S}")


if __name__ == "__main__":
    main()
