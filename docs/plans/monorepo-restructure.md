# Monorepo Restructure: frontend/ + backend/

## Goal
Separate the existing Python/FastAPI backend from the new React/Vite frontend into a clean monorepo layout.

## New Structure

```
A:\projects\plaid-local\
├── backend/          ← existing codebase moved here
│   ├── main.py
│   ├── core/
│   ├── modules/
│   ├── reports/
│   ├── utils/
│   ├── data/
│   ├── scripts/
│   ├── tests/
│   ├── auth.html
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile
│   ├── ...
├── frontend/         ← new React/Vite dashboard
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
├── docs/             ← project-wide documentation (stays at root)
├── .gitignore        ← updated for monorepo
├── AGENTS.md         ← updated to reflect new layout
```

## Key Design Decision: No Import Changes
Working directory becomes `backend/` — Python's `sys.path` adds the script's directory automatically, so `from modules.accounts.models import Account` resolves correctly from within `backend/`. All commands will be run as `cd backend && uv run ...`.

## Execution Steps
1. Move all existing files/directories into `backend/`
2. Update root `.gitignore` to cover both `backend/` and `frontend/` artifacts
3. Update `AGENTS.md` to reflect new layout
4. Scaffold `frontend/` with React + Vite + Recharts + Iconify
5. Create root-level scripts / docs to tie the monorepo together
