"""Tests for the data access layer."""

import pandas as pd
import pytest
import datetime
import unittest
from unittest.mock import patch
from sqlmodel import Session, select

from backend.modules.accounts.models import Account
from backend.modules.transactions.models import Transaction
from backend.modules.rules.models import CategoryRule
from backend.modules.transactions.logic import (
    _apply_account_exclusions,
    get_transactions_df,
    get_enriched_transactions_df,
)
from backend.core.config import settings as Config


@pytest.fixture(autouse=True)
def patch_data_layer_engine(db_session):
    """Patch the engine in backend.modules.transactions.logic to use the test DB."""
    # db_session.bind is the engine used by the session
    with patch("backend.modules.transactions.logic.engine", db_session.bind):
        yield


@pytest.fixture
def sample_data(db_session):
    """Populates the DB with sample data for testing."""
    # Note: Conftest already creates tables on the db_session engine.

    d1 = datetime.date(2023, 1, 1)
    d_tx1 = datetime.date(2023, 1, 10)
    d_tx2 = datetime.date(2023, 1, 11)
    d_tx3 = datetime.date(2023, 1, 12)

    # Accounts
    acc1 = Account(
        account_id="acc_1",
        name="Checking",
        type="depository",
        last_updated=d1,
    )
    acc2 = Account(
        account_id="acc_excluded",
        name="Old 401k",
        type="investment",
        last_updated=d1,
    )
    db_session.add(acc1)
    db_session.add(acc2)

    # Transactions
    t1 = Transaction(
        transaction_id="tx_1",
        account_id="acc_1",
        date=d_tx1,
        name="Grocery Store",
        amount=50.0,
        pending=False,
    )
    t2 = Transaction(
        transaction_id="tx_2",
        account_id="acc_excluded",
        date=d_tx2,
        name="Fee",
        amount=5.0,
        pending=False,
    )
    # Transaction needing categorization
    t3 = Transaction(
        transaction_id="tx_3",
        account_id="acc_1",
        date=d_tx3,
        name="UBER TRIP",
        amount=25.0,
        pending=False,
    )

    db_session.add(t1)
    db_session.add(t2)
    db_session.add(t3)

    # Category Rule
    rule = CategoryRule(
        match_value="UBER TRIP",
        match_type="pattern",
        category="Transport",
        flow_type="EXPENSE",
    )
    db_session.add(rule)

    db_session.commit()


def test_apply_account_exclusions(db_session, sample_data):
    """Test that _apply_account_exclusions correctly filters rows."""
    # Mock Config to exclude specific IDs and Names
    with (
        patch(
            "backend.core.config.Settings.excluded_account_ids",
            new_callable=unittest.mock.PropertyMock,
            return_value={"acc_excluded"},
        ),
        patch(
            "backend.core.config.Settings.excluded_account_names",
            new_callable=unittest.mock.PropertyMock,
            return_value=set(),
        ),
    ):
        # Create a DF with mixed accounts
        df = pd.DataFrame(
            {"account_id": ["acc_1", "acc_excluded"], "amount": [100, 200]}
        )

        filtered = _apply_account_exclusions(df)

        assert len(filtered) == 1
        assert filtered.iloc[0]["account_id"] == "acc_1"


def test_apply_account_name_exclusions(db_session, sample_data):
    """Test filtering by account name lookup."""
    with (
        patch(
            "backend.core.config.Settings.excluded_account_ids",
            new_callable=unittest.mock.PropertyMock,
            return_value=set(),
        ),
        patch(
            "backend.core.config.Settings.excluded_account_names",
            new_callable=unittest.mock.PropertyMock,
            return_value={"old 401k"},
        ),
    ):
        # Lowercase match check handled by config logic usually,
        # but here we pass lowercase set as config usually returns.

        df = pd.DataFrame(
            {"account_id": ["acc_1", "acc_excluded"], "amount": [100, 200]}
        )

        # This function queries the DB to map names to IDs
        filtered = _apply_account_exclusions(df)

        assert len(filtered) == 1
        assert filtered.iloc[0]["account_id"] == "acc_1"


def test_get_transactions_df(db_session, sample_data):
    """Test fetching transactions as DataFrame."""
    with (
        patch(
            "backend.core.config.Settings.excluded_account_ids",
            new_callable=unittest.mock.PropertyMock,
            return_value=set(),
        ),
        patch(
            "backend.core.config.Settings.excluded_account_names",
            new_callable=unittest.mock.PropertyMock,
            return_value=set(),
        ),
    ):
        df = get_transactions_df()

        assert len(df) == 3
        assert "date" in df.columns
        # verify date parsing
        assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_get_enriched_transactions_df(db_session, sample_data):
    """Test categorization logic application."""
    with (
        patch(
            "backend.core.config.Settings.excluded_account_ids",
            new_callable=unittest.mock.PropertyMock,
            return_value=set(),
        ),
        patch(
            "backend.core.config.Settings.excluded_account_names",
            new_callable=unittest.mock.PropertyMock,
            return_value=set(),
        ),
    ):
        df = get_enriched_transactions_df()

        # Check rule application
        uber = df[df["name"] == "UBER TRIP"].iloc[0]
        assert uber["enriched_category"] == "Transport"
        assert uber["flow_type"] == "EXPENSE"

        # Check heuristic fallback (Income detection)
        t_payroll = Transaction(
            transaction_id="tx_pay",
            account_id="acc_1",
            date=datetime.date(2023, 1, 15),  # Use datetime.date object
            name="GUSTO PAYROLL",
            amount=1000.0,
            pending=False,
        )
        db_session.add(t_payroll)
        db_session.commit()

        # Refetch
        df = get_enriched_transactions_df()
        payroll = df[df["name"] == "GUSTO PAYROLL"].iloc[0]
        assert payroll["enriched_category"] == "Income"
        assert payroll["flow_type"] == "INCOME"
