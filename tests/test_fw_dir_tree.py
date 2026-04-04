"""
Tests for fw_dir_tree.py

Pure-function tests only — no PowerShell or real filesystem scans.
build_records() is tested with synthetic temp CSV files.
"""

import csv
import os
from pathlib import Path

import pytest

import fw_dir_tree


# ---------------------------------------------------------------------------
# TestGetDepth
# ---------------------------------------------------------------------------
class TestGetDepth:
    def test_drive_root_is_zero(self):
        assert fw_dir_tree.get_depth("C:\\") == 0

    def test_one_level_deep(self):
        assert fw_dir_tree.get_depth("C:\\Users") == 1

    def test_two_levels_deep(self):
        assert fw_dir_tree.get_depth("C:\\Users\\arika") == 2

    def test_three_levels_deep(self):
        assert fw_dir_tree.get_depth("C:\\Users\\arika\\OneDrive") == 3


# ---------------------------------------------------------------------------
# TestIsExcluded
# ---------------------------------------------------------------------------
class TestIsExcluded:
    def test_exact_match(self):
        assert fw_dir_tree.is_excluded("C:\\Windows", ["C:\\Windows"])

    def test_prefix_match_child(self):
        assert fw_dir_tree.is_excluded("C:\\Windows\\System32", ["C:\\Windows"])

    def test_prefix_match_grandchild(self):
        assert fw_dir_tree.is_excluded("C:\\Windows\\System32\\drivers", ["C:\\Windows"])

    def test_case_insensitive(self):
        assert fw_dir_tree.is_excluded("c:\\windows", ["C:\\Windows"])

    def test_non_match_not_excluded(self):
        assert not fw_dir_tree.is_excluded("C:\\Users", ["C:\\Windows"])

    def test_partial_name_not_excluded(self):
        # "C:\Win" should NOT match "C:\Windows"
        assert not fw_dir_tree.is_excluded("C:\\Win", ["C:\\Windows"])

    def test_empty_excludes_list(self):
        assert not fw_dir_tree.is_excluded("C:\\Windows", [])

    def test_empty_string_in_excludes_ignored(self):
        assert not fw_dir_tree.is_excluded("C:\\Windows", [""])


# ---------------------------------------------------------------------------
# TestNormalize
# ---------------------------------------------------------------------------
class TestNormalize:
    def test_strips_leading_whitespace(self):
        result = fw_dir_tree.normalize("  C:\\Users")
        expected = str(Path("C:\\Users").resolve())
        assert result == expected

    def test_strips_trailing_whitespace(self):
        result = fw_dir_tree.normalize("C:\\Users  ")
        expected = str(Path("C:\\Users").resolve())
        assert result == expected

    def test_trailing_separator_removed(self):
        a = fw_dir_tree.normalize("C:\\Users\\")
        b = fw_dir_tree.normalize("C:\\Users")
        assert a == b

    def test_returns_string(self):
        result = fw_dir_tree.normalize("C:\\")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# TestExpandToSubdirs
# ---------------------------------------------------------------------------
class TestExpandToSubdirs:
    def test_root_with_subdirs_includes_subdirs(self, tmp_path):
        sub = tmp_path / "sub1"
        sub.mkdir()
        result = fw_dir_tree.expand_to_subdirs([str(tmp_path)], [])
        assert str(sub) in result

    def test_root_with_subdirs_adds_files_only_sentinel(self, tmp_path):
        (tmp_path / "sub1").mkdir()
        result = fw_dir_tree.expand_to_subdirs([str(tmp_path)], [])
        assert str(tmp_path) + "|files_only" in result

    def test_root_without_subdirs_included_as_is(self, tmp_path):
        # tmp_path is empty — no subdirs
        result = fw_dir_tree.expand_to_subdirs([str(tmp_path)], [])
        assert result == [str(tmp_path)]

    def test_excluded_root_not_in_result(self, tmp_path):
        result = fw_dir_tree.expand_to_subdirs([str(tmp_path)], [str(tmp_path)])
        assert result == []

    def test_excluded_subdir_not_in_result(self, tmp_path):
        sub1 = tmp_path / "keep"
        sub2 = tmp_path / "skip"
        sub1.mkdir()
        sub2.mkdir()
        result = fw_dir_tree.expand_to_subdirs([str(tmp_path)], [str(sub2)])
        assert str(sub2) not in result
        assert str(sub1) in result

    def test_permission_error_on_root_returns_root_as_is(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "listdir", lambda p: (_ for _ in ()).throw(PermissionError()))
        result = fw_dir_tree.expand_to_subdirs([str(tmp_path)], [])
        assert result == [str(tmp_path)]


# ---------------------------------------------------------------------------
# TestBuildRecords
# ---------------------------------------------------------------------------

def _write_dirs_csv(path, dir_paths):
    """Write a dirs temp CSV with FullName column (utf-8-sig, as PowerShell would)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write('"FullName"\n')
        for d in dir_paths:
            f.write(f'"{d}"\n')


def _write_files_csv(path, rows):
    """Write a files temp CSV with FullName/DirectoryName/Length columns."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write('"FullName","DirectoryName","Length"\n')
        for fp, dp, length in rows:
            f.write(f'"{fp}","{dp}","{length}"\n')


class TestBuildRecords:
    def test_direct_file_count(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        dirs_csv = tmp_path / "dirs.csv"
        files_csv = tmp_path / "files.csv"

        _write_dirs_csv(dirs_csv, [str(data_dir)])
        _write_files_csv(files_csv, [
            (str(data_dir / "a.txt"), str(data_dir), "100"),
            (str(data_dir / "b.txt"), str(data_dir), "200"),
        ])

        records = fw_dir_tree.build_records(
            [{"files": str(files_csv), "dirs": str(dirs_csv)}], []
        )
        rec = next(r for r in records if r["full_path"].lower() == str(data_dir).lower())
        assert rec["direct_file_count"] == 2

    def test_direct_size_bytes(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        dirs_csv = tmp_path / "dirs.csv"
        files_csv = tmp_path / "files.csv"

        _write_dirs_csv(dirs_csv, [str(data_dir)])
        _write_files_csv(files_csv, [
            (str(data_dir / "a.txt"), str(data_dir), "100"),
            (str(data_dir / "b.txt"), str(data_dir), "200"),
        ])

        records = fw_dir_tree.build_records(
            [{"files": str(files_csv), "dirs": str(dirs_csv)}], []
        )
        rec = next(r for r in records if r["full_path"].lower() == str(data_dir).lower())
        assert rec["direct_size_bytes"] == 300

    def test_total_count_rolls_up_to_parent(self, tmp_path):
        parent = tmp_path / "parent"
        child = parent / "child"
        parent.mkdir()
        child.mkdir()

        dirs_csv = tmp_path / "dirs.csv"
        files_csv = tmp_path / "files.csv"
        _write_dirs_csv(dirs_csv, [str(parent), str(child)])
        _write_files_csv(files_csv, [
            (str(parent / "file1.txt"), str(parent), "50"),
            (str(child / "file2.txt"), str(child), "150"),
        ])

        records = fw_dir_tree.build_records(
            [{"files": str(files_csv), "dirs": str(dirs_csv)}], []
        )
        parent_rec = next(r for r in records if r["full_path"].lower() == str(parent).lower())
        assert parent_rec["total_file_count"] == 2
        assert parent_rec["total_size_bytes"] == 200

    def test_child_direct_not_rolled_into_sibling(self, tmp_path):
        parent = tmp_path / "parent"
        child1 = parent / "child1"
        child2 = parent / "child2"
        parent.mkdir(); child1.mkdir(); child2.mkdir()

        dirs_csv = tmp_path / "dirs.csv"
        files_csv = tmp_path / "files.csv"
        _write_dirs_csv(dirs_csv, [str(parent), str(child1), str(child2)])
        _write_files_csv(files_csv, [
            (str(child1 / "f.txt"), str(child1), "100"),
        ])

        records = fw_dir_tree.build_records(
            [{"files": str(files_csv), "dirs": str(dirs_csv)}], []
        )
        child2_rec = next(r for r in records if r["full_path"].lower() == str(child2).lower())
        assert child2_rec["direct_file_count"] == 0
        assert child2_rec["total_file_count"] == 0

    def test_depth_field_set_correctly(self, tmp_path):
        child = tmp_path / "child"
        child.mkdir()

        dirs_csv = tmp_path / "dirs.csv"
        files_csv = tmp_path / "files.csv"
        _write_dirs_csv(dirs_csv, [str(child)])
        _write_files_csv(files_csv, [])

        records = fw_dir_tree.build_records(
            [{"files": str(files_csv), "dirs": str(dirs_csv)}], []
        )
        child_rec = next(r for r in records if r["full_path"].lower() == str(child).lower())
        assert child_rec["depth"] == len(child.parts) - 1

    def test_excluded_dirs_not_in_records(self, tmp_path):
        keep_dir = tmp_path / "keep"
        skip_dir = tmp_path / "skip"
        keep_dir.mkdir(); skip_dir.mkdir()

        dirs_csv = tmp_path / "dirs.csv"
        files_csv = tmp_path / "files.csv"
        _write_dirs_csv(dirs_csv, [str(keep_dir), str(skip_dir)])
        _write_files_csv(files_csv, [])

        records = fw_dir_tree.build_records(
            [{"files": str(files_csv), "dirs": str(dirs_csv)}], [str(skip_dir)]
        )
        paths_lower = [r["full_path"].lower() for r in records]
        assert str(skip_dir).lower() not in paths_lower
        assert str(keep_dir).lower() in paths_lower

    def test_empty_dir_has_zero_counts(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        dirs_csv = tmp_path / "dirs.csv"
        files_csv = tmp_path / "files.csv"
        _write_dirs_csv(dirs_csv, [str(empty_dir)])
        _write_files_csv(files_csv, [])

        records = fw_dir_tree.build_records(
            [{"files": str(files_csv), "dirs": str(dirs_csv)}], []
        )
        rec = next(r for r in records if r["full_path"].lower() == str(empty_dir).lower())
        assert rec["direct_file_count"] == 0
        assert rec["direct_size_bytes"] == 0
        assert rec["total_file_count"] == 0
        assert rec["total_size_bytes"] == 0

    def test_missing_length_defaults_to_zero(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        dirs_csv = tmp_path / "dirs.csv"
        files_csv = tmp_path / "files.csv"
        _write_dirs_csv(dirs_csv, [str(data_dir)])
        # Length is empty string
        with open(files_csv, "w", encoding="utf-8-sig", newline="") as f:
            f.write('"FullName","DirectoryName","Length"\n')
            f.write(f'"{data_dir / "f.txt"}","{data_dir}",""\n')

        records = fw_dir_tree.build_records(
            [{"files": str(files_csv), "dirs": str(dirs_csv)}], []
        )
        rec = next(r for r in records if r["full_path"].lower() == str(data_dir).lower())
        assert rec["direct_size_bytes"] == 0


# ---------------------------------------------------------------------------
# TestWriteCsv
# ---------------------------------------------------------------------------
class TestWriteCsv:
    def _sample_records(self):
        return [
            {
                "full_path": "C:\\A", "parent_path": "C:\\", "dir_name": "A",
                "depth": 1, "direct_file_count": 2, "direct_size_bytes": 512,
                "total_file_count": 4, "total_size_bytes": 1024,
            },
            {
                "full_path": "C:\\B", "parent_path": "C:\\", "dir_name": "B",
                "depth": 1, "direct_file_count": 0, "direct_size_bytes": 0,
                "total_file_count": 0, "total_size_bytes": 0,
            },
        ]

    def test_correct_headers(self, tmp_path):
        out = tmp_path / "out.csv"
        fw_dir_tree.write_csv([], str(out))
        with open(out, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == fw_dir_tree.FIELDNAMES

    def test_correct_row_count(self, tmp_path):
        out = tmp_path / "out.csv"
        fw_dir_tree.write_csv(self._sample_records(), str(out))
        with open(out, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2

    def test_field_values_correct(self, tmp_path):
        out = tmp_path / "out.csv"
        fw_dir_tree.write_csv(self._sample_records(), str(out))
        with open(out, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["full_path"] == "C:\\A"
        assert rows[0]["direct_file_count"] == "2"
        assert rows[0]["total_size_bytes"] == "1024"

    def test_empty_records_writes_header_only(self, tmp_path):
        out = tmp_path / "out.csv"
        fw_dir_tree.write_csv([], str(out))
        with open(out, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 0
