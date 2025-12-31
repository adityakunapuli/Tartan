#%%
import sys
import os
from pathlib import Path

# Add analysis dir to sys.path
sys.path.append(str(Path(__file__).parent))

from data_layer import get_transactions_df, get_denormalized_holdings

#%%
# ==========================================
# 1. LOAD TRANSACTIONS
# ==========================================
df_tx = get_transactions_df()

if not df_tx.empty:
    print(f"Loaded {len(df_tx)} transactions.")
    print(df_tx[['date', 'name', 'amount', 'category']].head())
else:
    print("No transactions found.")

#%%
# ==========================================
# 2. SPENDING BY CATEGORY
# ==========================================
if not df_tx.empty:
    # Filter out negative amounts (income/transfers) for spending analysis
    spending = df_tx[df_tx['amount'] > 0].copy()
    
    # Category is often a list, take the first element or 'Uncategorized'
    # Since we store JSON, we might need to parse it or if pandas read it as list, it works.
    # SQL read might return list as string if not using sqlalchemy type processing in pandas read (which we didn't explicitly do for raw sql read)
    # But our models.py defined it as JSON type, so if we use ORM it handles it. 
    # data_layer uses read_sql, which relies on DBAPI. SQLite JSON is string.
    # Let's simple check type.
    
    def get_cat_name(x):
        if isinstance(x, list) and len(x) > 0:
            return x[0]
        # if string representation of list
        if isinstance(x, str) and x.startswith('['):
            import ast
            try:
                l = ast.literal_eval(x)
                if len(l) > 0: return l[0]
            except:
                pass
        return "Uncategorized"

    spending['primary_category'] = spending['category'].apply(get_cat_name)
    category_sum = spending.groupby('primary_category')['amount'].sum().sort_values(ascending=False)

    print("\n--- Spending by Category ---")
    print(category_sum)

#%%
# ==========================================
# 3. INVESTMENT PORTFOLIO
# ==========================================
df_inv = get_denormalized_holdings()

if not df_inv.empty:
    print(f"\nLoaded {len(df_inv)} investment holdings.")
    
    total_value = df_inv['institution_value'].sum()
    print(f"\nTotal Portfolio Value: ${total_value:,.2f}")

    print("\n--- Top Holdings ---")
    print(df_inv[['security_name', 'ticker_symbol', 'institution_value', 'quantity']].sort_values(by='institution_value', ascending=False).head())
else:
    print("No investment holdings found.")
