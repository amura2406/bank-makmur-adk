import pytest
from app.agent import root_agent

@pytest.fixture(autouse=True)
def clear_cached_api_clients():
    """Clear cached GenAI API clients from root_agent model dict to avoid closed event loop errors."""
    for key in ["api_client", "_live_api_client", "_api_backend", "_base_url_and_api_version", "_live_api_version"]:
        if key in root_agent.model.__dict__:
            try:
                del root_agent.model.__dict__[key]
            except KeyError:
                pass
