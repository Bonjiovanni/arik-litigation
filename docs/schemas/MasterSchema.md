# Litigation Evidence KB — Knowledge Capture Document
Last Updated: 2026-03-27

> **IMPORTANT DISCLAIMER**
> This is a knowledge capture document, not a canonical technical spec.
> Its purpose is to record decisions made, strategies discussed, and work
> completed so that any future conversation or Claude Code session can
> orient quickly without re-explaining context.
>
> Throughout this document, sections are marked as follows:
> - ✅ BUILT / DONE — exists on disk, has been executed
> - 🎯 DESIGNED — architecture decided, not yet built
> - 💬 DISCUSSED — explored but no final decision made
> - ⏳ PENDING — depends on a prior step completing first
> - ❌ DEFERRED — consciously set aside for later
> - 🧪 POC — proof-of-concept tested and working, not yet a finalized pipeline

---

## How to Use This Document

At the start of any new Claude or Claude Code session related to this
project, say:

    Please read this file before we begin:
    "C:\Users\arika\OneDrive\Litigation\09-Data Schemas\MasterSchema.md"

Claude Code slash command (once configured): /kb

---

## Project Overview

Pro se trust litigation, Vermont Superior Court. Arik Marks is the sole
surviving beneficiary of the Marks Family Revocable Trust, seeking removal
of trustee Jeanne for breach of fiduciary duty. Evidence corpus of ~1,600
emails and attachments. Goal: fully extracted, structured, searchable
evidence KB to support court filings. Active two-week filing deadline.

---

## Actual Files on Disk ✅

### Email Bodies (Aid4Mail JSON exports — 3 files)
    "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 ti json 2dtime\Gmail body master.json"
    "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 ti json 2dtime\EML body master.json"
    "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 ti json 2dtime\MSG body master.json"
Status: ✅ BUILT — extracted from Aid4Mail (separate files per source type)

### Merged Email Body Repository
    "C:\Users\arika\OneDrive\Litigation\Pipeline\combined_repository.json"  (1,672 records)
    "C:\Users\arika\OneDrive\Litigation\Pipeline\all_emails (2).xlsx"        [current Excel export]
Status: ✅ BUILT — produced by merge_and_classify.py + export_all_emails.py (see Email Body Pipeline section below)

### Attachment Metadata
    "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 to json with python attachments\attachments w python to json.json"
Status: ✅ BUILT — extracted from Aid4Mail

### Attachment Files (two locations)
    "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 to json with python attachments\attachment\"
    "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 to json with python attachments\embedded\"
Status: ✅ BUILT — files extracted by Aid4Mail

### PDF Classification Script
    "C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 to json with python attachments\pdf_classifier.py"
Status: ✅ BUILT — classifies all files in attachment directory
Output: pdf_classification_report.xlsx (same directory) — confirmed full run completed (69 KB output)

### Attachment Manifest Script
    Script name:   attachment_manifest_v15_multirun.flt.py
    Script type:   Aid4Mail filter script (.flt.py) — NOT a standalone Python script
    Resides in:    Aid4Mail's internal Scripts directory
                   (typically C:\Users\arika\AppData\Roaming\Aid4Mail\Scripts\)
    Invoked via:   Aid4Mail UI — loaded as part of a processing profile,
                   NOT run from the command line
    Output:        Attachment_Manifest.xlsx — one row per attachment, spanning
                   all export runs (Run A, Run B, lawyer EMLs)
    Output loc:    Configured export destination in Aid4Mail profile;
                   currently in Aid4Mail Exports\Aid4 to json with python attachments\
    Naming note:   Windows auto-numbered copies exist (e.g. Attachment_Manifest (10).xlsx,
                   Attachment_Manifest (11).xlsx) from repeated Aid4Mail runs
    Version note:  v15_multirun = 15th iteration of this script; multirun =
                   designed to process across multiple Aid4Mail export runs
Status: ✅ BUILT — script exists and has been executed; Attachment_Manifest.xlsx
  is the primary attachment manifest input to the EmailMaster Power Query pipeline

### Master Schema / Knowledge Capture Doc (this file)
    "C:\Users\arika\OneDrive\Litigation\09-Data Schemas\MasterSchema.md"
Status: ✅ BUILT

---

## Files Planned But Not Yet Built 🎯

### emails_master.jsonl
One record per email. Planned key fields:
- canonical_email_id (primary key)
- thread_id
- source_system
- headers_raw
- from, to, cc, bcc, date_utc
- subject
- body_plain, body_html, body_text_full, body_text_no_quotes
- labels
- integrity hashes (SHA1, SHA256, header hash, body hash)
- MIME structure map

Status: 🎯 DESIGNED — not yet built
Note: Near-term Excel approach (EmailMaster.xlsx) takes priority over JSONL.
JSONL format was originally designed as a Chroma indexing target, but the
Gemini context cache + SQLite approach now supersedes that plan. ChromaDB/vector DB
is shelved unless revisited. combined_repository.json (1,672 records) is the current
canonical email body store; its fields are a superset of what emails_master.jsonl
will require.

### attachments_master.jsonl
One record per attachment file. Planned key fields:
- attachment_id (primary key)
- parent_email_id (foreign key to emails_master)
- file_path, filename, extension
- content_type, disposition, content_id
- file_size_kb, page_count (PDFs)
- text_extracted
- extraction_method (native-pymupdf / vision-claude / ocr-adobe /
  form-fields-mcp / manual)
- ocr_confidence
- is_searchable (Y/N)
- pdf_type (Native/Scanned/Mixed/N/A)
- pdf_ocr_preexisting (Y/N/N/A)
- hashes (MD5, SHA256)
- notes

Status: 🎯 DESIGNED — not yet built
Note: attachments w python to json.json exists with attachment metadata.
Relationship to this planned canonical format and exact field mapping
not yet resolved.

### email_nav.csv
CloudHQ enrichment table joined to emails on RFC 822 Message-ID.
Contains PDF volume/page pointers, Thread ID, Message ID, and navigation
metadata from original CloudHQ export.

Status: 💬 DISCUSSED — exists in some form, exact current state and
field names not confirmed

---

## Master Excel File Strategy 🎯

Near-term target: EmailMaster.xlsx — two-tab Excel workbook.

Design decided:
- Tab 1 EmailMaster: one row per email, cols from WorkingCopyTable + AllEmailBod joined
- Tab 2 AttachmentDetail: attachment manifest rows linked via message_id
- Join key: RFC 822 Message-ID (authoritative across all sources)
- Body text sourced via AllEmailBod PQ (parameterized by Email_Body_Input_File) —
  NOT embedded directly in Excel cells
- Field selection not yet finalized

Current working workbook: V11.xlsx (see Email Body Pipeline section)
Longer-term: emails_master.jsonl available if vector DB approach is ever revisited (currently shelved in favor of Gemini cache + SQLite)

Status: 🎯 DESIGNED — EmailMaster.xlsx not yet built

---

## Chroma Search Architecture — SHELVED

> **Status: SHELVED** — Superseded by Gemini context cache + SQLite FTS5 approach
> (see Email Sifter section). ChromaDB is installed locally but not configured or
> used. This section preserved for reference if a vector DB approach is ever revisited.

### Originally Planned Collections

**case_marks_sender**
- Quote-stripped sender-only email text
- Paragraph-aware chunks, 800-1200 tokens, zero overlap
- Primary search surface, highest signal

**case_marks_thread**
- Rolling conversation windows, 8-20 messages
- Step size 4-10 messages
- Not quote-stripped, preserves context
- Pattern detection surface

**case_marks_full** (deferred)
- Full email bodies with quoted history
- High noise, fallback only

---

## Indexing Pipeline Scripts 🎯

All four scripts designed but not yet built.
Planned project name: a4m-indexer (directory not yet created)

1. build_chunks.py
   Input: emails_master.jsonl
   Output: sender_items.jsonl, thread_items.jsonl

2. dedup.py
   Input: sender_items.jsonl, thread_items.jsonl
   Output: deduped versions + dedup_map.jsonl

3. index_to_chroma.py
   Input: deduped files
   Action: upserts to Chroma collections

4. search.py
   Input: plain English query (CLI)
   Output: merged results, sender + thread collections

5. run_pipeline.py
   Orchestrator — runs scripts 1-3 in sequence

Status: 🎯 DESIGNED — not yet built

---

## PDF Attachment Processing Pipeline

### Step 1 — Classification ✅
Script: pdf_classifier.py
Output: pdf_classification_report.xlsx

Classifies every file in attachment directories.

PDF columns:
- Filename, Full Path, File Size (KB), Page Count
- Type: Native / Scanned / Mixed / Protected / Error
- OCR: Y / N / N/A
- Avg Chars Per Page, Notes

Non-PDF columns:
- Filename, Full Path, File Size (KB), Extension
- Category: Word Document / Spreadsheet / Image / Audio/Video /
  Email File / Text / Presentation / Archive / Other/Unknown
- PDF-specific columns left blank

Output sorted by Extension then Filename.

### Classification Report Summary ⏳
PENDING — populate when script completes

- Total files:
- PDF Native:
- PDF Scanned:
- PDF Mixed:
- PDF Protected:
- PDF Error:
- OCR Y:
- OCR N:
- OCR N/A:
- Images:
- Word Documents:
- Spreadsheets:
- Audio/Video:
- Email Files:
- Text:
- Other:

### Step 2 — PDF Extraction Routing 🎯
Status: DESIGNED — not yet built

Routing logic decided:
- Native → pymupdf text extraction
- Scanned, no OCR → Claude Vision structured extraction
- Scanned, OCR already applied → evaluate quality first,
  re-process with Claude Vision if degraded
- Mixed → page-by-page handling
- Fillable forms → PDF Tools MCP read_pdf_fields

### Step 3 — Non-PDF Processing ❌
Status: DEFERRED — PDF pipeline must complete first
File types to handle: Word docs, images, spreadsheets,
audio/video, email files (.msg/.eml)

⚠️ **REVISIT DOCLING + DATA PREP KIT HERE** (added 2026-04-05):

### Docling + Data Prep Kit — Pipeline Augmentation Suggestions 💬

Evaluated 2026-04-05. Both tools are open-source, run locally, no cloud dependency.
Docling: IBM document converter — PDF, DOCX, PPTX, XLSX, CSV, HTML, images,
audio, XBRL financial reports, and more. GitHub: https://github.com/DS4SD/docling
Data Prep Kit: IBM pipeline orchestrator — sits on top of Docling for batch processing,
deduplication, quality scoring, filtering. GitHub: https://github.com/data-prep-kit/data-prep-kit
Install: `pip install docling` / `pip install data-prep-toolkit`
Docling MCP server also available: `docling-mcp` — allows Claude to convert docs on-the-fly.

**Ruled out for PDF extraction** — pymupdf + Claude Vision + PDF Tools MCP are better per-type.
**Ruled out for email corpus** — SQLite + Gemini cache handles that (see Email Sifter section).
**Valuable for non-PDF processing and drive-level sifting** — see below.

Also evaluated and ruled out (2026-04-05):
- **Unity Catalog** — enterprise data lake governance, overkill at any scale we operate at
- **Apache Iceberg / Delta Lake** — distributed table formats, no benefit on single workstation

#### Level 1 — Sift

Use Data Prep Kit to augment the existing fileWalker + classifier output before manual review.
- fileWalker and the classifier have already produced the 600K-row inventory with
  keep/ignore/maybe classifications based on file metadata and extensions
- Data Prep Kit takes that existing output as input and enriches it by actually opening
  files — validating that extensions match real content, flagging near-duplicates,
  scoring directories by likely value
- This converts "maybe" rows into confident "keep" or "ignore" before you review,
  so your manual pass is faster and better informed
- Does not replace fileWalker — builds on top of what it already produced

#### Level 2 — Narrow

Use Docling to fill the non-PDF triage gap that currently has no tool.
- PDF triage is handled — the PDF classifier reports page counts, types, OCR status
- For every other file type (Word docs, spreadsheets, images, HTML) there is nothing
  that can look inside a file and tell you whether it has substantive content
- Docling does a lightweight read across non-PDF candidates and reports: structured
  content vs empty template, tables vs prose vs junk, with confidence scores
- This gives you a scored, ranked list of non-PDF files worth extracting — the same
  kind of output the PDF classifier gives you for PDFs

#### Level 3 — Extract

Use Docling to replace the missing Step 3 extraction pipeline for non-PDF files.
- PDF extraction is designed: pymupdf for native, Claude Vision for scanned, PDF
  Tools MCP for fillable forms
- Non-PDF extraction has no tool assigned — Step 3 is deferred with no plan
- Docling handles Word docs, spreadsheets, images (layout-aware OCR), HTML,
  XBRL — one tool covering every gap
- Use Data Prep Kit to orchestrate the extraction at scale — batch processing, error
  handling, quality scoring, flagging low-confidence results for human review
- Extracted text feeds into the same downstream destinations: SQLite for keyword
  search, Gemini cache for semantic search

#### Additional Context

- Non-email images on the local hard drive (outside the email attachment corpus)
  have not yet been inventoried or processed — photographed documents, scanned
  letters, screenshots scattered across litigation folders. Docling is the candidate
  for this broader image corpus once inventoried.
- Existing image classification POC: `script-for images folder.js` in
  `C:\Users\arika\gemini-images-lab\` — Node.js script using Gemini Vision API.
  Classifies images (category, subtype, relevance) but does NOT extract text content.
  Docling would complement this by doing the actual text extraction from images
  that the POC identifies as documents.

---

## PDF Extraction Method Decisions 💬

### Financial Statements (e.g. EastRise mortgage statements)
These are scanned image PDFs with consistent repeating structure.
Decision: Claude Vision extraction directly to structured JSON.

Rationale:
- Adobe OCR produces text blob requiring further parsing
- Claude Vision skips that step, returns structured data directly
- Running both is duplicative for scanned docs (both read same pixels)
- Double-processing only warranted for specific ambiguous numbers
  being cited in a filing — handled via human spot-check, not
  second pipeline pass

### Fillable Government/Legal Forms
Decision: PDF Tools MCP read_pdf_fields
Returns perfect key-value pairs, no OCR needed.
Note: This method performed excellently in a prior session.

### Letters and Correspondence
- Native → pymupdf
- Scanned → Claude Vision for prose extraction

### Adobe Acrobat Pro Use Cases
Best for: complex scanned prose documents, letters where you need
text output and layout is complex.
Not needed for: financial statements with known schema (Vision better),
fillable forms (MCP better), native digital docs (pymupdf better).

Status: 💬 DISCUSSED — routing logic decided, scripts not yet built

---

## Financial Statement Extraction Schema 🎯

Applies to mortgage/bank statements via Claude Vision.
One JSON record per statement:

    {
      "statement_date": "",
      "account_number": "",
      "due_date": "",
      "amount_due": "",
      "late_fee_threshold": "",
      "principal_balance": "",
      "interest_rate": "",
      "principal_component": "",
      "interest_component": "",
      "escrow_component": "",
      "regular_payment": "",
      "fees_charged": "",
      "past_due_amount": "",
      "total_due": "",
      "transactions": [
        {"date": "", "description": "", "payment": "", "charge": ""}
      ],
      "paid_last_period": {
        "principal": "", "interest": "", "escrow": "",
        "fees": "", "partial": "", "total": ""
      },
      "paid_ytd": {
        "principal": "", "interest": "", "escrow": "",
        "fees": "", "partial": "", "total": ""
      }
    }

Status: 🎯 DESIGNED — schema decided, extraction script not yet built

---

## EastRise Mortgage Statements — Evidence Summary ✅

Account: 101185
Property: 6 Lavigne Rd, South Hero VT 05486
Borrowers: Robert Marks and Barbara B Marks
Interest Rate: 3.250%
Regular Payment: $1,388.31/month

Three statements reviewed and analyzed:

| Statement Date | Amount Due | Past Due   | Paid Last Period | Notes                              |
|----------------|------------|------------|------------------|-------------------------------------|
| 12-07-2024     | $2,776.62  | $1,388.31  | $0.00            | One payment missed                 |
| 01-07-2025     | $4,234.35  | $2,776.62  | $0.00            | Late charge $69.42 on 12-16-2024   |
| 10-07-2025     | $5,894.56  | $4,506.25  | $1,388.31        | First payment made 09-22-2025      |

Litigation narrative: Trustee allowed trust property mortgage to fall into
serious delinquency from at least December 2024 through October 2025, with
only one payment made in that entire period. Core evidence of breach of
fiduciary duty.

---

## Key Architectural Principles ✅

Decided and fixed — these do not change:

1. Deterministic acquisition — Aid4Mail extraction is source of truth,
   never re-run or modified
2. Non-destructive — originals never modified, OCR stored separately
3. Accuracy over speed — litigation use case, evidence must be verified
4. Full provenance — every record traceable to source file and parent email
5. Extraction method logged — every record carries extraction_method field
6. Human review queue — low confidence or filing-critical data gets
   manual spot-check before entering evidence record
7. AI governance — AI proposes structural changes, human approves
8. Legally defensible — integrity hashes, clear chain of custody

---

## Tool Stack ✅

| Tool                          | Purpose                        | Status                      |
|-------------------------------|--------------------------------|-----------------------------|
| Aid4Mail                      | Forensic email extraction      | ✅ Done                     |
| Adobe CC Pro / Acrobat Pro    | Complex OCR, export            | ✅ Available                |
| Claude Pro                    | Vision extraction, analysis    | ✅ Active                   |
| Google AI Pro / Gemini Pro    | Large doc analysis             | ✅ Active                   |
| NotebookLM Pro                | Corpus synthesis, retrieval    | ✅ Active                   |
| Paxton AI                     | Legal research                 | ✅ Active                   |
| ChatGPT Plus                  | Supplementary analysis         | ✅ Active                   |
| M365 Personal                 | Word, Excel                    | ✅ Active                   |
| Python / Claude Code in VS Code | Pipeline development         | ✅ Active                   |
| PDF Tools MCP                 | Form field extraction          | ✅ Installed                |
| Filesystem MCP                | File access                    | ✅ Installed                |
| Windows-MCP                   | Windows automation             | ✅ Installed                |
| Desktop Commander MCP         | Windows Search, CLI            | ✅ Installed                |
| ChromaDB                      | Semantic search backend        | ⏸️ Installed, not in use (shelved in favor of Gemini cache) |
| Chroma MCP                    | Chroma to Claude bridge        | ⏸️ Installed, not in use    |
| pymupdf (fitz)                | Native PDF extraction          | ✅ Installed (used by JH LTC scripts) |
| openpyxl                      | Excel generation               | ✅ Installed (classifier)   |
| Gemini Vision API (Node.js)   | Image file classification      | 🧪 POC tested, not in production |

---

## Email Body Pipeline ✅

Scripts now in repo: `C:\Users\arika\Repo-for-Claude-android\email_pipeline\`

Pipeline chain:
```
Gmail body master.json  --+
EML body master.json      +--> merge_and_classify.py --> combined_repository.json
MSG body master.json    --+        (uses strippers.py)
                                          |
                                          v
                                 export_all_emails.py
                                          |
                                          v
                               all_emails (2).xlsx [current]
                                          |
                                          v
                    AllEmailBod PQ (Email_Body_Input_File param) in V11.xlsx
```

Key scripts:
- merge_and_classify.py — merges/dedupes 3 sources, classifies strip_method, writes body_clean
- strippers.py — quote-stripping library (10 methods) + attorney sig removal
- export_all_emails.py — JSON → Excel via xlsxwriter
- validate_attachments.py — validates attachment manifest vs disk
- read_xlsx.py — utility: dumps any .xlsx to JSON

Primary workbook: `label_LegalEmailExtracts - Ariks Version V11.xlsx`
Universal join key: RFC 822 Message-ID

---

## Image File Processing — Gemini Vision POC 🧪

**Status: Proof-of-concept — successfully tested, not yet a finalized pipeline**

A working capability was demonstrated for classifying non-PDF image files
(JPG, PNG, etc.) from the attachment corpus using the Gemini Vision API.
This is distinct from the PDF pipeline and handles image-format attachments
that cannot be processed by pymupdf or PDF Tools MCP.

### Scripts

Location: `C:\Users\arika\gemini-images-lab\`

| Script | Purpose |
|--------|---------|
| `script.js` | Basic API connectivity test — sends a single image to Gemini, verifies response |
| `script-for images folder.js` | Batch classification script — processes a folder of images, outputs Excel with embedded thumbnails |

### How the batch script works

- Launches a Windows folder-picker dialog to select the target image folder
- Scans for all image files (JPG, JPEG, PNG, GIF, WebP, BMP)
- Sends each image to `gemini-3.1-flash-image-preview` via Google Generative AI SDK
- Classifies each image with a litigation-specific prompt:
  - **Category**: document / screenshot / other / unrelated
  - **Subtype**: invoice / statement / letter / legal-filing / form / financial-report / email / etc.
  - **Issuer**: company or person who produced the document
  - **Relevance**: high / medium / low
  - **Summary**: one-sentence description of what it is and why it may matter
- Outputs `image_review.xlsx` in the same folder, with thumbnail images
  embedded in column A and classification results in subsequent columns

### Runtime

- Node.js script, requires `@google/generative-ai` and `exceljs` packages
- API key via environment variable `API_KEY` (Google AI API key)
- Tested and confirmed working

### Relationship to broader pipeline

This capability covers the gap in the attachment processing pipeline for
image-format files. The PDF pipeline (`pdf_classifier.py`) handles PDFs;
this script handles the image bucket. Both feed into the same goal of
producing a classified, reviewable inventory of the full attachment corpus.

### Next steps (not yet designed)

- Decide whether this becomes a standalone tool or integrates into the
  main attachment pipeline
- Determine output schema alignment with `pdf_classification_report.xlsx`
  so image and PDF results can be merged into a single inventory
- Consider whether the litigation-specific prompt needs refinement based
  on actual corpus results
- Script currently processes one flat folder — may need recursive folder
  support for the full attachment directory tree

---

## Email Sifter — Search Architecture ✅

Last updated: 2026-04-08. Database built and loaded.

### Goal
A single, unified, searchable email corpus combining email bodies and attachment
content — stored locally and queryable via a hybrid semantic + keyword search
invokable as a Claude skill.

### Decision: One Gemini Context Cache (not Vertex AI, not two caches) ✅
- Google AI Pro provides 2M token cache limit
- Email corpus (12-field slim CSV): ~830K tokens
- Extracted attachment text (estimated): ~320-400K tokens
- Total estimated: ~1.1-1.2M tokens — fits in one cache with 800K+ to spare
- One cache = full cross-referencing between email bodies and attachment content
  in a single Gemini response (critical for litigation — e.g. email says one thing,
  attachment shows another)
- Vertex AI ruled out: overkill for 1,550 rows, enterprise infrastructure not
  warranted at this scale
- Two-cache architecture ruled out: Gemini can only reference one cache per API
  call; two caches cannot cross-reference in a single response

### Decision: SQLite with Two Tables (renamed database) ✅
**Database name: `litigation_corpus.db`** (renamed from `email_sifter.db`)
**Location:** `C:\Users\arika\OneDrive\Litigation\Pipeline\litigation_corpus.db`

Database scope: Single unified database for ALL evidence types (emails, texts, files), not just emails.
- `emails_master` — sourced from V11.xlsx (99 columns, 1,550 rows)
- `attachments` — sourced from Attachment_Manifest_GML_EML_MSG (1).xlsx
  (2,154 rows, one per attachment)
- `entity_master` — shared entity table (currently empty, reserved for future expansion)
- `entity_candidates` — shared entity candidates table (currently empty, reserved for future expansion)
- Join key: RFC 822 Message ID throughout
- FTS5 virtual tables (`_fts_emails`, `_fts_attachments`) index Subject + body_clean.1 and attachment filenames + extracted text for keyword/literal search
- Physical files (PDFs, images, docs) stay on disk — SQLite holds paths only
- SQLite role: keyword search + full metadata retrieval after a cache hit

**Status: BUILT 2026-04-08**
- Database loaded: 1,550 emails from V11.xlsx Merge1 sheet
- Attachments loaded: 2,154 from manifest
- Orphan attachments: 187 flagged (in manifest but no parent email)
- FTS5 indexed: `_fts_emails` (Subject + body_clean.1), `_fts_attachments` (filename + extracted_text)
- Entity tables created: empty, ready for future use
- Tests: 52 passing

### Decision: What Goes in the Cache 🎯
- Email bodies + metadata: the 12-field slim CSV as-is
- Extracted attachment text: output of PDF extraction pipeline + Vision extraction
- Attachment metadata stub per record: filename, date, parent email From/Date/Subject
  (essential for grounded answers — Gemini must know which email an attachment came from)
- Physical files: NOT in cache, stay local, referenced by path in SQLite
- Images: Vision-extracted text/description goes in cache, not the image file itself

### Attachment Corpus — Current State ✅
PDF classifier rerun 2026-04-03 against attachment/ folder (342 PDFs, 911 total files):
- Native PDFs: 231 documents, 1,241 pages — extractable via pymupdf now
- Scanned PDFs: 83 documents, 303 pages — need OCR/Vision
- Mixed PDFs: 28 documents, 581 pages — page-by-page handling
- True duplicate PDFs (by SHA256 hash): 5 pairs out of 342 — negligible
- High-value scanned docs identified:
  - Documents supporting Trust accounting: 44 pages
  - MetLife Forms: 22 pages
  - Metlife Life Insurance Claim Forms: 18 pages
  - Eastrise Mail received 6-7-2025: 18 pages
  - TIAA Unclaimed Funds Letter: 14 pages (two copies)
  - DURABLE FINANCIAL POWER OF ATTORNEY - dad to jean: 5 pages
  - Marks Trust Inventory and Accounting through February 2025: 5 pages (two copies)
  - The case for theft: 5 pages

### Decision: Image Handling 🎯
- Embedded images (embedded/ folder, 185 files): mostly signatures/logos — skim
  manifest by filename + size_bytes to identify exceptions (handwritten notes etc.)
- Attachment images (attachment/ folder, 91 jpg/png): intentionally attached —
  run Gemini Vision batch script (already built, POC tested)
- Vision output (extracted text/description) goes into cache, not the image file

### Schema Creation & Data Loading Scripts ✅

**Location:** `C:\Users\arika\Repo-for-Claude-android\`

| Script | Purpose |
|--------|---------|
| `corpus_sqlite_schema.py` | Creates litigation_corpus.db schema: emails_master, attachments, entity_master, entity_candidates tables; FTS5 indexes; FK constraints; domain-aware design |
| `corpus_sqlite_loader.py` | Loads data from Excel sources: emails from V11.xlsx Merge1 sheet, attachments from manifest. CLI args for file paths. Validates orphans. |
| `tests/test_corpus_sqlite.py` | 52 tests covering: schema creation, field mapping, data loading, foreign keys, FTS5 functionality, domain isolation |

### Claude Skill 🎯
- A Claude skill that detects email corpus queries and runs hybrid search:
  1. Gemini API call with cached context → semantic hits
  2. SQLite FTS5 query → keyword/literal hits
  3. Merge by Message ID → pull full record from emails_master
  4. Synthesize grounded response with provenance
- Scripts to build: sifter_gemini.py, sifter_sqlite.py, sifter_hybrid.py

---

## Open Items

- [x] Run pdf_classifier.py — DONE 2026-04-03, results above
- [x] Resolve master Excel file strategy — RESOLVED: EmailMaster.xlsx two-tab design decided
- [x] Decide whether body master.json merges into master Excel — RESOLVED: PQ parameterized approach, not embedded
- [x] Decide search/storage architecture — RESOLVED: one Gemini cache + SQLite (see Email Sifter section)
- [x] Finalize Gemini image pipeline decision — RESOLVED: run Vision on 91 attachment images, skim embedded manifest
- [ ] Confirm field names in attachments json (body fields confirmed via combined_repository.json)
- [ ] Skim Attachment_Manifest embedded rows by filename + size_bytes — flag any non-noise images
- [ ] Run Gemini Vision batch script on 91 attachment/ images (jpg + png)
- [ ] Build PDF extraction pipeline Step 2 — route 83 scanned + 28 mixed PDFs
  - Priority docs: Documents supporting Trust accounting (44p), DURABLE POA (5p),
    Marks Trust Inventory (5p), MetLife Forms (22p+18p), The case for theft (5p)
- [x] Build SQLite DB — emails_master from V11.xlsx + attachments from manifest — DONE 2026-04-08
- [x] Build FTS5 index on Subject + body_clean.1 — DONE 2026-04-08 (tables: `_fts_emails`, `_fts_attachments`)
- [ ] Set up Gemini context cache with 12-field CSV (get API key first)
- [ ] Build Claude skill for hybrid sifter search
- [~] ~~Install ChromaDB and Chroma MCP~~ — SHELVED: installed but not in use; Gemini cache + SQLite approach supersedes
- [~] ~~Build a4m-indexer pipeline scripts~~ — SHELVED: Chroma indexing pipeline not needed under current architecture
- [ ] Build non-PDF processing pipeline — Word docs (26), spreadsheets (16) (deferred)
- [ ] Prompt engineering for Claude Vision financial statement extraction
- [ ] Configure Claude Code /kb slash command

---

## Claude Code Instructions — How to Save This File

To save this file to its correct location on the Windows machine,
paste the following instruction into Claude Code:

    Read the file MasterSchema.md from wherever you saved it during
    this session, then copy it to:
    "C:\Users\arika\OneDrive\Litigation\09-Data Schemas\MasterSchema.md"
    Create the directory if it does not exist.
    Confirm the file was written successfully and show me the file size.

---

*Knowledge capture document. Updated by Claude Code as work progresses.
Not a canonical technical spec — a living record of decisions and progress.*
