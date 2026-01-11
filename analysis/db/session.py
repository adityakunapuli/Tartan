"""Database session management."""

import os
from typing import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

# Construct absolute path to the database file
# __file__ is analysis/db/session.py
# dirname -> analysis/db
# dirname -> analysis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "financial_data.db")
DB_PATH = f"sqlite:///{DB_FILE}"

engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    """Initializes the database by creating all tables defined in models."""
    Base.metadata.create_all(bind=engine)

def get_db() -> Iterator[Session]:
    """Provides a transactional scope around a series of operations.

    Yields:
        Session: A SQLAlchemy session object.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
