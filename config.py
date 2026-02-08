"""Centralized configuration management."""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 1. Load Environment Variables
# override=True ensures that if we change .env, the app picks it up without caching issues
load_dotenv(find_dotenv(), override=True)

class Config:
    """Application configuration constants."""

    # Paths
    ROOT_DIR = Path(__file__).parent.resolve()
    DB_FILE = ROOT_DIR / "financial_data.db"
    DB_URL = f"sqlite:///{DB_FILE}"

    # Plaid Credentials
    PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
    PLAID_SECRET = os.getenv("PLAID_SECRET")
    PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")
    
    # Plaid Sync Settings
    PLAID_ACCESS_TOKENS = [
        t.strip() 
        for t in os.getenv("PLAID_ACCESS_TOKEN", "").split(",") 
        if t.strip()
    ]
    
    # Exclusions
    EXCLUDED_ACCOUNT_IDS = {
        v.strip() 
        for v in os.getenv("EXCLUDED_ACCOUNT_IDS", "").split(",") 
        if v.strip()
    }
    
    EXCLUDED_ACCOUNT_NAMES = {
        v.strip().lower() 
        for v in os.getenv("EXCLUDED_ACCOUNT_NAMES", "").split(",") 
        if v.strip()
    }

    @classmethod
    def validate(cls):
        """Validates critical configuration."""
        if not cls.PLAID_CLIENT_ID or not cls.PLAID_SECRET:
            raise ValueError("Missing PLAID_CLIENT_ID or PLAID_SECRET in .env")
        if not cls.PLAID_ACCESS_TOKENS:
            # Not strictly fatal for some scripts, but fatal for sync
            pass

# Validate on import (optional, but good for catching issues early)
# Config.validate()
