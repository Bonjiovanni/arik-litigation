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
