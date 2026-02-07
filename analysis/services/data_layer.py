"""Data access layer for retrieving financial data as DataFrames."""

import os
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from analysis.db.session import engine
from analysis.utils import clean_name

load_dotenv(find_dotenv(), override=True)


def _parse_csv_env(name: str) -> set[str]:
    value = os.getenv(name, "")
    return {v.strip() for v in value.split(",") if v.strip()}


def _apply_account_exclusions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "account_id" not in df.columns:
        return df

    excluded_ids = _parse_csv_env("EXCLUDED_ACCOUNT_IDS")
    excluded_names = {n.lower() for n in _parse_csv_env("EXCLUDED_ACCOUNT_NAMES")}

    if excluded_names:
        accounts = pd.read_sql("SELECT account_id, name FROM accounts", engine)
        if not accounts.empty:
            name_map = {
                row["account_id"]: str(row["name"]).lower()
                for _, row in accounts.iterrows()
            }
            excluded_ids |= {
                acc_id for acc_id, name in name_map.items() if name in excluded_names
            }

    if excluded_ids:
        return df[~df["account_id"].isin(excluded_ids)].copy()

    return df


def get_denormalized_holdings(date_captured: str | None = None) -> pd.DataFrame:
    """Returns a DataFrame of investment holdings joined with security details.

    Args:
        date_captured (str | None): The date to retrieve holdings for.
            If None, returns the latest snapshot.

    Returns:
        pd.DataFrame: DataFrame containing holdings and security data.
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

    df = pd.read_sql(query, engine)
    return _apply_account_exclusions(df)


def get_transactions_df() -> pd.DataFrame:
    """Returns all transactions as a DataFrame with parsed dates.

    Returns:
        pd.DataFrame: DataFrame containing all transactions.
    """
    df = pd.read_sql("SELECT * FROM transactions", engine)
    df = _apply_account_exclusions(df)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_enriched_transactions_df() -> pd.DataFrame:
    """Returns transactions with an 'enriched_category' column applied from CategoryRules.

    Returns:
        pd.DataFrame: DataFrame containing enriched transactions.
    """
    df = get_transactions_df()
    if df.empty:
        return df

    # Load rules
    rules = pd.read_sql("SELECT * FROM category_rules", engine)

    if rules.empty:
        df["enriched_category"] = "Uncategorized"
        df["flow_type"] = "EXPENSE"
        return df

    # Create lookup dicts
    # Helper to pack category and flow_type
    rules["value_dict"] = rules.apply(
        lambda x: {"category": x["category"], "flow_type": x["flow_type"]}, axis=1
    )

    merchant_map = (
        rules[rules["match_type"] == "merchant_name"]
        .set_index("match_value")["value_dict"]
        .to_dict()
    )
    pattern_map = (
        rules[rules["match_type"] == "pattern"]
        .set_index("match_value")["value_dict"]
        .to_dict()
    )

    def apply_rule(row: pd.Series) -> pd.Series:
        default = pd.Series({'enriched_category': 'Uncategorized', 'flow_type': 'EXPENSE'})
        
        # 1. Try Merchant Match
        if row['merchant_name'] and row['merchant_name'] in merchant_map:
            match = merchant_map[row['merchant_name']]
            return pd.Series({'enriched_category': match['category'], 'flow_type': match['flow_type']})
            
        # 2. Try Pattern Match
        c_name = clean_name(row['name'])
        if c_name in pattern_map:
            match = pattern_map[c_name]
            return pd.Series({'enriched_category': match['category'], 'flow_type': match['flow_type']})
            
        return default

    df[["enriched_category", "flow_type"]] = df.apply(apply_rule, axis=1)
    
    # 4. Vectorized Heuristic Fallback (Safety Net)
    # Catch transfers and income that might have been missed
    mask = df['name'].str.upper().str.contains('TRANSFER|GOLDMAN SACHS|ONLINE BANKING|PAYMENT TO|CREDIT CRD|VACP TREAS|VA BENEF|GUSTO|PAYROLL|MR. COOPER', regex=True, na=False)
    uncat_mask = df['enriched_category'] == 'Uncategorized'
    
    final_mask = mask & uncat_mask
    
    if final_mask.any():
        # Determine if it's Income or Transfer based on common keywords
        # This is a bit crude but safer than 'EXPENSE'
        income_mask = df['name'].str.upper().str.contains('VACP TREAS|VA BENEF|GUSTO|PAYROLL', regex=True, na=False)
        
        df.loc[final_mask & income_mask, 'enriched_category'] = 'Income'
        df.loc[final_mask & income_mask, 'flow_type'] = 'INCOME'
        
        # Everything else in the final_mask is a Transfer
        df.loc[final_mask & ~income_mask, 'enriched_category'] = 'Transfer'
        df.loc[final_mask & ~income_mask, 'flow_type'] = 'TRANSFER'
        
    return df

def get_investment_transactions_df() -> pd.DataFrame:
    """Returns all investment transactions joined with securities.

    Returns:
        pd.DataFrame: DataFrame containing investment transactions and security info.
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
    df = _apply_account_exclusions(df)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df