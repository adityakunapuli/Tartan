"""Service for syncing financial data from Plaid to the local database."""

import datetime
import json
import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.investments_transactions_get_request import (
    InvestmentsTransactionsGetRequest,
)
from plaid.model.investments_transactions_get_request_options import (
    InvestmentsTransactionsGetRequestOptions,
)
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from sqlmodel import Session, delete, select

from core.config import settings
from modules.accounts.models import Account, Liability, PlaidItem
from modules.transactions.models import Transaction
from modules.investments.models import (
    Security,
    InvestmentHolding,
    InvestmentTransaction,
)
from core.db.database import init_db, engine
from utils.helpers import make_json_serializable
from utils.logger import get_logger

logger = get_logger(__name__)


class PlaidSyncService:
    """Orchestrates the synchronization of financial data from Plaid.

    This service handles the complex logic of incremental syncs, cursor management,
    and deduplication of financial data across Transactions, Investments, and Liabilities.
    """

    def __init__(self, session: Session):
        """Initializes the PlaidSyncService.

        Args:
            session (Session): The database session used for persistence.
        """
        self.session = session
        self.client = self._get_plaid_client()

    @staticmethod
    def _get_plaid_client() -> plaid_api.PlaidApi:
        """Initializes and returns the Plaid API client using credentials from settings.

        Returns:
            plaid_api.PlaidApi: The authenticated Plaid client.

        Raises:
            ValueError: If credentials are missing in the environment.
        """
        # Security Note: settings.PLAID_* reads directly from os.getenv()
        if not settings.PLAID_CLIENT_ID or not settings.PLAID_SECRET:
            raise ValueError("Missing PLAID_CLIENT_ID or PLAID_SECRET in .env")

        host = getattr(plaid.Environment, settings.PLAID_ENV.capitalize())
        configuration = plaid.Configuration(
            host=host,
            api_key={
                "clientId": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
            },
        )
        api_client = plaid.ApiClient(configuration)
        return plaid_api.PlaidApi(api_client)

    def _should_skip_transaction(self, transaction_id: str, account_id: str) -> bool:
        """Determines if a transaction should be skipped to prevent ID collisions.

        In some rare cases (especially Sandbox), Plaid might re-issue the same
        transaction_id for a different account. We must detect this to preserve data integrity.

        Args:
            transaction_id (str): The Plaid transaction ID.
            account_id (str): The account ID associated with the incoming transaction.

        Returns:
            bool: True if the transaction exists for a DIFFERENT account, False otherwise.
        """
        existing = self.session.exec(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        ).first()

        if not existing:
            return False

        if existing.account_id != account_id:
            logger.warning(
                f"Skipping transaction collision: {transaction_id} "
                f"(Existing Account: {existing.account_id}, Incoming: {account_id})"
            )
            return True

        return False

    def sync_transactions(
        self,
        access_token: str,
        institution_name: str,
        excluded_account_ids: set[str] | None = None,
        seen_tx_keys: set[str] | None = None,
        seen_content_keys: set[tuple] | None = None,
    ) -> None:
        """Fetches and saves transactions incrementally using the /transactions/sync endpoint.

        Args:
            access_token (str): Plaid access token.
            institution_name (str): Name of the institution (for logging).
            excluded_account_ids (set[str] | None): Set of account IDs to ignore (from .env).
            seen_tx_keys (set[str] | None): Shared set to track processed (tx_id:acc_id) pairs
                                            across multiple tokens (if applicable) to avoid duplicates.
            seen_content_keys (set[tuple] | None): Shared set to track (date, amount, name) content
                                                   across multiple tokens for cross-item dedup.
        """
        logger.info("Syncing Transactions (Incremental)...")

        # 1. Get the latest cursor for this access token
        plaid_item = self.session.exec(
            select(PlaidItem).where(PlaidItem.access_token == access_token)
        ).first()

        if not plaid_item:
            # Create item entry if it doesn't exist to store the cursor
            plaid_item = PlaidItem(access_token=access_token)
            self.session.add(plaid_item)
            self.session.commit()
            self.session.refresh(plaid_item)

        cursor = plaid_item.next_cursor
        stats = {"added": 0, "modified": 0, "removed": 0}
        sync_failed = False
        seen = seen_tx_keys if seen_tx_keys is not None else set()
        seen_content = seen_content_keys if seen_content_keys is not None else set()

        while True:
            try:
                request_kwargs = {"access_token": access_token, "count": 500}
                if cursor:
                    request_kwargs["cursor"] = cursor

                request = TransactionsSyncRequest(**request_kwargs)
                response = self.client.transactions_sync(request)

                # --- Process ADDED ---
                for t in response["added"]:
                    if excluded_account_ids and t.account_id in excluded_account_ids:
                        continue
                    if self._should_skip_transaction(t.transaction_id, t.account_id):
                        continue

                    # Prevent duplicates within the same run
                    tx_key = f"{t.transaction_id}:{t.account_id}"
                    if tx_key in seen:
                        continue
                    seen.add(tx_key)

                    # Cross-item dedup: same real transaction reported by multiple
                    # Plaid items (e.g. Merrill + BofA) with different transaction_ids
                    content_key = (str(t.date), round(t.amount, 2), (t.merchant_name or t.name or "").lower().strip())
                    if content_key in seen_content:
                        stats["skipped_dup"] = stats.get("skipped_dup", 0) + 1
                        logger.debug(f"Skipping duplicate content: {content_key}")
                        continue
                    seen_content.add(content_key)

                    t_dict_serializable = make_json_serializable(t.to_dict())
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
                    self.session.merge(tx_obj)
                    stats["added"] += 1

                # --- Process MODIFIED ---
                for t in response["modified"]:
                    if excluded_account_ids and t.account_id in excluded_account_ids:
                        continue
                    if self._should_skip_transaction(t.transaction_id, t.account_id):
                        continue

                    tx_key = f"{t.transaction_id}:{t.account_id}"
                    if tx_key in seen:
                        continue
                    seen.add(tx_key)

                    # Cross-item content dedup
                    content_key = (str(t.date), round(t.amount, 2), (t.merchant_name or t.name or "").lower().strip())
                    if content_key in seen_content:
                        stats["skipped_dup"] = stats.get("skipped_dup", 0) + 1
                        continue
                    seen_content.add(content_key)

                    t_dict_serializable = make_json_serializable(t.to_dict())
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
                    self.session.merge(tx_obj)
                    stats["modified"] += 1

                # --- Process REMOVED ---
                for t in response["removed"]:
                    # Check exclusions before deleting (safety check)
                    if excluded_account_ids and t["transaction_id"]:
                        existing = self.session.exec(
                            select(Transaction).where(
                                Transaction.transaction_id == t["transaction_id"]
                            )
                        ).first()
                        if existing and existing.account_id in excluded_account_ids:
                            continue

                    stmt = delete(Transaction).where(
                        Transaction.transaction_id == t["transaction_id"]
                    )
                    self.session.exec(stmt)
                    stats["removed"] += 1

                # --- Update Cursor & Commit ---
                cursor = response["next_cursor"]
                plaid_item.next_cursor = cursor
                self.session.add(plaid_item)
                self.session.commit()

                if not response["has_more"]:
                    break

            except plaid.ApiException as e:
                logger.error(
                    f"Plaid API Error ({institution_name}) during transaction sync: {e}"
                )
                self.session.rollback()
                sync_failed = True
                break
            except Exception as e:
                logger.exception(
                    f"Unexpected error ({institution_name}) during transaction sync: {e}"
                )
                self.session.rollback()
                sync_failed = True
                break

        if sync_failed:
            logger.error(
                f"Transactions sync FAILED for {institution_name}. "
                "No transactions were processed."
            )
        else:
            logger.info(
                f"Transactions Synced: Added={stats['added']}, "
                f"Modified={stats['modified']}, Removed={stats['removed']}"
            )

    def sync_holdings(
        self,
        access_token: str,
        institution_name: str,
        excluded_account_ids: set[str] | None = None,
    ) -> None:
        """Fetches and saves investment holdings (snapshot).

        Holdings are not incremental. This method performs a snapshot sync:
        1. Fetches current holdings.
        2. Updates the `Securities` table with any new security definitions.
        3. DELETES existing holdings for the current `date_captured` (today) to prevent duplication.
        4. Inserts the new holdings.

        Args:
            access_token (str): Plaid access token.
            institution_name (str): Name of the institution (for logging).
            excluded_account_ids (set[str] | None): Set of account IDs to ignore.
        """
        logger.info("Syncing Investment Holdings...")

        try:
            request = InvestmentsHoldingsGetRequest(access_token=access_token)
            response = self.client.investments_holdings_get(request)

            today = datetime.date.today()

            # 1. Sync Securities first (Upsert)
            for s in response["securities"]:
                s_dict_serializable = make_json_serializable(s.to_dict())
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
                self.session.merge(sec_obj)

            # 2. Cleanup: Delete existing holdings for today for THESE accounts
            # This ensures idempotency if we run the script multiple times a day.
            account_ids = {h.account_id for h in response["holdings"]}
            if excluded_account_ids:
                account_ids = {
                    aid for aid in account_ids if aid not in excluded_account_ids
                }

            if account_ids:
                stmt = delete(InvestmentHolding).where(
                    (InvestmentHolding.date_captured == today)
                    & (InvestmentHolding.account_id.in_(account_ids))
                )
                self.session.exec(stmt)

            # 3. Insert Holdings
            count = 0
            for h in response["holdings"]:
                if excluded_account_ids and h.account_id in excluded_account_ids:
                    continue

                h_dict_serializable = make_json_serializable(h.to_dict())
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
                self.session.add(holding_obj)
                count += 1

            self.session.commit()
            logger.info(f"Saved {count} investment holdings.")

        except plaid.ApiException as e:
            error_response = json.loads(e.body)
            if error_response.get("error_code") == "PRODUCTS_NOT_SUPPORTED":
                logger.info(f"Investments product not supported by {institution_name}.")
            else:
                logger.error(
                    f"Plaid API Error ({institution_name}) during holdings sync: {e}"
                )
            self.session.rollback()
        except Exception as e:
            logger.exception(
                f"Unexpected error ({institution_name}) during holdings sync: {e}"
            )
            self.session.rollback()

    def sync_investment_transactions(
        self,
        access_token: str,
        institution_name: str,
        days: int = 730,
        excluded_account_ids: set[str] | None = None,
    ) -> None:
        """Fetches and saves investment transactions (history).

        Uses `options.offset` for pagination to retrieve the full history requested.

        Args:
            access_token (str): Plaid access token.
            institution_name (str): Name of the institution (for logging).
            days (int): Number of days of history to fetch (default: 730).
            excluded_account_ids (set[str] | None): Set of account IDs to ignore.
        """
        logger.info(f"Syncing Investment Transactions (last {days} days)...")

        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)

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
                response = self.client.investments_transactions_get(request)
                inv_transactions = response["investment_transactions"]
                total_available = response["total_investment_transactions"]

                # Upsert Securities
                for s in response["securities"]:
                    s_dict_serializable = make_json_serializable(s.to_dict())
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
                    self.session.merge(sec_obj)

                if not inv_transactions:
                    break

                # Upsert Transactions
                count = 0
                for t in inv_transactions:
                    if excluded_account_ids and t.account_id in excluded_account_ids:
                        continue

                    t_dict_serializable = make_json_serializable(t.to_dict())
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
                        subtype=str(t.subtype) if t.subtype else None,
                        currency=t.iso_currency_code,
                        raw_json=t_dict_serializable,
                    )
                    self.session.merge(inv_tx_obj)
                    count += 1

                self.session.commit()
                total_retrieved += count
                logger.info(
                    f"Saved {count} investment transactions (Offset: {offset})."
                )

                offset += len(inv_transactions)
                if offset >= total_available:
                    break

            except plaid.ApiException as e:
                error_response = json.loads(e.body)
                if error_response.get("error_code") == "PRODUCTS_NOT_SUPPORTED":
                    logger.info(
                        f"Investments product not supported by {institution_name}."
                    )
                else:
                    logger.error(
                        f"Plaid API Error ({institution_name}) during inv. tx sync: {e}"
                    )
                self.session.rollback()
                break

        logger.info(f"Total Investment Transactions Synced: {total_retrieved}")

    def sync_liabilities(
        self,
        access_token: str,
        institution_name: str,
        excluded_account_ids: set[str] | None = None,
    ) -> None:
        """Fetches and saves Liability data (Credit Cards, Mortgages, Student Loans).

        Args:
            access_token (str): Plaid access token.
            institution_name (str): Name of the institution (for logging).
            excluded_account_ids (set[str] | None): Set of account IDs to ignore.
        """
        logger.info("Syncing Liabilities (APR/Loan terms)...")
        try:
            request = LiabilitiesGetRequest(access_token=access_token)
            response = self.client.liabilities_get(request)
            liabilities = response["liabilities"]

            count = 0
            # Credit Cards
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
                    raw_json=make_json_serializable(c),
                )
                self.session.merge(lib_obj)
                count += 1

            # Mortgages
            for m in liabilities.get("mortgage", []):
                if excluded_account_ids and m["account_id"] in excluded_account_ids:
                    continue
                lib_obj = Liability(
                    account_id=m["account_id"],
                    type="mortgage",
                    interest_rate_percentage=m.get("interest_rate", {}).get(
                        "percentage"
                    ),
                    origination_date=m.get("origination_date"),
                    principal_amount=m.get("origination_principal_amount"),
                    raw_json=make_json_serializable(m),
                )
                self.session.merge(lib_obj)
                count += 1

            # Student Loans
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
                    raw_json=make_json_serializable(s),
                )
                self.session.merge(lib_obj)
                count += 1

            self.session.commit()
            logger.info(f"Saved {count} liability records.")

        except plaid.ApiException as e:
            error_response = json.loads(e.body)
            error_code = error_response.get("error_code")

            if error_code == "ADDITIONAL_CONSENT_REQUIRED":
                logger.warning(
                    f"Action Required: Re-link {institution_name} to enable Liabilities data."
                )
            elif error_code == "PRODUCTS_NOT_SUPPORTED":
                logger.info(f"Liabilities product not supported by {institution_name}.")
            elif error_code == "NO_LIABILITY_ACCOUNTS":
                logger.info(f"No liability accounts found for {institution_name}.")
            else:
                logger.error(
                    f"Plaid API Error ({institution_name}) during liabilities sync: {e}"
                )
            self.session.rollback()

    def sync_accounts(self, access_token: str, institution_name: str) -> str | None:
        """Fetches and saves account balances and metadata.

        Args:
            access_token (str): Plaid access token.
            institution_name (str): Name of the institution (for logging).

        Returns:
            str | None: The `institution_id` (e.g., 'ins_10985') if successful, else None.
        """
        logger.info(f"Syncing Accounts (Balances) for {institution_name}...")
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)

            institution_id = response["item"]["institution_id"]
            count = 0

            for a in response["accounts"]:
                a_dict_serializable = make_json_serializable(a.to_dict())
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
                    apy=getattr(a, "apy", None),
                    interest_rate=getattr(a, "interest_rate", None),
                    maturity_date=getattr(a, "maturity_date", None),
                    last_updated=datetime.date.today(),
                    sync_interval_hours=24,
                    raw_json=a_dict_serializable,
                )
                self.session.merge(acc_obj)
                count += 1

            self.session.commit()
            logger.info(f"Saved {count} accounts.")
            return institution_id

        except plaid.ApiException as e:
            logger.error(
                f"Plaid API Error ({institution_name}) during accounts sync: {e}"
            )
            self.session.rollback()
            return None


def run_sync() -> None:
    """Entry point to orchestrate synchronization for all configured tokens."""
    init_db()

    # Check for tokens
    if not settings.plaid_access_tokens:
        logger.warning("No PLAID_ACCESS_TOKEN found in .env. Skipping sync.")
        return

    logger.info(f"Found {len(settings.plaid_access_tokens)} access token(s).")

    with Session(engine) as session:
        service = PlaidSyncService(session)
        token_map = {}
        seen_tx_keys: set[str] = set()
        seen_content_keys: set[tuple] = set()

        for i, token in enumerate(settings.plaid_access_tokens):
            # 1. Try to get institution name from DB first (in case sync fails)
            existing_item = session.exec(
                select(PlaidItem).where(PlaidItem.access_token == token)
            ).first()
            inst_name = (
                existing_item.institution_name
                if existing_item and existing_item.institution_name
                else "Unknown Institution"
            )

            # 2. Sync Accounts (to get Institution ID/Name)
            inst_id = service.sync_accounts(token, inst_name)

            if inst_id:
                try:
                    # Update PlaidItem metadata
                    plaid_item = session.exec(
                        select(PlaidItem).where(PlaidItem.access_token == token)
                    ).first()

                    if not plaid_item:
                        plaid_item = PlaidItem(access_token=token)
                        session.add(plaid_item)

                    plaid_item.institution_id = inst_id

                    # Fetch Institution Name
                    request = InstitutionsGetByIdRequest(
                        institution_id=inst_id, country_codes=[CountryCode("US")]
                    )
                    inst_response = service.client.institutions_get_by_id(request)
                    inst_name = inst_response["institution"]["name"]
                    plaid_item.institution_name = inst_name

                    session.add(plaid_item)
                    session.commit()
                except Exception as e:
                    logger.warning(f"Could not resolve institution name: {e}")
                    inst_name = f"Institution {inst_id}"

            token_map[token] = inst_name
            logger.info(
                f"--- Syncing {inst_name} ({i + 1}/{len(settings.plaid_access_tokens)}) ---"
            )

            # 2. Sync Data
            if settings.excluded_account_ids:
                logger.info(
                    f"Excluding {len(settings.excluded_account_ids)} account(s)."
                )

            service.sync_transactions(
                token, inst_name, settings.excluded_account_ids, seen_tx_keys, seen_content_keys
            )
            service.sync_holdings(token, inst_name, settings.excluded_account_ids)
            service.sync_investment_transactions(
                token, inst_name, 730, settings.excluded_account_ids
            )
            service.sync_liabilities(token, inst_name, settings.excluded_account_ids)

        # Summary
        logger.info("=" * 60)
        logger.info(f"{'INSTITUTION':<30} | {'ACCESS TOKEN'}")
        logger.info("-" * 60)
        for token, name in token_map.items():
            logger.info(f"{name:<30} | {token}")
        logger.info("=" * 60)


if __name__ == "__main__":
    run_sync()
