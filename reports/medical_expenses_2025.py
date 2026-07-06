"""Medical expenses report generator."""

import json
from datetime import date

import pandas as pd

from modules.transactions.logic import get_enriched_transactions_df


# Ensure the root project directory is in the Python path
def get_medical_report(
    start_date: str = "2025-01-01",
    end_date: str | None = None,
    csv=False,
    exclude_debits=False,
):
    """3Generates a report of medical expenses for a given date range."""
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    print(f"Fetching and processing transactions from {start_date} to {end_date}...")
    df = get_enriched_transactions_df()

    # Filter for date range and positive amounts
    mask = df["date"] >= start_date
    mask &= df["date"] <= end_date
    if exclude_debits:
        mask &= df["amount"] > 0
    df = df[mask]

    # Helper to check Plaid category
    def is_plaid_medical(cat_val):
        if not cat_val or pd.isna(cat_val):
            return False
        cat_str = str(cat_val).lower()
        keywords = [
            "health",
            "pharmacies",
            "glasses",
            "optometrist",
            "medical",
            "dentist",
            "pharmacy",
        ]
        return any(k in cat_str for k in keywords)

    mask_enriched = df["enriched_category"] == "Health"
    mask_plaid = df["category"].apply(is_plaid_medical)

    medical_df = df[mask_enriched | mask_plaid].copy()

    # Sort by date
    medical_df = medical_df.sort_values(by="date")

    print("\n" + "=" * 120)
    print(f"MEDICAL EXPENSES REPORT: {start_date} to {end_date}")
    print("=" * 120)

    print(
        f"{'Date':<10} | {'Amount':<10} | {'Merchant / Name':<35} | {'Enriched Cat':<15} | {'Plaid Categories'}"
    )
    print("-" * 120)

    for _, row in medical_df.iterrows():
        # Clean up name display
        name = (
            row["merchant_name"]
            if pd.notna(row["merchant_name"]) and row["merchant_name"]
            else row["name"]
        )
        name_trunc = (name[:32] + "...") if len(str(name)) > 35 else str(name)

        # Clean up Plaid category display
        try:
            cat_list = json.loads(row["category"]) if pd.notna(row["category"]) else []
            if isinstance(cat_list, list):
                plaid_cat = " > ".join(cat_list)
            else:
                plaid_cat = str(cat_list)
        except:
            plaid_cat = str(row["category"])

        plaid_cat_trunc = (plaid_cat[:38] + "...") if len(plaid_cat) > 38 else plaid_cat

        print(
            f"{row['date'].strftime('%Y-%m-%d')} | ${row['amount']:>8.2f} | {name_trunc:<35} | {row['enriched_category']:<15} | {plaid_cat_trunc}"
        )

    print("-" * 120)
    total = medical_df["amount"].sum()
    print(f"TOTAL MEDICAL EXPENSES: ${total:,.2f}")
    print(f"TOTAL TRANSACTIONS:   {len(medical_df)}")
    print("=" * 120)
    if csv:
        medical_df.to_csv(
            index=False, path_or_buf=f"medical_expenses_{start_date}_to_{end_date}.csv"
        )
    return medical_df


if __name__ == "__main__":
    df = get_medical_report("2025-01-01", "2025-12-31")
