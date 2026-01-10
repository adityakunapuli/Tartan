import os
import datetime
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.investments_transactions_get_request import InvestmentsTransactionsGetRequest
from plaid.model.investments_transactions_get_request_options import InvestmentsTransactionsGetRequestOptions
from plaid.model.accounts_get_request import AccountsGetRequest
from dotenv import load_dotenv

from analysis.db.models import Transaction, InvestmentHolding, Security, InvestmentTransaction, Account
from analysis.db.session import SessionLocal, init_db

# Load .env from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

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

def sync_transactions(session, client, access_token, days=730):
    print(f"Syncing Transactions (last {days} days)...")
    
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    
    # Pagination loop
    offset = 0
    total_retrieved = 0
    
    while True:
        try:
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(count=500, offset=offset)
            )
            response = client.transactions_get(request)
            transactions = response['transactions']
            total_available = response['total_transactions']
            
            if not transactions:
                break
            
            count = 0
            for t in transactions:
                t_dict = t.to_dict()
                t_dict_serializable = make_json_serializable(t_dict)
                
                tx_obj = Transaction(
                    transaction_id=t.transaction_id,
                    account_id=t.account_id,
                    date=t.date,
                    name=t.name,
                    amount=t.amount,
                    currency=t.iso_currency_code,
                    category=make_json_serializable(t.category),
                    category_id=t.category_id,
                    pending=t.pending,
                    merchant_name=t.merchant_name,
                    payment_channel=t.payment_channel,
                    raw_json=t_dict_serializable
                )
                session.merge(tx_obj)
                count += 1
            
            session.commit()
            total_retrieved += count
            print(f"  -> Saved {count} transactions (Batch {offset}-{offset+count}).")
            
            offset += len(transactions)
            if offset >= total_available:
                break
                
        except plaid.ApiException as e:
            print(f"  -> Error: {e}")
            session.rollback()
            break
            
    print(f"  -> Total Transactions Synced: {total_retrieved}")

def sync_holdings(session, client, access_token):
    print("Syncing Investment Holdings...")
    
    try:
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        response = client.investments_holdings_get(request)
        
        today = datetime.date.today()
        
        # Sync Securities first
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
        print(f"  -> Saved {count} holdings.")
    except plaid.ApiException as e:
        print(f"  -> Error: {e}")
        session.rollback()

def sync_investment_transactions(session, client, access_token, days=730):
    print(f"Syncing Investment Transactions (last {days} days)...")
    
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    
    # Pagination loop
    offset = 0
    total_retrieved = 0
    
    while True:
        try:
            request = InvestmentsTransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=InvestmentsTransactionsGetRequestOptions(count=500, offset=offset)
            )
            response = client.investments_transactions_get(request)
            inv_transactions = response['investment_transactions']
            total_available = response['total_investment_transactions']
            
            # Sync Securities (again, just in case new ones appear here)
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

            if not inv_transactions:
                break

            # Sync Transactions
            count = 0
            for t in inv_transactions:
                t_dict = t.to_dict()
                t_dict_serializable = make_json_serializable(t_dict)
                
                inv_tx_obj = InvestmentTransaction(
                    investment_transaction_id=t.investment_transaction_id,
                    account_id=t.account_id,
                    security_id=t.security_id,
                    date=t.date,
                    name=t.name,
                    quantity=t.quantity,
                    amount=t.amount,
                    price=t.price,
                    fees=t.fees,
                    type=str(t.type), # Convert enum to string
                    subtype=str(t.subtype) if t.subtype else None, # Convert enum to string
                    currency=t.iso_currency_code,
                    raw_json=t_dict_serializable
                )
                session.merge(inv_tx_obj)
                count += 1
                
            session.commit()
            total_retrieved += count
            print(f"  -> Saved {count} investment transactions (Batch {offset}-{offset+count}).")
            
            offset += len(inv_transactions)
            if offset >= total_available:
                break
            
        except plaid.ApiException as e:
            print(f"  -> Error: {e}")
            session.rollback()
            break
    
    print(f"  -> Total Investment Transactions Synced: {total_retrieved}")

def sync_accounts(session, client, access_token):
    print("Syncing Accounts (Balances)...")
    try:
        request = AccountsGetRequest(access_token=access_token)
        response = client.accounts_get(request)
        
        count = 0
        for a in response['accounts']:
            a_dict = a.to_dict()
            a_dict_serializable = make_json_serializable(a_dict)
            
            # Balances object
            balances = a.balances
            
            acc_obj = Account(
                account_id=a.account_id,
                name=a.name,
                mask=a.mask,
                type=str(a.type),
                subtype=str(a.subtype) if a.subtype else None,
                current_balance=balances.current,
                available_balance=balances.available,
                iso_currency_code=balances.iso_currency_code,
                limit=balances.limit,
                last_updated=datetime.date.today(),
                raw_json=a_dict_serializable
            )
            session.merge(acc_obj)
            count += 1
            
        session.commit()
        print(f"  -> Saved {count} accounts.")
        
    except plaid.ApiException as e:
        print(f"  -> Error: {e}")
        session.rollback()

def run_sync():
    init_db()
    client = get_plaid_client()
    session = SessionLocal()
    
    try:
        # Support multiple tokens comma-separated
        access_tokens_str = os.getenv('PLAID_ACCESS_TOKEN', '')
        access_tokens = [t.strip() for t in access_tokens_str.split(',') if t.strip()]
        
        if not access_tokens:
            print("No PLAID_ACCESS_TOKEN found in .env")
            return

        print(f"Found {len(access_tokens)} access token(s).")

        for i, token in enumerate(access_tokens):
            print(f"\n--- Syncing Institution {i+1}/{len(access_tokens)} ---")
            sync_accounts(session, client, token)
            sync_transactions(session, client, token)
            sync_holdings(session, client, token)
            sync_investment_transactions(session, client, token)
            
    finally:
        session.close()

if __name__ == "__main__":
    run_sync()
