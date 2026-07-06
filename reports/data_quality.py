"""Reporting script for analyzing the quality and consistency of transaction data."""

from modules.transactions.logic import get_transactions_df


def analyze_transaction_data() -> None:
    """Analyzes transaction data for merchant coverage and category consistency."""
    df = get_transactions_df()
    if df.empty:
        print("No transactions found to analyze.")
        return

    print(f"Total Transactions: {len(df)}")

    # 1. Merchant Name Coverage
    missing_merchant = df["merchant_name"].isnull().sum()
    print("\n--- Merchant Name Coverage ---")
    print(
        f"Transactions with Merchant Name: {len(df) - missing_merchant} ({(len(df) - missing_merchant) / len(df):.1%})"
    )
    print(
        f"Transactions MISSING Merchant Name: {missing_merchant} ({(missing_merchant) / len(df):.1%})"
    )

    # 2. Name vs Merchant Name sample (where merchant_name exists)
    print("\n--- Name vs Merchant Name (Sample) ---")
    sample = df[df["merchant_name"].notnull()].sample(min(10, len(df)))
    print(sample[["name", "merchant_name", "category"]].to_string())

    # 3. Name vs Merchant Name sample (where merchant_name is MISSING)
    if missing_merchant > 0:
        print("\n--- Transactions missing Merchant Name (Sample) ---")
        missing_sample = df[df["merchant_name"].isnull()].sample(
            min(10, missing_merchant)
        )
        print(missing_sample[["name", "amount", "category"]].to_string())

    # 4. Category Consistency (Does one merchant have multiple Plaid categories?)
    print("\n--- Category Consistency by Merchant ---")
    if not df[df["merchant_name"].notnull()].empty:
        # Convert category list/string to simple string for grouping
        df["cat_str"] = df["category"].astype(str)
        merchant_cats = df.groupby("merchant_name")["cat_str"].nunique()
        inconsistent = merchant_cats[merchant_cats > 1]

        if not inconsistent.empty:
            print(
                f"Found {len(inconsistent)} merchants with multiple Plaid categories:"
            )
            print(inconsistent.head(5))

            # Show example of inconsistency
            example_merchant = inconsistent.index[0]
            print(f"\nExample Inconsistency ({example_merchant}):")
            print(
                df[df["merchant_name"] == example_merchant][
                    ["date", "name", "category"]
                ].to_string()
            )
        else:
            print(
                "Plaid categories are consistent per merchant (for the data we have)."
            )


if __name__ == "__main__":
    analyze_transaction_data()
