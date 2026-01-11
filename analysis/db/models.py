"""SQLModel database models for financial data."""

from datetime import date
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship, JSON
from sqlalchemy import Column


class Transaction(SQLModel, table=True):
    """SQLModel for bank transactions."""

    __tablename__ = "transactions"

    transaction_id: str = Field(primary_key=True)
    account_id: str = Field(index=True)
    date: date
    name: str
    amount: float
    currency: str | None = None
    flow_type: str | None = None  # 'INCOME', 'EXPENSE', 'TRANSFER'
    
    # JSON fields need explicit SA column for SQLite/PG compatibility
    category: list | dict | None = Field(default=None, sa_column=Column(JSON))
    category_id: str | None = None
    pending: bool
    merchant_name: str | None = None
    payment_channel: str | None = None
    raw_json: dict | list | None = Field(default=None, sa_column=Column(JSON))


class Security(SQLModel, table=True):
    """SQLModel for securities (stocks, funds, etc.)."""

    __tablename__ = "securities"

    security_id: str = Field(primary_key=True)
    name: str | None = None
    ticker_symbol: str | None = None
    institution_security_id: str | None = None
    type: str | None = None
    close_price: float | None = None
    close_price_as_of: date | None = None
    currency: str | None = None
    is_cash_equivalent: bool | None = None
    raw_json: dict | list | None = Field(default=None, sa_column=Column(JSON))

    # Relationships
    holdings: list["InvestmentHolding"] = Relationship(back_populates="security")


class InvestmentTransaction(SQLModel, table=True):
    """SQLModel for investment transactions."""

    __tablename__ = "investment_transactions"

    investment_transaction_id: str = Field(primary_key=True)
    account_id: str = Field(index=True)
    security_id: str = Field(foreign_key="securities.security_id", index=True)
    date: date
    name: str
    quantity: float
    amount: float
    price: float
    fees: float | None = None
    type: str
    subtype: str | None = None
    currency: str | None = None
    raw_json: dict | list | None = Field(default=None, sa_column=Column(JSON))

    # Relationships
    security: Optional[Security] = Relationship()


class InvestmentHolding(SQLModel, table=True):
    """SQLModel for investment holdings (positions)."""

    __tablename__ = "investment_holdings"

    id: int | None = Field(default=None, primary_key=True)
    date_captured: date = Field(index=True)
    account_id: str = Field(index=True)
    security_id: str = Field(foreign_key="securities.security_id", index=True)
    quantity: float
    institution_price: float
    institution_value: float
    cost_basis: float | None = None
    currency: str | None = None
    raw_json: dict | list | None = Field(default=None, sa_column=Column(JSON))

    # Relationships
    security: Optional[Security] = Relationship(back_populates="holdings")


class Account(SQLModel, table=True):
    """SQLModel for financial accounts."""

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
    raw_json: dict | list | None = Field(default=None, sa_column=Column(JSON))


class CategoryRule(SQLModel, table=True):
    """SQLModel for transaction categorization rules."""

    __tablename__ = "category_rules"

    id: int | None = Field(default=None, primary_key=True)
    match_value: str = Field(unique=True, index=True)
    match_type: str  # 'merchant_name' or 'name'
    flow_type: str  # 'INCOME', 'EXPENSE', 'TRANSFER'
    category: str


class PlaidItem(SQLModel, table=True):
    """SQLModel for Plaid Items (connections)."""

    __tablename__ = "plaid_items"

    access_token: str = Field(primary_key=True)
    item_id: str | None = None
    institution_id: str | None = None
    institution_name: str | None = None
    next_cursor: str | None = None
