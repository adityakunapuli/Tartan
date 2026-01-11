"""Reporting script for deep analysis of transaction patterns and anomalies."""

from analysis.services.data_layer import get_transactions_df
from analysis.utils import clean_name


def analyze_deep_data() -> None:
    """Performs deep clustering and frequency analysis on transaction data."""
    df = get_transactions_df()
    if df.empty:
        print("No transactions found.")
        return

    print(f"Total Transactions: {len(df)}")

    # Filter for missing merchant
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

    # 2. Amount Analysis
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

    # 3. Day of Month Analysis (Rent/Bills)
    print("\n--- Transactions by Day of Month (Top Days) ---")
    df["day"] = df["date"].dt.day
    print(df["day"].value_counts().sort_index().head(10))  # First 10 days of month


if __name__ == "__main__":
    analyze_deep_data()