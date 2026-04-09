# SQLite Setup Decisions for Email Sifter Pipeline

Last updated: 2026-04-04

## Installation Status

- **SQLite CLI:** Installed at `C:\Users\arika\AppData\Local\Programs\sqlite\sqlite3.exe` — version 3.51.3
- **Python sqlite3 module:** Built-in to Python 3.11 — version 3.45.1
- **PATH:** Added to user PATH via setx

---

## Source Files

| File | Path | Rows | Columns |
|------|------|------|---------|
| V11.xlsx | `C:\Users\arika\OneDrive\Litigation\Pipeline\label_LegalEmailExtracts - Ariks Version V11.xlsx` | 1,550 | 102 |
| Attachment Manifest | `C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 to json with python attachments\Attachment_Manifest_GML_EML_MSG (1).xlsx` | 2,154 | 17 |

CSV versions of both also exist at the same locations.

---

## Database Design (from MasterSchema.md)

### Database File
- **Decision needed:** Where to store the `.db` file. Options:
  - `C:\Users\arika\OneDrive\Litigation\Pipeline\email_sifter.db` (with the source data)
  - `C:\Users\arika\Repo-for-Claude-android\email_sifter.db` (with the code)
  - A dedicated data directory

### Table 1: `emails_master`

**Source:** V11.xlsx (all 102 columns)

**Key columns:**
| Column | Source Field | Notes |
|--------|-------------|-------|
| `message_id` | `RFC 822 Message ID` | **Primary key** — the join key across all sources |
| `from_addr` | `From` | Email address |
| `from_name` | `From (name)` | Display name |
| `to_addr` | `To` | |
| `to_name` | `To (name)` | |
| `cc` | `Cc` | |
| `bcc` | `Bcc` | |
| `subject` | `Subject` | Indexed via FTS5 |
| `date_sent` | `Date & Time Sent` | |
| `body_clean` | `body_clean.1` | Cleaned email body, quote-stripped. Indexed via FTS5 |

Plus ~92 additional metadata columns imported as-is from V11.

**Decisions needed:**
- Column name normalization — V11 has spaces and special characters in column names (e.g. `Date & Time Sent`, `body_clean.1`). Need to decide on snake_case mapping.
- Data types — SQLite is dynamically typed but we should declare `TEXT`, `INTEGER`, `REAL` for documentation and query clarity.
- NULL handling — some columns in V11 are sparsely populated. Keep as NULL or default to empty string?

### Table 2: `attachments`

**Source:** Attachment_Manifest_GML_EML_MSG (1).xlsx (17 columns)

**Key columns:**
| Column | Source Field | Notes |
|--------|-------------|-------|
| `attachment_id` | (auto-generated) | **Primary key** — INTEGER AUTOINCREMENT |
| `message_id` | `message_id` | **Foreign key** → `emails_master.message_id` |
| `source` | `source` | Gmail/EML/MSG |
| `from_addr` | `from` | Sender |
| `to_addr` | `to` | Recipient |
| `subject` | `subject` | |
| `date_sent` | `sent_local_nyc` | |
| `attachment_ordinal` | `attachment_ordinal` | Sequence within email |
| `original_filename` | `original_filename` | |
| `saved_filename` | `saved_filename` | |
| `file_type` | `file_type` | Extension/MIME |
| `saved_full_path` | `saved_full_path` | Disk location of physical file |
| `storage_folder` | `storage_folder` | attachment/ or embedded/ |
| `size_bytes` | `size_bytes` | |
| `sha256` | `sha256` | Content hash for dedup |

**Decisions needed:**
- Foreign key enforcement — SQLite has FK support but it's off by default. Run `PRAGMA foreign_keys = ON;` at connection time.
- The manifest has some parent email fields (from, to, subject, date) that duplicate `emails_master`. Keep them for denormalized querying, or drop them and always join?

---

## FTS5 Full-Text Search Index

**Decision already made:** FTS5 virtual table on `subject` + `body_clean` for keyword/literal search.

**Setup needed:**
```sql
CREATE VIRTUAL TABLE emails_fts USING fts5(
    subject,
    body_clean,
    content='emails_master',
    content_rowid='rowid'
);
```

**Decisions needed:**
- Tokenizer — default `unicode61` handles most cases. Consider `porter` for stemming (e.g. searching "filed" also matches "filing"). Stemming adds fuzziness which may not be wanted for litigation precision.
- Should attachment filenames also be FTS-indexed? Would allow searching for "W-9" or "HIPAA" across attachment names.

---

## Import Process

**Decision already made:** Python script (`sifter_sqlite.py`) reads the Excel/CSV files and loads them into SQLite.

**Decisions needed:**
- Read from Excel (.xlsx) or CSV (.csv)? CSV is simpler and avoids openpyxl. The CSV versions exist for both files.
- Batch insert size — 1,550 emails and 2,154 attachments are small enough to load in a single transaction.
- Encoding — CSV files may have UTF-8 or cp1252 encoding. Need to verify.
- Rebuild strategy — on re-import, drop and recreate tables, or upsert by message_id?

---

## Indexing

Beyond FTS5, standard B-tree indexes needed for query performance:

```sql
CREATE INDEX idx_emails_date ON emails_master(date_sent);
CREATE INDEX idx_emails_from ON emails_master(from_addr);
CREATE INDEX idx_attachments_message_id ON attachments(message_id);
CREATE INDEX idx_attachments_file_type ON attachments(file_type);
CREATE INDEX idx_attachments_sha256 ON attachments(sha256);
```

**Decision needed:** Any additional indexes based on expected query patterns?

---

## Decisions — ALL DECIDED (2026-04-08)

1. **Database file:** `C:\Users\arika\OneDrive\Litigation\Pipeline\litigation_corpus.db` (renamed from email_sifter.db — single DB for all evidence types)
2. **Column names:** snake_case via automated mapping in `corpus_sqlite_schema.py`. Original names preserved in `_column_map` table.
3. **Data types:** Mapped from source data — INTEGER for counts/sizes/pages/ordinals; TEXT for everything else including dates.
4. **NULLs:** Preserved (not converted to empty string)
5. **Foreign keys:** ON (`PRAGMA foreign_keys = ON`). 187 orphan attachments loaded with FK temporarily disabled, flagged as `pending_orphan`.
6. **Denormalized attachment fields:** Keep — from, to, subject, date stay in attachments table for standalone queries.
7. **FTS5 tokenizer:** `unicode61` (exact matching, no stemming)
8. **FTS5 scope:** `subject` + `body_clean` from emails; `original_filename` + `extracted_text` from attachments. Full attachment text extraction is future work.
9. **Import source:** Excel via openpyxl read-only (not CSV). File paths + sheet name are CLI args, not hardcoded.
10. **Rebuild strategy:** Drop and recreate per domain. Email rebuild never touches entity tables or future domain tables.

## Additional Design Decisions (2026-04-08)

- **Source sheet:** Merge1 in V11.xlsx (1,550 rows x 103 cols)
- **Database scope:** Single DB (`litigation_corpus.db`) for all evidence: emails, texts, files, etc. Emails are first domain loaded.
- **Entity tables:** `entity_master` + `entity_candidates` (from fileWalker spec) included as shared tables across all domains.
- **Domain isolation:** Each domain's tables can be rebuilt independently. Entity tables are NEVER dropped by a domain rebuild.
- **Attachment overlap warning:** V11 has attachment summary columns (stale blobs). Real attachment data lives in the `attachments` table from the manifest.
- **Extraction tracking:** `extraction_status` column on attachments (`pending`, `pending_orphan`, `extracted`, `skipped`, `error`) + `extraction_log` table for detailed tracking.
- **Orphan attachments:** 187 attachments whose message_id is not in V11/Merge1. Loaded with `extraction_status='pending_orphan'`. Will resolve when email corpus expands.

## Build Status

- **Schema script:** `C:\Users\arika\Repo-for-Claude-android\corpus_sqlite_schema.py` — COMPLETE
- **Loader script:** `C:\Users\arika\Repo-for-Claude-android\corpus_sqlite_loader.py` — COMPLETE
- **Tests:** `C:\Users\arika\Repo-for-Claude-android\tests\test_corpus_sqlite.py` — 52 passing
- **Database:** `C:\Users\arika\OneDrive\Litigation\Pipeline\litigation_corpus.db` — LOADED
  - emails_master: 1,550 rows
  - attachments: 2,154 rows (187 orphans)
  - emails_fts: 1,550 entries
  - attachments_fts: 2,154 entries
  - _column_map: 120 mappings
  - entity_master: 0 (empty, ready)
  - entity_candidates: 0 (empty, ready)

## Next Steps

- **Extractor script** (`corpus_sqlite_extractor.py`) — reads attachment files, extracts text, updates `extracted_text` + `extraction_log`. Incremental by file type.
- **Docling integration** — for non-PDF extraction (Word, Excel, images, scanned PDFs). Not installed yet.
- **Gemini context cache** — load email bodies + extracted attachment text into Google AI Pro cache for semantic search.
