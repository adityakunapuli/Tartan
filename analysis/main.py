"""Entry point for the financial data synchronization process."""

from analysis.services.sync import run_sync

if __name__ == "__main__":
    run_sync()
