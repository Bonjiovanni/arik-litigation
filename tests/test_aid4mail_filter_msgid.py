"""
Tests for the pure-Python helper functions in filter_by_rfc_message_id_csv.flt.py.

The filter script itself runs inside Aid4Mail's embedded Python runtime (a4m_* variables),
so we can't import the full script. Instead we extract and test the four standalone functions:
  - normalize_message_id
  - extract_message_id_from_header
  - load_settings
  - load_message_id_csv
"""

import csv
import configparser
import os
import re
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Inline copies of the functions under test.
# These are identical to the script; if the script changes, update here.
# (We can't import the .flt.py directly because it references a4m_* globals.)
# ---------------------------------------------------------------------------

def normalize_message_id(value):
    if value is None:
        return ""
    msgid = str(value).strip().lower()
    if msgid.startswith("message-id:"):
        msgid = msgid[len("message-id:"):].strip()
    if msgid.startswith("<") and msgid.endswith(">") and len(msgid) >= 2:
        msgid = msgid[1:-1].strip()
    if not msgid:
        return ""
    return "<" + msgid + ">"


def extract_message_id_from_header(header_text):
    if not header_text:
        return ""
    match = re.search(
        r'(?im)^message-id:\s*(.+(?:\r?\n[ \t].+)*)',
        header_text
    )
    if not match:
        return ""
    raw_value = match.group(1)
    raw_value = re.sub(r'\r?\n[ \t]+', ' ', raw_value).strip()
    return normalize_message_id(raw_value)


SCRIPT_NAME = "filter_by_rfc_message_id_csv.flt.py"
DEFAULT_CSV_FILE = r"C:\Temp\message_ids.csv"
DEFAULT_LOG_FILE = "message_id_results.csv"


def load_settings(settings_path):
    result = {"csv_file": DEFAULT_CSV_FILE, "log_file": DEFAULT_LOG_FILE}
    try:
        if settings_path and os.path.exists(settings_path):
            config = configparser.ConfigParser()
            config.read(settings_path, encoding="utf-8")
            csv_file = config.get(SCRIPT_NAME, "CSV_FILE", fallback=DEFAULT_CSV_FILE).strip()
            log_file = config.get(SCRIPT_NAME, "LOG_FILE", fallback=DEFAULT_LOG_FILE).strip()
            if csv_file:
                result["csv_file"] = csv_file
            if log_file:
                result["log_file"] = log_file
    except Exception:
        pass
    return result


def load_message_id_csv(path):
    ids = []
    seen = set()
    if not os.path.exists(path):
        return ids, "CSV file not found: " + path
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row_number, row in enumerate(reader, start=1):
                if not row:
                    continue
                value = row[0].strip()
                if not value:
                    continue
                if value.startswith("#") or value.startswith(";"):
                    continue
                if row_number == 1 and "message" in value.lower():
                    continue
                normalized = normalize_message_id(value)
                if not normalized:
                    continue
                if normalized in seen:
                    continue
                seen.add(normalized)
                ids.append(normalized)
    except Exception as exc:
        return [], "Unable to read CSV file: " + str(exc)
    return ids, ""


# ===========================================================================
# Tests
# ===========================================================================


class TestNormalizeMessageId:

    def test_standard_angle_brackets(self):
        assert normalize_message_id("<abc@example.com>") == "<abc@example.com>"

    def test_no_angle_brackets(self):
        assert normalize_message_id("abc@example.com") == "<abc@example.com>"

    def test_case_insensitive(self):
        assert normalize_message_id("<ABC@Example.COM>") == "<abc@example.com>"

    def test_strips_whitespace(self):
        assert normalize_message_id("  <abc@example.com>  ") == "<abc@example.com>"

    def test_handles_pasted_header_line(self):
        assert normalize_message_id("Message-ID: <abc@example.com>") == "<abc@example.com>"

    def test_none_returns_empty(self):
        assert normalize_message_id(None) == ""

    def test_empty_string_returns_empty(self):
        assert normalize_message_id("") == ""

    def test_whitespace_only_returns_empty(self):
        assert normalize_message_id("   ") == ""

    def test_just_angle_brackets_returns_empty(self):
        assert normalize_message_id("<>") == ""

    def test_preserves_complex_gmail_id(self):
        gmail_id = "<CABx+XJ3kz_ZRo=example@mail.gmail.com>"
        result = normalize_message_id(gmail_id)
        assert result == "<cabx+xj3kz_zro=example@mail.gmail.com>"


class TestExtractMessageIdFromHeader:

    def test_standard_header(self):
        header = "From: alice@example.com\r\nMessage-ID: <abc@example.com>\r\nSubject: Hi\r\n"
        assert extract_message_id_from_header(header) == "<abc@example.com>"

    def test_folded_header(self):
        header = "From: alice@example.com\r\nMessage-ID:\r\n <abc@example.com>\r\nSubject: Hi\r\n"
        assert extract_message_id_from_header(header) == "<abc@example.com>"

    def test_missing_message_id(self):
        header = "From: alice@example.com\r\nSubject: Hi\r\n"
        assert extract_message_id_from_header(header) == ""

    def test_empty_header(self):
        assert extract_message_id_from_header("") == ""

    def test_none_header(self):
        assert extract_message_id_from_header(None) == ""

    def test_case_insensitive_field_name(self):
        header = "from: alice@example.com\r\nmessage-id: <abc@example.com>\r\n"
        assert extract_message_id_from_header(header) == "<abc@example.com>"

    def test_message_id_at_start_of_header(self):
        header = "Message-ID: <first@example.com>\r\nFrom: alice@example.com\r\n"
        assert extract_message_id_from_header(header) == "<first@example.com>"


class TestLoadSettings:

    def test_reads_csv_file_setting(self, tmp_path):
        ini = tmp_path / "settings.ini"
        ini.write_text(
            f"[{SCRIPT_NAME}]\nCSV_FILE=C:\\Cases\\ids.csv\nLOG_FILE=results.csv\n",
            encoding="utf-8"
        )
        result = load_settings(str(ini))
        assert result["csv_file"] == r"C:\Cases\ids.csv"
        assert result["log_file"] == "results.csv"

    def test_defaults_when_file_missing(self):
        result = load_settings(r"C:\nonexistent\settings.ini")
        assert result["csv_file"] == DEFAULT_CSV_FILE
        assert result["log_file"] == DEFAULT_LOG_FILE

    def test_defaults_when_section_missing(self, tmp_path):
        ini = tmp_path / "settings.ini"
        ini.write_text("[other_script.flt.py]\nFOO=bar\n", encoding="utf-8")
        result = load_settings(str(ini))
        assert result["csv_file"] == DEFAULT_CSV_FILE

    def test_defaults_when_path_is_none(self):
        result = load_settings(None)
        assert result["csv_file"] == DEFAULT_CSV_FILE


class TestLoadMessageIdCsv:

    def test_loads_ids_with_header_row(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_text(
            "MessageID\n<abc@example.com>\n<def@example.com>\n",
            encoding="utf-8"
        )
        ids, err = load_message_id_csv(str(csv_file))
        assert err == ""
        assert len(ids) == 2
        assert "<abc@example.com>" in ids
        assert "<def@example.com>" in ids

    def test_loads_ids_without_header_row(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_text(
            "<abc@example.com>\n<def@example.com>\n",
            encoding="utf-8"
        )
        ids, err = load_message_id_csv(str(csv_file))
        assert err == ""
        assert len(ids) == 2

    def test_skips_comment_lines(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_text(
            "MessageID\n# this is a comment\n; also a comment\n<abc@example.com>\n",
            encoding="utf-8"
        )
        ids, err = load_message_id_csv(str(csv_file))
        assert len(ids) == 1

    def test_skips_blank_lines(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_text(
            "MessageID\n\n\n<abc@example.com>\n\n",
            encoding="utf-8"
        )
        ids, err = load_message_id_csv(str(csv_file))
        assert len(ids) == 1

    def test_deduplicates(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_text(
            "MessageID\n<abc@example.com>\n<ABC@Example.com>\n",
            encoding="utf-8"
        )
        ids, err = load_message_id_csv(str(csv_file))
        assert len(ids) == 1

    def test_normalizes_without_angle_brackets(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_text(
            "MessageID\nabc@example.com\n",
            encoding="utf-8"
        )
        ids, err = load_message_id_csv(str(csv_file))
        assert ids == ["<abc@example.com>"]

    def test_error_on_missing_file(self):
        ids, err = load_message_id_csv(r"C:\nonexistent\ids.csv")
        assert ids == []
        assert "not found" in err

    def test_handles_utf8_bom(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_bytes(
            b"\xef\xbb\xbfMessageID\r\n<abc@example.com>\r\n"
        )
        ids, err = load_message_id_csv(str(csv_file))
        assert err == ""
        assert len(ids) == 1

    def test_empty_file_returns_empty_list(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_text("", encoding="utf-8")
        ids, err = load_message_id_csv(str(csv_file))
        assert ids == []
        assert err == ""

    def test_header_only_returns_empty_list(self, tmp_path):
        csv_file = tmp_path / "ids.csv"
        csv_file.write_text("MessageID\n", encoding="utf-8")
        ids, err = load_message_id_csv(str(csv_file))
        assert ids == []
        assert err == ""
