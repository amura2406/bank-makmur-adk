import os
import re
import pytest
from fastapi.testclient import TestClient
from mock_api.main import app
from mock_api.db_manager import DBManager
from mock_api.populate import populate_db
from crawler.refactor import refactor_text, refactor_faq
from crawler.ingest import ingest_data
from crawler.search import FAQSearchSingleton, get_search_helper
from langchain_core.embeddings import Embeddings

client = TestClient(app)

class MockEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[0.1] * 768 for _ in texts]
    def embed_query(self, text):
        return [0.1] * 768
    def __call__(self, text):
        return self.embed_query(text)

def test_branding_refactor():
    # Test Bank Jago -> Bank Makmur
    assert refactor_text("Selamat datang di Bank Jago.") == "Selamat datang di Bank Makmur."
    # Test Jago -> Makmur
    assert refactor_text("Kami adalah Jago.") == "Kami adalah Makmur."
    # Test JagoID -> MakmurID
    assert refactor_text("Gunakan JagoID Anda.") == "Gunakan MakmurID Anda."
    # Test lowercase jago is NOT replaced
    assert refactor_text("Saya jago mengelola uang.") == "Saya jago mengelola uang."
    # Test mix
    assert refactor_text("Bank Jago membantu Anda agar jago mengelola.") == "Bank Makmur membantu Anda agar jago mengelola."
    # Test word boundary does not replace parts of other words
    assert refactor_text("Penjaga gawang itu hebat.") == "Penjaga gawang itu hebat."
    # Test competitor domain / email
    assert refactor_text("tanya@jago.com") == "tanya@makmur.com"

def test_database_population():
    # Populate the database
    populate_db()
    
    db = DBManager()
    
    # Verify exactly 200 accounts exist
    accounts = db.accounts_table.all()
    assert len(accounts) == 200
    
    # Verify Angga's account details
    angga_acct = db.get_account("acc-angga-001")
    assert angga_acct is not None
    assert angga_acct["owner"] == "Angga"
    pockets = {p["name"]: p["balance"] for p in angga_acct["pockets"]}
    assert "main pocket" in pockets
    assert "saving pocket" in pockets
    assert pockets["main pocket"] == 12500000.0
    assert pockets["saving pocket"] == 50000000.0
    
    # Verify transaction count for Angga is 120
    angga_txs = db.get_transactions("acc-angga-001")
    assert len(angga_txs) == 120
    
    # Verify other accounts have 100-150 transactions
    for idx in range(1, 200):
        acct_id = f"acc-{idx:03d}"
        acct = db.get_account(acct_id)
        assert acct is not None, f"Account {acct_id} is missing"
        txs = db.get_transactions(acct_id)
        assert 100 <= len(txs) <= 150, f"Account {acct_id} has {len(txs)} transactions"

def test_fastapi_routes():
    # Enforce population first
    populate_db()
    
    # Test GET /accounts/{account_id} with valid ID
    response = client.get("/accounts/acc-angga-001")
    assert response.status_code == 200
    data = response.json()
    assert data["owner"] == "Angga"
    
    # Test GET /accounts/{account_id} with invalid format
    response = client.get("/accounts/ab")
    assert response.status_code == 400
    
    response = client.get("/accounts/acc-angga-001-with-an-extremely-long-id-that-exceeds-fifty-characters")
    assert response.status_code == 400
    
    response = client.get("/accounts/acc*angga")
    assert response.status_code == 400
    
    # Test GET /accounts/{account_id} with non-existent but valid format ID
    response = client.get("/accounts/acc-notexist-999")
    assert response.status_code == 404
    
    # Test GET /accounts/{account_id}/transactions
    response = client.get("/accounts/acc-angga-001/transactions")
    assert response.status_code == 200
    txs = response.json()
    assert len(txs) == 120
    
    # Test transactions filtering by pocket
    response = client.get("/accounts/acc-angga-001/transactions?pocket=saving pocket")
    assert response.status_code == 200
    saving_txs = response.json()
    assert len(saving_txs) < 120
    assert all(tx["pocket"] == "saving pocket" for tx in saving_txs)
    
    # Test limit and offset on transactions
    response = client.get("/accounts/acc-angga-001/transactions?limit=10&offset=5")
    assert response.status_code == 200
    limited_txs = response.json()
    assert len(limited_txs) == 10
    
    all_txs = client.get("/accounts/acc-angga-001/transactions").json()
    assert limited_txs[0]["transaction_id"] == all_txs[5]["transaction_id"]
    
    # Test GET /accounts?owner={owner_name} case-insensitive substring
    response = client.get("/accounts?owner=angga")
    assert response.status_code == 200
    matches = response.json()
    assert len(matches) == 1
    assert matches[0]["owner"] == "Angga"
    
    response = client.get("/accounts?owner=ANgGa")
    assert response.status_code == 200
    matches = response.json()
    assert len(matches) == 1
    assert matches[0]["owner"] == "Angga"
    
    response = client.get("/accounts?owner=ud")
    assert response.status_code == 200
    matches = response.json()
    assert len(matches) > 0

    # Test GET /accounts?owner={owner_name} with empty owner name (fails min_length=1)
    response = client.get("/accounts?owner=")
    assert response.status_code == 422

    # Test GET /accounts?owner={owner_name} with owner name > 100 characters (fails max_length=100)
    response = client.get("/accounts?owner=" + "a" * 101)
    assert response.status_code == 422

def test_faiss_search(tmp_path):
    temp_index_dir = str(tmp_path / "faiss_index_test")
    
    import crawler.ingest
    import crawler.search
    
    original_index_dir_ingest = crawler.ingest.INDEX_DIR
    original_index_dir_search = crawler.search.INDEX_DIR
    
    crawler.ingest.INDEX_DIR = temp_index_dir
    crawler.search.INDEX_DIR = temp_index_dir
    
    try:
        mock_embeddings = MockEmbeddings()
        crawler.ingest.ingest_data(embeddings_model=mock_embeddings)
        
        search_helper = get_search_helper(embeddings_model=mock_embeddings, index_dir=temp_index_dir)
        search_helper.db = None
        search_helper.index_dir = temp_index_dir
        search_helper.embeddings_model = mock_embeddings
        
        results = search_helper.search("Apa itu Bank Makmur?", k=2)
        assert len(results) == 2
        
        for res in results:
            assert "Bank Jago" not in res
            assert "JagoID" not in res
            assert "Bank Makmur" in res or "Makmur" in res or "Kantong Makmur" in res or "jago" in res.lower()
            
    finally:
        crawler.ingest.INDEX_DIR = original_index_dir_ingest
        crawler.search.INDEX_DIR = original_index_dir_search
