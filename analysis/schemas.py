from pydantic import BaseModel
from typing import Optional
from datetime import date

class AccountSchema(BaseModel):
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
