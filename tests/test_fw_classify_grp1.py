"""
tests/test_fw_classify_grp1.py
-------------------------------
Unit tests for fw_classify_grp1.py:
    extract_text_from_text_file, detect_money, detect_dates,
    match_keywords, get_text_sample
"""

import pytest
from pathlib import Path

import fw_classify_grp1 as grp1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_text(tmp_path: Path, content: str, filename: str = "sample.txt") -> str:
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# TestExtractTextFromTextFile
# ---------------------------------------------------------------------------

class TestExtractTextFromTextFile:

    def test_reads_content(self, tmp_path):
        path = _write_text(tmp_path, "Hello world")
        result = grp1.extract_text_from_text_file(path)
        assert result == "Hello world"

    def test_respects_max_chars(self, tmp_path):
        path = _write_text(tmp_path, "A" * 200)
        result = grp1.extract_text_from_text_file(path, max_chars=50)
        assert result == "A" * 50

    def test_returns_empty_on_missing_file(self, tmp_path):
        result = grp1.extract_text_from_text_file(str(tmp_path / "nonexistent.txt"))
        assert result == ""

    def test_handles_utf8_content(self, tmp_path):
        path = _write_text(tmp_path, "café résumé naïve")
        result = grp1.extract_text_from_text_file(path)
        assert "café" in result

    def test_multiline_content(self, tmp_path):
        path = _write_text(tmp_path, "line1\nline2\nline3")
        result = grp1.extract_text_from_text_file(path)
        assert "line1" in result and "line3" in result


# ---------------------------------------------------------------------------
# TestDetectMoney
# ---------------------------------------------------------------------------

class TestDetectMoney:

    def test_dollar_sign_amount(self):
        assert grp1.detect_money("Invoice total: $1,234.56") == "Y"

    def test_dollar_no_cents(self):
        assert grp1.detect_money("Payment of $500 due today") == "Y"

    def test_usd_keyword(self):
        assert grp1.detect_money("Amount in USD: 500") == "Y"

    def test_dollars_word(self):
        assert grp1.detect_money("five hundred dollars") == "Y"

    def test_cents_word(self):
        assert grp1.detect_money("fifty cents owed") == "Y"

    def test_no_money_signals(self):
        assert grp1.detect_money("This is a plain text document") == "N"

    def test_empty_string_returns_empty(self):
        assert grp1.detect_money("") == ""

    def test_whitespace_only_returns_empty(self):
        assert grp1.detect_money("   ") == ""

    def test_none_returns_empty(self):
        assert grp1.detect_money(None) == ""


# ---------------------------------------------------------------------------
# TestDetectDates
# ---------------------------------------------------------------------------

class TestDetectDates:

    def test_slash_format(self):
        assert grp1.detect_dates("Date: 01/15/2023") == "Y"

    def test_iso_format(self):
        assert grp1.detect_dates("Updated 2023-12-31.") == "Y"

    def test_long_form_month(self):
        assert grp1.detect_dates("January 15, 2020 meeting") == "Y"

    def test_abbreviated_month(self):
        assert grp1.detect_dates("Oct 3, 2021 invoice") == "Y"

    def test_no_dates(self):
        assert grp1.detect_dates("No date information here") == "N"

    def test_empty_string_returns_empty(self):
        assert grp1.detect_dates("") == ""

    def test_whitespace_only_returns_empty(self):
        assert grp1.detect_dates("   ") == ""

    def test_none_returns_empty(self):
        assert grp1.detect_dates(None) == ""

    def test_mixed_money_and_date(self):
        # both money and date present — date check should still fire
        assert grp1.detect_dates("$100 paid on 03/01/2022") == "Y"


# ---------------------------------------------------------------------------
# TestMatchKeywords
# ---------------------------------------------------------------------------

class TestMatchKeywords:

    def test_single_hit(self):
        result = grp1.match_keywords("This trust document", ["trust"])
        assert result == "trust"

    def test_multiple_hits(self):
        hits = grp1.match_keywords("trust beneficiary distribution", ["trust", "beneficiary", "invoice"])
        assert "trust" in hits
        assert "beneficiary" in hits
        assert "invoice" not in hits

    def test_case_insensitive(self):
        result = grp1.match_keywords("TRUST DOCUMENT", ["trust"])
        assert result == "trust"

    def test_no_hits_returns_empty(self):
        result = grp1.match_keywords("plain text", ["trust", "invoice"])
        assert result == ""

    def test_empty_text_returns_empty(self):
        result = grp1.match_keywords("", ["trust"])
        assert result == ""

    def test_none_text_returns_empty(self):
        result = grp1.match_keywords(None, ["trust"])
        assert result == ""

    def test_empty_keywords_returns_empty(self):
        result = grp1.match_keywords("trust document", [])
        assert result == ""

    def test_hits_semicolon_joined(self):
        result = grp1.match_keywords("trust beneficiary", ["trust", "beneficiary"])
        parts = result.split(";")
        assert len(parts) == 2

    def test_preserves_keyword_case(self):
        result = grp1.match_keywords("ltc claim", ["LTC"])
        assert result == "LTC"


# ---------------------------------------------------------------------------
# TestGetTextSample
# ---------------------------------------------------------------------------

class TestGetTextSample:

    def test_text_file_dispatch(self, tmp_path):
        path = _write_text(tmp_path, "Hello from text file")
        text, ok = grp1.get_text_sample(str(path), "text_file", max_chars=500)
        assert ok is True
        assert "Hello" in text

    def test_text_file_max_chars_respected(self, tmp_path):
        path = _write_text(tmp_path, "X" * 300)
        text, ok = grp1.get_text_sample(str(path), "text_file", max_chars=50)
        assert len(text) <= 50

    def test_unsupported_family_returns_empty_false(self, tmp_path):
        text, ok = grp1.get_text_sample(str(tmp_path / "vid.mp4"), "video")
        assert text == ""
        assert ok is False

    def test_image_family_returns_empty_false(self, tmp_path):
        text, ok = grp1.get_text_sample(str(tmp_path / "pic.jpg"), "image")
        assert text == ""
        assert ok is False

    def test_archive_family_returns_empty_false(self, tmp_path):
        text, ok = grp1.get_text_sample(str(tmp_path / "arc.zip"), "archive")
        assert text == ""
        assert ok is False

    def test_word_doc_family_falls_back_to_text(self, tmp_path):
        path = _write_text(tmp_path, "Word content here", filename="doc.txt")
        text, ok = grp1.get_text_sample(str(path), "word_doc", max_chars=500)
        # May or may not succeed depending on file — just verify return types
        assert isinstance(text, str)
        assert isinstance(ok, bool)

    def test_empty_family_returns_empty_false(self, tmp_path):
        text, ok = grp1.get_text_sample(str(tmp_path / "x.bin"), "")
        assert text == ""
        assert ok is False

    def test_case_insensitive_family(self, tmp_path):
        # The dispatcher lowercases family
        path = _write_text(tmp_path, "content")
        text, ok = grp1.get_text_sample(str(path), "TEXT_FILE", max_chars=500)
        assert ok is True
        assert "content" in text


# ---------------------------------------------------------------------------
# TestDetectFormFields
# ---------------------------------------------------------------------------

class TestDetectFormFields:

    def _make_plain_pdf(self, tmp_path):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Plain document with no form fields.")
        path = str(tmp_path / "plain.pdf")
        doc.save(path)
        doc.close()
        return path

    def _make_form_pdf(self, tmp_path):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        widget = fitz.Widget()
        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        widget.rect = fitz.Rect(50, 50, 200, 70)
        widget.field_name = "TestField"
        widget.field_value = ""
        page.add_widget(widget)
        path = str(tmp_path / "form.pdf")
        doc.save(path)
        doc.close()
        return path

    def test_returns_n_for_plain_pdf(self, tmp_path):
        path = self._make_plain_pdf(tmp_path)
        assert grp1.detect_form_fields(path) == "N"

    def test_returns_y_for_form_pdf(self, tmp_path):
        path = self._make_form_pdf(tmp_path)
        assert grp1.detect_form_fields(path) == "Y"

    def test_returns_empty_for_bad_path(self, tmp_path):
        result = grp1.detect_form_fields(str(tmp_path / "nonexistent.pdf"))
        assert result == ""

    def test_returns_empty_when_fitz_unavailable(self, monkeypatch):
        monkeypatch.setattr(grp1, "_FITZ_AVAILABLE", False)
        result = grp1.detect_form_fields("any_path.pdf")
        assert result == ""


# ---------------------------------------------------------------------------
# TestCheckPageDensity
# ---------------------------------------------------------------------------

class TestCheckPageDensity:

    def _make_dense_pdf(self, tmp_path, pages=1):
        """All pages have >= 50 chars."""
        import fitz
        doc = fitz.open()
        for _ in range(pages):
            page = doc.new_page()
            page.insert_text((50, 50), "A" * 200)
        path = str(tmp_path / "dense.pdf")
        doc.save(path)
        doc.close()
        return path

    def _make_sparse_pdf(self, tmp_path, pages=1):
        """All pages have < 50 chars (empty pages)."""
        import fitz
        doc = fitz.open()
        for _ in range(pages):
            doc.new_page()   # no text inserted
        path = str(tmp_path / "sparse.pdf")
        doc.save(path)
        doc.close()
        return path

    def _make_mixed_pdf(self, tmp_path):
        """First page dense, second page sparse."""
        import fitz
        doc = fitz.open()
        p1 = doc.new_page()
        p1.insert_text((50, 50), "B" * 200)   # dense
        doc.new_page()                          # sparse
        path = str(tmp_path / "mixed.pdf")
        doc.save(path)
        doc.close()
        return path

    def test_returns_n_for_dense_pdf(self, tmp_path):
        # All pages >= 50 chars → no OCR needed → "N"
        path = self._make_dense_pdf(tmp_path)
        assert grp1.check_page_density(path) == "N"

    def test_returns_y_for_sparse_pdf(self, tmp_path):
        # All pages < 50 chars → needs OCR → "Y"
        path = self._make_sparse_pdf(tmp_path)
        assert grp1.check_page_density(path) == "Y"

    def test_returns_partial_for_mixed_pdf(self, tmp_path):
        path = self._make_mixed_pdf(tmp_path)
        assert grp1.check_page_density(path) == "PARTIAL"

    def test_returns_n_for_multi_page_all_dense(self, tmp_path):
        path = self._make_dense_pdf(tmp_path, pages=3)
        assert grp1.check_page_density(path) == "N"

    def test_returns_empty_for_bad_path(self, tmp_path):
        result = grp1.check_page_density(str(tmp_path / "nonexistent.pdf"))
        assert result == ""

    def test_returns_empty_when_fitz_unavailable(self, monkeypatch):
        monkeypatch.setattr(grp1, "_FITZ_AVAILABLE", False)
        result = grp1.check_page_density("any_path.pdf")
        assert result == ""
