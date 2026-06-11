import os
import contextlib
import fcntl
import json
import copy
import contextvars
from typing import Optional
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage

_db_lock_depth = contextvars.ContextVar("db_lock_depth", default=0)

DB_PATH = os.path.join(os.path.dirname(__file__), "db.json")

class CachingJSONStorage(JSONStorage):
    # Process-level cache mapping: path -> (mtime, size, parsed_dict)
    _cache = {}

    def __init__(self, path: str, *args, **kwargs):
        self.path = path
        super().__init__(path, *args, **kwargs)

    def read(self):
        try:
            stat = os.stat(self.path)
            mtime = stat.st_mtime
            size = stat.st_size
        except FileNotFoundError:
            return None
        
        if not size:
            return None

        cached = CachingJSONStorage._cache.get(self.path)
        if cached and cached[0] == mtime and cached[1] == size:
            return copy.deepcopy(cached[2])

        data = super().read()
        CachingJSONStorage._cache[self.path] = (mtime, size, copy.deepcopy(data))
        return copy.deepcopy(data)

    def write(self, data):
        super().write(data)
        try:
            stat = os.stat(self.path)
            CachingJSONStorage._cache[self.path] = (stat.st_mtime, stat.st_size, copy.deepcopy(data))
        except FileNotFoundError:
            pass

@contextlib.contextmanager
def db_lock(db_path: str):
    lock_path = db_path + ".lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "a+") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except IOError:
                pass

class TableProxy:
    def __init__(self, db_manager: "DBManager", table_name: str):
        self.db_manager = db_manager
        self.table_name = table_name

    def all(self) -> list[dict]:
        with self.db_manager.db_session() as db:
            data = db._storage.read() or {}
            res = data.get(self.table_name, {}).values()
            return [dict(r) for r in res]

class DBManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    @contextlib.contextmanager
    def db_session(self):
        depth = _db_lock_depth.get()
        if depth > 0:
            _db_lock_depth.set(depth + 1)
            db = TinyDB(self.db_path, storage=CachingJSONStorage)
            try:
                yield db
            finally:
                db.close()
                _db_lock_depth.set(_db_lock_depth.get() - 1)
        else:
            lock_path = self.db_path + ".lock"
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            with open(lock_path, "a+") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                _db_lock_depth.set(1)
                
                # Check file size on disk before loading
                if os.path.exists(self.db_path):
                    sz = os.path.getsize(self.db_path)
                    if sz == 0:
                        print(f"WARNING: db.json size is 0 before opening TinyDB! lock_file: {lock_file}")
                else:
                    print(f"WARNING: db.json does not exist before opening TinyDB!")
                    
                db = TinyDB(self.db_path, storage=CachingJSONStorage)
                try:
                    yield db
                finally:
                    try:
                        if hasattr(db, '_storage') and hasattr(db._storage, '_handle'):
                            handle = db._storage._handle
                            if handle and not handle.closed:
                                handle.flush()
                                import os as os_mod
                                os_mod.fsync(handle.fileno())
                    except Exception as e:
                        print(f"Error syncing DB file: {e}")
                    db.close()
                    try:
                        fcntl.flock(lock_file, fcntl.LOCK_UN)
                    except IOError:
                        pass
                    _db_lock_depth.set(0)

    @property
    def accounts_table(self):
        return TableProxy(self, "accounts")

    @property
    def transactions_table(self):
        return TableProxy(self, "transactions")

    def get_account(self, account_id: str) -> Optional[dict]:
        with self.db_session() as db:
            data = db._storage.read() or {}
            for doc in data.get("accounts", {}).values():
                if doc.get("account_id") == account_id:
                    return dict(doc)
            return None

    def find_accounts_by_owner(self, owner_name: str) -> list[dict]:
        with self.db_session() as db:
            data = db._storage.read() or {}
            results = []
            for doc in data.get("accounts", {}).values():
                owner = doc.get("owner", "")
                if owner_name.lower() in owner.lower():
                    results.append(dict(doc))
            return results

    def get_transactions(self, account_id: str, pocket: str = None, limit: int = None, offset: int = None) -> list[dict]:
        with self.db_session() as db:
            data = db._storage.read() or {}
            results = []
            for doc in data.get("transactions", {}).values():
                if doc.get("account_id") == account_id:
                    if pocket and doc.get("pocket") != pocket:
                        continue
                    results.append(dict(doc))
            if results:
                results = sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
                if offset is not None:
                    results = results[offset:]
                if limit is not None:
                    results = results[:limit]
                return results
            return []

    def insert_account(self, account_data: dict):
        with self.db_session() as db:
            accounts_table = db.table("accounts")
            accounts_table.insert(account_data)

    def insert_accounts_bulk(self, accounts_data: list[dict]):
        with self.db_session() as db:
            accounts_table = db.table("accounts")
            accounts_table.insert_multiple(accounts_data)

    def insert_transaction(self, tx_data: dict):
        with self.db_session() as db:
            transactions_table = db.table("transactions")
            transactions_table.insert(tx_data)

    def insert_transactions_bulk(self, txs_data: list[dict]):
        with self.db_session() as db:
            transactions_table = db.table("transactions")
            transactions_table.insert_multiple(txs_data)

    def clear_db(self):
        with self.db_session() as db:
            db.table("accounts").truncate()
            db.table("transactions").truncate()
