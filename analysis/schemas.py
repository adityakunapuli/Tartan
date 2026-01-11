"""Schemas for data validation and serialization."""

from pydantic import BaseModel
from typing import Optional
from datetime import date


class AccountSchema(BaseModel):
    """Pydantic model representing an account's financial data.

    Attributes:
        account_id (str): Unique identifier for the account.
        name (str): Name of the account.
        mask (str | None): Last 4 digits of the account number.
        type (str): The account type (e.g., 'depository', 'credit').
        subtype (str | None): The account subtype (e.g., 'checking', 'cd').
        current_balance (float | None): The current balance.
        available_balance (float | None): The available balance.
        iso_currency_code (str | None): The ISO currency code (e.g., 'USD').
        limit (float | None): Credit limit or overdraft limit.
        apy (float | None): Annual Percentage Yield (for interest-bearing accounts).
        interest_rate (float | None): Interest rate (for loans).
        maturity_date (date | None): Maturity date (for CDs/Loans).
        raw_json (dict | None): The raw JSON response from the provider.
    """

    account_id: str
    name: str
    mask: Optional[str] = None
    type: str
    subtype: Optional[str] = None
    current_balance: Optional[float] = None
    available_balance: Optional[float] = None
    iso_currency_code: Optional[str] = None
    limit: Optional[float] = None

    # New fields for completeness (CDs/HYS)
    apy: Optional[float] = None
    interest_rate: Optional[float] = None
    maturity_date: Optional[date] = None

    raw_json: Optional[dict] = None

    class Config:
        from_attributes = True
