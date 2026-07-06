"""Centralized configuration management."""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Set

# Automatically find and load the .env file in a REPL-safe way
env_path = find_dotenv()
load_dotenv(env_path)

class Settings(BaseSettings):
    """Application configuration constants."""

    # Paths (REPL-safe)
    ROOT_DIR: Path = Path(env_path).parent if env_path else Path.cwd()
    DB_FILE: Path = ROOT_DIR / "core" / "db" / "financial_data.db"
    DB_URL: str = f"sqlite:///{DB_FILE}"

    # Plaid Credentials
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"

    # Plaid Sync Settings (raw string to be parsed)
    PLAID_ACCESS_TOKEN: str = ""

    # Exclusions (raw string to be parsed)
    EXCLUDED_ACCOUNT_IDS: str = ""
    EXCLUDED_ACCOUNT_NAMES: str = ""

    model_config = SettingsConfigDict(
        env_file=env_path if env_path else ".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def plaid_access_tokens(self) -> List[str]:
        """Returns list of Plaid access tokens from the comma-separated env var."""
        return [t.strip() for t in self.PLAID_ACCESS_TOKEN.split(",") if t.strip()]

    @property
    def excluded_account_ids(self) -> Set[str]:
        """Returns set of account IDs to exclude from synchronization."""
        return {v.strip() for v in self.EXCLUDED_ACCOUNT_IDS.split(",") if v.strip()}

    @property
    def excluded_account_names(self) -> Set[str]:
        """Returns set of account names to exclude from synchronization."""
        return {
            v.strip().lower()
            for v in self.EXCLUDED_ACCOUNT_NAMES.split(",")
            if v.strip()
        }


settings = Settings()
