import os
import sqlite3
import datetime
import pandas as pd
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_FILE = os.path.join(os.path.dirname(__file__), 'financial_data.db')

def get_plaid_client():
    client_id = os.getenv('PLAID_CLIENT_ID')
    secret = os.getenv('PLAID_SECRET')
    env = os.getenv('PLAID_ENV', 'sandbox')
    
    if not client_id or not secret:
        raise ValueError("Missing PLAID_CLIENT_ID or PLAID_SECRET in .env")

    host = getattr(plaid.Environment, env.capitalize())
    configuration = plaid.Configuration(
        host=host,
        api_key={'clientId': client_id, 'secret': secret}
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)

def init_db():
    """Initialize the local SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        account_id TEXT,
        date TEXT,
        name TEXT,
        amount REAL,
        category TEXT,
        pending BOOLEAN
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS investment_holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_captured TEXT,
        account_id TEXT,
        security_id TEXT,
        quantity REAL,
        price REAL,
        value REAL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS securities (
        security_id TEXT PRIMARY KEY,
        name TEXT,
        ticker TEXT,
        type TEXT
    )''')
    
    conn.commit()
    print(f"Database initialized at: {DB_FILE}")
    return conn

def sync_transactions(days=30):
    """Fetch transactions from Plaid and save to SQLite."""
    access_token = os.getenv('PLAID_ACCESS_TOKEN')
    if not access_token:
        print("Error: PLAID_ACCESS_TOKEN not found in .env")
        return

    client = get_plaid_client()
    conn = init_db()
    c = conn.cursor()

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    
    print(f"Fetching transactions from {start_date} to {end_date}...")
    
    try:
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(count=500)
        )
        response = client.transactions_get(request)
        transactions = response['transactions']
        
        count = 0
        for t in transactions:
            cat = t.category[0] if t.category else ""
            c.execute('''INSERT OR REPLACE INTO transactions 
                (transaction_id, account_id, date, name, amount, category, pending)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (t.transaction_id, t.account_id, t.date, t.name, t.amount, cat, t.pending))
            count += 1
            
        conn.commit()
        print(f"Success: Synced {count} transactions.")
        
    except plaid.ApiException as e:
        print(f"Plaid API Error: {e}")
    finally:
        conn.close()

def sync_investments():
    """Fetch investment holdings from Plaid and save to SQLite."""
    access_token = os.getenv('PLAID_ACCESS_TOKEN')
    if not access_token:
        print("Error: PLAID_ACCESS_TOKEN not found in .env")
        return

    client = get_plaid_client()
    conn = init_db()
    c = conn.cursor()
    
    print("Fetching investment holdings...")
    
    try:
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        response = client.investments_holdings_get(request)
        
        today = datetime.date.today().isoformat()
        
        # Sync Securities
        for s in response['securities']:
             c.execute('''INSERT OR REPLACE INTO securities
                (security_id, name, ticker, type)
                VALUES (?, ?, ?, ?)''',
                (s.security_id, s.name, s.ticker_symbol, s.type))

        # Sync Holdings
        count = 0
        for h in response['holdings']:
            c.execute('''INSERT INTO investment_holdings
                (date_captured, account_id, security_id, quantity, price, value)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (today, h.account_id, h.security_id, h.quantity, h.institution_price, h.institution_value))
            count += 1
            
        conn.commit()
        print(f"Success: Synced {count} holdings.")
        
    except plaid.ApiException as e:
        print(f"Plaid API Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # You can run this script directly to sync everything
    sync_transactions()
    sync_investments()
