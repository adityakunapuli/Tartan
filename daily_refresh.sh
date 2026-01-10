#!/bin/bash

# Ensure script fails on first error
set -e

# Change directory to the script's location (project root)
cd "$(dirname "$0")"

# Ensure log directory exists
mkdir -p logs
LOG_FILE="logs/daily_refresh.log"

# Redirect stdout and stderr to the log file (and console)
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================================"
echo "Starting Daily Refresh at $(date)"
echo "========================================================"

# Activate Virtual Environment
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "WARNING: .venv/bin/activate not found. Attempting to run with system python."
fi

# 1. Sync Data
echo "[Step 1] Syncing Data..."
python -m analysis.main

# 2. Categorize
echo "[Step 2] Categorizing Transactions..."
python -m analysis.services.llm_categorizer

# 3. Report
echo "[Step 3] Generating Report..."
python -m analysis.reporting.portfolio_summary

echo "========================================================"
echo "Daily Refresh Completed Successfully at $(date)"
echo "========================================================"
