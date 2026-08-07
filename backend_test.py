#!/usr/bin/env python3
"""
Backend test suite for Fase 4 cognitive profile bugfix.
Tests GET /api/cognitive-profile after Firestore integration fix.
"""
import requests
import sys
from typing import Dict, Any, Set

# Backend URL from frontend/.env
BASE_URL = "https://ebf1a3c9-880c-47b4-8543-da912a98cf66.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
USER_WITH_ANSWERS = {
    "email": "renan.test@sapiens.dev",
    "password": "renan1234",
    "expected_answered_items": 18,
    "expected_processes": {
        "PROC-ESPACO-01", "PROC-ESPACO-02", "PROC-INC-04", "PROC-MUD-01",
        "PROC-QUANT-01", "PROC-QUANT-02", "PROC-QUANT-04",
        "PROC-SIMB-01", "PROC-SIMB-02", "PROC-TEXT-01", "PROC-TEXT-03"
    },
    "expected_dominio_count": 6,
    "expected_competencia_count": 6,
    "expected_habilidade_count": 25
}

USER_WITHOUT_ANSWERS = {
    "email": "teste@sapiens.dev",
    "password": "teste1234",
    "expected_answered_items": 0
}

def print_test(name: str):
    """Print test header."""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print('='*80)

def print_result(passed: bool, message: str):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {message}")

def login(email: str, password: str) -> Dict[str, Any]:
    """Login and return response with token."""
    print(f"\n→ POST /auth/login with {email}")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=10
    )
    print(f"← Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"← Response: {response.text}")
        return {"success": False, "status": response.status_code}
    
    data = response.json()
    print(f"← Token: {data.get('token', '')[:50]}...")
    return {"success": True, "token": data.get("token"), "user": data.get("user")}

def get_cognitive_profile(token: str = None) -> Dict[str, Any]:
    """Get cognitive profile with optional auth token."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print(f"\n→ GET /cognitive-profile with Bearer token")
    else:
        print(f"\n→ GET /cognitive-profile WITHOUT auth")
    
    response = requests.get(
        f"{BASE_URL}/cognitive-profile",
        headers=headers,
        timeout=10
    )
    print(f"← Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"← Response: {response.text[:200]}")
        return {"success": False, "status": response.status_code}
    
    data = response.json()
    print(f"← Keys: {list(data.keys())}")
    print(f"← answered_items: {data.get('answered_items', 'N/A')}")
    return {"success": True, "data": data}

def count_answered_nodes(tree: list, level: str) -> int:
    """Count nodes with answered=true at a specific level."""
    count = 0
    
    def traverse(nodes):
        nonlocal count
        for node in nodes:
            if node.get("level") == level and node.get("answered") is True:
                count += 1
            if "children" in node:
                traverse(node["children"])
    
    traverse(tree)
    return count

def get_answered_process_codes(tree: list) -> Set[str]:
    """Get set of process codes where answered=true."""
    codes = set()
    
    def traverse(nodes):
        for node in nodes:
            if node.get("level") == "processo" and node.get("answered") is True:
                codes.add(node.get("code"))
            if "children" in node:
                traverse(node["children"])
    
    traverse(tree)
    return codes

def count_domain_nodes(tree: list) -> int:
    """Count total domain nodes (level=dominio)."""
    return len([n for n in tree if n.get("level") == "dominio"])

def test_a_user_with_answers():
    """TEST A - Real user WITH 18 answers."""
    print_test("TEST A - User WITH 18 answers (renan.test@sapiens.dev)")
    
    # Step 1: Login
    login_result = login(USER_WITH_ANSWERS["email"], USER_WITH_ANSWERS["password"])
    if not login_result["success"]:
        print_result(False, f"Login failed with status {login_result['status']}")
        return False
    print_result(True, "Login successful, token received")
    
    token = login_result["token"]
    
    # Step 2: Get cognitive profile
    profile_result = get_cognitive_profile(token)
    if not profile_result["success"]:
        print_result(False, f"GET /cognitive-profile failed with status {profile_result['status']}")
        return False
    print_result(True, "GET /cognitive-profile returned 200")
    
    data = profile_result["data"]
    
    # Step 3: Validate ontology_tree exists
    if "ontology_tree" not in data:
        print_result(False, "Response missing 'ontology_tree' key")
        return False
    print_result(True, "Response contains 'ontology_tree'")
    
    tree = data["ontology_tree"]
    
    # Step 4: Validate 11 domain nodes
    domain_count = count_domain_nodes(tree)
    if domain_count != 11:
        print_result(False, f"Expected 11 domain nodes, got {domain_count}")
        return False
    print_result(True, f"Exactly 11 domain nodes found")
    
    # Step 5: Validate answered_items == 18
    answered_items = data.get("answered_items", 0)
    if answered_items != USER_WITH_ANSWERS["expected_answered_items"]:
        print_result(False, f"Expected answered_items=18, got {answered_items}")
        return False
    print_result(True, f"answered_items == 18")
    
    # Step 6: Count answered nodes at processo level
    processo_count = count_answered_nodes(tree, "processo")
    expected_proc_count = len(USER_WITH_ANSWERS["expected_processes"])
    if processo_count != expected_proc_count:
        print_result(False, f"Expected {expected_proc_count} processos with answered=true, got {processo_count}")
        return False
    print_result(True, f"Exactly {expected_proc_count} processos with answered=true")
    
    # Step 7: Validate specific process codes
    actual_processes = get_answered_process_codes(tree)
    expected_processes = USER_WITH_ANSWERS["expected_processes"]
    if actual_processes != expected_processes:
        missing = expected_processes - actual_processes
        extra = actual_processes - expected_processes
        print_result(False, f"Process codes mismatch. Missing: {missing}, Extra: {extra}")
        print(f"   Expected: {sorted(expected_processes)}")
        print(f"   Actual:   {sorted(actual_processes)}")
        return False
    print_result(True, f"Process codes match exactly: {sorted(actual_processes)}")
    
    # Step 8: Count answered nodes at dominio level
    dominio_count = count_answered_nodes(tree, "dominio")
    if dominio_count != USER_WITH_ANSWERS["expected_dominio_count"]:
        print_result(False, f"Expected {USER_WITH_ANSWERS['expected_dominio_count']} dominios with answered=true, got {dominio_count}")
        return False
    print_result(True, f"Exactly {USER_WITH_ANSWERS['expected_dominio_count']} dominios with answered=true")
    
    # Step 9: Count answered nodes at competencia level
    competencia_count = count_answered_nodes(tree, "competencia")
    if competencia_count != USER_WITH_ANSWERS["expected_competencia_count"]:
        print_result(False, f"Expected {USER_WITH_ANSWERS['expected_competencia_count']} competencias with answered=true, got {competencia_count}")
        return False
    print_result(True, f"Exactly {USER_WITH_ANSWERS['expected_competencia_count']} competencias with answered=true")
    
    # Step 10: Count answered nodes at habilidade level
    habilidade_count = count_answered_nodes(tree, "habilidade")
    if habilidade_count != USER_WITH_ANSWERS["expected_habilidade_count"]:
        print_result(False, f"Expected {USER_WITH_ANSWERS['expected_habilidade_count']} habilidades with answered=true, got {habilidade_count}")
        return False
    print_result(True, f"Exactly {USER_WITH_ANSWERS['expected_habilidade_count']} habilidades with answered=true")
    
    print("\n" + "="*80)
    print("TEST A SUMMARY: ✅ ALL CHECKS PASSED")
    print("="*80)
    return True

def test_b_user_without_answers():
    """TEST B - User with NO answers."""
    print_test("TEST B - User WITHOUT answers (teste@sapiens.dev)")
    
    # Step 1: Login
    login_result = login(USER_WITHOUT_ANSWERS["email"], USER_WITHOUT_ANSWERS["password"])
    if not login_result["success"]:
        print_result(False, f"Login failed with status {login_result['status']}")
        return False
    print_result(True, "Login successful, token received")
    
    token = login_result["token"]
    
    # Step 2: Get cognitive profile
    profile_result = get_cognitive_profile(token)
    if not profile_result["success"]:
        print_result(False, f"GET /cognitive-profile failed with status {profile_result['status']}")
        return False
    print_result(True, "GET /cognitive-profile returned 200")
    
    data = profile_result["data"]
    
    # Step 3: Validate ontology_tree exists
    if "ontology_tree" not in data:
        print_result(False, "Response missing 'ontology_tree' key")
        return False
    print_result(True, "Response contains 'ontology_tree'")
    
    tree = data["ontology_tree"]
    
    # Step 4: Validate 11 domain nodes
    domain_count = count_domain_nodes(tree)
    if domain_count != 11:
        print_result(False, f"Expected 11 domain nodes, got {domain_count}")
        return False
    print_result(True, f"Exactly 11 domain nodes found")
    
    # Step 5: Validate answered_items == 0
    answered_items = data.get("answered_items", -1)
    if answered_items != 0:
        print_result(False, f"Expected answered_items=0, got {answered_items}")
        return False
    print_result(True, f"answered_items == 0")
    
    # Step 6: Validate ALL nodes have answered=false
    for level in ["processo", "dominio", "competencia", "habilidade"]:
        count = count_answered_nodes(tree, level)
        if count != 0:
            print_result(False, f"Expected 0 {level} nodes with answered=true, got {count}")
            return False
        print_result(True, f"All {level} nodes have answered=false")
    
    print("\n" + "="*80)
    print("TEST B SUMMARY: ✅ ALL CHECKS PASSED")
    print("="*80)
    return True

def test_c_auth_protection():
    """TEST C - Auth protection."""
    print_test("TEST C - Auth protection (401 without token)")
    
    # Get cognitive profile without auth
    profile_result = get_cognitive_profile(token=None)
    
    if profile_result["success"]:
        print_result(False, "Expected 401, but got 200")
        return False
    
    if profile_result["status"] != 401:
        print_result(False, f"Expected 401, got {profile_result['status']}")
        return False
    
    print_result(True, "GET /cognitive-profile without auth returns 401")
    
    print("\n" + "="*80)
    print("TEST C SUMMARY: ✅ ALL CHECKS PASSED")
    print("="*80)
    return True

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("BACKEND TEST SUITE - Fase 4 Cognitive Profile Bugfix")
    print("Testing GET /api/cognitive-profile after Firestore integration")
    print("="*80)
    
    results = {
        "TEST A (User with 18 answers)": test_a_user_with_answers(),
        "TEST B (User without answers)": test_b_user_without_answers(),
        "TEST C (Auth protection)": test_c_auth_protection()
    }
    
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
