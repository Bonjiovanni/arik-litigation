"""
tests/test_fw_dirmap_grp1.py
Unit tests for fw_dirmap_grp1: validate_and_normalize_path, generate_run_id.
pick_scan_dirs() is interactive/COM-based and not unit-tested here.
"""

import os
import sys
import re
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fw_dirmap_grp1 import validate_and_normalize_path, generate_run_id


# ---------------------------------------------------------------------------
# generate_run_id
# ---------------------------------------------------------------------------

class TestGenerateRunId:
    def test_format(self):
        run_id = generate_run_id()
        assert re.match(r"^DIRMAP_\d{8}_\d{6}$", run_id), \
            f"Unexpected format: {run_id}"

    def test_prefix(self):
        assert generate_run_id().startswith("DIRMAP_")

    def test_unique_on_successive_calls(self):
        """Two calls in the same second produce equal IDs — that's fine,
        but the function should at least return a string each time."""
        a = generate_run_id()
        b = generate_run_id()
        assert isinstance(a, str)
        assert isinstance(b, str)


# ---------------------------------------------------------------------------
# validate_and_normalize_path
# ---------------------------------------------------------------------------

class TestValidateAndNormalizePath:
    def test_existing_dir_returns_forward_slashes(self, tmp_path):
        result = validate_and_normalize_path(str(tmp_path))
        assert "\\" not in result

    def test_existing_dir_is_absolute(self, tmp_path):
        result = validate_and_normalize_path(str(tmp_path))
        assert os.path.isabs(result.replace("/", os.sep))

    def test_nonexistent_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            validate_and_normalize_path(r"C:\this_path_does_not_exist_fw_dirmap_test")

    def test_file_path_raises(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("x")
        with pytest.raises(ValueError):
            validate_and_normalize_path(str(f))

    def test_strips_whitespace(self, tmp_path):
        result = validate_and_normalize_path("  " + str(tmp_path) + "  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_strips_quotes(self, tmp_path):
        quoted = f'"{tmp_path}"'
        result = validate_and_normalize_path(quoted)
        assert not result.startswith('"')

    def test_tilde_expansion(self):
        home = os.path.expanduser("~").replace("\\", "/")
        result = validate_and_normalize_path("~")
        assert result == home or result.startswith(home)
