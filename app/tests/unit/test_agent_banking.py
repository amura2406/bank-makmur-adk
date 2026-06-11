import pytest
from unittest.mock import patch, MagicMock
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.genai import types

from app.agent import before_agent_callback
from app.tools import (
    set_user_identity,
    check_pocket_balance,
    check_transactions,
    search_faq
)

class MockContent:
    def __init__(self, role, text):
        self.role = role
        self.parts = [MagicMock(text=text)]

class MockEvent:
    def __init__(self, author, role, text):
        self.author = author
        self.content = MockContent(role, text)

@pytest.mark.asyncio
async def test_before_agent_callback_language_detection_english():
    # Setup mock callback context with an English query
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.state = {}
    
    event = MockEvent("user", "user", "Hello, how can I check my pocket balance today?")
    callback_context.session = MagicMock()
    callback_context.session.events = [event]
    
    await before_agent_callback(callback_context)
    
    assert callback_context.state["preferred_language"] == "en"
    assert callback_context.state["user_name"] == "not set"

@pytest.mark.asyncio
async def test_before_agent_callback_language_detection_indonesian():
    # Setup mock callback context with an Indonesian query
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.state = {}
    
    event = MockEvent("user", "user", "Halo, tolong tampilkan mutasi tabungan saya.")
    callback_context.session = MagicMock()
    callback_context.session.events = [event]
    
    await before_agent_callback(callback_context)
    
    assert callback_context.state["preferred_language"] == "id"

@pytest.mark.asyncio
async def test_before_agent_callback_name_extraction_english():
    # English introduction
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.state = {}
    
    event = MockEvent("user", "user", "My name is Angga")
    callback_context.session = MagicMock()
    callback_context.session.events = [event]
    
    await before_agent_callback(callback_context)
    
    assert callback_context.state["user_name"] == "Angga"

@pytest.mark.asyncio
async def test_before_agent_callback_name_extraction_indonesian():
    # Indonesian introduction
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.state = {}
    
    event = MockEvent("user", "user", "Nama saya Budi.")
    callback_context.session = MagicMock()
    callback_context.session.events = [event]
    
    await before_agent_callback(callback_context)
    
    assert callback_context.state["user_name"] == "Budi"

def test_set_user_identity():
    context = MagicMock(spec=Context)
    context.state = {}
    res = set_user_identity("Agus", context)
    assert res["status"] == "success"
    assert context.state["user_name"] == "Agus"

@patch("requests.get")
def test_check_pocket_balance_success(mock_get):
    # Mock API response for account search
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{
        "account_id": "acc-angga-001",
        "owner": "angga",
        "pockets": [
            {"name": "Utama", "balance": 500000},
            {"name": "Tabungan", "balance": 1500000}
        ]
    }]
    mock_get.return_value = mock_response
    
    context = MagicMock(spec=Context)
    context.state = {"user_name": "angga"}
    
    res = check_pocket_balance("Utama", context)
    assert res["status"] == "success"
    assert res["pocket"] == "Utama"
    assert res["balance"] == 500000

@patch("requests.get")
def test_check_pocket_balance_not_found(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{
        "account_id": "acc-angga-001",
        "owner": "angga",
        "pockets": [
            {"name": "Utama", "balance": 500000}
        ]
    }]
    mock_get.return_value = mock_response
    
    context = MagicMock(spec=Context)
    context.state = {"user_name": "angga"}
    
    res = check_pocket_balance("Investasi", context)
    assert res["status"] == "error"
    assert "Investasi" in res["message"]

@patch("requests.get")
def test_check_transactions_success(mock_get):
    # First get accounts, then transactions
    mock_acc_resp = MagicMock()
    mock_acc_resp.status_code = 200
    mock_acc_resp.json.return_value = [{
        "account_id": "acc-angga-001",
        "owner": "angga",
        "pockets": [
            {"name": "Utama", "balance": 500000}
        ]
    }]
    
    mock_tx_resp = MagicMock()
    mock_tx_resp.status_code = 200
    mock_tx_resp.json.return_value = [
        {"id": "tx-01", "pocket": "Utama", "amount": -5000, "description": "Transfer to Budi"}
    ]
    
    # Configure mock_get to return account first, then transactions
    mock_get.side_effect = [mock_acc_resp, mock_tx_resp]
    
    context = MagicMock(spec=Context)
    context.state = {"user_name": "angga"}
    
    res = check_transactions(pocket_name="Utama", limit=5, tool_context=context)
    assert res["status"] == "success"
    assert res["owner"] == "angga"
    assert len(res["transactions"]) == 1

@patch("app.tools.faq_search")
def test_search_faq(mock_faq_search):
    mock_faq_search.return_value = ["Bank Makmur is open Mon-Fri 8am-3pm."]
    res = search_faq("what are the working hours")
    assert res["status"] == "success"
    assert res["query"] == "what are the working hours"
    assert res["results"] == ["Bank Makmur is open Mon-Fri 8am-3pm."]
