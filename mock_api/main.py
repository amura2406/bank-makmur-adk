import re
from typing import Optional, List
from fastapi import FastAPI, Path, Query, HTTPException
from mock_api.models import Account, Transaction
from mock_api.db_manager import DBManager

app = FastAPI(title="Mock Banking API")
db_manager = DBManager()

@app.get("/accounts/{account_id}", response_model=Account)
async def get_account(
    account_id: str = Path(...)
):
    # Enforce regex check: ^[a-zA-Z0-9_-]{3,50}$
    if not re.match(r"^[a-zA-Z0-9_-]{3,50}$", account_id):
        raise HTTPException(status_code=400, detail="Invalid account ID format. Must match ^[a-zA-Z0-9_-]{3,50}$")
    
    account = db_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@app.get("/accounts/{account_id}/transactions", response_model=List[Transaction])
async def get_transactions(
    account_id: str = Path(...),
    pocket: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(None, ge=0)
):
    # Enforce regex check: ^[a-zA-Z0-9_-]{3,50}$
    if not re.match(r"^[a-zA-Z0-9_-]{3,50}$", account_id):
        raise HTTPException(status_code=400, detail="Invalid account ID format. Must match ^[a-zA-Z0-9_-]{3,50}$")
    
    account = db_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    transactions = db_manager.get_transactions(account_id, pocket=pocket, limit=limit, offset=offset)
    return transactions

@app.get("/accounts", response_model=List[Account])
async def find_accounts_by_owner(
    owner: str = Query(..., min_length=1, max_length=100)
):
    accounts = db_manager.find_accounts_by_owner(owner)
    return accounts

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    # Bind to 0.0.0.0 for Cloud Run compatibility
    uvicorn.run(app, host="0.0.0.0", port=port)
