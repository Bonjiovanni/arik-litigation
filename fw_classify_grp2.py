"""
fw_classify_grp2.py
--------------------
Master_File_Inventory Excel I/O layer for the fw_classify pipeline.

Reads rows that need classification, writes signal columns back, and
marks rows as classified. Column positions are resolved via _COL_INDEX
imported from fw_walk_grp2.

Functions:
    get_classifiable_rows   — returns (row_num, record_dict) for unclassified rows
    write_classify_signals  — writes signal columns to a specific row
    mark_row_classified     — sets ProcessingStatus = "classified"
"""

from fw_walk_grp2 import _COL_INDEX


# ---------------------------------------------------------------------------
# FUNCTION 1: get_classifiable_rows
# ---------------------------------------------------------------------------

def get_classifiable_rows(ws) -> list[tuple[int, dict]]:
    """Return (row_num, record_dict) for rows that need classification.

    Criteria:
      - ProcessingStatus is None, "", or "file_listed"
      - SkipReason is None or empty (already-skipped files are excluded)

    Stops iteration when FileID cell is None/empty (end of data).

    record_dict keys: FileID, FilePath, FileName, FileFamily,
                      LikelyTextBearing, NeedsOCR, ProcessingStatus
    """
    _FIELDS = ["FileID", "FilePath", "FileName", "FileFamily",
               "LikelyTextBearing", "NeedsOCR", "ProcessingStatus"]

    result = []
    for row_num in range(2, ws.max_row + 1):
        file_id = ws.cell(row=row_num, column=_COL_INDEX["FileID"]).value
        if file_id is None or str(file_id).strip() == "":
            break  # end of data

        processing_status = ws.cell(row=row_num, column=_COL_INDEX["ProcessingStatus"]).value
        skip_reason       = ws.cell(row=row_num, column=_COL_INDEX["SkipReason"]).value

        # Skip rows that have already been classified or are intentionally skipped
        if processing_status not in (None, "", "file_listed"):
            continue
        if skip_reason is not None and str(skip_reason).strip() != "":
            continue

        record = {}
        for field in _FIELDS:
            record[field] = ws.cell(row=row_num, column=_COL_INDEX[field]).value

        result.append((row_num, record))

    return result


# ---------------------------------------------------------------------------
# FUNCTION 2: write_classify_signals
# ---------------------------------------------------------------------------

# Columns that write_classify_signals is allowed to write
_WRITABLE_SIGNAL_COLS = {
    "TextSample", "MoneyDetected", "DateDetected", "KeywordHits",
    "LikelyTextBearing", "NeedsOCR",
    "DocType", "DocSubtype", "DocTypeConfidence",
}

# Columns that must never be overwritten
_PROTECTED_COLS = {"ManualReviewStatus", "KeepForCase", "PossibleExhibit"}


def write_classify_signals(ws, row_num: int, signals: dict) -> None:
    """Write signal column values to a specific row.

    Only writes keys present in signals dict and in _WRITABLE_SIGNAL_COLS.
    Never touches _PROTECTED_COLS.
    Unknown signal keys that happen to map to _COL_INDEX are also written,
    unless they are in _PROTECTED_COLS.
    """
    for key, value in signals.items():
        if key in _PROTECTED_COLS:
            continue
        if key not in _COL_INDEX:
            continue
        ws.cell(row=row_num, column=_COL_INDEX[key], value=value)


# ---------------------------------------------------------------------------
# FUNCTION 3: mark_row_classified
# ---------------------------------------------------------------------------

def mark_row_classified(ws, row_num: int) -> None:
    """Set ProcessingStatus = 'classified' for the given row."""
    ws.cell(row=row_num, column=_COL_INDEX["ProcessingStatus"], value="classified")
