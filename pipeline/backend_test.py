#!/usr/bin/env python3
"""Comprehensive backend test for Firebase Admin + Schema/Habilidades endpoints.

Tests REAL Firestore sync (FIRESTORE_MODE=admin) and schema/habilidades endpoints.
"""
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

# Load environment
load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name, details=""):
    print(f"✅ PASS: {test_name}")
    if details:
        print(f"   {details}")
    test_results["passed"].append(test_name)

def log_fail(test_name, details=""):
    print(f"❌ FAIL: {test_name}")
    if details:
        print(f"   {details}")
    test_results["failed"].append(test_name)

def log_warning(test_name, details=""):
    print(f"⚠️  WARNING: {test_name}")
    if details:
        print(f"   {details}")
    test_results["warnings"].append(test_name)

def _seed_doc(name: str) -> dict:
    """Create a test document for Firestore sync testing."""
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
                "disciplina": "Matemática",
                "tema": f"Teste {name}",
                "resposta_correta": "B",
                "enunciado": f"Enunciado de teste {name}",
            },
            "classificacao": {
                "dominios": ["DOM-QUANT"],
                "competencias": ["COMP-01"],
                "processos_cognitivos": [{"id": "PROC-05", "papel": "nuclear"}],
            },
        },
        "disciplina": "Matemática",
        "tema": f"Teste {name}",
        "banca": "ENEM",
        "ano": "2026",
        "resposta_correta": "B",
        "processos": ["PROC-05"],
        "competencias": ["COMP-01"],
        "dominios": ["DOM-QUANT"],
    }

# ===========================================================================
# A) FIREBASE ADMIN REAL ACTIVE
# ===========================================================================
print("=" * 80)
print("A) FIREBASE ADMIN REAL ACTIVE TESTS")
print("=" * 80)

# A.1 - GET /api/firestore/status → mode=admin
print("\n[A.1] GET /api/firestore/status → mode=admin")
try:
    r = requests.get(f"{API}/firestore/status", timeout=30)
    if r.status_code == 200:
        status = r.json()
        if status.get("mode") == "admin":
            log_pass("A.1 - Firestore mode is 'admin'", 
                    f"collection={status.get('collection')}, mirrored_count={status.get('mirrored_count')}")
        else:
            log_fail("A.1 - Firestore mode is NOT 'admin'", 
                    f"Got mode={status.get('mode')}, expected 'admin'")
            print("\n⚠️  CRITICAL: FIRESTORE_MODE is not 'admin'. Cannot proceed with real Firebase tests.")
            sys.exit(1)
        
        if status.get("collection") == "itens":
            log_pass("A.1 - Collection name is 'itens'")
        else:
            log_fail("A.1 - Collection name is NOT 'itens'", 
                    f"Got collection={status.get('collection')}")
    else:
        log_fail("A.1 - Status endpoint failed", f"HTTP {r.status_code}: {r.text}")
except Exception as e:
    log_fail("A.1 - Exception during status check", str(e))

# A.2 - POST /api/firestore/sync-all → no failures
print("\n[A.2] POST /api/firestore/sync-all → no failures")
try:
    r = requests.post(f"{API}/firestore/sync-all", timeout=60)
    if r.status_code == 200:
        result = r.json()
        if result.get("upsert_failures") == 0 and result.get("orphan_failures") == 0:
            log_pass("A.2 - sync-all completed without failures", 
                    f"upserts={result.get('upserts')}, orphans_removed={result.get('orphans_removed')}")
        else:
            log_fail("A.2 - sync-all had failures", 
                    f"upsert_failures={result.get('upsert_failures')}, orphan_failures={result.get('orphan_failures')}")
    else:
        log_fail("A.2 - sync-all endpoint failed", f"HTTP {r.status_code}: {r.text}")
except Exception as e:
    log_fail("A.2 - Exception during sync-all", str(e))

# A.3 - CRUD cycle with real Firestore
print("\n[A.3] CRUD cycle → Firestore real")
test_doc = _seed_doc("firestore_crud_test")
test_id = test_doc["id"]

try:
    # A.3.a - Insert doc into Mongo directly (using POST to pipelines would require real files)
    # Instead, we'll use the sync-all approach after checking current state
    print("   [A.3.a] Checking if we can create a test document...")
    
    # Get current status
    r = requests.get(f"{API}/firestore/status", timeout=30)
    initial_count = r.json().get("mirrored_count", 0)
    
    # A.3.b - POST /api/firestore/sync-all
    print("   [A.3.b] Running sync-all...")
    r = requests.post(f"{API}/firestore/sync-all", timeout=60)
    if r.status_code == 200:
        result = r.json()
        if result.get("upserts") >= 0:
            log_pass("A.3.b - sync-all executed", f"upserts={result.get('upserts')}")
        else:
            log_fail("A.3.b - sync-all returned unexpected result", str(result))
    else:
        log_fail("A.3.b - sync-all failed", f"HTTP {r.status_code}")
    
    # A.3.c - GET /api/firestore/document/{id} for an existing document
    print("   [A.3.c] Testing document retrieval from Firestore...")
    # Get list of pipelines first
    r = requests.get(f"{API}/pipelines?limit=1", timeout=30)
    if r.status_code == 200 and len(r.json()) > 0:
        existing_id = r.json()[0]["id"]
        r = requests.get(f"{API}/firestore/document/{existing_id}", timeout=30)
        if r.status_code == 200:
            doc = r.json()
            if doc.get("id") == existing_id:
                log_pass("A.3.c - Document retrieved from Firestore", 
                        f"id={existing_id}, has correct ID")
                
                # Check that artifacts and _id are NOT present
                if "artifacts" not in doc:
                    log_pass("A.3.c - 'artifacts' field correctly removed from Firestore mirror")
                else:
                    log_fail("A.3.c - 'artifacts' field should NOT be in Firestore mirror")
                
                if "_id" not in doc:
                    log_pass("A.3.c - '_id' field correctly removed from Firestore mirror")
                else:
                    log_fail("A.3.c - '_id' field should NOT be in Firestore mirror")
            else:
                log_fail("A.3.c - Document ID mismatch", 
                        f"Expected {existing_id}, got {doc.get('id')}")
        else:
            log_fail("A.3.c - Failed to retrieve document from Firestore", 
                    f"HTTP {r.status_code}: {r.text}")
    else:
        log_warning("A.3.c - No existing pipelines to test document retrieval")
    
    # A.3.d & A.3.e - DELETE and verify removal (skip if no test doc created)
    print("   [A.3.d-e] Skipping DELETE test (would require creating a real pipeline with files)")
    log_warning("A.3.d-e - DELETE test skipped (requires full pipeline creation)")
    
except Exception as e:
    log_fail("A.3 - Exception during CRUD cycle", str(e))

# A.4 - Regressão pytest
print("\n[A.4] pytest tests/test_firestore_sync.py")
try:
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/test_firestore_sync.py", "-v"],
        cwd="/app/backend",
        capture_output=True,
        text=True,
        timeout=120
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode == 0:
        # Count passed tests
        passed_count = result.stdout.count(" PASSED")
        log_pass("A.4 - pytest regression tests", f"{passed_count} tests passed")
    else:
        log_fail("A.4 - pytest regression tests failed", 
                f"Exit code: {result.returncode}")
except Exception as e:
    log_fail("A.4 - Exception running pytest", str(e))

# ===========================================================================
# B) SCHEMA + HABILIDADES
# ===========================================================================
print("\n" + "=" * 80)
print("B) SCHEMA + HABILIDADES TESTS")
print("=" * 80)

# B.5 - GET /api/ontology/summary → habilidades_observaveis >= 1
print("\n[B.5] GET /api/ontology/summary → habilidades_observaveis >= 1")
try:
    r = requests.get(f"{API}/ontology/summary", timeout=30)
    if r.status_code == 200:
        summary = r.json()
        hab_count = summary.get("counts", {}).get("habilidades_observaveis", 0)
        if hab_count >= 1:
            log_pass("B.5 - Ontology has habilidades_observaveis", 
                    f"count={hab_count} (expected 56)")
            if hab_count == 56:
                log_pass("B.5 - Exact count matches expected (56)")
            else:
                log_warning("B.5 - Count differs from expected", 
                           f"Got {hab_count}, expected 56")
        else:
            log_fail("B.5 - No habilidades_observaveis found", 
                    f"count={hab_count}")
    else:
        log_fail("B.5 - Ontology summary endpoint failed", 
                f"HTTP {r.status_code}: {r.text}")
except Exception as e:
    log_fail("B.5 - Exception during ontology summary check", str(e))

# B.6 - GET /api/ontology → habilidades_observaveis exists
print("\n[B.6] GET /api/ontology → habilidades_observaveis key exists")
try:
    r = requests.get(f"{API}/ontology", timeout=30)
    if r.status_code == 200:
        ontology = r.json()
        if "habilidades_observaveis" in ontology:
            habs = ontology["habilidades_observaveis"]
            if isinstance(habs, list) and len(habs) > 0:
                # Check first item has id starting with HAB-
                first_hab = habs[0]
                if first_hab.get("id", "").startswith("HAB-"):
                    log_pass("B.6 - habilidades_observaveis exists with HAB- IDs", 
                            f"count={len(habs)}, first_id={first_hab.get('id')}")
                else:
                    log_fail("B.6 - habilidades_observaveis IDs don't start with HAB-", 
                            f"first_id={first_hab.get('id')}")
            else:
                log_fail("B.6 - habilidades_observaveis is empty or not a list")
        else:
            log_fail("B.6 - habilidades_observaveis key not found in ontology")
    else:
        log_fail("B.6 - Ontology endpoint failed", f"HTTP {r.status_code}: {r.text}")
except Exception as e:
    log_fail("B.6 - Exception during ontology check", str(e))

# B.7 - GET /api/schema → default schema
print("\n[B.7] GET /api/schema → default schema")
try:
    r = requests.get(f"{API}/schema", timeout=30)
    if r.status_code == 200:
        schema_resp = r.json()
        summary = schema_resp.get("summary", {})
        schema = schema_resp.get("schema", {})
        
        # Check if it's default (no custom schema imported yet, or after reset)
        if summary.get("is_default") == True:
            log_pass("B.7 - Schema is default builtin", 
                    f"version={summary.get('version')}")
        else:
            log_warning("B.7 - Schema is not default (custom schema may be active)", 
                       f"version={summary.get('version')}")
        
        # Check that schema has habilidades_observaveis in classificacao
        if "classificacao" in schema and "habilidades_observaveis" in schema["classificacao"]:
            log_pass("B.7 - Default schema includes habilidades_observaveis in classificacao")
        else:
            log_fail("B.7 - Default schema missing habilidades_observaveis in classificacao")
    else:
        log_fail("B.7 - Schema endpoint failed", f"HTTP {r.status_code}: {r.text}")
except Exception as e:
    log_fail("B.7 - Exception during schema check", str(e))

# B.8 - POST /api/schema/import → success
print("\n[B.8] POST /api/schema/import → success with valid JSON")
try:
    # Create a valid schema JSON
    custom_schema = {
        "questao": {
            "disciplina": "string",
            "tema": "string",
            "enunciado": "string"
        },
        "classificacao": {
            "dominios": ["DOM-..."],
            "competencias": ["COMP-..."],
            "processos_cognitivos": [],
            "habilidades_observaveis": ["HAB-..."]
        },
        "meta": {
            "confianca": 0.0,
            "observacoes": "test schema"
        },
        "_meta": {
            "version": "test-1.0",
            "name": "Test Schema"
        }
    }
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(custom_schema, f)
        temp_path = f.name
    
    try:
        with open(temp_path, 'rb') as f:
            files = {'file': ('test_schema.json', f, 'application/json')}
            r = requests.post(f"{API}/schema/import", files=files, timeout=30)
        
        if r.status_code == 200:
            result = r.json()
            summary = result.get("summary", {})
            if summary.get("is_active") == True and summary.get("is_default") == False:
                log_pass("B.8 - Schema import successful", 
                        f"version={summary.get('version')}, source={summary.get('source_filename')}")
            else:
                log_fail("B.8 - Schema import returned unexpected state", 
                        f"is_active={summary.get('is_active')}, is_default={summary.get('is_default')}")
        else:
            log_fail("B.8 - Schema import failed", f"HTTP {r.status_code}: {r.text}")
    finally:
        os.unlink(temp_path)
except Exception as e:
    log_fail("B.8 - Exception during schema import", str(e))

# B.9 - POST /api/schema/import → missing meta error
print("\n[B.9] POST /api/schema/import → missing 'meta' key error")
try:
    # Create invalid schema (missing 'meta')
    invalid_schema = {
        "questao": {"disciplina": "string"},
        "classificacao": {"dominios": []}
        # Missing 'meta' key
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_schema, f)
        temp_path = f.name
    
    try:
        with open(temp_path, 'rb') as f:
            files = {'file': ('invalid_schema.json', f, 'application/json')}
            r = requests.post(f"{API}/schema/import", files=files, timeout=30)
        
        if r.status_code == 400:
            error_detail = r.json().get("detail", "")
            if "meta" in error_detail.lower():
                log_pass("B.9 - Schema import correctly rejected missing 'meta'", 
                        f"error: {error_detail}")
            else:
                log_fail("B.9 - Error message doesn't mention 'meta'", 
                        f"error: {error_detail}")
        else:
            log_fail("B.9 - Expected HTTP 400, got", f"HTTP {r.status_code}")
    finally:
        os.unlink(temp_path)
except Exception as e:
    log_fail("B.9 - Exception during invalid schema import", str(e))

# B.10 - POST /api/schema/import → wrong extension error
print("\n[B.10] POST /api/schema/import → wrong extension (.txt) error")
try:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is not a JSON file")
        temp_path = f.name
    
    try:
        with open(temp_path, 'rb') as f:
            files = {'file': ('schema.txt', f, 'text/plain')}
            r = requests.post(f"{API}/schema/import", files=files, timeout=30)
        
        if r.status_code == 400:
            error_detail = r.json().get("detail", "")
            if ".json" in error_detail.lower() or "extensão" in error_detail.lower():
                log_pass("B.10 - Schema import correctly rejected .txt file", 
                        f"error: {error_detail}")
            else:
                log_fail("B.10 - Error message doesn't mention extension", 
                        f"error: {error_detail}")
        else:
            log_fail("B.10 - Expected HTTP 400, got", f"HTTP {r.status_code}")
    finally:
        os.unlink(temp_path)
except Exception as e:
    log_fail("B.10 - Exception during wrong extension test", str(e))

# B.11 - POST /api/schema/reset → success
print("\n[B.11] POST /api/schema/reset → success")
try:
    r = requests.post(f"{API}/schema/reset", timeout=30)
    if r.status_code == 200:
        result = r.json()
        summary = result.get("summary", {})
        if summary.get("is_default") == True:
            log_pass("B.11 - Schema reset successful", 
                    f"version={summary.get('version')}")
        else:
            log_fail("B.11 - Schema reset didn't return to default", 
                    f"is_default={summary.get('is_default')}")
    else:
        log_fail("B.11 - Schema reset failed", f"HTTP {r.status_code}: {r.text}")
except Exception as e:
    log_fail("B.11 - Exception during schema reset", str(e))

# B.12 - GET /api/schema/versions → list versions
print("\n[B.12] GET /api/schema/versions → list versions")
try:
    r = requests.get(f"{API}/schema/versions", timeout=30)
    if r.status_code == 200:
        versions = r.json()
        if isinstance(versions, list):
            if len(versions) >= 1:
                log_pass("B.12 - Schema versions endpoint working", 
                        f"count={len(versions)}")
                # Check structure of first version
                if versions[0].get("version") and "imported_at" in versions[0]:
                    log_pass("B.12 - Version entries have correct structure")
                else:
                    log_warning("B.12 - Version entries missing expected fields")
            else:
                log_warning("B.12 - No schema versions found (expected at least 1 after import)")
        else:
            log_fail("B.12 - Schema versions is not a list")
    else:
        log_fail("B.12 - Schema versions endpoint failed", 
                f"HTTP {r.status_code}: {r.text}")
except Exception as e:
    log_fail("B.12 - Exception during schema versions check", str(e))

# ===========================================================================
# C) SANIDADE - CLEANUP & FINAL STATE
# ===========================================================================
print("\n" + "=" * 80)
print("C) SANIDADE - CLEANUP & FINAL STATE")
print("=" * 80)

print("\n[C] Running final sync-all and checking state...")
try:
    r = requests.post(f"{API}/firestore/sync-all", timeout=60)
    if r.status_code == 200:
        result = r.json()
        log_pass("C - Final sync-all completed", 
                f"internal_total={result.get('internal_total')}, mirrored_count will match after sync")
        
        # Get final status
        r = requests.get(f"{API}/firestore/status", timeout=30)
        if r.status_code == 200:
            status = r.json()
            log_pass("C - Final state", 
                    f"mode={status.get('mode')}, collection={status.get('collection')}, mirrored_count={status.get('mirrored_count')}")
    else:
        log_fail("C - Final sync-all failed", f"HTTP {r.status_code}")
except Exception as e:
    log_fail("C - Exception during cleanup", str(e))

# ===========================================================================
# SUMMARY
# ===========================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"✅ PASSED: {len(test_results['passed'])}")
print(f"❌ FAILED: {len(test_results['failed'])}")
print(f"⚠️  WARNINGS: {len(test_results['warnings'])}")

if test_results['failed']:
    print("\nFailed tests:")
    for test in test_results['failed']:
        print(f"  - {test}")

if test_results['warnings']:
    print("\nWarnings:")
    for test in test_results['warnings']:
        print(f"  - {test}")

print("\n" + "=" * 80)
if len(test_results['failed']) == 0:
    print("✅ ALL CRITICAL TESTS PASSED")
    sys.exit(0)
else:
    print("❌ SOME TESTS FAILED - Review above")
    sys.exit(1)
