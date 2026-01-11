"""Service for categorizing transactions using a local LLM."""

import requests
import json
import re
import statistics
from collections import Counter
from typing import Optional
from sqlalchemy import select
from analysis.db.session import SessionLocal
from analysis.db.models import Transaction, CategoryRule

LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"

CATEGORIES = [
    'Groceries', 'Dining', 'Transport', 'Utilities', 'Housing', 
    'Income', 'Transfer', 'Shopping', 'Health', 'Entertainment', 
    'Tech', 'Services', 'Financial', 'Travel', 'Education', 'General'
]

SYSTEM_PROMPT = f"""
You are a financial transaction categorizer.
Your goal is to map a transaction pattern to exactly ONE of the following categories:
{json.dumps(CATEGORIES)}

Input is a JSON object describing a cluster of transactions (pattern, sample names, amounts, dates).
Output must be a JSON object with a single key "category".
Rules:
- "Venmo", "Zelle", "PayPal", "Wire" -> "Transfer"
- "Payroll", "Deposit", "Credit" -> "Income" (if amount is negative/credit)
- "Mortgage", "Rent" -> "Housing"
- "Gas", "Fuel" -> "Transport"
- "Restaurant", "Cafe", "Coffee", "Burger" -> "Dining"
- "Spotify", "Netflix", "Hulu" -> "Entertainment"
- "AWS", "Google Cloud", "Apple" -> "Tech" or "Shopping"
- "Loan" -> "Financial"
"""

def clean_name(name: str) -> str:
    """Cleans the transaction name by removing prefixes, dates, and special characters.

    Args:
        name (str): The raw transaction name.

    Returns:
        str: The cleaned name.
    """
    if not name:
        return "UNKNOWN"
    # Remove common prefixes
    name = re.sub(r'^(CHECKCARD|PURCHASE|POS PURCHASE|DEBIT CARD PURCHASE)\s*\d*\s*', '', name, flags=re.IGNORECASE)
    # Remove dates (MM/DD, MM-DD)
    name = re.sub(r'\b\d{1,2}[/-]\d{1,2}\b', '', name)
    # Remove large number sequences (IDs)
    name = re.sub(r'\b\d{4,}\b', '', name)
    # Remove special chars
    name = re.sub(r'[^\w\s]', ' ', name)
    return ' '.join(name.split()).upper()

def query_llm(context_data: dict) -> Optional[str]:
    """Queries the local LLM to categorize a transaction pattern.

    Args:
        context_data (dict): The context for the transaction pattern.

    Returns:
        str | None: The suggested category, or None if the LLM is unreachable.
    """
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context_data)}
        ],
        "temperature": 0.1,
        "max_tokens": 50,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(LLM_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        if content.startswith("```json"):
            content = content[7:-3]
        return json.loads(content).get('category', 'General')
    except requests.exceptions.ConnectionError:
        print(f"  -> Warning: LLM endpoint ({LLM_URL}) is unreachable. Skipping categorization.")
        return None
    except Exception as e:
        print(f"LLM Error: {e}")
        return "General"

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
        "plaid_categories": list(set(str(t.category) for t in transactions[:3]))
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
            ktype = 'merchant_name'
        else:
            key = clean_name(tx.name)
            ktype = 'pattern'
            
        if key not in clusters:
            clusters[key] = {'type': ktype, 'txs': []}
        clusters[key]['txs'].append(tx)
        
    print(f"Identified {len(clusters)} unique patterns/merchants.")
    
    # 3. Process Clusters
    new_rules = 0
    
    for key, data in clusters.items():
        # Check if rule exists
        existing = session.execute(
            select(CategoryRule).where(
                (CategoryRule.match_value == key) & 
                (CategoryRule.match_type == data['type'])
            )
        ).scalar_one_or_none()
        
        if existing:
            continue
            
        # Analyze Cluster
        stats = get_cluster_stats(data['txs'])
        
        context = {
            "pattern": key,
            "type": data['type'],
            **stats
        }
        
        print(f"Categorizing [{data['type']}]: {key} ({len(data['txs'])} txs)...")
        # print(f"  Context: {json.dumps(stats)}")
        
        category = query_llm(context)
        if category is None:
            continue
            
        print(f"  -> {category}")
        
        rule = CategoryRule(match_value=key, match_type=data['type'], category=category)
        session.add(rule)
        new_rules += 1
        
        if new_rules % 10 == 0:
            session.commit()
            
    session.commit()
    print(f"Categorization complete. Added {new_rules} new rules.")
    session.close()

if __name__ == "__main__":
    run_categorization()
