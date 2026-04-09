"""
corpus_sqlite_schema.py — Creates the litigation_corpus.db schema.

Domain-aware: shared tables (entities, metadata) are never dropped.
Each domain (email, text, file) has its own tables that can be
rebuilt independently.

Usage:
    python corpus_sqlite_schema.py [--db PATH] [--rebuild-email]
"""

import argparse
import re
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = r"C:\Users\arika\OneDrive\Litigation\Pipeline\litigation_corpus.db"


def to_snake_case(header: str) -> str:
    """Convert a messy Excel header to a valid snake_case SQLite column name.

    Rules:
    - Lowercase everything
    - Spaces, dots, hyphens, parentheses → underscores
    - Strip leading/trailing underscores
    - Collapse multiple underscores
    - Special chars (?, !, @, #, =, +) → removed
    - 'body_clean.1' → 'body_clean_1'
    - 'original=saved' → 'original_saved'
    - 'RFC 822 Message ID' → 'rfc_822_message_id'
    """
    s = header.strip().lower()
    # Replace dots, spaces, hyphens, parens with underscores
    s = re.sub(r'[\s.\-\(\)]+', '_', s)
    # Replace = with underscore (e.g. original=saved → original_saved)
    s = s.replace('=', '_')
    # Remove remaining special chars
    s = re.sub(r'[?!@#+\'"&]', '', s)
    # Collapse multiple underscores
    s = re.sub(r'_+', '_', s)
    # Strip leading/trailing underscores
    s = s.strip('_')
    return s


# --- INTEGER columns by table (everything else is TEXT) ---

EMAILS_INTEGER_COLUMNS = {
    'attachments_count', 'combined_start_page', 'combined_end_page',
    'start_page', 'end_page', 'page_count', 'email_size',
    'header_x_priority', 'attachment_count',
}

ATTACHMENTS_INTEGER_COLUMNS = {
    'attachment_ordinal', 'original_saved', 'size_bytes',
}


def get_column_type(snake_name: str, table: str) -> str:
    """Return SQLite type affinity for a column."""
    if table == 'emails_master' and snake_name in EMAILS_INTEGER_COLUMNS:
        return 'INTEGER'
    if table == 'attachments' and snake_name in ATTACHMENTS_INTEGER_COLUMNS:
        return 'INTEGER'
    return 'TEXT'


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection with FK enforcement enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_shared_tables(conn: sqlite3.Connection) -> None:
    """Create shared tables (entities, metadata). Idempotent — IF NOT EXISTS."""

    conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_master (
            entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT NOT NULL,
            entity_type TEXT,
            known_aliases TEXT,
            status TEXT DEFAULT 'active',
            first_seen_source TEXT,
            notes TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_candidates (
            candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_text TEXT NOT NULL,
            suggested_canonical_name TEXT,
            likely_entity_type TEXT,
            seen_count INTEGER DEFAULT 1,
            first_seen_source TEXT,
            example_context TEXT,
            promotion_status TEXT DEFAULT 'pending',
            merged_into_entity_id INTEGER,
            notes TEXT,
            FOREIGN KEY (merged_into_entity_id) REFERENCES entity_master(entity_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS _column_map (
            source_table TEXT NOT NULL,
            original_name TEXT NOT NULL,
            snake_case_name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            PRIMARY KEY (source_table, original_name)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS _schema_notes (
            note_key TEXT PRIMARY KEY,
            note_text TEXT NOT NULL,
            created_date TEXT DEFAULT (datetime('now'))
        )
    """)

    # Indexes on shared tables
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entity_type
        ON entity_master(entity_type)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entity_candidates_status
        ON entity_candidates(promotion_status)
    """)

    conn.commit()


def drop_email_tables(conn: sqlite3.Connection) -> None:
    """Drop all email-domain tables, FTS, and indexes. Leaves shared tables intact."""
    # FTS virtual tables first
    conn.execute("DROP TABLE IF EXISTS _fts_emails")
    conn.execute("DROP TABLE IF EXISTS _fts_attachments")
    # Domain tables (order matters for FK)
    conn.execute("DROP TABLE IF EXISTS extraction_log")
    conn.execute("DROP TABLE IF EXISTS attachments")
    conn.execute("DROP TABLE IF EXISTS emails_master")
    # Clean up _column_map rows for this domain
    conn.execute("DELETE FROM _column_map WHERE source_table IN ('emails_master', 'attachments')")
    conn.commit()


def create_email_tables(conn: sqlite3.Connection, email_columns: list[tuple[str, str, str]],
                        rebuild: bool = False) -> None:
    """Create email-domain tables.

    Args:
        conn: SQLite connection
        email_columns: list of (original_name, snake_case_name, data_type) for emails_master
        rebuild: if True, drop existing email tables first
    """
    if rebuild:
        drop_email_tables(conn)

    # --- emails_master ---
    # Build column definitions from the provided mapping
    col_defs = []
    for _, snake_name, dtype in email_columns:
        if snake_name == 'rfc_822_message_id':
            col_defs.append(f"    {snake_name} {dtype} PRIMARY KEY")
        else:
            col_defs.append(f"    {snake_name} {dtype}")

    cols_sql = ",\n".join(col_defs)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS emails_master (
{cols_sql}
        )
    """)

    # --- attachments ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mih TEXT,
            source TEXT,
            message_id TEXT,
            sent_local_nyc TEXT,
            from_addr TEXT,
            to_addr TEXT,
            cc TEXT,
            subject TEXT,
            attachment_ordinal INTEGER,
            original_filename TEXT,
            saved_filename TEXT,
            original_saved INTEGER,
            file_type TEXT,
            saved_full_path TEXT,
            storage_folder TEXT,
            size_bytes INTEGER,
            sha256 TEXT,
            extracted_text TEXT,
            extraction_status TEXT DEFAULT 'pending',
            FOREIGN KEY (message_id) REFERENCES emails_master(rfc_822_message_id)
        )
    """)

    # --- extraction_log ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extraction_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            attachment_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            method TEXT,
            file_type TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            error_message TEXT,
            FOREIGN KEY (attachment_id) REFERENCES attachments(attachment_id)
        )
    """)

    # --- FTS5 virtual tables ---
    # These are standalone (no content= sync) because column names in the
    # source tables are dynamically mapped (e.g. body_clean.1 → body_clean_1).
    # The loader script populates them explicitly after data insert.
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS _fts_emails USING fts5(
            subject, body_clean,
            tokenize='unicode61'
        )
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS _fts_attachments USING fts5(
            original_filename, extracted_text,
            tokenize='unicode61'
        )
    """)

    # --- B-tree indexes ---
    conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_date ON emails_master(date_time_sent)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_from ON emails_master(from_addr)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_message_id ON attachments(message_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_file_type ON attachments(file_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_sha256 ON attachments(sha256)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_status ON attachments(extraction_status)")

    conn.commit()


def build_email_column_mapping(headers: list[str]) -> list[tuple[str, str, str]]:
    """Convert raw Excel headers to (original, snake_case, type) tuples.

    Also handles collision detection — if two headers map to the same
    snake_case name, appends a suffix.
    """
    mapping = []
    seen = {}
    for original in headers:
        if original is None:
            original = "unnamed"
        snake = to_snake_case(str(original))
        if not snake:
            snake = "unnamed"

        # Handle collisions
        if snake in seen:
            seen[snake] += 1
            snake = f"{snake}_{seen[snake]}"
        else:
            seen[snake] = 1

        # Rename 'from' and 'to' to avoid SQL reserved words
        if snake == 'from':
            snake = 'from_addr'
        elif snake == 'to':
            snake = 'to_addr'

        dtype = get_column_type(snake, 'emails_master')
        mapping.append((str(original), snake, dtype))

    return mapping


def build_attachments_column_mapping(headers: list[str]) -> list[tuple[str, str, str]]:
    """Convert attachment manifest headers to (original, snake_case, type) tuples."""
    # The attachments table has a fixed schema (we know the 17 columns),
    # but we still map for _column_map provenance tracking.
    mapping = []
    for original in headers:
        if original is None:
            original = "unnamed"
        snake = to_snake_case(str(original))

        # Rename reserved words
        if snake == 'from':
            snake = 'from_addr'
        elif snake == 'to':
            snake = 'to_addr'

        dtype = get_column_type(snake, 'attachments')
        mapping.append((str(original), snake, dtype))

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Create litigation_corpus.db schema")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to database file")
    parser.add_argument("--rebuild-email", action="store_true",
                        help="Drop and recreate email domain tables")
    args = parser.parse_args()

    # Ensure parent directory exists
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    conn = connect(args.db)
    try:
        create_shared_tables(conn)
        print(f"Shared tables created/verified in: {args.db}")

        if args.rebuild_email:
            print("NOTE: Email tables require column mapping from source file.")
            print("Use corpus_sqlite_loader.py to rebuild with data.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
