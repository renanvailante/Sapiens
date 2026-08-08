"""Auth login bug-fix tests: verify strip/lower normalisation on email/password."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://taxonomia-visual.preview.emergentagent.com").rstrip("/")
LOGIN = f"{BASE_URL}/api/auth/login"
ME = f"{BASE_URL}/api/auth/me"
TURMA = f"{BASE_URL}/api/turma"


def _login(email: str, password: str):
    s = requests.Session()
    r = s.post(LOGIN, json={"email": email, "password": password}, timeout=15)
    return s, r


@pytest.mark.parametrize("email,password,label", [
    ("admin@sapiens.edu", "admin123", "baseline"),
    ("admin@sapiens.edu ", "admin123", "email trailing space"),
    (" admin@sapiens.edu", "admin123", "email leading space"),
    ("Admin@Sapiens.edu", "admin123", "uppercase email"),
    ("admin@sapiens.edu", "admin123 ", "password trailing space"),
    ("Admin@Sapiens.edu ", " admin123 ", "combo strip"),
])
def test_login_variants_authenticate(email, password, label):
    s, r = _login(email, password)
    assert r.status_code == 200, f"{label}: expected 200, got {r.status_code} body={r.text}"
    data = r.json()
    assert data.get("user", {}).get("email") == "admin@sapiens.edu"
    assert data.get("user", {}).get("role") == "admin"
    # cookie set
    assert any(c.name == "access_token" for c in s.cookies), f"{label}: access_token cookie not set"


def test_login_wrong_password_401():
    _, r = _login("admin@sapiens.edu", "wrongpass")
    assert r.status_code == 401
    body = r.json()
    # Portuguese error text
    detail = (body.get("detail") or body.get("message") or "").lower()
    assert "credenc" in detail or "invalid" in detail, f"unexpected body: {body}"


def test_me_after_login():
    s, r = _login("admin@sapiens.edu ", "admin123")
    assert r.status_code == 200
    me = s.get(ME, timeout=10)
    assert me.status_code == 200
    assert me.json().get("email") == "admin@sapiens.edu"


def test_turma_endpoint_after_login():
    s, r = _login("admin@sapiens.edu", "admin123")
    assert r.status_code == 200
    t = s.get(TURMA, timeout=15)
    assert t.status_code == 200, f"/api/turma failed: {t.status_code} {t.text[:200]}"


def test_bcrypt_hash_format():
    """Sanity: seeded admin hash should be bcrypt ($2b$)."""
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "sapiens_dashboard")
    client = MongoClient(mongo_url)
    user = client[db_name]["users"].find_one({"email": "admin@sapiens.edu"})
    assert user is not None, "admin user not seeded"
    ph = user.get("password_hash") or user.get("password") or ""
    assert ph.startswith("$2"), f"bcrypt hash expected, got: {ph[:10]}"
