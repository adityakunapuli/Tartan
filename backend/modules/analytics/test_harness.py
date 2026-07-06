"""Test harness for optimizing the transaction categorization prompt template.

Evaluates test cases sequentially to minimize local LLM token usage and electricity consumption.
"""

import json
import os
import sys
from dotenv import find_dotenv

# Set root directory for clean imports
sys.path.insert(0, os.path.dirname(find_dotenv()))

from modules.analytics.categorizer import agent


def load_evaluation_set() -> list[dict]:
    """Loads the ground-truth evaluation set.

    Returns:
        list[dict]: List of test case dictionaries.
    """
    root_dir = os.path.dirname(find_dotenv())
    eval_path = os.path.join(root_dir, "data", "evaluation_set.json")
    with open(eval_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_sequential_evaluation() -> None:
    """Runs test cases one-by-one, halting immediately upon the first failure."""
    cases = load_evaluation_set()
    total_cases = len(cases)
    print(f"Loaded {total_cases} test cases. Commencing sequential evaluation...\n")

    for idx, case in enumerate(cases, 1):
        pattern = case["pattern"]
        expected_cat = case["expected_category"]
        expected_flow = case["expected_flow_type"]

        print(f"[{idx}/{total_cases}] Testing pattern: '{pattern}'")
        print(f"      Expected: Category = {expected_cat}, Flow = {expected_flow}")

        # Map to the format the LLM expects
        context_batch = [{
            "id": "test_case",
            "pattern": pattern,
            "type": case["type"],
            "avg_amount": case["avg_amount"],
            "sample_names": case["sample_names"],
            "common_day_of_month": case["common_day_of_month"],
            "payment_channel": case["payment_channel"],
            "plaid_categories": case["plaid_categories"]
        }]

        try:
            # Query the exact agent imported from categorizer
            result = agent.run_sync(json.dumps(context_batch))
            
            if not result.output.items:
                raise ValueError("Model returned an empty items list.")
            
            output_item = result.output.items[0]
            cat = output_item.category
            flow = output_item.flow_type

            print(f"      Got:      Category = {cat}, Flow = {flow}")

            if cat != expected_cat or flow != expected_flow:
                print(f"\n[FAIL] Case #{idx} failed!")
                print(f"   Pattern:   '{pattern}'")
                print(f"   Expected:  Category = '{expected_cat}', Flow = '{expected_flow}'")
                print(f"   Got:       Category = '{cat}', Flow = '{flow}'")
                print("\nStopping evaluation sequence to save resources.")
                sys.exit(1)

            print("      Result:   PASSED\n")

        except Exception as e:
            print(f"\n[ERROR] Exception occurred during evaluation of Case #{idx}: {e}")
            print("Stopping evaluation sequence.")
            sys.exit(1)

    print("SUCCESS: All evaluation cases passed!")
    sys.exit(0)


if __name__ == "__main__":
    run_sequential_evaluation()
