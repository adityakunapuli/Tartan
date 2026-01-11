"""Reporting script for generating portfolio summaries and spending analysis."""

from analysis.services.data_layer import (
    get_enriched_transactions_df,
    get_denormalized_holdings,
    get_investment_transactions_df,
)


def print_spending_by_category() -> None:
    """Prints a summary of spending grouped by enriched category."""
    print("\n--- SPENDING ANALYSIS (Enriched) ---")
    df_tx = get_enriched_transactions_df()

    if df_tx.empty:
        print("No transactions found.")
        return

    print(f"Loaded {len(df_tx)} transactions.")

    # Filter out negative amounts (income/transfers) for spending analysis
    # And maybe Transfers? If 'enriched_category' == 'Transfer', we might want to exclude it from "Spending".
    # But let's show all positive amounts for now, grouped by our new categories.

    spending = df_tx[df_tx["amount"] > 0].copy()

    category_sum = (
        spending.groupby("enriched_category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    print(category_sum)


def print_portfolio_summary() -> None:
    """Prints a summary of the investment portfolio including total value and top holdings."""
    print("\n--- PORTFOLIO SUMMARY ---")
    df_inv = get_denormalized_holdings()

    if df_inv.empty:
        print("No investment holdings found.")
        return

    print(f"Loaded {len(df_inv)} investment holdings.")

    total_value = df_inv["institution_value"].sum()
    print(f"Total Portfolio Value: ${total_value:,.2f}")

    print("\nTop Holdings:")
    print(
        df_inv[["security_name", "ticker_symbol", "institution_value", "quantity"]]
        .sort_values(by="institution_value", ascending=False)
        .head()
    )


def print_investment_activity() -> None:
    """Prints recent investment transaction activity."""
    print("\n--- INVESTMENT ACTIVITY ---")
    df_it = get_investment_transactions_df()

    if df_it.empty:
        print("No investment transactions found.")
        return

    print(f"Loaded {len(df_it)} investment transactions.")
    print(
        df_it[["date", "type", "name", "amount", "price"]]
        .sort_values(by="date", ascending=False)
        .head()
    )


def print_historical_performance() -> None:
    """Prints historical investment performance metrics including fees and net flow."""
    print("\n--- HISTORICAL PERFORMANCE (Last 2 Years) ---")
    df_it = get_investment_transactions_df()

    if df_it.empty:
        print("No investment transactions found.")
        return

    # Group by Type
    summary = df_it.groupby(["type", "subtype"])["amount"].sum().reset_index()
    print("Transaction Totals by Type:")
    print(summary)

    # Calculate Fees
    total_fees = df_it[df_it["type"] == "fee"]["amount"].sum()
    print(f"\nTotal Fees Paid: ${total_fees:,.2f}")

    # Calculate Buys vs Sells (Flow)
    # Plaid conventions:
    # - Buys are positive amount (cost to buy).
    # - Sells are negative amount (proceeds from sell).
    # Wait, let's verify this convention. Usually:
    # Amount is the value of the transaction.
    # For a 'buy', amount is positive (money leaving cash to buy stock).
    # For a 'sell', amount is negative (money entering cash from stock)?
    # Or is amount always positive and type determines direction?
    # Let's check the data we just saw:
    # 0 2025-12-31 cash withdrawal 1000.00
    # 9 2025-12-30 buy buy 1000.00
    # It seems amount is positive.

    buys = df_it[df_it["type"] == "buy"]["amount"].sum()
    sells = df_it[df_it["type"] == "sell"][
        "amount"
    ].sum()  # Assuming sell exists, otherwise 0

    print(f"Total Invested (Buys): ${buys:,.2f}")
    print(f"Total Divested (Sells): ${sells:,.2f}")


if __name__ == "__main__":
    print_spending_by_category()
    print_portfolio_summary()
    print_investment_activity()
    print_historical_performance()
