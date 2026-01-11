"""Reporting script for deep analysis of transaction patterns and anomalies."""

import re
from analysis.services.data_layer import get_transactions_df

def clean_name(name: str) -> str:
    """Cleans the transaction name by removing common prefixes, dates, and special characters.

    Args:
        name (str): The raw transaction name.

    Returns:
        str: The cleaned and normalized transaction name.
    """
    if not name:
        return ""
    # Remove common prefixes
    name = re.sub(r'^(CHECKCARD|PURCHASE|POS PURCHASE|DEBIT CARD PURCHASE)\s*\d*\s*', '', name, flags=re.IGNORECASE)
    # Remove dates (MM/DD, MM-DD)
    name = re.sub(r'\b\d{1,2}[/-]\d{1,2}\b', '', name)
    # Remove large number sequences (IDs, card numbers) - 4 or more digits
    name = re.sub(r'\b\d{4,}\b', '', name)
    # Remove special chars
    name = re.sub(r'[^\w\s]', ' ', name)
    # Collapse whitespace
    return ' '.join(name.split()).upper()

def analyze_deep_data() -> None:
    """Performs deep clustering and frequency analysis on transaction data."""
    df = get_transactions_df()
    if df.empty:
        print("No transactions found.")
        return

    print(f"Total Transactions: {len(df)}")
    
    # Filter for missing merchant
    missing_merch = df[df['merchant_name'].isnull()].copy()
    print(f"\nTransactions with Missing Merchant: {len(missing_merch)}")

    if not missing_merch.empty:
        # 1. Clean Names Clustering
        missing_merch['cleaned_name'] = missing_merch['name'].apply(clean_name)
        
        print("\n--- Top Clusters by Cleaned Name (Missing Merchant) ---")
        clusters = missing_merch['cleaned_name'].value_counts().head(20)
        print(clusters)
        
        print("\n--- Example Raw Names for Top Clusters ---")
        for pattern in clusters.index[:5]:
            print(f"\nPattern: '{pattern}'")
            examples = missing_merch[missing_merch['cleaned_name'] == pattern]['name'].head(3).values
            for ex in examples:
                print(f"  - {ex}")

    # 2. Amount Analysis
    print("\n--- Amount Frequency (Recurring Payments?)")
    # Round to 2 decimals, look for counts > 2
    amount_counts = df['amount'].value_counts()
    recurring = amount_counts[amount_counts > 2].head(10)
    print(recurring)
    
    # Check what these amounts correspond to
    print("\n--- Potential Subscriptions (by Amount) ---")
    for amt in recurring.index[:5]:
        print(f"\nAmount: ${amt}")
        # Show merchants/names associated with this amount
        subset = df[df['amount'] == amt]
        print(subset[['date', 'merchant_name', 'name']].head(3).to_string())

    # 3. Day of Month Analysis (Rent/Bills)
    print("\n--- Transactions by Day of Month (Top Days) ---")
    df['day'] = df['date'].dt.day
    print(df['day'].value_counts().sort_index().head(10)) # First 10 days of month

if __name__ == "__main__":
    analyze_deep_data()
