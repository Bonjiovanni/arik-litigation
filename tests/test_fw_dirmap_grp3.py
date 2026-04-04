"""
tests/test_fw_dirmap_grp3.py
Unit tests for fw_dirmap_grp3: build_dir_records.
Uses dependency injection to avoid real filesystem calls.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fw_dirmap_grp3 import build_dir_records


# ---------------------------------------------------------------------------
# Fake dependency helpers
# ---------------------------------------------------------------------------

def _fake_validate(raw):
    return raw.replace("\\", "/").rstrip("/")

def _fake_detect_store(path):
    return "Local"

def _fake_count_contents(path):
    return (3, 2)

def _fake_walk(root, recursive, max_depth):
    """Yields a small fixed tree regardless of root."""
    norm = root.replace("\\", "/").rstrip("/")
    yield (norm, 0)
    yield (norm + "/sub1", 1)
    yield (norm + "/sub1/sub1a", 2)

def _fake_walk_single(root, recursive, max_depth):
    norm = root.replace("\\", "/").rstrip("/")
    yield (norm, 0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildDirRecords:
    def _call(self, roots=None, recursive=True, max_depth=None, run_id="TEST_001",
              walk_fn=_fake_walk):
        if roots is None:
            roots = ["C:/TestRoot"]
        return build_dir_records(
            roots=roots,
            recursive=recursive,
            max_depth=max_depth,
            run_id=run_id,
            _validate=_fake_validate,
            _detect_store=_fake_detect_store,
            _count_contents=_fake_count_contents,
            _walk=walk_fn,
        )

    def test_returns_list(self):
        assert isinstance(self._call(), list)

    def test_record_count_matches_walk(self):
        records = self._call()
        assert len(records) == 3  # root + sub1 + sub1a

    def test_first_record_is_root_at_depth_0(self):
        records = self._call()
        assert records[0]["depth"] == 0

    def test_dir_ids_are_sequential(self):
        records = self._call()
        ids = [r["dir_id"] for r in records]
        assert ids == ["D001", "D002", "D003"]

    def test_dir_ids_dont_reset_between_roots(self):
        records = self._call(roots=["C:/RootA", "C:/RootB"])
        ids = [r["dir_id"] for r in records]
        # 3 entries per root = 6 total, IDs D001-D006
        assert ids[0] == "D001"
        assert ids[3] == "D004"
        assert ids[5] == "D006"

    def test_relative_dir_is_dot_for_root(self):
        records = self._call()
        assert records[0]["relative_dir"] == "."

    def test_relative_dir_for_child(self):
        records = self._call()
        assert records[1]["relative_dir"] == "sub1"

    def test_full_path_uses_forward_slashes(self):
        records = self._call()
        for r in records:
            assert "\\" not in r["full_path"]

    def test_run_id_propagated(self):
        records = self._call(run_id="MY_RUN_ID")
        for r in records:
            assert r["run_id"] == "MY_RUN_ID"

    def test_source_store_set(self):
        records = self._call()
        for r in records:
            assert r["source_store"] == "Local"

    def test_file_count_and_subdir_count(self):
        records = self._call()
        for r in records:
            assert r["file_count"] == 3
            assert r["subdir_count"] == 2

    def test_scan_root_field(self):
        records = self._call(roots=["C:/TestRoot"])
        for r in records:
            assert r["scan_root"] == "C:/TestRoot"

    def test_dir_name_for_root_is_basename(self):
        records = self._call(roots=["C:/TestRoot"])
        assert records[0]["dir_name"] == "TestRoot"

    def test_dir_name_for_child(self):
        records = self._call()
        assert records[1]["dir_name"] == "sub1"

    def test_empty_roots_returns_empty(self):
        records = self._call(roots=[])
        assert records == []

    def test_single_root_single_dir(self):
        records = self._call(walk_fn=_fake_walk_single)
        assert len(records) == 1
        assert records[0]["depth"] == 0
        assert records[0]["dir_id"] == "D001"
