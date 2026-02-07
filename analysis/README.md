# Financial Analysis Suite

This directory contains the logic for the "Local Environment" shown in the root README diagrams.

## Key Modules

### `services.sync`
- Fetches data from Plaid API.
- Supports pagination for large transaction histories (default 2 years).
- Stores raw JSON responses for future-proofing.

### `services.llm_categorizer`
- **The Brains.** Connects to your local LLM to classify transactions.
- Clusters transactions by `merchant_name` or `cleaned_name` (regex pattern).
- Sends rich context (average amount, frequency, payment channel) to the LLM for higher accuracy.
- Saves decisions as rules in `category_rules` table.

### `reporting.portfolio_summary`
- Generates the final view.
- Joins `transactions` with `category_rules` to show spending by enriched category.
- Calculates historical investment flows (Buys vs Sells) and Fees.

## Running
Execute modules as scripts from the **project root**:

```bash
# Sync
python -m analysis.main

# Categorize
python -m analysis.services.llm_categorizer

# Report
python -m analysis.reporting.portfolio_summary
```

## Manual Data (Gitignored)
Sensitive personal inputs are stored outside tracked code in `.archive/manual_data.json`.
This file is gitignored and loaded by `analysis/reporting/financial_health.py` at runtime.

Expected format:

```json
{
  "monthly_spouse_income": 0.0,
  "vesting_schedule": [
    {
      "description": "RSU Vest 1",
      "date": "2026-05-15",
      "amount_post_tax": 12345.67
    }
  ]
}
```
