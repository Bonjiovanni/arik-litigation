# Aid4Mail Message-ID Filter Pipeline

## Purpose

Pull a specific subset of emails from Gmail by RFC Message-ID, export to JSON,
convert to Excel. Fully automatable from the command line — no GUI interaction required.

---

## Components

### 1. Filter Script — `filter_by_rfc_message_id_csv.flt.py`

**Location:** `C:\Users\arika\AppData\Roaming\Aid4Mail6\Scripts\`

Reads a CSV of RFC Message-IDs, filters emails during Aid4Mail processing,
and produces a defensible audit log.

**Input:** CSV file with one Message-ID per line (angle brackets optional).
**Output:** Audit CSV (`message_id_results.csv`) + summary report (`message_id_filter_summary.txt`).

Audit CSV columns:
```
RequestedMessageID,Status,Found,Exported,MatchCount,Subject,Sender,SentUtcDateTime
```

Status values: `FoundAndExported` | `Missing`

### 2. Modifier Script — `timestamp_json_output.mod.py`

**Location:** `C:\Users\arika\AppData\Roaming\Aid4Mail6\Scripts\`

Appends a timestamp to the target filename so runs never overwrite each other.

Example: `Gmail body master-Stragglers.json` → `Gmail body master-Stragglers (2026-04-10 15-30-00).json`

### 3. Configuration — `ScriptSettings.ini`

**Location:** `C:\Users\arika\AppData\Roaming\Aid4Mail6\Scripts\ScriptSettings.ini`

```ini
[filter_by_rfc_message_id_csv.flt.py]
CSV_FILE=C:\Users\arika\OneDrive\Litigation\Pipeline\message_ids.csv
LOG_FILE=message_id_results.csv
```

- `CSV_FILE` — full path to input Message-ID list
- `LOG_FILE` — output audit log name (relative = written to Aid4Mail DataFolder)

### 4. Input CSV — `message_ids.csv`

**Location:** `C:\Users\arika\OneDrive\Litigation\Pipeline\message_ids.csv`

Template file — populate with your target Message-IDs before running.

```csv
MessageID
<abc123@mail.gmail.com>
<def456@mail.gmail.com>
```

Rules:
- First column only
- Header row optional (skipped if first cell contains "message")
- `#` and `;` lines are comments
- Accepts `<id@domain>` or `id@domain` (normalized automatically)
- Case-insensitive, deduplicates automatically

### 5. JSON → Excel — `export_all_emails.py`

**Location:** `C:\Users\arika\Repo-for-Claude-android\email_pipeline\export_all_emails.py`

Converts Aid4Mail JSON output to Excel. Supports headless mode:
```
python export_all_emails.py "input.json" "output.xlsx"
```

See [email_pipeline.md](email_pipeline.md) for full documentation.

---

## End-to-End Workflow

### Step 1: Populate the Message-ID list

Edit `C:\Users\arika\OneDrive\Litigation\Pipeline\message_ids.csv` with your target IDs.

### Step 2: Configure Aid4Mail session

In Aid4Mail GUI, load your saved session (`Body-gmail to json - FINDING STRAGGL`):
- Set **Python filtering script** → `filter_by_rfc_message_id_csv.flt.py`
- Set **Python modifier script** → `timestamp_json_output.mod.py`
- Save the session

### Step 3: Run from CLI

```bat
"C:\Program Files\Aid4Mail 6\Aid4Mail.exe" /run "C:\Users\arika\OneDrive\Documents\Aid4Mail\Projects\Aid4Mail - get the clean data\Body-gmail to json - for integration w cloudhq - FINDING STRAGGL.settings.ini" /minimized /exit
```

### Step 4: Convert JSON to Excel

```bat
"C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe" "C:\Users\arika\Repo-for-Claude-android\email_pipeline\export_all_emails.py" "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 ti json 2dtime\Gmail body master-Stragglers (TIMESTAMP).json" "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 ti json 2dtime\Gmail body master-Stragglers (TIMESTAMP).xlsx"
```

Replace `(TIMESTAMP)` with the actual timestamp from the modifier script output.

---

## Outputs Per Run

| File | Location | Contents |
|------|----------|----------|
| `...Stragglers (timestamp).json` | Aid4Mail target folder | Exported emails in JSON |
| `...Stragglers (timestamp).xlsx` | Same folder (or chosen) | Excel version of the JSON |
| `message_id_results.csv` | Aid4Mail DataFolder | Per-ID audit: found vs missing |
| `message_id_filter_summary.txt` | Aid4Mail DataFolder | Run stats summary |

---

## Tests

| Test file | Tests | Covers |
|-----------|-------|--------|
| `tests/test_aid4mail_filter_msgid.py` | 31 | normalize_message_id, extract_message_id_from_header, load_settings, load_message_id_csv |
| `tests/test_export_all_emails.py` | 22 | Excel export including 7 headless-mode tests |

---

## Technical Notes

- Filter script runs at **stage 3** (Python filtering) — after Aid4Mail's label-based pre-acquisition filter already narrowed Gmail. Only label-matched emails are downloaded; this script narrows further.
- Matching is on the **RFC Message-ID header** (`a4m_SmtpHeader.Value`), not Gmail internal IDs.
- The modifier script applies the timestamp **once** per session (first MIME event only), using `a4m_SessionMemoryModify` to track state.
- Both scripts use the Aid4Mail Event System (`Initialize` → `MIME` → `Finalize`).
- All Aid4Mail variables use `.Value` suffix (Delphi bridge requirement).

---

---

## Session 2: Attachments

### Attachment Filter Script — `attachment_manifest_v16_msgid_filter.flt.py`

**Locations:**
- `C:\Users\arika\OneDrive\Documents\Aid4Mail\` (canonical)
- `C:\Users\arika\AppData\Roaming\Aid4Mail6\Scripts\` (Aid4Mail runtime copy)

Based on v15 multirun. Identical attachment extraction, dedup, collision handling,
and manifest CSV output — with two additions:
1. Message-ID gate that skips any email not in the CSV list
2. `incremental` run mode for straggler runs

**Configuration:** Same `ScriptSettings.ini`, separate section:
```ini
[attachment_manifest_v16_msgid_filter.flt.py]
CSV_FILE=C:\Users\arika\OneDrive\Litigation\Pipeline\message_ids.csv
```

Both sessions (body + attachments) read from the **same** `message_ids.csv`.

**Aid4Mail session:** "gmail to json attachments for integration w cloudhq python" (#33)
- Set Python filtering script → `attachment_manifest_v16_msgid_filter.flt.py`
- Set Python modifier script → `timestamp_json_output.mod.py`
- All other settings unchanged from your existing attachment runs

**Additional output:** `attachment_msgid_audit.csv` — per-ID audit log (found/missing)

### Run Modes (Attachment_Config_Aid4mail.xlsx)

Set `run_mode` in the config workbook (new key — takes precedence over legacy `fresh_run`):

| run_mode | Dedup maps | Output manifest | Use case |
|---|---|---|---|
| `fresh` | Empty | This run only | First-ever run, or standalone test |
| `accumulate` | Seeded from prior CSVs | Prior + new rows | Merging multiple source formats (Gmail + EML + MSG) |
| `incremental` | Seeded from prior CSVs | **New rows only** | Straggler/update runs — dedup-aware, output only new |

For straggler runs, use `incremental` with `prior_csv_1` pointing at your existing merged manifest.
Attachment files are correctly deduped against the full prior corpus. The output manifest
contains only straggler rows with full file paths (`saved_full_path`), ready for direct
append to SQLite/cache.

### CLI Wrapper

For command-line use, run the wrapper instead of calling Aid4Mail directly:
```
python run_aid4mail_attachments.py
```
- Reads config workbook + ScriptSettings.ini
- Explains all settings with plain-language descriptions
- Asks Y/N confirmation before launching
- `--yes` flag skips confirmation for automation

### Running Both Sessions

```bat
REM Session 1: Email bodies
"C:\Program Files\Aid4Mail 6\Aid4Mail.exe" /run "...Body-gmail to json - for integration w cloudhq - FINDING STRAGGL.settings.ini" /minimized /exit

REM Session 2: Attachments
"C:\Program Files\Aid4Mail 6\Aid4Mail.exe" /run "...gmail to json attachments for integration w cloudhq python.settings.ini" /minimized /exit

REM Convert bodies JSON to Excel
python export_all_emails.py "path\to\Stragglers (timestamp).json" "path\to\Stragglers (timestamp).xlsx"
```

---

## CLI Quick Reference

```
Aid4Mail.exe /run "session.settings.ini"              # run session
Aid4Mail.exe /run "session.settings.ini" /minimized    # run minimized
Aid4Mail.exe /run "session.settings.ini" /minimized /exit  # run + auto-close
```

PowerShell CLI switch syntax uses `+` instead of `.`:
```
-Source+Format:GoogleAPI  (not -Source.Format:GoogleAPI)
```
