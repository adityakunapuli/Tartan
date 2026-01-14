"""Utility to reset the database schema."""

from sqlmodel import SQLModel
from analysis.db.session import engine

def reset_db() -> None:
    """Drops all tables and recreates them with the latest schema."""
    print("Dropping all tables...")
    SQLModel.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    SQLModel.metadata.create_all(bind=engine)
    print("Database reset complete.")

if __name__ == "__main__":
    reset_db()
