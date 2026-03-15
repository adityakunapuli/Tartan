"""Entry point for the financial data synchronization process."""

from services.plaid_sync import run_sync
from config import Config

if __name__ == "__main__":
    # Optional: validate config before running
    Config.validate()
    run_sync()