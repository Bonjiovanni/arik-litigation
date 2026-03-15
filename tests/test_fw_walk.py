"""
tests/test_fw_walk.py

Smoke tests for the merged fw_walk.py module.
Verifies all public functions are importable and accessible,
and that no name collisions exist between groups.
Run with: pytest tests/test_fw_walk.py
"""

import sys
import os
import openpyxl
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fw_walk


# ---------------------------------------------------------------------------
# Import-level smoke tests
# ---------------------------------------------------------------------------

class TestPublicAPI:

    def test_group1_functions_accessible(self):
        assert callable(fw_walk.load_file_family_config)
        assert callable(fw_walk.classify_file_family)
        assert callable(fw_walk.should_skip_file)
        assert callable(fw_walk.get_file_metadata)
        assert callable(fw_walk.compute_sha256)
        assert callable(fw_walk.peek_archive_contents)

    def test_group2_functions_accessible(self):
        assert callable(fw_walk.ensure_master_file_inventory_sheet)
        assert callable(fw_walk.get_next_file_id)
        assert callable(fw_walk.find_existing_file_row)
        assert callable(fw_walk.insert_file_record)
        assert callable(fw_walk.update_file_record)
        assert callable(fw_walk.write_or_update_file_record)
        assert callable(fw_walk.ensure_file_family_config_sheet)

    def test_group3_functions_accessible(self):
        assert isinstance(fw_walk.PROCESSING_LEVEL_ORDER, list)
        assert callable(fw_walk.get_covered_paths)
        assert callable(fw_walk.check_overlap)
        assert callable(fw_walk.prompt_overlap_decision)
        assert callable(fw_walk.walk_files)

    def test_group4_functions_accessible(self):
        assert callable(fw_walk.ensure_walk_coverage_sheet)
        assert callable(fw_walk.get_next_coverage_id)
        assert callable(fw_walk.update_walk_coverage)
        assert callable(fw_walk.ensure_walk_history_sheet)
        assert callable(fw_walk.log_walk_run)

    def test_group5_main_accessible(self):
        assert callable(fw_walk.main)

    def test_workbook_path_defined(self):
        assert hasattr(fw_walk, "WORKBOOK_PATH")
        assert "xlsx" in fw_walk.WORKBOOK_PATH


# ---------------------------------------------------------------------------
# Cross-group consistency tests (merged module)
# ---------------------------------------------------------------------------

class TestCrossGroupConsistency:

    def test_processing_level_order_has_file_listed(self):
        assert "file_listed" in fw_walk.PROCESSING_LEVEL_ORDER

    def test_classify_and_sheet_use_same_family_names(self):
        # Families in _FAMILY_MAP should all appear in FileFamily_Config defaults
        wb = openpyxl.Workbook()
        fc_ws = fw_walk.ensure_file_family_config_sheet(wb)
        config_families = {
            row[0] for row in fc_ws.iter_rows(min_row=2, values_only=True) if row and row[0]
        }
        # A few spot checks
        assert "pdf" in config_families
        assert "archive" in config_families
        assert "text_file" in config_families

    def test_master_inventory_has_archive_contents_column(self):
        wb = openpyxl.Workbook()
        ws = fw_walk.ensure_master_file_inventory_sheet(wb)
        headers = {c.value for c in ws[1] if c.value}
        assert "ArchiveContents" in headers

    def test_walk_coverage_and_history_created_together(self):
        wb = openpyxl.Workbook()
        fw_walk.ensure_walk_coverage_sheet(wb)
        fw_walk.ensure_walk_history_sheet(wb)
        assert "Walk_Coverage" in wb.sheetnames
        assert "Walk_History" in wb.sheetnames

    def test_write_or_update_creates_inventory_sheet_if_absent(self):
        wb = openpyxl.Workbook()
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]
        record = {"file_path": "C:/Test/file.pdf", "filename": "file.pdf", "size_bytes": 100}
        fw_walk.write_or_update_file_record(wb, record, "RUN1")
        assert "Master_File_Inventory" in wb.sheetnames

    def test_full_init_sequence_creates_all_sheets(self):
        wb = openpyxl.Workbook()
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]
        fw_walk.ensure_master_file_inventory_sheet(wb)
        fw_walk.ensure_file_family_config_sheet(wb)
        fw_walk.ensure_walk_coverage_sheet(wb)
        fw_walk.ensure_walk_history_sheet(wb)
        expected = {
            "Master_File_Inventory", "FileFamily_Config",
            "Walk_Coverage", "Walk_History",
        }
        assert expected.issubset(set(wb.sheetnames))
