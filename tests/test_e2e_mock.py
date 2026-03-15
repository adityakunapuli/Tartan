"""End-to-end integration tests (Mocked)."""

import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import select

from services.plaid_sync import run_sync
from services.llm_categorizer import run_categorization
from reports.portfolio_summary import print_portfolio_summary
from db.models import Transaction, CategoryRule, PlaidItem
import datetime # Import datetime for date object usage in mocks


@pytest.fixture
def mock_plaid_env():
    """Sets up environment variables for Plaid sync."""
    with (
        patch("config.Config.PLAID_ACCESS_TOKENS", ["token_1"]),
        patch("config.Config.PLAID_CLIENT_ID", "id"),
        patch("config.Config.PLAID_SECRET", "secret")
    ):
        yield

@patch("services.plaid_sync.PlaidSyncService._get_plaid_client")
@patch("services.llm_categorizer.query_llm")
def test_full_pipeline_mocked(mock_llm, mock_get_client, db_session, mock_plaid_env):
    """
    Test the full data pipeline:
    1. Sync (Mock Plaid) -> DB
    2. Categorize (Mock LLM) -> DB Rules
    3. Report (Read DB) -> No Errors
    """
    pass

# We need to override the global engine used by the app to match the test engine
# This is tricky with global variables. 
# Better strategy: Patch the 'engine' object in the modules we are testing.

@pytest.fixture(autouse=True)
def patch_engine(db_session):
    """Patches the engine in service modules to use the test session's bind."""
    test_engine = db_session.bind
    
    # Patch where 'engine' is imported and used directly
    with (
        patch("services.plaid_sync.engine", test_engine),
        patch("services.llm_categorizer.engine", test_engine),
        patch("services.data_layer.engine", test_engine),
        patch("db.session.engine", test_engine) # Patching db.session.engine ensures init_db works
    ):
        yield

@patch("services.plaid_sync.PlaidSyncService._get_plaid_client")
@patch("services.llm_categorizer.query_llm")
def test_full_pipeline_execution(mock_llm, mock_get_client, mock_plaid_env, db_session):
    """Tests the entire pipeline: Sync -> Categorize -> Report."""
    
    # Setup Mocks for Plaid API responses
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # --- Mock Accounts Response ---
    # Configure mock account with ALL required fields as attributes
    mock_acc = MagicMock()
    # Primitives
    mock_acc.account_id = "a1"
    mock_acc.name = "Checking"
    mock_acc.mask = "0000"
    mock_acc.type = "depository"
    mock_acc.subtype = "checking"
    mock_acc.apy = None
    mock_acc.interest_rate = None
    mock_acc.maturity_date = None
    
    # Balances object
    mock_balances = MagicMock()
    mock_balances.current = 100.0
    mock_balances.available = 100.0
    mock_balances.iso_currency_code = "USD"
    mock_balances.limit = None
    mock_acc.balances = mock_balances
    
    mock_acc.to_dict.return_value = {"account_id": "a1", "name": "Checking", "balances": {"current": 100.0}}

    mock_acc_resp = MagicMock()
    mock_acc_resp.accounts = [mock_acc] 

    def acc_getitem(name):
        if name == "item": return {"institution_id": "ins_1"}
        if name == "accounts": return [mock_acc]
        return MagicMock()
    
    mock_acc_resp.__getitem__.side_effect = acc_getitem
    mock_acc_resp.item = {"institution_id": "ins_1"} 
    
    mock_client.accounts_get.return_value = mock_acc_resp
    
    # --- Mock Institution Response ---
    mock_client.institutions_get_by_id.return_value = {"institution": {"name": "TestBank"}}
    
    # --- Mock Transactions Sync Response ---
    mock_tx = MagicMock()
    mock_tx.transaction_id = "tx1"
    mock_tx.account_id = "a1"
    mock_tx.date = datetime.date(2023, 1, 1) # Use datetime.date object
    mock_tx.name = "Unknown Store"
    mock_tx.amount = 50.0
    mock_tx.category = ["Gen"]
    mock_tx.category_id = "123"
    mock_tx.merchant_name = None
    mock_tx.pending = False
    mock_tx.payment_channel = "online"
    mock_tx.iso_currency_code = "USD"
    mock_tx.to_dict.return_value = {"transaction_id": "tx1", "account_id": "a1", "name": "Unknown Store", "amount": 50.0}
    
    mock_sync = MagicMock(added=[mock_tx], modified=[], removed=[], next_cursor="c1")
    # Mock __getitem__ for sync response attributes
    mock_sync.__getitem__.side_effect = lambda k: False if k == "has_more" else getattr(mock_sync, k)
    mock_client.transactions_sync.return_value = mock_sync
    
    # --- Mock Investments Transactions ---
    mock_inv_tx_resp = MagicMock()
    def inv_tx_getitem(name):
        if name == "investment_transactions": return []
        if name == "securities": return []
        if name == "total_investment_transactions": return 0
        return MagicMock()
    mock_inv_tx_resp.__getitem__.side_effect = inv_tx_getitem
    mock_client.investments_transactions_get.return_value = mock_inv_tx_resp

    # --- Mock Investments Holdings ---
    mock_inv_hold_resp = MagicMock()
    def inv_hold_getitem(name):
        if name == "holdings": return []
        if name == "securities": return []
        return MagicMock()
    mock_inv_hold_resp.__getitem__.side_effect = inv_hold_getitem
    mock_client.investments_holdings_get.return_value = mock_inv_hold_resp

    # --- Mock Liabilities ---
    mock_liab_resp = MagicMock()
    mock_liab_resp.liabilities = {} # For attr access if used
    mock_liab_resp.__getitem__.side_effect = lambda k: {} if k == "liabilities" else MagicMock()
    mock_client.liabilities_get.return_value = mock_liab_resp

    # --- EXECUTE FULL PIPELINE ---
    run_sync() # This will call sync_accounts, sync_transactions etc.
    
    # --- VERIFY SYNC RESULTS ---
    txs = db_session.exec(select(Transaction)).all()
    assert len(txs) == 1
    assert txs[0].name == "Unknown Store"
    
    # --- EXECUTE STEP 2: CATEGORIZE ---
    mock_llm.return_value = ("Shopping", "EXPENSE")
    
    run_categorization()
    
    # Verify Rules were created
    rules = db_session.exec(select(CategoryRule)).all()
    assert len(rules) == 1
    assert rules[0].match_value == "UNKNOWN STORE"
    assert rules[0].category == "Shopping"
    
    # --- EXECUTE STEP 3: REPORT ---
    try:
        print_portfolio_summary()
    except Exception as e:
        pytest.fail(f"Report generation failed: {e}")
