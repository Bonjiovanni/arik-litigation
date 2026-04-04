# fileWalker Pipeline Architecture

## Overview

Five-stage pipeline, each as a standalone Python script sharing `filewalker_master.xlsx`.
Stages run sequentially; each picks up where the previous left off via `ProcessingStatus`.

```
fw_walk  →  fw_classify  →  fw_triage  →  [fw_ocr]  →  [fw_classify re-run]
```

---

## Stage 1: fw_walk
**Script:** `fw_walk.py`
**Input:** User selects scan directories at runtime
**Output:** Master_File_Inventory rows (ProcessingStatus = "file_listed")

- Inventories files: path, metadata, SHA256 hash, file family
- Detects overlaps with prior scans (Dir_Processing_Status)
- Skips files in skip families (email_file, archive by default — configurable in FileFamily_Config)
- Logs Walk_Coverage (per-dir) and Walk_History (per-run)

**Config sheets:** FileFamily_Config

---

## Stage 2: fw_classify
**Script:** `fw_classify.py`
**Input:** Rows where ProcessingStatus = "file_listed" + SkipReason empty
**Output:** Signal columns written; ProcessingStatus → "classified"

- Extracts text sample (pymupdf for PDF, plain read for text files, openpyxl for spreadsheets)
- Text-only — NO Vision/OCR at this stage
- Detects: MoneyDetected, DateDetected, keyword hits
- Infers: LikelyTextBearing, NeedsOCR
- Assigns: DocType, DocSubtype, DocTypeConfidence (keyword-rule driven)
- Logs Classify_History (per-run)

**Config sheets:** Keywords_Config, DocType_Rules_Config

---

## Stage 3: fw_triage
**Script:** `fw_triage.py` ← (merge of fw_triage_grp1–4, pending)
**Input:** Rows where ProcessingStatus = "classified"
**Output:** Triage columns written; ProcessingStatus → "triaged"

- Scores each file 0–100 based on DocType weights + signal weights
- Assigns TriageBand (High/Medium/Low/Skip) from configurable thresholds
- Sets ReasonFlagged and NextStep
- Special routing: NeedsOCR="Y" + Medium band → "OCR then review"
- Logs Triage_History (per-run)

**Config sheets:** Triage_Config, Triage_Bands

---

## Stage 4: fw_ocr  ← PLANNED
**Script:** `fw_ocr.py` (not yet written)
**Input:** Rows where NeedsOCR = "Y" (typically scanned PDFs and image files)
**Output:** OCRSnippet filled; ProcessingStatus → "ocr_complete"

**See:** `docs/fw_ocr_vision_spec.md` for full design (being authored separately)

Two candidate approaches (to be resolved in spec):
1. **Acrobat OCR** — shell out to Adobe Acrobat Pro (user has full CC Pro)
   - High quality; preserves layout; good for scanned documents
   - Requires Acrobat installed; slower per-file
2. **Claude Vision API** — send image/PDF page to Claude API with vision
   - Works for images and screenshots; no Acrobat required
   - Better for screenshots, handwriting, mixed-content images
   - Usage costs per call
3. **Hybrid** — Acrobat for dense text documents; Vision for images/screenshots/handwriting

After OCR, rows re-enter fw_classify for signal extraction on the OCR'd text.

**Columns written:** OCRSnippet, NeedsOCR (update), ProcessingStatus

---

## Stage 5: fw_classify re-run (post-OCR)
Same fw_classify script, but now operates on rows with ProcessingStatus = "ocr_complete".
Picks up OCRSnippet as the text source.

---

## Visual signal columns (set by fw_classify or fw_ocr)

These columns exist in Master_File_Inventory but are NOT yet populated by current scripts.
They require either Vision API calls or dedicated image analysis:

| Column | Meaning | Stage |
|---|---|---|
| SignatureLike | Signature detected | fw_ocr / Vision |
| HandwritingLike | Handwriting detected | fw_ocr / Vision |
| LogoLetterheadLike | Letterhead / logo detected | fw_ocr / Vision |
| TableLayoutLike | Table/grid layout detected | fw_ocr / Vision |
| OCRSnippet | OCR-extracted text sample | fw_ocr |

---

## ProcessingStatus flow

```
file_listed → classified → triaged → ocr_complete → [re-classified] → [re-triaged]
```

Each stage only processes rows at its expected input status.
Rows can be manually set to an earlier status to force reprocessing.

---

## Config sheets in filewalker_master.xlsx

| Sheet | Owned by | Purpose |
|---|---|---|
| FileFamily_Config | fw_walk | File extension → family mapping; skip flags |
| Keywords_Config | fw_classify | Keywords for text signal detection |
| DocType_Rules_Config | fw_classify | Keyword rules → DocType assignment |
| Triage_Config | fw_triage | Scoring weights per signal/DocType |
| Triage_Bands | fw_triage | Band thresholds and NextStep routing |

**IMPORTANT:** Review all 5 config sheets before running fw_classify or fw_triage.
Configs seed with reasonable defaults but must be tuned for this specific case.

---

## Related pipelines

### Email Body Processing Pipeline
A separate pipeline for processing Aid4Mail email exports lives in `email_pipeline/`.
It is independent of the fileWalker pipeline — it operates on email body content,
not on the file system inventory.

See `docs/email_pipeline.md` for full documentation.

---

## History / audit sheets

| Sheet | Written by | One row per |
|---|---|---|
| Walk_History | fw_walk | Run |
| Walk_Coverage | fw_walk | Directory × run |
| Classify_History | fw_classify | Run |
| Triage_History | fw_triage | Run |
