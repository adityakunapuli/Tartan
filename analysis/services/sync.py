"Service for syncing financial data from Plaid to the local database."

import os
import datetime
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.investments_transactions_get_request import (
    InvestmentsTransactionsGetRequest,
)
from plaid.model.investments_transactions_get_request_options import (
    InvestmentsTransactionsGetRequestOptions,
)
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.country_code import CountryCode
from dotenv import load_dotenv
import json
from sqlmodel import select, delete, Session

from analysis.db.sqlmodel_models import (
    Transaction,
    InvestmentHolding,
    Security,
    InvestmentTransaction,
    Account,
    PlaidItem,
)
from analysis.db.session import engine, init_db
from analysis.utils import make_json_serializable

# Load .env from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)


def get_plaid_client() -> plaid_api.PlaidApi:
    """Initializes and returns the Plaid API client.

    Returns:
        plaid_api.PlaidApi: The authenticated Plaid client.

    Raises:
        ValueError: If PLAID_CLIENT_ID or PLAID_SECRET are missing.
    """
    client_id = os.getenv("PLAID_CLIENT_ID")
    secret = os.getenv("PLAID_SECRET")
    env = os.getenv("PLAID_ENV", "sandbox")

    if not client_id or not secret:
        raise ValueError("Missing PLAID_CLIENT_ID or PLAID_SECRET in .env")

    host = getattr(plaid.Environment, env.capitalize())
    configuration = plaid.Configuration(
        host=host, api_key={"clientId": client_id, "secret": secret}
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def sync_transactions(session: Session, client: plaid_api.PlaidApi, access_token: str) -> None:
    """Fetches and saves transactions incrementally using /transactions/sync.

    Args:
        session (Session): Database session.
        client (PlaidApi): Plaid API client.
        access_token (str): Plaid access token.
    """
    print("Syncing Transactions (Incremental)...")

    # 1. Get the latest cursor for this access token
    plaid_item = session.exec(
        select(PlaidItem).where(PlaidItem.access_token == access_token)
    ).first()

    if not plaid_item:
        # Create item entry if it doesn't exist
        # We'll populate item_id on the first sync response
        plaid_item = PlaidItem(access_token=access_token)
        session.add(plaid_item)
        session.commit()
        session.refresh(plaid_item)

    cursor = plaid_item.next_cursor
    added_count = 0
    modified_count = 0
    removed_count = 0

    while True:
        try:
            request_kwargs = {"access_token": access_token, "count": 500}
            if cursor:
                request_kwargs["cursor"] = cursor

            request = TransactionsSyncRequest(**request_kwargs)
            response = client.transactions_sync(request)

            # Process ADDED
            for t in response["added"]:
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
                    raw_json=t_dict_serializable,
                )
                session.merge(tx_obj)
                added_count += 1

            # Process MODIFIED
            for t in response["modified"]:
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
                    raw_json=t_dict_serializable,
                )
                session.merge(tx_obj)
                modified_count += 1

            # Process REMOVED
            for t in response["removed"]:
                stmt = delete(Transaction).where(
                    Transaction.transaction_id == t["transaction_id"]
                )
                session.exec(stmt)
                removed_count += 1

            # Update Cursor
            cursor = response["next_cursor"]
            plaid_item.next_cursor = cursor
            session.add(plaid_item) # Explicit add for SQLModel update
            session.commit()

            if not response["has_more"]:
                break

        except plaid.ApiException as e:
            print(f"  -> Error: {e}")
            session.rollback()
            break

    print(
        f"  -> Added: {added_count}, Modified: {modified_count}, Removed: {removed_count}"
    )


def sync_holdings(session: Session, client: plaid_api.PlaidApi, access_token: str) -> None:
    """Fetches and saves investment holdings.

    Args:
        session (Session): Database session.
        client (PlaidApi): Plaid API client.
        access_token (str): Plaid access token.
    """
    print("Syncing Investment Holdings...")

    try:
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        response = client.investments_holdings_get(request)

        today = datetime.date.today()

        # Sync Securities first
        for s in response["securities"]:
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
                raw_json=s_dict_serializable,
            )
            session.merge(sec_obj)

        # Sync Holdings
        # Prevent Zombie Data: Delete existing holdings for today for the accounts involved
        # Since one access token can have multiple accounts, we collect them first
        account_ids = {h.account_id for h in response["holdings"]}

        if account_ids:
            # SQLModel uses exec for statements too
            stmt = delete(InvestmentHolding).where(
                (InvestmentHolding.date_captured == today)
                & (InvestmentHolding.account_id.in_(account_ids))
            )
            session.exec(stmt)
            # No commit yet, we do it after adding new ones

        count = 0
        for h in response["holdings"]:
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
                raw_json=h_dict_serializable,
            )
            session.add(holding_obj)
            count += 1

        session.commit()
        print(f"  -> Saved {count} holdings.")
    except plaid.ApiException as e:
        error_response = json.loads(e.body)
        if error_response.get("error_code") == "PRODUCTS_NOT_SUPPORTED":
            print(
                "  -> Skipping: Investments product not supported by this institution."
            )
        else:
            print(f"  -> Error: {e}")
        session.rollback()


def sync_investment_transactions(
    session: Session, client: plaid_api.PlaidApi, access_token: str, days: int = 730
) -> None:
    """Fetches and saves investment transactions.

    Args:
        session (Session): Database session.
        client (PlaidApi): Plaid API client.
        access_token (str): Plaid access token.
        days (int, optional): Number of days of history to fetch. Defaults to 730.
    """
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
                options=InvestmentsTransactionsGetRequestOptions(
                    count=500, offset=offset
                ),
            )
            response = client.investments_transactions_get(request)
            inv_transactions = response["investment_transactions"]
            total_available = response["total_investment_transactions"]

            # Sync Securities (again, just in case new ones appear here)
            for s in response["securities"]:
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
                    raw_json=s_dict_serializable,
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
                    type=str(t.type),  # Convert enum to string
                    subtype=str(t.subtype)
                    if t.subtype
                    else None,  # Convert enum to string
                    currency=t.iso_currency_code,
                    raw_json=t_dict_serializable,
                )
                session.merge(inv_tx_obj)
                count += 1

            session.commit()
            total_retrieved += count
            print(
                f"  -> Saved {count} investment transactions (Batch {offset}-{offset + count})."
            )

            offset += len(inv_transactions)
            if offset >= total_available:
                break

        except plaid.ApiException as e:
            error_response = json.loads(e.body)
            if error_response.get("error_code") == "PRODUCTS_NOT_SUPPORTED":
                print(
                    "  -> Skipping: Investments product not supported by this institution."
                )
            else:
                print(f"  -> Error: {e}")
            session.rollback()
            break

    print(f"  -> Total Investment Transactions Synced: {total_retrieved}")


def sync_accounts(session: Session, client: plaid_api.PlaidApi, access_token: str) -> str | None:
    """Fetches and saves account balances and metadata.

    Args:
        session (Session): Database session.
        client (PlaidApi): Plaid API client.
        access_token (str): Plaid access token.

    Returns:
        str | None: The institution_id if successful, None otherwise.
    """
    print("Syncing Accounts (Balances)...")
    try:
        request = AccountsGetRequest(access_token=access_token)
        response = client.accounts_get(request)

        # Capture Institution ID
        institution_id = response["item"]["institution_id"]

        count = 0
        for a in response["accounts"]:
            a_dict = a.to_dict()
            a_dict_serializable = make_json_serializable(a_dict)

            # Balances object
            balances = a.balances

            # SQLModel (Account) can be instantiated directly with validated data
            # since it inherits from Pydantic BaseModel.
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
                apy=getattr(a, "apy", None),
                interest_rate=getattr(a, "interest_rate", None),
                maturity_date=getattr(a, "maturity_date", None),
                last_updated=datetime.date.today(),
                raw_json=a_dict_serializable,
            )
            
            # Use merge to upsert
            session.merge(acc_obj)
            count += 1

        session.commit()
        print(f"  -> Saved {count} accounts.")
        return institution_id

    except plaid.ApiException as e:
        print(f"  -> Error: {e}")
        session.rollback()
        return None


def run_sync() -> None:
    """Orchestrates the synchronization process for all configured access tokens."""
    init_db()
    client = get_plaid_client()
    
    # Use Session context manager manually since get_db yields it
    with Session(engine) as session:
        try:
            # Support multiple tokens comma-separated
            access_tokens_str = os.getenv("PLAID_ACCESS_TOKEN", "")
            access_tokens = [t.strip() for t in access_tokens_str.split(",") if t.strip()]

            if not access_tokens:
                print("No PLAID_ACCESS_TOKEN found in .env")
                return

            print(f"Found {len(access_tokens)} access token(s).")

            token_map = {}

            for i, token in enumerate(access_tokens):
                inst_id = sync_accounts(session, client, token)
                inst_name = "Unknown Institution"

                if inst_id:
                    try:
                        # Update PlaidItem with institution_id
                        plaid_item = session.exec(
                            select(PlaidItem).where(PlaidItem.access_token == token)
                        ).first()

                        if not plaid_item:
                            plaid_item = PlaidItem(access_token=token)
                            session.add(plaid_item)

                        plaid_item.institution_id = inst_id

                        # Resolve Name
                        request = InstitutionsGetByIdRequest(
                            institution_id=inst_id, country_codes=[CountryCode("US")]
                        )
                        inst_response = client.institutions_get_by_id(request)
                        inst_name = inst_response["institution"]["name"]
                        plaid_item.institution_name = inst_name
                        session.add(plaid_item)
                        session.commit()

                    except Exception as e:
                        print(f"  -> Could not resolve institution name: {e}")
                        inst_name = f"Institution {inst_id}"

                token_map[token] = inst_name
                print(f"\n--- Syncing {inst_name} ({i + 1}/{len(access_tokens)}) ---")

                sync_transactions(session, client, token)
                sync_holdings(session, client, token)
                sync_investment_transactions(session, client, token)

            print("\n" + "=" * 60)
            print(f"{ 'INSTITUTION':<30} | {'ACCESS TOKEN'}")
            print("-" * 60)
            for token, name in token_map.items():
                print(f"{name:<30} | {token}")
            print("=" * 60)

        finally:
            # Context manager handles close, but explicit check doesn't hurt
            pass


if __name__ == "__main__":
    run_sync()
