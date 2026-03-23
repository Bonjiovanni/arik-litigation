# Claude Code Onboarding Prompt — Email Pipeline Integration
# Created: 2026-03-15
# Updated: 2026-03-18 — major session update:
#   - Workbook renamed from V10.xlsx to V11.xlsx
#   - AllEmailBod PQ now sources from external file via Email_Body_Input_File parameter
#   - All Email Bodies sheet eliminated — replaced by parameterized PQ
#   - CloudHQ_Live connected as live PQ source via Google Sheets publish-to-web CSV URL
#   - Three-way audit query built (ThreeWayAudit) comparing AllEmailBod/WorkingCopyTable/CloudHQ_Live
#   - Audit results: 1,695 unique emails, 145 gaps (81 CloudHQ-only, 64 EML-only)
#   - 81 CloudHQ-only rows = delta list for next Aid4Mail export run
#   - merge_and_classify.py needs update: output filename hardcoded, needs auto-increment (PENDING)
#   - merge_and_classify.py needs update: input filenames hardcoded, need to be configurable (PENDING)
# Purpose: Bring Claude Code up to speed on the email evidence pipeline
#          and integrate it with the existing fileWalker documentation in CLAUDE.md
# Usage: Paste this entire prompt into a Claude Code session

---

## OVERVIEW — Why This Prompt Exists

This prompt exists because the litigation evidence pipeline has two major
workstreams that were built in separate sessions and have never been
documented together in one place:

**Workstream 1 — fileWalker (already in CLAUDE.md)**
A Python pipeline that walks the OneDrive file system, classifies files,
scores them for litigation relevance, and routes them for OCR processing.
This is documented in CLAUDE.md and docs/pipeline_architecture.md in the
repo at C:\Users\arika\Repo-for-Claude-android.

**Workstream 2 — Email Evidence Pipeline (NOT yet in CLAUDE.md)**
A separate pipeline built to extract, merge, clean, and structure ~1,600+
litigation emails from three source types (Gmail, EML, MSG files) exported
via Aid4Mail. This pipeline was built across multiple chat sessions and
the Python scripts live in C:\Users\arika\OneDrive\Litigation\Pipeline\.
It has never been formally documented in CLAUDE.md or MasterSchema.md.

**Why they need to be unified now:**
Both pipelines feed the same litigation case and converge at two points:
1. The attachment files — emails have attachments that fileWalker also
   walks and classifies. The sha256 hash is the join key between them.
2. ChromaDB — both email bodies and extracted attachment text will
   eventually be indexed for hybrid RAG + BM25 semantic search.

**What this prompt asks Code to do:**
1. Read and orient on existing documentation
2. Search memory for any additional context from prior sessions
3. Inventory all known email pipeline scripts
4. Ask the user curation questions before touching anything
5. Append a new Email Evidence Pipeline section to CLAUDE.md
6. Update MasterSchema.md to close out open items that are now resolved
7. Commit both documentation updates to git

**IMPORTANT RULE: Do not modify any code files. Documentation updates only.
Do not build anything. Do not run any scripts. Ask before touching anything
not explicitly listed in the steps below.**

---

## STANDING INSTRUCTION — Ask questions throughout

This applies to every step in this prompt without exception.
If at any point you need info, find a conflict, are uncertain, or are about
to make an assumption — STOP and ask. Do not guess. This is a litigation
evidence project where incorrect assumptions can corrupt the pipeline.

---

## STEP 1 — Read existing documentation first

WHY: Claude Code has no memory between sessions. Reading these files ensures
you are oriented before proceeding. Do not skip even if you think you remember.

Read in order:
1. C:\Users\arika\Repo-for-Claude-android\CLAUDE.md
2. C:\Users\arika\Repo-for-Claude-android\docs\pipeline_architecture.md
3. C:\Users\arika\OneDrive\Litigation\09-Data Schemas\MasterSchema.md

Confirm you have read all three with a one-line summary of each.

---

## STEP 2 — Search memory and chat history

WHY: Significant design work was done in Claude.ai chat sessions, not Code.
This surfaces context not yet in the .md files.

Search for: Aid4Mail exports, CloudHQ spreadsheet, ChromaDB, attachment OCR,
body text extraction, Power Query joins, EmailMaster.xlsx design.

Summarize what you find in a brief paragraph.

---

## STEP 3 — Inventory all email pipeline scripts

WHY: Scripts were written across many sessions. Some are active, some superseded.
We need a clear picture before documenting anything.

ALREADY REVIEWED — verify accuracy and confirm status:

| Script | Known purpose |
|--------|--------------|
| merge_and_classify.py | Stage 1: reads 3 Aid4Mail JSON exports (Gmail/EML/MSG), merges + deduplicates on SHA256 then Message-ID, classifies strip_method, writes body_clean via strippers.py, outputs combined_repository.json + merge_report.json. PENDING FIX: input and output filenames hardcoded |
| strippers.py | Body text cleaning library — strips quoted reply text per strip_method, leaving only sender words |
| export_all_emails.py | Stage 2: reads combined_repository.json, exports to all_emails (N).xlsx, auto-increments filename, never overwrites. Current active: all_emails (2).xlsx |
| validate_attachments.py | Validates attachment manifest against disk — outputs validation_report.xlsx |

NEED YOUR REVIEW — read and summarize:
C:\Users\arika\OneDrive\Litigation\Pipeline\read_xlsx.py
C:\Users\arika\OneDrive\Litigation\09-Data Schemas\batch_eob_process.py
C:\Users\arika\OneDrive\Litigation\09-Data Schemas\batch_invoice_process.py
C:\Users\arika\OneDrive\Litigation\09-Data Schemas\extract_one_detail_page.py
C:\Users\arika\OneDrive\Litigation\09-Data Schemas\visualize_eob_fields.py
C:\Users\arika\OneDrive\Litigation\09-Data Schemas\visualize_invoice_fields.py

Present as table: Script | What it does | Status (ask me).

---

## STEP 4 — Ask me curation questions

WHY: Only the user knows which scripts are active vs superseded and whether
any are missing. Getting this right before writing to CLAUDE.md is critical.

Ask me:
1. Which scripts are active vs superseded or abandoned?
2. Are there other script locations not listed above?
3. Which scripts should be documented in CLAUDE.md?
4. Any scripts to rename, move, or consolidate first?

Wait for my answers before proceeding to Step 5.

---

## STEP 5 — Append email pipeline section to CLAUDE.md

WHY: CLAUDE.md is the root context file every future Code session reads first.
Without this section, any session working on email starts from zero.
Appending protects existing fileWalker content.

Append to BOTTOM of C:\Users\arika\Repo-for-Claude-android\CLAUDE.md.
DO NOT modify anything already in the file.
UPDATE script list based on Step 4 answers before appending.

---

## Email Evidence Pipeline — Separate System, Same Case

This is a second major pipeline alongside fileWalker, operating on email
evidence. Both converge at the Chroma indexing layer.

### Email Body Pipeline Chain

    Gmail body master.json  --+
    EML body master.json      +--> merge_and_classify.py --> combined_repository.json
    MSG body master.json    --+        (uses strippers.py)      + merge_report.json
                                                                       |
                                                                       v
                                                            export_all_emails.py
                                                                       |
                                                                       v
                                                        all_emails (2).xlsx [CURRENT]
                                                                       |
                                                                       v
                                         AllEmailBod PQ (via Email_Body_Input_File param)
                                                                       |
                                                                       v
                                                    AllEmailBod_1 table in V11.xlsx

All intermediate files: C:\Users\arika\OneDrive\Litigation\Pipeline\
Aid4Mail JSON sources: C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 ti json 2dtime\

### Email Pipeline Scripts (confirmed)

**merge_and_classify.py**
- Path: C:\Users\arika\OneDrive\Litigation\Pipeline\merge_and_classify.py
- Reads Gmail/EML/MSG JSON exports, merges + deduplicates on SHA256 then Message-ID
- EML/MSG wins over Gmail API as forensically authoritative copy
- Classifies strip_method, writes body_clean via strippers.py
- Outputs: combined_repository.json + merge_report.json
- PENDING FIX: input filenames hardcoded — needs to be configurable
- PENDING FIX: output filename hardcoded — needs auto-increment (no overwrite policy)

**strippers.py**
- Path: C:\Users\arika\OneDrive\Litigation\Pipeline\strippers.py
- get_body_clean() called per strip_method type
- Body.SenderText = Aid4Mail extraction; body_clean = our processed version; Body.Text = full thread

**export_all_emails.py**
- Path: C:\Users\arika\OneDrive\Litigation\Pipeline\export_all_emails.py
- Reads combined_repository.json, exports to all_emails (N).xlsx
- Auto-increments — never overwrites. Current active: all_emails (2).xlsx

**validate_attachments.py**
- Path: C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Json attachments\validate_attachments.py
- Validates attachment manifest vs disk, outputs validation_report.xlsx

### Email Pipeline Scripts (status TBD — confirm with user)
[UPDATE AFTER STEP 4]
- C:\Users\arika\OneDrive\Litigation\Pipeline\read_xlsx.py
- C:\Users\arika\OneDrive\Litigation\09-Data Schemas\batch_eob_process.py
- C:\Users\arika\OneDrive\Litigation\09-Data Schemas\batch_invoice_process.py
- C:\Users\arika\OneDrive\Litigation\09-Data Schemas\extract_one_detail_page.py
- C:\Users\arika\OneDrive\Litigation\09-Data Schemas\visualize_eob_fields.py
- C:\Users\arika\OneDrive\Litigation\09-Data Schemas\visualize_invoice_fields.py

### Data Sources

1. Aid4Mail body export
   - Gmail: ...\Aid4 ti json 2dtime\Gmail body master.json
   - EML:   ...\Aid4 ti json 2dtime\EML body master.json
   - MSG:   ...\Aid4 ti json 2dtime\MSG body master.json
   - Merged: C:\Users\arika\OneDrive\Litigation\Pipeline\combined_repository.json
   - Excel:  C:\Users\arika\OneDrive\Litigation\Pipeline\all_emails (2).xlsx [CURRENT]
   - Previous versions kept, never overwrite
   - 1,672 rows. Key fields: Body.Text, Body.SenderText, body_clean, strip_method, Drafts2
   - CloudHQ "Email Text" is known bad — superseded by this pipeline

2. CloudHQ live Google Sheet
   - Browser URL: https://docs.google.com/spreadsheets/d/1cwgPXJZbbIYdRGD-94bst9sd3CejkjBAJk8C6wrAlHY
   - PQ CSV URL: https://docs.google.com/spreadsheets/d/1cwgPXJZbbIYdRGD-94bst9sd3CejkjBAJk8C6wrAlHY/export?format=csv&gid=0
     (Generated via File > Share > Publish to web > CSV — NOT the browser URL)
   - 1,695 rows as of March 18, 2026. Query name: CloudHQ_Live
   - Columns: Thread ID, Message ID, From, From (name), To, Cc, Bcc, Subject,
     Date & Time Sent, Date & Time Received, Labels, RFC 822 Message ID,
     Email in PDF, Attachments Count, Body Snippet, Email Text, Is Real Reply?, Is Auto Reply?

3. Aid4Mail Attachment Manifest
   - File: ...\Aid4 to json with python attachments\Attachment_Manifest_GML_EML_MSG (1).xlsx
   - One row per attachment. Columns: mih, source, message_id, sent_local_nyc, from, to,
     subject, attachment_ordinal, original_filename, saved_filename, file_type,
     saved_full_path, storage_folder, size_bytes, sha256
   - Physical files: ...\Attachment\ and ...\Embedded\

### Primary Working Workbook
C:\Users\arika\OneDrive\Litigation\Pipeline\label_LegalEmailExtracts - Ariks Version V11.xlsx
(Renamed from V10.xlsx on March 18, 2026)

Tabs: LegalEmailExtracts (CloudHQ snapshot), working copy (editable + formula cols),
AllEmailBod (PQ output table AllEmailBod_1, $A$1:$BS$1673), Table6 (superseded, kept),
CloudHQ_Live sheet

PQ queries: WorkingCopyTable, AllEmailBod (parameterized), CloudHQ_Live (live CSV),
ThreeWayAudit, Merge1 (active join), Guns (merge1)

PQ Parameter: Email_Body_Input_File
- Current: C:\Users\arika\OneDrive\Litigation\Pipeline\all_emails (2).xlsx
- Update after new Aid4Mail run. NEVER overwrite prior files.

### Universal Join Key
- CloudHQ: "RFC 822 Message ID"
- AllEmailBod: "Header.Message-ID"
- Attachment Manifest: "message_id"

### Three-Way Audit Query (ThreeWayAudit) — BUILT
- Compares Message IDs across AllEmailBod, WorkingCopyTable, CloudHQ_Live
- Output: Message_ID, In_AllEmailBod, In_WorkingCopy, In_CloudHQ_Live, Has_Gap, Pattern
- Uses full outer join (type 2) — NOT JoinKind.Left (causes errors)
- Results March 18, 2026: 1,695 unique, 1,550 OK, 81 CloudHQ-only (delta), 64 EML-only (expected)

### Planned Output — EmailMaster.xlsx — DESIGNED, NOT YET BUILT
- Tab 1 EmailMaster: one row per email, all cols from WorkingCopyTable + AllEmailBod
- Tab 2 AttachmentDetail: all attachment manifest rows, links via message_id
- Field selection not yet finalized

### Convergence with fileWalker
- sha256 in Attachment Manifest = SHA256 in fileWalker Master_File_Inventory
- OCR output from fw_ocr links back via sha256

### Downstream Chroma / RAG — PLANNED, NOT YET BUILT
- Primary chunk: Body.SenderText; Secondary: Body.Text
- Metadata: RFC 822 Message ID, Header.From, Header.Date, Header.Subject,
  Header.X-Gmail-Labels, Email.HashSHA256
- Hybrid RAG (BM25 + dense vector)

---

## STEP 6 — Update MasterSchema.md open items

WHY: MasterSchema.md has open items now resolved. Close them out so the doc
reflects reality and future sessions aren't confused.

Open: C:\Users\arika\OneDrive\Litigation\09-Data Schemas\MasterSchema.md

Targeted updates only — do not restructure:
1. Master Excel File Strategy: change DISCUSSED to DESIGNED, note EmailMaster.xlsx plan
2. emails_master.jsonl: note Excel EmailMaster.xlsx is near-term, JSONL/Chroma is downstream
3. Open Items: close out "Resolve master Excel file strategy" and "Decide body master.json"
4. Add section "Email Body Pipeline Scripts" with pipeline chain

Show summary of changes before committing.

---

## STEP 7 — Confirm and commit

WHY: Git commit = permanent timestamped record for chain of custody.

Show me:
1. Last 50 lines of updated CLAUDE.md
2. Summary of MasterSchema.md changes

Commit: "docs: add email evidence pipeline to CLAUDE.md and update MasterSchema.md"
Do not push — commit locally only.
