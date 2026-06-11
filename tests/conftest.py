import os
import sys
import time
import subprocess
import pytest
from mock_api.populate import populate_db

@pytest.fixture(scope="session", autouse=True)
def run_mock_api():
    mode = os.getenv("E2E_MODE", "mock")
    # Clean local session DB file if exists to prevent session leakage from prior runs
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "app", ".saved_chats", "local_sessions.json")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
    # Populate mock DB before starting
    populate_db()
    
    server_process = None
    if mode == "api":
        print("\n[conftest] Starting mock API server in background...")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "mock_api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Wait for uvicorn to startup
        time.sleep(1.5)
        
    yield
    
    if server_process:
        print("\n[conftest] Stopping mock API server...")
        server_process.terminate()
        server_process.wait()
