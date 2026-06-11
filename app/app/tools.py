import sys
import os
import requests
from typing import Optional, Any, Dict, List

# Add package directory to sys.path to allow importing packaged modules
sys.path.append(os.path.dirname(__file__))
from crawler.search import search as faq_search
from google.adk.agents.context import Context


def search_faq(query: str) -> Dict[str, Any]:
    """Performs a semantic search on the bank's FAQ database to retrieve relevant answers.

    Args:
        query: The search query.

    Returns:
        A dict containing status, query, and search results.
    """
    results = faq_search(query, k=3)
    return {
        "status": "success",
        "query": query,
        "results": results
    }


def set_user_identity(owner_name: str, tool_context: Context) -> Dict[str, Any]:
    """Stores the user's owner name in the session state to retrieve account details.

    Args:
        owner_name: The name of the account owner.

    Returns:
        A dict indicating the user identity was set.
    """
    tool_context.state["user_name"] = owner_name
    return {
        "status": "success",
        "message": f"User identity set to {owner_name}."
    }


class AccountNotFoundError(Exception):
    pass


def _get_auth_headers(url: str) -> dict:
    headers = {}
    if url.startswith("https://"):
        try:
            import google.auth
            import google.auth.transport.requests
            from google.oauth2 import id_token
            from urllib.parse import urlparse
            parsed = urlparse(url)
            audience = f"{parsed.scheme}://{parsed.netloc}"
            auth_req = google.auth.transport.requests.Request()
            token = id_token.fetch_id_token(auth_req, audience)
            headers["Authorization"] = f"Bearer {token}"
        except Exception:
            pass
    return headers


def _get_account_data(tool_context: Optional[Context]) -> Dict[str, Any]:
    """Helper function to fetch account data from the mock API."""
    owner_name = None
    if tool_context and tool_context.state:
        owner_name = tool_context.state.get("user_name")

    mock_api_url = os.environ.get("MOCK_API_URL", "http://127.0.0.1:8000")
    headers = _get_auth_headers(mock_api_url)
    if owner_name is not None and owner_name != "" and owner_name != "not set":
        try:
            r = requests.get(f"{mock_api_url}/accounts", params={"owner": owner_name}, headers=headers, timeout=5)
            r.raise_for_status()
            data = r.json()
            if data and isinstance(data, list):
                for acc in data:
                    if acc.get("owner", "").strip().lower() == owner_name.strip().lower():
                        return acc
            raise AccountNotFoundError(f"Account not found for owner '{owner_name}'.")
        except AccountNotFoundError:
            raise
        except Exception as e:
            raise AccountNotFoundError(f"Account not found for owner '{owner_name}'.") from e
    else:
        r = requests.get(f"{mock_api_url}/accounts/acc-angga-001", headers=headers, timeout=5)
        r.raise_for_status()
        return r.json()


def check_pocket_balance(pocket_name: str, tool_context: Context) -> Dict[str, Any]:
    """Retrieves the balance of the specified pocket in the user's account.

    Args:
        pocket_name: The name of the pocket to check the balance for.

    Returns:
        A dict containing the balance details or an error message if the pocket is not found.
    """
    try:
        account_data = _get_account_data(tool_context)
    except AccountNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }

    pockets = account_data.get("pockets", [])

    target_name = pocket_name.lower().strip()
    for p in pockets:
        if p["name"].lower().strip() == target_name:
            return {
                "status": "success",
                "account_id": account_data["account_id"],
                "owner": account_data["owner"],
                "pocket": p["name"],
                "balance": p["balance"]
            }

    pocket_names = [p["name"] for p in pockets]
    return {
        "status": "error",
        "message": f"Pocket '{pocket_name}' not found. Available pockets: {', '.join(pocket_names)}."
    }


def check_transactions(
    pocket_name: Optional[str] = None,
    limit: Optional[int] = 5,
    tool_context: Optional[Context] = None
) -> Dict[str, Any]:
    """Retrieves the transaction history for the user's account.

    Args:
        pocket_name: Optional pocket name to filter transactions.
        limit: Maximum number of transactions to return (default is 5).

    Returns:
        A dict containing the status and a list of transactions.
    """
    try:
        account_data = _get_account_data(tool_context)
    except AccountNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }

    account_id = account_data["account_id"]

    params = {}
    if limit is not None:
        params["limit"] = limit

    if pocket_name:
        pockets = account_data.get("pockets", [])
        target_pocket = None
        for p in pockets:
            if p["name"].lower().strip() == pocket_name.lower().strip():
                target_pocket = p["name"]
                break

        if target_pocket:
            params["pocket"] = target_pocket
        else:
            return {
                "status": "error",
                "message": f"Pocket '{pocket_name}' not found on this account."
            }

    mock_api_url = os.environ.get("MOCK_API_URL", "http://127.0.0.1:8000")
    headers = _get_auth_headers(mock_api_url)
    url = f"{mock_api_url}/accounts/{account_id}/transactions"
    r = requests.get(url, params=params, headers=headers, timeout=5)
    r.raise_for_status()

    return {
        "status": "success",
        "account_id": account_id,
        "owner": account_data["owner"],
        "transactions": r.json()
    }
