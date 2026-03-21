"""
Tests for drive_scout_server.py

Uses FastAPI TestClient for HTTP endpoint tests.
PowerShell subprocess calls are NOT tested directly.
WebSocket live-streaming is NOT tested (integration-level).
asyncio.create_task is patched in scan-start tests to prevent
real PowerShell scans from running during the test suite.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import drive_scout_server as dss

client = TestClient(dss.app)


# ---------------------------------------------------------------------------
# Fixture — clear module-level scan state between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clear_scans():
    dss.scans.clear()
    dss.active_procs.clear()
    yield
    dss.scans.clear()
    dss.active_procs.clear()


# ---------------------------------------------------------------------------
# TestGetDrives
# ---------------------------------------------------------------------------
class TestGetDrives:
    def test_returns_drives_key(self):
        response = client.get("/api/drives")
        assert response.status_code == 200
        assert "drives" in response.json()

    def test_drives_is_list(self):
        data = client.get("/api/drives").json()
        assert isinstance(data["drives"], list)

    def test_c_drive_present(self):
        data = client.get("/api/drives").json()
        paths = [d["path"] for d in data["drives"]]
        assert any("C:" in p for p in paths)

    def test_each_entry_has_path_and_name(self):
        data = client.get("/api/drives").json()
        for drive in data["drives"]:
            assert "path" in drive
            assert "name" in drive


# ---------------------------------------------------------------------------
# TestGetTree
# ---------------------------------------------------------------------------
class TestGetTree:
    def test_valid_path_returns_children_list(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        response = client.get(f"/api/tree?path={tmp_path}")
        assert response.status_code == 200
        data = response.json()
        assert "children" in data
        names = [c["name"] for c in data["children"]]
        assert "subdir" in names

    def test_children_sorted_by_name(self, tmp_path):
        (tmp_path / "zzz").mkdir()
        (tmp_path / "aaa").mkdir()
        (tmp_path / "mmm").mkdir()
        data = client.get(f"/api/tree?path={tmp_path}").json()
        names = [c["name"] for c in data["children"]]
        assert names == sorted(names, key=lambda x: x.lower())

    def test_each_child_has_path_name_has_children(self, tmp_path):
        (tmp_path / "sub").mkdir()
        data = client.get(f"/api/tree?path={tmp_path}").json()
        for child in data["children"]:
            assert "path" in child
            assert "name" in child
            assert "has_children" in child

    def test_permission_denied_returns_empty_children_and_error(self):
        with patch("os.scandir", side_effect=PermissionError("denied")):
            data = client.get("/api/tree?path=C:\\SomeDir").json()
        assert data["children"] == []
        assert "error" in data

    def test_nonexistent_path_returns_error(self):
        data = client.get("/api/tree?path=C:\\DOES_NOT_EXIST_XYZ999").json()
        assert "error" in data
        assert data["children"] == []

    def test_empty_dir_returns_empty_children(self, tmp_path):
        data = client.get(f"/api/tree?path={tmp_path}").json()
        assert data["children"] == []


# ---------------------------------------------------------------------------
# TestNlParse
# ---------------------------------------------------------------------------
class TestNlParse:
    def test_depth_extracted(self):
        data = client.post("/api/nl_parse", json={"text": "scan 2 levels deep"}).json()
        assert data["depth"] == 2

    def test_depth_three(self):
        data = client.post("/api/nl_parse", json={"text": "go 3 levels deep"}).json()
        assert data["depth"] == 3

    def test_files_keyword_sets_scan_type_files(self):
        data = client.post("/api/nl_parse", json={"text": "scan files here"}).json()
        assert data["scan_type"] == "files"

    def test_no_files_keyword_gives_dirs(self):
        data = client.post("/api/nl_parse", json={"text": "scan folders"}).json()
        assert data["scan_type"] == "dirs"

    def test_exclude_extracted(self):
        data = client.post("/api/nl_parse", json={"text": "scan users except AppData"}).json()
        assert any("appdata" in e.lower() for e in data["exclude"])

    def test_unknown_keyword_no_crash(self):
        response = client.post("/api/nl_parse", json={"text": "xyz_unknown_keyword_999"})
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data

    def test_summary_field_present(self):
        data = client.post("/api/nl_parse", json={"text": "scan files"}).json()
        assert "summary" in data

    def test_raw_field_echoes_input(self):
        data = client.post("/api/nl_parse", json={"text": "hello world"}).json()
        assert data["raw"] == "hello world"


# ---------------------------------------------------------------------------
# TestScanStartStop
# ---------------------------------------------------------------------------
class TestScanStartStop:
    def test_start_returns_scan_id(self):
        with patch("asyncio.create_task", side_effect=lambda coro: coro.close()):
            response = client.post("/api/scan/start",
                                   json={"paths": ["C:\\"], "scan_type": "dirs"})
        assert response.status_code == 200
        data = response.json()
        assert "scan_id" in data

    def test_start_returns_scan_summary(self):
        with patch("asyncio.create_task", side_effect=lambda coro: coro.close()):
            data = client.post("/api/scan/start",
                               json={"paths": ["C:\\"], "scan_type": "dirs"}).json()
        assert "scan" in data
        assert data["scan"]["status"] == "queued"

    def test_start_empty_paths_returns_400(self):
        response = client.post("/api/scan/start", json={"paths": [], "scan_type": "dirs"})
        assert response.status_code == 400

    def test_stop_known_scan_id_returns_ok(self):
        with patch("asyncio.create_task", side_effect=lambda coro: coro.close()):
            scan_id = client.post("/api/scan/start",
                                  json={"paths": ["C:\\"], "scan_type": "dirs"}).json()["scan_id"]
        response = client.post("/api/scan/stop", json={"scan_id": scan_id})
        assert response.json()["ok"] is True

    def test_stop_unknown_scan_id_no_crash(self):
        response = client.post("/api/scan/stop", json={"scan_id": "XXXXXXXX"})
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_scan_type_preserved(self):
        with patch("asyncio.create_task", side_effect=lambda coro: coro.close()):
            data = client.post("/api/scan/start",
                               json={"paths": ["C:\\"], "scan_type": "files"}).json()
        assert data["scan"]["scan_type"] == "files"


# ---------------------------------------------------------------------------
# TestGetScans
# ---------------------------------------------------------------------------
class TestGetScans:
    def test_returns_scans_key(self):
        data = client.get("/api/scans").json()
        assert "scans" in data

    def test_scans_is_list(self):
        data = client.get("/api/scans").json()
        assert isinstance(data["scans"], list)

    def test_started_scan_appears_in_list(self):
        with patch("asyncio.create_task", side_effect=lambda coro: coro.close()):
            scan_id = client.post("/api/scan/start",
                                  json={"paths": ["C:\\"], "scan_type": "dirs"}).json()["scan_id"]
        scans = client.get("/api/scans").json()["scans"]
        ids = [s["id"] for s in scans]
        assert scan_id in ids

    def test_empty_before_any_scan(self):
        data = client.get("/api/scans").json()
        assert data["scans"] == []


# ---------------------------------------------------------------------------
# TestScanSummary  (unit-tests the pure scan_summary() function)
# ---------------------------------------------------------------------------
class TestScanSummary:
    def _record(self, start=None, end=None, status="done"):
        return {
            "id": "TESTID",
            "paths": ["C:\\"],
            "scan_type": "dirs",
            "status": status,
            "count": 0,
            "start_time": start,
            "end_time": end,
            "error": None,
        }

    def test_no_start_time_elapsed_is_empty(self):
        result = dss.scan_summary(self._record())
        assert result["elapsed"] == ""

    def test_elapsed_65_seconds_formatted_1_05(self):
        now = datetime.now()
        start = (now - timedelta(seconds=65)).isoformat()
        end = now.isoformat()
        result = dss.scan_summary(self._record(start=start, end=end))
        assert result["elapsed"] == "1:05"

    def test_elapsed_3600_seconds_formatted_60_00(self):
        now = datetime.now()
        start = (now - timedelta(seconds=3600)).isoformat()
        end = now.isoformat()
        result = dss.scan_summary(self._record(start=start, end=end))
        assert result["elapsed"] == "60:00"

    def test_elapsed_zero_seconds_formatted_0_00(self):
        now = datetime.now()
        t = now.isoformat()
        result = dss.scan_summary(self._record(start=t, end=t))
        assert result["elapsed"] == "0:00"

    def test_summary_contains_required_keys(self):
        result = dss.scan_summary(self._record())
        for key in ("id", "paths", "scan_type", "status", "count", "elapsed"):
            assert key in result
