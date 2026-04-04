"""
fw_dirmap_grp3.py
-----------------
Directory mapper agent module — Group 3 component.

Provides build_dir_records(), which walks one or more root directories,
calls the shared helper functions (validate_and_normalize_path,
detect_source_store, count_dir_contents, walk_directories), and returns
a flat list of DirRecord dicts in tree order (parents before children).

Windows 10 only.  No third-party pip dependencies.
"""

import os
import sys

# ---------------------------------------------------------------------------
# NOTE: The four helper functions below are defined elsewhere in the project.
# They are imported at runtime by whichever entry-point wires up sys.path.
# If you run this module standalone during development, ensure the module
# that defines them is on sys.path before importing.
#
#   validate_and_normalize_path(raw: str) -> str
#   detect_source_store(path: str) -> str
#   count_dir_contents(dir_path: str) -> tuple[int, int]   # (file_count, subdir_count)
#   walk_directories(root, recursive, max_depth) -> generator of (full_path: str, depth: int)
#
# These are NOT redefined here — only called.
# ---------------------------------------------------------------------------

# NOTE FOR MERGE: replace 'fw_helpers' with actual module name during merge into fw_dirmap.py
# from fw_helpers import (
#     validate_and_normalize_path,
#     detect_source_store,
#     count_dir_contents,
#     walk_directories,
# )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PROGRESS_INTERVAL = 50  # print a milestone message every N directories


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_dir_records(
    roots: list,
    recursive: bool,
    max_depth,
    run_id: str,
    # Injected dependencies (for testing and merging into single module)
    _validate=None,
    _detect_store=None,
    _count_contents=None,
    _walk=None,
) -> list:
    """Walk one or more root directories and return a list of DirRecord dicts.

    Parameters
    ----------
    roots : list[str]
        Raw (un-normalized) or already-normalized root paths to scan.
        Each element is passed through validate_and_normalize_path() before use.
    recursive : bool
        Whether to descend into sub-directories.
    max_depth : int | None
        Maximum descent depth (None = unlimited).
    run_id : str
        Opaque run identifier injected into every DirRecord for traceability.

    Returns
    -------
    list[dict]
        DirRecord dicts in tree order (parents appear before their children),
        across all roots combined.  Dir IDs are sequential across all roots
        (D001, D002, ... -- never reset between roots).

    DirRecord schema
    ----------------
    {
        "dir_id":       str,   # e.g. "D001"
        "scan_root":    str,   # normalized path of the root this dir belongs to
        "relative_dir": str,   # os.path.relpath from scan_root, forward-slashes;
                               # "." if the dir IS the scan_root
        "dir_name":     str,   # basename of full_path; last segment of root for depth=0
        "full_path":    str,   # full normalized path (forward slashes)
        "depth":        int,   # 0 = scan_root itself
        "file_count":   int,
        "subdir_count": int,
        "source_store": str,
        "run_id":       str,
    }
    """
    # Allow dependency injection for testing; fall back to real imports at runtime
    if _validate is None:
        from fw_dirmap_grp1 import validate_and_normalize_path as _validate
    if _detect_store is None:
        from fw_dirmap_grp2 import detect_source_store as _detect_store
    if _count_contents is None:
        from fw_dirmap_grp2 import count_dir_contents as _count_contents
    if _walk is None:
        from fw_dirmap_grp2 import walk_directories as _walk

    all_records = []   # accumulates every DirRecord across all roots
    dir_counter = 0    # global sequential counter -- never resets per root

    for raw_root in roots:
        # ------------------------------------------------------------------
        # 1. Normalize the root path so all downstream code works with a
        #    consistent, absolute, forward-slash path.
        # ------------------------------------------------------------------
        scan_root = _validate(raw_root)

        print(f"  Scanning: {scan_root}")

        # ------------------------------------------------------------------
        # 2. Walk the directory tree.
        #    walk_directories yields (full_path, depth) in tree order.
        # ------------------------------------------------------------------
        for full_path, depth in _walk(scan_root, recursive, max_depth):

            # ---- progress feedback ----------------------------------------
            dir_counter += 1
            if dir_counter % _PROGRESS_INTERVAL == 0:
                print(f"  ... {dir_counter} dirs found")

            # ---- normalize the yielded path to forward slashes ------------
            full_path_fwd = full_path.replace("\\", "/")

            # ---- relative_dir ---------------------------------------------
            if os.path.normcase(full_path) == os.path.normcase(scan_root):
                relative_dir = "."
            else:
                relative_dir = os.path.relpath(full_path, scan_root).replace("\\", "/")

            # ---- dir_name -------------------------------------------------
            if depth == 0:
                dir_name = os.path.basename(scan_root.rstrip("/\\"))
            else:
                dir_name = os.path.basename(full_path)

            # ---- dir_id ---------------------------------------------------
            dir_id = f"D{dir_counter:03d}"

            # ---- delegated calls ------------------------------------------
            file_count, subdir_count = _count_contents(full_path)
            source_store = _detect_store(full_path)

            # ---- assemble record ------------------------------------------
            record = {
                "dir_id":       dir_id,
                "scan_root":    scan_root,
                "relative_dir": relative_dir,
                "dir_name":     dir_name,
                "full_path":    full_path_fwd,
                "depth":        depth,
                "file_count":   file_count,
                "subdir_count": subdir_count,
                "source_store": source_store,
                "run_id":       run_id,
            }

            all_records.append(record)

    print(f"  Done. Total directories mapped: {dir_counter}")
    return all_records
