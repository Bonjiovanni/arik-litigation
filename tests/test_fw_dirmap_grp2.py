"""
tests/test_fw_dirmap_grp2.py
Unit tests for fw_dirmap_grp2: detect_source_store, count_dir_contents,
walk_directories.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fw_dirmap_grp2 import detect_source_store, count_dir_contents, walk_directories


# ---------------------------------------------------------------------------
# detect_source_store
# ---------------------------------------------------------------------------

class TestDetectSourceStore:
    def test_onedrive_segment(self):
        assert detect_source_store("C:/Users/arika/OneDrive/Documents") == "OneDrive"

    def test_onedrive_end(self):
        assert detect_source_store("C:/Users/arika/OneDrive") == "OneDrive"

    def test_onedrive_case_insensitive(self):
        assert detect_source_store("C:/users/arika/onedrive/files") == "OneDrive"

    def test_google_drive_with_space(self):
        assert detect_source_store("C:/Users/arika/Google Drive/Docs") == "GoogleDriveSync"

    def test_google_drive_no_space(self):
        assert detect_source_store("C:/Users/arika/GoogleDrive/Docs") == "GoogleDriveSync"

    def test_local(self):
        assert detect_source_store("C:/Users/arika/Documents") == "Local"

    def test_empty_string(self):
        assert detect_source_store("") == "Local"


# ---------------------------------------------------------------------------
# count_dir_contents
# ---------------------------------------------------------------------------

class TestCountDirContents:
    def test_counts_files_and_subdirs(self, tmp_path):
        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "b.txt").write_text("x")
        sub = tmp_path / "subdir"
        sub.mkdir()
        file_count, subdir_count = count_dir_contents(str(tmp_path))
        assert file_count == 2
        assert subdir_count == 1

    def test_empty_dir(self, tmp_path):
        assert count_dir_contents(str(tmp_path)) == (0, 0)

    def test_symlinks_excluded(self, tmp_path):
        real_file = tmp_path / "real.txt"
        real_file.write_text("x")
        try:
            link = tmp_path / "link.txt"
            link.symlink_to(real_file)
            file_count, _ = count_dir_contents(str(tmp_path))
            # symlink is_file(follow_symlinks=False) returns False for file symlinks
            # so only the real file should be counted
            assert file_count == 1
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this system/config")

    def test_permission_error_returns_zero_zero(self, tmp_path, monkeypatch):
        import os as _os
        original_scandir = _os.scandir

        def raising_scandir(path):
            raise PermissionError("denied")

        monkeypatch.setattr(_os, "scandir", raising_scandir)
        result = count_dir_contents(str(tmp_path))
        assert result == (0, 0)


# ---------------------------------------------------------------------------
# walk_directories
# ---------------------------------------------------------------------------

class TestWalkDirectories:
    def _build_tree(self, tmp_path):
        """
        tmp_path/
          file.txt
          sub1/
            sub1a/
          sub2/
        """
        (tmp_path / "file.txt").write_text("x")
        sub1 = tmp_path / "sub1"
        sub1.mkdir()
        (sub1 / "sub1a").mkdir()
        (tmp_path / "sub2").mkdir()
        return tmp_path

    def test_root_is_depth_zero(self, tmp_path):
        self._build_tree(tmp_path)
        paths_depths = list(walk_directories(str(tmp_path), recursive=True, max_depth=None))
        assert paths_depths[0][1] == 0

    def test_root_path_uses_forward_slashes(self, tmp_path):
        self._build_tree(tmp_path)
        root_path, _ = list(walk_directories(str(tmp_path), recursive=True, max_depth=None))[0]
        assert "\\" not in root_path

    def test_non_recursive_yields_only_depth_0_and_1(self, tmp_path):
        self._build_tree(tmp_path)
        results = list(walk_directories(str(tmp_path), recursive=False, max_depth=None))
        depths = [d for _, d in results]
        assert max(depths) == 1

    def test_recursive_yields_sub1a_at_depth_2(self, tmp_path):
        self._build_tree(tmp_path)
        results = list(walk_directories(str(tmp_path), recursive=True, max_depth=None))
        depths = [d for _, d in results]
        assert 2 in depths

    def test_max_depth_prunes(self, tmp_path):
        self._build_tree(tmp_path)
        results = list(walk_directories(str(tmp_path), recursive=True, max_depth=1))
        depths = [d for _, d in results]
        assert max(depths) == 1

    def test_all_paths_use_forward_slashes(self, tmp_path):
        self._build_tree(tmp_path)
        for path, _ in walk_directories(str(tmp_path), recursive=True, max_depth=None):
            assert "\\" not in path

    def test_immediate_children_count(self, tmp_path):
        self._build_tree(tmp_path)
        results = list(walk_directories(str(tmp_path), recursive=False, max_depth=None))
        depth_1 = [p for p, d in results if d == 1]
        assert len(depth_1) == 2  # sub1, sub2
