"""Database session management."""

from collections.abc import Iterator
from sqlmodel import SQLModel, create_engine, Session

from core.config import settings

# Use the centralized DB path
engine = create_engine(settings.DB_URL)


def init_db() -> None:
    """Initializes the database by creating all tables defined in models."""
    from modules.accounts.models import Account, Liability, PlaidItem
    from modules.transactions.models import Transaction
    from modules.investments.models import (
        Security,
        InvestmentHolding,
        InvestmentTransaction,
    )
    from modules.rules.models import CategoryRule

    SQLModel.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """Provides a transactional scope around a series of operations.

    FastAPI dependency.

    Yields:
        Session: A SQLModel session object.
    """
    with Session(engine) as session:
        yield session
