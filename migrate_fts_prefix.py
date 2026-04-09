"""One-time migration: rename FTS tables from emails_fts / attachments_fts
to _fts_emails / _fts_attachments so infrastructure tables sort together
under the _ prefix, keeping user tables visually separated.

Usage:
    python migrate_fts_prefix.py [path_to_db]

Default DB: (see DEFAULT_DB constant below)
"""
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = r"C:\Users\arika\OneDrive\Litigation\Pipeline\litigation_corpus.db"


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # --- Step 1: Read existing FTS data into memory ---
    print("Reading emails_fts...")
    email_rows = cur.execute("SELECT subject, body_clean FROM emails_fts").fetchall()
    print(f"  {len(email_rows):,} rows")

    print("Reading attachments_fts...")
    attach_rows = cur.execute(
        "SELECT original_filename, extracted_text FROM attachments_fts"
    ).fetchall()
    print(f"  {len(attach_rows):,} rows")

    # --- Step 2: Drop old FTS tables (cascades to helper tables) ---
    print("Dropping old FTS tables...")
    cur.execute("DROP TABLE IF EXISTS emails_fts")
    cur.execute("DROP TABLE IF EXISTS attachments_fts")

    # --- Step 3: Create new FTS tables with _ prefix ---
    print("Creating _fts_emails...")
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS _fts_emails USING fts5(
            subject, body_clean,
            tokenize='unicode61'
        )
    """)

    print("Creating _fts_attachments...")
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS _fts_attachments USING fts5(
            original_filename, extracted_text,
            tokenize='unicode61'
        )
    """)

    # --- Step 4: Repopulate ---
    print("Repopulating _fts_emails...")
    cur.executemany(
        "INSERT INTO _fts_emails (subject, body_clean) VALUES (?, ?)",
        email_rows,
    )

    print("Repopulating _fts_attachments...")
    cur.executemany(
        "INSERT INTO _fts_attachments (original_filename, extracted_text) VALUES (?, ?)",
        attach_rows,
    )

    conn.commit()

    # --- Step 5: Verify ---
    new_email = cur.execute("SELECT COUNT(*) FROM _fts_emails").fetchone()[0]
    new_attach = cur.execute("SELECT COUNT(*) FROM _fts_attachments").fetchone()[0]

    print(f"\nVerification:")
    print(f"  _fts_emails:       {new_email:,} rows (was {len(email_rows):,})")
    print(f"  _fts_attachments:  {new_attach:,} rows (was {len(attach_rows):,})")

    assert new_email == len(email_rows), "Email FTS row count mismatch!"
    assert new_attach == len(attach_rows), "Attachment FTS row count mismatch!"

    # Show new table list
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\nAll tables (sorted):")
    for t in tables:
        print(f"  {t}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    if not Path(db).exists():
        print(f"ERROR: DB not found: {db}")
        sys.exit(1)
    migrate(db)
