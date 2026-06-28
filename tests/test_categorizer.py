"""Tests for the LLM categorizer service."""

import pytest
import datetime
import unittest
from unittest.mock import patch, MagicMock
from sqlmodel import select

from backend.modules.transactions.models import Transaction
from backend.modules.rules.models import CategoryRule
from backend.modules.accounts.models import Account
from backend.modules.analytics.categorizer import (
    _fetch_transactions,
    _group_transactions,
    query_llm,
    _process_categorization,
    get_cluster_stats,
)


@pytest.fixture
def categorizer_data(db_session):
    """Populates the test DB with sample transactions for categorizer tests."""
    d1 = datetime.date(2023, 1, 1)
    d2 = datetime.date(2023, 1, 2)
    d3 = datetime.date(2023, 1, 3)

    t1 = Transaction(
        transaction_id="1",
        account_id="a1",
        date=d1,
        name="Starbucks 123",
        amount=5.0,
        pending=False,
        merchant_name="Starbucks",
    )
    t2 = Transaction(
        transaction_id="2",
        account_id="a1",
        date=d2,
        name="Starbucks 456",
        amount=6.0,
        pending=False,
        merchant_name="Starbucks",
    )
    t3 = Transaction(
        transaction_id="3",
        account_id="a1",
        date=d3,
        name="Unknown Store",
        amount=10.0,
        pending=False,
    )  # No merchant

    db_session.add(t1)
    db_session.add(t2)
    db_session.add(t3)
    db_session.commit()


def test_fetch_transactions_exclusions(db_session, categorizer_data):
    """Test that fetch respects exclusions."""
    with patch(
        "backend.core.config.Settings.excluded_account_ids",
        new_callable=unittest.mock.PropertyMock,
        return_value={"a1"},
    ):
        txs = _fetch_transactions(db_session)
        assert len(txs) == 0

    with patch(
        "backend.core.config.Settings.excluded_account_ids",
        new_callable=unittest.mock.PropertyMock,
        return_value=set(),
    ):
        txs = _fetch_transactions(db_session)
        assert len(txs) == 3


def test_group_transactions(db_session, categorizer_data):
    """Test grouping by merchant and pattern."""
    txs = _fetch_transactions(db_session)
    clusters = _group_transactions(txs)

    assert "Starbucks" in clusters
    assert len(clusters["Starbucks"]["txs"]) == 2
    assert clusters["Starbucks"]["type"] == "merchant_name"

    assert "UNKNOWN STORE" in clusters  # clean_name uppercases
    assert len(clusters["UNKNOWN STORE"]["txs"]) == 1
    assert clusters["UNKNOWN STORE"]["type"] == "pattern"


def test_get_cluster_stats(categorizer_data, db_session):
    """Test stats calculation."""
    txs = _fetch_transactions(db_session)
    starbucks_txs = [t for t in txs if t.merchant_name == "Starbucks"]

    stats = get_cluster_stats(starbucks_txs)
    assert stats["avg_amount"] == "$5.50"
    assert len(stats["sample_names"]) == 2


@patch("backend.modules.analytics.categorizer.requests.post")
def test_query_llm_success(mock_post):
    """Test successful LLM query parsing."""
    mock_response = MagicMock()
    # Use raw string for JSON content
    json_content = '```json\n{"category": "Dining", "flow_type": "EXPENSE"}\n```'

    mock_response.json.return_value = {
        "choices": [{"message": {"content": json_content}}]
    }
    mock_post.return_value = mock_response

    cat, flow = query_llm({"pattern": "Starbucks"})
    assert cat == "Dining"
    assert flow == "EXPENSE"


@patch("backend.modules.analytics.categorizer.query_llm")
def test_process_categorization(mock_query, db_session, categorizer_data):
    """Test full categorization flow: group -> query -> save rule."""
    # Setup: 1 cluster
    txs = _fetch_transactions(db_session)
    clusters = _group_transactions(txs)

    # Mock LLM response
    mock_query.return_value = ("Dining", "EXPENSE")

    _process_categorization(db_session, clusters)

    # Verify Rules Saved
    rules = db_session.exec(select(CategoryRule)).all()
    assert len(rules) >= 1

    sb_rule = next(r for r in rules if r.match_value == "Starbucks")
    assert sb_rule.category == "Dining"
    assert sb_rule.flow_type == "EXPENSE"

    # Verify idempotency (shouldn't categorize again)
    _process_categorization(db_session, clusters)
    rules_after = db_session.exec(select(CategoryRule)).all()
    assert len(rules_after) == len(rules)
