"""
fw_walk_grp1.py — Pure-logic utility functions for the fw_walk.py file inventory agent.

Provides:
    - classify_file_family:   Map a file extension to its logical family
    - should_skip_file:       Determine whether a file should be excluded
    - get_file_metadata:      Collect filesystem metadata for a file path
    - compute_sha256:         Hash a file (with optional truncation)
    - peek_archive_contents:  Describe contents of a zip archive without extracting
    - load_file_family_config: Load family map and skip-family set from the
                               FileFamily_Config worksheet (falls back to built-in
                               defaults if the sheet is absent or unreadable)

No Excel I/O except in load_file_family_config (openpyxl read-only access to the
config sheet). Python 3.11, Windows 10.
Stdlib only (zipfile, hashlib, os, datetime) — openpyxl injected at call time.
"""

import os
import hashlib
import zipfile
from datetime import datetime


# ---------------------------------------------------------------------------
# Built-in file family extension map  (used as fallback if workbook absent)
# ---------------------------------------------------------------------------

_FAMILY_MAP: dict[str, set[str]] = {
    "pdf":          {".pdf"},
    "word_doc":     {".doc", ".docx", ".odt", ".rtf", ".dot", ".dotx"},
    "spreadsheet":  {".xls", ".xlsx", ".xlsm", ".xlsb", ".csv", ".ods", ".numbers"},
    "text_file":    {".txt", ".md", ".log", ".json", ".xml", ".html", ".htm",
                     ".yaml", ".yml", ".ini", ".toml", ".cfg"},
    "presentation": {".ppt", ".pptx", ".odp", ".key"},
    "image":        {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
                     ".heic", ".heif", ".webp", ".svg", ".raw", ".cr2", ".nef",
                     ".arw", ".dng", ".ico"},
    "email_file":   {".eml", ".msg", ".pst", ".ost", ".mbox"},
    "archive":      {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".cab"},
    "audio":        {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma", ".aiff"},
    "video":        {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v",
                     ".mpg", ".mpeg", ".webm"},
}

# Families whose files are skipped during the main walk
_DEFAULT_SKIP_FAMILIES: set[str] = {"email_file", "archive"}

_SYSTEM_EXTENSIONS: set[str] = {
    ".tmp", ".temp", ".lock", ".lnk", ".url", ".ds_store", ".thumbs.db",
}


# ---------------------------------------------------------------------------
# FUNCTION 1: load_file_family_config
# ---------------------------------------------------------------------------

def load_file_family_config(ws) -> "tuple[dict[str, set[str]], set[str], dict[str, dict[str, str]]]":
    """Load the file-family extension map, skip-family set, and likely-flags from a worksheet.

    Reads the FileFamily_Config worksheet (openpyxl Worksheet object).
    Expected columns (row 1 = header):
        A: Family          — family name string (e.g. "pdf")
        B: Extensions      — semicolon-separated list (e.g. ".pdf" or ".doc;.docx")
        C: ShouldSkip      — "Y" or "N"
        D: LikelyTextBearing — "Y" or "N"
        E: LikelyImage       — "Y" or "N"
        F: LikelySpreadsheet — "Y" or "N"
        G: LikelyDocument    — "Y" or "N"
        H: LikelyScreenshot  — "Y" or "N"  [optional]

    Returns:
        (family_map, skip_families, likely_flags)
            family_map    — {family_name: {".ext", ...}}
            skip_families — set of family names where ShouldSkip == "Y"
            likely_flags  — {family_name: {"likely_text_bearing": "Y"/"N", ...}}
    """
    family_map: dict[str, set[str]] = {}
    skip_families: set[str] = set()
    likely_flags: dict[str, dict[str, str]] = {}

    _flag_cols = [
        (3, "likely_text_bearing"),
        (4, "likely_image"),
        (5, "likely_spreadsheet"),
        (6, "likely_document"),
        (7, "likely_screenshot"),
    ]

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[0] is None:
            continue

        family = str(row[0]).strip().lower()
        if not family:
            continue

        # Extensions column (B)
        raw_exts = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        ext_set: set[str] = set()
        for token in raw_exts.split(";"):
            token = token.strip().lower()
            if not token:
                continue
            if not token.startswith("."):
                token = "." + token
            ext_set.add(token)
        family_map[family] = ext_set

        # ShouldSkip column (C)
        should_skip_val = str(row[2]).strip().upper() if len(row) > 2 and row[2] is not None else "N"
        if should_skip_val == "Y":
            skip_families.add(family)

        # Likely-flags columns (D-H)
        flags: dict[str, str] = {}
        for col_idx, key in _flag_cols:
            val = row[col_idx] if len(row) > col_idx else None
            flags[key] = str(val).strip().upper() if val is not None else "N"
        likely_flags[family] = flags

    return family_map, skip_families, likely_flags


# ---------------------------------------------------------------------------
# FUNCTION 2: classify_file_family
# ---------------------------------------------------------------------------

def classify_file_family(
    filename: str,
    extension: str,
    family_map: "dict[str, set[str]] | None" = None,
) -> str:
    """Classify a file into a logical family based on its extension.

    Args:
        filename:   The file's basename (not currently inspected; reserved
                    for future magic-byte fallback).
        extension:  Lowercased extension including the leading dot, e.g. ".pdf".
                    Caller is responsible for lowercasing before passing in.
        family_map: Optional extension map loaded via load_file_family_config().
                    Falls back to the built-in _FAMILY_MAP if None.

    Returns:
        One of the family names in the map, or "other" if not matched.
    """
    effective_map = family_map if family_map is not None else _FAMILY_MAP
    ext = extension.lower()
    for family, extensions in effective_map.items():
        if ext in extensions:
            return family
    return "other"


# ---------------------------------------------------------------------------
# FUNCTION 3: should_skip_file
# ---------------------------------------------------------------------------

def should_skip_file(
    filename: str,
    extension: str,
    file_family: str,
    skip_families: "set[str] | None" = None,
) -> "tuple[bool, str]":
    """Determine whether a file should be skipped during inventory processing.

    Archives are NOT skipped outright — they get a content summary via
    peek_archive_contents() and are logged with SkipReason="archive".
    Email files are fully skipped (logged but not described).

    Checked in priority order:
        1. file_family is in skip_families (default: email_file, archive)
        2. Filename starts with "~$"     → Office temp, skip
        3. Filename starts with "."      → Hidden file, skip
        4. Extension is a system type    → skip

    Args:
        filename:     The file's basename (e.g. "~$report.docx").
        extension:    Lowercased extension with leading dot (e.g. ".tmp").
        file_family:  Result of classify_file_family() for this file.
        skip_families: Set of family names to skip. Defaults to
                       {"email_file", "archive"} if None.

    Returns:
        (should_skip: bool, skip_reason: str)
        skip_reason is one of: the family name (e.g. "email_file", "archive"),
        "office_temp", "hidden_file", "system_file", or "" when not skipped.
    """
    effective_skip = skip_families if skip_families is not None else _DEFAULT_SKIP_FAMILIES

    if file_family in effective_skip:
        return (True, file_family)

    if filename.startswith("~$"):
        return (True, "office_temp")

    if filename.startswith("."):
        return (True, "hidden_file")

    if extension.lower() in _SYSTEM_EXTENSIONS:
        return (True, "system_file")

    return (False, "")


# ---------------------------------------------------------------------------
# FUNCTION 4: get_file_metadata
# ---------------------------------------------------------------------------

def get_file_metadata(filepath: str) -> dict:
    """Collect filesystem metadata for a file.

    Uses os.stat() for all timestamps. On Windows, st_ctime is creation time.
    All path strings are normalized to forward slashes.

    Args:
        filepath: Absolute or relative path to the target file.

    Returns:
        Dict with keys:
            filename      — basename
            extension     — lowercased with dot (e.g. ".pdf"); "" if none
            parent_folder — forward-slash normalized parent directory
            file_path     — forward-slash normalized full path
            size_bytes    — int, or "" on error
            created_time  — ISO datetime string (st_ctime), or ""
            modified_time — ISO datetime string (st_mtime), or ""
            accessed_time — ISO datetime string (st_atime), or ""
    """
    def _norm(p: str) -> str:
        return p.replace("\\", "/")

    filename      = os.path.basename(filepath)
    _, raw_ext    = os.path.splitext(filename)
    extension     = raw_ext.lower()
    parent_folder = _norm(os.path.dirname(os.path.abspath(filepath)))
    norm_path     = _norm(filepath)

    result: dict = {
        "filename":      filename,
        "extension":     extension,
        "parent_folder": parent_folder,
        "file_path":     norm_path,
        "size_bytes":    "",
        "created_time":  "",
        "modified_time": "",
        "accessed_time": "",
    }

    try:
        st = os.stat(filepath)
        result["size_bytes"]    = st.st_size
        result["created_time"]  = datetime.fromtimestamp(st.st_ctime).isoformat()
        result["modified_time"] = datetime.fromtimestamp(st.st_mtime).isoformat()
        try:
            result["accessed_time"] = datetime.fromtimestamp(st.st_atime).isoformat()
        except OSError:
            pass
    except OSError:
        pass

    return result


# ---------------------------------------------------------------------------
# FUNCTION 5: compute_sha256
# ---------------------------------------------------------------------------

def compute_sha256(filepath: str, max_bytes: int = 524_288_000) -> "tuple[str, bool]":
    """Compute a SHA-256 digest for a file, with an optional byte-count cap.

    Reads in 64 KB chunks up to max_bytes. Returns a partial hash if
    truncated; is_complete=False signals the hash is not over the full file.

    Args:
        filepath:  Path to the file.
        max_bytes: Max bytes to read (default 500 MB). 0 or negative = no cap.

    Returns:
        (hash_hex: str, is_complete: bool)
        hash_hex is "" and is_complete is False on any read error.
    """
    _CHUNK = 65_536  # 64 KB

    hasher     = hashlib.sha256()
    bytes_read = 0
    is_complete = True

    try:
        with open(filepath, "rb") as fh:
            while True:
                if max_bytes > 0:
                    remaining = max_bytes - bytes_read
                    if remaining <= 0:
                        is_complete = False
                        break
                    read_size = min(_CHUNK, remaining)
                else:
                    read_size = _CHUNK

                chunk = fh.read(read_size)
                if not chunk:
                    break

                hasher.update(chunk)
                bytes_read += len(chunk)

        return (hasher.hexdigest(), is_complete)

    except (PermissionError, OSError):
        return ("", False)


# ---------------------------------------------------------------------------
# FUNCTION 6: peek_archive_contents
# ---------------------------------------------------------------------------

def peek_archive_contents(filepath: str) -> str:
    """Generate a plain-text description of the contents of an archive file.

    Only .zip files are fully supported (stdlib zipfile).
    For .rar, .7z, .tar, .gz, .bz2, .xz, .cab — returns a brief note
    explaining the format is not peekable without additional dependencies.

    Does NOT extract any files. Reads only the central directory listing.

    Args:
        filepath: Path to the archive file.

    Returns:
        A human-readable string summarising the archive contents, e.g.:
            "47 files: 32 images (.jpg .png), 8 PDFs, 5 documents (.docx), 2 other"
        Or on error / unsupported format:
            "cannot peek — unsupported format (.rar)"
            "cannot peek — corrupt or unreadable zip"
            "cannot peek — access denied"
    """
    ext = os.path.splitext(filepath)[1].lower()

    # --- Non-zip formats: stdlib cannot peek inside without 3rd-party deps ---
    if ext != ".zip":
        return f"cannot peek — unsupported format ({ext}); install rarfile/py7zr to enable"

    # --- ZIP: use stdlib zipfile ---
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            names = [info.filename for info in zf.infolist() if not info.is_dir()]
    except zipfile.BadZipFile:
        return "cannot peek — corrupt or unreadable zip"
    except PermissionError:
        return "cannot peek — access denied"
    except OSError as exc:
        return f"cannot peek — OS error ({exc.strerror})"

    total = len(names)
    if total == 0:
        return "empty archive (0 files)"

    # --- Classify each file inside by extension ---
    family_counts: dict[str, int] = {}
    ext_examples: dict[str, list[str]] = {}

    for name in names:
        _, inner_ext = os.path.splitext(name)
        inner_ext = inner_ext.lower()
        family = classify_file_family(os.path.basename(name), inner_ext)
        family_counts[family] = family_counts.get(family, 0) + 1
        if family not in ext_examples:
            ext_examples[family] = []
        if inner_ext and inner_ext not in ext_examples[family]:
            ext_examples[family].append(inner_ext)

    # --- Build readable summary ---
    # Sort by count descending so the dominant type leads
    sorted_families = sorted(family_counts.items(), key=lambda kv: kv[1], reverse=True)

    parts = []
    for family, count in sorted_families:
        exts = " ".join(sorted(ext_examples.get(family, [])))
        label = family.replace("_", " ")
        if exts:
            parts.append(f"{count} {label} ({exts})")
        else:
            parts.append(f"{count} {label}")

    summary = f"{total} file{'s' if total != 1 else ''}: " + ", ".join(parts)
    return summary
