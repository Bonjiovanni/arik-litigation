#!/usr/bin/env python3
"""
JH Invoice Field Visualizer (page 1 — digital cover sheet only)
Left panel:  Annotated PDF image with numbered, color-coded field boxes.
Right panel: Interactive table — editable values, validation toggle, notes, export JSON.

Pages 2+ are scanned/handwritten timesheets — not auto-extracted.
page_count field records total pages so the timesheet presence is noted.

Usage: python visualize_invoice_fields.py [path_to_invoice.pdf]
Output: <name>_review.html  — opens in Edge
"""

import fitz  # pymupdf
import sys
import subprocess
import base64
import json
import re
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Color palette (same keys as EOB visualizer for consistency)
# ---------------------------------------------------------------------------
COLORS = {
    "entity":    ((  0,   0,   0), (0.00, 0.00, 0.00)),  # black   — invoice number, dates from filename
    "id":        ((220,  30,  30), (0.86, 0.12, 0.12)),  # red     — policy/claim numbers
    "payment":   (( 20, 100, 210), (0.08, 0.39, 0.82)),  # blue    — submission date
    "recipient": ((155,  30, 185), (0.61, 0.12, 0.73)),  # purple  — submitted by, phone, email
    "insured":   (( 20, 155,  50), (0.08, 0.61, 0.20)),  # green   — care questions
    "service":   ((195, 115,  10), (0.76, 0.45, 0.04)),  # orange  — provider, service dates
    "amounts":   (( 90,  20, 175), (0.35, 0.08, 0.69)),  # violet  — charges, hourly rate
    "lifetime":  (( 20, 135, 135), (0.08, 0.53, 0.53)),  # teal    — additional info
}

# ---------------------------------------------------------------------------
# FIELD_PATTERNS — page 1 only.
# Label and value are SEPARATE spans at the same y (confirmed from span dump).
# capture_inline_value=True boxes the value span to the right of the label.
# issuing_entity is boxed via image-block detection in annotate_page(), not here.
# ---------------------------------------------------------------------------
FIELD_PATTERNS = [
    ("Policy Number:",         "policy_number",          "id",        True,  "1"),
    ("Claim Number:",          "claim_number",           "id",        True,  "2"),
    ("Provider:",              "provider_name",          "service",   True,  "3"),
    ("Total Charges:",         "total_charges",          "amounts",   True,  "4"),
    ("Hourly Rate:",           "hourly_rate",            "amounts",   True,  "5"),
    ("Service Date From",      "service_date_from",      "service",   True,  "6"),
    ("Service Date To",        "service_date_to",        "service",   True,  "7"),
    ("Submitted By:",          "submitted_by",           "recipient", True,  "8"),
    ("Date Submitted:",        "date_submitted",         "payment",   True,  "9"),
    ("Phone Number:",          "provider_phone",         "recipient", True,  "10"),
    ("Email Address:",         "provider_email",         "recipient", True,  "11"),
    ("Q1:",                    "care_at_home",           "insured",   False, "12"),
    ("Q1a.",                   "q1a_response",           "insured",   False, "12a"),
    # Q2/Q4 groups present on 2023+ forms (page 1); absent on 2022 form
    ("Q2.",                    "shared_care",            "insured",   False, "17"),
    ("Q2a.",                   "q2a_who_else",           "insured",   False, "17a"),
    ("Q2b.",                   "q2b_jh_customer",        "insured",   False, "17b"),
    ("Q2c.",                   "q2c_other_policy",       "id",        False, "17c"),
    ("Q2d.",                   "q2d_other_claim",        "id",        False, "17d"),
    ("Q3.",                    "assignment_of_benefits", "insured",   False, "13"),
    ("Q4.",                    "proof_of_payment_type",  "payment",   False, "18"),
    ("Q4a.",                   "q4a_payment_desc",       "payment",   False, "18a"),
    # Additional Info + Attestation: page 1 on 2022 form, page 2 on 2023+ forms
    ("Additional Information", "additional_info",        "lifetime",  False, "14"),
    ("Fraud Attestation:",     "fraud_attestation",      "entity",    False, "15"),
    ("I attest to the",        "fraud_attestation_text", "entity",    False, "16"),
]

# ---------------------------------------------------------------------------
# Field display order for the right panel
# (includes doc_date and page_count extracted from filename/metadata, not page text)
# ---------------------------------------------------------------------------
FIELD_ORDER = [
    # (schema_key,               display_label,                  box_num, color_key)
    ("doc_type",                 "doc_type",                     "—",  "entity"),
    ("doc_subtype",              "doc_subtype",                  "—",  "entity"),
    ("issuing_entity",           "issuing_entity",               "0",  "entity"),
    ("invoice_number",           "invoice_number",               "—",  "entity"),
    ("doc_date",                 "doc_date",                     "—",  "entity"),
    ("page_count",               "page_count",                   "—",  "entity"),
    ("policy_number",            "policy_number",           "1",  "id"),
    ("claim_number",             "claim_number",            "2",  "id"),
    ("provider_name",            "provider_name",           "3",  "service"),
    ("total_charges",            "total_charges",           "4",  "amounts"),
    ("hourly_rate",              "hourly_rate",             "5",  "amounts"),
    ("service_date_from",        "service_date_from",       "6",  "service"),
    ("service_date_to",          "service_date_to",         "7",  "service"),
    ("submitted_by",             "submitted_by",            "8",  "recipient"),
    ("date_submitted",           "date_submitted",          "9",  "payment"),
    ("provider_phone",           "provider_phone",          "10", "recipient"),
    ("provider_email",           "provider_email",          "11", "recipient"),
    ("care_at_home",             "care_at_home",            "12",  "insured"),
    ("q1a_response",             "q1a: if not, where/when", "12a", "insured"),
    ("shared_care",              "Q2: shared care?",        "17",  "insured"),
    ("q2a_who_else",             "Q2a: who else?",          "17a", "insured"),
    ("q2b_jh_customer",          "Q2b: JH customer?",       "17b", "insured"),
    ("q2c_other_policy",         "Q2c: other policy#",      "17c", "id"),
    ("q2d_other_claim",          "Q2d: other claim#",       "17d", "id"),
    ("assignment_of_benefits",   "assignment_of_benefits",  "13",  "insured"),
    ("proof_of_payment_type",    "Q4: proof of payment",    "18",  "payment"),
    ("q4a_payment_desc",         "Q4a: payment desc.",      "18a", "payment"),
    ("additional_info",          "additional_info",         "14",  "lifetime"),
    ("fraud_attestation_checked","fraud_attestation_checked","15", "entity"),
    ("fraud_attestation_text",   "fraud_attestation_text",  "16",  "entity"),
    ("proof_payment_attested",   "proof_pmt_attested",      "19",  "entity"),
    ("proof_payment_attest_text","proof_pmt_attest_text",   "19a", "entity"),
]

# Fields absent on older (2022) form version — "Question not asked" instead of "not extracted"
FIELD_PLACEHOLDER = {
    "assignment_of_benefits":  "Question not asked",
    "shared_care":             "Question not asked",
    "q2a_who_else":            "Question not asked",
    "q2b_jh_customer":         "Question not asked",
    "q2c_other_policy":        "Question not asked",
    "q2d_other_claim":         "Question not asked",
    "proof_of_payment_type":   "Question not asked",
    "q4a_payment_desc":        "Question not asked",
    "proof_payment_attested":  "Question not asked",
    "proof_payment_attest_text": "Question not asked",
}

COLOR_LEGEND = [
    ("entity",    "0/15/16 issuing_entity (logo), fraud attestation checked+text; — invoice_number/doc_date/page_count"),
    ("id",        "1–2   Policy number, Claim number"),
    ("service",   "3,6,7 Provider name, Service dates"),
    ("amounts",   "4–5   Total charges, Hourly rate"),
    ("recipient", "8,10,11 Submitted by, Phone, Email"),
    ("payment",   "9     Date submitted"),
    ("insured",   "12/12a/13 Care at home, Q1a, Assignment of benefits"),
    ("lifetime",  "14    Additional information"),
]


# ---------------------------------------------------------------------------
# PDF text helpers (same as EOB visualizer)
# ---------------------------------------------------------------------------
def get_spans(page):
    result = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                t = span["text"].strip()
                if t:
                    result.append((fitz.Rect(span["bbox"]), t))
    return result


# ---------------------------------------------------------------------------
# Field value extraction — page 1 text only
# pdf_path passed to extract invoice_number, doc_date from filename
# page_count passed separately from doc metadata
# ---------------------------------------------------------------------------
def extract_field_values(page, pdf_path=None, page_count=None, doc=None):
    ft = page.get_text()
    v = {}

    # --- Page 2 text (2023+ forms split cover sheet across 2 digital pages) ---
    # Page 2 holds: Additional Info, Fraud Attestation, I-XXXXX
    ft2 = ""
    if doc is not None and doc.page_count > 1:
        p2_text = doc[1].get_text()
        if len(p2_text.strip()) > 100:   # digital page, not scanned
            ft2 = p2_text

    # --- From filename ---
    if pdf_path:
        m = re.search(r"Invoice_(\d+)_", pdf_path.name)
        if m:
            v["invoice_number"] = m.group(1)

        m = re.search(r"_(\d{4}-\d{2}-\d{2})_", pdf_path.name)
        if m:
            v["doc_date"] = m.group(1)

    # --- From PDF metadata ---
    if page_count is not None:
        v["page_count"] = str(page_count)

    # --- Document type constants ---
    v["doc_type"]    = "Claim_Invoice"
    v["doc_subtype"] = "Invoice_Cover_Sheet"

    # --- Issuing entity — logo is image-only; hardcoded for all JH invoices ---
    v["issuing_entity"] = "John Hancock Life Insurance Company (U.S.A.)"

    # --- Invoice number from page text as "I-XXXXX" ---
    # 2022 form: on page 1.  2023+ forms: on page 2.
    for text_block in (ft, ft2):
        m = re.search(r"\bI-(\d+)\b", text_block)
        if m and "invoice_number" not in v:
            v["invoice_number"] = m.group(1)
            break

    # --- Policy / Claim ---
    m = re.search(r"Policy Number:\s*(\S+)", ft)
    v["policy_number"] = m.group(1).strip() if m else None

    m = re.search(r"Claim Number:\s*(\S+)", ft)
    v["claim_number"] = m.group(1).strip() if m else None

    # --- Provider ---
    m = re.search(r"Provider:\s*(.+?)(?:\s{2,}|$|\n)", ft)
    v["provider_name"] = m.group(1).strip() if m else None

    # --- Amounts ---
    m = re.search(r"Total Charges:\s*\$?([\d,]+\.?\d*)", ft)
    v["total_charges"] = "$" + m.group(1).strip() if m else None

    m = re.search(r"Hourly Rate:\s*\$?([\d,]+\.?\d*)", ft)
    v["hourly_rate"] = "$" + m.group(1).strip() if m else None

    # --- Service dates ---
    m = re.search(r"Service Date From[:\s]*([\d/]+)", ft)
    v["service_date_from"] = m.group(1).strip() if m else None

    m = re.search(r"Service Date To[:\s]*([\d/]+)", ft)
    v["service_date_to"] = m.group(1).strip() if m else None

    # --- Submitter ---
    m = re.search(r"Submitted By:\s*(.+?)(?:\n|Date Submitted)", ft)
    v["submitted_by"] = m.group(1).strip() if m else None

    m = re.search(r"Date Submitted:\s*([\d/]+)", ft)
    v["date_submitted"] = m.group(1).strip() if m else None

    m = re.search(r"Phone Number:\s*([\d]+)", ft)
    v["provider_phone"] = m.group(1).strip() if m else None

    m = re.search(r"Email Address:\s*(\S+)", ft)
    v["provider_email"] = m.group(1).strip() if m else None

    # --- Q1: care at home ---
    m = re.search(r"Q1:.*?at home\?\s*\n\s*([^\n]+)", ft, re.DOTALL)
    v["care_at_home"] = m.group(1).strip() if m else None

    # --- Q1a: if not at home, where/when ---
    m = re.search(r"Q1a\..*?what dates\?\s*\n\s*([^\n]+)", ft, re.DOTALL)
    if m:
        v["q1a_response"] = m.group(1).strip()

    # --- Q2: shared care (2023+ forms only) ---
    m = re.search(r"Q2\..*?with you\?\s*\n\s*([^\n]+)", ft, re.DOTALL)
    if m:
        v["shared_care"] = m.group(1).strip()

    # --- Q2a: who else ---
    m = re.search(r"Q2a\..*?for\?\s*\n\s*([^\n]+)", ft, re.DOTALL)
    if m:
        v["q2a_who_else"] = m.group(1).strip()

    # --- Q2b: JH customer ---
    m = re.search(r"Q2b\..*?customer\?\s*\n\s*([^\n]+)", ft, re.DOTALL)
    if m:
        v["q2b_jh_customer"] = m.group(1).strip()

    # --- Q2c: other policy number ---
    m = re.search(r"Q2c\..*?ID:\s*\n\s*([^\n]+)", ft, re.DOTALL)
    if m:
        v["q2c_other_policy"] = m.group(1).strip()

    # --- Q2d: other claim number ---
    m = re.search(r"Q2d\..*?number:\s*\n\s*([^\n]+)", ft, re.DOTALL)
    if m:
        v["q2d_other_claim"] = m.group(1).strip()

    # --- Q3: assignment of benefits (2023+ forms only) ---
    m = re.search(r"Q3\..*?this provider\?\s*\n\s*([^\n]+)", ft, re.DOTALL)
    v["assignment_of_benefits"] = m.group(1).strip() if m else None

    # --- Q4: proof of payment type (2023+ forms only) ---
    m = re.search(r"Q4\..*?type:\s*\n\s*([^\n]+)", ft, re.DOTALL)
    if m:
        v["proof_of_payment_type"] = m.group(1).strip()

    # --- Q4a: other payment description ---
    m = re.search(r"Q4a\..*?description:\s*\n([^\n]+)", ft, re.DOTALL)
    if m:
        desc = m.group(1).strip()
        if desc:
            v["q4a_payment_desc"] = desc

    # --- Additional Information ---
    # 2022 form: on page 1.  2023+ forms: on page 2.
    for text_block in (ft, ft2):
        m = re.search(r"Additional Information:\s*\n[ \t]*([^\n]+)", text_block)
        if m:
            val = m.group(1).strip()
            # Reject false matches — if regex bled into the next section header, discard
            if val and not val.startswith("Fraud Attestation"):
                v["additional_info"] = val
                break

    # --- Fraud Attestation (attestation 1 of 2 on newer forms) ---
    # 2022 form: on page 1.  2023+ forms: on page 2.
    ft_combined = ft + "\n" + ft2 if ft2 else ft
    # Stop before the second attestation ("I attest that I have submitted") if present
    m_attest = re.search(
        r"I attest to the knowledge that(.+?)(?=\nI attest that I have|\n+I-\d+\b|\Z)",
        ft_combined, re.DOTALL)
    if m_attest:
        v["fraud_attestation_checked"] = "Yes"
        v["fraud_attestation_text"] = ("I attest to the knowledge that" +
                                        m_attest.group(1).strip().replace("\n", " "))
    else:
        v["fraud_attestation_checked"] = "No"

    # --- Proof of Payment Attestation (attestation 2, 2023+ forms only) ---
    m_pop = re.search(
        r"I attest that I have submitted proof of payment(.+?)(?=\n+I-\d+\b|\Z)",
        ft_combined, re.DOTALL)
    if m_pop:
        v["proof_payment_attested"] = "Yes"
        v["proof_payment_attest_text"] = ("I attest that I have submitted proof of payment" +
                                           m_pop.group(1).strip().replace("\n", " "))
    else:
        v["proof_payment_attested"] = None   # absent on 2022 form — FIELD_PLACEHOLDER handles display

    return {k: val for k, val in v.items() if val is not None}


# ---------------------------------------------------------------------------
# PDF annotation — page 1 only
# ---------------------------------------------------------------------------
def annotate_page(page):
    spans = get_spans(page)

    _, fc_entity = COLORS["entity"]
    logo_done = False

    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 1:
            continue
        rect = fitz.Rect(block["bbox"])

        if rect.y0 < 150 and not logo_done:
            # John Hancock logo — issuing_entity (box 0)
            page.draw_rect(rect + (-3, -3, 3, 3), color=fc_entity, width=1.5)
            page.insert_text(fitz.Point(max(rect.x0 - 14, 2), rect.y1 - 1),
                             "0", fontsize=6, color=fc_entity)
            page.insert_text(fitz.Point(rect.x0, max(rect.y0 - 2, 5)),
                             "issuing_entity", fontsize=4.5, color=fc_entity)
            logo_done = True

        elif rect.y0 > 500 and rect.width < 30:
            # Small image below mid-page = fraud attestation checkbox (box 15)
            page.draw_rect(rect + (-3, -3, 3, 3), color=fc_entity, width=1.5)
            page.insert_text(fitz.Point(max(rect.x0 - 14, 2), rect.y1 - 1),
                             "15", fontsize=6, color=fc_entity)
            page.insert_text(fitz.Point(rect.x0, max(rect.y0 - 2, 5)),
                             "chk", fontsize=4.5, color=fc_entity)

    for pattern, field_name, color_key, capture_value, box_num in FIELD_PATTERNS:
        _, fc = COLORS[color_key]

        matched = [(r, t) for r, t in spans if pattern.lower() in t.lower()]
        for rect, _ in matched:
            page.draw_rect(rect + (-2, -2, 2, 2), color=fc, width=1.5)

            badge_x = max(rect.x0 - 14, 2)
            badge_y = rect.y1 - 1
            page.insert_text(fitz.Point(badge_x, badge_y), box_num, fontsize=6, color=fc)

            page.insert_text(
                fitz.Point(rect.x0, max(rect.y0 - 2, 5)),
                field_name, fontsize=4.5, color=fc,
            )

            if capture_value:
                same_line_after = [
                    (r2, t2) for r2, t2 in spans
                    if abs(r2.y0 - rect.y0) < 4 and r2.x0 > rect.x1 + 1
                ]
                if same_line_after:
                    val_rect, _ = min(same_line_after, key=lambda x: x[0].x0)
                    page.draw_rect(val_rect + (-2, -2, 2, 2), color=fc, width=2.0)

    # Dynamically box I-XXXXX (invoice reference number at bottom of page)
    for rect, t in spans:
        if re.match(r"^I-\d+$", t.strip()):
            page.draw_rect(rect + (-3, -3, 3, 3), color=fc_entity, width=1.5)
            page.insert_text(fitz.Point(max(rect.x0 - 14, 2), rect.y1 - 1),
                             "ref", fontsize=6, color=fc_entity)
            page.insert_text(fitz.Point(rect.x0, max(rect.y0 - 2, 5)),
                             "invoice_number", fontsize=4.5, color=fc_entity)


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------
def rgb_css(color_key):
    r, g, b = COLORS[color_key][0]
    return f"rgb({r},{g},{b})"


def build_html(png_path, field_values, pdf_name):
    with open(png_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    rows_html = ""
    for key, label, num, ck in FIELD_ORDER:
        color = rgb_css(ck)
        raw_value = field_values.get(key, "")
        safe_value = raw_value.replace('"', "&quot;")
        found_class = "found" if raw_value else "missing"
        placeholder_text = FIELD_PLACEHOLDER.get(key, "not extracted")
        rows_html += f"""
      <tr id="row-{key}" class="field-row {found_class}">
        <td class="num-cell" style="border-left:4px solid {color};">
          <span class="badge" style="background:{color};">{num}</span>
        </td>
        <td class="name-cell" style="color:{color};">{label}</td>
        <td class="val-cell">
          <input type="text" id="val-{key}" class="val-input" value="{safe_value}"
                 oninput="markEdited('{key}')" placeholder="— {placeholder_text} —">
        </td>
        <td class="status-cell">
          <button class="status-btn status-pending" id="status-{key}"
                  onclick="cycleStatus('{key}')">?</button>
        </td>
        <td class="notes-cell">
          <input type="text" id="notes-{key}" class="notes-input" placeholder="notes…">
        </td>
      </tr>"""

    legend_html = ""
    for ck, desc in COLOR_LEGEND:
        legend_html += f"""
      <div class="legend-row">
        <div class="legend-swatch" style="background:{rgb_css(ck)};"></div>
        <span>{desc}</span>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Invoice Review — {pdf_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, sans-serif; background: #e8e8e8; }}
  .header {{
    background: #1a3a5c; color: white;
    padding: 9px 18px; font-size: 14px; font-weight: bold;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .note {{
    background: #fff3cd; color: #856404; font-size: 11px;
    padding: 5px 18px; border-bottom: 1px solid #ffc107;
  }}
  .header-buttons {{ display: flex; gap: 8px; }}
  .btn {{ padding: 5px 14px; border: none; border-radius: 4px; font-size: 12px; font-weight: bold; cursor: pointer; }}
  .btn-export  {{ background: #27ae60; color: white; }}
  .btn-reset   {{ background: #7f8c8d; color: white; }}
  .btn-approve {{ background: #2980b9; color: white; }}
  .layout {{ display: flex; height: calc(100vh - 60px); overflow: hidden; }}
  .left  {{ flex: 1.3; overflow: auto; padding: 10px; background: white; border-right: 2px solid #ccc; }}
  .right {{ flex: 0.9; overflow: auto; padding: 14px; background: #fafafa; }}
  img {{ max-width: 100%; display: block; }}
  h3 {{ font-size: 13px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 10px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  .field-row:nth-child(even) {{ background: #f4f4f4; }}
  .field-row.missing {{ background: #fff3f3; }}
  .field-row.edited  {{ background: #fffbe6; }}
  td {{ border-bottom: 1px solid #e0e0e0; vertical-align: middle; }}
  .num-cell  {{ width: 36px; padding: 5px 4px 5px 8px; }}
  .name-cell {{ width: 200px; padding: 5px 8px; font-family: monospace; font-size: 11px; white-space: nowrap; }}
  .val-cell  {{ padding: 4px 6px; }}
  .status-cell {{ width: 36px; padding: 4px; text-align: center; }}
  .notes-cell  {{ padding: 4px 6px; }}
  .badge {{ display: inline-block; color: white; font-size: 10px; font-weight: bold;
    min-width: 18px; height: 18px; line-height: 18px; text-align: center; border-radius: 9px; padding: 0 3px; }}
  .val-input, .notes-input {{ width: 100%; border: 1px solid #ddd; border-radius: 3px;
    padding: 3px 6px; font-size: 12px; background: transparent; }}
  .val-input:focus, .notes-input:focus {{ outline: none; border-color: #4a90d9; background: white; }}
  .notes-input {{ color: #666; font-style: italic; }}
  .status-btn {{ width: 28px; height: 24px; border: 1px solid #ccc; border-radius: 4px;
    font-size: 13px; cursor: pointer; font-weight: bold; display: flex; align-items: center; justify-content: center; }}
  .status-pending  {{ background: #f0f0f0; color: #888; border-color: #bbb; }}
  .status-approved {{ background: #d4edda; color: #155724; border-color: #80bd94; }}
  .status-rejected {{ background: #f8d7da; color: #721c24; border-color: #f5a8b0; }}
  .legend {{ margin-top: 16px; padding: 10px; background: white; border: 1px solid #ddd; border-radius: 4px; }}
  .legend h4 {{ font-size: 11px; color: #555; margin-bottom: 8px; }}
  .legend-row {{ display: flex; align-items: center; margin-bottom: 4px; }}
  .legend-swatch {{ width: 13px; height: 13px; border-radius: 2px; margin-right: 8px; flex-shrink: 0; }}
  .legend-row span {{ font-size: 11px; }}
  #toast {{ display: none; position: fixed; bottom: 20px; right: 20px;
    background: #27ae60; color: white; padding: 10px 20px; border-radius: 6px; font-size: 13px; z-index: 999; }}
</style>
</head>
<body>
<div class="header">
  <span>JH Invoice Review — {pdf_name}</span>
  <div class="header-buttons">
    <button class="btn btn-approve" onclick="approveAll()">&#10003; Approve All Visible</button>
    <button class="btn btn-export"  onclick="exportJSON()">&#11015; Export JSON</button>
    <button class="btn btn-reset"   onclick="resetAll()">&#8635; Reset</button>
  </div>
</div>
<div class="note">Page 1 (digital cover sheet) annotated below. Pages 2+ are scanned/handwritten timesheets — not auto-extracted. See page_count field. Note: assignment_of_benefits (Q3) is absent on 2022-era forms — pink = field not present on this form version, not an extraction error.</div>

<div class="layout">
  <div class="left">
    <img src="data:image/png;base64,{img_b64}" alt="Annotated Invoice — {pdf_name}">
  </div>
  <div class="right">
    <h3>Extracted Fields — click ? to validate each row</h3>
    <table>
      <thead>
        <tr>
          <th style="padding:5px 4px 5px 8px; background:#e0e0e0; font-size:11px; text-align:left;">#</th>
          <th style="padding:5px 8px; background:#e0e0e0; font-size:11px; text-align:left;">Field</th>
          <th style="padding:5px 8px; background:#e0e0e0; font-size:11px; text-align:left;">Extracted Value (editable)</th>
          <th style="padding:5px; background:#e0e0e0; font-size:11px; text-align:center;">OK?</th>
          <th style="padding:5px 8px; background:#e0e0e0; font-size:11px; text-align:left;">Notes / correction</th>
        </tr>
      </thead>
      <tbody id="field-tbody">
{rows_html}
      </tbody>
    </table>
    <div class="legend">
      <h4>Color legend (number = box on image)</h4>
      {legend_html}
    </div>
  </div>
</div>
<div id="toast"></div>
<script>
const STATUS_CYCLE = ['pending', 'approved', 'rejected'];
const STATUS_LABELS = {{ pending: '?', approved: '&#10003;', rejected: '&#10007;' }};
function cycleStatus(key) {{
  const btn = document.getElementById('status-' + key);
  const current = btn.dataset.status || 'pending';
  const next = STATUS_CYCLE[(STATUS_CYCLE.indexOf(current) + 1) % STATUS_CYCLE.length];
  setStatus(key, next);
}}
function setStatus(key, status) {{
  const btn = document.getElementById('status-' + key);
  btn.dataset.status = status;
  btn.innerHTML = STATUS_LABELS[status];
  btn.className = 'status-btn status-' + status;
}}
function markEdited(key) {{ document.getElementById('row-' + key).classList.add('edited'); }}
function approveAll() {{
  document.querySelectorAll('.field-row').forEach(row => {{
    const key = row.id.replace('row-', '');
    const val = document.getElementById('val-' + key).value.trim();
    if (val) setStatus(key, 'approved');
  }});
  toast('All non-empty fields marked approved');
}}
function resetAll() {{
  document.querySelectorAll('.field-row').forEach(row => {{
    const key = row.id.replace('row-', '');
    setStatus(key, 'pending');
    row.classList.remove('edited');
  }});
}}
function exportJSON() {{
  const result = {{ _source: "{pdf_name}", _reviewed: new Date().toISOString(), fields: {{}} }};
  document.querySelectorAll('.field-row').forEach(row => {{
    const key = row.id.replace('row-', '');
    const val   = document.getElementById('val-' + key).value.trim();
    const notes = document.getElementById('notes-' + key).value.trim();
    const status= document.getElementById('status-' + key).dataset.status || 'pending';
    result.fields[key] = {{ value: val, status: status, notes: notes || null }};
  }});
  const blob = new Blob([JSON.stringify(result, null, 2)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '{pdf_name}_validated.json';
  a.click();
  toast('Exported: {pdf_name}_validated.json');
}}
function toast(msg) {{
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(() => {{ el.style.display = 'none'; }}, 2500);
}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def run(pdf_path):
    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))

    page_count = doc.page_count
    page = doc[0]   # annotate page 1 only

    # Extract from page 1 + filename/metadata
    field_values = extract_field_values(page, pdf_path=pdf_path, page_count=page_count)

    # Annotate page 1
    annotate_page(page)

    # Render at 2.5x
    pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
    png_path = pdf_path.parent / (pdf_path.stem + "_fields.png")
    pix.save(str(png_path))
    print(f"Annotated PNG : {png_path}")

    html_content = build_html(png_path, field_values, pdf_path.stem)
    html_path = pdf_path.parent / (pdf_path.stem + "_review.html")
    html_path.write_text(html_content, encoding="utf-8")
    print(f"Review HTML   : {html_path}")

    subprocess.Popen(["cmd", "/c", "start", "msedge", str(html_path)])
    return html_path


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        run(sys.argv[1])
    else:
        default = (
            r"C:\Users\arika\OneDrive\Litigation\08_INCOMING"
            r"\John Hancock long term care document dpwnloads on 11-9-2025"
            r"\Invoice_864936_Claim_P27958_Policy_10013255_2022-01-19_143229.pdf"
        )
        run(default)
