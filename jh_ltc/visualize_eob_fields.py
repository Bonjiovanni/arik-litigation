#!/usr/bin/env python3
"""
EOB Field Visualizer
Left panel: Annotated PDF image with numbered, color-coded field boxes.
Right panel: Interactive table — editable values, ✓/✗/? validation toggle, notes, export JSON.

Usage: python visualize_eob_fields.py [path_to_eob.pdf]
Output: <pdf_name>_review.html  — opens in your default browser
"""

import fitz  # pymupdf
import sys
import subprocess
import base64
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Color palette:  color_key → (rgb 0-255 for HTML,  rgb 0-1 for fitz drawing)
# ---------------------------------------------------------------------------
COLORS = {
    "entity":    ((  0,   0,   0), (0.00, 0.00, 0.00)),  # black  — issuing entity (top header)
    "id":        ((220,  30,  30), (0.86, 0.12, 0.12)),  # red    — identifiers
    "payment":   (( 20, 100, 210), (0.08, 0.39, 0.82)),  # blue   — payment
    "recipient": ((155,  30, 185), (0.61, 0.12, 0.73)),  # purple — recipient
    "insured":   (( 20, 155,  50), (0.08, 0.61, 0.20)),  # green  — insured
    "txn":       ((160,  95,  10), (0.63, 0.37, 0.04)),  # brown  — transaction seq
    "service":   ((195, 115,  10), (0.76, 0.45, 0.04)),  # orange — service row
    "amounts":   (( 90,  20, 175), (0.35, 0.08, 0.69)),  # violet — charges/benefit
    "lifetime":  (( 20, 135, 135), (0.08, 0.53, 0.53)),  # teal   — lifetime limits
}

# ---------------------------------------------------------------------------
# FIELD_PATTERNS:
#   (search_text, field_name, color_key, capture_inline_value, box_number)
#
#   search_text         — substring to find in a PDF text span (the LABEL text)
#   field_name          — schema field name shown in table and on image
#   color_key           — key into COLORS dict
#   capture_inline_value— if True, also box the value span on the same line
#   box_number          — number printed in the badge on the image
# ---------------------------------------------------------------------------
FIELD_PATTERNS = [
    ("John Hancock Life Insurance Company (U.S.A.)", "issuing_entity", "entity", False, "1"),
    ("Page ",                    "page_number/total",     "entity",    False, "19"),
    ("Claim ID",                 "claim_id",              "id",        True,  "2"),
    ("Group Nbr",                "group_nbr",             "id",        True,  "3"),
    ("Payment Date",             "payment_date",          "payment",   True,  "4"),
    ("Payment Amount",           "payment_amount",        "payment",   True,  "5"),
    ("Payment is being made to", "payment_recipient",     "recipient", False, "6"),
    ("Insured:",                 "insured_name/address",  "insured",   False, "7"),
    ("Transaction Seq",          "transaction_seq",       "txn",       True,  "8"),
    ("Provider:",                "provider",              "service",   False, "9"),
    ("Lavigne, J",               "provider",              "service",   False, "9"),
    ("Service:",                 "service_type",          "service",   False, "10"),
    ("Home Health",              "service_type",          "service",   False, "10"),
    ("Dates:",                   "service_date_from/to",  "service",   False, "11"),
    ("Total Charge",             "total_charge",          "amounts",   True,  "13"),
    ("Exceeds Plan",             "exceeds_plan_max",      "amounts",   True,  "14"),
    ("Benefit:",                 "benefit_paid",          "amounts",   True,  "15"),
    ("You have used",            "lifetime_used/maximum", "lifetime",  False, "16"),
]

# For multi-line block values (recipient address, insured address):
# after finding the label span, also box blocks containing these strings
BLOCK_CAPTURES = {
    "payment_recipient": ["Robert Marks", "6 Lavigne", "South Hero"],
    "insured_name/address": ["Robert Marks", "6 Lavigne", "South Hero"],
}

# ---------------------------------------------------------------------------
# Field display order for the right panel
# ---------------------------------------------------------------------------
FIELD_ORDER = [
    # (schema_key,               display_label,             box_num, color_key)
    ("issuing_entity",           "issuing_entity",          "1",  "entity"),
    ("page_number",              "page_number",             "19", "entity"),
    ("page_total",               "page_total",              "19", "entity"),
    ("claim_id",                 "claim_id",                "2",  "id"),
    ("group_nbr",                "group_nbr",               "3",  "id"),
    ("payment_date",             "payment_date",            "4",  "payment"),
    ("payment_amount",           "payment_amount",          "5",  "payment"),
    ("payment_recipient_name",   "payment_recipient_name",  "6",  "recipient"),
    ("payment_recipient_address","payment_recipient_address","6",  "recipient"),
    ("insured_name",             "insured_name",            "7",  "insured"),
    ("insured_address",          "insured_address",         "7",  "insured"),
    ("transaction_seq",          "transaction_seq",         "8",  "txn"),
    ("provider",                 "provider",                "9",  "service"),
    ("service_type",             "service_type",            "10", "service"),
    ("service_date_from",        "service_date_from",       "11", "service"),
    ("service_date_to",          "service_date_to",         "12", "service"),
    ("total_charge",             "total_charge",            "13", "amounts"),
    ("exceeds_plan_max",         "exceeds_plan_max",        "14", "amounts"),
    ("benefit_paid",             "benefit_paid",            "15", "amounts"),
    ("lifetime_used",            "lifetime_used",           "16", "lifetime"),
    ("lifetime_maximum",         "lifetime_maximum",        "16", "lifetime"),
]

COLOR_LEGEND = [
    ("entity",    "1     Issuing entity (John Hancock)"),
    ("id",        "2–3   Identifiers (claim_id, group_nbr)"),
    ("payment",   "4–5   Payment (date, amount)"),
    ("recipient", "6     Payment recipient"),
    ("insured",   "7     Insured name / address"),
    ("txn",       "8     Transaction seq"),
    ("service",   "9–12  Service row (provider, type, dates)"),
    ("amounts",   "13–15 Charges & benefit"),
    ("lifetime",  "16    Lifetime used / maximum"),
]


# ---------------------------------------------------------------------------
# PDF text helpers
# ---------------------------------------------------------------------------
def get_spans(page):
    """All text spans with bounding boxes."""
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


def get_blocks(page):
    """All text blocks with bounding boxes and concatenated text."""
    result = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        lines_text = [
            " ".join(s["text"].strip() for s in line["spans"] if s["text"].strip())
            for line in block["lines"]
        ]
        full = "\n".join(t for t in lines_text if t)
        if full:
            result.append((fitz.Rect(block["bbox"]), full))
    return result


# ---------------------------------------------------------------------------
# Field value extraction
#
# NOTE: pymupdf reads this two-column layout in a non-intuitive order.
# Actual text order (from page.get_text()) for key fields:
#   VALUE "10/21/2022"  → then LABEL "Payment Date:"
#   VALUE "$7,015.00"   → then LABEL "Payment Date:" (payment_amount before its label)
#   VALUE "759641/A"    → then LABEL "Transaction Seq. Nbr.:"
#   VALUES $7,686 / $671 / $7,015 → then LABELS Exceeds / Benefit / Total Charge
# All regexes below account for this reversed label/value ordering.
# ---------------------------------------------------------------------------
def extract_field_values(page):
    """Return dict of schema_key -> extracted value string."""
    ft = page.get_text()
    v = {}

    # issuing_entity — match only the header form "(U.S.A.)", not the footer address line
    m = re.search(r"(John Hancock Life Insurance Company \(U\.S\.A\.\))", ft)
    v["issuing_entity"] = m.group(1).strip() if m else None

    # page_number / page_total — "Page X of Y"
    m = re.search(r"Page (\d+) of (\d+)", ft)
    if m:
        v["page_number"] = m.group(1).strip()
        v["page_total"]  = m.group(2).strip()

    # claim_id, group_nbr — left column, label then value (normal order)
    m = re.search(r"Claim ID:\s*\n([A-Z0-9]+)", ft)
    v["claim_id"] = m.group(1).strip() if m else None

    m = re.search(r"Group Nbr:\s*\n(\d+)", ft)
    v["group_nbr"] = m.group(1).strip() if m else None

    # payment_date — value appears on its own line BEFORE "Payment Amount:" label
    pos = ft.find("Payment Amount:")
    pre = ft[:pos] if pos > 0 else ft
    m = re.search(r"([\d]{1,2}/[\d]{1,2}/[\d]{4})", pre)
    v["payment_date"] = m.group(1).strip() if m else None

    # payment_amount — value appears immediately after "Payment is being made to:" label
    m = re.search(r"Payment is being made to:\s*\n\$([\d,]+\.?\d*)", ft)
    v["payment_amount"] = "$" + m.group(1).strip() if m else None

    # transaction_seq — value appears on its own line BEFORE "Transaction Seq. Nbr.:" label
    m = re.search(r"(\d{5,7}/[A-Z])\s*\nTransaction Seq", ft)
    v["transaction_seq"] = m.group(1).strip() if m else None

    # insured block — "Insured:\n<name>\n<name_repeated>\n<addr1>\n<addr2>"
    # pymupdf reads the two address blocks (insured left, recipient right) together
    # so the name appears twice; the first is insured, second is recipient
    m = re.search(r"Insured:\s*\n([^\n]+)\n([^\n]+)\n([^\n]+)\n([^\n]+)", ft)
    if m:
        v["insured_name"]             = m.group(1).strip()
        v["payment_recipient_name"]   = m.group(2).strip()  # recipient col read alongside insured
        v["insured_address"]          = m.group(3).strip() + ", " + m.group(4).strip()

    # payment_recipient_address — appears after "Transaction Seq. Nbr.:" label
    m = re.search(r"Transaction Seq\. Nbr\.:\s*\n([^\n]+)\n([^\n]+)", ft)
    if m:
        v["payment_recipient_address"] = m.group(1).strip() + ", " + m.group(2).strip()

    # service amounts — three dollar values appear consecutively BEFORE their labels
    # order in text: total_charge, exceeds_plan_max, benefit_paid
    m = re.search(r"\$([\d,]+\.?\d*)\n\$([\d,]+\.?\d*)\n\$([\d,]+\.?\d*)\nHome Health", ft)
    if m:
        v["total_charge"]    = "$" + m.group(1).strip()
        v["exceeds_plan_max"]= "$" + m.group(2).strip()
        v["benefit_paid"]    = "$" + m.group(3).strip()

    # service row — type and date range appear together in text
    m = re.search(r"(Home Health[^\n]+)\n([\d/]+ - [\d/]+)\n([^\n]+)", ft)
    if m:
        v["service_type"]      = m.group(1).strip()
        dates                  = m.group(2).strip().split(" - ")
        v["service_date_from"] = dates[0].strip() if dates else None
        v["service_date_to"]   = dates[1].strip() if len(dates) > 1 else None
        v["provider"]          = m.group(3).strip()

    # lifetime — single sentence, normal order
    m = re.search(r"used \$([\d,]+\.?\d*) of your \$([\d,]+\.?\d*) lifetime maximum", ft)
    if m:
        v["lifetime_used"]    = "$" + m.group(1).strip()
        v["lifetime_maximum"] = "$" + m.group(2).strip()

    return {k: val for k, val in v.items() if val is not None}


# ---------------------------------------------------------------------------
# PDF annotation
# ---------------------------------------------------------------------------
def annotate_page(page, field_values=None):
    spans  = get_spans(page)
    blocks = get_blocks(page)

    for pattern, field_name, color_key, capture_value, box_num in FIELD_PATTERNS:
        _, fc = COLORS[color_key]   # fitz color (0-1 float tuple)

        matched = [(r, t) for r, t in spans if pattern.lower() in t.lower()]
        for rect, _ in matched:
            # Draw box around label span
            page.draw_rect(rect + (-2, -2, 2, 2), color=fc, width=1.5)

            # Draw numbered badge to the left of the label
            badge_x = max(rect.x0 - 14, 2)
            badge_y = rect.y1 - 1
            page.insert_text(
                fitz.Point(badge_x, badge_y),
                box_num,
                fontsize=6,
                color=fc,
            )

            # Also print field name in small text above the box
            page.insert_text(
                fitz.Point(rect.x0, max(rect.y0 - 2, 5)),
                field_name,
                fontsize=4.5,
                color=fc,
            )

            # Box the value that follows on the same line
            if capture_value:
                same_line_after = [
                    (r2, t2) for r2, t2 in spans
                    if abs(r2.y0 - rect.y0) < 4 and r2.x0 > rect.x1 + 1
                ]
                if same_line_after:
                    val_rect, _ = min(same_line_after, key=lambda x: x[0].x0)
                    page.draw_rect(val_rect + (-2, -2, 2, 2), color=fc, width=2.0)

        # Box multi-line value blocks (e.g. address blocks below label)
        # Uses x-column constraint so insured (left) and recipient (right) don't cross-box
        if field_name in BLOCK_CAPTURES:
            label_y = min(r.y0 for r, _ in matched) if matched else 0
            label_x = min(r.x0 for r, _ in matched) if matched else 0
            page_width = page.rect.width
            targets = BLOCK_CAPTURES[field_name]
            for blk_rect, blk_text in blocks:
                if any(s.lower() in blk_text.lower() for s in targets):
                    if blk_rect.y0 >= label_y - 5:
                        # Constrain to same horizontal half as the label
                        blk_mid_x = (blk_rect.x0 + blk_rect.x1) / 2
                        label_in_left  = label_x < page_width / 2
                        block_in_left  = blk_mid_x < page_width / 2
                        if label_in_left == block_in_left:
                            page.draw_rect(blk_rect + (-3, -3, 3, 3), color=fc, width=1.2)

    # Dynamically box service dates using extracted values (dates vary per EOB)
    if field_values:
        _, fc = COLORS["service"]
        for date_key, box_num in [("service_date_from", "11"), ("service_date_to", "12")]:
            date_val = field_values.get(date_key)
            if date_val:
                for rect, t in spans:
                    if date_val in t:
                        page.draw_rect(rect + (-2, -2, 2, 2), color=fc, width=1.5)
                        page.insert_text(
                            fitz.Point(max(rect.x0 - 14, 2), rect.y1 - 1),
                            box_num, fontsize=6, color=fc,
                        )
                        page.insert_text(
                            fitz.Point(rect.x0, max(rect.y0 - 2, 5)),
                            date_key, fontsize=4.5, color=fc,
                        )


# ---------------------------------------------------------------------------
# HTML builder — interactive validation panel
# ---------------------------------------------------------------------------
def rgb_css(color_key):
    r, g, b = COLORS[color_key][0]
    return f"rgb({r},{g},{b})"


def build_html(png_path, field_values, pdf_name):
    with open(png_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    # Build table rows
    rows_html = ""
    for key, label, num, ck in FIELD_ORDER:
        color = rgb_css(ck)
        raw_value = field_values.get(key, "")
        safe_value = raw_value.replace('"', "&quot;")
        found_class = "found" if raw_value else "missing"
        rows_html += f"""
      <tr id="row-{key}" class="field-row {found_class}">
        <td class="num-cell" style="border-left:4px solid {color};">
          <span class="badge" style="background:{color};">{num}</span>
        </td>
        <td class="name-cell" style="color:{color};">{label}</td>
        <td class="val-cell">
          <input type="text" id="val-{key}" class="val-input" value="{safe_value}"
                 oninput="markEdited('{key}')" placeholder="— not extracted —">
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
<title>EOB Review — {pdf_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, sans-serif; background: #e8e8e8; }}

  .header {{
    background: #1a3a5c; color: white;
    padding: 9px 18px; font-size: 14px; font-weight: bold;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .header-buttons {{ display: flex; gap: 8px; }}
  .btn {{
    padding: 5px 14px; border: none; border-radius: 4px;
    font-size: 12px; font-weight: bold; cursor: pointer;
  }}
  .btn-export  {{ background: #27ae60; color: white; }}
  .btn-reset   {{ background: #7f8c8d; color: white; }}
  .btn-approve {{ background: #2980b9; color: white; }}

  .layout {{
    display: flex; height: calc(100vh - 40px); overflow: hidden;
  }}
  .left  {{ flex: 1.3; overflow: auto; padding: 10px; background: white; border-right: 2px solid #ccc; }}
  .right {{ flex: 0.9; overflow: auto; padding: 14px; background: #fafafa; }}

  img {{ max-width: 100%; display: block; }}

  h3 {{ font-size: 13px; color: #333; border-bottom: 1px solid #ccc;
        padding-bottom: 5px; margin-bottom: 10px; }}

  table {{ border-collapse: collapse; width: 100%; }}
  .field-row:nth-child(even) {{ background: #f4f4f4; }}
  .field-row.missing {{ background: #fff3f3; }}
  .field-row.edited  {{ background: #fffbe6; }}

  td {{ border-bottom: 1px solid #e0e0e0; vertical-align: middle; }}

  .num-cell  {{ width: 36px; padding: 5px 4px 5px 8px; }}
  .name-cell {{ width: 180px; padding: 5px 8px; font-family: monospace; font-size: 11px; white-space: nowrap; }}
  .val-cell  {{ padding: 4px 6px; }}
  .status-cell {{ width: 36px; padding: 4px; text-align: center; }}
  .notes-cell  {{ padding: 4px 6px; }}

  .badge {{
    display: inline-block; color: white; font-size: 10px; font-weight: bold;
    min-width: 18px; height: 18px; line-height: 18px;
    text-align: center; border-radius: 9px; padding: 0 3px;
  }}

  .val-input, .notes-input {{
    width: 100%; border: 1px solid #ddd; border-radius: 3px;
    padding: 3px 6px; font-size: 12px; background: transparent;
  }}
  .val-input:focus, .notes-input:focus {{
    outline: none; border-color: #4a90d9; background: white;
  }}
  .notes-input {{ color: #666; font-style: italic; }}

  .status-btn {{
    width: 28px; height: 24px; border: 1px solid #ccc; border-radius: 4px;
    font-size: 13px; cursor: pointer; font-weight: bold;
    display: flex; align-items: center; justify-content: center;
  }}
  .status-pending  {{ background: #f0f0f0; color: #888; border-color: #bbb; }}
  .status-approved {{ background: #d4edda; color: #155724; border-color: #80bd94; }}
  .status-rejected {{ background: #f8d7da; color: #721c24; border-color: #f5a8b0; }}

  .legend {{ margin-top: 16px; padding: 10px; background: white;
             border: 1px solid #ddd; border-radius: 4px; }}
  .legend h4 {{ font-size: 11px; color: #555; margin-bottom: 8px; }}
  .legend-row {{ display: flex; align-items: center; margin-bottom: 4px; }}
  .legend-swatch {{ width: 13px; height: 13px; border-radius: 2px;
                    margin-right: 8px; flex-shrink: 0; }}
  .legend-row span {{ font-size: 11px; }}

  #toast {{
    display: none; position: fixed; bottom: 20px; right: 20px;
    background: #27ae60; color: white; padding: 10px 20px;
    border-radius: 6px; font-size: 13px; z-index: 999;
  }}
</style>
</head>
<body>
<div class="header">
  <span>JH EOB Field Review — {pdf_name}</span>
  <div class="header-buttons">
    <button class="btn btn-approve" onclick="approveAll()">✓ Approve All Visible</button>
    <button class="btn btn-export"  onclick="exportJSON()">⬇ Export JSON</button>
    <button class="btn btn-reset"   onclick="resetAll()">↺ Reset</button>
  </div>
</div>

<div class="layout">
  <div class="left">
    <img src="data:image/png;base64,{img_b64}" alt="Annotated EOB — {pdf_name}">
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
const STATUS_LABELS = {{ pending: '?', approved: '✓', rejected: '✗' }};

function cycleStatus(key) {{
  const btn = document.getElementById('status-' + key);
  const current = btn.dataset.status || 'pending';
  const next = STATUS_CYCLE[(STATUS_CYCLE.indexOf(current) + 1) % STATUS_CYCLE.length];
  setStatus(key, next);
}}

function setStatus(key, status) {{
  const btn = document.getElementById('status-' + key);
  btn.dataset.status = status;
  btn.textContent = STATUS_LABELS[status];
  btn.className = 'status-btn status-' + status;
}}

function markEdited(key) {{
  const row = document.getElementById('row-' + key);
  row.classList.add('edited');
}}

function approveAll() {{
  document.querySelectorAll('.field-row').forEach(row => {{
    const key = row.id.replace('row-', '');
    const val = document.getElementById('val-' + key).value.trim();
    if (val) setStatus(key, 'approved');
  }});
  toast('All non-empty fields marked ✓');
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
    doc  = fitz.open(str(pdf_path))
    page = doc[0]

    # Extract values BEFORE drawing (drawing modifies the page object)
    field_values = extract_field_values(page)

    # Draw numbered annotation overlays
    annotate_page(page, field_values)

    # Render to PNG at 2.5× resolution
    pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
    png_path = pdf_path.parent / (pdf_path.stem + "_fields.png")
    pix.save(str(png_path))
    print(f"Annotated PNG : {png_path}")

    # Build and save self-contained HTML
    html_content = build_html(png_path, field_values, pdf_path.stem)
    html_path = pdf_path.parent / (pdf_path.stem + "_review.html")
    html_path.write_text(html_content, encoding="utf-8")
    print(f"Review HTML   : {html_path}")

    # Open HTML in Microsoft Edge
    subprocess.Popen(["cmd", "/c", "start", "msedge", str(html_path)])
    return html_path


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        run(sys.argv[1])
    else:
        default = (
            r"C:\Users\arika\OneDrive\Litigation\08_INCOMING"
            r"\John Hancock long term care document dpwnloads on 11-9-2025"
            r"\2022-10-24-EOB.pdf"
        )
        run(default)
