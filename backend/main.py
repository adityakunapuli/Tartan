import os
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

@app.get("/api/transactions")
async def get_transactions():
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token not set. Link your account first.")
    
    try:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(count=100)
        )
        response = client.transactions_get(request)
        return response.to_dict()
    except plaid.ApiException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/investments")
async def get_investments():
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token not set. Link your account first.")
    
    try:
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        response = client.investments_holdings_get(request)
        return response.to_dict()
    except plaid.ApiException as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
