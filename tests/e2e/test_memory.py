import pytest
import asyncio
import os
from tests.run_e2e import execute_turn, MOCK_MEMORY_BANK

@pytest.mark.anyio
async def test_in_session_memory():
    """Verify that name memory is preserved within the same conversation session."""
    history = []
    mode = os.getenv("E2E_MODE", "mock")
    endpoint = os.getenv("E2E_ENDPOINT", "http://localhost:8000")
    
    # Reset mock memory first
    if mode == "mock":
        MOCK_MEMORY_BANK.clear()
        
    # Turn 1: Introduce name
    user_input_1 = "My name is Angga"
    response_1 = await execute_turn(user_input_1, history, mode, endpoint)
    assert response_1["text"] is not None
    
    # Append to history
    history.append({"role": "user", "parts": [{"text": user_input_1}]})
    history.append({"role": "model", "parts": [{"text": response_1["text"]}]})
    
    # Turn 2: Ask what my name is
    user_input_2 = "What is my name?"
    response_2 = await execute_turn(user_input_2, history, mode, endpoint)
    assert "angga" in response_2["text"].lower()

@pytest.mark.anyio
async def test_multi_session_memory():
    """Verify that name memory persists across different conversation sessions (long-term memory)."""
    mode = os.getenv("E2E_MODE", "mock")
    endpoint = os.getenv("E2E_ENDPOINT", "http://localhost:8000")
    
    # Reset mock memory
    if mode == "mock":
        MOCK_MEMORY_BANK.clear()
        
    # Session 1: Set name
    history_1 = []
    await execute_turn("My name is Joko", history_1, mode, endpoint)
    
    # Session 2: Start new session with empty history
    history_2 = []
    response = await execute_turn("What is my name?", history_2, mode, endpoint)
    assert "joko" in response["text"].lower()

@pytest.mark.anyio
async def test_clear_memory():
    """Verify that resetting memory removes the stored name."""
    mode = os.getenv("E2E_MODE", "mock")
    endpoint = os.getenv("E2E_ENDPOINT", "http://localhost:8000")
    
    # Reset mock memory and set a name
    if mode == "mock":
        MOCK_MEMORY_BANK.clear()
        MOCK_MEMORY_BANK["user_name"] = "Susi"
        
    # Programmatic or simulator memory reset
    if mode == "mock":
        MOCK_MEMORY_BANK.clear()
        
    # Query after reset
    history = []
    response = await execute_turn("What is my name?", history, mode, endpoint)
    assert "susi" not in response["text"].lower()
