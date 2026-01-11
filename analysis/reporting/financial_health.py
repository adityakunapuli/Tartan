"""Reporting script for personal financial health and strategy."""

import pandas as pd
from analysis.services.data_layer import get_enriched_transactions_df
from analysis.db.session import engine

def get_current_liquidity() -> float:
    """Calculates total liquid cash from depository accounts.

    Returns:
        float: Total available balance in checking/savings accounts.
    """
    # We only count 'depository' accounts (Checking/Savings) as liquid cash.
    # Exclude 'credit', 'loan', 'investment'.
    query = "SELECT current_balance FROM accounts WHERE type = 'depository'"
    df = pd.read_sql(query, engine)
    return df['current_balance'].sum() if not df.empty else 0.0

def get_current_debt() -> float:
    """Calculates total high-interest debt (Credit Cards).

    Returns:
        float: Total balance of credit card accounts.
    """
    query = "SELECT current_balance FROM accounts WHERE type = 'credit'"
    df = pd.read_sql(query, engine)
    return df['current_balance'].sum() if not df.empty else 0.0

def analyze_financial_health() -> None:
    """Executes the financial strategy logic."""
    print("\n========================================================")
    print("       PERSONAL FINANCIAL STRATEGY ENGINE       ")
    print("========================================================")

    # 1. Calculate True Burn Rate
    df = get_enriched_transactions_df()
    if df.empty:
        print("No transactions found. Cannot calculate burn rate.")
        return

    # Filter: Last 6 months AND flow_type == 'EXPENSE'
    # Assuming 'date' is already datetime from data_layer
    latest_date = df['date'].max()
    six_months_ago = latest_date - pd.DateOffset(months=6)
    
    # We exclude 'TRANSFER' and 'INCOME' to get true spending
    expenses = df[
        (df['date'] >= six_months_ago) & 
        (df['flow_type'] == 'EXPENSE') &
        (df['amount'] > 0) # Safety check, expenses are positive in Plaid
    ]
    
    if expenses.empty:
        print("No expenses found in the last 6 months.")
        return

    total_spend = expenses['amount'].sum()
    monthly_burn = total_spend / 6.0
    
    print(f"\n[METRIC] True Burn Rate (6-mo Avg): ${monthly_burn:,.2f} / month")
    print(f"  -> Total Spend (6-mo): ${total_spend:,.2f}")
    
    # 2. Target Emergency Fund
    target_cash = monthly_burn * 6.0
    print(f"[METRIC] Target Emergency Fund (6 Months): ${target_cash:,.2f}")
    
    # 3. Current State
    current_cash = get_current_liquidity()
    current_debt = get_current_debt()
    
    print(f"\n[STATUS] Current Liquid Cash: ${current_cash:,.2f}")
    print(f"[STATUS] Current Credit Debt: ${current_debt:,.2f}")
    
    # 4. Strategy Execution
    deployable_cash = current_cash - target_cash
    
    print("\n--- STRATEGY EXECUTION ---")
    
    if deployable_cash > 0:
        print(f"✅ SURPLUS DETECTED: You have ${deployable_cash:,.2f} in excess cash.")
        
        if current_debt > 0:
            pay_amount = min(deployable_cash, current_debt)
            print(f"🚨 STRATEGY ALERT: Pay off ${pay_amount:,.2f} of debt IMMEDIATELY.")
            
            remaining_surplus = deployable_cash - pay_amount
            if remaining_surplus > 0:
                print(f"  -> After debt payoff, you still have ${remaining_surplus:,.2f} surplus.")
                print("  -> Recommendation: Invest in Tax-Advantaged Accounts (529/Backdoor Roth).")
        else:
            print("🎉 NO DEBT DETECTED.")
            print(f"  -> Recommendation: Invest ${deployable_cash:,.2f} (529, Brokerage, Real Estate).")
            
    else:
        shortfall = abs(deployable_cash)
        print(f"⚠️ RISK ALERT: You are underfunded by ${shortfall:,.2f}.")
        print("  -> ACTION: Halt all extra debt payments. Hoard cash until Target is met.")

if __name__ == "__main__":
    analyze_financial_health()
