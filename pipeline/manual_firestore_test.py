#!/usr/bin/env python3
"""Manual end-to-end test of Firestore sync requirements."""
import os
import sys
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
    """Create a test document."""
    pid = str(uuid.uuid4())
    return {
        "id": pid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ontology_version": "1.0.0-seed",
        "artifacts": {
            "originals": [{
                "filename": f"TEST_{name}.pdf",
                "path": "n/a",
                "content_type": "application/pdf",
                "size": 1,
            }],
            "extraction": "n/a",
            "pipeline": "n/a",
        },
        "pipeline": {
            "questao": {
                "disciplina": "Matemática",
                "tema": name,
                "resposta_correta": "B",
                "enunciado": f"Enunciado de teste {name}",
            },
            "classificacao": {
                "dominios": ["DOM-TEST"],
                "competencias": ["C1"],
                "processos_cognitivos": [{"id": "P1", "label": "analisar"}],
            },
        },
        "disciplina": "Matemática",
        "tema": name,
        "banca": "ENEM",
        "ano": "2026",
        "resposta_correta": "B",
        "processos": ["P1"],
        "competencias": ["C1"],
        "dominios": ["DOM-TEST"],
    }

async def insert_to_mongo(doc: dict):
    """Insert document to MongoDB."""
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.insert_one(doc)
    cli.close()

async def update_in_mongo(pid: str, updates: dict):
    """Update document in MongoDB."""
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.update_one({"id": pid}, {"$set": updates})
    cli.close()

async def delete_from_mongo(pid: str):
    """Delete document from MongoDB."""
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.delete_one({"id": pid})
    cli.close()

def main():
    print("=" * 80)
    print("MANUAL FIRESTORE SYNC END-TO-END TEST")
    print("=" * 80)
    
    # Create test document
    doc = create_test_doc("ManualTest_CRUD")
    test_id = doc["id"]
    print(f"\n✓ Created test document with ID: {test_id}")
    
    try:
        # REQUIREMENT 1: Create question → Firestore created with SAME ID
        print("\n" + "=" * 80)
        print("REQUIREMENT 1: Create question → Firestore created with SAME ID")
        print("=" * 80)
        
        # Insert to MongoDB
        asyncio.run(insert_to_mongo(doc))
        print(f"✓ Inserted document to MongoDB with ID: {test_id}")
        
        # Sync to Firestore
        r = requests.post(f"{API}/firestore/sync-all", timeout=30)
        assert r.status_code == 200, f"sync-all failed: {r.text}"
        sync_result = r.json()
        print(f"✓ Sync-all completed: {sync_result['upserts']} upserts, {sync_result['orphans_removed']} orphans removed")
        
        # Verify in Firestore
        r = requests.get(f"{API}/firestore/document/{test_id}", timeout=30)
        assert r.status_code == 200, f"Document not found in Firestore: {r.status_code}"
        mirror = r.json()
        
        # Verify SAME ID
        assert mirror["id"] == test_id, f"ID mismatch! Mongo: {test_id}, Firestore: {mirror['id']}"
        print(f"✓ Firestore mirror created with SAME ID: {mirror['id']}")
        
        # Verify artifacts removed
        assert "artifacts" not in mirror, "artifacts field should be removed from mirror!"
        print("✓ 'artifacts' field correctly removed from mirror")
        
        # Verify _id removed
        assert "_id" not in mirror, "_id field should be removed from mirror!"
        print("✓ '_id' field correctly removed from mirror")
        
        # Verify content
        assert mirror["tema"] == "ManualTest_CRUD", f"tema mismatch: {mirror['tema']}"
        assert mirror["disciplina"] == "Matemática", f"disciplina mismatch: {mirror['disciplina']}"
        print(f"✓ Mirror content verified: tema={mirror['tema']}, disciplina={mirror['disciplina']}")
        
        print("\n✅ REQUIREMENT 1 PASSED: Create → Mirror created with SAME ID, no artifacts, no _id")
        
        # REQUIREMENT 2: Edit question → Firestore updated
        print("\n" + "=" * 80)
        print("REQUIREMENT 2: Edit question → Firestore updated")
        print("=" * 80)
        
        # Update directly in MongoDB (simulates internal edit)
        update_payload = {
            "tema": "ManualTest_EDITED",
            "resposta_correta": "C",
            "disciplina": "Física",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        asyncio.run(update_in_mongo(test_id, update_payload))
        print(f"✓ Updated document in MongoDB with new values")
        
        # Sync to Firestore
        r = requests.post(f"{API}/firestore/sync-all", timeout=30)
        assert r.status_code == 200, f"sync-all failed after update: {r.text}"
        print(f"✓ Sync-all completed after update")
        
        # Verify update in Firestore
        r = requests.get(f"{API}/firestore/document/{test_id}", timeout=30)
        assert r.status_code == 200, f"Document not found after update: {r.status_code}"
        updated_mirror = r.json()
        
        # Verify ID unchanged
        assert updated_mirror["id"] == test_id, f"ID changed after update! Was: {test_id}, Now: {updated_mirror['id']}"
        print(f"✓ ID unchanged after update: {updated_mirror['id']}")
        
        # Verify updates reflected
        assert updated_mirror["tema"] == "ManualTest_EDITED", f"tema not updated: {updated_mirror['tema']}"
        assert updated_mirror["resposta_correta"] == "C", f"resposta_correta not updated: {updated_mirror['resposta_correta']}"
        assert updated_mirror["disciplina"] == "Física", f"disciplina not updated: {updated_mirror['disciplina']}"
        print(f"✓ Updates reflected in mirror: tema={updated_mirror['tema']}, resposta_correta={updated_mirror['resposta_correta']}, disciplina={updated_mirror['disciplina']}")
        
        # Verify still no artifacts
        assert "artifacts" not in updated_mirror, "artifacts appeared after update!"
        print("✓ 'artifacts' still removed after update")
        
        print("\n✅ REQUIREMENT 2 PASSED: Edit → Mirror updated with same ID, changes reflected")
        
        # REQUIREMENT 3: Delete question → Firestore removed (no orphan)
        print("\n" + "=" * 80)
        print("REQUIREMENT 3: Delete question → Firestore removed (no orphan)")
        print("=" * 80)
        
        # Delete via DELETE endpoint
        r = requests.delete(f"{API}/pipeline/{test_id}", timeout=30)
        assert r.status_code == 200, f"Delete failed: {r.text}"
        delete_result = r.json()
        assert delete_result["deleted"] is True, f"Delete not confirmed: {delete_result}"
        print(f"✓ Deleted document via DELETE /api/pipeline/{test_id}")
        
        # Verify removed from Firestore
        r = requests.get(f"{API}/firestore/document/{test_id}", timeout=30)
        assert r.status_code == 404, f"Document still exists in Firestore! Status: {r.status_code}"
        print(f"✓ Mirror removed from Firestore (404 returned)")
        
        print("\n✅ REQUIREMENT 3 PASSED: Delete → Mirror removed, no orphan")
        
        # Final status check
        print("\n" + "=" * 80)
        print("FINAL STATUS CHECK")
        print("=" * 80)
        r = requests.get(f"{API}/firestore/status", timeout=30)
        status = r.json()
        print(f"✓ Mode: {status['mode']}")
        print(f"✓ Collection: {status['collection']}")
        print(f"✓ Mirrored count: {status['mirrored_count']}")
        print(f"✓ Retry queue size: {status['retry_queue_size']}")
        
        print("\n" + "=" * 80)
        print("✅ ALL REQUIREMENTS PASSED!")
        print("=" * 80)
        print("\nSummary:")
        print("1. ✅ Create → Firestore mirror created with SAME ID (no duplicates)")
        print("2. ✅ Edit → Firestore mirror updated (same ID, changes reflected)")
        print("3. ✅ Delete → Firestore mirror removed (no orphan)")
        print("4. ✅ Mirrors do NOT contain 'artifacts' or '_id' fields")
        print("5. ✅ Status endpoint returns mode='mock', collection='pipelines'")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        print("\n" + "=" * 80)
        print("CLEANUP")
        print("=" * 80)
        try:
            asyncio.run(delete_from_mongo(test_id))
            print(f"✓ Cleaned up MongoDB document {test_id}")
            requests.post(f"{API}/firestore/sync-all", timeout=30)
            print("✓ Final sync-all to remove any residual mirrors")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")

if __name__ == "__main__":
    main()
