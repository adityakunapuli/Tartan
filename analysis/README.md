# Financial Analysis

This directory contains standalone scripts for fetching and analyzing your financial data. 
These scripts run independently of the web application.

## Prerequisites
1. Ensure your `.env` file in the project root has your `PLAID_CLIENT_ID`, `PLAID_SECRET`, and a valid `PLAID_ACCESS_TOKEN`.
   - If you don't have an access token yet, run the web app (`pnpm start` in root), link your account, and copy the token from the UI (or `.env` if using the experimental sync).

## Usage

### 1. Fetch Data
Run `data_fetcher.py` to download transactions and investments from Plaid into a local SQLite database (`financial_data.db`).

```bash
# From project root
python analysis/data_fetcher.py
```

### 2. Analyze Data
Run `basic_analysis.py` to view simple insights (Spending by Category, Portfolio Value).
This file is formatted with `#%%` markers, making it compatible with VS Code's Interactive Window or Jupyter functionality for chunk-based execution.

```bash
# From project root
python analysis/basic_analysis.py
```

## Files
- `data_fetcher.py`: Connects to Plaid API, fetches data, saves to `financial_data.db`.
- `basic_analysis.py`: Reads `financial_data.db` using Pandas and prints analysis.
- `financial_data.db`: SQLite database storing your financial data (local only, ignored by git).
