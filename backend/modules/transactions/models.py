from datetime import date
from sqlmodel import Field, SQLModel, JSON
from sqlalchemy import Column

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    transaction_id: str = Field(primary_key=True)
    account_id: str = Field(index=True)
    date: date
    name: str
    amount: float
    currency: str | None = None
    flow_type: str | None = None
    
    category: list | dict | None = Field(default=None, sa_column=Column(JSON))
    category_id: str | None = None
    pending: bool
    merchant_name: str | None = None
    payment_channel: str | None = None
    
    # New fields for Smart Tracking
    is_recurring: bool = Field(default=False)
    
    raw_json: dict | list | None = Field(default=None, sa_column=Column(JSON))
