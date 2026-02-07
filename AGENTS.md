# Repository Guidelines

## Project Structure & Module Organization
- `analysis/`: Python "analysis suite".
- `analysis/services/`: Plaid sync + LLM categorization (core pipeline).
- `analysis/reporting/`: Reports (e.g. portfolio/spending summaries).
- `analysis/db/`: SQLModel models + SQLite session; local DB lives at `analysis/financial_data.db`.
- `analysis/scripts/`: One-off utilities (e.g. `inspect_tokens.py`).
- `auth_utility/`: Plaid Link setup app (`backend/` FastAPI, `frontend/` React/Vite).
- `tests/`: Pytest tests (start here for regression coverage).

## Build, Test, and Development Commands
- Python env: copy `.env.example` to `.env` and fill `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ACCESS_TOKEN`.
- Auth utility (one-time linking): `cd auth_utility && pnpm install-all && pnpm start`.
- Sync data: `python -m analysis.main`.
- Categorize transactions (local LLM): `python -m analysis.services.llm_categorizer` (expects llama.cpp at `http://127.0.0.1:8080`).
- Reports: `python -m analysis.reporting.portfolio_summary`.
- Tests: `python -m pytest`.
- Lint: `ruff check .` and `pre-commit run -a`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, type hints where useful, and Google-style docstrings.
- Prefer small, testable functions in `analysis/services/` and keep DB writes localized.
- Frontend: follow the existing ESLint setup (`cd auth_utility/frontend && npm run lint`).

## Testing Guidelines
- Framework: pytest.
- Naming: `tests/test_*.py` with focused unit tests (sync, categorization, data layer).

## Commit & Pull Request Guidelines
- Commits commonly use prefixes like `Fix:`, `Refactor:`, `Cleanup:`, `Implement` — keep messages action-oriented.
- PRs should call out schema changes, new `.env` knobs, and any data-impacting behavior (sync/categorizer/reporting).

## Security & Configuration Tips
- Never commit `.env` or share `analysis/financial_data.db` (contains sensitive financial data).
- Useful `.env` knobs: `LLM_WORKERS`, `EXCLUDED_ACCOUNT_IDS`, `EXCLUDED_ACCOUNT_NAMES`.
