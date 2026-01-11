"""Database session management."""

import os
from collections.abc import Iterator
from sqlmodel import SQLModel, create_engine, Session

# Construct absolute path to the database file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "financial_data.db")
DB_PATH = f"sqlite:///{DB_FILE}"

engine = create_engine(DB_PATH)


def init_db() -> None:
    """Initializes the database by creating all tables defined in models."""
    SQLModel.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """Provides a transactional scope around a series of operations.

    Yields:
        Session: A SQLModel session object.
    """
    with Session(engine) as session:
        yield session
