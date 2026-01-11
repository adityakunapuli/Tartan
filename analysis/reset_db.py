"""Utility to reset the database schema."""

from analysis.db.session import engine
from analysis.db.models import Base

def reset_db() -> None:
    """Drops all tables and recreates them with the latest schema."""
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database reset complete.")

if __name__ == "__main__":
    reset_db()
