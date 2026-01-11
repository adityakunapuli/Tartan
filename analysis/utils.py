"""Utility functions for data cleaning and processing."""

import re
import datetime
from typing import Any


def clean_name(name: str) -> str:
    """Cleans the transaction name by removing common prefixes, dates, and special characters.

    Args:
        name (str): The raw transaction name.

    Returns:
        str: The cleaned and normalized transaction name.
    """
    if not name:
        return "UNKNOWN"
    # Remove common prefixes
    name = re.sub(
        r"^(CHECKCARD|PURCHASE|POS PURCHASE|DEBIT CARD PURCHASE)\s*\d*\s*",
        "",
        name,
        flags=re.IGNORECASE,
    )
    # Remove dates (MM/DD, MM-DD)
    name = re.sub(r"\b\d{1,2}[/-]\d{1,2}\b", "", name)
    # Remove large number sequences (IDs)
    name = re.sub(r"\b\d{4,}\b", "", name)
    # Remove special chars
    name = re.sub(r"[^\w\s]", " ", name)
    return " ".join(name.split()).upper()


def make_json_serializable(data: Any) -> Any:
    """Recursively converts datetime objects to ISO format strings.

    Args:
        data (Any): The data to serialize (dict, list, or scalar).

    Returns:
        Any: The JSON-serializable data.
    """
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_json_serializable(v) for v in data]
    elif isinstance(data, (datetime.date, datetime.datetime)):
        return data.isoformat()
    return data
