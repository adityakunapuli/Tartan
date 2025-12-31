# Plaid Local Analysis

A local-first tool for analyzing your financial data using Plaid.

## Architecture
- **`analysis/`**: **Main Work Area.** Standalone Python scripts to fetch data and run analysis.
- **`auth_utility/`**: A utility web app used *only* to link your bank account and generate an Access Token.
- **`.venv/`**: Python virtual environment.

## Workflow

### 1. Setup Authentication
1. Copy `.env.example` to `.env` and fill in your `PLAID_CLIENT_ID` and `PLAID_SECRET`.
2. Start the auth utility:
   ```bash
   cd auth_utility
   pnpm install-all
   pnpm start
   ```
3. Open `http://localhost:5173`, link your bank account.
4. **Copy the Access Token** displayed on the screen and paste it into your `.env` file (in the project root) as `PLAID_ACCESS_TOKEN`.
5. Stop the web app (Ctrl+C).

### 2. Fetch Data
Return to the project root and run the fetcher script to download your transactions and investments to a local SQLite database (`analysis/financial_data.db`).

```bash
# From project root
python analysis/data_fetcher.py
```

### 3. Analyze
Run the analysis script to query the local database.

```bash
# From project root
python analysis/basic_analysis.py
```
