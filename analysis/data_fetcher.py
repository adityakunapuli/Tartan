import os
import json
import datetime
from pathlib import Path
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from dotenv import load_dotenv

from models import init_db, SessionLocal, Transaction, InvestmentHolding, Security

# Add sys.path hack just in case, though relative imports were removed
import sys
sys.path.append(str(Path(__file__).parent))

# Load .env from project root
# Using Path to resolve 2 levels up safely
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / '.env')

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

def make_json_serializable(data):
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_json_serializable(v) for v in data]
    elif isinstance(data, (datetime.date, datetime.datetime)):
        return data.isoformat()
    return data

def sync_transactions(days=30):
    """Fetch transactions from Plaid and save to SQLite using SQLAlchemy."""
    access_token = os.getenv('PLAID_ACCESS_TOKEN')
    if not access_token:
        print("Error: PLAID_ACCESS_TOKEN not found in .env")
        return

    client = get_plaid_client()
    session = SessionLocal()

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    
    print(f"Fetching transactions from {start_date} to {end_date}...")
    
    try:
        # Loop for pagination could be added here, but starting with simple fetch
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
            t_dict = t.to_dict()
            t_dict_serializable = make_json_serializable(t_dict)
            
            # Create or update Transaction object
            # We use merge to handle upserts based on primary key (transaction_id)
            tx_obj = Transaction(
                transaction_id=t.transaction_id,
                account_id=t.account_id,
                date=t.date,
                name=t.name,
                amount=t.amount,
                currency=t.iso_currency_code,
                category=make_json_serializable(t.category), # Ensure category list is also safe
                category_id=t.category_id,
                pending=t.pending,
                merchant_name=t.merchant_name,
                payment_channel=t.payment_channel,
                raw_json=t_dict_serializable # Capture everything else!
            )
            session.merge(tx_obj)
            count += 1
            
        session.commit()
        print(f"Success: Synced {count} transactions.")
        
    except plaid.ApiException as e:
        print(f"Plaid API Error: {e}")
        session.rollback()
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

def sync_investments():
    """Fetch investment holdings from Plaid and save to SQLite using SQLAlchemy."""
    access_token = os.getenv('PLAID_ACCESS_TOKEN')
    if not access_token:
        print("Error: PLAID_ACCESS_TOKEN not found in .env")
        return

    client = get_plaid_client()
    session = SessionLocal()
    
    print("Fetching investment holdings...")
    
    try:
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        response = client.investments_holdings_get(request)
        
        today = datetime.date.today()
        
        # Sync Securities
        for s in response['securities']:
            s_dict = s.to_dict()
            s_dict_serializable = make_json_serializable(s_dict)
            
            sec_obj = Security(
                security_id=s.security_id,
                name=s.name,
                ticker_symbol=s.ticker_symbol,
                institution_security_id=s.institution_security_id,
                type=s.type,
                close_price=s.close_price,
                close_price_as_of=s.close_price_as_of,
                currency=s.iso_currency_code,
                is_cash_equivalent=s.is_cash_equivalent,
                raw_json=s_dict_serializable
            )
            session.merge(sec_obj)

        # Sync Holdings
        # Note: Holdings don't always have a unique stable ID from Plaid across fetches (unlike transactions).
        # Typically we snapshot them by date.
        count = 0
        for h in response['holdings']:
            h_dict = h.to_dict()
            h_dict_serializable = make_json_serializable(h_dict)
            
            holding_obj = InvestmentHolding(
                date_captured=today,
                account_id=h.account_id,
                security_id=h.security_id,
                quantity=h.quantity,
                institution_price=h.institution_price,
                institution_value=h.institution_value,
                cost_basis=h.cost_basis,
                currency=h.iso_currency_code,
                raw_json=h_dict_serializable
            )
            session.add(holding_obj)
            count += 1
            
        session.commit()
        print(f"Success: Synced {count} holdings.")
        
    except plaid.ApiException as e:
        print(f"Plaid API Error: {e}")
        session.rollback()
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    init_db()
    sync_transactions()
    sync_investments()