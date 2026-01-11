"""Service for categorizing transactions using a local LLM."""

import requests
import json
import statistics
from collections import Counter
from sqlalchemy import select
from analysis.db.session import SessionLocal
from analysis.db.models import Transaction, CategoryRule
from analysis.utils import clean_name

LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"

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
    - Loan Payments (e.g. "Bank Name Auto Loan", "Toyota Financial", "Mortgage Payment").
    - Transfers between accounts (e.g. "Transfer to Savings", "Zelle to self").
    - Investment deposits.
    - These are balance sheet movements, NOT spending.
- "INCOME":
    - Payroll, Salary, Deposit, Interest, Refunds.
- "EXPENSE":
    - Real spending (Groceries, Rent, Utilities, Dining).
    - If it buys a good or service, it is an EXPENSE.

Examples:
- "Payment to Chase Card" -> {{"category": "Transfer", "flow_type": "TRANSFER"}}
- "Bank Name Auto Loan" -> {{"category": "Transfer", "flow_type": "TRANSFER"}}
- "Giant Eagle" -> {{"category": "Groceries", "flow_type": "EXPENSE"}}
- "Payroll Deposit" -> {{"category": "Income", "flow_type": "INCOME"}}
"""


def query_llm(context_data: dict) -> tuple[str, str]:
    """Queries the local LLM to categorize a transaction pattern.

    Args:
        context_data (dict): The context for the transaction pattern.

    Returns:
        tuple[str, str]: (category, flow_type). Returns ("General", "EXPENSE") on failure.
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
        response = requests.post(LLM_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        if content.startswith("```json"):
            content = content[7:-3]

        data = json.loads(content)
        return data.get("category", "General"), data.get("flow_type", "EXPENSE")

    except requests.exceptions.ConnectionError:
        print(
            f"  -> Warning: LLM endpoint ({LLM_URL}) is unreachable. Skipping categorization."
        )
        return None
    except Exception as e:
        print(f"LLM Error: {e}")
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


def run_categorization() -> None:
    """Orchestrates the categorization process for uncategorized transaction patterns."""
    session = SessionLocal()

    # 1. Fetch all transactions
    all_tx = session.execute(select(Transaction)).scalars().all()
    print(f"Loaded {len(all_tx)} transactions.")

    # 2. Group by Key
    # Priority: Merchant Name -> Cleaned Name
    clusters = {}

    for tx in all_tx:
        if tx.merchant_name:
            key = tx.merchant_name
            ktype = "merchant_name"
        else:
            key = clean_name(tx.name)
            ktype = "pattern"

        if key not in clusters:
            clusters[key] = {"type": ktype, "txs": []}
        clusters[key]["txs"].append(tx)

    print(f"Identified {len(clusters)} unique patterns/merchants.")

    # 3. Process Clusters
    new_rules = 0

    for key, data in clusters.items():
        # Check if rule exists
        existing = session.execute(
            select(CategoryRule).where(
                (CategoryRule.match_value == key)
                & (CategoryRule.match_type == data["type"])
            )
        ).scalar_one_or_none()

        if existing:
            continue

        # Analyze Cluster
        stats = get_cluster_stats(data["txs"])

        context = {"pattern": key, "type": data["type"], **stats}

        print(f"Categorizing [{data['type']}]: {key} ({len(data['txs'])} txs)...")
        # print(f"  Context: {json.dumps(stats)}")

        result = query_llm(context)
        if result is None:
            continue

        category, flow_type = result
        print(f"  -> {category} ({flow_type})")

        rule = CategoryRule(
            match_value=key,
            match_type=data["type"],
            category=category,
            flow_type=flow_type,
        )
        session.add(rule)
        new_rules += 1

        if new_rules % 10 == 0:
            session.commit()

    session.commit()
    print(f"Categorization complete. Added {new_rules} new rules.")
    session.close()


if __name__ == "__main__":
    run_categorization()
