"""Utility to verify the LLM prompt logic without processing the whole DB."""

from analysis.services.llm_categorizer import query_llm

def verify_categorization_logic() -> None:
    """Tests the LLM against critical test cases for flow_type logic."""
    test_cases = [
        {
            "name": "Credit Card Payment",
            "context": {
                "pattern": "PAYMENT TO CHASE CARD", 
                "type": "pattern",
                "avg_amount": "$2500.00"
            },
            "expected_flow": "TRANSFER"
        },
        {
            "name": "Grocery Store",
            "context": {
                "pattern": "GIANT EAGLE #4502", 
                "type": "merchant_name",
                "avg_amount": "$154.20"
            },
            "expected_flow": "EXPENSE"
        },
        {
            "name": "Payroll",
            "context": {
                "pattern": "GUSTO PAYROLL", 
                "type": "pattern",
                "avg_amount": "-$4000.00"
            },
            "expected_flow": "INCOME"
        }
    ]    
    print("Running LLM Verification...\n")    
    all_passed = True
    for test in test_cases:
        print(f"Testing: {test['name']}...")
        category, flow_type = query_llm(test['context'])
        
        print(f"  -> Result: Category='{category}', Flow='{flow_type}'")
        
        if flow_type == test['expected_flow']:
            print("  -> ✅ PASS")
        else:
            print(f"  -> ❌ FAIL (Expected {test['expected_flow']})")
            all_passed = False
        print("-" * 20)            
    if all_passed:
        print("\nAll systems operational. LLM logic is sound.")
    else:
        print("\nWARNING: LLM logic failed some tests. Adjust SYSTEM_PROMPT.")

if __name__ == "__main__":
    verify_categorization_logic()
