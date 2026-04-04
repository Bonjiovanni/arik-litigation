"""
fw_classify_grp1.py
--------------------
Text extraction and signal detection for the fw_classify pipeline.

Functions:
    extract_text_from_pdf       — extract text from PDF via pymupdf (fitz)
    extract_text_from_text_file — extract text from plain-text files
    extract_text_from_spreadsheet — extract text sample from xlsx/csv
    get_text_sample             — dispatcher: routes to correct extractor by file_family
    detect_money                — returns "Y"/"N"/"" — looks for $ amounts and currency words
    detect_dates                — returns "Y"/"N"/"" — looks for date patterns
    match_keywords              — returns semicolon-joined keyword hits

Python 3.11, Windows 10.
"""

import re
import csv
from pathlib import Path

try:
    import fitz  # pymupdf
    _FITZ_AVAILABLE = True
except ImportError:
    _FITZ_AVAILABLE = False

try:
    import openpyxl
    _OPENPYXL_AVAILABLE = True
except ImportError:
    _OPENPYXL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(filepath: str, max_chars: int = 5000) -> tuple[str, bool]:
    """Extract text from a PDF file using pymupdf (fitz).

    Returns:
        (text_sample, is_complete) where is_complete is True if full text
        was extracted, False if truncated or extraction failed.
    """
    if not _FITZ_AVAILABLE:
        return ("", False)

    try:
        doc = fitz.open(filepath)
        parts = []
        total = 0
        for page in doc:
            page_text = page.get_text("text")
            if not page_text:
                continue
            remaining = max_chars - total
            if remaining <= 0:
                break
            chunk = page_text[:remaining]
            parts.append(chunk)
            total += len(chunk)
            if total >= max_chars:
                break
        doc.close()
        text = "".join(parts)
        is_complete = total < max_chars
        return (text, is_complete)
    except Exception:
        return ("", False)


def extract_text_from_text_file(filepath: str, max_chars: int = 5000) -> str:
    """Extract text from a plain-text file (txt, log, md, json, xml, etc.).

    Tries UTF-8 first, falls back with errors='replace'.
    Returns the first max_chars characters.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_chars)
    except Exception:
        return ""


def extract_text_from_spreadsheet(filepath: str, max_cells: int = 200) -> str:
    """Extract a text sample from a spreadsheet (.xlsx, .csv).

    For .xlsx: reads up to max_cells non-empty cells via openpyxl read_only + data_only mode.
    For .csv: reads up to max_cells fields.
    Returns a space-separated string of cell values.
    """
    path = Path(filepath)
    suffix = path.suffix.lower()

    # --- xlsx ---
    if suffix in (".xlsx", ".xlsm", ".xls") and _OPENPYXL_AVAILABLE:
        try:
            wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
            parts = []
            count = 0
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    for cell in row:
                        if cell is not None and str(cell).strip():
                            parts.append(str(cell).strip())
                            count += 1
                            if count >= max_cells:
                                break
                    if count >= max_cells:
                        break
                if count >= max_cells:
                    break
            wb.close()
            return " ".join(parts)
        except Exception:
            return ""

    # --- csv ---
    if suffix == ".csv":
        try:
            parts = []
            count = 0
            with open(filepath, "r", encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    for field in row:
                        if field.strip():
                            parts.append(field.strip())
                            count += 1
                            if count >= max_cells:
                                break
                    if count >= max_cells:
                        break
            return " ".join(parts)
        except Exception:
            return ""

    return ""


def get_text_sample(filepath: str, file_family: str, max_chars: int = 500) -> tuple[str, bool]:
    """Dispatcher: extract a short text sample based on file_family.

    Returns:
        (text_sample, extraction_succeeded)
        - text_sample: up to max_chars characters
        - extraction_succeeded: False if no text extracted or unsupported family
    """
    family = (file_family or "").lower()

    if family == "pdf":
        text, _ = extract_text_from_pdf(filepath, max_chars=max_chars)
        return (text, bool(text))

    if family in ("text_file",):
        text = extract_text_from_text_file(filepath, max_chars=max_chars)
        return (text, bool(text))

    if family in ("spreadsheet",):
        # For spreadsheets, max_cells scales roughly with max_chars
        text = extract_text_from_spreadsheet(filepath, max_cells=max(50, max_chars // 10))
        text = text[:max_chars]
        return (text, bool(text))

    if family in ("word_doc",):
        # Word docs: attempt as text file (may work for .txt-like); future: python-docx
        text = extract_text_from_text_file(filepath, max_chars=max_chars)
        return (text, bool(text))

    # Unsupported family (image, audio, video, email_file, archive, etc.)
    return ("", False)


# ---------------------------------------------------------------------------
# Signal detection
# ---------------------------------------------------------------------------

# Money patterns: $1,234.56 / $10 / USD / dollars
_MONEY_PATTERNS = [
    re.compile(r'\$\s*[\d,]+(?:\.\d{1,2})?'),          # $1,234.56
    re.compile(r'\b(?:USD|dollars?|cents?)\b', re.IGNORECASE),
]

# Date patterns: MM/DD/YYYY, YYYY-MM-DD, long-form (January 1, 2020)
_DATE_PATTERNS = [
    re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),         # MM/DD/YYYY or M/D/YY
    re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),                # YYYY-MM-DD
    re.compile(                                           # January 1, 2020 / Jan 1 2020
        r'\b(?:January|February|March|April|May|June|July|August|September|'
        r'October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        r'\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
        re.IGNORECASE,
    ),
]


def detect_money(text: str) -> str:
    """Return "Y" if money signals found in text, "N" if text present but no signals, "" if no text."""
    if not text or not text.strip():
        return ""
    for pattern in _MONEY_PATTERNS:
        if pattern.search(text):
            return "Y"
    return "N"


def detect_dates(text: str) -> str:
    """Return "Y" if date patterns found in text, "N" if text present but no dates, "" if no text."""
    if not text or not text.strip():
        return ""
    for pattern in _DATE_PATTERNS:
        if pattern.search(text):
            return "Y"
    return "N"


def detect_form_fields(pdf_path: str) -> str:
    if not _FITZ_AVAILABLE:
        return ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            if list(page.widgets()):
                doc.close()
                return "Y"
        doc.close()
        return "N"
    except Exception:
        return ""


def check_page_density(pdf_path: str) -> str:
    if not _FITZ_AVAILABLE:
        return ""
    try:
        doc = fitz.open(pdf_path)
        results = []
        for page in doc:
            char_count = len(page.get_text("text"))
            results.append(char_count >= 50)
        doc.close()
        if not results:
            return ""
        if all(results):
            return "N"
        if not any(results):
            return "Y"
        return "PARTIAL"
    except Exception:
        return ""


def match_keywords(text: str, keywords: list[str]) -> str:
    """Return semicolon-joined list of keywords found in text (case-insensitive).

    Args:
        text: text to search
        keywords: list of keyword strings to look for

    Returns:
        Semicolon-separated string of matched keywords (preserving original case from keywords list),
        or "" if no matches or no text.
    """
    if not text or not text.strip() or not keywords:
        return ""
    text_lower = text.lower()
    hits = [kw for kw in keywords if kw.lower() in text_lower]
    return ";".join(hits)
