#!/usr/bin/env python3
"""
Comprehensive backend test suite for Firestore auto-provisioning endpoint + auth regression.
Tests the new POST /api/firestore/students/me/ensure endpoint and verifies auth still works.
"""
import os
import sys
import requests
import random
import string
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://fast-preview-15.preview.emergentagent.com"
BASE_URL = f"{BACKEND_URL}/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@sapiens.app"
ADMIN_PASSWORD = "Sapiens@2026"

def random_email():
    """Generate a random email for fresh user testing."""
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"freshuser+{rand}@sapiens.app"

def print_test(num, desc):
    print(f"\n{'='*80}")
    print(f"TEST {num}: {desc}")
    print('='*80)

def print_result(passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {details}")
    return passed

def main():
    results = []
    admin_token = None
    fresh_token = None
    fresh_user_id = None
    fresh_email = None
    
    # ========================================================================
    # TEST 1: POST /api/auth/login with admin credentials
    # ========================================================================
    print_test(1, "POST /api/auth/login with admin@sapiens.app / Sapiens@2026")
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response keys: {list(data.keys())}")
            if "user" in data and "token" in data:
                admin_token = data["token"]
                print(f"Token captured: {admin_token[:20]}...")
                results.append(print_result(True, "Login successful, token captured"))
            else:
                print(f"Response: {data}")
                results.append(print_result(False, "Missing 'user' or 'token' in response"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    if not admin_token:
        print("\n❌ CRITICAL: Cannot proceed without admin token. Stopping tests.")
        sys.exit(1)
    
    # ========================================================================
    # TEST 2: POST /api/firestore/students/me/ensure WITH Bearer token (first call)
    # ========================================================================
    print_test(2, "POST /api/firestore/students/me/ensure WITH Bearer token (first call)")
    try:
        resp = requests.post(
            f"{BASE_URL}/firestore/students/me/ensure",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            required_keys = ["created", "user_id", "path", "doc"]
            missing = [k for k in required_keys if k not in data]
            if missing:
                results.append(print_result(False, f"Missing keys: {missing}"))
            else:
                # Verify path format
                expected_path_prefix = f"students_behavior/students_id/{data['user_id']}/behavior_student"
                if data["path"] == expected_path_prefix:
                    # Note: created might be False if doc already exists from previous tests
                    results.append(print_result(True, f"Endpoint working, created={data['created']}, path correct"))
                else:
                    results.append(print_result(False, f"Path mismatch: expected {expected_path_prefix}, got {data['path']}"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 3: POST /api/firestore/students/me/ensure WITH Bearer token AGAIN (idempotent)
    # ========================================================================
    print_test(3, "POST /api/firestore/students/me/ensure WITH Bearer token AGAIN (idempotent)")
    try:
        resp = requests.post(
            f"{BASE_URL}/firestore/students/me/ensure",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            if data.get("created") == False:
                results.append(print_result(True, "Idempotent: created=False on second call"))
            else:
                results.append(print_result(False, f"Expected created=False, got created={data.get('created')}"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 4: POST /api/firestore/students/me/ensure WITHOUT auth
    # ========================================================================
    print_test(4, "POST /api/firestore/students/me/ensure WITHOUT any auth")
    try:
        resp = requests.post(
            f"{BASE_URL}/firestore/students/me/ensure",
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 401:
            results.append(print_result(True, "Correctly returns 401 without auth"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 401, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 5: Sign up a FRESH user
    # ========================================================================
    print_test(5, "POST /api/auth/signup with fresh user")
    fresh_email = random_email()
    fresh_password = "Fresh@2026"
    fresh_name = "Fresh User"
    print(f"Fresh user email: {fresh_email}")
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/signup",
            json={"email": fresh_email, "password": fresh_password, "name": fresh_name},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response keys: {list(data.keys())}")
            if "user" in data and "token" in data:
                fresh_token = data["token"]
                fresh_user_id = data["user"]["user_id"]
                print(f"Fresh token captured: {fresh_token[:20]}...")
                print(f"Fresh user_id: {fresh_user_id}")
                results.append(print_result(True, "Fresh user signup successful"))
            else:
                print(f"Response: {data}")
                results.append(print_result(False, "Missing 'user' or 'token' in response"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    if not fresh_token:
        print("\n❌ CRITICAL: Cannot proceed without fresh user token. Stopping remaining tests.")
        sys.exit(1)
    
    # ========================================================================
    # TEST 6: POST /api/firestore/students/me/ensure with NEW user's Bearer token (first time)
    # ========================================================================
    print_test(6, "POST /api/firestore/students/me/ensure with NEW user's Bearer token (first time)")
    try:
        resp = requests.post(
            f"{BASE_URL}/firestore/students/me/ensure",
            headers={"Authorization": f"Bearer {fresh_token}"},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            if data.get("created") == True:
                results.append(print_result(True, "Fresh user's doc created: created=True"))
            else:
                results.append(print_result(False, f"Expected created=True, got created={data.get('created')}"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 7: POST /api/firestore/students/me/ensure again with new user's token (idempotent)
    # ========================================================================
    print_test(7, "POST /api/firestore/students/me/ensure again with new user's token (idempotent)")
    try:
        resp = requests.post(
            f"{BASE_URL}/firestore/students/me/ensure",
            headers={"Authorization": f"Bearer {fresh_token}"},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            if data.get("created") == False:
                results.append(print_result(True, "Idempotent for fresh user: created=False on second call"))
            else:
                results.append(print_result(False, f"Expected created=False, got created={data.get('created')}"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 8: GET /api/firestore/students/me/behavior with new user's Bearer token
    # ========================================================================
    print_test(8, "GET /api/firestore/students/me/behavior with new user's Bearer token")
    try:
        resp = requests.get(
            f"{BASE_URL}/firestore/students/me/behavior",
            headers={"Authorization": f"Bearer {fresh_token}"},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response keys: {list(data.keys())}")
            # Verify doc has user_id matching fresh user
            if data.get("user_id") == fresh_user_id:
                # Check for initial schema fields
                required_fields = ["profile", "stats", "flags", "events", "created_at"]
                missing = [f for f in required_fields if f not in data]
                if missing:
                    results.append(print_result(False, f"Missing schema fields: {missing}"))
                else:
                    results.append(print_result(True, f"Behavior doc exists with correct user_id and schema"))
            else:
                results.append(print_result(False, f"user_id mismatch: expected {fresh_user_id}, got {data.get('user_id')}"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 9: PUT /api/firestore/students/me/behavior with new user's token
    # ========================================================================
    print_test(9, "PUT /api/firestore/students/me/behavior with new user's token")
    try:
        resp = requests.put(
            f"{BASE_URL}/firestore/students/me/behavior",
            headers={"Authorization": f"Bearer {fresh_token}"},
            json={"data": {"event": "onboarded", "score": 1}},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            results.append(print_result(True, "PUT behavior successful"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 10: GET /api/firestore/students/me/behavior again (verify merge)
    # ========================================================================
    print_test(10, "GET /api/firestore/students/me/behavior again (verify merge)")
    try:
        resp = requests.get(
            f"{BASE_URL}/firestore/students/me/behavior",
            headers={"Authorization": f"Bearer {fresh_token}"},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            if data.get("event") == "onboarded":
                results.append(print_result(True, "Merge successful: event=onboarded found in doc"))
            else:
                results.append(print_result(False, f"Expected event=onboarded, got event={data.get('event')}"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 11a: Regression - GET /api/auth/me with fresh token
    # ========================================================================
    print_test("11a", "Regression: GET /api/auth/me with fresh token")
    try:
        resp = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {fresh_token}"},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            if data.get("user_id") == fresh_user_id:
                results.append(print_result(True, "Auth /me endpoint working correctly"))
            else:
                results.append(print_result(False, f"user_id mismatch: expected {fresh_user_id}, got {data.get('user_id')}"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # TEST 11b: Regression - POST /api/auth/login with admin again
    # ========================================================================
    print_test("11b", "Regression: POST /api/auth/login with admin@sapiens.app again")
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response keys: {list(data.keys())}")
            if "user" in data and "token" in data:
                results.append(print_result(True, "Admin login still working"))
            else:
                results.append(print_result(False, "Missing 'user' or 'token' in response"))
        else:
            print(f"Response: {resp.text}")
            results.append(print_result(False, f"Expected 200, got {resp.status_code}"))
    except Exception as e:
        print(f"Exception: {e}")
        results.append(print_result(False, f"Exception: {e}"))
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
