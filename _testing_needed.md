# Testing Needed

**Triggered by:** orchestrator (main Claude Code window)
**Date:** 2026-03-15
**Batch:** fw_triage pipeline (grp1–4) + fw_classify (grp1–5 + merged)

---

## fw_triage — DONE ✓ (2026-03-15)

All 4 grp test files written and passing (109 tests):
`test_fw_triage_grp1.py`, `test_fw_triage_grp2.py`, `test_fw_triage_grp3.py`, `test_fw_triage_grp4.py`

Full suite: **572 tests passing** across 15 test files.

## fw_classify — DONE ✓ (2026-03-15)

All 5 grp test files written and passing (136 tests):
`test_fw_classify_grp1.py`, `test_fw_classify_grp2.py`, `test_fw_classify_grp3.py`,
`test_fw_classify_grp4.py`, `test_fw_classify_grp5.py`

**Open item — ExcelMCP compliance review:**
`fw_classify_grp3.py` and `fw_classify_grp4.py` use `openpyxl` to write to the
master workbook. Per project rules, production writes should go through ExcelMCP.
Orchestrator should confirm whether openpyxl is intentional here (unattended pipeline)
or rewrite to ExcelMCP.  Tests are unaffected (openpyxl is correct for headless pytest).

---

## Test file targets

```
tests/test_fw_triage_grp1.py   ← DONE
tests/test_fw_triage_grp2.py   ← DONE
tests/test_fw_triage_grp3.py   ← DONE
tests/test_fw_triage_grp4.py   ← DONE
tests/test_fw_triage.py        ← pending (merged module, not yet delivered)
tests/test_fw_classify_grp1.py  ← DONE (needs: detect_form_fields, check_page_density — see below)
tests/test_fw_classify_grp2.py  ← DONE
tests/test_fw_classify_grp3.py  ← DONE
tests/test_fw_classify_grp4.py  ← DONE
tests/test_fw_classify_grp5.py  ← DONE
tests/test_fw_classify.py       ← pending (merged module, not yet delivered)
```

---

## New functions needing tests

### fw_classify_grp1.py — two new functions
Add to `tests/test_fw_classify_grp1.py`:
- `detect_form_fields` — add a new `TestDetectFormFields` class
- `check_page_density` — add a new `TestCheckPageDensity` class

### fw_classify.py — merged module is STALE
grp1 and grp5 both changed since the merged module was last built.
Do NOT write `test_fw_classify.py` until the orchestrator rebuilds the merged module.

### fw_triage_grp1.py — score values changed (2026-03-15)
Orchestrator updated these DocType scores:
- Bank_Statement: 20 → 70
- Financial_Statement: 70 (new entry)
- Invoice: 20 → 65
- Tax_Document: 18 → 65 (was Tax_Document, confirmed new value)
- Utility_Bill: 60 (new entry)
Tests in `test_fw_triage_grp1.py` updated to match (3 tests fixed, suite green).

---

---

## NEW — 2026-03-16 — load_file_family_config returns 3-tuple — DONE ✓

Fixed `tests/test_fw_walk.py` (6 2-tuple → 3-tuple) + added `TestLikelyFlags` (12 tests)
and 4 walk_files Likely* column tests in `TestWalkFilesPipeline`.
**640 tests passing** across 16 test files.

---

## NEW — 2026-03-16 — fw_walk.py COLUMNS synced to fw_walk_grp2.py

Added 3 missing columns to fw_walk.py COLUMNS list:
- `HasFormFields` (after NeedsOCR)
- `ExtractionMethod` (after HasFormFields)
- `EntityHits` (between KeywordHits and MoneyDetected)

These were present in fw_walk_grp2.py but missing from the merged fw_walk.py, causing a column index mismatch that broke fw_classify.

### Tests needed:
- Verify `fw_walk.COLUMNS` and `fw_walk_grp2.COLUMNS` are identical (or add a sync-check test)
- Verify `fw_walk._COL_INDEX["ProcessingStatus"]` == `fw_walk_grp2._COL_INDEX["ProcessingStatus"]`

## After all merged modules delivered

Delete this file and commit.

---

## NEW — 2026-03-21 — Drive Scout + fw_dir_tree + fw_file_inventory — DONE ✓

90 tests written and passing across 3 files:
- `tests/test_fw_dir_tree.py` (30 tests)
- `tests/test_fw_file_inventory.py` (26 tests)
- `tests/test_drive_scout_server.py` (34 tests)

Note: asyncio.create_task patched with `side_effect=lambda coro: coro.close()`
to prevent real PowerShell scans. WebSocket tests skipped (integration-level).
conftest.py updated to add repo root to sys.path (fixes Pylance import resolution).
Suite: **928 tests passing** across 26 files.

---

## NEW — 2026-03-18 — email_pipeline/validate_attachments.py — DONE ✓

22 tests written and passing. `tests/test_validate_attachments.py`.

---

## NEW — 2026-03-18 — jh_ltc/ scripts — DONE ✓

70 tests written and passing across 2 files:
- `tests/test_jh_ltc_eob.py` (34 tests)
- `tests/test_jh_ltc_invoice.py` (36 tests)

Note: batch_invoice_process.py and extract_one_detail_page.py have module-level
`OUT_DIR.mkdir()` — patched with `unittest.mock.patch("pathlib.Path.mkdir")` at import.
TestExtractOneDetailPageConfig skips in CI (requires real Litigation drive).

---

## NEW — 2026-03-18 — email_pipeline/ scripts — DONE ✓

106 tests written and passing. Suite: 746 tests across 20 files.

---

## ARCHIVED — 2026-03-18 — email_pipeline/ scripts added to repo

Four scripts moved from `C:\Users\arika\OneDrive\Litigation\Pipeline\` into `email_pipeline/`:

- `email_pipeline/merge_and_classify.py`
- `email_pipeline/export_all_emails.py`
- `email_pipeline/strippers.py`
- `email_pipeline/read_xlsx.py`

### Tests needed — write from scratch, no existing tests exist

#### `strippers.py` — highest priority, most logic
- `TestHtmlToText` — br tags become newlines, consecutive blanks collapsed
- `TestStripGmail` — outermost gmail_quote div removed, siblings dropped, fallback to full text
- `TestStripOutlook` — cut at From:/Sent: boundary in plain + HTML
- `TestStripForward` — dash-line header cut, Begin forwarded message: cut, Outlook fallback
- `TestStripGtPrefix` — >-prefixed lines removed, On...wrote: attribution removed, blank collapse
- `TestStripOutlookPlain` — -----Original Message----- primary cut, Outlook fallback
- `TestStripIos` — Apple Mail "On..., at..., wrote:", Samsung dashes, Mobile Outlook From:/Subject:
- `TestStripOnWrote` — cut at "On...wrote:" boundary
- `TestStripPassthrough` — Original/Inline/Clean_Reply return Body.Text unchanged
- `TestStripAttorneySig` — Gravel & Shea trigger + walk-back, Primmer trigger, disclaimer catch-all, Get Outlook for iOS line
- `TestGetBodyClean` — dispatcher routes to correct stripper; attorney sig applied after

#### `merge_and_classify.py`
- `TestNormalizeMessageId` — strips whitespace, lowercases, removes < >
- `TestScoreRecord` — EML/MSG beats GMAIL_API, body size tiebreaker, run date tiebreaker
- `TestPickWinner` — returns correct winner and loser list
- `TestGetStripMethod` — each classification branch: Inline, Forward, Gmail, Outlook, GT_Prefix, iOS, Outlook_Plain, OnWrote, Original, Clean_Reply
- `TestLoadExport` — valid JSON loads correctly, missing file returns [], invalid structure raises
- `TestDeduplication` — SHA256 grouping, Message-ID fallback grouping, no-key records kept
- `TestZeroRecordsHalt` — if all inputs missing, main() returns before writing anything

#### `export_all_emails.py`
- `TestSafeStr` — None returns "", truncates at 32000, strips bad control chars, keeps \n \r \t
- `TestNextAvailablePath` — non-existent returns base, existing returns (1), (2) etc.
- `TestColumnOrdering` — priority cols appear first, rest sorted alphabetically
- Integration: given a minimal combined_repository.json, verify xlsx is written with correct headers and row count

#### `read_xlsx.py`
- Valid file + sheet name returns correct dict
- Valid file, no sheet name returns all sheets
- Missing sheet returns error string (not exception)
- Non-existent file path returns error JSON and exits with code 1
- Blank rows are skipped
