"""
Tests for jh_ltc/visualize_eob_fields.py and jh_ltc/batch_eob_process.py

Pure-function tests only — no real PDFs or API calls required.
fitz.Page is mocked via a simple class that returns canned text.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import visualize_eob_fields as eob_viz
import batch_eob_process as eob_batch


# ---------------------------------------------------------------------------
# Minimal mock for a fitz page
# ---------------------------------------------------------------------------
class MockPage:
    """Lightweight stand-in for a fitz.Page with get_text() only."""
    def __init__(self, text):
        self._text = text

    def get_text(self, *args, **kwargs):
        return self._text


# Sample EOB page text carefully ordered to match all regex patterns
# in extract_field_values().
SAMPLE_EOB_TEXT = (
    "John Hancock Life Insurance Company (U.S.A.)\n"
    "Page 1 of 2\n"
    "Claim ID:\n"
    "P12345\n"
    "Group Nbr:\n"
    "9900\n"
    "10/21/2022\n"                              # payment_date appears before label
    "Payment Amount:\n"
    "Payment is being made to:\n"
    "$7,015.00\n"                               # payment_amount after label
    "Insured:\n"
    "Robert Marks\n"
    "Bob Smith\n"
    "123 Main Street\n"
    "South Hero, VT 05486\n"
    "759641/A\n"                                # transaction_seq before label
    "Transaction Seq. Nbr.:\n"
    "456 Oak Drive\n"
    "South Burlington, VT\n"
    "$7,686.00\n"                               # total_charge (amounts in order)
    "$671.00\n"                                 # exceeds_plan_max
    "$7,015.00\n"                               # benefit_paid
    "Home Health Care Services\n"               # service_type (also terminates amounts match)
    "10/01/2022 - 10/31/2022\n"                 # service dates
    "Lavigne Home Health\n"                     # provider
    "used $50,000.00 of your $200,000.00 lifetime maximum\n"
)


# ---------------------------------------------------------------------------
# TestEobFieldOrder
# ---------------------------------------------------------------------------
class TestEobFieldOrder:
    def test_field_order_is_nonempty(self):
        assert len(eob_viz.FIELD_ORDER) > 0

    def test_field_order_has_expected_keys(self):
        keys = {row[0] for row in eob_viz.FIELD_ORDER}
        for expected in ("claim_id", "payment_date", "payment_amount",
                         "provider", "total_charge", "benefit_paid",
                         "lifetime_used", "lifetime_maximum"):
            assert expected in keys, f"Missing key: {expected}"

    def test_field_order_tuples_are_4_element(self):
        for item in eob_viz.FIELD_ORDER:
            assert len(item) == 4, f"Expected 4-tuple, got: {item}"

    def test_field_order_color_keys_valid(self):
        valid_colors = set(eob_viz.COLORS.keys())
        for _key, _label, _num, color_key in eob_viz.FIELD_ORDER:
            assert color_key in valid_colors, f"Unknown color key: {color_key}"


# ---------------------------------------------------------------------------
# TestExtractFieldValuesEob
# ---------------------------------------------------------------------------
class TestExtractFieldValuesEob:
    def _extract(self, text=SAMPLE_EOB_TEXT):
        page = MockPage(text)
        return eob_viz.extract_field_values(page)

    def test_issuing_entity(self):
        v = self._extract()
        assert v.get("issuing_entity") == "John Hancock Life Insurance Company (U.S.A.)"

    def test_page_number_and_total(self):
        v = self._extract()
        assert v.get("page_number") == "1"
        assert v.get("page_total") == "2"

    def test_claim_id(self):
        v = self._extract()
        assert v.get("claim_id") == "P12345"

    def test_group_nbr(self):
        v = self._extract()
        assert v.get("group_nbr") == "9900"

    def test_payment_date(self):
        v = self._extract()
        assert v.get("payment_date") == "10/21/2022"

    def test_payment_amount(self):
        v = self._extract()
        assert v.get("payment_amount") == "$7,015.00"

    def test_transaction_seq(self):
        v = self._extract()
        assert v.get("transaction_seq") == "759641/A"

    def test_insured_name(self):
        v = self._extract()
        assert v.get("insured_name") == "Robert Marks"

    def test_service_type(self):
        v = self._extract()
        assert v.get("service_type") == "Home Health Care Services"

    def test_service_dates(self):
        v = self._extract()
        assert v.get("service_date_from") == "10/01/2022"
        assert v.get("service_date_to") == "10/31/2022"

    def test_provider(self):
        v = self._extract()
        assert v.get("provider") == "Lavigne Home Health"

    def test_service_amounts(self):
        v = self._extract()
        assert v.get("total_charge") == "$7,686.00"
        assert v.get("exceeds_plan_max") == "$671.00"
        assert v.get("benefit_paid") == "$7,015.00"

    def test_lifetime_values(self):
        v = self._extract()
        assert v.get("lifetime_used") == "$50,000.00"
        assert v.get("lifetime_maximum") == "$200,000.00"

    def test_empty_text_returns_empty_dict(self):
        v = self._extract("")
        assert isinstance(v, dict)
        assert len(v) == 0

    def test_none_values_excluded_from_result(self):
        """extract_field_values filters out None values."""
        v = self._extract("no matching text at all")
        assert all(val is not None for val in v.values())


# ---------------------------------------------------------------------------
# TestFindEobsSorting
# ---------------------------------------------------------------------------
class TestFindEobsSorting:
    def test_sorted_oldest_to_newest(self, tmp_path, monkeypatch):
        (tmp_path / "2022-10-24-EOB.pdf").touch()
        (tmp_path / "2023-03-15-EOB.pdf").touch()
        (tmp_path / "2021-05-01-EOB.pdf").touch()
        monkeypatch.setattr(eob_batch, "EOB_DIR", tmp_path)
        result = eob_batch.find_eobs()
        names = [p.name for p in result]
        assert names == [
            "2021-05-01-EOB.pdf",
            "2022-10-24-EOB.pdf",
            "2023-03-15-EOB.pdf",
        ]

    def test_non_date_prefix_files_excluded(self, tmp_path, monkeypatch):
        (tmp_path / "2022-10-24-EOB.pdf").touch()
        (tmp_path / "EOB_summary.pdf").touch()       # no date prefix
        (tmp_path / "EOB_all_chrono.pdf").touch()    # no date prefix
        monkeypatch.setattr(eob_batch, "EOB_DIR", tmp_path)
        result = eob_batch.find_eobs()
        assert len(result) == 1
        assert result[0].name == "2022-10-24-EOB.pdf"

    def test_non_eob_pdfs_excluded(self, tmp_path, monkeypatch):
        (tmp_path / "2022-10-24-EOB.pdf").touch()
        (tmp_path / "2022-10-24-Invoice.pdf").touch()  # no "EOB" in name
        monkeypatch.setattr(eob_batch, "EOB_DIR", tmp_path)
        result = eob_batch.find_eobs()
        assert len(result) == 1
        assert "EOB" in result[0].name

    def test_empty_directory_returns_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eob_batch, "EOB_DIR", tmp_path)
        result = eob_batch.find_eobs()
        assert result == []


# ---------------------------------------------------------------------------
# TestCoerceEob
# ---------------------------------------------------------------------------
class TestCoerceEob:
    def test_currency_strips_dollar_and_comma(self):
        assert eob_batch.coerce("$7,015.00", "currency") == 7015.0

    def test_currency_plain_number(self):
        assert eob_batch.coerce("1234.56", "currency") == 1234.56

    def test_currency_empty_returns_empty_string(self):
        assert eob_batch.coerce("", "currency") == ""

    def test_currency_unparseable_returned_as_string(self):
        assert eob_batch.coerce("N/A", "currency") == "N/A"

    def test_date_mm_slash_dd_slash_yyyy(self):
        result = eob_batch.coerce("10/21/2022", "date")
        assert isinstance(result, datetime)
        assert result.month == 10
        assert result.day == 21
        assert result.year == 2022

    def test_date_unparseable_returned_as_string(self):
        result = eob_batch.coerce("not-a-date", "date")
        assert result == "not-a-date"

    def test_int_valid(self):
        assert eob_batch.coerce("42", "int") == 42

    def test_int_unparseable_returned_as_string(self):
        assert eob_batch.coerce("abc", "int") == "abc"

    def test_text_returned_unchanged(self):
        assert eob_batch.coerce("Hello World", "text") == "Hello World"

    def test_empty_int_returns_empty_string(self):
        assert eob_batch.coerce("", "int") == ""
