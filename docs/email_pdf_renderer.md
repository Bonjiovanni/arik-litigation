# Email PDF Renderer

## Purpose

Render emails from the combined_repository.json to PDF, as a replacement for
CloudHQ's PDF rendering service. Produces one PDF per email with:
- Full email header (From, To, CC, BCC, Date Sent, Date Received, Subject, Attachments)
- Sender-only body content (reply chain stripped via body_clean)
- Embedded images resolved from the attachment manifest

## Status: PROTOTYPE WORKING (2026-04-13)

Tested on 6+ emails including multi-image Gmail emails with inline screenshots.
Not yet productized into a reusable script. Current working code is in one-off
render scripts in `C:\Users\arika\OneDrive\CLaude Cowork\render_*.py`.

## How It Works

### Pipeline

```
combined_repository.json (has body_clean + Body.HTML)
         ↓
Python script: resolve cid: images → truncate HTML at body_clean → wrap in template
         ↓
Chrome headless --print-to-pdf
         ↓
One PDF per email
```

### Key Techniques

**1. Body truncation via body_clean**

The `body_clean` field (from strippers.py via merge_and_classify.py) contains only
the sender's text with reply chains removed. The renderer finds where body_clean
content ends in the Body.HTML and truncates the HTML at that point. This preserves
HTML formatting and inline images while removing quoted replies.

- If body_clean ≈ Body.Text (within 10 chars): no truncation needed (Original strip_method)
- If body_clean is very short (<20 chars): render as plain text instead of truncating HTML
- Otherwise: find the last ~40 chars of body_clean in the HTML's text content, map that
  position back to the HTML, truncate there

**2. Embedded image resolution**

Two different cid: schemes exist:

- **Outlook (EML/MSG source):** `cid:image001.jpg@01DC02CC.2AFF4A70`
  - Strip `@` suffix → `image001.jpg`
  - Look up `original_filename` in attachment manifest by message_id
  - Get `saved_full_path` → `file:///` URL

- **Gmail source:** `cid:ii_19318682d3cefb32bff1`
  - No filename in the cid — Gmail uses opaque hex identifiers
  - Map by ordinal position against Body.Contents list
  - **IMPORTANT: Gmail ordering quirk** — the LAST file in Body.Contents maps to
    the FIRST cid: reference in the HTML. Remaining files map in forward order.
    Pattern: `[last, first, second, third, ...]`

**3. Word/Outlook margin override**

Outlook-generated HTML includes `@page WordSection1 {margin:1.0in}` which causes
content to push to page 2. The renderer strips these:
- Remove `@page` CSS blocks
- Override `margin: X.Xin` declarations with `margin:0`
- Force `div[class*="WordSection"]` to `margin:0 !important`

**4. Chrome headless PDF generation**

```
chrome.exe --headless --disable-gpu --allow-file-access-from-files
    --print-to-pdf=output.pdf input.html
```

- `--allow-file-access-from-files` required for `file:///` image URLs
- Chrome adds page numbers in footer automatically
- No extra Python libraries needed (no weasyprint/pdfkit)

### Email Header Fields

Rendered in order, only if non-empty:

| Field | Source |
|---|---|
| From | Header.From or Address.Sender |
| To | Header.To or Address.To |
| Cc | Header.Cc or Address.Cc |
| Bcc | Header.Bcc or Address.Bcc |
| Date Sent | Header.Date |
| Date Received | Header.Delivery-Date or Date.Display |
| Subject | Header.Subject |
| Attachments | Attachment.Names (if Attachment.Count > 0) |

Labels are deliberately excluded.

## Input Files

| File | Location | Purpose |
|---|---|---|
| combined_repository.json | `C:\Users\arika\OneDrive\Litigation\Pipeline\` | Email records with body_clean |
| Attachment_Manifest_GML_EML_MSG.csv | `C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 to json with python attachments\` | Maps message_id + original_filename → saved_full_path |
| Embedded/ folder | Same directory as manifest | Actual image files |
| Attachment/ folder | Same directory as manifest | Actual attachment files |

## What's Left to Productize

1. **Batch rendering script** — loop over all emails (or a filtered set), render each to PDF
   with a deterministic filename (e.g., by message_id hash or date+subject)
2. **Gmail cid: mapping** — the last-first-then-forward pattern needs verification across
   more emails. May need a more robust heuristic or fallback to image content matching.
3. **Outlook cid: mapping** — uses manifest lookup by (message_id, original_filename).
   Works for EML/MSG source. Needs the merged manifest to be available.
4. **Bates stamping** — Chrome headless doesn't support CSS @page margin boxes.
   Options: post-process with pymupdf to stamp text on each page, or accept Chrome's
   default footer (date + URL + page number).
5. **Date Received** — currently falls back to Date.Display which may be the same as
   Date Sent for some emails. Need to verify against actual Delivery-Date field.
6. **Error handling** — missing images, missing body_clean, empty HTML, etc.
7. **Integration with V11/pipeline** — add PDF path column to V11 alongside CloudHQ URL

## Sample Renders (in EML_PDF_samples/)

| File | Source | Notes |
|---|---|---|
| main_creditcard_v9.pdf | combined_repository index 739 | 5 Gmail inline images, body_clean stripped, images correct |
| main_830am_v5.pdf | combined_repository index 524 | Outlook strip, 97 chars body_clean from 7107 |
| main_insurance_v5.pdf | combined_repository | Outlook strip, with attachment listed |
| main_fwd_docs_v6.pdf | combined_repository | Outlook cid: image resolved from manifest |

## Dependencies

- Python 3.11 (json, re, html, csv, subprocess, os)
- Google Chrome (for headless PDF generation)
- No additional Python packages required
