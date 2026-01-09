import pandas as pd
from analysis.db.session import engine
from analysis.utils import clean_name

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
    df = pd.read_sql("SELECT * FROM transactions", engine)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

def get_enriched_transactions_df() -> pd.DataFrame:
    """
    Returns transactions with an 'enriched_category' column applied from CategoryRules.
    """
    df = get_transactions_df()
    if df.empty:
        return df
    
    # Load rules
    rules = pd.read_sql("SELECT * FROM category_rules", engine)
    
    if rules.empty:
        df['enriched_category'] = 'Uncategorized'
        return df
        
    # Create lookup dicts
    # merchant_map: merchant_name -> category
    merchant_map = rules[rules['match_type'] == 'merchant_name'].set_index('match_value')['category'].to_dict()
    
    # pattern_map: cleaned_name_pattern -> category
    pattern_map = rules[rules['match_type'] == 'pattern'].set_index('match_value')['category'].to_dict()
    
    def apply_rule(row):
        # 1. Try Merchant Match
        if row['merchant_name'] and row['merchant_name'] in merchant_map:
            return merchant_map[row['merchant_name']]
            
        # 2. Try Pattern Match
        c_name = clean_name(row['name'])
        if c_name in pattern_map:
            return pattern_map[c_name]
            
        return 'Uncategorized'

    df['enriched_category'] = df.apply(apply_rule, axis=1)
    return df

def get_investment_transactions_df() -> pd.DataFrame:
    """
    Returns all investment transactions joined with securities.
    """
    query = """
    SELECT 
        it.*,
        s.name as security_name,
        s.ticker_symbol,
        s.type as security_type
    FROM investment_transactions it
    LEFT JOIN securities s ON it.security_id = s.security_id
    """
    df = pd.read_sql(query, engine)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df
