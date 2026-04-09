# doc_data_extraction_spec.md
## Document Data Extraction & Storage Specification
### Marks Family Trust Litigation — Evidence Database

Last updated: 2026-02-24  
Purpose: Defines storage schemas and extraction instructions for all document types in the litigation evidence pipeline. (Originally targeted ChromaDB; now stored in SQLite `litigation_corpus.db` with Gemini context cache for search.)  
Location: Save to `C:\Users\arika\litigation\schema\doc_data_extraction_spec.md`

---

## UNIVERSAL FIELDS
These fields are required on every document regardless of type. They enable cross-collection querying and linking.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `doc_id` | string | Unique identifier across all collections. Format: `{doc_type}_{identifier}_{YYYYMMDD}` | `check_1102_20240510` |
| `doc_type` | string | Document category | `check` \| `PCA_timesheet` \| `email` |
| `event_date` | string | Normalized date in YYYY-MM-DD format | `2024-05-10` |
| `file_path` | string | Full path to source file on disk | `C:\Users\arika\litigation\checks\check_1102.jpg` |

---

## DOCUMENT TYPE: CHECK

### Storage Schema

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `doc_id` | string | Format: `check_{check_number}_{YYYYMMDD}` | `check_1102_20240510` |
| `doc_type` | string | Always `"check"` | `check` |
| `event_date` | string | Normalized check date | `2024-05-10` |
| `file_path` | string | Path to check image | |
| `account_holder` | string | Name(s) printed on check | `Robert Marks / Barbara B Marks` |
| `address` | string | Address printed on check | `6 Lavigne Rd, South Hero, VT 05486` |
| `phone` | string | Phone printed on check | `802-372-9360` |
| `account_name` | string | Institution name (not branding) | `Fidelity` |
| `check_number` | string | Check number | `1102` |
| `date` | string | Date as written on check (raw) | `5/10/24` |
| `payee` | string | Pay to the order of | `Community Bank` |
| `amount` | float | Dollar amount as number (for range queries) | `5820.00` |
| `amount_written` | string | Written dollar amount | `fifty-eight hundred twenty and 00/100` |
| `memo` | string | Memo/For field | `PCA's` |
| `signed_by` | list | All signatories | `["Robert Marks", "Jeanne Lavigne"]` |
| `poa_flag` | boolean | True if any signer signed as POA | `true` |
| `poa_signer` | string | Name of POA signer if applicable | `Jeanne Lavigne` |
| `bank_display` | string | Bank name as printed on check | `UMB Bank, N.A., Kansas City, MO` |
| `bank_actual` | string | True institution identified by logo or branding | `Fidelity` |
| `routing_code` | string | Routing number from MICR line | `101205681` |
| `account_number` | string | Account number from MICR line | `77107670416 87` |
| `timesheet_refs` | list | doc_ids of linked PCA_timesheet records | `[]` |
| `notes` | string | Free text for anything not captured above | `""` |

---

### Extraction Instructions (for Claude Code processing check images)

When presented with a check image, extract the following fields using these rules:

1. **account_holder** — Read the name(s) printed in the upper left of the check.

2. **address / phone** — Read from upper left block beneath account holder name.

3. **account_name** — Look for institutional branding (logo, wordmark). Use the institution name, not their product branding. Example: if you see a Fidelity logo, record `"Fidelity"` not `"Fidelity Account®"`.

4. **check_number** — Printed in upper right corner.

5. **date** — Record exactly as written on the check in the `date` field. Also normalize to YYYY-MM-DD for `event_date`.

6. **payee** — "Pay to the Order of" line.

7. **amount** — Record numeric value in `amount` field (float). Record the written-out dollar amount in `amount_written`.

8. **memo** — The "For" or "Memo" line. Read carefully — handwriting may be difficult. Use context clues (e.g. "PCA's" refers to Personal Care Attendants).

9. **signed_by** — List all signatures. Include all signatories even if one signed on behalf of another.

10. **poa_flag / poa_signer** — If any signature includes "P.O.A.", "POA", or "Power of Attorney" notation, set `poa_flag: true` and record that signer's name in `poa_signer`.

11. **bank_display** — Read the bank name exactly as printed (often in small text near the bottom or on the check face).

12. **bank_actual** — Look for any logos or visual branding that identifies the true institution. If the printed bank differs from the logo (e.g. UMB Bank printed but Fidelity logo visible), record both separately. If they match, both fields will be the same value.

13. **MICR line** — The machine-readable line at the bottom of the check contains routing and account numbers encoded in special font. Split into:
    - `routing_code` — the bank routing number
    - `account_number` — the account number
    Note: MICR lines also contain the check number which should match `check_number` above.

14. **timesheet_refs** — Leave as empty list `[]` at extraction time. Populated later when payment linkage is established.

15. **notes** — Use for anything ambiguous, illegible, or that doesn't fit the schema. Flag handwriting misreads here.

---

## DOCUMENT TYPE: PCA_TIMESHEET

*Schema to be defined. Pending review of timesheet documents.*

---

## DOCUMENT TYPE: EMAIL

*Schema to be defined. Based on CloudHQ export fields.*

---

## DOCUMENT TYPE: EOB (Explanation of Benefits)

Last updated: 2026-03-02
Source directory (JH): `C:\Users\arika\OneDrive\Litigation\08_INCOMING\John Hancock long term care document dpwnloads on 11-9-2025\`
File pattern: `YYYY-MM-DD-EOB*.pdf`
Extraction method: pymupdf (native digital PDF, 1 page, consistent structure)
Validated against: 10 JH EOB files spanning 2022-10-24 through 2024-10-02
Note: `doc_type = "EOB"` is carrier-agnostic. `issuing_entity` field identifies the carrier (e.g. John Hancock). If EOBs from other carriers are added, they use the same schema and collection.

### Storage Schema

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `doc_id` | string | Format: `EOB_{transaction_seq_clean}` — unique per transaction | `EOB_759641A` |
| `doc_type` | string | Always `"EOB"` | `EOB` |
| `event_date` | string | payment_date normalized YYYY-MM-DD | `2022-10-21` |
| `file_path` | string | Full path to source PDF | |
| `issuing_entity` | string | Full legal name of issuing company as printed at top of document | `John Hancock Life Insurance Company (U.S.A.)` |
| `page_number` | integer | Current page number from footer | `1` |
| `page_total` | integer | Total pages in document from footer | `1` |
| `claim_id` | string | JH claim identifier | `P27958` |
| `group_nbr` | string | Group policy number | `108` |
| `transaction_seq` | string | Transaction sequence number as printed | `759641/A` |
| `insured_name` | string | Name of insured | `Robert Marks` |
| `insured_address` | string | Insured mailing address | `6 Lavigne Road, South Hero, VT 05486` |
| `payment_date` | string | Date as printed on EOB | `10/21/2022` |
| `payment_amount` | float | Dollar amount of payment issued | `7015.00` |
| `payment_recipient_name` | string | Name payment is made to | `Robert Marks` |
| `payment_recipient_address` | string | Address payment is sent to | `6 Lavigne Road, South Hero, VT 05486` |
| `provider` | string | Care provider name as printed | `Lavigne, J` |
| `service_type` | string | Type of care service | `Home Health Aide Care` |
| `service_date_from` | string | Start of service period YYYY-MM-DD | `2022-08-01` |
| `service_date_to` | string | End of service period YYYY-MM-DD | `2022-09-30` |
| `total_charge` | float | Total amount billed by provider | `7686.00` |
| `exceeds_plan_max` | float | Amount exceeding plan maximums (not paid) | `671.00` |
| `benefit_paid` | float | Actual benefit paid (= payment_amount) | `7015.00` |
| `lifetime_used` | float | Cumulative lifetime benefits used to date | `92805.00` |
| `lifetime_maximum` | float | Total lifetime maximum on policy | `420000.00` |
| `special_notices` | string | Any additional notices printed on EOB | `"Proof of payment submitted with this invoice is missing."` |
| `duplicate_flag` | boolean | True if transaction_seq matches another file | `false` |
| `notes` | string | Free text for anomalies or observations | `""` |

### Extraction Instructions

When extracting an EOB, locate fields as follows:

1. **issuing_entity** — Bold centered header at the very top of the document. Capture the full legal name exactly as printed, including any parenthetical suffix (e.g. `"John Hancock Life Insurance Company (U.S.A.)"`).

2. **claim_id / group_nbr** — Header row of the main table, left side.

3. **transaction_seq** — Below the payment block, right-aligned. Format is numeric/A (e.g. `759641/A`). Use as-is for the field; strip the slash for `doc_id`.

4. **payment_date / payment_amount** — Right side of header block.

5. **payment_recipient** — Bold block below "Payment is being made to:" on the right side. May differ from insured address (note if different).

6. **insured_name / insured_address** — Left side block labeled "Insured:".

7. **provider / service_type / service dates** — Line item row in the service table. Provider is last-name-first (e.g. "Lavigne, J").

8. **total_charge / exceeds_plan_max / benefit_paid** — Right side of service table. Verify: `total_charge - exceeds_plan_max = benefit_paid`.

9. **lifetime_used / lifetime_maximum** — Sentence at bottom of page: "You have used $X of your $Y lifetime maximum."

10. **special_notices** — Any text appearing between the service table and the footer fraud notice. Capture verbatim. Leave empty string if none.

11. **duplicate_flag** — Set true if the same `transaction_seq` appears in more than one file in this directory. Known duplicate: `836317/A` appears in both `2024-10-01-EOB letter.pdf` and `2024-10-02-EOB.pdf`.

### Data Notes

- The `exceeds_plan_max` amount grew significantly over time (from ~$671 in 2022 to ~$2,340 by 2024), indicating Lavigne's billed rates exceeded the plan monthly cap by an increasing margin.
- Service periods are not always calendar months — some span partial months or multiple months in a single EOB.
- `payment_recipient` always matches `insured` in this claim but the field is preserved separately in case it ever differs.

---

## CROSS-REFERENCE CONVENTIONS

| Link | How stored |
|------|-----------|
| Check → PCA_timesheet | `timesheet_refs` on check record lists PCA_timesheet `doc_id` values |
| PCA_timesheet → Check | `check_refs` on timesheet record lists check `doc_id` values |
| JH_EOB → JH_Invoice | `invoice_refs` on EOB lists Invoice `doc_id` values for the same service period |
| Linkage is provided explicitly by user | Do not infer linkage — user specifies which records link |

---

## COLLECTION NAMES — SHELVED (was ChromaDB)

> ChromaDB approach shelved in favor of SQLite + Gemini context cache.
> These collection names preserved for reference if vector DB is revisited.

| Collection | doc_type |
|------------|----------|
| `checks` | `check` |
| `pca_timesheets` | `PCA_timesheet` |
| `emails` | `email` |
| `eobs` | `EOB` |

---

## DOCUMENT TYPE: CLAIMS_CORRESPONDENCE

Last updated: 2026-03-02
Source directory (JH): `C:\Users\arika\OneDrive\Litigation\08_INCOMING\John Hancock long term care document dpwnloads on 11-9-2025\`
File pattern: `YYYY-MM-DD-Claims Correspondence*.pdf`
Extraction method: pymupdf (native, 2023–2024 files) | claude_vision_ocr (scanned, 2021–2022 files)
Validated against: 4 native PDFs (2023-11-04, 2024-02-21, 2024-07-02, 2024-09-23)
Note: 5 earlier files (2021-11-22, 2022-01-06 ×4) are scanned images — require ANTHROPIC_API_KEY for OCR extraction.

### Storage Schema

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `doc_id` | string | Format: `CC_{letter_id_clean}_{YYYYMMDD}` | `CC_EE1195670_20231103` |
| `doc_type` | string | Always `"claims_correspondence"` | `claims_correspondence` |
| `event_date` | string | Letter date normalized YYYY-MM-DD | `2023-11-03` |
| `file_path` | string | Full path to source PDF | |
| `letter_id` | string | JH internal letter reference printed at top of letter | `EE-1195-670` |
| `letter_date_raw` | string | Date as printed on letter | `November 03, 2023` |
| `policy_id` | string | LTC policy number from RE line | `10013255` |
| `group_name` | string | Group plan name from RE line | `International Business Machines Group Long-Term Care Insurance` |
| `insured_name` | string | Name of insured as printed in address block | `Robert Marks` |
| `insured_address` | string | Insured mailing address | `6 Lavigne Road, South Hero, VT 05486-4227` |
| `signatory_name` | string | Name of signer | `Peter Burke` |
| `signatory_title` | string | Title of signer | `Assistant Vice President, LTC Claims Operations` |
| `issuing_entity` | string | JH legal entity name as printed in signature block | `John Hancock Life Insurance Company (U.S.A)` |
| `body_text` | string | Full verbatim body of the letter (between salutation and signature) | |
| `letter_category` | string | Primary topic classification (see categories below) | `icp_billing_deficiency` |
| `referenced_provider` | string | Care provider name mentioned in body, if any | `Jeanne Lavigne` |
| `referenced_dates_of_service` | string | Date range of service bill referenced in body, if any | `1/21-28/2024` |
| `missing_items` | list | Items JH states are missing or incomplete | `["ICP service bill cover page", "proof of payment"]` |
| `action_required` | string | Brief summary of what insured must do | `Resubmit ICP service bill with complete cover page` |
| `page_count` | integer | Total pages in document | `1` |
| `extraction_method` | string | How text was obtained | `pymupdf_text` \| `claude_vision_ocr` |
| `notes` | string | Free text for anomalies or observations | `""` |

### Letter Category Values

| Value | Meaning |
|-------|---------|
| `icp_billing_deficiency` | ICP (Independent Care Provider) service bill is incomplete or missing required fields |
| `provider_approval_with_billing_issue` | Provider approved as eligible ICP, but claim blocked pending correct documentation |
| `provider_eligibility_pending` | Letter concerns provider eligibility determination (awaiting or requesting info) |
| `general_inquiry` | General status update or informational correspondence |
| `unknown` | Could not classify from body text |

### Extraction Instructions

When extracting a Claims Correspondence letter:

1. **letter_id** — First line of text on the page, before the addressee block. Format `XX-NNNN-NNN` (e.g. `EE-1195-670`). Present on native PDFs; may appear as a printed code on scanned letters.

2. **letter_date_raw / event_date** — Date line appears after the address block, before the RE line. Capture verbatim for `letter_date_raw`; normalize to YYYY-MM-DD for `event_date`.

3. **policy_id** — Extract numeric ID from RE line: `LTC ID #XXXXXXXX`.

4. **group_name** — Text in RE line before `LTC ID`. Typically `International Business Machines Group Long-Term Care Insurance`.

5. **insured_name / insured_address** — Address block at top of letter. Name is all-caps; address follows on subsequent lines.

6. **body_text** — All text between the salutation (e.g. `ROBERT MARKS:`) and the `Sincerely,` line. Capture verbatim including all sentences.

7. **letter_category** — Classify from body keywords:
   - Contains `"ICP service bill"` or `"Independent Care Service Bill"` + `"missing"` → `icp_billing_deficiency`
   - Contains `"currently approved as an eligible independent care provider"` + billing issue → `provider_approval_with_billing_issue`
   - Other provider eligibility language → `provider_eligibility_pending`
   - Default → `unknown`

8. **referenced_provider** — Look for a person's name in the body text in context of care provision (e.g. `"Jeanne Lavigne is currently approved"`). Null if no specific provider named.

9. **referenced_dates_of_service** — Look for a date range pattern like `M/DD-DD/YYYY` or `M/DD-M/DD/YY` in the body. These refer to the ICP service bill period being discussed. Capture the full date range string as printed.

10. **missing_items** — Parse the body for items described as missing or required. Common phrases: `"missing"`, `"we require"`, `"we request"`. Build a list of short descriptive strings.

11. **action_required** — One-sentence summary of what the insured must do (based on body content).

12. **signatory_name / signatory_title** — Lines immediately after `Sincerely,`.

### Data Notes

- All 4 native letters are signed by Peter Burke, AVP LTC Claims Operations.
- The 2024 letters (Feb, Jul, Sept) are nearly identical in structure — boilerplate with the specific date range and missing item varying.
- `referenced_dates_of_service` values seen: `1/21-28/2024` (Feb 2024 letter), `1/21-31/24` (Jul 2024 letter), `6/1-8/31/2024` (Sept 2024 letter). These are the ICP service bill periods for which reimbursement was delayed.
- The 2023-11-04 letter is distinct — it names Jeanne Lavigne as the provider and references the Independent Care Service Bill by its full name (not abbreviation ICP).
- Scanned files (2021-11-22, 2022-01-06 ×4): letter structure may differ; content unknown until OCR is run. The 2022-01-06 batch has 3 lettered variants (Letter 1, 2, 3) plus an unlabeled one — likely sub-letters similar to Provider Eligibility Determination packets.

---

*End of current spec. JH document types being added in 2026-03-02 session.*
