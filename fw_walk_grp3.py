"""
fw_walk_grp3.py
---------------
Overlap detection and file-walking orchestration for fw_walk.py.

Provides:
    PROCESSING_LEVEL_ORDER  — ordered list of processing depth strings
    get_covered_paths       — read Dir_Processing_Status; return paths already
                              walked to at least the target depth
    check_overlap           — compare scan dirs against covered paths
    prompt_overlap_decision — console prompt: skip / rewalk / abort
    walk_files              — walk dirs, call grp1/grp2 per file, return stats

Imports fw_walk_grp1 and fw_walk_grp2 at call time (no circular imports).
Python 3.11, Windows 10.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Processing level ordering
# ---------------------------------------------------------------------------

PROCESSING_LEVEL_ORDER: list[str] = [
    "file_listed",
    "hashed",
    "classified",
    "text_extracted",
    "ocr_complete",
    "entity_matched",
    "triaged",
]


def _level_index(level: str) -> int:
    """Return the depth index for a level string, or -1 if unrecognised."""
    try:
        return PROCESSING_LEVEL_ORDER.index(level)
    except ValueError:
        return -1


def _normalize_path(p: str) -> str:
    return p.replace("\\", "/").rstrip("/").lower()


# ---------------------------------------------------------------------------
# FUNCTION 1: get_covered_paths
# ---------------------------------------------------------------------------

def get_covered_paths(ws_status, target_level: str) -> "dict[str, str]":
    """Return paths from Dir_Processing_Status already at or above target_level.

    Scans the Dir_Processing_Status worksheet (column C = DirPath,
    column E = ProcessingLevel). For each path, tracks the highest
    processing level seen. Returns only those paths whose highest level
    index >= target_level index.

    Args:
        ws_status:    openpyxl Worksheet for Dir_Processing_Status.
        target_level: The processing level the current walk intends to reach.

    Returns:
        dict mapping normalized_path -> highest_level_string, for all
        paths that are already covered at or above target_level depth.
        Returns {} if worksheet has no data rows or target_level is unknown.

    Dir_Processing_Status column layout (1-based):
        A: DirID
        B: RunID
        C: DirPath
        D: ProcessingLevel
        E: Status
        F: LastUpdated
    """
    target_idx = _level_index(target_level)
    if target_idx < 0:
        return {}

    # First pass: find highest level per path
    highest: dict[str, str] = {}

    for row in ws_status.iter_rows(min_row=2, values_only=True):
        if not row or row[2] is None or row[3] is None:
            continue
        path  = _normalize_path(str(row[2]))
        level = str(row[3]).strip()

        if path not in highest:
            highest[path] = level
        else:
            if _level_index(level) > _level_index(highest[path]):
                highest[path] = level

    # Second pass: filter to only those at or above target
    return {
        path: level
        for path, level in highest.items()
        if _level_index(level) >= target_idx
    }


# ---------------------------------------------------------------------------
# FUNCTION 2: check_overlap
# ---------------------------------------------------------------------------

def check_overlap(
    scan_dirs: "list[str]",
    covered_paths: "dict[str, str]",
) -> "list[dict]":
    """Compare scan_dirs against covered_paths to detect overlaps.

    A directory is overlapping when its normalized path appears as a key
    in covered_paths (meaning it was already walked to at least the
    requested depth).

    Args:
        scan_dirs:     List of directory paths to be walked (raw strings).
        covered_paths: Output of get_covered_paths().

    Returns:
        List of overlap dicts, one per overlapping directory::

            {
                "path":           str,  # normalized path
                "existing_level": str,  # level already on record
            }

        Returns [] if no overlaps.
    """
    overlaps = []
    for raw_dir in scan_dirs:
        norm = _normalize_path(raw_dir)
        if norm in covered_paths:
            overlaps.append({
                "path":           norm,
                "existing_level": covered_paths[norm],
            })
    return overlaps


# ---------------------------------------------------------------------------
# FUNCTION 3: prompt_overlap_decision
# ---------------------------------------------------------------------------

def prompt_overlap_decision(overlaps: "list[dict]") -> str:
    """Print overlap summary and prompt the user for a global decision.

    Args:
        overlaps: Output of check_overlap() — non-empty list.

    Returns:
        One of: "skip", "rewalk", "abort".

    Prints to stdout. Re-prompts on invalid input.
    """
    print("\n[fw_walk] Overlap detected — the following directories have already")
    print("been walked to the requested depth or deeper:\n")
    for o in overlaps:
        print(f"  {o['path']}  (already: {o['existing_level']})")

    print("\nOptions:")
    print("  [S] Skip overlapping directories (only walk new/unprocessed)")
    print("  [R] Re-walk all directories (overwrite existing records)")
    print("  [A] Abort\n")

    _choices = {"s": "skip", "r": "rewalk", "a": "abort"}
    while True:
        raw = input("Enter choice [S/R/A]: ").strip().lower()
        if raw in _choices:
            return _choices[raw]
        print("  Invalid — please enter S, R, or A.")


# ---------------------------------------------------------------------------
# FUNCTION 4: walk_files
# ---------------------------------------------------------------------------

def walk_files(
    scan_dirs: "list[str]",
    run_id: str,
    processing_level: str,
    wb,
    overlap_action: str = "skip",
) -> dict:
    """Walk directories, inventory every file, and write to Master_File_Inventory.

    For each file:
      1. Collect metadata (fw_walk_grp1.get_file_metadata)
      2. Classify file family (fw_walk_grp1.classify_file_family)
      3. Determine skip (fw_walk_grp1.should_skip_file)
      4. For archives: peek inside (fw_walk_grp1.peek_archive_contents)
      5. If level >= "hashed": compute SHA-256 (fw_walk_grp1.compute_sha256)
      6. Write/update record (fw_walk_grp2.write_or_update_file_record)

    Args:
        scan_dirs:        Already-validated, forward-slash paths to walk.
        run_id:           Run ID string (e.g. "WALK_20260315_143022").
        processing_level: Target level string (must be in PROCESSING_LEVEL_ORDER).
        wb:               Open openpyxl Workbook — caller is responsible for saving.
        overlap_action:   "skip" | "rewalk" — how to handle dirs already covered.
                          "skip" means those dirs are excluded from this walk;
                          the caller must have already filtered scan_dirs or
                          pass only dirs not in covered_paths when using "skip".

    Returns:
        Stats dict::

            {
                "inserted":     int,
                "updated":      int,
                "skipped_files": int,
                "skipped_dirs":  int,
                "errors":        int,
                "error_paths":   list[str],
            }
    """
    import fw_walk_grp1
    import fw_walk_grp2

    do_hash = _level_index(processing_level) >= _level_index("hashed")

    # Load family config from workbook (falls back to built-ins inside grp1)
    fc_ws = fw_walk_grp2.ensure_file_family_config_sheet(wb)
    family_map, skip_families = fw_walk_grp1.load_file_family_config(fc_ws)

    stats: dict = {
        "inserted":      0,
        "updated":       0,
        "skipped_files": 0,
        "skipped_dirs":  0,
        "errors":        0,
        "error_paths":   [],
    }

    for raw_dir in scan_dirs:
        norm_dir = raw_dir.replace("\\", "/").rstrip("/")

        # os.walk the directory tree
        try:
            walker = os.walk(norm_dir, topdown=True, followlinks=False)
        except PermissionError as exc:
            stats["errors"] += 1
            stats["error_paths"].append(norm_dir)
            print(f"[fw_walk] WARNING: cannot walk {norm_dir}: {exc}", file=sys.stderr)
            stats["skipped_dirs"] += 1
            continue

        for dirpath, dirnames, filenames in walker:
            # Prune inaccessible subdirectories in-place
            accessible = []
            for d in dirnames:
                subpath = os.path.join(dirpath, d)
                try:
                    os.scandir(subpath).close()
                    accessible.append(d)
                except PermissionError:
                    stats["skipped_dirs"] += 1
                    print(
                        f"[fw_walk] WARNING: permission denied, skipping dir: {subpath}",
                        file=sys.stderr,
                    )
            dirnames[:] = accessible

            for filename in filenames:
                filepath = os.path.join(dirpath, filename).replace("\\", "/")

                try:
                    meta = fw_walk_grp1.get_file_metadata(filepath)
                    file_family = fw_walk_grp1.classify_file_family(
                        meta["filename"], meta["extension"], family_map
                    )
                    should_skip, skip_reason = fw_walk_grp1.should_skip_file(
                        meta["filename"], meta["extension"], file_family, skip_families
                    )

                    # For archives: peek contents before marking as skipped
                    archive_contents = ""
                    if should_skip and file_family == "archive":
                        archive_contents = fw_walk_grp1.peek_archive_contents(filepath)

                    # Hash if level requires it (and file not skipped, or
                    # archive/email where we still want the hash for dedup)
                    sha256 = ""
                    if do_hash and not should_skip:
                        hash_hex, is_complete = fw_walk_grp1.compute_sha256(filepath)
                        if hash_hex:
                            sha256 = hash_hex if is_complete else hash_hex + "_partial"

                    record = {
                        "file_path":        meta["file_path"],
                        "parent_folder":    meta["parent_folder"],
                        "filename":         meta["filename"],
                        "scan_root_path":   norm_dir,
                        "source_store":     "",     # set by caller / fw_dirmap detect
                        "size_bytes":       meta["size_bytes"],
                        "created_time":     meta["created_time"],
                        "modified_time":    meta["modified_time"],
                        "sha256":           sha256,
                        "is_duplicate_exact": "",
                        "duplicate_group_id": "",
                        "file_family":      file_family,
                        "source_type":      "standalone_file",
                        "likely_text_bearing": "",
                        "likely_image":     "",
                        "likely_spreadsheet": "",
                        "likely_document":  "",
                        "likely_screenshot": "",
                        "needs_ocr":        "",
                        "is_container_type": "Y" if file_family == "archive" else "",
                        "skip_reason":      skip_reason,
                        "archive_contents": archive_contents,
                        "processing_status": processing_level,
                    }

                    if should_skip:
                        stats["skipped_files"] += 1
                        # Still log skipped files (archive/email) so they appear
                        # in the inventory with SkipReason set
                        fw_walk_grp2.write_or_update_file_record(wb, record, run_id)
                    else:
                        action, _ = fw_walk_grp2.write_or_update_file_record(
                            wb, record, run_id
                        )
                        if action == "inserted":
                            stats["inserted"] += 1
                        else:
                            stats["updated"] += 1

                except (PermissionError, OSError) as exc:
                    stats["errors"] += 1
                    stats["error_paths"].append(filepath)
                    print(
                        f"[fw_walk] WARNING: error processing {filepath}: {exc}",
                        file=sys.stderr,
                    )

    return stats
