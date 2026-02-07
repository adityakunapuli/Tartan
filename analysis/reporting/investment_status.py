"""Reporting script for investment status and performance analysis."""

import json
from datetime import date

import pandas as pd
from dotenv import find_dotenv, load_dotenv

from analysis.services.data_layer import get_denormalized_holdings


def report_investment_status(
    asset_type: str | None = None,
    ticker: str | None = None,
    show_json: bool = False,
) -> None:
    """Calculates and prints investment performance metrics.

    Args:
        asset_type: Optional filter for security type (e.g., 'equity', 'mutual fund').
        ticker: Optional filter for ticker symbol.
        show_json: Whether to output the summary as JSON.
    """
    df = get_denormalized_holdings()

    if df.empty:
        print("No investment holdings found.")
        return

    # Apply filters
    if asset_type:
        df = df[df["security_type"].str.lower() == asset_type.lower()]
    if ticker:
        df = df[df["ticker_symbol"].str.lower() == ticker.lower()]

    if df.empty:
        print(f"No holdings match the filters (type={asset_type}, ticker={ticker}).")
        return

    # Basic Metrics
    total_value = df["institution_value"].sum()
    total_cost = df["cost_basis"].sum()
    total_gain = total_value - total_cost
    gain_pct = (total_gain / total_cost * 100) if total_cost != 0 else 0

    # Group by Security Type
    allocation = (
        df.groupby("security_type")["institution_value"]
        .sum()
        .sort_values(ascending=False)
    )

    # Performance by Security
    df["unrealized_gain"] = df["institution_value"] - df["cost_basis"]
    df["gain_pct"] = (df["unrealized_gain"] / df["cost_basis"] * 100).fillna(0)

    security_perf = df[
        [
            "security_name",
            "ticker_symbol",
            "quantity",
            "institution_value",
            "unrealized_gain",
            "gain_pct",
        ]
    ].sort_values(by="institution_value", ascending=False)

    if show_json:
        summary = {
            "total_value": float(total_value),
            "total_cost_basis": float(total_cost),
            "total_unrealized_gain": float(total_gain),
            "gain_percent": float(gain_pct),
            "allocation": allocation.to_dict(),
            "holdings": security_perf.to_dict(orient="records"),
        }
        print(json.dumps(summary, indent=2))
        return

    # Console Output
    print("\n" + "=" * 50)
    print("INVESTMENT STATUS REPORT")
    print("=" * 50)
    print(f"Date Captured: {df['date_captured'].iloc[0]}")
    print(f"Total Portfolio Value:  ${total_value:14,.2f}")
    print(f"Total Cost Basis:       ${total_cost:14,.2f}")
    print(f"Total Unrealized Gain:  ${total_gain:14,.2f} ({gain_pct:.2f}%)")
    print("-" * 50)

    print("\nALLOCATION BY ASSET TYPE:")
    for atype, val in allocation.items():
        pct = (val / total_value * 100) if total_value != 0 else 0
        print(f"  {str(atype):<15}: ${val:12,.2f} ({pct:5.1f}%)")

    print("\nTOP HOLDINGS & PERFORMANCE:")
    # Format for better console reading
    pd.options.display.float_format = "{:,.2f}".format
    print(security_perf.head(10).to_string(index=False))

    # YTD Logic (Approximation)
    _print_ytd_summary(total_value, asset_type, ticker)


def _print_ytd_summary(
    current_value: float,
    asset_type: str | None = None,
    ticker: str | None = None,
) -> None:
    """Prints a simple YTD performance comparison based on earliest record of the year."""
    today = date.today()
    start_of_year = date(today.year, 1, 1)

    from analysis.db.session import engine

    # Query for the first available date of the year
    date_query = f"SELECT MIN(date_captured) as start_date FROM investment_holdings WHERE date_captured >= '{start_of_year}'"
    date_res = pd.read_sql(date_query, engine)

    if date_res.empty or date_res["start_date"].iloc[0] is None:
        return

    start_date = date_res["start_date"].iloc[0]

    # Now get the sum for that date, with filters
    query = f"""
    SELECT SUM(h.institution_value) as total_val 
    FROM investment_holdings h
    LEFT JOIN securities s ON h.security_id = s.security_id
    WHERE h.date_captured = '{start_date}'
    """

    if asset_type:
        query += f" AND LOWER(s.type) = '{asset_type.lower()}'"
    if ticker:
        query += f" AND LOWER(s.ticker_symbol) = '{ticker.lower()}'"

    first_record = pd.read_sql(query, engine)

    if not first_record.empty and first_record["total_val"].iloc[0] is not None:
        start_val = first_record["total_val"].iloc[0]

        ytd_change = current_value - start_val
        ytd_pct = (ytd_change / start_val * 100) if start_val != 0 else 0

        print("\n" + "-" * 50)
        print(f"YTD PERFORMANCE (since {start_date})")
        print(f"  Starting Value:  ${start_val:14,.2f}")
        print(f"  Current Value:   ${current_value:14,.2f}")
        print(f"  Change:          ${ytd_change:14,.2f} ({ytd_pct:.2f}%)")
        print("  *Note: Does not account for contributions/withdrawals.")
        print("-" * 50)


if __name__ == "__main__":
    load_dotenv(find_dotenv(), override=True)
    report_investment_status()