import random
import os
from datetime import datetime, timedelta
from mock_api.db_manager import DBManager, db_lock

def populate_db():
    random.seed(42)
    db = DBManager()
    print(f"DEBUG: db.db_path = {db.db_path}")

    accounts_to_insert = []
    transactions_to_insert = []

    # Create Angga's account (custom account)
    angga_account = {
        "account_id": "acc-angga-001",
        "owner": "Angga",
        "pockets": [
            {"name": "main pocket", "balance": 12500000.0},
            {"name": "saving pocket", "balance": 50000000.0}
        ]
    }
    accounts_to_insert.append(angga_account)

    # Generate transactions for Angga (120 transactions)
    base_time = datetime(2026, 4, 12, 10, 0, 0)
    descriptions_main = [
        "GoFood purchase", "Kopi Kenangan", "GrabRide", "Tokopedia checkout",
        "Netflix subscription", "Spotify family plan", "Indomaret payment",
        "Electricity bill", "Internet bill", "Lunch at Warteg", "Gym membership"
    ]
    descriptions_saving = [
        "Monthly interest deposit", "Auto-save transfer", "Investment dividend"
    ]
    
    for i in range(120):
        # 80% main pocket, 20% saving pocket
        is_main = random.random() < 0.8
        pocket_name = "main pocket" if is_main else "saving pocket"
        timestamp = (base_time + timedelta(hours=i * 12 + random.randint(-4, 4))).isoformat() + "Z"
        tx_id = f"tx-angga-{i:03d}"
        
        if is_main:
            if i % 60 == 0:  # monthly salary
                tx_type = "deposit"
                amount = 15000000.0
                desc = "Monthly Salary from PT Makmur Jaya"
            else:
                tx_type = "withdrawal" if random.random() < 0.7 else "transfer_out"
                amount = float(random.randint(20, 500) * 1000)
                desc = random.choice(descriptions_main)
        else:
            tx_type = "deposit" if random.random() < 0.7 else "withdrawal"
            amount = float(random.randint(50, 1000) * 1000)
            desc = random.choice(descriptions_saving)
            
        transactions_to_insert.append({
            "transaction_id": tx_id,
            "account_id": "acc-angga-001",
            "pocket": pocket_name,
            "type": tx_type,
            "amount": amount,
            "description": desc,
            "timestamp": timestamp
        })

    # Generate remaining 199 accounts (to make 200 total accounts)
    owners = [
        "Budi", "Siti", "Dewi", "Agus", "Rian", "Aditya", "Rini", "Eko", "Wawan", "Hendra",
        "Yanto", "Bambang", "Sri", "Ani", "Kartika", "Rudi", "Tono", "Andi", "Joko", "Megawati",
        "Susilo", "Prabowo", "Gibran", "Jokowi", "Anies", "Ganjar", "Luhut", "Mahfud", "Erick",
        "Retno", "Sri Mulyani", "Basuki", "Nadiem", "Sandiaga", "Tito", "Bahlil", "Zulkifli"
    ]
    last_names = ["Santoso", "Wijaya", "Kurniawan", "Prasetyo", "Siregar", "Hidayat", "Saputra", "Lubis", "Ginting", "Nasution"]
    
    generated_names = []
    for _ in range(199):
        first = random.choice(owners)
        last = random.choice(last_names)
        name = f"{first} {last}"
        while name in generated_names:
            first = random.choice(owners)
            last = random.choice(last_names)
            name = f"{first} {last}"
        generated_names.append(name)

    pocket_options = ["main pocket", "saving pocket", "travel pocket", "shopping pocket", "emergency pocket"]

    for idx in range(1, 200):
        acct_id = f"acc-{idx:03d}"
        owner_name = generated_names[idx - 1]
        
        # Determine pockets
        num_pockets = random.randint(1, 4)
        selected_pockets = random.sample(pocket_options, num_pockets)
        if "main pocket" not in selected_pockets:
            selected_pockets.append("main pocket")
        
        pockets = []
        for p_name in selected_pockets:
            pockets.append({
                "name": p_name,
                "balance": float(random.randint(100, 100000) * 1000)
            })
            
        accounts_to_insert.append({
            "account_id": acct_id,
            "owner": owner_name,
            "pockets": pockets
        })
        
        # Generate 100 to 150 transactions per account
        num_tx = random.randint(100, 150)
        for tx_idx in range(num_tx):
            p_name = random.choice([p["name"] for p in pockets])
            tx_type = "deposit" if random.random() < 0.3 else "withdrawal"
            amount = float(random.randint(10, 2000) * 1000)
            timestamp = (base_time + timedelta(hours=tx_idx * 10 + random.randint(-3, 3))).isoformat() + "Z"
            desc = random.choice(descriptions_main) if tx_type == "withdrawal" else "Pocket Transfer Deposit"
            
            transactions_to_insert.append({
                "transaction_id": f"tx-{idx:03d}-{tx_idx:03d}",
                "account_id": acct_id,
                "pocket": p_name,
                "type": tx_type,
                "amount": amount,
                "description": desc,
                "timestamp": timestamp
            })

    # Re-distribute/re-assign to ensure every pocket has at least one transaction
    for acc in accounts_to_insert:
        acc_id = acc["account_id"]
        # Find all transactions for this account
        acc_txs = [tx for tx in transactions_to_insert if tx["account_id"] == acc_id]
        # Group by pocket
        pockets_in_acc = [p["name"] for p in acc["pockets"]]
        txs_per_pocket = {p: [] for p in pockets_in_acc}
        for tx in acc_txs:
            if tx["pocket"] in txs_per_pocket:
                txs_per_pocket[tx["pocket"]].append(tx)
        
        # For any pocket with 0 transactions, reassign one transaction from the pocket with the most transactions
        for p_name in pockets_in_acc:
            if not txs_per_pocket[p_name]:
                most_tx_pocket = max(txs_per_pocket.keys(), key=lambda k: len(txs_per_pocket[k]))
                tx_to_move = txs_per_pocket[most_tx_pocket][-1]
                txs_per_pocket[most_tx_pocket].remove(tx_to_move)
                tx_to_move["pocket"] = p_name
                txs_per_pocket[p_name].append(tx_to_move)

    # Reconcile pocket balances with transaction histories
    from collections import defaultdict
    txs_by_pocket = defaultdict(list)
    for tx in transactions_to_insert:
        key = (tx["account_id"], tx["pocket"])
        txs_by_pocket[key].append(tx)

    # Map account_id to its pockets list for easy access to target balances
    account_pockets_map = {}
    for acc in accounts_to_insert:
        account_pockets_map[acc["account_id"]] = {p["name"]: p for p in acc["pockets"]}

    def reconcile_pocket(target_balance: float, txs: list[dict]):
        if not txs:
            return
        
        # Sort chronologically by timestamp
        txs.sort(key=lambda x: x.get("timestamp", ""))
        
        # 1. Ensure the first transaction is a deposit
        tx_0 = txs[0]
        if tx_0["type"] != "deposit":
            tx_0["type"] = "deposit"
            if "main pocket" in tx_0["pocket"]:
                tx_0["description"] = "Initial Deposit"
            else:
                tx_0["description"] = "Pocket Transfer Deposit"
        
        # 2. Try the simple approach (set A_0 = T - R, keep all other amounts unchanged)
        R = 0.0
        for tx in txs[1:]:
            amount = tx["amount"]
            if tx["type"] == "deposit":
                R += amount
            elif tx["type"] in ("withdrawal", "transfer_out"):
                R -= amount
                
        A_0_candidate = target_balance - R
        if A_0_candidate > 0:
            valid = True
            balance = A_0_candidate
            for tx in txs[1:]:
                amount = tx["amount"]
                if tx["type"] == "deposit":
                    balance += amount
                elif tx["type"] in ("withdrawal", "transfer_out"):
                    balance -= amount
                if balance <= 0:
                    valid = False
                    break
            if valid:
                tx_0["amount"] = A_0_candidate
                return

        # 3. Fallback: Backward-capping algorithm
        current_balance = target_balance
        adjusted_amounts = {}
        for i in range(len(txs) - 1, 0, -1):
            tx = txs[i]
            tx_type = tx["type"]
            amount = tx["amount"]
            
            if tx_type in ("withdrawal", "transfer_out"):
                adjusted_amounts[i] = amount
                current_balance += amount
            else:  # deposit
                max_allowed = current_balance - 1.0
                if max_allowed > 0:
                    amount = min(amount, max_allowed)
                else:
                    amount = current_balance * 0.1
                adjusted_amounts[i] = amount
                current_balance -= amount
                
        tx_0["amount"] = current_balance
        for i, amount in adjusted_amounts.items():
            txs[i]["amount"] = amount

    for (acc_id, pocket_name), pocket_txs in txs_by_pocket.items():
        acc_pockets = account_pockets_map.get(acc_id, {})
        pocket_obj = acc_pockets.get(pocket_name)
        if not pocket_obj:
            continue
        reconcile_pocket(pocket_obj["balance"], pocket_txs)

    # Bulk insert using a single TinyDB session to prevent file buffering race conditions
    print(f"DEBUG: Inserting {len(accounts_to_insert)} accounts and {len(transactions_to_insert)} transactions")
    with db.db_session() as session:
        session.table("accounts").truncate()
        session.table("transactions").truncate()
        session.table("accounts").insert_multiple(accounts_to_insert)
        session.table("transactions").insert_multiple(transactions_to_insert)
    print("DEBUG: Bulk insert finished")

if __name__ == "__main__":
    populate_db()
    print("Database populated successfully.")

