"""Reporting script for deep analysis of transaction patterns and anomalies."""

import pandas as pd

from modules.transactions.logic import get_transactions_df
from utils.helpers import clean_name


def analyze_missing_merchants(df: pd.DataFrame) -> None:
    """Analyzes clusters of transactions that are missing merchant names.

    Args:
        df (pd.DataFrame): The transactions DataFrame.
    """
    missing_merch = df[df["merchant_name"].isnull()].copy()
    print(f"\nTransactions with Missing Merchant: {len(missing_merch)}")

    if not missing_merch.empty:
        # 1. Clean Names Clustering
        missing_merch["cleaned_name"] = missing_merch["name"].apply(clean_name)

        print("\n--- Top Clusters by Cleaned Name (Missing Merchant) ---")
        clusters = missing_merch["cleaned_name"].value_counts().head(20)
        print(clusters)

        print("\n--- Example Raw Names for Top Clusters ---")
        # Ensure we iterate over the index as values
        cluster_patterns = clusters.index.tolist()
        for pattern in cluster_patterns[:5]:
            print(f"\nPattern: '{pattern}'")
            examples = (
                missing_merch[missing_merch["cleaned_name"] == pattern]["name"]
                .head(3)
                .values
            )
            for ex in examples:
                print(f"  - {ex}")


def analyze_recurring_amounts(df: pd.DataFrame) -> None:
    """Analyzes frequent transaction amounts to identify potential recurring payments.

    Args:
        df (pd.DataFrame): The transactions DataFrame.
    """
    print("\n--- Amount Frequency (Recurring Payments?)")
    # Round to 2 decimals, look for counts > 2
    amount_counts = df["amount"].value_counts()
    recurring = amount_counts[amount_counts > 2].head(10)
    print(recurring)

    # Check what these amounts correspond to
    print("\n--- Potential Subscriptions (by Amount) ---")
    recurring_amounts = recurring.index.tolist()
    for amt in recurring_amounts[:5]:
        print(f"\nAmount: ${amt}")
        # Show merchants/names associated with this amount
        subset = df[df["amount"] == amt]
        print(subset[["date", "merchant_name", "name"]].head(3).to_string())


def analyze_transaction_days(df: pd.DataFrame) -> None:
    """Analyzes transaction frequency by day of the month.

    Args:
        df (pd.DataFrame): The transactions DataFrame.
    """
    print("\n--- Transactions by Day of Month (Top Days) ---")
    # Need to avoid SettingWithCopyWarning if df is a slice
    df_copy = df.copy()
    df_copy["day"] = df_copy["date"].dt.day
    print(df_copy["day"].value_counts().sort_index().head(10))


def analyze_deep_data() -> None:
    """Performs deep clustering and frequency analysis on transaction data."""
    df = get_transactions_df()
    if df.empty:
        print("No transactions found.")
        return

    print(f"Total Transactions: {len(df)}")

    analyze_missing_merchants(df)
    analyze_recurring_amounts(df)
    analyze_transaction_days(df)


if __name__ == "__main__":
    analyze_deep_data()
