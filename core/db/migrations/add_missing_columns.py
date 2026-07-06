"""Migration to add missing columns to existing database tables."""

import sqlite3

from core.config import settings


def migrate():
    """Add columns that exist in SQLModel but are missing from the database."""
    db_path = settings.DB_FILE
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    migrations = [
        ("accounts", "sync_interval_hours", "INTEGER DEFAULT 24"),
        ("transactions", "is_recurring", "BOOLEAN DEFAULT 0"),
    ]

    for table, column, col_type in migrations:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = {col[1] for col in cursor.fetchall()}
        if column not in columns:
            print(f"Adding {column} to {table}...")
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            )
        else:
            print(f"Column {column} already exists in {table}")

    conn.commit()
    conn.close()
    print("Migration completed successfully")


if __name__ == "__main__":
    migrate()