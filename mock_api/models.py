from pydantic import BaseModel, Field
from typing import List, Optional

class Pocket(BaseModel):
    name: str
    balance: float

class Account(BaseModel):
    account_id: str
    owner: str
    pockets: List[Pocket]

class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    pocket: str
    type: str  # e.g., "deposit", "withdrawal", "transfer_in", "transfer_out"
    amount: float
    description: str
    timestamp: str  # ISO-8601 format
