"""Smoke tests for reporting scripts."""

import pytest
from unittest.mock import patch

from reports.portfolio_summary import (
    print_portfolio_summary,
    print_spending_by_category,
    print_investment_activity,
    print_historical_performance,
)
from reports.financial_health import analyze_financial_health
from reports.investment_status import report_investment_status


@pytest.fixture(autouse=True)
def patch_db_engine(db_session):
    """Ensure reports use the test database."""
    test_engine = db_session.bind

    # Reports use backend.modules.transactions.logic or db.session directly.
    # We must patch where 'engine' is imported FROM.
    # Actually, we must patch where it is USED.
    # backend.modules.transactions.logic imports engine from db.session.
    # reports.financial_health imports engine from db.session.
    # reports.investment_status imports engine from db.session.

    # We need to patch db.session.engine?
    # If the modules have already imported 'engine', patching db.session.engine might be too late
    # if they did 'from db.session import engine'.
    # In that case, we patch 'reports.financial_health.engine' IF it has that name in its namespace.
    # Let's check imports in reports.

    # reports/financial_health.py: from db.session import engine
    # reports/investment_status.py: from db.session import engine
    # reports/portfolio_summary.py: DOES NOT import engine. Uses backend.modules.transactions.logic.

    with (
        patch("reports.financial_health.engine", test_engine),
        patch("reports.investment_status.engine", test_engine),
        patch("backend.modules.transactions.logic.engine", test_engine),
    ):
        yield


def test_portfolio_summary_reports():
    """Smoke test for portfolio summary reports."""
    # Should not raise errors even with empty DB
    print_portfolio_summary()
    print_spending_by_category()
    print_investment_activity()
    print_historical_performance()


def test_financial_health_report():
    """Smoke test for financial health report."""
    analyze_financial_health()


def test_investment_status_report():
    """Smoke test for investment status report."""
    report_investment_status()
