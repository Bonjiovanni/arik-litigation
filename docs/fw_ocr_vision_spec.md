# Extraction Workstream Handoff
## For: File Walker / Evidence Pipeline (Claude Code)
## From: Parallel design sessions in Claude.ai chat

---

## Purpose

This document describes extraction schemas, routing logic, and architectural decisions developed in separate Claude.ai sessions **before** the file walker project existed. That work was done in isolation and did not know about the walker's architecture, schema, or naming conventions.

**Your job:** Read this, integrate what's useful, and adjust or override anything here that conflicts with or duplicates what the walker has already established. You are the authority on the overall project architecture. Flag any collisions or questions before writing any code.

---

## 1. PDF Routing Logic

A document-type routing system was designed to direct each PDF to the appropriate extraction tool. These decisions are considered settled but should be reconciled with however the walker currently classifies files.

| Document Type | Detection Method | Extraction Tool | Output |
|---|---|---|---|
| Fillable PDF forms (government, legal, insurance) | PDF has form fields | PDF Tools MCP `read_pdf_fields` | Key-value pairs |
| Native digital PDFs (typed letters, contracts, reports) | High char density, no form fields | pymupdf/fitz | Raw text |
| Scanned PDFs — no OCR yet | Low char density, image-based | Claude Vision API | Structured JSON or prose |
| Scanned PDFs — OCR already applied | Text present but layout-dependent | Evaluate quality; re-process via Adobe if needed | Text |
| Mixed PDFs | Page-by-page variance | Per-page routing | Mixed |
| Complex scanned prose (letters, narrative docs) | Scanned + prose-heavy | Adobe Acrobat Pro OCR | Text |

**Core principle:** Accuracy over speed. This is litigation evidence. Every extracted record must include an `extraction_method` field for provenance.

---

## 2. John Hancock LTC Claim Forms (LTCC-ICPSB)

### What these are
Scanned, handwritten itemized service claim forms submitted by a care provider to John Hancock under a long-term care insurance policy. These are **not** fillable PDFs — they are physical forms filled out by hand and scanned. They are core evidentiary documents.

### Form versions
Three versions exist in the corpus, each with slightly different field layouts:
- `11/22` — oldest version; coordinate schema fully calibrated at v3.7
- `05/24` — blank template available; coordinate schema not yet built
- `09/24` — blank template available (page 2 only); coordinate schema not yet built

### Coordinate schema approach
Because these are scanned handwritten forms, extraction works by:
1. Rendering each PDF page to pixels at known DPI
2. Cropping bounding-box regions per field (coordinates in points, scale by DPI factor)
3. Passing each crop to Claude Vision or OCR per field type

Each field in the schema has:
```json
{
  "region": [x0, y0, x1, y1],
  "field_type": "typed | handwritten | checkbox",
  "label": "human readable name"
}
```

### Page 2 structure (the itemized services page — highest evidentiary value)
- **Header:** policy_number, claim_number, insured_name, provider_name, hourly_charge, page_x_of_y
- **Service table:** 14 rows, each containing:
  - date, time_in, time_out, total_hours, total_daily_charge, other_detail
  - `adl` sub-object: `adl.bathing`, `adl.dressing`, `adl.continence`, `adl.transferring`, `adl.toileting`, `adl.eating` (all checkboxes)
  - Row addressing: `row[N].adl.continence`, `row[N].date`, etc.
- **Footer:** total_charges, other_detail
- **Signatures block:** insured_sig, insured_sig_date, poa_checkbox, guardian_checkbox, other_title_checkbox, other_title_writein, provider_sig, provider_sig_date

### Multiple instances per submission
A single submission PDF may contain **multiple copies** of this form (one per billing period). The output structure must handle this:
```json
{
  "submission_id": "...",
  "form_instances": [
    {
      "instance": 1,
      "page_ref": 2,
      "fields": { "header": {}, "rows": {}, "footer": {}, "signatures": {} }
    },
    { "instance": 2, "page_ref": 6, "fields": { "..." : "..." } }
  ]
}
```

### Online portal summary fields (already extracted separately)
Each submission also has a corresponding JH portal PDF with clean machine-readable data. These have already been extracted. The join key to the handwritten form data is `invoice_id`. Fields:
```
invoice_id, policy_number, claim_number, provider_name, total_charges, hourly_rate,
service_date_from, service_date_to, submitted_by, date_submitted, phone, email,
q1_home_care, q1a_location_if_not_home, q2_other_clients, q2a_who, q2b_jh_customer,
q2c_policy_id, q2d_claim_number, q3_assignment_of_benefits,
q4_proof_of_payment_type, q4a_other_proof_description,
additional_information_text, fraud_attestation_checked,
proof_of_payment_attestation_checked
```

### Anomaly flags (per-page and per-invoice checks)
These were designed as evidentiary integrity checks and should run against extracted data:

| Flag ID | Scope | Description |
|---|---|---|
| `duplicate_sig_dates` | Per page | Insured sig date == Provider sig date (pre-signed blank form) |
| `sig_date_before_service` | Per page | Sig date precedes last service date on page |
| `row1_arrows_only` | Per page | Row 1 filled, rows 2–N blank (ditto arrow pattern) |
| `total_crossout` | Per page | Multiple numeric values in total_charges field |
| `identical_other_detail` | Per invoice | "Other" detail text identical across all pages |
| `page_number_mismatch` | Per invoice | Page X of Y inconsistent with actual page count |

Cross-invoice overlap detection (same service dates billed twice) is outlined but not yet designed.

### Existing files from the design sessions
These may or may not already exist on disk — verify before recreating:
- `ltcc_icpsb_1122_coords_FINAL.json` — coordinate schema v3.7 for 11/22 form version
- `ltcc_extraction_spec.md` — full spec document from the design session
- `extract_1122.py` — extraction stub (needs update for current JSON structure)
- `bbox_ruler.png` — bounding box overlay with 4-sided ruler for calibration

---

## 3. Financial Statement Extraction (EastRise Mortgage Statements)

### What these are
Scanned or native PDF mortgage statements from EastRise Credit Union. These are **high-priority evidence** — they document a pattern of mortgage delinquency on the trust property that is central to the breach of fiduciary duty claim.

### Known account
- Account: 101185
- Property: 6 Lavigne Rd, South Hero VT 05486
- Borrowers: Robert Marks and Barbara B Marks
- Interest Rate: 3.250%
- Regular Payment: $1,388.31/month

### Extraction method
Claude Vision → structured JSON. Do not use pymupdf for these — the tabular layout and the evidentiary importance of specific numbers warrants Vision extraction, not text blob parsing.

### Output schema (one record per statement)
```json
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
```

This schema applies to mortgage/bank statements generally — adjust field presence as needed for other statement types.

---

## 4. Architectural Principles (Established — Do Not Override Without Flagging)

These were decided across multiple sessions and are considered fixed:

1. **Deterministic acquisition** — Aid4Mail extraction is source of truth, never re-run
2. **Immutable canonical records** — JSONL files are not modified after creation
3. **Non-destructive** — original files never modified; OCR output stored separately
4. **Full provenance** — every extracted record traceable to source file and parent email
5. **Extraction method logged** — every record has an `extraction_method` field
6. **Accuracy over speed** — litigation use case; human spot-check queue for filing-critical values
7. **Legally defensible** — SHA256 integrity hashes, chain of custody maintained

---

## 5. What Is NOT Yet Built

Be aware of these gaps — do not assume they exist:
- Extraction scripts for 05/24 and 09/24 LTC form versions (coordinate schemas not calibrated)
- The Vision extraction script for financial statements (schema designed, script not written)
- Cross-invoice overlap detection for LTC forms
- Any non-PDF file handling (Word, images, spreadsheets, audio) — explicitly deferred

---

## 6. Your Instructions

1. Read this document fully before touching anything
2. Cross-reference against what the walker has already built
3. **Surface any collisions** — schema field name conflicts, key mismatches, duplicate logic, or assumptions here that contradict the walker's existing design
4. Propose how to reconcile conflicts rather than silently overriding either side
5. Wait for Arik to resolve any flagged collisions before proceeding with integration

---

## 7. Document Type Taxonomy & Schemas

This section was designed in a separate session focused on OCR and form processing object types. It defines the full document type universe for the evidence pipeline. The walker should treat these as the canonical type definitions and reconcile its own classification labels against them.

### 7.1 Universal Fields (Every Record, Every Type)

Every extracted document record regardless of type must carry:

```json
{
  "doc_id": "",
  "doc_type": "",
  "doc_date": "",
  "file_path": ""
}
```

This is the cross-referencing spine. Nothing gets stored without these four fields.

### 7.2 Document Types — Fully Designed

---

#### `email`
Universal fields plus: thread linking, RFC 822 Message-ID as primary key.
RFC 822 Message-ID is the authoritative join key across all sources (Aid4Mail JSONL, CloudHQ spreadsheet, attachment log).

---

#### `check`
Physical checks — images scanned from bank statements or produced in discovery.

Fields:
```json
{
  "doc_id": "",
  "doc_type": "check",
  "doc_date": "",
  "file_path": "",
  "check_number": "",
  "amount": "",
  "payee": "",
  "memo": "",
  "signed_by": "",
  "poa_flag": false,
  "bank_display": "",
  "bank_actual": "",
  "micr": "",
  "timesheet_refs": []
}
```

Notes:
- `bank_display` vs `bank_actual` — distinguish what's printed on the check face vs the issuing institution actually identified from MICR/routing number
- `poa_flag` — true if signed under power of attorney authority
- `timesheet_refs` — array of doc_ids linking to PCA timesheets covering the same date(s)

---

#### `PCA_timesheet`
Personal care attendant timesheets cross-referenced to checks. Detailed field schema was **intentionally deferred** pending review of actual timesheet documents. The cross-reference to `check.timesheet_refs` is the integration point.

---

### 7.3 Document Types — Stubbed (Schema Not Yet Written)

These types are identified and named but field schemas have not been designed. The walker should recognize them as valid types and flag files that appear to belong to these categories for later schema completion.

| Type | Notes |
|---|---|
| `BILL` | Schema outlined, to be confirmed |
| `invoice` | Same schema as BILL — noted as equivalent |
| `receipt` | Schema to be defined |
| `notice` | Schema to be defined |
| `correspondence` | Schema to be defined |
| `account_statement` | Most complex type — explicitly deferred last |

### 7.4 Entity Schema

Designed in parallel with the document type taxonomy. Universal fields plus type-specific extensions.

**Universal entity fields:**
```json
{
  "entity_id": "",
  "entity_type": "",
  "full_name": "",
  "aliases": [],
  "role": "",
  "addresses": []
}
```

**Type-specific extensions defined for:**
- `person`
- `attorney`
- `financial_institution`
- `insurance_company`

The normalized Excel entity workbook (`EntityIndex_Normalized_v21.xlsx`) implements this as `tblEntities` / `tblAliases` / `tblContacts` / `tblEntityRoles` with `tblMasterIndex` as the rollup view. That workbook is a separate artifact — the pipeline entity schema and the Excel workbook should stay in sync but are managed independently.

### 7.5 What Still Needs To Be Done

- PCA_timesheet field schema (requires review of actual timesheet documents)
- BILL / invoice field schema (confirmation pass needed)
- receipt, notice, correspondence, account_statement schemas (not yet started)
- Reconcile entity type-specific extension fields with the Excel workbook schema

---

## 8. File Inventory — Artifacts From Prior Workstreams

These files already exist on disk. The walker should reference them rather than recreate them.

### OCR / LTC Form Extraction
All in: `C:\Users\arika\OneDrive\Litigation\Litigation Downloads\Claude\OCR outputs\`

| File | Description |
|---|---|
| `ltcc_icpsb_1122_coords_FINAL.json` | Coordinate schema v3.7 for 11/22 form version |
| `ltcc_extraction_spec.md` | Full LTC form extraction spec (13.5 KB) |
| `extract_1122.py` | Extraction script stub — needs update for current JSON structure (17.3 KB) |
| `bbox_final.png` | Bounding box overlay render #1 (1.2 MB) |
| `bbox_final1.png` | Bounding box overlay render #2 (1.2 MB) |

Note: `bbox_ruler.png` referenced in the spec was never generated — `bbox_final.png` and `bbox_final1.png` are the calibration visuals that were actually produced.

### PDF Classification Report
`C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 to json with python attachments\pdf_classification_report.xlsx`

The output of the PDF classification script — one row per attachment file, with Type (Native/Scanned/Mixed), OCR flag, avg chars per page, and notes. 69.5 KB. This is the input that drives all subsequent extraction routing decisions.

### Entity Index Workbook
Most current version: `C:\Users\arika\OneDrive\Copy of EntityIndex_Normalized_v24_fixed.xlsm` (33.3 KB)

Earlier versions also present (v21b, v22_fixed, v23_fixed, v2) — treat v24_fixed as authoritative.

Tables: `tblEntities`, `tblAliases`, `tblContacts`, `tblEntityRoles`, `tblMasterIndex` (sheet: `90_MasterIndex`).
Primary key: `Entity_ID`. See Section 7.4 for schema details.

---

## 9. Entity Workbook — Config Input for Code

The entity workbook is a **live config input** to the pipeline, not just a reference artifact. Code should read from it to resolve entity names, aliases, roles, and contact info rather than hardcoding any of that.

**File:** `C:\Users\arika\OneDrive\Copy of EntityIndex_Normalized_v24_fixed.xlsm`

### Sheets & Tables

| Sheet | Table | Columns | Purpose |
|---|---|---|---|
| `01_Entities` | `tblEntities` | Entity_ID, Canonical_Name, Entity_Type, DOB, DOD, Notes | Source of truth — 53 entities currently |
| `02_Aliases` | `tblAliases` | Alias_ID, Entity_ID, Alias_Value | Name variants for matching |
| `03_Contacts` | `tblContacts` | Contact_ID, Entity_ID, Contact_Type, Contact_Value | Email, phone, address per entity |
| `04_EntityRoles` | `tblEntityRoles` | Role_ID, Entity_ID, Role_Context, Matter, Notes | Who plays what role in which matter |
| `90_MasterIndex` | `tblMasterIndex` | Entity_ID, Canonical_Name, Entity_Type, DOB, DOD, Aliases, Emails, Phone_Main, Phone_Mobile, URLs | Rollup view — one row per entity, all aliases/contacts concatenated |
| `99_Validation` | — | — | Controlled vocabulary lists (Contact_Type values, Entity_Type values, etc.) |
| `Data_Dictionary` | — | — | Field definitions |
| `PQ_Queries` | — | — | Power Query staging sheet |
| `90_MasterIndex_PQ` | — | — | Power Query version of master index |

### Primary Key
`Entity_ID` — text, unique, used as foreign key in all child tables and as the join key from extracted document records back to the entity registry.

### How Code Should Use This
- Read `tblAliases` to build a name→Entity_ID lookup for matching names found in extracted documents
- Read `tblEntities` to resolve Entity_ID → Canonical_Name for output normalization
- Read `tblEntityRoles` to understand which entities are relevant to which matters
- Do not write to this workbook from the pipeline — it is managed separately
