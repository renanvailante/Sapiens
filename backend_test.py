#!/usr/bin/env python3
"""Backend test for Fase 4 - Cognitive ontology tree from JSON v1.4"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load frontend .env to get REACT_APP_BACKEND_URL
load_dotenv("/app/frontend/.env")
BACKEND_URL = os.getenv("REACT_APP_BACKEND_URL", "http://localhost:8001")
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
TEST_EMAIL = "teste@sapiens.dev"
TEST_PASSWORD = "teste1234"

def test_auth_login():
    """Test 1: POST /api/auth/login - Auth regression check"""
    print("\n" + "="*80)
    print("TEST 1: POST /api/auth/login (Auth Regression Check)")
    print("="*80)
    
    url = f"{API_BASE}/auth/login"
    payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        data = response.json()
        
        # Validate response structure
        if "user" not in data or "token" not in data:
            print(f"❌ FAILED: Response missing 'user' or 'token' keys")
            print(f"Response: {data}")
            return None
        
        token = data["token"]
        user = data["user"]
        
        print(f"✅ PASSED: Login successful")
        print(f"   User: {user.get('email')}")
        print(f"   Token: {token[:20]}...")
        
        return token
        
    except Exception as e:
        print(f"❌ FAILED: Exception during login: {e}")
        return None


def test_cognitive_profile_with_auth(token):
    """Test 2: GET /api/cognitive-profile with Bearer token"""
    print("\n" + "="*80)
    print("TEST 2: GET /api/cognitive-profile WITH Auth")
    print("="*80)
    
    url = f"{API_BASE}/cognitive-profile"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        data = response.json()
        
        # Validate ontology_tree key exists
        if "ontology_tree" not in data:
            print(f"❌ FAILED: Response missing 'ontology_tree' key")
            print(f"Response keys: {list(data.keys())}")
            return None
        
        print(f"✅ PASSED: Response contains 'ontology_tree' key")
        print(f"   Response keys: {list(data.keys())}")
        
        return data
        
    except Exception as e:
        print(f"❌ FAILED: Exception during request: {e}")
        return None


def test_ontology_tree_structure(data):
    """Test 3-5: Validate ontology_tree structure"""
    print("\n" + "="*80)
    print("TEST 3-5: Validate ontology_tree Structure")
    print("="*80)
    
    ontology_tree = data.get("ontology_tree", [])
    
    # Test 3: Validate exactly 11 domain nodes
    print("\n--- Test 3: Domain Count ---")
    domain_nodes = [node for node in ontology_tree if node.get("level") == "dominio"]
    domain_count = len(domain_nodes)
    
    if domain_count != 11:
        print(f"❌ FAILED: Expected 11 domain nodes, got {domain_count}")
        print(f"   Domain codes: {[d.get('code') for d in domain_nodes]}")
    else:
        print(f"✅ PASSED: Exactly 11 domain nodes found")
        print(f"   Domain codes: {[d.get('code') for d in domain_nodes]}")
    
    # Test 4: Validate node structure (code, nome, level, answered, children)
    print("\n--- Test 4: Node Structure Validation ---")
    required_fields = ["code", "nome", "level", "answered", "children"]
    all_valid = True
    
    for domain in domain_nodes:
        missing_fields = [f for f in required_fields if f not in domain]
        if missing_fields:
            print(f"❌ FAILED: Domain {domain.get('code')} missing fields: {missing_fields}")
            all_valid = False
    
    if all_valid:
        print(f"✅ PASSED: All domain nodes have required fields: {required_fields}")
    
    # Test 5: Validate 4-level structure and answered=false
    print("\n--- Test 5: 4-Level Structure & Answered Status ---")
    
    # Find DOM-QUANT as example
    dom_quant = next((d for d in domain_nodes if d.get("code") == "DOM-QUANT"), None)
    
    if not dom_quant:
        print(f"❌ FAILED: DOM-QUANT domain not found")
        return False
    
    print(f"\nValidating DOM-QUANT structure:")
    print(f"  Level: {dom_quant.get('level')}")
    print(f"  Answered: {dom_quant.get('answered')}")
    print(f"  Children count: {len(dom_quant.get('children', []))}")
    
    # Check answered=false for domain
    if dom_quant.get("answered") != False:
        print(f"❌ FAILED: DOM-QUANT answered should be False, got {dom_quant.get('answered')}")
    else:
        print(f"✅ PASSED: DOM-QUANT answered=False (no coverage)")
    
    # Check competencias (level 2)
    competencias = dom_quant.get("children", [])
    if not competencias:
        print(f"❌ FAILED: DOM-QUANT has no competencia children")
        return False
    
    print(f"\n  Competencias in DOM-QUANT: {len(competencias)}")
    comp_01 = next((c for c in competencias if c.get("code") == "COMP-01"), None)
    
    if comp_01:
        print(f"  ✅ Found COMP-01 in DOM-QUANT")
        print(f"     Level: {comp_01.get('level')}")
        print(f"     Answered: {comp_01.get('answered')}")
        print(f"     Children count: {len(comp_01.get('children', []))}")
        
        # Check answered=false for competencia
        if comp_01.get("answered") != False:
            print(f"     ❌ FAILED: COMP-01 answered should be False, got {comp_01.get('answered')}")
        else:
            print(f"     ✅ PASSED: COMP-01 answered=False")
        
        # Check processos (level 3)
        processos = comp_01.get("children", [])
        if not processos:
            print(f"     ❌ FAILED: COMP-01 has no processo children")
        else:
            print(f"\n     Processos in COMP-01: {len(processos)}")
            proc_codes = [p.get("code") for p in processos]
            print(f"     Processo codes: {proc_codes}")
            
            # Check for PROC-QUANT-01..04
            expected_procs = ["PROC-QUANT-01", "PROC-QUANT-02", "PROC-QUANT-03", "PROC-QUANT-04"]
            found_procs = [p for p in expected_procs if p in proc_codes]
            
            if found_procs:
                print(f"     ✅ Found expected processos: {found_procs}")
            else:
                print(f"     ⚠️  Expected processos not found: {expected_procs}")
            
            # Check first processo
            if processos:
                proc_01 = processos[0]
                print(f"\n     Validating first processo: {proc_01.get('code')}")
                print(f"        Level: {proc_01.get('level')}")
                print(f"        Answered: {proc_01.get('answered')}")
                print(f"        Children count: {len(proc_01.get('children', []))}")
                
                # Check answered=false for processo
                if proc_01.get("answered") != False:
                    print(f"        ❌ FAILED: Processo answered should be False, got {proc_01.get('answered')}")
                else:
                    print(f"        ✅ PASSED: Processo answered=False")
                
                # Check habilidades (level 4)
                habilidades = proc_01.get("children", [])
                if not habilidades:
                    print(f"        ⚠️  Processo has no habilidade children")
                else:
                    print(f"\n        Habilidades in {proc_01.get('code')}: {len(habilidades)}")
                    hab_codes = [h.get("code") for h in habilidades[:5]]  # Show first 5
                    print(f"        Sample habilidade codes: {hab_codes}")
                    
                    # Check first habilidade
                    hab_01 = habilidades[0]
                    print(f"\n        Validating first habilidade: {hab_01.get('code')}")
                    print(f"           Level: {hab_01.get('level')}")
                    print(f"           Answered: {hab_01.get('answered')}")
                    
                    # Check answered=false for habilidade
                    if hab_01.get("answered") != False:
                        print(f"           ❌ FAILED: Habilidade answered should be False, got {hab_01.get('answered')}")
                    else:
                        print(f"           ✅ PASSED: Habilidade answered=False")
                    
                    # Validate 4-level structure
                    if (dom_quant.get("level") == "dominio" and
                        comp_01.get("level") == "competencia" and
                        proc_01.get("level") == "processo" and
                        hab_01.get("level") == "habilidade"):
                        print(f"\n✅ PASSED: 4-level structure validated: dominio -> competencia -> processo -> habilidade")
                    else:
                        print(f"\n❌ FAILED: 4-level structure validation failed")
    else:
        print(f"  ⚠️  COMP-01 not found in DOM-QUANT")
    
    # Check all nodes have answered=false
    print("\n--- Checking all nodes have answered=False (no coverage) ---")
    all_false = True
    
    for domain in domain_nodes:
        if domain.get("answered") != False:
            print(f"❌ Domain {domain.get('code')} answered={domain.get('answered')} (expected False)")
            all_false = False
        
        for comp in domain.get("children", []):
            if comp.get("answered") != False:
                print(f"❌ Competencia {comp.get('code')} answered={comp.get('answered')} (expected False)")
                all_false = False
            
            for proc in comp.get("children", []):
                if proc.get("answered") != False:
                    print(f"❌ Processo {proc.get('code')} answered={proc.get('answered')} (expected False)")
                    all_false = False
                
                for hab in proc.get("children", []):
                    if hab.get("answered") != False:
                        print(f"❌ Habilidade {hab.get('code')} answered={hab.get('answered')} (expected False)")
                        all_false = False
    
    if all_false:
        print(f"✅ PASSED: All nodes at all levels have answered=False (no coverage)")
    else:
        print(f"❌ FAILED: Some nodes have answered != False")
    
    return True


def test_cognitive_profile_without_auth():
    """Test 6: GET /api/cognitive-profile without auth"""
    print("\n" + "="*80)
    print("TEST 6: GET /api/cognitive-profile WITHOUT Auth")
    print("="*80)
    
    url = f"{API_BASE}/cognitive-profile"
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 401:
            print(f"❌ FAILED: Expected 401, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        print(f"✅ PASSED: Correctly returns 401 without auth")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Exception during request: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("BACKEND TEST: Fase 4 - Cognitive Ontology Tree from JSON v1.4")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    print(f"Test User: {TEST_EMAIL}")
    
    # Test 1: Login
    token = test_auth_login()
    if not token:
        print("\n❌ CRITICAL: Login failed, cannot proceed with other tests")
        sys.exit(1)
    
    # Test 2: Get cognitive profile with auth
    data = test_cognitive_profile_with_auth(token)
    if not data:
        print("\n❌ CRITICAL: Failed to get cognitive profile, cannot proceed with structure tests")
        sys.exit(1)
    
    # Test 3-5: Validate ontology tree structure
    test_ontology_tree_structure(data)
    
    # Test 6: Get cognitive profile without auth
    test_cognitive_profile_without_auth()
    
    print("\n" + "="*80)
    print("BACKEND TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
