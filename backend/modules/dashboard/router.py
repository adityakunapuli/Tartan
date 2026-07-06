"""API endpoints for the frontend dashboard."""
import datetime
import json
import asyncio
import threading
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func
from core.config import settings
from core.db.database import get_db
from modules.accounts.models import Account, Liability, PlaidItem
from modules.transactions.models import Transaction
from modules.rules.models import CategoryRule
from utils.helpers import clean_name

router = APIRouter(prefix="/api", tags=["dashboard"])

# In-memory sync state tracker for SSE streaming
_sync_lock = threading.Lock()
_sync_state = {
    "is_running": False,
    "step": "",
    "detail": "",
}
_sync_event = threading.Event()


def _get_excluded_account_ids(db: Session) -> set[str]:
    """Resolves excluded account names to IDs and returns the full exclusion set."""
    excluded = settings.excluded_account_ids.copy()
    if settings.excluded_account_names:
        accounts = db.exec(select(Account)).all()
        for a in accounts:
            if a.name and a.name.lower() in settings.excluded_account_names:
                excluded.add(a.account_id)
    return excluded


def _set_sync_state(is_running: bool | None = None, step: str | None = None, detail: str | None = None):
    with _sync_lock:
        if is_running is not None:
            _sync_state["is_running"] = is_running
        if step is not None:
            _sync_state["step"] = step
        if detail is not None:
            _sync_state["detail"] = detail
    _sync_event.set()


@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Returns aggregate financial summary for the dashboard overview."""
    today = datetime.date.today()
    first_of_month = today.replace(day=1)
    excluded = _get_excluded_account_ids(db)

    stmt = select(Account)
    if excluded:
        stmt = stmt.where(Account.account_id.not_in(excluded))
    accounts = db.exec(stmt).all()
    total_balance = sum(a.current_balance or 0 for a in accounts)
    total_assets = sum(
        a.current_balance or 0
        for a in accounts
        if a.type in ("depository", "investment")
    )

    stmt = select(Liability)
    if excluded:
        stmt = stmt.where(Liability.account_id.not_in(excluded))
    liabilities = db.exec(stmt).all()
    total_liabilities = sum(l.principal_amount or 0 for l in liabilities)
    # also include credit/loan account balances as liabilities
    for a in accounts:
        if a.type in ("credit", "loan") and a.current_balance and a.current_balance > 0:
            total_liabilities += a.current_balance

    stmt = select(Transaction).where(Transaction.date >= first_of_month)
    if excluded:
        stmt = stmt.where(Transaction.account_id.not_in(excluded))
    month_txs = db.exec(stmt).all()
    month_txs = db.exec(stmt).all()
    monthly_income = sum(abs(t.amount) for t in month_txs if t.amount < 0)
    monthly_expenses = sum(t.amount for t in month_txs if t.amount > 0)

    return {
        "total_balance": round(total_balance, 2),
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses": round(monthly_expenses, 2),
        "net_worth": round(total_assets - total_liabilities, 2),
    }


@router.get("/transactions")
def get_transactions(
    account_id: str | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Returns a paginated list of transactions, optionally filtered by account or search term."""
    base_filter = []
    if account_id:
        base_filter.append(Transaction.account_id == account_id)
    if search:
        base_filter.append(Transaction.name.ilike(f"%{search}%"))

    excluded = _get_excluded_account_ids(db)
    if excluded:
        base_filter.append(Transaction.account_id.not_in(excluded))

    count_query = select(func.count(Transaction.transaction_id))
    if base_filter:
        count_query = count_query.where(*base_filter)
    total = db.exec(count_query).one()

    query = select(Transaction).order_by(Transaction.date.desc())
    if base_filter:
        query = query.where(*base_filter)
    transactions = db.exec(query.offset(offset).limit(limit)).all()

    # Load category rules for enrichment
    rules = db.exec(select(CategoryRule)).all()
    merchant_map = {}
    pattern_map = {}
    for r in rules:
        if r.match_type == "merchant_name":
            merchant_map[r.match_value.lower()] = (r.category, r.flow_type)
        else:
            pattern_map[r.match_value.lower()] = (r.category, r.flow_type)

    def enrich(tx: Transaction) -> dict:
        enriched_cat = None

        # Try merchant_name match
        if tx.merchant_name and tx.merchant_name.lower() in merchant_map:
            cat, ft = merchant_map[tx.merchant_name.lower()]
            enriched_cat = cat
            flow = ft
        # Try pattern (cleaned name) match
        elif tx.name:
            cname = clean_name(tx.name).lower()
            if cname in pattern_map:
                cat, ft = pattern_map[cname]
                enriched_cat = cat
                flow = ft
            else:
                flow = tx.flow_type or ("INCOME" if tx.amount < 0 else "EXPENSE" if tx.amount > 0 else "TRANSFER")
        else:
            flow = tx.flow_type or ("INCOME" if tx.amount < 0 else "EXPENSE" if tx.amount > 0 else "TRANSFER")

        return {
            "transaction_id": tx.transaction_id,
            "account_id": tx.account_id,
            "date": str(tx.date),
            "name": tx.name,
            "amount": abs(tx.amount),
            "currency": tx.currency or "USD",
            "flow_type": flow,
            "category": tx.category if isinstance(tx.category, dict) else {},
            "category_id": tx.category_id,
            "enriched_category": enriched_cat,
            "pending": tx.pending,
            "merchant_name": tx.merchant_name,
            "payment_channel": tx.payment_channel or "other",
            "is_recurring": tx.is_recurring,
        }

    result = [enrich(t) for t in transactions]

    # Deduplicate across Plaid items (same real transaction from different items)
    seen = set()
    deduped = []
    for r in result:
        name = (r.get("merchant_name") or r["name"] or "").lower().strip()
        key = (r["date"], round(r["amount"], 2), name)
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return {"transactions": deduped, "total": len(deduped)}


@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    """Returns all financial accounts with current balances."""
    excluded = _get_excluded_account_ids(db)
    stmt = select(Account).order_by(Account.name)
    if excluded:
        stmt = stmt.where(Account.account_id.not_in(excluded))
    accounts = db.exec(stmt).all()
    return {
        "accounts": [
            {
                "account_id": a.account_id,
                "name": a.name,
                "mask": a.mask or "",
                "type": a.type,
                "current_balance": a.current_balance or 0,
                "available_balance": a.available_balance,
                "last_updated": str(a.last_updated),
            }
            for a in accounts
        ]
    }


@router.get("/liabilities")
def get_liabilities(db: Session = Depends(get_db)):
    """Returns all liability records (credit cards, mortgages, loans)."""
    excluded = _get_excluded_account_ids(db)
    stmt = select(Liability)
    if excluded:
        stmt = stmt.where(Liability.account_id.not_in(excluded))
    liabilities = db.exec(stmt).all()
    return {
        "liabilities": [
            {
                "account_id": l.account_id,
                "type": l.type,
                "is_overdue": l.is_overdue or False,
                "last_payment_amount": l.last_payment_amount,
                "last_payment_date": str(l.last_payment_date) if l.last_payment_date else None,
                "next_payment_due_date": str(l.next_payment_due_date) if l.next_payment_due_date else None,
                "minimum_payment_amount": l.minimum_payment_amount,
                "principal_amount": l.principal_amount,
                "interest_rate_percentage": l.interest_rate_percentage,
                "expected_payoff_date": str(l.expected_payoff_date) if l.expected_payoff_date else None,
            }
            for l in liabilities
        ]
    }


@router.get("/sync/status")
def get_sync_status(db: Session = Depends(get_db)):
    """Returns the list of PlaidItem records and their sync state."""
    items = db.exec(select(PlaidItem)).all()
    return {
        "is_running": False,
        "last_sync": None,
        "items": [
            {
                "access_token": item.access_token,
                "item_id": item.item_id,
                "institution_id": item.institution_id,
                "institution_name": item.institution_name,
                "next_cursor": item.next_cursor,
            }
            for item in items
        ],
    }


@router.post("/sync/trigger")
def trigger_sync(db: Session = Depends(get_db)):
    """Triggers a full sync with SSE progress tracking."""
    if _sync_state["is_running"]:
        return {"status": "already_running"}

    from modules.plaid_integration.sync import run_sync

    def _run():
        from core.config import settings
        _set_sync_state(is_running=True, step="starting", detail="Initializing sync...")
        try:
            tokens = settings.plaid_access_tokens
            if not tokens:
                _set_sync_state(step="error", detail="No Plaid tokens configured.")
                return
            _set_sync_state(step="syncing", detail=f"Syncing {len(tokens)} institution(s)...",)
            run_sync()
            _set_sync_state(step="complete", detail="Sync finished.")
        except Exception as e:
            _set_sync_state(step="error", detail=str(e))
        finally:
            _set_sync_state(is_running=False)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"status": "sync_started"}


@router.get("/sync/stream")
async def sync_stream():
    """SSE endpoint streaming sync progress events."""
    async def event_generator():
        _sync_event.clear()
        while True:
            await asyncio.sleep(1)
            with _sync_lock:
                state = dict(_sync_state)
            yield f"data: {json.dumps(state)}\n\n"
            if not state["is_running"]:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")
