"""Reporting script for investment status and performance analysis."""

import json
from datetime import date

import pandas as pd
from dotenv import find_dotenv, load_dotenv

from analysis.services.data_layer import get_denormalized_holdings


def get_institution_name_heuristic(account_name: str) -> str:
    """Guesses the institution name based on the account name.

    Args:
        account_name (str): The name of the account.

    Returns:
        str: The guessed institution name.
    """
    name = str(account_name).lower()
    if "amgen" in name or "pennymac" in name or "bank of america" in name:
        return "Merrill Lynch / BofA"
    if "brokerage" in name or "ira" in name:
        return "E*TRADE"
    if "marcus" in name or "goldman" in name:
        return "Marcus"
    return "Other"


def sanitize_cost_basis(row: pd.Series) -> float | None:
    """Heuristic to fix or exclude bad cost basis data.

    Args:
        row (pd.Series): A row containing 'cost_basis' and 'institution_value'.

    Returns:
        float | None: The sanitized cost basis or None if invalid.
    """
    basis = row["cost_basis"]
    val = row["institution_value"]

    if basis is None or basis == 0:
        return None

    # If basis is > 10x the current value, it's almost certainly a data error
    if val > 1.0 and basis > (val * 10):
        # Try a 100x correction first (cents to dollars)
        corrected = basis / 100.0
        if corrected < (val * 5):
            return corrected
        return None

    return basis


def _print_account_breakdown(df: pd.DataFrame, ticker: str) -> None:
    """Prints a breakdown of shares by account for a specific ticker.

    Args:
        df (pd.DataFrame): The holdings DataFrame.
        ticker (str): The ticker symbol to filter by.
    """
    df_acc = df[df["ticker_symbol"].str.lower() == ticker.lower()].copy()
    if not df_acc.empty:
        summary = (
            df_acc.groupby("account_name")
            .agg(
                {
                    "quantity": "sum",
                    "institution_price": "first",
                    "institution_value": "sum",
                }
            )
            .reset_index()
            .sort_values("institution_value", ascending=False)
        )
        print(f"\nDETAILED BREAKDOWN FOR {ticker.upper()}:")
        print(summary.to_string(index=False))


def _print_ytd_summary(
    current_value: float, asset_type: str | None, ticker: str | None
) -> None:
    """Prints YTD performance comparison.

    Args:
        current_value (float): The current total value of the portfolio/selection.
        asset_type (str | None): The asset type filter used.
        ticker (str | None): The ticker filter used.
    """
    today = date.today()
    start_of_year = date(today.year, 1, 1)
    from analysis.db.session import engine

    date_query = (
        f"SELECT MIN(date_captured) as start_date FROM investment_holdings "
        f"WHERE date_captured >= '{start_of_year}'"
    )
    date_res = pd.read_sql(date_query, engine)
    if date_res.empty or date_res["start_date"].iloc[0] is None:
        return
    start_date = date_res["start_date"].iloc[0]
    query = f"""
        SELECT SUM(h.institution_value) as total_val FROM investment_holdings h
        LEFT JOIN securities s ON h.security_id = s.security_id
        WHERE h.date_captured = '{start_date}'
    """
    if asset_type:
        query += f" AND LOWER(s.type) = '{asset_type.lower()}'"
    if ticker:
        query += f" AND LOWER(s.ticker_symbol) = '{ticker.lower()}'"
    res = pd.read_sql(query, engine)
    if not res.empty and res["total_val"].iloc[0] is not None:
        start_val = res["total_val"].iloc[0]
        change = current_value - start_val
        pct = (change / start_val * 100) if start_val != 0 else 0
        print("\n" + "-" * 60)
        print(f"YTD PERFORMANCE (since {start_date})")
        print(f"  Starting Value:  ${start_val:14,.2f}")
        print(f"  Change:          ${change:14,.2f} ({pct:.2f}%)")
        print("-" * 60)


def report_investment_status(
    asset_type: str | None = None,
    ticker: str | None = None,
    show_json: bool = False,
) -> None:
    """Calculates and prints investment performance metrics.

    Args:
        asset_type (str | None): Optional filter for security type.
        ticker (str | None): Optional filter for ticker symbol.
        show_json (bool): Whether to output the summary as JSON.
    """
    df = get_denormalized_holdings()

    if df.empty:
        print("No investment holdings found.")
        return

    # Join with account/institution info for better grouping
    # Using a heuristic for the report as discussed.
    df["institution"] = df["account_name"].apply(get_institution_name_heuristic)

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

    df["cost_basis_fixed"] = df.apply(sanitize_cost_basis, axis=1)
    df["unrealized_gain"] = df["institution_value"] - df["cost_basis_fixed"]
    df["gain_pct"] = df["unrealized_gain"] / df["cost_basis_fixed"] * 100

    total_cost_valid = df["cost_basis_fixed"].sum()
    total_value_with_basis = df[df["cost_basis_fixed"].notna()][
        "institution_value"
    ].sum()
    total_gain = total_value_with_basis - total_cost_valid
    gain_pct = (total_gain / total_cost_valid * 100) if total_cost_valid != 0 else 0

    if show_json:
        print(json.dumps(df.to_dict(orient="records"), indent=2))
        return

    # Console Output
    print("\n" + "=" * 60)
    print("INVESTMENT STATUS REPORT")
    print("=" * 60)
    print(f"Snapshot Date: {df['date_captured'].iloc[0]}")
    print(f"Total Portfolio Value:  ${total_value:14,.2f}")
    print(f"Adj. Cost Basis:        ${total_cost_valid:14,.2f}")
    print(f"Adj. Unrealized Gain:   ${total_gain:14,.2f} ({gain_pct:.2f}%)")
    print("-" * 60)

    print("\nVALUE BY INSTITUTION:")
    inst_summary = (
        df.groupby("institution")["institution_value"].sum().sort_values(ascending=False)
    )
    for inst, val in inst_summary.items():
        print(f"  {inst:<20}: ${val:12,.2f}")

    print("\nVALUE BY ACCOUNT:")
    acc_summary = (
        df.groupby("account_name")["institution_value"].sum().sort_values(ascending=False)
    )
    for name, val in acc_summary.items():
        print(f"  {name:<40}: ${val:12,.2f}")

    print("\nTOP HOLDINGS & PERFORMANCE:")
    pd.options.display.float_format = "{:,.2f}".format
    cols = ["security_name", "ticker_symbol", "institution_value", "gain_pct"]
    print(
        df[cols]
        .sort_values(by="institution_value", ascending=False)
        .head(15)
        .to_string(index=False)
    )

    # Data Quality Warnings
    invalid = df[df["cost_basis_fixed"].isna() & df["cost_basis"].notna()]
    if not invalid.empty:
        print("\n[!] DATA QUALITY WARNING: Ignored erroneous cost basis for:")
        for _, row in invalid.iterrows():
            print(
                f"    - {row['security_name']}: Reported ${row['cost_basis']:,.0f} "
                f"vs Value ${row['institution_value']:,.0f}"
            )

    if ticker:
        _print_account_breakdown(df, ticker)

    _print_ytd_summary(total_value, asset_type, ticker)


if __name__ == "__main__":
    load_dotenv(find_dotenv(), override=True)

    # PYCHARM CONSOLE CONFIG
    TICKER_FILTER = None
    ASSET_FILTER = None

    report_investment_status(ticker=TICKER_FILTER, asset_type=ASSET_FILTER)