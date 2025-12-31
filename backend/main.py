import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from dotenv import load_dotenv
import datetime
import time

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')
PLAID_PRODUCTS = [p.strip() for p in os.getenv('PLAID_PRODUCTS', 'transactions').split(',')]
PLAID_COUNTRY_CODES = [c.strip() for c in os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')]
DB_FILE = "financial_data.db"

# Setup Plaid Client
host = getattr(plaid.Environment, PLAID_ENV.capitalize())

configuration = plaid.Configuration(
    host=host,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

# Database Setup
def init_db():
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
    return conn

@app.on_event("startup")
async def startup_event():
    init_db()

# Simple in-memory storage for demonstration (use a DB for production)
access_token = os.getenv('PLAID_ACCESS_TOKEN', None)

class TokenExchangeRequest(BaseModel):
    public_token: str

@app.post("/api/create_link_token")
async def create_link_token():
    try:
        products = [Products(p) for p in PLAID_PRODUCTS]
        country_codes = [CountryCode(c) for c in PLAID_COUNTRY_CODES]
        
        request = LinkTokenCreateRequest(
            products=products,
            country_codes=country_codes,
            language='en',
            client_name="Plaid Local App",
            user=LinkTokenCreateRequestUser(client_user_id=str(time.time()))
        )
        response = client.link_token_create(request)
        return response.to_dict()
    except plaid.ApiException as e:
        print(f"Plaid API Error: {e.body}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/set_access_token")
async def set_access_token(request: TokenExchangeRequest):
    global access_token
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=request.public_token
        )
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        # In a real app, you'd save this to a .env or DB
        return {"access_token": access_token}
    except plaid.ApiException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync")
async def sync_data():
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token not set.")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Sync Transactions
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(count=500)
        )
        response = client.transactions_get(request)
        for t in response['transactions']:
            cat = t.category[0] if t.category else ""
            c.execute('''INSERT OR REPLACE INTO transactions 
                (transaction_id, account_id, date, name, amount, category, pending)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (t.transaction_id, t.account_id, t.date, t.name, t.amount, cat, t.pending))
        
        # Sync Investments
        inv_request = InvestmentsHoldingsGetRequest(access_token=access_token)
        inv_response = client.investments_holdings_get(inv_request)
        today = datetime.date.today().isoformat()
        
        for s in inv_response['securities']:
             c.execute('''INSERT OR REPLACE INTO securities
                (security_id, name, ticker, type)
                VALUES (?, ?, ?, ?)''',
                (s.security_id, s.name, s.ticker_symbol, s.type))
             
        for h in inv_response['holdings']:
            c.execute('''INSERT INTO investment_holdings
                (date_captured, account_id, security_id, quantity, price, value)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (today, h.account_id, h.security_id, h.quantity, h.institution_price, h.institution_value))
            
        conn.commit()
        return {"status": "success", "transactions_synced": len(response['transactions']), "holdings_synced": len(inv_response['holdings'])}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/transactions")
async def get_transactions():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/investments")
async def get_investments():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Get latest holdings snapshot
    c.execute("""
        SELECT h.*, s.name as security_name, s.ticker as ticker
        FROM investment_holdings h
        JOIN securities s ON h.security_id = s.security_id
        WHERE h.date_captured = (SELECT MAX(date_captured) FROM investment_holdings)
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
