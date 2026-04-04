"""
Tests for jh_ltc/visualize_invoice_fields.py, jh_ltc/batch_invoice_process.py,
and jh_ltc/extract_one_detail_page.py

batch_invoice_process.py and extract_one_detail_page.py both call
OUT_DIR.mkdir() at module level. We patch pathlib.Path.mkdir before
importing them so CI doesn't fail when INVOICE_DIR doesn't exist.
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# jh_ltc/ is on sys.path via conftest.py — safe to import.
import visualize_invoice_fields as inv_viz

# batch_invoice_process.py has OUT_DIR.mkdir() at module level.
# Patch Path.mkdir before the first import so CI doesn't crash.
with patch("pathlib.Path.mkdir"):
    import batch_invoice_process as inv_batch

# extract_one_detail_page.py has OUT_DIR.mkdir() at module level.
with patch("pathlib.Path.mkdir"):
    import extract_one_detail_page as probe


# ---------------------------------------------------------------------------
# Minimal mock for a fitz page
# ---------------------------------------------------------------------------
class MockPage:
    def __init__(self, text):
        self._text = text

    def get_text(self, *args, **kwargs):
        return self._text


# Sample Invoice page 1 text
SAMPLE_INVOICE_TEXT = (
    "Policy Number: 10013255\n"
    "Claim Number: P27958\n"
    "Provider: Lavigne Home Health\n"
    "Total Charges: $1,764.00\n"
    "Hourly Rate: $18.00\n"
    "Service Date From: 05/01/2023\n"
    "Service Date To: 05/31/2023\n"
    "Submitted By: Robert Marks\n"
    "Date Submitted: 06/09/2023\n"
    "Phone Number: 8023721234\n"
    "Email Address: test@example.com\n"
)

# Fake invoice filename that contains invoice number and date
SAMPLE_PDF_NAME = "Invoice_1554588_Claim_P27958_Policy_10013255_2023-10-02_162103.pdf"
SAMPLE_PDF_PATH = Path(SAMPLE_PDF_NAME)


# ---------------------------------------------------------------------------
# TestInvoiceFieldOrder
# ---------------------------------------------------------------------------
class TestInvoiceFieldOrder:
    def test_field_order_is_nonempty(self):
        assert len(inv_viz.FIELD_ORDER) > 0

    def test_field_order_has_expected_keys(self):
        keys = {row[0] for row in inv_viz.FIELD_ORDER}
        for expected in ("policy_number", "claim_number", "provider_name",
                         "total_charges", "invoice_number", "doc_date",
                         "service_date_from", "service_date_to"):
            assert expected in keys, f"Missing key: {expected}"

    def test_field_order_tuples_are_4_element(self):
        for item in inv_viz.FIELD_ORDER:
            assert len(item) == 4, f"Expected 4-tuple, got: {item}"

    def test_field_order_color_keys_valid(self):
        valid_colors = set(inv_viz.COLORS.keys())
        for _key, _label, _num, color_key in inv_viz.FIELD_ORDER:
            assert color_key in valid_colors, f"Unknown color key: {color_key}"


# ---------------------------------------------------------------------------
# TestExtractFieldValuesInvoice
# ---------------------------------------------------------------------------
class TestExtractFieldValuesInvoice:
    def _extract(self, text=SAMPLE_INVOICE_TEXT, pdf_path=SAMPLE_PDF_PATH,
                 page_count=3, doc=None):
        page = MockPage(text)
        return inv_viz.extract_field_values(
            page, pdf_path=pdf_path, page_count=page_count, doc=doc
        )

    def test_doc_type_constant(self):
        v = self._extract()
        assert v.get("doc_type") == "Claim_Invoice"

    def test_doc_subtype_constant(self):
        v = self._extract()
        assert v.get("doc_subtype") == "Invoice_Cover_Sheet"

    def test_issuing_entity_hardcoded(self):
        v = self._extract()
        assert v.get("issuing_entity") == "John Hancock Life Insurance Company (U.S.A.)"

    def test_invoice_number_from_filename(self):
        v = self._extract()
        assert v.get("invoice_number") == "1554588"

    def test_doc_date_from_filename(self):
        v = self._extract()
        assert v.get("doc_date") == "2023-10-02"

    def test_page_count_from_argument(self):
        v = self._extract(page_count=5)
        assert v.get("page_count") == "5"

    def test_policy_number(self):
        v = self._extract()
        assert v.get("policy_number") == "10013255"

    def test_claim_number(self):
        v = self._extract()
        assert v.get("claim_number") == "P27958"

    def test_provider_name(self):
        v = self._extract()
        assert v.get("provider_name") == "Lavigne Home Health"

    def test_total_charges(self):
        v = self._extract()
        assert v.get("total_charges") == "$1,764.00"

    def test_hourly_rate(self):
        v = self._extract()
        assert v.get("hourly_rate") == "$18.00"

    def test_no_pdf_path_skips_filename_fields(self):
        v = self._extract(pdf_path=None)
        assert "doc_date" not in v

    def test_no_page_count_skips_page_count(self):
        v = self._extract(page_count=None)
        assert "page_count" not in v


# ---------------------------------------------------------------------------
# TestFindInvoicesSorting
# ---------------------------------------------------------------------------
class TestFindInvoicesSorting:
    def test_sorted_oldest_to_newest(self, tmp_path, monkeypatch):
        (tmp_path / "Invoice_001_Claim_X_Policy_Y_2022-01-15_120000.pdf").touch()
        (tmp_path / "Invoice_002_Claim_X_Policy_Y_2023-06-30_093000.pdf").touch()
        (tmp_path / "Invoice_003_Claim_X_Policy_Y_2021-11-20_080000.pdf").touch()
        monkeypatch.setattr(inv_batch, "INVOICE_DIR", tmp_path)
        result = inv_batch.find_invoices()
        dates = []
        import re
        DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})_")
        for p in result:
            m = DATE_RE.search(p.name)
            dates.append(m.group(1))
        assert dates == sorted(dates)

    def test_non_invoice_prefix_files_excluded(self, tmp_path, monkeypatch):
        (tmp_path / "Invoice_001_Claim_X_Policy_Y_2022-01-15_120000.pdf").touch()
        (tmp_path / "EOB_2022-01-15_something.pdf").touch()  # doesn't start with Invoice_
        monkeypatch.setattr(inv_batch, "INVOICE_DIR", tmp_path)
        result = inv_batch.find_invoices()
        assert len(result) == 1
        assert result[0].name.startswith("Invoice_")

    def test_files_without_date_excluded(self, tmp_path, monkeypatch):
        (tmp_path / "Invoice_001_no_date_here.pdf").touch()
        monkeypatch.setattr(inv_batch, "INVOICE_DIR", tmp_path)
        result = inv_batch.find_invoices()
        assert len(result) == 0

    def test_empty_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(inv_batch, "INVOICE_DIR", tmp_path)
        result = inv_batch.find_invoices()
        assert result == []


# ---------------------------------------------------------------------------
# TestCoerceInvoice
# ---------------------------------------------------------------------------
class TestCoerceInvoice:
    def test_currency_value(self):
        result = inv_batch.coerce("$1,764.00", "currency")
        assert result == 1764.0

    def test_currency_empty(self):
        assert inv_batch.coerce("", "currency") == ""

    def test_currency_unparseable(self):
        assert inv_batch.coerce("N/A", "currency") == "N/A"

    def test_date_yyyy_mm_dd(self):
        result = inv_batch.coerce("2023-10-02", "date")
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 10
        assert result.day == 2

    def test_date_mm_slash_dd_slash_yyyy(self):
        result = inv_batch.coerce("06/09/2023", "date")
        assert isinstance(result, datetime)
        assert result.month == 6

    def test_date_unparseable(self):
        result = inv_batch.coerce("not-a-date", "date")
        assert result == "not-a-date"

    def test_int_valid(self):
        assert inv_batch.coerce("10013255", "int") == 10013255

    def test_int_unparseable(self):
        assert inv_batch.coerce("P27958", "int") == "P27958"

    def test_text_passthrough(self):
        assert inv_batch.coerce("Lavigne Home Health", "text") == "Lavigne Home Health"


# ---------------------------------------------------------------------------
# TestExtractOneDetailPageConfig
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not Path(r"C:\Users\arika\OneDrive\Litigation").exists(),
    reason="Requires real INVOICE_DIR — integration test, skip in CI"
)
class TestExtractOneDetailPageConfig:
    def test_invoice_dir_is_path(self):
        assert isinstance(probe.INVOICE_DIR, Path)

    def test_out_dir_is_path(self):
        assert isinstance(probe.OUT_DIR, Path)

    def test_key_file_is_path(self):
        assert isinstance(probe.KEY_FILE, Path)

    def test_out_dir_is_subdir_of_invoice_dir(self):
        assert probe.INVOICE_DIR in probe.OUT_DIR.parents
