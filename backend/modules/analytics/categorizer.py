"""Service for categorizing transactions using a local LLM."""

import json
import statistics
import os
from collections import Counter
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic import BaseModel
from sqlmodel import select, Session

from core.config import settings
from core.db.database import engine
from modules.transactions.models import Transaction
from modules.rules.models import CategoryRule
from modules.accounts.models import Account
from utils.helpers import clean_name
from utils.logger import get_logger

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

logger = get_logger(__name__)

# LLM Configuration
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-local")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "Qwen3.6-27B:fast")
LLM_WORKERS = max(1, int(os.getenv("LLM_WORKERS", "1")))

# Initialize AsyncOpenAI client with timeout and wrap it in the provider
async_openai_client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    timeout=120.0
)

openai_provider = OpenAIProvider(
    openai_client=async_openai_client
)

llm_model = OpenAIChatModel(
    OPENAI_MODEL,
    provider=openai_provider
)

class CategoryItem(BaseModel):
    """A single categorized transaction pattern from the LLM."""

    id: str
    category: str
    flow_type: str

class BatchCategoryResult(BaseModel):
    """Container for a batch of categorized items returned by the LLM."""

    items: list[CategoryItem]


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
    "Credit Card Payment",
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

# Try loading prompt template from file, otherwise fallback to default
root_dir = os.path.dirname(find_dotenv())
prompt_path = os.path.join(root_dir, "modules", "analytics", "prompt.txt")
try:
    with open(prompt_path, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT_TEMPLATE = f.read()
except Exception:
    SYSTEM_PROMPT_TEMPLATE = """
You are a financial transaction categorizer.
Your goal is to map a batch of transaction patterns to:
1. A 'category' from the list: {categories}
2. A 'flow_type' from: ["INCOME", "EXPENSE", "TRANSFER"]

Input is a JSON array of transaction pattern clusters, where each item has a unique "id".
Output must contain a list of items, each with the matching "id", "category", and "flow_type".

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
"""

SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.format(categories=json.dumps(CATEGORIES))


agent = Agent(
    llm_model,
    system_prompt=SYSTEM_PROMPT,
    output_type=BatchCategoryResult,
    model_settings=ModelSettings(max_tokens=4096, temperature=0.1)
)


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

    logger.info(
        f"Queued {len(pending)} patterns for LLM categorization."
    )

    # 2. Batch LLM Querying
    batch_size = 5
    results = []
    
    # Store key/match_type map to match results back
    # Use numeric indices as string keys to avoid type conversion and Pydantic validation errors
    pending_map = {str(idx): (key, match_type, tx_count) for idx, (key, match_type, tx_count, _) in enumerate(pending)}

    for i in range(0, len(pending), batch_size):
        chunk = pending[i : i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1}/{(len(pending) - 1) // batch_size + 1} ({len(chunk)} items)...")
        
        # Use simple string index IDs (e.g. "0", "1", "2") to avoid Pydantic parsing issues with numbers or merchant strings
        context_batch = [{"id": str(i + offset), **context} for offset, (_, _, _, context) in enumerate(chunk)]
        
        result = agent.run_sync(json.dumps(context_batch))
        
        for item in result.output.items:
            if item.id in pending_map:
                key, match_type, tx_count = pending_map[item.id]
                logger.info(
                    f"Categorized [{match_type}]: {key} ({tx_count} txs) -> {item.category} ({item.flow_type})"
                )
                results.append((key, match_type, item.category, item.flow_type))

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
