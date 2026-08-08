#!/usr/bin/env python3
"""Test bulk delete removes all mirrors."""
import os
import uuid
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

def create_test_doc(name: str) -> dict:
    pid = str(uuid.uuid4())
    return {
        "id": pid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ontology_version": "1.0.0-seed",
        "artifacts": {"originals": [], "extraction": "n/a", "pipeline": "n/a"},
        "pipeline": {"questao": {"tema": name}},
        "tema": name,
        "disciplina": "TEST",
    }

async def insert_to_mongo(doc: dict):
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.insert_one(doc)
    cli.close()

async def cleanup_mongo(ids: list):
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.delete_many({"id": {"$in": ids}})
    cli.close()

print("Testing bulk_delete removes all mirrors...")

# Create 3 test documents
docs = [create_test_doc(f"BulkTest_{i}") for i in range(3)]
ids = [d["id"] for d in docs]

try:
    # Insert to MongoDB
    for doc in docs:
        asyncio.run(insert_to_mongo(doc))
    print(f"✓ Inserted {len(docs)} documents to MongoDB")
    
    # Sync to Firestore
    r = requests.post(f"{API}/firestore/sync-all", timeout=30)
    assert r.status_code == 200
    print(f"✓ Synced to Firestore")
    
    # Verify all mirrors exist
    for doc_id in ids:
        r = requests.get(f"{API}/firestore/document/{doc_id}", timeout=30)
        assert r.status_code == 200, f"Mirror {doc_id} not found"
    print(f"✓ All {len(ids)} mirrors exist in Firestore")
    
    # Bulk delete
    r = requests.post(f"{API}/pipelines/bulk_delete", json={"ids": ids}, timeout=30)
    assert r.status_code == 200, f"Bulk delete failed: {r.text}"
    result = r.json()
    assert result["deleted"] == len(ids), f"Expected {len(ids)} deleted, got {result['deleted']}"
    print(f"✓ Bulk delete removed {result['deleted']} documents")
    
    # Verify all mirrors removed
    for doc_id in ids:
        r = requests.get(f"{API}/firestore/document/{doc_id}", timeout=30)
        assert r.status_code == 404, f"Mirror {doc_id} still exists!"
    print(f"✓ All {len(ids)} mirrors removed from Firestore")
    
    print("\n✅ BULK DELETE TEST PASSED")
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
finally:
    asyncio.run(cleanup_mongo(ids))
    requests.post(f"{API}/firestore/sync-all", timeout=30)
    print("✓ Cleanup complete")
