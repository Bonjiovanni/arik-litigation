# Project Context

## What This Is
A Python script that authenticates to Google Drive via OAuth, finds a folder at `email/all`, lists all files with metadata (name, size, extension), and exports results to a styled Excel file.

## Files
- `drive_file_metadata.py` — main script (written by Claude)
- `credentials.json` — Google OAuth credentials (Desktop app type) — DO NOT commit
- `token.json` — saved auth token after first login — DO NOT commit
- `requirements.txt` — Python dependencies
- `.gitignore` — already excludes credentials.json and token.json

## Google Cloud Setup
- **Project ID:** claude-sndroid (project name: Claude Android)
- **App name:** Claudi android
- **OAuth type:** Desktop app (installed)
- **Scope:** `https://www.googleapis.com/auth/drive.readonly`
- **Test user:** arik.arik@gmail.com (added to OAuth consent screen → Audience → Test users)

## Current Status (as of 2026-02-23)
- Test user `arik.arik@gmail.com` added to OAuth consent screen ✓
- credentials.json valid on server (verified 403 bytes, `installed` key confirmed) ✓
- Google Drive API enabled in claude-sndroid project ✓
- Script now uses manual URL/code flow (no browser auto-open) ✓
- Repo cloned on phone at `~/downloads/Repo-for-Claude-android` ✓
- credentials.json copied from `client_secret_1076938672717-....json` ✓
- token.json does NOT exist — auth not yet completed

## NEXT STEP — Run in Termux (on phone)
1. Pull latest script and run:
   ```bash
   cd ~/downloads/Repo-for-Claude-android
   git pull origin claude/google-drive-file-metadata-C554z
   python drive_file_metadata.py
   ```
2. Script prints a long URL — copy it
3. Open URL in Android browser, sign in as arik.arik@gmail.com, click Allow
4. Google shows a short auth code — copy it
5. Switch back to Termux, paste the code and press Enter
6. token.json saved, Excel file generated

## To Regenerate Credentials
1. console.cloud.google.com → project gen-lang-client-0226922644
2. APIs & Services → Credentials
3. Edit or delete/recreate the OAuth 2.0 client (Desktop app type)
4. Download new credentials.json
5. Replace the file at /home/user/Repo-for-Claude-android/credentials.json
6. Delete token.json if it exists

## To Run
```bash
cd /home/user/Repo-for-Claude-android
python drive_file_metadata.py
```
Script will print a Google auth URL — open it in browser, sign in as arik.arik@gmail.com, complete auth. Token saved to token.json for future runs.

## User Context
- User is on Android using Claude Code Android app
- App gets killed when switching to browser/Google Console
- Chat history is lost when app is killed
- User accesses this Linux server via Claude Code Android app

---

## fileWalker — File Walker + Triage System (Active Project)

**Branch:** `claude/upload-file-form-sipNu`

A Python-based file walker + first-pass triage system for litigation evidence surfacing. Scans user-selected Windows directories (OneDrive), inventories files with metadata, and outputs to a multi-tab Excel workbook.

### Key Files
- `fileWalker.md` — Full specification/design document (from user's email)
- `generate_dir_format_sample.py` — Generates sample Excel comparing directory inventory formats
- `dir_format_sample.xlsx` — Sample workbook with Option A (FullPath) vs Option C (Hybrid) formats + Dir_Processing_Status sheet

### Implementation Plan
Saved at: `/root/.claude/plans/giggly-wiggling-castle.md`

**Architecture:** Separate focused Python scripts (agents), each does one thing, all operate on the same master workbook (`filewalker_master.xlsx`).

**Build phases:**
- **Phase 0 (current):** Directory Mapper (`fw_dirmap.py`) — map folder structure, Dir_Inventory sheet. User needs to review `dir_format_sample.xlsx` and choose Option A vs Option C format before building.
- **Phase 1:** File Walker foundation — config, workbook creation, basic file walking
- **Phase 2:** Core enrichment — hashing, file family classification, Likely* flags, skip logic
- **Phase 3:** Walk management — history, coverage, overlap detection
- **Phase 4:** Triage layer — entity/keyword matching, scoring, summaries

**Code will live in:** `filewalker/` subdirectory (config.py, workbook.py, walker.py, classify.py, triage.py, main.py)

### Build Rules
1. Do NOT build anything without explicit user approval — ask before each piece
2. Do NOT build everything at once — build in phases, discuss between phases
3. Production Excel files must use Excel MCP tools in VS Code, not openpyxl
4. All code committed to git so it persists across sessions

---

## Testing Suite

### File Discovery Rule (IMPORTANT)
When checking for new scripts to test, always verify by reading the file system directly
(use Glob or ls on the actual paths). Do NOT rely on git status or assume files must be
pushed to remote. All work happens locally on branch `claude/upload-file-form-sipNu`.
If _testing_needed.md references a file, check the path on disk before concluding it doesn't exist.



**Run all tests:**
```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/ -v
```

**Rules — mandatory for every session:**
1. Every module gets a corresponding `tests/test_<module>.py`. Maintain all test files when the module changes.
2. **Run the full suite before AND after any code change.** Confirm all tests pass before moving on.
3. If a previously passing test breaks, fix the regression immediately — do not proceed with new work while tests are red.
4. When adding a new function, add its tests in the same session before closing out.
5. After merging group files into a single-file module (e.g. `fw_dirmap.py`), add module-level integration tests for the merged file.

### Test files

| File | Module tested | Scope |
|---|---|---|
| `tests/test_fw_dirmap_grp1.py` | `fw_dirmap_grp1.py` | `validate_and_normalize_path`, `generate_run_id` |
| `tests/test_fw_dirmap_grp2.py` | `fw_dirmap_grp2.py` | `detect_source_store`, `count_dir_contents`, `walk_directories` |
| `tests/test_fw_dirmap_grp3.py` | `fw_dirmap_grp3.py` | `build_dir_records` (DI-based, no real filesystem) |
| `tests/test_fw_dirmap_grp4.py` | `fw_dirmap_grp4.py` | `open_or_create_workbook`, `ensure_dir_inventory_sheet`, `write_dir_inventory_rows` |
| `tests/test_fw_dirmap_grp5.py` | `fw_dirmap_grp5.py` | `ensure_dir_processing_status_sheet`, `initialize_processing_status_rows` |
| `tests/test_fw_dirmap_grp6.py` | `fw_dirmap_grp6.py` | `log_dirmap_run`, `print_run_summary` |
| `tests/test_fw_dirmap.py` | `fw_dirmap.py` | **Module-level integration** — namespace, full pipeline, cross-group data contracts, round-trip save/reload, multi-root, sheet structure |
| `tests/test_fw_walk_grp1_grp2.py` | `fw_walk_grp1.py`, `fw_walk_grp2.py` | File utilities, sheet management (MFI + FileFamily_Config), insert/update |
| `tests/test_fw_walk_grp3.py` | `fw_walk_grp3.py` | `PROCESSING_LEVEL_ORDER`, `get_covered_paths`, `check_overlap`, `prompt_overlap_decision` |
| `tests/test_fw_walk_grp4.py` | `fw_walk_grp4.py` | Walk_Coverage + Walk_History sheet management and logging |
| `tests/test_fw_walk.py` | `fw_walk.py` | **Module-level integration** — namespace, level ordering, FileFamily_Config round-trip, insert/update pipeline, `walk_files` against real temp dir, logging pipeline, sheet structure, round-trip save/reload |
| `tests/test_fw_classify_grp1.py` | `fw_classify_grp1.py` | `extract_text_from_text_file`, `detect_money`, `detect_dates`, `match_keywords`, `get_text_sample` |
| `tests/test_fw_classify_grp2.py` | `fw_classify_grp2.py` | `get_classifiable_rows`, `write_classify_signals`, `mark_row_classified` |
| `tests/test_fw_classify_grp3.py` | `fw_classify_grp3.py` | `ensure_keywords_config_sheet`, `load_keywords`, `infer_likely_text_bearing`, `infer_needs_ocr`, `classify_doc_type` |
| `tests/test_fw_classify_grp4.py` | `fw_classify_grp4.py` | `ensure_classify_history_sheet`, `log_classify_run` |
| `tests/test_fw_classify_grp5.py` | `fw_classify_grp5.py` | Namespace + main() branch tests (no MFI sheet → exit 1; no rows → exit 0) |
| `tests/test_fw_triage_grp1.py` | `fw_triage_grp1.py` | `ensure_triage_config_sheet`, `ensure_triage_bands_sheet`, `load_triage_config`, `load_triage_bands`, `score_record`, `get_triage_band`, `get_reason_flagged`, `get_next_step` |
| `tests/test_fw_triage_grp2.py` | `fw_triage_grp2.py` | `get_triageable_rows`, `write_triage_results`, `mark_row_triaged` |
| `tests/test_fw_triage_grp3.py` | `fw_triage_grp3.py` | `ensure_triage_history_sheet`, `log_triage_run` |
| `tests/test_fw_triage_grp4.py` | `fw_triage_grp4.py` | Namespace + main() branch tests (no MFI sheet → exit 1; no rows → exit 0) |

### What `test_fw_walk.py` covers (module-level only)
- All public functions importable from the merged single-file module
- `PROCESSING_LEVEL_ORDER` ordering contract
- `ensure_file_family_config_sheet` → `load_file_family_config` round-trip (10 families, skip sets)
- `write_or_update_file_record`: insert on first call, update on second, FileID format, `ManualReviewStatus` not overwritten
- `walk_files` against real temp directory: stats dict, insert/skip counts, second walk updates not inserts, forward-slash paths
- `update_walk_coverage`: sequential CoverageIDs, correct data
- `log_walk_run`: RunID written, pipe-separated ScanDirs, second run appends
- Freeze panes and idempotency for all 4 sheets
- Save → reload preserving all 4 sheets and MFI data rows

---

## Email Evidence Pipeline

A second major pipeline alongside fileWalker, operating on litigation email evidence.
Both pipelines converge at the Chroma indexing layer (planned) and via the sha256 join key.

### Email Body Pipeline Chain

```
Gmail body master.json  --+
EML body master.json      +--> merge_and_classify.py --> combined_repository.json
MSG body master.json    --+        (uses strippers.py)      + <name>_report.json
                                                                   |
                                                                   v
                                                        export_all_emails.py
                                                                   |
                                                                   v
                                                    all_emails (N).xlsx [current: (2)]
                                                                   |
                                                                   v
                                     AllEmailBod PQ (via Email_Body_Input_File param)
                                                                   |
                                                                   v
                                                AllEmailBod_1 table in V11.xlsx
```

Aid4Mail JSON sources: `C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 ti json 2dtime\`
All scripts: `C:\Users\arika\Repo-for-Claude-android\email_pipeline\`
Intermediate outputs: `C:\Users\arika\OneDrive\Litigation\Pipeline\` (not in git)

### Email Pipeline Scripts (in repo: email_pipeline/)

**merge_and_classify.py**
- Interactive file pickers for Gmail/EML/MSG inputs — asks Y/N per source
- Deduplicates on SHA256 (primary) then Message-ID (fallback)
- EML/MSG wins over Gmail API as forensically authoritative
- Classifies strip_method, writes body_clean via strippers.py
- Outputs: `<name>.json` + `<name>_report.json`
- Config memory: `Email_Body_Processing_Config.json` (not committed)
- Offers to chain directly into export_all_emails.py at end of run

**strippers.py**
- Quote-stripping library — 10 strip methods (Gmail, Outlook, Forward, GT_Prefix,
  Outlook_Plain, iOS, OnWrote, Original, Inline, Clean_Reply)
- Post-processing: attorney signature removal (Gravel & Shea, Primmer Piper)
- Called by merge_and_classify.py via get_body_clean()

**export_all_emails.py**
- Interactive file picker for input JSON and output xlsx
- Exports all fields, all records via xlsxwriter/write_string (no formula corruption)
- Priority cols first; rest alphabetical. Overwrite protection.

**validate_attachments.py**
- Validates attachment manifest (Excel index) against physical Attachment/ and Embedded/ folders
- Checks: missing files, orphans, count mismatches, duplicate basenames, name collisions
- Outputs: validation_report.xlsx (multi-tab)

**read_xlsx.py**
- General utility: dumps any .xlsx to JSON on stdout
- Used by claude.ai Desktop Commander and pipeline scripts
- Usage: `python read_xlsx.py <path.xlsx> [sheet_name]`

### JH LTC Document Extraction Scripts (09-Data Schemas — not yet in repo)

**visualize_eob_fields.py** + **batch_eob_process.py**
- EOB PDF field extraction via pymupdf; HTML review page per doc + Excel summary + merged PDF

**visualize_invoice_fields.py** + **batch_invoice_process.py**
- JH Invoice PDF field extraction (page 1 digital only; pages 2+ are scanned timesheets)

**extract_one_detail_page.py**
- Probe script: Claude Vision extraction of one scanned invoice detail page

All five live at: `C:\Users\arika\OneDrive\Litigation\09-Data Schemas\`

### Data Sources

**Aid4Mail body exports** (JSON, 3 files)
- Gmail: `...\Aid4 ti json 2dtime\Gmail body master.json`
- EML:   `...\Aid4 ti json 2dtime\EML body master.json`
- MSG:   `...\Aid4 ti json 2dtime\MSG body master.json`
- Merged output: `C:\Users\arika\OneDrive\Litigation\Pipeline\combined_repository.json`
- Excel output:  `C:\Users\arika\OneDrive\Litigation\Pipeline\all_emails (2).xlsx` [current]
- 1,672 rows. Key fields: Body.Text, Body.SenderText, body_clean, strip_method
- CloudHQ "Email Text" field is superseded by this pipeline

**CloudHQ live Google Sheet**
- 1,695 rows as of 2026-03-18. Query name in V11.xlsx: CloudHQ_Live
- PQ CSV URL published via File > Share > Publish to web > CSV
- Columns include: Thread ID, RFC 822 Message ID, From, To, Subject, Labels,
  Date & Time Sent/Received, Attachments Count, Body Snippet

**Aid4Mail Attachment Manifest**
- File: `...\Aid4 to json with python attachments\Attachment_Manifest_GML_EML_MSG (1).xlsx`
- One row per attachment. Key columns: mih, message_id, attachment_ordinal,
  original_filename, saved_filename, file_type, saved_full_path, storage_folder, size_bytes, sha256
- Physical files: `...\Attachment\` and `...\Embedded\`

### Primary Working Workbook
`C:\Users\arika\OneDrive\Litigation\Pipeline\label_LegalEmailExtracts - Ariks Version V11.xlsx`
(Renamed from V10 on 2026-03-18)

PQ queries: WorkingCopyTable, AllEmailBod (parameterized via Email_Body_Input_File),
CloudHQ_Live (live CSV), ThreeWayAudit, Merge1, Guns

**PQ Parameter: Email_Body_Input_File**
- Current value: `C:\Users\arika\OneDrive\Litigation\Pipeline\all_emails (2).xlsx`
- Update this after each new Aid4Mail run. NEVER overwrite prior all_emails files.

### Universal Join Key
- CloudHQ: `RFC 822 Message ID`
- AllEmailBod / merge output: `Header.Message-ID`
- Attachment Manifest: `message_id`

### Three-Way Audit (ThreeWayAudit query — BUILT)
Compares Message IDs across AllEmailBod, WorkingCopyTable, CloudHQ_Live.
Results 2026-03-18: 1,695 unique, 1,550 OK, 81 CloudHQ-only (delta list for next Aid4Mail run),
64 EML-only (expected). Uses full outer join (type 2) — NOT JoinKind.Left.

### Planned: EmailMaster.xlsx (DESIGNED, NOT YET BUILT)
- Tab 1 EmailMaster: one row per email, cols from WorkingCopyTable + AllEmailBod joined
- Tab 2 AttachmentDetail: all attachment manifest rows linked via message_id

### Convergence with fileWalker
- sha256 in Attachment Manifest = SHA256 in fileWalker Master_File_Inventory
- OCR output from fw_ocr will link back via sha256

### Downstream: Chroma / RAG (PLANNED, NOT YET BUILT)
- Primary chunk: Body.SenderText; Secondary: Body.Text
- Metadata: RFC 822 Message ID, Header.From, Header.Date, Header.Subject,
  Header.X-Gmail-Labels, Email.HashSHA256
- Hybrid RAG (BM25 + dense vector)
