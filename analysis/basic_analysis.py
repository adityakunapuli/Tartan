#%%
import sqlite3
import pandas as pd
import os
import matplotlib.pyplot as plt

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'financial_data.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

#%%
# ==========================================
# 1. LOAD TRANSACTIONS
# ==========================================
conn = get_connection()
df_tx = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
df_tx['date'] = pd.to_datetime(df_tx['date'])
df_tx['amount'] = pd.to_numeric(df_tx['amount'])

print(f"Loaded {len(df_tx)} transactions.")
print(df_tx.head())

#%%
# ==========================================
# 2. SPENDING BY CATEGORY
# ==========================================
# Filter out negative amounts (income/transfers) for spending analysis
spending = df_tx[df_tx['amount'] > 0].copy()
category_sum = spending.groupby('category')['amount'].sum().sort_values(ascending=False)

print("\n--- Spending by Category ---")
print(category_sum)

# Optional: Plot
# category_sum.plot(kind='bar', title='Spending by Category')
# plt.show()

#%%
# ==========================================
# 3. INVESTMENT PORTFOLIO
# ==========================================
# Get the most recent snapshot of holdings
query = """
    SELECT h.*, s.name as security_name, s.ticker
    FROM investment_holdings h
    JOIN securities s ON h.security_id = s.security_id
    WHERE h.date_captured = (SELECT MAX(date_captured) FROM investment_holdings)
"""
df_inv = pd.read_sql_query(query, conn)

print(f"\nLoaded {len(df_inv)} investment holdings.")

total_value = df_inv['value'].sum()
print(f"\nTotal Portfolio Value: ${total_value:,.2f}")

print("\n--- Top Holdings ---")
print(df_inv[['security_name', 'ticker', 'value', 'quantity']].sort_values(by='value', ascending=False).head())

conn.close()
