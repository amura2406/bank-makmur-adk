import pytest
import asyncio
import gc
import weakref
import os
from mock_api.db_manager import DBManager
from tests.run_e2e import TaskLocalDict

@pytest.mark.anyio
async def test_nested_db_sessions_no_deadlock():
    """Verify that nested db_session contexts do not deadlock."""
    db_manager = DBManager()
    
    # 1. Outer session
    with db_manager.db_session() as db1:
        assert db1 is not None
        
        # 2. Call DBManager methods which use db_session internally (nested lookup)
        account = db_manager.get_account("acc-angga-001")
        assert account is not None
        assert account["owner"] == "Angga"
        
        # 3. Another level of nesting
        transactions = db_manager.get_transactions("acc-angga-001", limit=5)
        assert len(transactions) > 0
        
        # 4. Explicit nested session block
        with db_manager.db_session() as db2:
            assert db2 is not None
            accounts = db_manager.accounts_table.all()
            assert len(accounts) > 0
            
    print("Nested DB sessions test completed successfully without deadlocking.")

def test_cache_mutations_isolation():
    """Verify that database cache modifications in-place do not pollute the cache."""
    db_manager = DBManager()
    
    # Clear the DB manager's caching storage cache to start fresh
    from mock_api.db_manager import CachingJSONStorage
    CachingJSONStorage._cache.clear()
    
    # 1. Fetch account (should populate cache)
    account1 = db_manager.get_account("acc-angga-001")
    assert account1 is not None
    original_owner = account1["owner"]
    original_pocket_count = len(account1["pockets"])
    
    # 2. Modify returned dict in-place
    account1["owner"] = "MUTATED_OWNER_NAME"
    account1["pockets"].append({"name": "fake pocket", "balance": 999999.0})
    
    # 3. Fetch account again (should hit cache)
    account2 = db_manager.get_account("acc-angga-001")
    assert account2 is not None
    
    # Verify that the cache was NOT polluted by the mutations
    assert account2["owner"] == original_owner, "Cache polluted: owner name was modified in cache!"
    assert len(account2["pockets"]) == original_pocket_count, "Cache polluted: pockets were appended in cache!"
    
    # 4. Test table all() lookup mutations
    accounts_list1 = db_manager.accounts_table.all()
    assert len(accounts_list1) > 0
    accounts_list1[0]["owner"] = "MUTATED_LIST_OWNER"
    
    accounts_list2 = db_manager.accounts_table.all()
    assert accounts_list2[0]["owner"] != "MUTATED_LIST_OWNER", "Cache polluted via table.all() list mutation!"
    
    print("Cache mutation isolation test completed successfully.")

@pytest.mark.anyio
async def test_task_local_dict_no_reference_cycle():
    """Verify that memory reference cycles on TaskLocalDict are broken and tasks are garbage collected immediately."""
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        local_dict = TaskLocalDict()
        
        async def dummy_task_func():
            # Set some value in the TaskLocalDict to register the task
            local_dict["key"] = "value"
            assert local_dict["key"] == "value"
        
        # Create and run the task
        task = asyncio.create_task(dummy_task_func())
        task_ref = weakref.ref(task)
        
        await task
        
        # Verify the task has completed
        assert task.done()
        
        # Remove the strong reference to the task
        del task
        
        # Allow the event loop to retire the task scheduling references
        await asyncio.sleep(0.1)
        
        # Check if the weakref has cleared (meaning the task object was garbage collected via reference counting)
        # Without weakref.ref in TaskLocalDict, this assert would fail since cyclic garbage collection is disabled.
        assert task_ref() is None, "Memory leak: Task object is still alive, reference cycle not broken!"
        
    finally:
        if gc_was_enabled:
            gc.enable()
            
    print("TaskLocalDict reference cycle breaking test completed successfully.")
