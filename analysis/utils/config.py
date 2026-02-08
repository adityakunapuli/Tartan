"""Configuration utilities for the application."""

import os
from dotenv import load_dotenv, find_dotenv
from sqlmodel import Session, select
from analysis.db.models import Account

load_dotenv(find_dotenv(), override=True)


def parse_csv_env(name: str) -> set[str]:
    """Parses a comma-separated environment variable into a set of strings.

    Args:
        name (str): The name of the environment variable.

    Returns:
        set[str]: A set of stripped strings from the CSV value.
    """
    value = os.getenv(name, "")
    parts = set()
    for p in value.split(","):
        p = p.strip()
        # Remove surrounding quotes if present
        if (p.startswith('"') and p.endswith('"')) or (
            p.startswith("'") and p.endswith("'")
        ):
            p = p[1:-1]
        if p:
            parts.add(p)
    return parts


def get_excluded_account_ids(session: Session) -> set[str]:
    """Resolves account IDs to exclude based on env vars and database names.

    Args:
        session (Session): The database session.

    Returns:
        set[str]: A set of account IDs to exclude.
    """
    excluded_ids = parse_csv_env("EXCLUDED_ACCOUNT_IDS")
    excluded_names = {n.lower() for n in parse_csv_env("EXCLUDED_ACCOUNT_NAMES")}
    if not excluded_names:
        return excluded_ids

    accounts = session.exec(select(Account)).all()
    for a in accounts:
        if a.name and a.name.lower() in excluded_names:
            excluded_ids.add(a.account_id)
    return excluded_ids
