"""Reporting script for generating portfolio summaries and spending analysis."""

from backend.modules.transactions.logic import (
    get_enriched_transactions_df,
    get_denormalized_holdings,
    get_investment_transactions_df,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def print_spending_by_category() -> None:
    """Prints a summary of spending grouped by enriched category."""
    logger.info("--- SPENDING ANALYSIS (Enriched) ---")
    df_tx = get_enriched_transactions_df()

    if df_tx.empty:
        logger.info("No transactions found.")
        return

    logger.info(f"Loaded {len(df_tx)} transactions.")

    # Filter out negative amounts (income/transfers) for spending analysis
    spending = df_tx[df_tx["amount"] > 0].copy()

    category_sum = (
        spending.groupby("enriched_category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    # For DataFrame printing, standard print is often better than log lines,
    # but let's stick to logger for consistency or just print the block.
    # Since logger adds timestamps, it might mess up the table.
    # I'll use logger for headers and print for data tables to keep them readable.
    print(category_sum)


def print_portfolio_summary() -> None:
    """Prints a summary of the investment portfolio including total value and top holdings."""
    logger.info("--- PORTFOLIO SUMMARY ---")
    df_inv = get_denormalized_holdings()

    if df_inv.empty:
        logger.info("No investment holdings found.")
        return

    logger.info(f"Loaded {len(df_inv)} investment holdings.")

    total_value = df_inv["institution_value"].sum()
    logger.info(f"Total Portfolio Value: ${total_value:,.2f}")

    logger.info("Top Holdings:")
    print(
        df_inv[["security_name", "ticker_symbol", "institution_value", "quantity"]]
        .sort_values(by="institution_value", ascending=False)
        .head()
    )


def print_investment_activity() -> None:
    """Prints recent investment transaction activity."""
    logger.info("--- INVESTMENT ACTIVITY ---")
    df_it = get_investment_transactions_df()

    if df_it.empty:
        logger.info("No investment transactions found.")
        return

    logger.info(f"Loaded {len(df_it)} investment transactions.")
    print(
        df_it[["date", "type", "name", "amount", "price"]]
        .sort_values(by="date", ascending=False)
        .head()
    )


def print_historical_performance() -> None:
    """Prints historical investment performance metrics including fees and net flow."""
    logger.info("--- HISTORICAL PERFORMANCE (Last 2 Years) ---")
    df_it = get_investment_transactions_df()

    if df_it.empty:
        logger.info("No investment transactions found.")
        return

    # Group by Type
    summary = df_it.groupby(["type", "subtype"])["amount"].sum().reset_index()
    logger.info("Transaction Totals by Type:")
    print(summary)

    # Calculate Fees
    total_fees = df_it[df_it["type"] == "fee"]["amount"].sum()
    logger.info(f"Total Fees Paid: ${total_fees:,.2f}")

    buys = df_it[df_it["type"] == "buy"]["amount"].sum()
    sells = df_it[df_it["type"] == "sell"]["amount"].sum()

    logger.info(f"Total Invested (Buys): ${buys:,.2f}")
    logger.info(f"Total Divested (Sells): ${sells:,.2f}")


if __name__ == "__main__":
    print_spending_by_category()
    print_portfolio_summary()
    print_investment_activity()
    print_historical_performance()