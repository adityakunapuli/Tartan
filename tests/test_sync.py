"""Tests for the synchronization services."""

import datetime
from unittest.mock import MagicMock

from backend.modules.accounts.models import Account, PlaidItem
from backend.modules.investments.models import InvestmentHolding
from backend.modules.transactions.models import Transaction
from backend.modules.plaid_integration.sync import PlaidSyncService
from sqlalchemy import select


# Mock Response Objects
class MockTransaction:
    """Mock object for Plaid transaction."""

    def __init__(self, id, amount, name, pending=False):
        """Initializes a mock transaction.

        Args:
            id (str): Transaction ID.
            amount (float): Transaction amount.
            name (str): Transaction name.
            pending (bool): Whether the transaction is pending.
        """
        self.transaction_id = id
        self.account_id = "acc_123"
        # Use date object
        self.date = datetime.date(2023, 1, 1)
        self.name = name
        self.amount = amount
        self.iso_currency_code = "USD"
        self.category = ["General"]
        self.category_id = "123"
        self.pending = pending
        self.merchant_name = name
        self.payment_channel = "online"

    def to_dict(self):
        """Converts the mock transaction to a dictionary."""
        return self.__dict__


class MockSyncResponse:
    """Mock object for Plaid transactions sync response."""

    def __init__(
        self, added, modified, removed, next_cursor, has_more, item_id="item_123"
    ):
        """Initializes the mock sync response.

        Args:
            added (list): List of added transactions.
            modified (list): List of modified transactions.
            removed (list): List of removed transactions.
            next_cursor (str): The next cursor.
            has_more (bool): Whether there are more transactions.
            item_id (str): The Plaid Item ID.
        """
        self.added = added
        self.modified = modified
        self.removed = removed
        self.next_cursor = next_cursor
        self.has_more = has_more
        self.request_id = "req_123"
        self._data = {"item_id": item_id}

    def __getitem__(self, key):
        """Allows dictionary-style access to attributes."""
        if key in ["added", "modified", "removed", "next_cursor", "has_more"]:
            return getattr(self, key)
        return self._data.get(key)

    def get(self, key):
        """Gets a value from the internal data dictionary."""
        return self._data.get(key)

    def to_dict(self):
        """Returns the internal data dictionary."""
        return self._data


class MockAccountResponse:
    """Mock object for Plaid accounts get response."""

    def __init__(self, accounts, item_id="item_123", inst_id="ins_1"):
        """Initializes the mock account response.

        Args:
            accounts (list): List of mock accounts.
            item_id (str): The Plaid Item ID.
            inst_id (str): The Institution ID.
        """
        self.accounts = accounts
        self.item = {"institution_id": inst_id, "item_id": item_id}

    def __getitem__(self, key):
        """Allows dictionary-style access to attributes."""
        if key == "accounts":
            return self.accounts
        if key == "item":
            return self.item
        return None


class MockAccount:
    """Mock object for a Plaid account."""

    def __init__(self, id, current, available=None):
        """Initializes a mock account.

        Args:
            id (str): Account ID.
            current (float): Current balance.
            available (float, optional): Available balance.
        """
        self.account_id = id
        self.name = "Checking"
        self.mask = "0000"
        self.type = "depository"
        self.subtype = "checking"
        self.balances = MagicMock(
            current=current, available=available, iso_currency_code="USD", limit=None
        )
        self.apy = 0.0
        self.interest_rate = 0.0
        self.maturity_date = None

    def to_dict(self):
        """Converts the mock account to a dictionary."""
        return {
            "account_id": self.account_id,
            "name": self.name,
            "balances": {"current": self.balances.current},
        }


def test_sync_accounts(db_session, mock_plaid_client):
    """Tests the sync_accounts function.

    Args:
        db_session: The database session fixture.
        mock_plaid_client: The mock Plaid client fixture.
    """
    # Setup
    service = PlaidSyncService(db_session)
    service.client = mock_plaid_client  # Override with mock

    acc = MockAccount("acc_1", 100.0)
    mock_plaid_client.accounts_get.return_value = MockAccountResponse(
        [acc], inst_id="ins_test"
    )

    # Execute
    inst_id = service.sync_accounts("token_123", "Test Inst")

    # Verify Return
    assert inst_id == "ins_test"

    # Verify DB
    saved_acc = db_session.execute(
        select(Account).where(Account.account_id == "acc_1")
    ).scalar_one()
    assert saved_acc.current_balance == 100.0


def test_sync_transactions_incremental(db_session, mock_plaid_client):
    """Tests incremental transaction synchronization.

    Args:
        db_session: The database session fixture.
        mock_plaid_client: The mock Plaid client fixture.
    """
    # Setup initial state
    token = "token_abc"
    db_session.add(PlaidItem(access_token=token, next_cursor="cursor_1"))
    db_session.commit()

    service = PlaidSyncService(db_session)
    service.client = mock_plaid_client

    # Mock Plaid Response
    # 1. First Page: 1 Added
    tx1 = MockTransaction("tx_1", 50.0, "Walmart")
    resp1 = MockSyncResponse(
        added=[tx1],
        modified=[],
        removed=[],
        next_cursor="cursor_2",
        has_more=False,
    )

    mock_plaid_client.transactions_sync.side_effect = [resp1]

    # Execute
    service.sync_transactions(token, "Test Inst")

    # Verify DB
    tx = db_session.execute(
        select(Transaction).where(Transaction.transaction_id == "tx_1")
    ).scalar_one()
    assert tx.name == "Walmart"
    assert tx.amount == 50.0

    # Verify Cursor Update
    item = db_session.execute(
        select(PlaidItem).where(PlaidItem.access_token == token)
    ).scalar_one()
    assert item.next_cursor == "cursor_2"


def test_sync_transactions_removals(db_session, mock_plaid_client):
    """Tests transaction removal synchronization.

    Args:
        db_session: The database session fixture.
        mock_plaid_client: The mock Plaid client fixture.
    """
    # Setup: Existing transaction
    token = "token_xyz"
    db_session.add(PlaidItem(access_token=token, next_cursor="c1"))
    db_session.add(
        Transaction(
            transaction_id="tx_del",
            account_id="acc_1",
            name="Old",
            amount=10.0,
            date=datetime.date(2023, 1, 1),
            pending=False,
        )
    )
    db_session.commit()

    service = PlaidSyncService(db_session)
    service.client = mock_plaid_client

    # Mock Response: 1 Removed
    removed_item = {"transaction_id": "tx_del"}
    resp = MockSyncResponse(
        added=[],
        modified=[],
        removed=[removed_item],
        next_cursor="c2",
        has_more=False,
    )
    mock_plaid_client.transactions_sync.return_value = resp

    # Execute
    service.sync_transactions(token, "Test Inst")

    # Verify Removal
    tx = db_session.execute(
        select(Transaction).where(Transaction.transaction_id == "tx_del")
    ).scalar_one_or_none()
    assert tx is None


def test_sync_holdings_cleanup(db_session, mock_plaid_client):
    """Tests that old holdings are cleaned up (deleted) during sync.

    Args:
        db_session: The database session fixture.
        mock_plaid_client: The mock Plaid client fixture.
    """
    # Setup: Zombie holding from 'today' (simulating re-run)
    token = "token_inv"
    import datetime

    today = datetime.date.today()

    # Existing Holding
    h1 = InvestmentHolding(
        date_captured=today,
        account_id="acc_inv",
        security_id="sec_1",
        quantity=10,
        institution_price=10.0,
        institution_value=100,
    )
    db_session.add(h1)
    db_session.commit()

    service = PlaidSyncService(db_session)
    service.client = mock_plaid_client

    # Mock Response: Same holding, maybe updated value
    # Plaid returns holdings list
    class MockHolding:
        def __init__(self):
            self.account_id = "acc_inv"
            self.security_id = "sec_1"
            self.quantity = 10
            self.institution_price = 10.0
            self.institution_value = 100.0
            self.cost_basis = 50.0
            self.iso_currency_code = "USD"

        def to_dict(self):
            return self.__dict__

    class MockSecurity:
        def __init__(self):
            self.security_id = "sec_1"
            self.name = "Apple"
            self.ticker_symbol = "AAPL"
            self.institution_security_id = "is_1"
            self.type = "equity"
            self.close_price = 150.0
            self.close_price_as_of = None
            self.iso_currency_code = "USD"
            self.is_cash_equivalent = False

        def to_dict(self):
            return self.__dict__

    mock_resp = {"holdings": [MockHolding()], "securities": [MockSecurity()]}
    mock_plaid_client.investments_holdings_get.return_value = mock_resp

    # Execute
    service.sync_holdings(token, "Test Inst")

    # Verify: Should still have 1 holding (zombie deleted, new added)
    holdings = db_session.execute(select(InvestmentHolding)).scalars().all()
    assert len(holdings) == 1
    assert holdings[0].security_id == "sec_1"
