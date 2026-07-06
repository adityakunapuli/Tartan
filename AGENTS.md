# Repository Guidelines

## Project Structure & Module Organization
- `core/`: Database initialization, configuration, and scheduling. `financial_data.db` lives in `core/db/`.
- `modules/`: Core business logic (accounts, analytics, plaid integration, transactions).
- `reports/`: Reporting scripts (e.g., portfolio/spending summaries, deep analysis).
- `utils/`: Helper utilities and logging.
- `data/`: Raw CSV exports and external datasets.
- `scripts/`: PowerShell/Bash scripts for daily syncing.
- `tests/`: Pytest suite (start here for regression coverage).
- `auth.html`: Single-page Plaid Link setup UI.
- `main.py`: FastAPI application entry point.

## Build, Test, and Development Commands
- Python env: copy `.env.example` to `.env` and fill `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ACCESS_TOKEN`.
- Auth utility (one-time linking): `uv run python main.py` then visit `http://localhost:8000/`.
- Daily Sync Pipeline: run `./scripts/daily_refresh.sh` (or `.ps1`).
- Sync data manually: `uv run python -m modules.plaid_integration.sync`.
- Categorize manually: `uv run python -m modules.analytics.categorizer` (expects llama.cpp at `http://127.0.0.1:8080`).
- Reports manually: `uv run python -m reports.portfolio_summary`.
- Tests: `uv run pytest`.
- Lint: `uv run ruff check .` and `uv run pre-commit run -a`.

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
