"""Pytest configuration and fixtures."""

from unittest.mock import MagicMock

import pytest
from analysis.db.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def mock_plaid_client():
    """Returns a mock Plaid API client."""
    return MagicMock()


@pytest.fixture
def db_session():
    """Creates an in-memory SQLite database session for testing.

    Yields:
        Session: The SQLAlchemy session.
    """
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()