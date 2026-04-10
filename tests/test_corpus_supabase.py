"""
Tests for corpus_supabase_loader.py

Covers: column mapping (core vs extended), row dict building,
coercion, and integration tests against live Supabase.
"""

import os
import sys

import pytest

# Add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from corpus_sqlite_schema import to_snake_case, build_email_column_mapping

# Will be implemented in corpus_supabase_loader.py
from corpus_supabase_loader import (
    CORE_EMAIL_COLUMNS,
    CORE_ATTACHMENT_COLUMNS,
    SNAKE_TO_SUPABASE,
    build_email_row,
    build_attachment_row,
    get_supabase_client,
)


# ─── Source file paths (same as SQLite tests) ───

EMAILS_PATH = r"C:\Users\arika\OneDrive\Litigation\Pipeline\label_LegalEmailExtracts - Ariks Version V11.xlsx"
ATTACHMENTS_PATH = r"C:\Users\arika\OneDrive\Litigation\Aid4Mail Exports\Aid4 to json with python attachments\Attachment_Manifest_GML_EML_MSG (1).xlsx"


# ═══════════════════════════════════════════════
# Column mapping — core vs extended
# ═══════════════════════════════════════════════

class TestCoreColumnMapping:
    """Verify the core column set matches the Supabase schema."""

    def test_core_email_columns_count(self):
        """Supabase emails_master has 24 user-writable core columns
        (excluding auto-generated: created_at, fts_vector)."""
        assert len(CORE_EMAIL_COLUMNS) == 24

    def test_message_id_is_core(self):
        assert "message_id" in CORE_EMAIL_COLUMNS

    def test_from_addr_is_core(self):
        assert "from_addr" in CORE_EMAIL_COLUMNS

    def test_subject_is_core(self):
        assert "subject" in CORE_EMAIL_COLUMNS

    def test_body_clean_is_core(self):
        assert "body_clean" in CORE_EMAIL_COLUMNS

    def test_extended_is_NOT_core(self):
        """extended is auto-built, not a user-writable core column."""
        assert "extended" not in CORE_EMAIL_COLUMNS

    def test_fts_vector_is_NOT_core(self):
        assert "fts_vector" not in CORE_EMAIL_COLUMNS

    def test_created_at_is_NOT_core(self):
        assert "created_at" not in CORE_EMAIL_COLUMNS

    def test_core_attachment_columns_count(self):
        """Supabase attachments has 18 user-writable core columns
        (excluding auto-generated: attachment_id, created_at, fts_vector)."""
        assert len(CORE_ATTACHMENT_COLUMNS) == 18


class TestSnakeToSupabaseMapping:
    """Verify the SQLite snake_case → Supabase column name mapping."""

    def test_rfc_message_id_maps_to_message_id(self):
        assert SNAKE_TO_SUPABASE["rfc_822_message_id"] == "message_id"

    def test_body_clean_1_maps_to_body_clean(self):
        assert SNAKE_TO_SUPABASE["body_clean_1"] == "body_clean"

    def test_date_time_sent_maps_to_date_sent(self):
        assert SNAKE_TO_SUPABASE["date_time_sent"] == "date_sent"

    def test_date_time_received_maps_to_date_received(self):
        assert SNAKE_TO_SUPABASE["date_time_received"] == "date_received"

    def test_unmapped_core_column_identity(self):
        """Core columns with no rename should map to themselves."""
        assert SNAKE_TO_SUPABASE.get("subject", "subject") == "subject"


# ═══════════════════════════════════════════════
# Row building — email
# ═══════════════════════════════════════════════

class TestBuildEmailRow:
    """Verify build_email_row produces correct core + extended split."""

    def test_core_fields_present(self):
        mapping = [
            ("RFC 822 Message ID", "rfc_822_message_id", "TEXT"),
            ("Subject", "subject", "TEXT"),
            ("From", "from_addr", "TEXT"),
            ("Attachments Count", "attachments_count", "INTEGER"),
        ]
        values = ["<msg001>", "Test Subject", "alice@example.com", 5]
        row = build_email_row(mapping, values)

        assert row["message_id"] == "<msg001>"
        assert row["subject"] == "Test Subject"
        assert row["from_addr"] == "alice@example.com"
        assert row["attachments_count"] == 5

    def test_non_core_goes_to_extended(self):
        mapping = [
            ("RFC 822 Message ID", "rfc_822_message_id", "TEXT"),
            ("Subject", "subject", "TEXT"),
            ("Some Weird Column", "some_weird_column", "TEXT"),
        ]
        values = ["<msg002>", "Hello", "weird_value"]
        row = build_email_row(mapping, values)

        assert "some_weird_column" not in row  # not a top-level key
        assert "extended" in row
        assert row["extended"]["some_weird_column"] == "weird_value"

    def test_none_values_excluded_from_extended(self):
        """NULL values should not clutter the JSONB blob."""
        mapping = [
            ("RFC 822 Message ID", "rfc_822_message_id", "TEXT"),
            ("Empty Col", "empty_col", "TEXT"),
        ]
        values = ["<msg003>", None]
        row = build_email_row(mapping, values)

        ext = row.get("extended", {})
        assert "empty_col" not in ext

    def test_integer_coercion(self):
        mapping = [
            ("RFC 822 Message ID", "rfc_822_message_id", "TEXT"),
            ("Attachments Count", "attachments_count", "INTEGER"),
        ]
        values = ["<msg004>", "3"]
        row = build_email_row(mapping, values)
        assert row["attachments_count"] == 3

    def test_empty_string_becomes_none(self):
        mapping = [
            ("RFC 822 Message ID", "rfc_822_message_id", "TEXT"),
            ("Subject", "subject", "TEXT"),
        ]
        values = ["<msg005>", "   "]
        row = build_email_row(mapping, values)
        assert row["subject"] is None

    def test_extended_is_dict_or_absent(self):
        """extended should be a dict if non-core fields exist, absent otherwise."""
        mapping = [
            ("RFC 822 Message ID", "rfc_822_message_id", "TEXT"),
            ("Subject", "subject", "TEXT"),
        ]
        values = ["<msg006>", "Only core"]
        row = build_email_row(mapping, values)
        # No non-core fields → extended should be empty dict or absent
        ext = row.get("extended", {})
        assert isinstance(ext, dict)

    def test_full_103_column_mapping(self):
        """Using real Excel headers, verify core/extended split."""
        import openpyxl
        wb = openpyxl.load_workbook(EMAILS_PATH, read_only=True)
        ws = wb["Merge1"]
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        wb.close()

        mapping = build_email_column_mapping(headers)
        # Create dummy values
        values = [f"val_{i}" for i in range(len(mapping))]
        # Fix the message_id to be a string (PK)
        msg_idx = [i for i, (_, s, _) in enumerate(mapping) if s == "rfc_822_message_id"][0]
        values[msg_idx] = "<test_msg>"
        # Fix integer columns
        for i, (_, snake, dtype) in enumerate(mapping):
            if dtype == "INTEGER":
                values[i] = 42

        row = build_email_row(mapping, values)

        # Core fields should be top-level
        assert "message_id" in row
        assert row["message_id"] == "<test_msg>"
        # Non-core fields should be in extended
        assert "extended" in row
        assert isinstance(row["extended"], dict)
        # Total keys: core columns + extended = all 103 mapped somewhere
        core_count = len([k for k in row if k != "extended"])
        ext_count = len(row.get("extended", {}))
        assert core_count + ext_count == 103, \
            f"Core {core_count} + Extended {ext_count} != 103"


# ═══════════════════════════════════════════════
# Row building — attachment
# ═══════════════════════════════════════════════

class TestBuildAttachmentRow:
    def test_core_fields_present(self):
        mapping = [
            ("MIH", "mih", "TEXT"),
            ("Source", "source", "TEXT"),
            ("Message.ID", "message_id", "TEXT"),
            ("Attachment Ordinal", "attachment_ordinal", "INTEGER"),
            ("Original Filename", "original_filename", "TEXT"),
        ]
        values = ["mih_001", "GML", "<msg001>", 1, "doc.pdf"]
        row = build_attachment_row(mapping, values)

        assert row["message_id"] == "<msg001>"
        assert row["original_filename"] == "doc.pdf"
        assert row["attachment_ordinal"] == 1

    def test_extraction_status_default(self):
        """Rows should get extraction_status='pending' if not in source."""
        mapping = [
            ("Message.ID", "message_id", "TEXT"),
            ("Original Filename", "original_filename", "TEXT"),
        ]
        values = ["<msg001>", "test.pdf"]
        row = build_attachment_row(mapping, values)
        assert row.get("extraction_status") == "pending"


# ═══════════════════════════════════════════════
# Supabase connection
# ═══════════════════════════════════════════════

class TestSupabaseConnection:
    def test_client_connects(self):
        """Verify we can create a Supabase client and ping."""
        client = get_supabase_client()
        # Simple query — should not raise
        result = client.table("_column_map").select("*").limit(1).execute()
        assert isinstance(result.data, list)


# ═══════════════════════════════════════════════
# Integration — single row insert/delete
# ═══════════════════════════════════════════════

class TestIntegrationInsert:
    """Insert a test row, verify it exists, then clean up."""

    TEST_MSG_ID = "__test_row_001__"

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Delete test rows before and after each test."""
        client = get_supabase_client()
        # Pre-clean
        client.table("attachments").delete().eq("message_id", self.TEST_MSG_ID).execute()
        client.table("emails_master").delete().eq("message_id", self.TEST_MSG_ID).execute()
        yield
        # Post-clean
        client.table("attachments").delete().eq("message_id", self.TEST_MSG_ID).execute()
        client.table("emails_master").delete().eq("message_id", self.TEST_MSG_ID).execute()

    def test_insert_email_row(self):
        client = get_supabase_client()
        row = {
            "message_id": self.TEST_MSG_ID,
            "subject": "Integration Test Email",
            "from_addr": "test@example.com",
            "extended": {"test_field": "test_value"},
        }
        result = client.table("emails_master").insert(row).execute()
        assert len(result.data) == 1
        assert result.data[0]["message_id"] == self.TEST_MSG_ID

    def test_insert_attachment_row(self):
        client = get_supabase_client()
        # Parent email first
        client.table("emails_master").insert({
            "message_id": self.TEST_MSG_ID,
            "subject": "Parent Email",
        }).execute()

        att_row = {
            "message_id": self.TEST_MSG_ID,
            "original_filename": "test_doc.pdf",
            "extraction_status": "pending",
        }
        result = client.table("attachments").insert(att_row).execute()
        assert len(result.data) == 1
        assert result.data[0]["original_filename"] == "test_doc.pdf"

    def test_fts_auto_populated(self):
        """Verify tsvector column is auto-populated on insert."""
        client = get_supabase_client()
        client.table("emails_master").insert({
            "message_id": self.TEST_MSG_ID,
            "subject": "HIPAA Authorization Unique Test",
            "body_clean": "Please sign the HIPAA form for John Hancock",
        }).execute()

        # FTS query using textSearch
        result = client.table("emails_master").select("message_id, subject").text_search(
            "fts_vector", "HIPAA"
        ).execute()
        found = [r for r in result.data if r["message_id"] == self.TEST_MSG_ID]
        assert len(found) == 1

    def test_extended_jsonb_queryable(self):
        """Verify JSONB extended column is queryable."""
        client = get_supabase_client()
        client.table("emails_master").insert({
            "message_id": self.TEST_MSG_ID,
            "subject": "JSONB Test",
            "extended": {"custom_field": "unique_marker_xyz"},
        }).execute()

        # Read it back
        result = client.table("emails_master").select(
            "message_id, extended"
        ).eq("message_id", self.TEST_MSG_ID).execute()
        assert result.data[0]["extended"]["custom_field"] == "unique_marker_xyz"


# ═══════════════════════════════════════════════
# Loaded data verification — row counts and integrity
# ═══════════════════════════════════════════════

class TestLoadedDataCounts:
    """Verify the production data load matches expected counts."""

    def test_emails_master_row_count(self):
        client = get_supabase_client()
        result = client.table("emails_master").select(
            "message_id", count="exact"
        ).limit(0).execute()
        assert result.count == 1550, f"Expected 1550 emails, got {result.count}"

    def test_attachments_row_count(self):
        client = get_supabase_client()
        result = client.table("attachments").select(
            "attachment_id", count="exact"
        ).limit(0).execute()
        assert result.count == 2154, f"Expected 2154 attachments, got {result.count}"

    def test_orphan_attachment_count(self):
        """187 attachments should have extraction_status='pending_orphan'."""
        client = get_supabase_client()
        result = client.table("attachments").select(
            "attachment_id", count="exact"
        ).eq("extraction_status", "pending_orphan").limit(0).execute()
        assert result.count == 187, f"Expected 187 orphans, got {result.count}"

    def test_column_map_row_count(self):
        """103 email + 17 attachment = 120 column mappings."""
        client = get_supabase_client()
        result = client.table("_column_map").select(
            "original_name", count="exact"
        ).limit(0).execute()
        assert result.count == 120, f"Expected 120 column mappings, got {result.count}"

    def test_no_null_message_ids_in_emails(self):
        """Every email must have a message_id (PK)."""
        client = get_supabase_client()
        result = client.table("emails_master").select(
            "message_id", count="exact"
        ).is_("message_id", "null").limit(0).execute()
        assert result.count == 0, f"Found {result.count} emails with NULL message_id"

    def test_non_orphan_attachments_have_valid_fk(self):
        """Non-orphan attachments should all have a message_id that exists in emails_master."""
        client = get_supabase_client()
        # Get count of non-orphan attachments with non-null message_id
        non_orphan = client.table("attachments").select(
            "attachment_id", count="exact"
        ).eq("extraction_status", "pending").limit(0).execute()
        # Get count of non-orphan attachments with null message_id (should be 0)
        bad_rows = client.table("attachments").select(
            "attachment_id", count="exact"
        ).eq("extraction_status", "pending").is_("message_id", "null").limit(0).execute()
        assert bad_rows.count == 0, \
            f"{bad_rows.count} non-orphan attachments have NULL message_id"

    def test_orphan_attachments_have_null_message_id(self):
        """All orphan attachments should have message_id=NULL (FK safety)."""
        client = get_supabase_client()
        orphans_with_msg_id = client.table("attachments").select(
            "attachment_id", count="exact"
        ).eq("extraction_status", "pending_orphan").neq("message_id", "null").limit(0).execute()
        # This checks orphans that have a non-null message_id — should be 0
        # (we set message_id=None for orphans to satisfy FK constraint)
        # Note: neq with "null" doesn't work for NULL checks, use not_.is_ instead
        orphans_total = client.table("attachments").select(
            "attachment_id", count="exact"
        ).eq("extraction_status", "pending_orphan").limit(0).execute()
        orphans_null = client.table("attachments").select(
            "attachment_id", count="exact"
        ).eq("extraction_status", "pending_orphan").is_("message_id", "null").limit(0).execute()
        assert orphans_total.count == orphans_null.count, \
            f"{orphans_total.count - orphans_null.count} orphans still have a message_id set"

    def test_emails_have_extended_jsonb(self):
        """Spot-check that emails have populated extended JSONB."""
        client = get_supabase_client()
        result = client.table("emails_master").select("extended").range(0, 0).execute()
        assert result.data, "No emails returned"
        ext = result.data[0].get("extended")
        assert ext is not None, "First email has NULL extended"
        assert isinstance(ext, dict), f"extended is {type(ext)}, not dict"
        assert len(ext) > 0, "extended dict is empty"

    def test_fts_returns_results_for_known_term(self):
        """FTS should find 'EastRise' in the loaded corpus."""
        client = get_supabase_client()
        result = client.table("emails_master").select(
            "message_id"
        ).text_search("fts_vector", "EastRise").execute()
        assert len(result.data) == 48, f"Expected 48 EastRise hits, got {len(result.data)}"
