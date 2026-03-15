"""Database session management."""

from collections.abc import Iterator
from sqlmodel import SQLModel, create_engine, Session

from config import Config

# Use the centralized DB path
engine = create_engine(Config.DB_URL)


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