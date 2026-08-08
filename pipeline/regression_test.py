#!/usr/bin/env python3
"""Regression test: Verify CRUD endpoints still sync to Firestore correctly."""
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


def _seed_doc(name: str) -> dict:
    """Create a test document."""
    pid = str(uuid.uuid4())
    return {
        "id": pid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ontology_version": "1.0.0-seed",
        "artifacts": {
            "originals": [
                {
                    "filename": f"TEST_{name}.pdf",
                    "path": "n/a",
                    "content_type": "application/pdf",
                    "size": 1,
                }
            ],
            "extraction": "n/a",
            "pipeline": "n/a",
        },
        "pipeline": {
            "questao": {
                "disciplina": "REGRESSION_TEST",
                "tema": name,
                "resposta_correta": "B",
                "enunciado": f"Enunciado regression {name}",
            },
            "classificacao": {
                "dominios": ["DOM-REG"],
                "competencias": ["C-REG"],
                "processos_cognitivos": [{"id": "P-REG", "label": "testar"}],
            },
        },
        "disciplina": "REGRESSION_TEST",
        "tema": name,
        "banca": "REGRESSION",
        "ano": "2026",
        "resposta_correta": "B",
        "processos": ["P-REG"],
        "competencias": ["C-REG"],
        "dominios": ["DOM-REG"],
    }


async def insert_doc(doc: dict) -> None:
    """Insert document into MongoDB."""
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.insert_one(doc)
    cli.close()


async def delete_doc(doc_id: str) -> None:
    """Delete document from MongoDB."""
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.delete_one({"id": doc_id})
    cli.close()


def main():
    print("=" * 80)
    print("REGRESSION TEST: CRUD ENDPOINTS STILL SYNC TO FIRESTORE")
    print("=" * 80)
    
    # Test 1: DELETE /api/pipeline/{id} removes from Firestore
    print("\n[TEST 1] DELETE /api/pipeline/{id} removes from Firestore")
    print("-" * 80)
    
    doc1 = _seed_doc("delete_test")
    doc1_id = doc1["id"]
    print(f"Creating test document: {doc1_id}")
    
    asyncio.run(insert_doc(doc1))
    
    # Sync to Firestore
    print("Syncing to Firestore...")
    r = requests.post(f"{API}/firestore/sync-all", timeout=30)
    assert r.status_code == 200
    
    # Verify it exists in Firestore
    r = requests.get(f"{API}/firestore/document/{doc1_id}", timeout=30)
    assert r.status_code == 200, f"Document should exist in Firestore before delete"
    print(f"✓ Document exists in Firestore")
    
    # Delete via API
    print(f"Deleting via DELETE /api/pipeline/{doc1_id}...")
    r = requests.delete(f"{API}/pipeline/{doc1_id}", timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    print(f"✓ DELETE returned 200")
    
    # Verify it's removed from Firestore
    r = requests.get(f"{API}/firestore/document/{doc1_id}", timeout=30)
    assert r.status_code == 404, f"Document should be removed from Firestore after delete, got {r.status_code}"
    print(f"✓ Document removed from Firestore")
    
    # Test 2: POST /api/pipelines/bulk_delete removes mirrors
    print("\n[TEST 2] POST /api/pipelines/bulk_delete removes mirrors")
    print("-" * 80)
    
    docs = [_seed_doc("bulk_del_1"), _seed_doc("bulk_del_2")]
    doc_ids = [d["id"] for d in docs]
    print(f"Creating 2 test documents: {doc_ids}")
    
    for doc in docs:
        asyncio.run(insert_doc(doc))
    
    # Sync to Firestore
    print("Syncing to Firestore...")
    r = requests.post(f"{API}/firestore/sync-all", timeout=30)
    assert r.status_code == 200
    
    # Verify they exist in Firestore
    for doc_id in doc_ids:
        r = requests.get(f"{API}/firestore/document/{doc_id}", timeout=30)
        assert r.status_code == 200, f"Document {doc_id} should exist in Firestore before bulk delete"
    print(f"✓ Both documents exist in Firestore")
    
    # Bulk delete via API
    print(f"Bulk deleting via POST /api/pipelines/bulk_delete...")
    r = requests.post(f"{API}/pipelines/bulk_delete", json={"ids": doc_ids}, timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    result = r.json()
    assert result["deleted"] == 2, f"Expected deleted=2, got {result['deleted']}"
    print(f"✓ Bulk delete returned deleted=2")
    
    # Verify they're removed from Firestore
    for doc_id in doc_ids:
        r = requests.get(f"{API}/firestore/document/{doc_id}", timeout=30)
        assert r.status_code == 404, f"Document {doc_id} should be removed from Firestore after bulk delete, got {r.status_code}"
    print(f"✓ Both documents removed from Firestore")
    
    print("\n" + "=" * 80)
    print("✅ ALL REGRESSION TESTS PASSED")
    print("=" * 80)
    print("\nSummary:")
    print("  • DELETE /api/pipeline/{id} removes from Firestore: ✓")
    print("  • POST /api/pipelines/bulk_delete removes mirrors: ✓")


if __name__ == "__main__":
    main()
