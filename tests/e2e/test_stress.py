import pytest
import asyncio
import os
import httpx
import json
from unittest.mock import patch, MagicMock, mock_open
from tests.run_e2e import execute_turn, MOCK_MEMORY_BANK
from tests.e2e.test_e2e_runner import execute_case

@pytest.mark.anyio
async def test_concurrent_multisession_leak():
    """
    Stress test to check if concurrent multi-session executions leak long-term state.
    We run two simulated user sessions concurrently:
      - Session A1: sets name to 'Alice'
      - Session B1: sets name to 'Bob'
      - Session A2 (empty history): queries name, expecting 'Alice'
      - Session B2 (empty history): queries name, expecting 'Bob'
    """
    mode = os.getenv("E2E_MODE", "mock")
    if mode != "mock":
        pytest.skip("This stress test targets the mock agent runner state safety")

    MOCK_MEMORY_BANK.clear()

    async def run_session_alice():
        # Session A1
        res1 = await execute_turn("My name is Alice", [], mode, "")
        assert "alice" in res1["text"].lower()
        
        # Artificial delay to let Session B1 run
        await asyncio.sleep(0.5)
        
        # Session A2 (new session, empty history)
        res2 = await execute_turn("What is my name?", [], mode, "")
        return res2["text"]

    async def run_session_bob():
        # Let Session A1 start first
        await asyncio.sleep(0.1)
        
        # Session B1
        res1 = await execute_turn("My name is Bob", [], mode, "")
        assert "bob" in res1["text"].lower()
        
        # Session B2 (new session, empty history)
        res2 = await execute_turn("What is my name?", [], mode, "")
        return res2["text"]

    # Run concurrently
    alice_name_resp, bob_name_resp = await asyncio.gather(
        run_session_alice(),
        run_session_bob()
    )

    print(f"Alice session got name response: {alice_name_resp}")
    print(f"Bob session got name response: {bob_name_resp}")

    # If it is thread/async safe, Alice should get 'Alice' and Bob should get 'Bob'
    assert "alice" in alice_name_resp.lower(), f"State leaked! Alice session got: '{alice_name_resp}'"
    assert "bob" in bob_name_resp.lower(), f"State leaked! Bob session got: '{bob_name_resp}'"


@pytest.mark.anyio
async def test_api_mode_connection_error():
    """
    Verify that in 'api' mode, connection errors are not handled by the runner
    and propagate directly, crashing the test execution.
    """
    # Use a port that is highly likely to be inactive (e.g. 9999)
    endpoint = "http://127.0.0.1:9999"
    
    with pytest.raises((httpx.ConnectError, httpx.HTTPError)):
        await execute_turn("Hello", [], "api", endpoint)


@pytest.mark.anyio
async def test_api_mode_invalid_json_response():
    """
    Verify that in 'api' mode, if the server returns non-JSON or distorted JSON,
    the runner fails to parse it and raises JSONDecodeError, crashing the run.
    """
    # Mock httpx AsyncClient.post to return a response with invalid JSON
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(side_effect=json.JSONDecodeError("Expecting value", "", 0))

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(json.JSONDecodeError):
            await execute_turn("Hello", [], "api", "http://127.0.0.1:8000")


@pytest.mark.anyio
async def test_local_mode_json_robustness():
    """
    Verify that in 'local' mode, the runner handles distorted JSON by falling back
    to the raw stdout string.
    """
    class MockProcess:
        stdout = "This is a non-JSON output string from agent"
        stderr = ""
        returncode = 0

    with patch("subprocess.run", return_value=MockProcess()):
        res = await execute_turn("Hello", [], "local", "")
        # It should catch JSONDecodeError and return the raw output as text
        assert res["text"] == "This is a non-JSON output string from agent"
        assert res["called_tools"] == []


def test_invalid_json_in_test_cases():
    """
    Verify that if the test cases file is not valid JSON, loading it raises a JSONDecodeError.
    """
    from tests.e2e.test_e2e_runner import load_test_cases
    # Use a mock patch to simulate invalid JSON in test_cases.json
    with patch("builtins.open", mock_open(read_data="invalid json { data }")):
        with pytest.raises(json.JSONDecodeError):
            load_test_cases()


@pytest.mark.anyio
async def test_missing_keys_in_test_case_execution():
    """
    Verify that if a test case has missing keys (e.g. no 'turns'), execute_case raises KeyError.
    """
    bad_case = {
        "id": "TC_BAD_1"
        # 'turns' is missing
    }
    with pytest.raises(KeyError):
        await execute_case(bad_case)


@pytest.mark.anyio
async def test_missing_user_input_in_turn_execution():
    """
    Verify that if a turn lacks the 'user_input' key, execute_case raises KeyError.
    """
    bad_case = {
        "id": "TC_BAD_2",
        "turns": [
            {
                # 'user_input' is missing
                "assertions": {"regex": "hello"}
            }
        ]
    }
    with pytest.raises(KeyError):
        await execute_case(bad_case)
