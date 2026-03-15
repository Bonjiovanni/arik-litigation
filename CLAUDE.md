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

### Pending test work

| Module | Status | Action needed |
|---|---|---|
| `fw_walk_grp1-5.py` | Being built in "upload file form" chat | Once merged into `fw_walk.py`: write per-group tests + module-level `tests/test_fw_walk.py` (same pattern as fw_dirmap) |

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

### What `test_fw_dirmap.py` covers (module-level only)
- All 13 public functions importable from the merged single-file module
- Full pipeline: `build_dir_records` → `write_dir_inventory_rows` → `initialize_processing_status_rows` → `log_dirmap_run` → all 3 sheets exist with correct row counts
- DirID consistency between Dir_Inventory and Dir_Processing_Status
- 9 distinct file families per directory in DPS
- Save → reload round-trip integrity
- `open_or_create_workbook` for new and existing files
- Continuous DirIDs across multiple roots
- Freeze panes, header rows, idempotent `ensure_*` calls
