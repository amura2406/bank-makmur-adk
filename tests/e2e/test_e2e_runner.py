"""
Pytest execution module for E2E tests.
Loads tests from test_cases.json and parameterizes them.
"""

import os
import json
import pytest
import re
import asyncio
from tests.run_e2e import execute_turn

def load_test_cases():
    cases_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_cases.json")
    if not os.path.exists(cases_path):
        return []
    with open(cases_path, "r") as f:
        data = json.load(f)
    return data.get("test_cases", [])

async def execute_case(case):
    os.environ["CURRENT_E2E_CASE_ID"] = case["id"]
    # Clean case-specific local session file if it exists
    case_db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "app", "app", ".saved_chats", f"local_sessions_{case['id']}.json"
    )
    if os.path.exists(case_db_path):
        try:
            os.remove(case_db_path)
        except Exception:
            pass
            
    from tests.run_e2e import MOCK_MEMORY_BANK
    MOCK_MEMORY_BANK.clear()
    history = []
    mode = os.getenv("E2E_MODE", "mock")
    endpoint = os.getenv("E2E_ENDPOINT", "http://localhost:8000")
    
    for turn_idx, turn in enumerate(case["turns"]):
        user_input = turn["user_input"]
        
        response = await execute_turn(user_input, history, mode, endpoint)
            
        assertions = turn.get("assertions", {})
        
        # 1. Regex assertion
        if "regex" in assertions:
            pattern = re.compile(assertions["regex"], re.IGNORECASE)
            assert pattern.search(response["text"]), f"Response '{response['text']}' did not match pattern '{assertions['regex']}'"
            
        # 2. Expected tools assertion
        if "expected_tools" in assertions:
            for tool in assertions["expected_tools"]:
                assert tool in response.get("called_tools", []), f"Expected tool '{tool}' was not called"
                
        # 3. Forbidden words assertion
        if "forbidden_words" in assertions:
            for word in assertions["forbidden_words"]:
                assert word.lower() not in response["text"].lower(), f"Forbidden word '{word}' found in response"
                
        # Append turn to history
        history.append({"role": "user", "parts": [{"text": user_input}]})
        history.append({"role": "model", "parts": [{"text": response["text"]}]})

@pytest.mark.parametrize("case", load_test_cases(), ids=lambda c: c["id"])
def test_e2e_case(case):
    """Dynamically tests a test case turns."""
    asyncio.run(execute_case(case))
