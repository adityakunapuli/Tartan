from datetime import date
from sqlmodel import Field, SQLModel, JSON
from sqlalchemy import Column

class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    account_id: str = Field(primary_key=True)
    name: str
    mask: str | None = None
    type: str
    subtype: str | None = None
    current_balance: float | None = None
    available_balance: float | None = None
    iso_currency_code: str | None = None
    limit: float | None = None
    apy: float | None = None
    interest_rate: float | None = None
    maturity_date: date | None = None
    last_updated: date
    sync_interval_hours: int = Field(default=24) # New field for APScheduler
    raw_json: dict | list | None = Field(default=None, sa_column=Column(JSON))

class Liability(SQLModel, table=True):
    __tablename__ = "liabilities"

    account_id: str = Field(primary_key=True)
    type: str
    aprs: list[dict] | None = Field(default=None, sa_column=Column(JSON))
    is_overdue: bool | None = None
    last_payment_amount: float | None = None
    last_payment_date: date | None = None
    next_payment_due_date: date | None = None
    minimum_payment_amount: float | None = None
    origination_date: date | None = None
    principal_amount: float | None = None
    interest_rate_percentage: float | None = None
    expected_payoff_date: date | None = None
    raw_json: dict | list | None = Field(default=None, sa_column=Column(JSON))

class PlaidItem(SQLModel, table=True):
    __tablename__ = "plaid_items"

    access_token: str = Field(primary_key=True)
    item_id: str | None = None
    institution_id: str | None = None
    institution_name: str | None = None
    next_cursor: str | None = None
