"""Reporting script for personal financial health and strategy."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
from backend.modules.transactions.logic import get_enriched_transactions_df
from backend.core.database import engine
from utils.logger import get_logger

logger = get_logger(__name__)


def load_manual_data():
    """Load personal financial inputs from a local, gitignored JSON file.

    Returns:
        Tuple of vesting schedule entries and monthly spouse income.
    """
    repo_root = Path.cwd()
    data_path = repo_root / ".archive" / "manual_data.json"
    if not data_path.exists():
        logger.warning(f"Manual data not found: {data_path}")
        return [], 0.0

    with data_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    vesting_schedule = data.get("vesting_schedule", [])
    monthly_spouse_income = float(data.get("monthly_spouse_income", 0.0) or 0.0)
    return vesting_schedule, monthly_spouse_income


def get_current_liquidity() -> float:
    """Calculates total liquid cash from depository accounts.

    Returns:
        float: Total available balance in checking/savings accounts.
    """
    query = "SELECT current_balance FROM accounts WHERE type = 'depository'"
    df = pd.read_sql(query, engine)
    return df['current_balance'].sum() if not df.empty else 0.0


def get_revolving_debt() -> float:
    """Calculates total high-interest revolving debt (Credit Cards).

    Returns:
        float: Total POSITIVE balance of credit card accounts.
    """
    query = "SELECT current_balance FROM accounts WHERE type = 'credit'"
    df = pd.read_sql(query, engine)
    if df.empty:
        return 0.0
    # Only count positive balances (money you owe).
    return df[df['current_balance'] > 0]['current_balance'].sum()


def get_installment_debt() -> float:
    """Calculates total installment debt (Loans, Mortgage).

    Returns:
        float: Total balance of loan accounts.
    """
    query = "SELECT current_balance FROM accounts WHERE type = 'loan'"
    df = pd.read_sql(query, engine)
    return df['current_balance'].sum() if not df.empty else 0.0


def analyze_financial_health() -> None:
    """Executes the financial strategy logic."""
    logger.info("========================================================")
    logger.info("       PERSONAL FINANCIAL STRATEGY ENGINE       ")
    logger.info("========================================================")

    vesting_schedule, monthly_spouse_income = load_manual_data()

    # 1. Calculate True Burn Rate
    df = get_enriched_transactions_df()
    if df.empty:
        logger.warning("No transactions found. Cannot calculate burn rate.")
        return

    latest_date = df['date'].max()
    six_months_ago = latest_date - pd.DateOffset(months=6)

    # We exclude 'TRANSFER' and 'INCOME' to get true spending
    expenses = df[
        (df['date'] >= six_months_ago) &
        (df['flow_type'] == 'EXPENSE') &
        (df['amount'] > 0)
        ]

    if expenses.empty:
        logger.warning("No expenses found in the last 6 months.")
        return

    total_spend = expenses['amount'].sum()
    monthly_burn = total_spend / 6.0

    logger.info(f"[METRIC] Gross Burn Rate (6-mo Avg): ${monthly_burn:,.2f} / month")
    logger.info(f"  -> Total Spend (6-mo): ${total_spend:,.2f}")

    # 2. Target Emergency Fund
    monthly_net_burn = max(0, monthly_burn - monthly_spouse_income)

    logger.info(f"[METRIC] Guaranteed Monthly Income: ${monthly_spouse_income:,.2f}")
    logger.info(f"[METRIC] Net Burn Rate (Risk Exposure): ${monthly_net_burn:,.2f} / month")

    target_cash = monthly_net_burn * 6.0
    logger.info(f"[METRIC] Target Emergency Fund (6 Months Net): ${target_cash:,.2f}")

    # 3. Current State
    current_cash = get_current_liquidity()
    revolving_debt = get_revolving_debt()
    installment_debt = get_installment_debt()

    logger.info(f"[STATUS] Current Liquid Cash: ${current_cash:,.2f}")
    logger.info(f"[STATUS] Revolving Debt (CC): ${revolving_debt:,.2f}")
    logger.info(f"[STATUS] Installment Debt (Loans): ${installment_debt:,.2f}")

    # 4. Strategy Execution
    deployable_cash = current_cash - target_cash

    logger.info("--- STRATEGY EXECUTION ---")

    if deployable_cash > 0:
        logger.info(f"✅ SURPLUS DETECTED: You have ${deployable_cash:,.2f} in excess cash.")

        # Priority 1: Revolving Debt
        if revolving_debt > 0:
            pay_amount = min(deployable_cash, revolving_debt)
            logger.warning(f"🚨 PRIORITY 1: Pay off ${pay_amount:,.2f} of Credit Card debt IMMEDIATELY.")
            deployable_cash -= pay_amount

        # Priority 2: Installment Debt or Invest
        if deployable_cash > 0:
            if installment_debt > 0:
                logger.info(f"✅ Credit Cards Clear. You have ${deployable_cash:,.2f} available to attack Loans or Invest.")
                logger.info("   -> Recommendation: Compare Loan APR vs Expected Investment Return.")
            else:
                logger.info(f"🎉 DEBT FREE. Invest ${deployable_cash:,.2f} (529, Backdoor Roth, Brokerage).")

    else:
        shortfall = abs(deployable_cash)
        logger.warning(f"[WARN] RISK ALERT: You are underfunded by ${shortfall:,.2f}.")
        logger.warning("  -> ACTION: Halt all extra debt payments. Hoard cash until Target is met.")

    # 5. Future Liquidity (Vesting)
    logger.info("🔮 FUTURE LIQUIDITY (Next 12 Months) 🔮")
    today = date.today()
    future_cash = 0.0

    for event in vesting_schedule:
        event_date_value = event.get("date")
        if not event_date_value:
            continue
        event_date = date.fromisoformat(str(event_date_value))
        days_until = (event_date - today).days
        if 0 <= days_until <= 365:
            description = event.get("description", "Vesting Event")
            amount_post_tax = float(event.get("amount_post_tax", 0.0) or 0.0)
            logger.info(
                f"  -> {event_date} (+{days_until} days): {description} - ${amount_post_tax:,.2f}")
            future_cash += amount_post_tax

    logger.info(f"  -> Total Projected Inflow: ${future_cash:,.2f}")


if __name__ == '__main__':
    analyze_financial_health()