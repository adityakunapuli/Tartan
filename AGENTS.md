# Repository Guidelines

## Monorepo Structure

```
plaid-local/
├── backend/         ← Python/FastAPI backend (uv)
│   ├── core/        DB init, config, scheduling. DB at core/db/financial_data.db
│   ├── modules/     Business logic (accounts, analytics, plaid, transactions, investments, rules)
│   ├── reports/     Reporting scripts
│   ├── utils/       Helpers and logging
│   ├── data/        Raw CSV exports
│   ├── scripts/     Sync scripts (PowerShell/Bash)
│   ├── tests/       Pytest suite
│   ├── main.py      FastAPI entry point
│   └── auth.html    Legacy Plaid Link UI (deprecated by dashboard)
├── frontend/        ← React + Vite dashboard
│   ├── src/
│   └── ...
└── docs/            Project documentation
```

## Build, Test, and Development Commands
- Python env: copy `backend/.env.example` to `backend/.env` and fill `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ACCESS_TOKEN`.
- Auth utility (one-time linking): `cd backend && uv run python main.py` then visit `http://localhost:8000/`.
- Daily Sync Pipeline: run `cd backend && ./scripts/daily_refresh.sh` (or `.ps1`).
- Sync data manually: `cd backend && uv run python -m modules.plaid_integration.sync`.
- Categorize manually: `cd backend && uv run python -m modules.analytics.categorizer` (expects llama.cpp at `http://127.0.0.1:8080`).
- Reports manually: `cd backend && uv run python -m reports.portfolio_summary`.
- Tests: `cd backend && uv run pytest`.
- Lint: `cd backend && uv run ruff check .` and `cd backend && uv run pre-commit run -a`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, type hints where useful, and Google-style docstrings.
- Prefer small, testable functions in `modules/` and keep DB writes localized.

## Testing Guidelines
- Framework: pytest.
- Naming: `tests/test_*.py` with focused unit tests.

## Commit & Pull Request Guidelines
- Commits commonly use prefixes like `Fix:`, `Refactor:`, `Cleanup:`, `Implement`.
- PRs should call out schema changes, new `.env` knobs, and any data-impacting behavior.

## Security & Configuration Tips
- Never commit `.env` or share `core/db/financial_data.db` (contains sensitive financial data).
- Useful `.env` knobs: `LLM_WORKERS`, `EXCLUDED_ACCOUNT_IDS`, `EXCLUDED_ACCOUNT_NAMES`.
