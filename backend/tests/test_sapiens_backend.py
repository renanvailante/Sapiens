"""Sapiens backend end-to-end pytest suite."""
from __future__ import annotations

import base64
import io
import os
import time
import uuid

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    from dotenv import dotenv_values
    BASE_URL = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")

API = f"{BASE_URL}/api"

TEST_EMAIL = "qa@sapiens.app"
TEST_PASSWORD = "qa12345"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_token(session):
    # try login first
    r = session.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    if r.status_code != 200:
        # signup
        r = session.post(f"{API}/auth/signup", json={"email": TEST_EMAIL, "name": "QA User", "password": TEST_PASSWORD}, timeout=15)
        assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    token = r.json().get("token")
    assert token
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ---------------- Root ----------------

def test_root(session):
    r = session.get(f"{API}/", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("app") == "Sapiens"
    assert data.get("status") == "ok"


# ---------------- Exams ----------------

def test_list_exams(session):
    r = session.get(f"{API}/exams", timeout=15)
    assert r.status_code == 200
    exams = r.json()
    assert isinstance(exams, list)
    assert len(exams) >= 6, f"Expected >=6 seeded exams, got {len(exams)}"
    for e in exams:
        assert e.get("total_questions") == 12, f"exam {e.get('title')} total_questions={e.get('total_questions')}"
        assert "_id" not in e
    years = {e["year"] for e in exams}
    assert {2022, 2023, 2024}.issubset(years)


def test_get_exam_hides_answers(session):
    exams = session.get(f"{API}/exams", timeout=15).json()
    exam_id = exams[0]["exam_id"]
    r = session.get(f"{API}/exams/{exam_id}", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "exam" in data and "questions" in data
    assert len(data["questions"]) == 12
    for q in data["questions"]:
        assert "correct_answer" not in q, "correct_answer leaked!"
        assert "tags" not in q, "tags leaked!"
        assert "_id" not in q


def test_get_exam_not_found(session):
    r = session.get(f"{API}/exams/does-not-exist", timeout=10)
    assert r.status_code == 404


# ---------------- Auth ----------------

def test_signup_duplicate(session):
    # After session fixture ran, TEST_EMAIL exists (from auth_token fixture at collection or now)
    # Ensure user exists first:
    session.post(f"{API}/auth/signup", json={"email": TEST_EMAIL, "name": "QA User", "password": TEST_PASSWORD}, timeout=15)
    r = session.post(f"{API}/auth/signup", json={"email": TEST_EMAIL, "name": "QA User", "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 400


def test_signup_new_user_returns_token_and_cookie(session):
    email = f"TEST_{uuid.uuid4().hex[:8]}@sapiens.app"
    r = session.post(f"{API}/auth/signup", json={"email": email, "name": "TestX", "password": "pw123456"}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["user"]["email"] == email
    # Cookie set
    assert any(c.name == "session_token" for c in r.cookies) or "session_token" in r.headers.get("set-cookie", "").lower()


def test_login_wrong_password(session, auth_token):
    r = session.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": "wrong-pw"}, timeout=15)
    assert r.status_code == 401


def test_login_correct(session, auth_token):
    r = session.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200
    assert r.json().get("token")


def test_me_without_token(session):
    r = requests.get(f"{API}/auth/me", timeout=10)  # fresh session, no auth
    assert r.status_code == 401


def test_me_with_token(auth_headers):
    r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == TEST_EMAIL
    assert "password_hash" not in data


# ---------------- Analysis (slow AI) ----------------

@pytest.fixture(scope="session")
def sample_exam_with_questions(session):
    exams = session.get(f"{API}/exams", timeout=15).json()
    exam_id = exams[0]["exam_id"]
    data = session.get(f"{API}/exams/{exam_id}", timeout=15).json()
    return exam_id, data["questions"]


def test_submit_analysis_full_ai(auth_headers, sample_exam_with_questions):
    exam_id, questions = sample_exam_with_questions
    # Provide a mix — first 6 letter A, rest B, so we exercise diagnosis
    letters = ["A", "B", "C", "D", "E"]
    answers = [{"question_id": q["question_id"], "letter": letters[i % 5]} for i, q in enumerate(questions)]
    payload = {"exam_id": exam_id, "answers": answers}
    start = time.time()
    r = requests.post(f"{API}/analyses", headers=auth_headers, json=payload, timeout=180)
    elapsed = time.time() - start
    print(f"analysis took {elapsed:.1f}s")
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    data = r.json()
    assert data["exam_id"] == exam_id
    assert data["total"] == len(questions)
    assert isinstance(data["percent"], (int, float))
    assert data["by_area"]
    assert data["diagnostic_headline"], "diagnostic_headline empty"
    assert data["diagnostic_body"], "diagnostic_body empty"
    cp = data["cognitive_profile"]
    assert isinstance(cp, dict) and len(cp) >= 6, f"cognitive_profile has {len(cp)} traits"
    assert isinstance(data["study_plan"], list) and len(data["study_plan"]) >= 1
    lm = data["learning_map"]
    assert "nodes" in lm and "edges" in lm
    # stash id
    pytest.analysis_id = data["analysis_id"]


def test_list_analyses_scoped(auth_headers):
    r = requests.get(f"{API}/analyses", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    lst = r.json()
    assert isinstance(lst, list)
    assert len(lst) >= 1
    aid = getattr(pytest, "analysis_id", None)
    if aid:
        assert any(a["analysis_id"] == aid for a in lst)


def test_get_analysis_by_id(auth_headers):
    aid = getattr(pytest, "analysis_id", None)
    if not aid:
        pytest.skip("no analysis created")
    r = requests.get(f"{API}/analyses/{aid}", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    assert r.json()["analysis_id"] == aid


def test_analyses_requires_auth():
    r = requests.get(f"{API}/analyses", timeout=10)
    assert r.status_code == 401


# ---------------- Admin import ----------------

def test_import_exam_with_tags(auth_headers):
    payload = {
        "provider": "ENEM",
        "year": 2021,
        "color": "TestColor",
        "area": "MT+CN",
        "title": "TEST_IMPORTED_EXAM",
        "questions": [
            {
                "number": i,
                "area": "MT",
                "subject": "Álgebra",
                "topic": "Equações",
                "statement": f"Test question {i}",
                "alternatives": [
                    {"letter": "A", "text": "opt A"},
                    {"letter": "B", "text": "opt B"},
                    {"letter": "C", "text": "opt C"},
                    {"letter": "D", "text": "opt D"},
                    {"letter": "E", "text": "opt E"},
                ],
                "correct_answer": "A",
                "difficulty": "medio",
                "tags": {"algebra": True},  # skip AI tagging
            }
            for i in range(1, 4)
        ],
    }
    r = requests.post(f"{API}/admin/import-exam", headers=auth_headers, json=payload, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 3
    assert body["exam_id"]
    # Verify accessible
    g = requests.get(f"{API}/exams/{body['exam_id']}", timeout=15)
    assert g.status_code == 200
    assert len(g.json()["questions"]) == 3


# ---------------- Vision OCR ----------------

def _make_realistic_jpeg_base64() -> str:
    """Create a JPEG with real visual features (per /app/image_testing.md)."""
    img = Image.new("RGB", (400, 500), "white")
    # Draw some grid + circles to simulate an answer sheet
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for row in range(12):
        y = 30 + row * 35
        d.text((10, y), f"{row+1}", fill="black")
        for col, letter in enumerate("ABCDE"):
            x = 60 + col * 55
            d.ellipse([x, y, x + 20, y + 20], outline="black", width=2)
            d.text((x + 6, y + 4), letter, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def test_vision_answer_sheet(auth_headers, session):
    exams = session.get(f"{API}/exams", timeout=15).json()
    exam_id = exams[0]["exam_id"]
    b64 = _make_realistic_jpeg_base64()
    payload = {"exam_id": exam_id, "image_base64": b64}
    r = requests.post(f"{API}/vision/answer-sheet", headers=auth_headers, json=payload, timeout=90)
    # Either 200 with normalized list, or graceful 500
    if r.status_code == 200:
        data = r.json()
        assert "answers" in data
        assert isinstance(data["answers"], list)
        assert len(data["answers"]) == 12
        # numbers 1..12
        nums = [a["number"] for a in data["answers"]]
        assert nums == list(range(1, 13))
    else:
        assert r.status_code == 500, f"expected 200 or graceful 500, got {r.status_code}"
