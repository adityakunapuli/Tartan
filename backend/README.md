# Backend - FastAPI

Handles Plaid API interaction and SQLite storage.

## Key Files
- `main.py`: The FastAPI server.
- `financial_data.db`: SQLite database (ignored by git).

## Setup
Ensure the root `.venv` is active or use the absolute path to the venv python:
```bash
..\.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```
