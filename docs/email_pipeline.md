# Email Body Processing Pipeline

## Purpose

Processes Aid4Mail JSON exports of Gmail, EML, and MSG email sources into a single
deduplicated, classified, and quote-stripped repository, then exports it to Excel for review.

This pipeline is separate from the fileWalker pipeline. It operates on email body content
extracted via Aid4Mail v6 rather than on the file system.

---

## Two-script workflow

```
Aid4Mail export(s)
       ↓
merge_and_classify.py  →  combined_repository.json  +  _report.json
       ↓
export_all_emails.py   →  all_emails.xlsx
```

Both scripts are interactive: they prompt for file paths via a GUI file picker and remember
your last choices in `Email_Body_Processing_Config.json` (see Config below).

---

## Script 1: merge_and_classify.py

**Location:** `email_pipeline/merge_and_classify.py`

**What it does:**
1. Asks Y/N for each of three input sources (Gmail, EML, MSG). Answering Y opens a file picker.
2. Asks for the output filename via file picker. Warns and re-prompts if file already exists.
3. Loads all selected JSON exports, tags each record with its source.
4. Deduplicates across sources (see Deduplication below).
5. Sorts all winners by `Header.Date` ascending.
6. Classifies each record with a `strip_method` and computes `body_clean` via `strippers.py`.
7. Writes `<output_name>.json` (merged records) and `<output_name>_report.json` (audit trail).
8. Offers to run `export_all_emails.py` immediately against the output file.

**Input format:** Aid4Mail v6 JSON — top-level object with an `emails` array. Each element
is a sparse dict; fields vary by source. Required structure:
```json
{ "emails": [ { "Header.Message-ID": "...", "Body.SenderText": "...", ... }, ... ] }
```

**Hard stop:** If no input files are selected or all are missing, script halts before writing anything.

---

## Script 2: export_all_emails.py

**Location:** `email_pipeline/export_all_emails.py`

**What it does:**
1. Writes all fields from all records to Excel using `xlsxwriter` with `write_string()` — values starting with `=`, `+`, `-`, `@` are never interpreted as formulas.
2. Priority columns appear first; all other columns follow in alphabetical order.
3. Auto-fits column widths (sampled from first 200 rows, capped at 60).

**Three usage modes:**

| Mode | Args | Input | Output | GUI? |
|---|---|---|---|---|
| Standalone | (none) | File picker | File picker | Yes |
| Chained | `argv[1]` | Provided path | File picker | Partial |
| Headless | `argv[1]` + `argv[2]` | Provided path | Provided path | None |

**Examples:**
```
# Standalone — both pickers open
python export_all_emails.py

# Chained from merge_and_classify — input provided, output picker opens
python export_all_emails.py "C:\path\to\combined.json"

# Headless — fully non-interactive, suitable for batch/CLI automation
python export_all_emails.py "C:\path\to\input.json" "C:\path\to\output.xlsx"
```

In headless mode:
- Parent directories for the output path are created automatically.
- Existing output files are overwritten without prompting.
- No tkinter or GUI dependencies are triggered.

**Priority columns (in order):**
`Header.Date`, `Header.Message-ID`, `Address.Sender`, `Address.To`, `Header.Subject`,
`strip_method`, `body_clean`, `Email.Status`, `Header.X-Gmail-Labels`

---

## Deduplication logic

**Primary key:** `Email.HashSHA256`
- Records with matching SHA256 are grouped as duplicates.

**Fallback key:** `Header.Message-ID` (normalized: trimmed, lowercased, `< >` removed)
- Used when SHA256 is absent. Records with matching normalized Message-ID are grouped.

**No-key records:** Records with neither SHA256 nor Message-ID are kept in full (no dedup).

**Winner selection** (highest score wins within each duplicate group):

| Priority | Criterion |
|---|---|
| 1 | Source is EML_FILE or MSG_FILE (file-based = forensically authoritative) |
| 2 | Has non-empty `Source.FileName` or `Source.File` |
| 3 | Larger combined body size (`Body.Text` + `Body.HTML`) |
| 4 | Has non-empty `Email.Header` |
| 5 | Earlier `Session.RunDate` |

Ties broken by first-encountered order (deterministic).
Winner receives a `Merge.DuplicateSessions` field listing all Session.Id values from the group.

---

## strip_method taxonomy

Assigned by `get_strip_method()` in `merge_and_classify.py`, used by `strippers.py`:

| Method | Description |
|---|---|
| `Gmail` | HTML body contains `gmail_quote` class — outermost quote div removed |
| `Outlook` | HTML/text body cut at `From:` / `Sent:` boundary |
| `Forward` | Cut at dash-line header, "Begin forwarded message:", or Outlook boundary |
| `GT_Prefix` | `>`-prefixed quoted lines removed (RFC 2822 plain-text quoting) |
| `Outlook_Plain` | Cut at `-----Original Message-----`, fallback to Outlook boundary |
| `iOS` | Apple Mail "On..., at..., wrote:", Samsung dashes, Mobile Outlook From:/Subject: |
| `OnWrote` | Cut at "On [date] [name] wrote:" attribution line |
| `Original` | No quoted content detected — passthrough |
| `Inline` | Inline reply — stripping would destroy context — passthrough |
| `Clean_Reply` | Sender already deleted quoted text — passthrough |

---

## Attorney signature stripping

Applied as a post-processing step after every quote stripper (including passthroughs).
Removes:
- Gravel & Shea firm signature block (domain: `gravelshea.com`)
- Primmer Piper firm signature block (domain: `primmer.com`)
- "Get Outlook for iOS" mobile app sig line
- Generic confidentiality disclaimer blocks

---

## Config file

**File:** `email_pipeline/Email_Body_Processing_Config.json`
**Not committed to git** (listed in `.gitignore`).

Keys:

| Key | Used by | Meaning |
|---|---|---|
| `last_gmail_dir` | merge_and_classify | Last folder browsed for Gmail export |
| `last_eml_dir` | merge_and_classify | Last folder browsed for EML export |
| `last_msg_dir` | merge_and_classify | Last folder browsed for MSG export |
| `last_output_path` | merge_and_classify | Last output JSON path |
| `last_export_input_dir` | export_all_emails | Last folder browsed for input JSON |
| `last_export_output_path` | export_all_emails | Last output xlsx path |

First run defaults for merge input: `C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 ti json 2dtime\`
First run defaults for export output: `email_pipeline/all_emails.xlsx`

---

## Output files

All output files land wherever you select via the file picker — they are not fixed-path.
They are excluded from git via `.gitignore`.

| File | Produced by | Contents |
|---|---|---|
| `<name>.json` | merge_and_classify | Merged, deduped, classified email records |
| `<name>_report.json` | merge_and_classify | Audit trail: counts, dupe groups, strip method breakdown |
| `<name>.xlsx` | export_all_emails | All records × all fields, Excel-safe |

---

## Dependencies

- `strippers.py` — must be in the same `email_pipeline/` folder as `merge_and_classify.py`
- `xlsxwriter` — for Excel export
- `beautifulsoup4` (`bs4`) — used by strippers.py for HTML parsing
- `tkinter` — standard library, used for file picker dialogs

---

## Related scripts

- `read_xlsx.py` — general utility in `email_pipeline/`; dumps any `.xlsx` to JSON on stdout.
  Used by claude.ai Desktop Commander and other scripts to read Excel files.
  Usage: `python read_xlsx.py <path.xlsx> [sheet_name]`
