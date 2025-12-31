import sys
from pathlib import Path

# Ensure analysis dir is in path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
import pandas as pd
from models import engine, Transaction, InvestmentHolding, Security

def get_denormalized_holdings(date_captured=None) -> pd.DataFrame:
    """
    Returns a DataFrame of investment holdings joined with security details.
    If date_captured is None, returns the latest snapshot available.
    """
    query = """
    SELECT 
        h.date_captured,
        h.account_id,
        h.quantity,
        h.institution_price,
        h.institution_value,
        h.cost_basis,
        s.name as security_name,
        s.ticker_symbol,
        s.type as security_type,
        s.currency
    FROM investment_holdings h
    LEFT JOIN securities s ON h.security_id = s.security_id
    """
    
    if date_captured:
        query += f" WHERE h.date_captured = '{date_captured}'"
    else:
        # Default to latest date
        query += " WHERE h.date_captured = (SELECT MAX(date_captured) FROM investment_holdings)"
        
    return pd.read_sql(query, engine)

def get_transactions_df() -> pd.DataFrame:
    """
    Returns all transactions as a DataFrame with parsed dates.
    """
    df = pd.read_sql(pd.read_sql("SELECT * FROM transactions", engine).to_sql(), engine) if False else pd.read_sql("SELECT * FROM transactions", engine)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df
