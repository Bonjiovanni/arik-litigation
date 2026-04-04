"""
fw_triage_grp2.py
-----------------
Master_File_Inventory Excel I/O for fw_triage.

Reads classified rows, writes triage results back.

Functions:
    get_triageable_rows   — returns (row_num, record_dict) for classified rows
    write_triage_results  — writes TriageScore, TriageBand, ReasonFlagged, NextStep
    mark_row_triaged      — sets ProcessingStatus = "triaged"
"""

from fw_walk_grp2 import _COL_INDEX


_PROTECTED_COLS = {"ManualReviewStatus", "KeepForCase", "PossibleExhibit"}

# Record fields needed for scoring
_TRIAGE_FIELDS = [
    "FileID", "FilePath", "FileFamily",
    "DocType", "DocSubtype", "DocTypeConfidence",
    "MoneyDetected", "DateDetected", "KeywordHits",
    "LikelyTextBearing", "NeedsOCR",
    "ProcessingStatus",
]


def get_triageable_rows(ws) -> list[tuple[int, dict]]:
    """Return (row_num, record_dict) for rows where ProcessingStatus = 'classified'.

    Stops at first empty FileID. Returns only rows ready for triage.
    """
    result = []
    for row_num in range(2, ws.max_row + 1):
        file_id = ws.cell(row=row_num, column=_COL_INDEX["FileID"]).value
        if file_id is None or str(file_id).strip() == "":
            break

        status = ws.cell(row=row_num, column=_COL_INDEX["ProcessingStatus"]).value
        if str(status or "").strip() != "classified":
            continue

        record = {field: ws.cell(row=row_num, column=_COL_INDEX[field]).value
                  for field in _TRIAGE_FIELDS}
        result.append((row_num, record))

    return result


def write_triage_results(ws, row_num: int, results: dict) -> None:
    """Write triage result columns to a specific row.

    Recognized results keys: TriageScore, TriageBand, ReasonFlagged, NextStep.
    Any key present in results and in _COL_INDEX is written (unless protected).
    """
    for key, value in results.items():
        if key in _PROTECTED_COLS:
            continue
        if key not in _COL_INDEX:
            continue
        ws.cell(row=row_num, column=_COL_INDEX[key], value=value)


def mark_row_triaged(ws, row_num: int) -> None:
    """Set ProcessingStatus = 'triaged' for the given row."""
    ws.cell(row=row_num, column=_COL_INDEX["ProcessingStatus"], value="triaged")
