# Repo Consolidation Session — 2026-04-09

Session record: consolidating all litigation tools/projects into a single repo, then auditing CLAUDE.md global-vs-project structure.

**Source thread:** `C:\Users\arika\.claude\projects\C--Users-arika-OneDrive-CLaude-Cowork\dd7574b3-2c48-44e7-8288-62db3825303f.jsonl`

---

## Goal

Before this session: project files scattered across 5+ locations plus a GitHub remote with 4 randomly-named branches.

After this session: one repo (`Repo-for-Claude-android`), one branch (`main`), GitHub remote in sync, all docs and scripts consolidated.

Then: automate (1) context/memory management during work sessions, (2) git/checkin workflows.

---

## Pre-Consolidation Inventory

### Locations

| # | Location | Contents |
|---|----------|----------|
| 1 | `C:\Users\arika\Repo-for-Claude-android\` | Main repo — fileWalker, email_pipeline, jh_ltc, drive_scout, tests |
| 2 | `C:\Users\arika\OneDrive\CLaude Cowork\` | Loose scripts + audio_pipeline (its own git repo) + decisions doc |
| 3 | `C:\Users\arika\OneDrive\Litigation\09-Data Schemas\` | MasterSchema.md, doc_data_extraction_spec.md, JH LTC script duplicates |
| 4 | `C:\Users\arika\OneDrive\Litigation\Pipeline\` | Data files (litigation_corpus.db, V11.xlsx, CSVs — 200+ MB total) |
| 5 | `C:\Users\arika\.claude\` | Agents, memory, settings, CLAUDE.md (must stay here) |
| 6 | GitHub: `Bonjiovanni/arik-litigation` | 4 `claude/*` branches, no `main` |

### GitHub Branch Analysis

| Branch | Commits | Date Range | Unique Content |
|--------|---------|-----------|----------------|
| `claude/google-drive-file-metadata-C554z` | 23 | Feb 23 only | OAuth/Termux setup (was the GitHub default) |
| `claude/upload-file-form-sipNu` | 41 | Feb 23 → Mar 23 | All real code (fw_*, email_pipeline, jh_ltc, tests) — 18 unique commits on top of base |
| `claude/excel-android-structured-tables-0J37x` | 1 | Feb 25 | Orphan — `build_workbook.py`, `THREAD_HISTORY.md`, `workbook.xlsx` |
| `claude/hybrid-search-model-fIA7u` | 26 | Feb 23 → Apr 4 | 3 unique CLAUDE.md behavior-rule commits |

### Cross-Branch File Comparison

Only **3 files differ** across branches:
- `.gitignore` — `upload-file-form` has the most complete version
- `requirements.txt` — `upload-file-form` has the most deps
- `CLAUDE.md` — all 3 branches have different versions

Files unique to each branch:
- `upload-file-form` — 80 files (all real code)
- `excel-android` — 3 files (the orphan ones)
- `google-drive`, `hybrid-search` — 0 unique files

**Important:** Commit dates are not authoritative — the user noted "there is no meaning to when commits were done... who knows what is most recent for any given file." But the cross-branch hash comparison proved that `upload-file-form` is effectively the trunk: it has all the unique code, and the only conflicts are the 3 files above.

---

## Consolidation Steps Executed

### 1. Create `main` branch ✅
- Created from `claude/upload-file-form-sipNu` (the de facto trunk)
- All 90 tracked files carried over

### 2. Bring in `excel-android` files ✅
- `build_workbook.py`, `THREAD_HISTORY.md`, `workbook.xlsx` checked out from orphan branch
- Staged for commit

### 3. Audio pipeline subtree merge ✅
- Audio_pipeline was a **separate git repo** at `OneDrive\CLaude Cowork\audio_pipeline\` (own `master` branch, 18 commits)
- Used `git subtree add --prefix=audio_pipeline` to merge with full history preserved
- Original folder deleted from OneDrive after verifying all 50 files made it across (51 in repo — 1 extra from a final commit before merge)
- Required temporary stash of working-tree changes during the merge

### 4. Sort and commit untracked files ✅
**Decision rules from user:**
- All Python files kept (no exceptions, even iterative versions like `compare_body_cols_v1/v2/v3`)
- Working data artifacts kept locally but gitignored (`output/` folder)
- `.claude/` and `.superpowers/` gitignored as machine-specific config
- Index files (`all_py_files.txt`, `my_py_files.txt`) kept and flagged for doc-keeper automation

**29 files committed in one batch** (commit `d63afbf`):
- corpus_sqlite_schema.py, corpus_sqlite_loader.py + tests
- session_importer.py, migrate_fts_prefix.py + tests
- compare_body_cols (v1-v3), check_shortest, csv_to_json_values, type_export
- build_workbook.py, workbook.xlsx, THREAD_HISTORY.md
- _PLANS.md, _automation_recommendations.md, _drive_scout_status.md
- all_py_files.txt, my_py_files.txt
- output/ folder created (gitignored)

### 5. Move scripts from CLaude Cowork into repo ✅
**7 files moved** (commit `d8ab7b2`):
- `elynah_scraper.py`, `find_macros.py`, `pdf_package_builder.py` → repo root
- `Run PDF Package Builder.bat`, `write_comparison.py`, `_query_tmp.py` → repo root
- `sqlite_setup_decisions.md` → `docs/`

**4 files deleted** (junk/temp):
- `tmpclaude-73f8-cwd`, `tmpclaude-74b1-cwd`, `tmpclaude-aa5f-cwd`, `_ul`

CLaude Cowork folder is now empty.

### 6. Move schema docs from Litigation\09-Data Schemas\ ✅
**2 files moved** to `docs/schemas/` (commit `20218eb`):
- `MasterSchema.md`
- `doc_data_extraction_spec.md`

**5 JH LTC scripts deleted** — confirmed identical (binary diff) to repo copies in `jh_ltc/`:
- `batch_eob_process.py`, `batch_invoice_process.py`, `extract_one_detail_page.py`
- `visualize_eob_fields.py`, `visualize_invoice_fields.py`

**Path references updated in 4 files** (same commit):
- `C:\Users\arika\.claude\CLAUDE.md`
- `C:\Users\arika\.claude\projects\C--Users-arika-OneDrive-CLaude-Cowork\memory\MEMORY.md`
- `C:\Users\arika\.claude\Claude Scripts Index.md`
- `C:\Users\arika\.claude\projects\C--Users-arika-OneDrive-CLaude-Cowork\memory\reference_master_index.md`

09-Data Schemas folder is now empty.

### 7. Update .gitignore ✅
Added (commit `d27bc59`):
- `output/` — working data artifacts
- `*.db` — database files (live in `Litigation\Pipeline\`)
- `audio_pipeline/.pytest_cache/`, `audio_pipeline/speakers/`, `audio_pipeline/transcripts/`

Kept conservative — no blanket `*.csv` or `*.xlsx` rules.

### 8. Push `main` to GitHub and set as default ✅
- `git push -u origin main` — created remote tracking branch
- User set `main` as default branch via GitHub web UI Settings page
- gh CLI was installed mid-session but not authenticated (interactive login required)

### 9. Old branches NOT yet deleted
**Reason:** They serve as a safety net until `main` is verified complete and CLAUDE.md is rewritten. To be deleted at end of consolidation:
- `claude/google-drive-file-metadata-C554z`
- `claude/upload-file-form-sipNu`
- `claude/excel-android-structured-tables-0J37x`
- `claude/hybrid-search-model-fIA7u`

---

## CLAUDE.md Analysis — Global vs Project

### How Global vs Project CLAUDE.md works

- **Global** (`C:\Users\arika\.claude\CLAUDE.md`) — loaded in every Claude Code session regardless of folder
- **Project** (`<repo>\CLAUDE.md`) — loaded only when Claude Code opens that folder
- **Both load** when in a project — global first, then project. Project should not duplicate global.

### Clashes (need resolution)

| # | Topic | Global says | Project says | Resolution |
|---|-------|------------|-------------|-----------|
| 1 | Excel rule | ExcelMCP preferred, xlsxwriter fallback | MUST use Excel MCP, never Python | **Keep global** — fallback needed for headless/pipeline scripts. Delete from project. |
| 2 | Branch name | (n/a) | `claude/upload-file-form-sipNu` | **Update project** to `main` |
| 3 | JH LTC location | (n/a) | "not yet in repo" at `09-Data Schemas\` | **Update project** — they're in `jh_ltc/` now |
| 4 | User context | Windows/PowerShell | Android/Linux/Termux | **Delete from project** — stale |

### In Global, not Project (where they should stay)

| # | Topic | Location |
|---|-------|----------|
| 1 | Session start checklist (UI check, master file versions) | **Global** |
| 2 | Master index pointers (Documentation Index, Scripts Index) | **Global** |
| 3 | claude.ai vs Claude Code capabilities table | **Global** |
| 4 | Adobe Acrobat Pro instructions | **Global** |
| 5 | Python environment (3.11 path, packages) | **Global** |
| 6 | Permanent tool permissions (read, legal-style-comparator) | **Global** |
| 7 | Workbook safety (never delete master.xlsx) | **Global** (with project pointer) |
| 8 | User dictation → write to disk immediately | **Global** |
| 9 | Execution discipline rules | **Global** |
| 10 | Testing Guru workflow (never edit tests, _testing_needed.md) | **Global** |
| 11 | TDD rules | **Global** |
| 12 | Remote control / mobile session rules | **Global** |
| 13 | Shell preference (PowerShell) | **Global** |
| 14 | Communication rules (no fake sympathy, no extrapolation, verify) | **Global** |
| 15 | Conversation flow rules (user controls topic) | **Global** |
| 16 | Agent context safety (85% capacity protocol) | **Global** |
| 17 | Known user directories (Screenshots) | **Global** |
| 18 | xlsm macro preservation | **Global** |

### In Project, not Global (suggested destinations)

| # | Topic | Suggested destination |
|---|-------|----------------------|
| 1 | Google Drive OAuth setup | **Delete** — stale Termux/Android context |
| 2 | Google Cloud project details | **Delete** or move to `docs/google_drive_setup.md` if keeping |
| 3 | fileWalker architecture (phases, build rules) | **`docs/pipeline_architecture.md`** (already exists, merge in) |
| 4 | Testing suite docs (every test file mapped to module) | **Slim version in project CLAUDE.md** + full table → **`docs/testing.md`** |
| 5 | Email pipeline chain diagram | **`docs/email_pipeline.md`** (already exists, merge in) |
| 6 | Email pipeline script docs | **`docs/email_pipeline.md`** |
| 7 | Data sources (Aid4Mail, CloudHQ, attachment manifest) | **`docs/email_pipeline.md`** or **`docs/schemas/MasterSchema.md`** |
| 8 | V11 workbook details (PQ queries, parameters) | **`docs/email_pipeline.md`** |
| 9 | Three-way audit results | **`docs/email_pipeline.md`** |
| 10 | EmailMaster.xlsx design (planned, not built) | **`docs/email_pipeline.md`** |
| 11 | sha256 convergence (email ↔ fileWalker) | **`docs/pipeline_architecture.md`** |
| 12 | ChromaDB shelved note | **`docs/email_pipeline.md`** (historical) |
| 13 | Behavior rules from `hybrid-search` branch ("don't patronize", cloud vs local) | **Global** — merge with existing Communication Rules |

### Net Result

Project CLAUDE.md goes from **300 lines → ~50 lines**:
- Repo description (what this is)
- How to run tests
- Current branch (`main`)
- Pointers to active project docs in `docs/`
- Anything else gets deleted or moved to `docs/`

---

## Files in Repo After Consolidation

### Top-level structure
```
Repo-for-Claude-android/
├── main branch
├── audio_pipeline/          # subtree-merged from CLaude Cowork (19 commits history)
├── docs/
│   ├── ClaudeCode_Onboarding_Prompt.md
│   ├── config_architecture_decision.md
│   ├── consolidation_session_2026-04-09.md  ← THIS FILE
│   ├── email_pipeline.md
│   ├── fw_ocr_vision_spec.md
│   ├── pipeline_architecture.md
│   ├── sqlite_setup_decisions.md            ← moved from CLaude Cowork
│   └── schemas/
│       ├── MasterSchema.md                  ← moved from 09-Data Schemas
│       └── doc_data_extraction_spec.md      ← moved from 09-Data Schemas
├── email_pipeline/
├── jh_ltc/
├── output/                  # gitignored — working artifacts
├── tests/
├── (root-level fw_*, drive_scout_*, corpus_sqlite_*, etc.)
├── CLAUDE.md                # to be rewritten next
└── .gitignore               # updated
```

### Empty source folders (verify and clean up)
- `C:\Users\arika\OneDrive\CLaude Cowork\` — empty
- `C:\Users\arika\OneDrive\Litigation\09-Data Schemas\` — empty

---

## Outstanding Work

1. **Rewrite project CLAUDE.md** — gut to ~50 lines per analysis above
2. **Update Documentation Index, Scripts Index, MEMORY.md, reference_master_index.md** — many stale entries (corpus_sqlite scripts, audio_pipeline new location, etc.)
3. **Delete the 4 old `claude/*` branches** (local + remote) once CLAUDE.md is verified
4. **Set up automation** — the original goals:
   - Context/memory management during sessions
   - Git/checkin workflow automation (user explicitly said "I dont know what the heck I'm doing in that")

---

## Commits This Session

| SHA | Message |
|-----|---------|
| `445fba9` | Add 'audio_pipeline/' from commit 'f091a2f' (subtree merge) |
| `d63afbf` | Consolidate: add untracked scripts, output folder, gitignore updates |
| `d8ab7b2` | Consolidate: move CLaude Cowork scripts into repo |
| `20218eb` | Consolidate: move schema docs from OneDrive to repo |
| `d27bc59` | Update .gitignore: add *.db, audio_pipeline artifacts |

Plus pending: this consolidation session doc + CLAUDE.md rewrite.
