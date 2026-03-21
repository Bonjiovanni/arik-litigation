"""
Tests for fw_file_inventory.py

Pure-function tests only — no PowerShell or real filesystem scans.
merge_and_write() is tested with synthetic temp CSV files.
"""

import csv
import os
from pathlib import Path

import pytest

import fw_file_inventory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PS_HEADERS = ["FullName", "DirectoryName", "Name", "Extension", "Length", "LastWriteDate"]


def _make_ps_csv(tmp_path, name, rows):
    """Write a synthetic PowerShell-output CSV (utf-8-sig encoding)."""
    f = tmp_path / name
    with open(f, "w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=_PS_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return str(f)


def _row(full_path, size="100", ext=".txt", date="2023-01-15"):
    """Build a minimal PowerShell row dict from a full path."""
    p = Path(full_path)
    return {
        "FullName":       full_path,
        "DirectoryName":  str(p.parent),
        "Name":           p.name,
        "Extension":      ext,
        "Length":         size,
        "LastWriteDate":  date,
    }


# ---------------------------------------------------------------------------
# TestIsExcluded
# ---------------------------------------------------------------------------
class TestIsExcluded:
    def test_exact_match(self):
        assert fw_file_inventory.is_excluded("C:\\Windows", ["C:\\Windows"])

    def test_prefix_match(self):
        assert fw_file_inventory.is_excluded("C:\\Windows\\System32", ["C:\\Windows"])

    def test_case_insensitive(self):
        assert fw_file_inventory.is_excluded("c:\\windows\\system32", ["C:\\Windows"])

    def test_non_match_passes(self):
        assert not fw_file_inventory.is_excluded("C:\\Users", ["C:\\Windows"])

    def test_partial_name_not_excluded(self):
        assert not fw_file_inventory.is_excluded("C:\\Win", ["C:\\Windows"])

    def test_empty_excludes(self):
        assert not fw_file_inventory.is_excluded("C:\\Windows", [])

    def test_empty_string_in_excludes_ignored(self):
        assert not fw_file_inventory.is_excluded("C:\\Windows", [""])


# ---------------------------------------------------------------------------
# TestExpandToSubdirs
# ---------------------------------------------------------------------------
class TestExpandToSubdirs:
    def test_root_with_subdirs_includes_subdirs(self, tmp_path):
        sub = tmp_path / "sub1"
        sub.mkdir()
        result = fw_file_inventory.expand_to_subdirs([str(tmp_path)], [])
        assert str(sub) in result

    def test_root_with_subdirs_adds_shallow_sentinel(self, tmp_path):
        (tmp_path / "sub1").mkdir()
        result = fw_file_inventory.expand_to_subdirs([str(tmp_path)], [])
        assert str(tmp_path) + "|shallow" in result

    def test_root_without_subdirs_returned_as_is(self, tmp_path):
        result = fw_file_inventory.expand_to_subdirs([str(tmp_path)], [])
        assert result == [str(tmp_path)]

    def test_excluded_root_not_in_result(self, tmp_path):
        result = fw_file_inventory.expand_to_subdirs([str(tmp_path)], [str(tmp_path)])
        assert result == []

    def test_excluded_subdir_not_in_result(self, tmp_path):
        keep = tmp_path / "keep"
        skip = tmp_path / "skip"
        keep.mkdir(); skip.mkdir()
        result = fw_file_inventory.expand_to_subdirs([str(tmp_path)], [str(skip)])
        assert str(skip) not in result
        assert str(keep) in result

    def test_permission_error_on_root_returns_root_as_is(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "listdir", lambda p: (_ for _ in ()).throw(PermissionError()))
        result = fw_file_inventory.expand_to_subdirs([str(tmp_path)], [])
        assert result == [str(tmp_path)]


# ---------------------------------------------------------------------------
# TestMergeAndWrite
# ---------------------------------------------------------------------------
class TestMergeAndWrite:
    def test_basic_output_has_correct_headers(self, tmp_path):
        csv_path = _make_ps_csv(tmp_path, "f.csv", [])
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv_path], [], str(output))
        with open(output, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == fw_file_inventory.FIELDNAMES

    def test_row_written_correctly(self, tmp_path):
        rows = [_row(str(tmp_path / "file.pdf"), size="500", ext=".pdf")]
        csv_path = _make_ps_csv(tmp_path, "f.csv", rows)
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv_path], [], str(output))
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert len(result) == 1
        assert result[0]["filename"] == "file.pdf"
        assert result[0]["size_bytes"] == "500"

    def test_deduplication_across_two_csvs(self, tmp_path):
        fp = str(tmp_path / "dup.txt")
        rows = [_row(fp)]
        csv1 = _make_ps_csv(tmp_path, "f1.csv", rows)
        csv2 = _make_ps_csv(tmp_path, "f2.csv", rows)
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv1, csv2], [], str(output))
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert len(result) == 1

    def test_deduplication_case_insensitive(self, tmp_path):
        rows_lower = [_row(str(tmp_path / "file.txt"))]
        rows_upper = [_row(str(tmp_path / "FILE.TXT"))]
        csv1 = _make_ps_csv(tmp_path, "f1.csv", rows_lower)
        csv2 = _make_ps_csv(tmp_path, "f2.csv", rows_upper)
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv1, csv2], [], str(output))
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert len(result) == 1

    def test_excluded_paths_filtered(self, tmp_path):
        keep_dir = tmp_path / "keep"
        skip_dir = tmp_path / "skip"
        keep_dir.mkdir(); skip_dir.mkdir()
        rows = [
            _row(str(keep_dir / "keep.txt")),
            _row(str(skip_dir / "skip.txt")),
        ]
        csv_path = _make_ps_csv(tmp_path, "f.csv", rows)
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv_path], [str(skip_dir)], str(output))
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert len(result) == 1
        assert "keep.txt" in result[0]["filename"]

    def test_extension_lowercased(self, tmp_path):
        rows = [_row(str(tmp_path / "doc.PDF"), ext=".PDF")]
        csv_path = _make_ps_csv(tmp_path, "f.csv", rows)
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv_path], [], str(output))
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert result[0]["extension"] == ".pdf"

    def test_missing_length_defaults_to_zero(self, tmp_path):
        row = _row(str(tmp_path / "file.txt"), size="")
        csv_path = _make_ps_csv(tmp_path, "f.csv", [row])
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv_path], [], str(output))
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert result[0]["size_bytes"] == "0"

    def test_missing_temp_csv_skipped(self, tmp_path):
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write(
            [str(tmp_path / "nonexistent.csv")], [], str(output)
        )
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert len(result) == 0

    def test_directory_field_is_parent(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        rows = [_row(str(sub / "file.txt"))]
        csv_path = _make_ps_csv(tmp_path, "f.csv", rows)
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv_path], [], str(output))
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert result[0]["directory"] == str(sub)

    def test_modified_date_preserved(self, tmp_path):
        rows = [_row(str(tmp_path / "file.txt"), date="2024-06-15")]
        csv_path = _make_ps_csv(tmp_path, "f.csv", rows)
        output = tmp_path / "out.csv"
        fw_file_inventory.merge_and_write([csv_path], [], str(output))
        with open(output, encoding="utf-8") as f:
            result = list(csv.DictReader(f))
        assert result[0]["modified_date"] == "2024-06-15"
