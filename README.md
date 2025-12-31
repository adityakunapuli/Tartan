# Plaid Local Analysis

A tool to sync Plaid financial data to a local SQLite database for analysis.

## Project Structure
- `backend/`: FastAPI server and SQLite database (`financial_data.db`).
- `frontend/`: React + Vite frontend.
- `.venv/`: Python virtual environment.

## Quick Start

1. **Setup Env**: Copy `.env.example` to `.env` and add your Plaid keys and `PLAID_ACCESS_TOKEN`.
2. **Install Dependencies**:
   ```bash
   pnpm install-all
   ```
3. **Run App**:
   ```bash
   pnpm start
   ```
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000

## How it works
- The **Sync** button in the UI triggers the backend to fetch the last 30 days of data from Plaid and save it to `backend/financial_data.db`.
- The UI reads directly from the local database, allowing for fast browsing without constant API calls.
