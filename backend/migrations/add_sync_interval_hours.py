"""Migration to add sync_interval_hours column to accounts table."""

import sqlite3
from pathlib import Path

from backend.core.config import settings


def migrate():
    """Add sync_interval_hours column to accounts table."""
    db_path = settings.DB_FILE
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(accounts)")
    columns = [col[1] for col in cursor.fetchall()]

    if "sync_interval_hours" in columns:
        print("Column sync_interval_hours already exists")
        conn.close()
        return

    print("Adding sync_interval_hours column to accounts table...")
    cursor.execute(
        "ALTER TABLE accounts ADD COLUMN sync_interval_hours INTEGER DEFAULT 24"
    )
    conn.commit()
    conn.close()
    print("Migration completed successfully")


if __name__ == "__main__":
    migrate()