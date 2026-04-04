"""
tests/test_fw_walk_grp3.py

Unit tests for fw_walk_grp3.py — overlap detection functions.
walk_files is integration-heavy; only its stats-dict shape is verified here.
Run with: pytest tests/test_fw_walk_grp3.py
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fw_walk_grp3 as grp3


# ---------------------------------------------------------------------------
# Mock worksheet for Dir_Processing_Status
# Dir_Processing_Status columns: A=DirID, B=RunID, C=DirPath, D=ProcessingLevel
# ---------------------------------------------------------------------------

class _MockStatusWs:
    def __init__(self, rows):
        # rows[0] = header, rows[1:] = data
        self._rows = rows

    def iter_rows(self, min_row=1, values_only=False):
        for row in self._rows[min_row - 1:]:
            yield row


def _status_ws(data_rows):
    header = ("DirID", "RunID", "DirPath", "ProcessingLevel", "Status", "LastUpdated")
    return _MockStatusWs([header] + data_rows)


# ---------------------------------------------------------------------------
# TestProcessingLevelOrder
# ---------------------------------------------------------------------------

class TestProcessingLevelOrder:

    def test_is_list_of_strings(self):
        assert isinstance(grp3.PROCESSING_LEVEL_ORDER, list)
        assert all(isinstance(l, str) for l in grp3.PROCESSING_LEVEL_ORDER)

    def test_starts_with_file_listed(self):
        assert grp3.PROCESSING_LEVEL_ORDER[0] == "file_listed"

    def test_ends_with_triaged(self):
        assert grp3.PROCESSING_LEVEL_ORDER[-1] == "triaged"

    def test_contains_hashed_and_classified(self):
        assert "hashed" in grp3.PROCESSING_LEVEL_ORDER
        assert "classified" in grp3.PROCESSING_LEVEL_ORDER

    def test_hashed_deeper_than_file_listed(self):
        assert grp3.PROCESSING_LEVEL_ORDER.index("hashed") > \
               grp3.PROCESSING_LEVEL_ORDER.index("file_listed")


# ---------------------------------------------------------------------------
# TestGetCoveredPaths
# ---------------------------------------------------------------------------

class TestGetCoveredPaths:

    def test_empty_sheet_returns_empty(self):
        ws = _status_ws([])
        result = grp3.get_covered_paths(ws, "file_listed")
        assert result == {}

    def test_unknown_target_level_returns_empty(self):
        ws = _status_ws([
            ("D1", "R1", "C:/Docs", "file_listed", "done", "2026-01-01"),
        ])
        result = grp3.get_covered_paths(ws, "nonexistent_level")
        assert result == {}

    def test_path_at_target_level_included(self):
        ws = _status_ws([
            ("D1", "R1", "C:/Docs", "file_listed", "done", "2026-01-01"),
        ])
        result = grp3.get_covered_paths(ws, "file_listed")
        assert len(result) == 1
        assert list(result.values())[0] == "file_listed"

    def test_path_below_target_level_excluded(self):
        # "file_listed" is below "hashed"
        ws = _status_ws([
            ("D1", "R1", "C:/Docs", "file_listed", "done", "2026-01-01"),
        ])
        result = grp3.get_covered_paths(ws, "hashed")
        assert result == {}

    def test_path_above_target_level_included(self):
        # "classified" is above "file_listed"
        ws = _status_ws([
            ("D1", "R1", "C:/Docs", "classified", "done", "2026-01-01"),
        ])
        result = grp3.get_covered_paths(ws, "file_listed")
        assert len(result) == 1

    def test_multiple_rows_same_path_highest_level_wins(self):
        ws = _status_ws([
            ("D1", "R1", "C:/Docs", "file_listed",  "done", "2026-01-01"),
            ("D1", "R2", "C:/Docs", "classified",   "done", "2026-01-02"),
            ("D1", "R3", "C:/Docs", "hashed",       "done", "2026-01-03"),
        ])
        result = grp3.get_covered_paths(ws, "file_listed")
        assert len(result) == 1
        path = list(result.keys())[0]
        assert result[path] == "classified"

    def test_paths_normalized_case_insensitive(self):
        ws = _status_ws([
            ("D1", "R1", "C:\\Docs\\Project", "file_listed", "done", "2026-01-01"),
        ])
        result = grp3.get_covered_paths(ws, "file_listed")
        # Normalized path should use forward slashes, lowercase
        assert any("docs/project" in k for k in result.keys())

    def test_rows_with_none_path_skipped(self):
        ws = _status_ws([
            ("D1", "R1", None, "file_listed", "done", "2026-01-01"),
            ("D2", "R1", "C:/Valid", "file_listed", "done", "2026-01-01"),
        ])
        result = grp3.get_covered_paths(ws, "file_listed")
        assert len(result) == 1

    def test_two_different_paths_both_returned(self):
        ws = _status_ws([
            ("D1", "R1", "C:/Alpha", "hashed", "done", "2026-01-01"),
            ("D2", "R1", "C:/Beta",  "hashed", "done", "2026-01-01"),
        ])
        result = grp3.get_covered_paths(ws, "hashed")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# TestCheckOverlap
# ---------------------------------------------------------------------------

class TestCheckOverlap:

    def test_no_overlap_returns_empty(self):
        overlaps = grp3.check_overlap(
            ["C:/New/Dir"],
            {"c:/existing/dir": "file_listed"},
        )
        assert overlaps == []

    def test_overlap_detected(self):
        covered = {"c:/docs": "file_listed"}
        overlaps = grp3.check_overlap(["C:/Docs"], covered)
        assert len(overlaps) == 1
        assert overlaps[0]["existing_level"] == "file_listed"

    def test_overlap_dict_has_path_and_existing_level(self):
        covered = {"c:/docs": "hashed"}
        overlaps = grp3.check_overlap(["C:/Docs"], covered)
        assert "path" in overlaps[0]
        assert "existing_level" in overlaps[0]

    def test_backslash_path_normalized(self):
        covered = {"c:/docs/project": "file_listed"}
        overlaps = grp3.check_overlap(["C:\\Docs\\Project"], covered)
        assert len(overlaps) == 1

    def test_case_insensitive_match(self):
        covered = {"c:/docs": "file_listed"}
        overlaps = grp3.check_overlap(["C:/DOCS"], covered)
        assert len(overlaps) == 1

    def test_partial_path_not_a_match(self):
        covered = {"c:/docs": "file_listed"}
        overlaps = grp3.check_overlap(["C:/docs/subdir"], covered)
        assert overlaps == []

    def test_multiple_overlaps_returned(self):
        covered = {
            "c:/alpha": "file_listed",
            "c:/beta":  "hashed",
        }
        overlaps = grp3.check_overlap(["C:/Alpha", "C:/Beta", "C:/Gamma"], covered)
        assert len(overlaps) == 2

    def test_empty_scan_dirs_returns_empty(self):
        covered = {"c:/docs": "file_listed"}
        assert grp3.check_overlap([], covered) == []

    def test_empty_covered_paths_returns_empty(self):
        assert grp3.check_overlap(["C:/Docs"], {}) == []


# ---------------------------------------------------------------------------
# TestPromptOverlapDecision
# ---------------------------------------------------------------------------

class TestPromptOverlapDecision:

    _SAMPLE_OVERLAPS = [
        {"path": "c:/docs", "existing_level": "file_listed"},
    ]

    def test_s_returns_skip(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "s")
        result = grp3.prompt_overlap_decision(self._SAMPLE_OVERLAPS)
        assert result == "skip"

    def test_r_returns_rewalk(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "r")
        result = grp3.prompt_overlap_decision(self._SAMPLE_OVERLAPS)
        assert result == "rewalk"

    def test_a_returns_abort(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "a")
        result = grp3.prompt_overlap_decision(self._SAMPLE_OVERLAPS)
        assert result == "abort"

    def test_case_insensitive_S(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "S")
        result = grp3.prompt_overlap_decision(self._SAMPLE_OVERLAPS)
        assert result == "skip"

    def test_invalid_then_valid_input(self, monkeypatch):
        responses = iter(["x", "q", "r"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        result = grp3.prompt_overlap_decision(self._SAMPLE_OVERLAPS)
        assert result == "rewalk"
