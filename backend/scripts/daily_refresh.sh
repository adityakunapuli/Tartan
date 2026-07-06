#!/bin/bash

set -e

# Always run from project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

mkdir -p logs
LOG_FILE="logs/daily_refresh.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================================"
echo "Starting Daily Refresh at $(date)"
echo "Working Directory: $PROJECT_ROOT"
echo "========================================================"

# 1. Sync Data
echo "[Step 1] Syncing Data..."
uv run python -m modules.plaid_integration.sync

# 2. Categorize
echo "[Step 2] Categorizing Transactions..."
uv run python -m modules.analytics.categorizer

# 3. Report
echo "[Step 3] Generating Report..."
uv run python -m reports.portfolio_summary

echo "========================================================"
echo "Daily Refresh Completed Successfully at $(date)"
echo "========================================================"
