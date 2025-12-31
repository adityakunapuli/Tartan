# Plaid Local Analysis

A local-first tool for analyzing your financial data using Plaid.

## Architecture
- **`analysis/`**: **Main Work Area.** Standalone Python scripts to fetch data and run analysis.
- **`backend/` & `frontend/`**: A utility web app used *only* to link your bank account and generate an Access Token.

## Workflow

### 1. Setup Authentication
1. Copy `.env.example` to `.env` and fill in your `PLAID_CLIENT_ID` and `PLAID_SECRET`.
2. Start the auth utility:
   ```bash
   pnpm install-all
   pnpm start
   ```
3. Open `http://localhost:5173`, link your bank account.
4. **Copy the Access Token** displayed on the screen and paste it into your `.env` file as `PLAID_ACCESS_TOKEN`.
5. Stop the web app (Ctrl+C). You don't need it anymore unless you need to link a new account.

### 2. Fetch Data
Run the fetcher script to download your transactions and investments to a local SQLite database (`analysis/financial_data.db`).

```bash
python analysis/data_fetcher.py
```

### 3. Analyze
Run the analysis script (or create your own) to query the local database.

```bash
python analysis/basic_analysis.py
```

## Requirements
- Python 3.x
- Node.js & pnpm