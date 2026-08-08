#!/usr/bin/env python3
"""Manual bulk sync flow test for Firestore collection rename verification."""
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
                "disciplina": "MANUAL_TEST",
                "tema": name,
                "resposta_correta": "A",
                "enunciado": f"Enunciado manual {name}",
            },
            "classificacao": {
                "dominios": ["DOM-MANUAL"],
                "competencias": ["C-MANUAL"],
                "processos_cognitivos": [{"id": "P-MANUAL", "label": "testar"}],
            },
        },
        "disciplina": "MANUAL_TEST",
        "tema": name,
        "banca": "MANUAL",
        "ano": "2026",
        "resposta_correta": "A",
        "processos": ["P-MANUAL"],
        "competencias": ["C-MANUAL"],
        "dominios": ["DOM-MANUAL"],
    }


async def insert_docs(docs: list[dict]) -> None:
    """Insert documents into MongoDB."""
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.insert_many(docs)
    cli.close()


async def delete_docs(ids: list[str]) -> None:
    """Delete documents from MongoDB."""
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.delete_many({"id": {"$in": ids}})
    cli.close()


def main():
    print("=" * 80)
    print("MANUAL BULK SYNC FLOW TEST")
    print("=" * 80)
    
    # Step 1: Create 3 test documents
    print("\n[1] Creating 3 test documents...")
    docs = [
        _seed_doc("manual_test_1"),
        _seed_doc("manual_test_2"),
        _seed_doc("manual_test_3"),
    ]
    doc_ids = [d["id"] for d in docs]
    print(f"    Document IDs: {doc_ids}")
    
    # Step 2: Insert into MongoDB
    print("\n[2] Inserting documents into MongoDB (collection: pipelines)...")
    asyncio.run(insert_docs(docs))
    print("    ✓ Documents inserted")
    
    try:
        # Step 3: Call POST /api/firestore/sync-all
        print("\n[3] Calling POST /api/firestore/sync-all...")
        r = requests.post(f"{API}/firestore/sync-all", timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        sync_result = r.json()
        print(f"    Response: {sync_result}")
        
        # Verify collection name
        assert sync_result["collection"] == "itens", f"Expected collection='itens', got '{sync_result['collection']}'"
        print(f"    ✓ Collection name: {sync_result['collection']}")
        
        # Verify counts
        assert sync_result["internal_total"] >= 3, f"Expected internal_total >= 3, got {sync_result['internal_total']}"
        assert sync_result["upserts"] >= 3, f"Expected upserts >= 3, got {sync_result['upserts']}"
        print(f"    ✓ internal_total: {sync_result['internal_total']}")
        print(f"    ✓ upserts: {sync_result['upserts']}")
        print(f"    ✓ orphans_removed: {sync_result['orphans_removed']}")
        
        # Step 4: Verify each document individually
        print("\n[4] Verifying each document via GET /api/firestore/document/{id}...")
        for i, doc_id in enumerate(doc_ids, 1):
            print(f"    [{i}] Checking document {doc_id}...")
            r = requests.get(f"{API}/firestore/document/{doc_id}", timeout=30)
            assert r.status_code == 200, f"Expected 200 for {doc_id}, got {r.status_code}: {r.text}"
            
            mirror = r.json()
            
            # Verify ID matches
            assert mirror["id"] == doc_id, f"Expected id={doc_id}, got {mirror['id']}"
            print(f"        ✓ ID matches: {mirror['id']}")
            
            # Verify no artifacts field
            assert "artifacts" not in mirror, f"Document {doc_id} should NOT contain 'artifacts' field"
            print(f"        ✓ No 'artifacts' field")
            
            # Verify no _id field
            assert "_id" not in mirror, f"Document {doc_id} should NOT contain '_id' field"
            print(f"        ✓ No '_id' field")
            
            # Verify tema matches
            expected_tema = f"manual_test_{i}"
            assert mirror["tema"] == expected_tema, f"Expected tema={expected_tema}, got {mirror['tema']}"
            print(f"        ✓ Tema matches: {mirror['tema']}")
            
            # Verify _synced_at exists
            assert "_synced_at" in mirror, f"Document {doc_id} should contain '_synced_at' field"
            print(f"        ✓ Has '_synced_at': {mirror['_synced_at']}")
        
        print("\n[5] Cleanup: Deleting test documents from MongoDB...")
        asyncio.run(delete_docs(doc_ids))
        print("    ✓ Documents deleted from MongoDB")
        
        print("\n[6] Running sync-all again to remove orphans...")
        r = requests.post(f"{API}/firestore/sync-all", timeout=30)
        assert r.status_code == 200
        sync_result = r.json()
        print(f"    Response: {sync_result}")
        print(f"    ✓ orphans_removed: {sync_result['orphans_removed']}")
        
        # Verify documents are gone from Firestore
        print("\n[7] Verifying documents are removed from Firestore...")
        for doc_id in doc_ids:
            r = requests.get(f"{API}/firestore/document/{doc_id}", timeout=30)
            assert r.status_code == 404, f"Expected 404 for {doc_id}, got {r.status_code}"
        print("    ✓ All documents removed from Firestore")
        
        print("\n" + "=" * 80)
        print("✅ ALL MANUAL TESTS PASSED")
        print("=" * 80)
        print("\nSummary:")
        print("  • Collection name: itens ✓")
        print("  • Bulk sync working: ✓")
        print("  • Documents retrievable by ID: ✓")
        print("  • No 'artifacts' field: ✓")
        print("  • No '_id' field: ✓")
        print("  • Orphan removal working: ✓")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        # Cleanup on failure
        print("\nCleaning up test documents...")
        asyncio.run(delete_docs(doc_ids))
        raise


if __name__ == "__main__":
    main()
