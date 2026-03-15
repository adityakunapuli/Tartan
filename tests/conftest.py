"""Pytest configuration and fixtures."""

from unittest.mock import MagicMock

import pytest
from backend.modules.transactions.models import Transaction
from backend.modules.accounts.models import PlaidItem, Account
from backend.modules.investments.models import InvestmentHolding, Security
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool


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
    # Use shared in-memory SQLite for testing to allow pandas/engine to see the same data
    # 'sqlite:///:memory:' with StaticPool ensures all connections share the same memory
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    # Create all tables defined in models. Using SQLModel.metadata instead of Base
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session
