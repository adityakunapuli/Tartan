"""Service for categorizing transactions using a local LLM."""

import json
import statistics
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import requests
from sqlmodel import select, Session

from backend.core.config import settings
from backend.core.database import engine
from backend.modules.transactions.models import Transaction
from backend.modules.rules.models import CategoryRule
from backend.modules.accounts.models import Account
from utils.helpers import clean_name
from utils.logger import get_logger

from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)

# LLM Configuration
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_WORKERS = max(1, int(os.getenv("LLM_WORKERS", "4")))


def _fetch_transactions(session: Session) -> list[Transaction]:
    """Fetch transactions, excluding those from ignored accounts.

    Args:
        session: SQLModel session.

    Returns:
        List of Transaction objects to process.
    """
    excluded_ids = settings.excluded_account_ids.copy()
    excluded_names = settings.excluded_account_names
    
    if excluded_names:
        accounts = session.exec(select(Account)).all()
        for a in accounts:
            if a.name and a.name.lower() in excluded_names:
                excluded_ids.add(a.account_id)

    if excluded_ids:
        logger.info(f"Excluding {len(excluded_ids)} account(s) from categorization.")
    
    # In a real prod env, we might want to filter in SQL, but for local 
    # finance, filtering in Python after fetch is acceptable and keeps 
    # the 'excluded_names' logic simple without complex joins.
    all_tx = session.exec(select(Transaction)).all()
    
    if not excluded_ids:
        return list(all_tx)

    valid_tx = [t for t in all_tx if t.account_id not in excluded_ids]
    skipped = len(all_tx) - len(valid_tx)
    if skipped > 0:
        logger.info(f"Skipped {skipped} transaction(s) due to exclusions.")
        
    return valid_tx


def _group_transactions(transactions: list[Transaction]) -> dict[str, dict]:
    """Group transactions by merchant name or cleaned name pattern.

    Args:
        transactions: List of transactions.

    Returns:
        Dictionary of clusters keyed by pattern/merchant name.
    """
    clusters = {}
    for tx in transactions:
        if tx.merchant_name:
            key = tx.merchant_name
            ktype = "merchant_name"
        else:
            key = clean_name(tx.name)
            ktype = "pattern"

        if key not in clusters:
            clusters[key] = {"type": ktype, "txs": []}
        clusters[key]["txs"].append(tx)
    
    return clusters


CATEGORIES = [
    "Groceries",
    "Dining",
    "Transport",
    "Utilities",
    "Housing",
    "Income",
    "Transfer",
    "Shopping",
    "Health",
    "Entertainment",
    "Tech",
    "Services",
    "Financial",
    "Travel",
    "Education",
    "General",
]

SYSTEM_PROMPT = f"""
You are a financial transaction categorizer.
Your goal is to map a transaction pattern to:
1. A 'category' from the list: {json.dumps(CATEGORIES)}
2. A 'flow_type' from: ["INCOME", "EXPENSE", "TRANSFER"]

Input is a JSON object describing a cluster of transactions.
Output must be a JSON object with keys "category" and "flow_type".

CRITICAL LOGIC RULES:
- "TRANSFER": 
    - Credit Card Payments (e.g. "Payment to Visa", "Autopay", "Chase Card").
    - Loan Payments (e.g. "Auto Loan", "Mortgage Payment").
    - Transfers between accounts (e.g. "Transfer to Savings", "Zelle to self").
    - Investment deposits.
    - These are balance sheet movements, NOT spending.
- "INCOME":
    - Payroll, Salary, Deposit, Interest, Refunds.
- "EXPENSE":
    - Real spending (Groceries, Rent, Utilities, Dining).
    - If it buys a good or service, it is an EXPENSE.

Examples:
- "Payment to Credit Card" -> {{"category": "Transfer", "flow_type": "TRANSFER"}}
- "Bank Auto Loan" -> {{"category": "Transfer", "flow_type": "TRANSFER"}}
- "Grocery Store" -> {{"category": "Groceries", "flow_type": "EXPENSE"}}
- "Payroll Deposit" -> {{"category": "Income", "flow_type": "INCOME"}}
"""


def query_llm(context_data: dict) -> tuple[str, str] | None:
    """Queries the local LLM to categorize a transaction pattern.

    Args:
        context_data (dict): The context for the transaction pattern.

    Returns:
        tuple[str, str] | None: (category, flow_type). Returns ("General", "EXPENSE") on failure.
        Returns None if the endpoint is unreachable.
    """
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context_data)},
        ],
        "temperature": 0.1,
        "max_tokens": 100,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(OPENAI_BASE_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        if content.startswith("```json"):
            content = content[7:-3]

        data = json.loads(content)
        return data.get("category", "General"), data.get("flow_type", "EXPENSE")

    except requests.exceptions.ConnectionError:
        logger.warning(
            f"LLM endpoint ({OPENAI_BASE_URL}) is unreachable. Skipping categorization."
        )
        return None
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return "General", "EXPENSE"


def get_cluster_stats(transactions: list) -> dict:
    """Calculates statistics for a cluster of transactions.

    Args:
        transactions (list): List of Transaction objects.

    Returns:
        dict: A dictionary of statistics.
    """
    if not transactions:
        return {}

    amounts = [t.amount for t in transactions]
    avg_amt = statistics.mean(amounts) if amounts else 0
    dates = [t.date.day for t in transactions if t.date]
    common_day = Counter(dates).most_common(1)[0][0] if dates else "N/A"
    channels = [t.payment_channel for t in transactions]
    common_channel = Counter(channels).most_common(1)[0][0] if channels else "N/A"

    return {
        "avg_amount": f"${avg_amt:.2f}",
        "sample_names": [t.name for t in transactions[:3]],
        "common_day_of_month": common_day,
        "payment_channel": common_channel,
        "plaid_categories": list(set(str(t.category) for t in transactions[:3])),
    }


def _process_categorization(session: Session, clusters: dict[str, dict]) -> None:
    """Submit clusters to LLM and save rules.

    Args:
        session: Database session.
        clusters: Grouped transactions.
    """
    new_rules = 0
    pending = []

    # 1. Filter out existing rules
    for key, data in clusters.items():
        existing = session.exec(
            select(CategoryRule).where(
                (CategoryRule.match_value == key)
                & (CategoryRule.match_type == data["type"])
            )
        ).first()

        if not existing:
            stats = get_cluster_stats(data["txs"])
            context = {"pattern": key, "type": data["type"], **stats}
            pending.append((key, data["type"], len(data["txs"]), context))

    if not pending:
        logger.info("No new merchants/patterns to categorize.")
        return

    logger.info(f"Queued {len(pending)} patterns for LLM categorization with {LLM_WORKERS} workers.")

    # 2. Parallel LLM Querying
    results = []
    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        future_map = {
            executor.submit(query_llm, context): (key, match_type, tx_count)
            for key, match_type, tx_count, context in pending
        }

        for future in as_completed(future_map):
            key, match_type, tx_count = future_map[future]
            try:
                result = future.result()
            except Exception as e:
                logger.error(f"LLM Error for [{match_type}]: {key}: {e}")
                continue

            if result:
                category, flow_type = result
                logger.info(f"Categorized [{match_type}]: {key} ({tx_count} txs) -> {category} ({flow_type})")
                results.append((key, match_type, category, flow_type))

    # 3. Save Rules
    for key, match_type, category, flow_type in results:
        rule = CategoryRule(
            match_value=key,
            match_type=match_type,
            category=category,
            flow_type=flow_type,
        )
        session.add(rule)
        new_rules += 1

        if new_rules % 10 == 0:
            session.commit()

    session.commit()
    logger.info(f"Categorization complete. Added {new_rules} new rules.")


def run_categorization() -> None:
    """Orchestrates the categorization process for uncategorized transaction patterns."""
    with Session(engine) as session:
        transactions = _fetch_transactions(session)
        logger.info(f"Loaded {len(transactions)} valid transactions.")
        
        clusters = _group_transactions(transactions)
        logger.info(f"Identified {len(clusters)} unique patterns/merchants.")
        
        _process_categorization(session, clusters)


if __name__ == "__main__":
    run_categorization()
