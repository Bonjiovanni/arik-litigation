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
        for key in ("id", "paths", "scan_type", "status", "count", "elapsed",
                    "subdir_count", "file_count", "size_bytes"):
            assert key in result

    def test_summary_subdir_count_defaults_to_zero(self):
        result = dss.scan_summary(self._record())
        assert result["subdir_count"] == 0

    def test_summary_file_count_defaults_to_zero(self):
        result = dss.scan_summary(self._record())
        assert result["file_count"] == 0

    def test_summary_size_bytes_defaults_to_zero(self):
        result = dss.scan_summary(self._record())
        assert result["size_bytes"] == 0


# ---------------------------------------------------------------------------
# TestSheetsConstants
# ---------------------------------------------------------------------------
class TestSheetsConstants:
    def test_sheets_row_limit(self):
        assert dss.SHEETS_ROW_LIMIT == 700_000

    def test_sheets_header_fields(self):
        assert dss.SHEETS_HEADER == [
            "full_path", "directory", "filename", "extension",
            "size_mb", "modified_date", "scanned_at",
        ]

    def test_sheets_header_first_field_is_sentinel(self):
        assert dss.SHEETS_HEADER[0] == "full_path"


# ---------------------------------------------------------------------------
# TestSheetsHelpers  (all Google API calls are mocked)
# ---------------------------------------------------------------------------
class TestSheetsHelpers:
    def _mock_svc(self):
        from unittest.mock import MagicMock
        return MagicMock()

    # _get_existing_sheet_titles
    def test_get_existing_sheet_titles_returns_list(self):
        svc = self._mock_svc()
        svc.spreadsheets().get().execute.return_value = {
            "sheets": [
                {"properties": {"title": "Sheet1"}},
                {"properties": {"title": "Inventory1"}},
            ]
        }
        result = dss._get_existing_sheet_titles(svc)
        assert result == ["Sheet1", "Inventory1"]

    def test_get_existing_sheet_titles_empty_spreadsheet(self):
        svc = self._mock_svc()
        svc.spreadsheets().get().execute.return_value = {"sheets": []}
        result = dss._get_existing_sheet_titles(svc)
        assert result == []

    # _create_sheet_tab
    def test_create_sheet_tab_calls_batch_update(self):
        svc = self._mock_svc()
        dss._create_sheet_tab(svc, "NewTab")
        svc.spreadsheets().batchUpdate.assert_called_once()

    def test_create_sheet_tab_correct_spreadsheet_id(self):
        svc = self._mock_svc()
        dss._create_sheet_tab(svc, "NewTab")
        kwargs = svc.spreadsheets().batchUpdate.call_args.kwargs
        assert kwargs["spreadsheetId"] == dss.SHEETS_ID

    def test_create_sheet_tab_correct_title_in_body(self):
        svc = self._mock_svc()
        dss._create_sheet_tab(svc, "Inventory5")
        kwargs = svc.spreadsheets().batchUpdate.call_args.kwargs
        title = kwargs["body"]["requests"][0]["addSheet"]["properties"]["title"]
        assert title == "Inventory5"

    # _next_tab_name
    def test_next_tab_name_empty_list_returns_inventory1(self):
        assert dss._next_tab_name([]) == "Inventory1"

    def test_next_tab_name_inventory1_exists_returns_inventory2(self):
        assert dss._next_tab_name(["Inventory1"]) == "Inventory2"

    def test_next_tab_name_sequential(self):
        existing = ["Inventory1", "Inventory2"]
        assert dss._next_tab_name(existing) == "Inventory3"

    def test_next_tab_name_with_gap_fills_gap(self):
        # Inventory1 and Inventory3 exist — should return Inventory2
        existing = ["Inventory1", "Inventory3"]
        assert dss._next_tab_name(existing) == "Inventory2"

    def test_next_tab_name_non_inventory_sheets_ignored(self):
        existing = ["Sheet1", "Data"]
        assert dss._next_tab_name(existing) == "Inventory1"

    # _tab_has_header
    def test_tab_has_header_true_when_full_path_in_a1(self):
        svc = self._mock_svc()
        svc.spreadsheets().values().get().execute.return_value = {
            "values": [["full_path"]]
        }
        assert dss._tab_has_header(svc, "Sheet1") is True

    def test_tab_has_header_false_when_empty(self):
        svc = self._mock_svc()
        svc.spreadsheets().values().get().execute.return_value = {"values": []}
        assert dss._tab_has_header(svc, "Sheet1") is False

    def test_tab_has_header_false_when_different_value(self):
        svc = self._mock_svc()
        svc.spreadsheets().values().get().execute.return_value = {
            "values": [["something_else"]]
        }
        assert dss._tab_has_header(svc, "Sheet1") is False

    # _append_to_tab
    def test_append_to_tab_calls_values_append(self):
        svc = self._mock_svc()
        dss._append_to_tab(svc, "Sheet1", [["row1col1", "row1col2"]])
        svc.spreadsheets().values().append.assert_called_once()

    def test_append_to_tab_correct_range(self):
        svc = self._mock_svc()
        dss._append_to_tab(svc, "MyTab", [["val"]])
        kwargs = svc.spreadsheets().values().append.call_args.kwargs
        assert kwargs["range"] == "MyTab!A1"

    def test_append_to_tab_uses_raw_input_option(self):
        svc = self._mock_svc()
        dss._append_to_tab(svc, "Sheet1", [["val"]])
        kwargs = svc.spreadsheets().values().append.call_args.kwargs
        assert kwargs["valueInputOption"] == "RAW"

    def test_append_to_tab_correct_body(self):
        svc = self._mock_svc()
        rows = [["a", "b"], ["c", "d"]]
        dss._append_to_tab(svc, "Sheet1", rows)
        kwargs = svc.spreadsheets().values().append.call_args.kwargs
        assert kwargs["body"]["values"] == rows


# ---------------------------------------------------------------------------
# TestScanRouting  (verify deep-sheets/deep/dirs route to correct coroutine)
# ---------------------------------------------------------------------------
class TestScanRouting:
    def _capture_coro_name(self, scan_type):
        captured = []
        def capture(coro):
            captured.append(coro.__name__)
            coro.close()
        with patch("asyncio.create_task", side_effect=capture):
            client.post("/api/scan/start",
                        json={"paths": ["C:\\"], "scan_type": scan_type})
        return captured

    def test_deep_sheets_routes_to_run_scan_to_sheets(self):
        names = self._capture_coro_name("deep-sheets")
        assert names == ["run_scan_to_sheets"]

    def test_deep_routes_to_run_scan(self):
        names = self._capture_coro_name("deep")
        assert names == ["run_scan"]

    def test_dirs_routes_to_run_scan(self):
        names = self._capture_coro_name("dirs")
        assert names == ["run_scan"]

    def test_files_routes_to_run_scan(self):
        names = self._capture_coro_name("files")
        assert names == ["run_scan"]


# ---------------------------------------------------------------------------
# TestOpenOutputDir
# ---------------------------------------------------------------------------
class TestOpenOutputDir:
    def test_returns_ok_true(self):
        with patch("subprocess.Popen"):
            response = client.get("/api/open-output-dir")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_calls_explorer(self):
        with patch("subprocess.Popen") as mock_popen:
            client.get("/api/open-output-dir")
        args = mock_popen.call_args.args[0]
        assert args[0] == "explorer"

    def test_opens_output_dir_path(self):
        with patch("subprocess.Popen") as mock_popen:
            client.get("/api/open-output-dir")
        args = mock_popen.call_args.args[0]
        assert str(dss.OUTPUT_DIR) in args[1]
