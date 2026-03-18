#!/usr/bin/env python3
"""
Phase 1 probe: extract one scanned detail page from Invoice_1554588 via Claude Vision.
Saves result to outputs/Invoice_1554588_p3_probe.json for review.

API key: place your Anthropic key in C:\\Users\\arika\\.anthropic_key (one line, no quotes).
"""

import os
import sys
import json
import base64
import re
from pathlib import Path

import fitz          # pymupdf
import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
INVOICE_DIR = Path(
    r"C:\Users\arika\OneDrive\Litigation\08_INCOMING"
    r"\John Hancock long term care document dpwnloads on 11-9-2025"
)
OUT_DIR = INVOICE_DIR / "outputs"
OUT_DIR.mkdir(exist_ok=True)

KEY_FILE = Path(r"C:\Users\arika\.anthropic_key")

TARGET_PDF = (
    INVOICE_DIR /
    "Invoice_1554588_Claim_P27958_Policy_10013255_2023-10-02_162103.pdf"
)

# ---------------------------------------------------------------------------
# API key loader
# ---------------------------------------------------------------------------
def get_api_key():
    # 1. Key file
    if KEY_FILE.exists():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    # 2. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    # 3. Give clear instructions and exit
    print("ERROR: Anthropic API key not found.")
    print()
    print("To fix, create this file with your key (one line, no quotes):")
    print(f"  {KEY_FILE}")
    print()
    print("Or set the environment variable before running:")
    print("  set ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Vision extraction prompt
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """
This is a scanned page from a John Hancock Long-Term Care insurance claim.
It contains two sections:

SECTION 3 — Itemized care services:
A table with one row per day of care. Columns are:
  Date (MM/DD/YY or MM/DD/YYYY), Time in, Time out, Total hours, Hourly charge, Total daily charge.
To the right are checkboxes for Activities of Daily Living (ADLs):
  Bathing, Continence, Dressing, Eating, Toileting, Transferring/mobility, Cognitive supervision, Other.
At the bottom: "Total charges: $X" and a free-text "other" services description.

SECTION 4 — Signature and authorization:
Two signature lines with dates: one for the insured (or fiduciary), one for the care provider.
Checkboxes for title: Power of Attorney, Guardian, Other.

Extract ALL data and return ONLY valid JSON in exactly this structure — no commentary, no markdown:

{
  "month_year": "May 2023",
  "service_records": [
    {
      "date": "05/01/2023",
      "time_in": "8 AM",
      "time_out": "8 PM",
      "total_hours": "7+",
      "hourly_charge": 18.00,
      "total_daily_charge": 126.00,
      "adl_bathing": true,
      "adl_continence": true,
      "adl_dressing": true,
      "adl_eating": true,
      "adl_toileting": true,
      "adl_transferring": true,
      "adl_cognitive": true,
      "adl_other": true
    }
  ],
  "page_total_charges": 1764.00,
  "other_services_detail": "MEDICATION, food prep, shopping, drs",
  "sig_insured_date": "06/09/2023",
  "sig_provider_date": "06/09/2023",
  "sig_title_poa": false,
  "sig_title_guardian": false
}

Rules:
- Include only rows that have a date written in them. Skip blank rows.
- For total_hours, use a string (e.g. "7", "7+", "7.5"). Use null if illegible.
- For hourly_charge and total_daily_charge, use a number (no $ sign). Use null if blank/illegible.
- For ADL checkboxes: true if the box is filled/checked, false if empty.
- For dates, normalize to MM/DD/YYYY format.
- If a field is completely illegible, use null.
- Return ONLY the JSON object. No explanation.
""".strip()


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------
def find_first_scanned_page(doc):
    """Return index of first page with < 100 chars of extractable text."""
    for i in range(doc.page_count):
        if len(doc[i].get_text().strip()) < 100:
            return i
    return None


def render_page_to_base64(page, dpi=200):
    """Render a PyMuPDF page to PNG and return base64-encoded bytes."""
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    return base64.standard_b64encode(png_bytes).decode("utf-8")


def extract_via_vision(client, b64_image):
    """Send page image to Claude Vision; return parsed JSON dict."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )
    raw = response.content[0].text.strip()

    # Strip markdown code fences if model wrapped the JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\n=== Invoice Detail Probe — Phase 1 ===\n")

    # API key
    api_key = get_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    print("API key loaded OK")

    # Open PDF
    if not TARGET_PDF.exists():
        print(f"ERROR: PDF not found:\n  {TARGET_PDF}")
        sys.exit(1)

    doc = fitz.open(str(TARGET_PDF))
    print(f"Opened: {TARGET_PDF.name}  ({doc.page_count} pages)")

    # Find first scanned page
    page_idx = find_first_scanned_page(doc)
    if page_idx is None:
        print("ERROR: No scanned pages found — all pages have extractable text.")
        sys.exit(1)
    print(f"First scanned page: index {page_idx} (page {page_idx + 1} of {doc.page_count})")

    # Render to image
    print(f"Rendering page {page_idx + 1} at 200 DPI...")
    b64 = render_page_to_base64(doc[page_idx], dpi=200)
    print(f"  Image size: {len(b64) // 1024} KB (base64)")

    # Call Vision API
    print("Calling Claude Vision API...")
    result = extract_via_vision(client, b64)
    print("  Response received.")

    # Print to console
    print("\n--- Extracted JSON ---")
    print(json.dumps(result, indent=2))

    # Save to outputs/
    out_path = OUT_DIR / "Invoice_1554588_p3_probe.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path}")

    # Summary
    records = result.get("service_records", [])
    total = result.get("page_total_charges")
    print(f"\nSummary: {len(records)} service days extracted, page total = ${total}")

    doc.close()


if __name__ == "__main__":
    main()
