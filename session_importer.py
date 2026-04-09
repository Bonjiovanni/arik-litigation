"""
session_importer.py — Merge Claude Code JSONL sessions across project folders.

Copies .jsonl session files from one ~/.claude/projects/<source>/ folder into
another, replacing only the top-level `cwd` field in each JSON line (Cat 1).
All other path references (tool I/O, text content) are left untouched.

Usage:
    python session_importer.py <source_dir> <target_dir> [--target-cwd PATH] [--dry-run]

Example:
    python session_importer.py ^
        "%USERPROFILE%\\.claude\\projects\\c--Users-arika-Repo-for-Claude-android" ^
        "%USERPROFILE%\\.claude\\projects\\C--Users-arika-OneDrive-CLaude-Cowork" ^
        --target-cwd "C:\\Users\\arika\\OneDrive\\CLaude Cowork"
"""

import json
import os
import shutil
import argparse


def _infer_cwd_from_folder_name(folder_path):
    """Best-effort: derive the original cwd from the project folder name.

    Folder names use the pattern C--Users-arika-somepath, which maps to
    C:\\Users\\arika\\somepath.  This is a guess and may not always be right,
    so callers should prefer the explicit --target-cwd flag.
    """
    name = os.path.basename(folder_path.rstrip("/\\"))
    # First character is the drive letter; the rest uses - as separator
    # but the real path may contain hyphens too, so this is fragile.
    parts = name.split("-")
    if len(parts) >= 2:
        drive = parts[0]
        rest = "\\".join(parts[1:])
        return f"{drive}:\\{rest}"
    return None


def _process_line(line, source_cwd_variants, target_cwd):
    """Process a single JSONL line: replace only top-level cwd field."""
    stripped = line.strip()
    if not stripped:
        return line

    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        # Malformed line — preserve as-is
        return line

    # Only replace the top-level "cwd" key
    if "cwd" in obj:
        current = obj["cwd"]
        # Check against all case variants of the source cwd
        for variant in source_cwd_variants:
            if current.lower() == variant.lower():
                obj["cwd"] = target_cwd
                break

    return json.dumps(obj, ensure_ascii=False) + "\n"


def _collect_source_cwd(source_dir):
    """Scan source JSONL files to find the cwd value used in them."""
    cwds = set()
    for name in os.listdir(source_dir):
        if not name.endswith(".jsonl"):
            continue
        path = os.path.join(source_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    if "cwd" in obj:
                        cwds.add(obj["cwd"])
                except (json.JSONDecodeError, KeyError):
                    pass
        if cwds:
            break  # one file is enough
    return cwds


def _process_jsonl_file(src_path, dst_path, source_cwd_variants, target_cwd):
    """Copy and transform a single JSONL file."""
    with open(src_path, "r", encoding="utf-8") as fin, \
         open(dst_path, "w", encoding="utf-8") as fout:
        for line in fin:
            fout.write(_process_line(line, source_cwd_variants, target_cwd))


def import_sessions(source_dir, target_dir, target_cwd=None, dry_run=False):
    """Import JSONL sessions from source_dir into target_dir.

    Args:
        source_dir:  Path to source project folder (e.g. ~/.claude/projects/c--...).
        target_dir:  Path to target project folder.
        target_cwd:  The working directory path to write into cwd fields.
                     If None, cwd fields are copied unchanged.
        dry_run:     If True, report what would happen without writing anything.

    Returns:
        dict with keys:
            copied (int): number of session files copied
            skipped (list[str]): filenames that already existed in target
            would_copy (int): dry-run only — files that would be copied
            would_skip (list[str]): dry-run only — files that would be skipped
    """
    result = {
        "copied": 0,
        "skipped": [],
        "would_copy": 0,
        "would_skip": [],
    }

    # Collect source cwd variants for case-insensitive matching
    source_cwd_variants = _collect_source_cwd(source_dir)

    # Process top-level .jsonl files
    jsonl_files = [f for f in os.listdir(source_dir) if f.endswith(".jsonl")]

    for name in jsonl_files:
        src_path = os.path.join(source_dir, name)
        dst_path = os.path.join(target_dir, name)

        if os.path.exists(dst_path):
            if dry_run:
                result["would_skip"].append(name)
            else:
                result["skipped"].append(name)
            continue

        if dry_run:
            result["would_copy"] += 1
            continue

        if target_cwd:
            _process_jsonl_file(src_path, dst_path, source_cwd_variants, target_cwd)
        else:
            shutil.copy2(src_path, dst_path)
        result["copied"] += 1

    # Process subdirectories (session folders with subagents/)
    for entry in os.listdir(source_dir):
        entry_path = os.path.join(source_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        target_entry_path = os.path.join(target_dir, entry)

        if dry_run:
            continue

        # Walk the subdirectory and copy any .jsonl files found
        for root, dirs, files in os.walk(entry_path):
            for fname in files:
                if not fname.endswith(".jsonl"):
                    continue
                src_file = os.path.join(root, fname)
                # Compute relative path from source entry
                rel = os.path.relpath(src_file, entry_path)
                dst_file = os.path.join(target_entry_path, rel)

                # Skip if already exists
                if os.path.exists(dst_file):
                    continue

                os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                if target_cwd:
                    _process_jsonl_file(src_file, dst_file, source_cwd_variants, target_cwd)
                else:
                    shutil.copy2(src_file, dst_file)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import Claude Code sessions from one project folder to another."
    )
    parser.add_argument("source", help="Source project folder path")
    parser.add_argument("target", help="Target project folder path")
    parser.add_argument(
        "--target-cwd",
        help="Working directory path to write into cwd fields",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without writing anything",
    )
    args = parser.parse_args()

    result = import_sessions(
        args.source, args.target,
        target_cwd=args.target_cwd,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"Would copy: {result['would_copy']} sessions")
        if result["would_skip"]:
            print(f"Would skip (already exist): {result['would_skip']}")
    else:
        print(f"Copied: {result['copied']} sessions")
        if result["skipped"]:
            print(f"Skipped (already exist): {result['skipped']}")
