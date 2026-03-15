"""
fw_dirmap_grp2.py
Part of the fw_dirmap directory mapper agent.
Windows 10 only. No third-party dependencies.

Functions:
    detect_source_store  -- identify cloud or local storage from a path string
    count_dir_contents   -- count files and subdirs at one level (no recursion)
    walk_directories     -- generator yielding (path, depth) tuples with depth control
"""

import os
import sys


# ---------------------------------------------------------------------------
# FUNCTION 1
# ---------------------------------------------------------------------------

def detect_source_store(path: str) -> str:
    """Identify the backing store for a given normalized forward-slash path.

    Matching is case-insensitive so that path variations on Windows
    (e.g. 'onedrive' vs 'OneDrive') are handled correctly.

    Args:
        path: A normalized path string that uses forward slashes as separators.

    Returns:
        "OneDrive"        -- path contains '/OneDrive/' or ends with '/OneDrive'
        "GoogleDriveSync" -- path contains '/Google Drive/' or '/GoogleDrive/'
        "Local"           -- anything else
    """
    lower = path.lower()

    if "/onedrive/" in lower or lower.endswith("/onedrive"):
        return "OneDrive"

    if "/google drive/" in lower or "/googledrive/" in lower:
        return "GoogleDriveSync"

    return "Local"


# ---------------------------------------------------------------------------
# FUNCTION 2
# ---------------------------------------------------------------------------

def count_dir_contents(dir_path: str) -> tuple:
    """Count the files and immediate subdirectories inside *dir_path*.

    Scans only ONE level deep (no recursion).  Symlinks are excluded from
    both counts so that only real filesystem objects are tallied.

    Args:
        dir_path: Absolute or relative path to the directory to inspect.

    Returns:
        A (file_count, subdir_count) tuple.
        Returns (0, 0) on PermissionError or OSError and prints a warning.
    """
    file_count = 0
    subdir_count = 0

    try:
        with os.scandir(dir_path) as scanner:
            for entry in scanner:
                if entry.is_file(follow_symlinks=False):
                    file_count += 1
                elif entry.is_dir(follow_symlinks=False):
                    subdir_count += 1

    except PermissionError:
        print(
            f"[fw_dirmap WARNING] PermissionError — cannot read directory: {dir_path}",
            file=sys.stderr,
        )
        return (0, 0)
    except OSError as exc:
        print(
            f"[fw_dirmap WARNING] OSError ({exc.strerror}) — cannot read directory: {dir_path}",
            file=sys.stderr,
        )
        return (0, 0)

    return (file_count, subdir_count)


# ---------------------------------------------------------------------------
# FUNCTION 3
# ---------------------------------------------------------------------------

def walk_directories(root: str, recursive: bool, max_depth):
    """Generator that yields (full_path, depth) tuples for a directory tree.

    Traversal is top-down (parents always yielded before their children).
    Symlinked directories are never followed (followlinks=False).
    Forward slashes are used in all yielded paths regardless of OS convention.

    Depth semantics:
        depth 0  = root itself
        depth 1  = immediate children of root
        depth N  = N levels below root

    Args:
        root:       Starting directory. Backslashes are normalised to forward
                    slashes in the yielded output.
        recursive:  If False, only depth-0 (root) and depth-1 (immediate
                    subdirectories) are yielded, then the generator stops.
        max_depth:  When not None, directories *at* this depth are yielded but
                    their children are pruned so os.walk does not descend
                    further. Ignored when recursive=False.

    Yields:
        (full_path: str, depth: int) — full_path uses forward slashes.
    """
    root_normalised = root.replace("\\", "/").rstrip("/")

    # Always yield the root itself at depth 0
    yield (root_normalised, 0)

    try:
        walker = os.walk(root, topdown=True, followlinks=False)
    except PermissionError:
        print(
            f"[fw_dirmap WARNING] PermissionError — cannot walk: {root}",
            file=sys.stderr,
        )
        return

    for dirpath, dirnames, _filenames in walker:
        norm_dirpath = dirpath.replace("\\", "/")

        # Skip the root itself — already yielded above
        if norm_dirpath.rstrip("/") == root_normalised:
            if not recursive:
                # Yield immediate subdirs at depth 1, then stop
                for name in list(dirnames):
                    subdir_path = f"{root_normalised}/{name}"
                    yield (subdir_path, 1)
                dirnames[:] = []  # prune: stop os.walk from descending
            continue

        # Calculate depth relative to root
        relative = norm_dirpath[len(root_normalised):].lstrip("/")
        depth = relative.count("/") + 1

        yield (norm_dirpath, depth)

        # Prune children if we've hit max_depth
        if max_depth is not None and depth >= max_depth:
            dirnames[:] = []
