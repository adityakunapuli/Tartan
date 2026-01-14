"""Reporting script for personal financial health and strategy."""

import pandas as pd
from analysis.services.data_layer import get_enriched_transactions_df
from analysis.db.session import engine
from analysis.manual_data import VESTING_SCHEDULE, MONTHLY_SPOUSE_INCOME
from datetime import date

def get_current_liquidity() -> float:
    """Calculates total liquid cash from depository accounts.

    Returns:
        float: Total available balance in checking/savings accounts.
    """
    # We only count 'depository' accounts (Checking/Savings) as liquid cash.
    # Exclude 'credit', 'loan', 'investment'.
    # Note: We are currently including CDs (subtype='cd') as liquid based on previous discussion (No-Penalty CD).
    # If you want to exclude CDs, filter by subtype != 'cd'.
    query = "SELECT current_balance FROM accounts WHERE type = 'depository'"
    df = pd.read_sql(query, engine)
    return df['current_balance'].sum() if not df.empty else 0.0

def get_revolving_debt() -> float:
    """Calculates total high-interest revolving debt (Credit Cards).

    Returns:
        float: Total POSITIVE balance of credit card accounts.
    """
    query = "SELECT current_balance FROM accounts WHERE type = 'credit'"
    df = pd.read_sql(query, engine)
    if df.empty:
        return 0.0
    # Only count positive balances (money you owe). Negative means they owe you.
    return df[df['current_balance'] > 0]['current_balance'].sum()

def get_installment_debt() -> float:
    """Calculates total installment debt (Loans, Mortgage).

    Returns:
        float: Total balance of loan accounts.
    """
    query = "SELECT current_balance FROM accounts WHERE type = 'loan'"
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
    
    print(f"\n[METRIC] Gross Burn Rate (6-mo Avg): ${monthly_burn:,.2f} / month")
    print(f"  -> Total Spend (6-mo): ${total_spend:,.2f}")
    
    # 2. Target Emergency Fund (Adjusted for Guaranteed Income)
    monthly_net_burn = max(0, monthly_burn - MONTHLY_SPOUSE_INCOME)
    
    print(f"[METRIC] Guaranteed Monthly Income: ${MONTHLY_SPOUSE_INCOME:,.2f}")
    print(f"[METRIC] Net Burn Rate (Risk Exposure): ${monthly_net_burn:,.2f} / month")
    
    target_cash = monthly_net_burn * 6.0
    print(f"[METRIC] Target Emergency Fund (6 Months Net): ${target_cash:,.2f}")
    
    # 3. Current State
    current_cash = get_current_liquidity()
    revolving_debt = get_revolving_debt()
    installment_debt = get_installment_debt()
    
    print(f"\n[STATUS] Current Liquid Cash: ${current_cash:,.2f}")
    print(f"[STATUS] Revolving Debt (CC): ${revolving_debt:,.2f}")
    print(f"[STATUS] Installment Debt (Loans): ${installment_debt:,.2f}")
    
    # 4. Strategy Execution
    deployable_cash = current_cash - target_cash
    
    print("\n--- STRATEGY EXECUTION ---")
    
    if deployable_cash > 0:
        print(f"✅ SURPLUS DETECTED: You have ${deployable_cash:,.2f} in excess cash.")
        
        # Priority 1: Revolving Debt
        if revolving_debt > 0:
            pay_amount = min(deployable_cash, revolving_debt)
            print(f"🚨 PRIORITY 1: Pay off ${pay_amount:,.2f} of Credit Card debt IMMEDIATELY.")
            
            deployable_cash -= pay_amount
        
        # Priority 2: Installment Debt or Invest
        if deployable_cash > 0:
            if installment_debt > 0:
                print(f"✅ Credit Cards Clear. You have ${deployable_cash:,.2f} available to attack Loans or Invest.")
                print("   -> Recommendation: Compare Loan APR vs Expected Investment Return.")
            else:
                print(f"🎉 DEBT FREE. Invest ${deployable_cash:,.2f} (529, Backdoor Roth, Brokerage).")
            
    else:
        shortfall = abs(deployable_cash)
        print(f"⚠️ RISK ALERT: You are underfunded by ${shortfall:,.2f}.")
        print("  -> ACTION: Halt all extra debt payments. Hoard cash until Target is met.")

    # 5. Future Liquidity (Vesting)
    print("\n🔮 FUTURE LIQUIDITY (Next 12 Months) 🔮")
    today = date.today()
    future_cash = 0.0
    
    for event in VESTING_SCHEDULE:
        days_until = (event['date'] - today).days
        if 0 <= days_until <= 365:
            print(f"  -> {event['date']} (+{days_until} days): {event['description']} - ${event['amount_post_tax']:,.2f}")
            future_cash += event['amount_post_tax']
            
    print(f"  -> Total Projected Inflow: ${future_cash:,.2f}")
if __name__ == '__main__':
    analyze_financial_health()
