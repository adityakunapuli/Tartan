from datetime import date
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship, JSON
from sqlalchemy import Column

class Security(SQLModel, table=True):
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

    holdings: list["InvestmentHolding"] = Relationship(back_populates="security")

class InvestmentTransaction(SQLModel, table=True):
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

    security: Optional["Security"] = Relationship()

class InvestmentHolding(SQLModel, table=True):
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

    security: Optional["Security"] = Relationship(back_populates="holdings")
