"Service for syncing financial data from Plaid to the local database."

import os
import datetime
import json
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
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.country_code import CountryCode
from dotenv import load_dotenv, find_dotenv
from sqlmodel import select, delete, Session

from analysis.db.models import (
    Transaction,
    InvestmentHolding,
    Security,
    InvestmentTransaction,
    Account,
    PlaidItem,
    Liability,
)
from analysis.db.session import engine, init_db
from analysis.utils import make_json_serializable

# Load .env from project root
load_dotenv(find_dotenv(), override=True)


def _parse_csv_env(name: str) -> set[str]:
    value = os.getenv(name, "")
    return {v.strip() for v in value.split(",") if v.strip()}


def _resolve_excluded_account_ids(session: Session) -> set[str]:
    excluded_ids = _parse_csv_env("EXCLUDED_ACCOUNT_IDS")
    excluded_names = {n.lower() for n in _parse_csv_env("EXCLUDED_ACCOUNT_NAMES")}
    if not excluded_names:
        return excluded_ids

    accounts = session.exec(select(Account)).all()
    for a in accounts:
        if a.name and a.name.lower() in excluded_names:
            excluded_ids.add(a.account_id)
    return excluded_ids


def _should_skip_transaction(
        session: Session, transaction_id: str, account_id: str
) -> bool:
    existing = session.exec(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).first()
    if not existing:
        return False

    if existing.account_id != account_id:
        print(
            "  -> Skipping transaction due to ID collision across accounts: "
            f"{transaction_id} (existing={existing.account_id}, incoming={account_id})"
        )
        return True

    return False


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


def sync_transactions(
        session: Session,
        client: plaid_api.PlaidApi,
        access_token: str,
        excluded_account_ids: set[str] | None = None,
        seen_tx_keys: set[str] | None = None,
) -> None:
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
        plaid_item = PlaidItem(access_token=access_token)
        session.add(plaid_item)
        session.commit()
        session.refresh(plaid_item)

    cursor = plaid_item.next_cursor
    added_count = 0
    modified_count = 0
    removed_count = 0

    seen = seen_tx_keys if seen_tx_keys is not None else set()
    while True:
        try:
            request_kwargs = {"access_token": access_token, "count": 500}
            if cursor:
                request_kwargs["cursor"] = cursor

            request = TransactionsSyncRequest(**request_kwargs)
            response = client.transactions_sync(request)

            # Process ADDED
            for t in response["added"]:
                if excluded_account_ids and t.account_id in excluded_account_ids:
                    continue
                if _should_skip_transaction(session, t.transaction_id, t.account_id):
                    continue
                tx_key = f"{t.transaction_id}:{t.account_id}"
                if tx_key in seen:
                    continue
                seen.add(tx_key)
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
                if excluded_account_ids and t.account_id in excluded_account_ids:
                    continue
                if _should_skip_transaction(session, t.transaction_id, t.account_id):
                    continue
                tx_key = f"{t.transaction_id}:{t.account_id}"
                if tx_key in seen:
                    continue
                seen.add(tx_key)
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
                if excluded_account_ids and t["transaction_id"]:
                    existing = session.exec(
                        select(Transaction).where(
                            Transaction.transaction_id == t["transaction_id"]
                        )
                    ).first()
                    if existing and existing.account_id in excluded_account_ids:
                        continue
                stmt = delete(Transaction).where(
                    Transaction.transaction_id == t["transaction_id"]
                )
                session.exec(stmt)
                removed_count += 1

            # Update Cursor
            cursor = response["next_cursor"]
            plaid_item.next_cursor = cursor
            session.add(plaid_item)
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


def sync_holdings(
        session: Session,
        client: plaid_api.PlaidApi,
        access_token: str,
        excluded_account_ids: set[str] | None = None,
) -> None:
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

        # 1. Sync Securities first
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

        # 2. Prevent Duplicates: Delete existing holdings for today for the accounts involved
        account_ids = {h.account_id for h in response["holdings"]}
        if excluded_account_ids:
            account_ids = {aid for aid in account_ids if aid not in excluded_account_ids}
        if account_ids:
            stmt = delete(InvestmentHolding).where(
                (InvestmentHolding.date_captured == today)
                & (InvestmentHolding.account_id.in_(account_ids))
            )
            session.exec(stmt)

        # 3. Sync Holdings
        count = 0
        for h in response["holdings"]:
            if excluded_account_ids and h.account_id in excluded_account_ids:
                continue
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
            print("  -> Skipping: Investments product not supported by this institution.")
        else:
            print(f"  -> Error: {e}")
        session.rollback()


def sync_investment_transactions(
        session: Session,
        client: plaid_api.PlaidApi,
        access_token: str,
        days: int = 730,
        excluded_account_ids: set[str] | None = None,
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
                if excluded_account_ids and t.account_id in excluded_account_ids:
                    continue
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
                    type=str(t.type),
                    subtype=str(t.subtype)
                    if t.subtype
                    else None,
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


def sync_liabilities(
        session: Session,
        client: plaid_api.PlaidApi,
        access_token: str,
        excluded_account_ids: set[str] | None = None,
) -> None:
    """Fetches and saves detailed liability information (Credit Cards, Loans).

    Args:
        session (Session): Database session.
        client (PlaidApi): Plaid API client.
        access_token (str): Plaid access token.
    """
    print("Syncing Liabilities (APR/Loan terms)...")
    try:
        request = LiabilitiesGetRequest(access_token=access_token)
        response = client.liabilities_get(request)
        liabilities = response["liabilities"]

        count = 0
        # Process Credit Cards
        for c in liabilities.get("credit", []):
            if excluded_account_ids and c["account_id"] in excluded_account_ids:
                continue
            lib_obj = Liability(
                account_id=c["account_id"],
                type="credit",
                aprs=make_json_serializable(c.get("aprs")),
                is_overdue=c.get("is_overdue"),
                last_payment_amount=c.get("last_payment_amount"),
                last_payment_date=c.get("last_payment_date"),
                next_payment_due_date=c.get("next_payment_due_date"),
                minimum_payment_amount=c.get("minimum_payment_amount"),
                raw_json=make_json_serializable(c)
            )
            session.merge(lib_obj)
            count += 1

        # Process Mortgages
        for m in liabilities.get("mortgage", []):
            if excluded_account_ids and m["account_id"] in excluded_account_ids:
                continue
            lib_obj = Liability(
                account_id=m["account_id"],
                type="mortgage",
                interest_rate_percentage=m.get("interest_rate", {}).get("percentage"),
                origination_date=m.get("origination_date"),
                principal_amount=m.get("origination_principal_amount"),
                raw_json=make_json_serializable(m)
            )
            session.merge(lib_obj)
            count += 1

        # Process Student Loans
        for s in liabilities.get("student", []):
            if excluded_account_ids and s["account_id"] in excluded_account_ids:
                continue
            lib_obj = Liability(
                account_id=s["account_id"],
                type="student",
                interest_rate_percentage=s.get("interest_rate_percentage"),
                origination_date=s.get("origination_date"),
                principal_amount=s.get("origination_principal_amount"),
                expected_payoff_date=s.get("expected_payoff_date"),
                last_payment_amount=s.get("last_payment_amount"),
                last_payment_date=s.get("last_payment_date"),
                next_payment_due_date=s.get("next_payment_due_date"),
                minimum_payment_amount=s.get("minimum_payment_amount"),
                raw_json=make_json_serializable(s)
            )
            session.merge(lib_obj)
            count += 1

        session.commit()
        print(f"  -> Saved {count} liability records.")

    except plaid.ApiException as e:
        error_response = json.loads(e.body)
        error_code = error_response.get("error_code")

        if error_code == "ADDITIONAL_CONSENT_REQUIRED":
            print("  -> [WARN] Action Required: Re-link this institution to enable Liabilities data.")
        elif error_code == "PRODUCTS_NOT_SUPPORTED":
            print("  -> Skipping: Liabilities product not supported by this institution.")
        elif error_code == "NO_LIABILITY_ACCOUNTS":
            print("  -> [INFO] No liability accounts (credit cards/loans) found for this item.")
        else:
            print(f"  -> Error: {e}")
        session.rollback()


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
            seen_tx_keys: set[str] = set()

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

                excluded_account_ids = _resolve_excluded_account_ids(session)
                if excluded_account_ids:
                    print(
                        f"Excluding {len(excluded_account_ids)} account(s) from sync for this run."
                    )

                sync_transactions(
                    session,
                    client,
                    token,
                    excluded_account_ids,
                    seen_tx_keys,
                )
                sync_holdings(session, client, token, excluded_account_ids)
                sync_investment_transactions(session, client, token, 730, excluded_account_ids)
                sync_liabilities(session, client, token, excluded_account_ids)

            print("\n" + "=" * 60)
            print(f"{'INSTITUTION':<30} | {'ACCESS TOKEN'}")
            print("-" * 60)
            for token, name in token_map.items():
                print(f"{name:<30} | {token}")
            print("=" * 60)

        finally:
            # Context manager handles close, but explicit check doesn't hurt
            pass


if __name__ == "__main__":
    run_sync()
