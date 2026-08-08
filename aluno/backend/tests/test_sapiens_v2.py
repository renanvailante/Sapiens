"""Sapiens v2 answer-key schema + recycle bin backend tests.

Covers:
- /api/exams (metadata only, no questions/alternatives leak)
- /api/exams/{id} (?language=english|spanish)
- /api/admin/paste-answer-key (create + upsert + invalid)
- /api/analyses (create independent attempts, list, get)
- /api/analyses/{id}/rename, /trash, /restore, DELETE
- Trash filtering (?trash=true)
- Auth enforcement (401 unauth, 404 for other-user or missing)
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

QA_EMAIL = "qa@sapiens.app"
QA_PASSWORD = "qa12345"
QA_NAME = "QA"


# ---------- Fixtures ----------

def _ensure_user(email: str, password: str, name: str) -> str:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code == 200:
        return r.json()["token"]
    r = s.post(f"{API}/auth/signup", json={"email": email, "name": name, "password": password}, timeout=30)
    assert r.status_code in (200, 201), f"signup failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def qa_token() -> str:
    return _ensure_user(QA_EMAIL, QA_PASSWORD, QA_NAME)


@pytest.fixture(scope="session")
def other_token() -> str:
    email = f"other_{uuid.uuid4().hex[:8]}@sapiens.app"
    return _ensure_user(email, "otherpass1", "Other User")


@pytest.fixture
def auth_client(qa_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {qa_token}"})
    return s


@pytest.fixture
def other_client(other_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {other_token}"})
    return s


# ---------- /api/exams ----------

class TestExams:
    def test_list_exams_metadata_only(self):
        r = requests.get(f"{API}/exams", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 2
        for exam in data:
            # Must NOT leak question letters/alternatives
            assert "questions" not in exam
            assert "answers" not in exam
            assert "answer_keys" not in exam
            assert "alternatives" not in exam
            # Required metadata
            for k in ("exam_id", "year", "day", "color", "total_questions", "has_english", "has_spanish"):
                assert k in exam, f"missing {k} in exam metadata"

    def test_seeded_exams_present(self):
        r = requests.get(f"{API}/exams", timeout=30)
        exams = r.json()
        d1 = [e for e in exams if e["year"] == 2023 and e["day"] == 1 and e["color"] == "Azul"]
        d2 = [e for e in exams if e["year"] == 2023 and e["day"] == 2 and e["color"] == "Azul"]
        assert len(d1) == 1 and d1[0]["has_english"] and d1[0]["has_spanish"]
        assert d1[0]["total_questions"] == 90
        assert len(d2) == 1 and d2[0]["has_english"] and not d2[0]["has_spanish"]
        assert d2[0]["total_questions"] == 90

    def test_get_exam_english(self):
        exams = requests.get(f"{API}/exams", timeout=30).json()
        d1 = next(e for e in exams if e["day"] == 1 and e["color"] == "Azul" and e["year"] == 2023)
        r = requests.get(f"{API}/exams/{d1['exam_id']}?language=english", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["language"] == "english"
        assert isinstance(body["numbers"], list) and len(body["numbers"]) == 90
        # numbers should be integers only, no letters
        assert all(isinstance(n, int) for n in body["numbers"])
        # exam metadata but no key letters
        assert "letter" not in str(body).lower() or True  # sanity; more explicit:
        assert "answers" not in body
        assert "letters" not in body

    def test_get_exam_spanish_when_available(self):
        exams = requests.get(f"{API}/exams", timeout=30).json()
        d1 = next(e for e in exams if e["day"] == 1 and e["color"] == "Azul" and e["year"] == 2023)
        r = requests.get(f"{API}/exams/{d1['exam_id']}?language=spanish", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["language"] == "spanish"
        assert len(body["numbers"]) == 90

    def test_get_exam_not_found(self):
        r = requests.get(f"{API}/exams/does-not-exist", timeout=30)
        assert r.status_code == 404


# ---------- /api/admin/paste-answer-key ----------

class TestPasteAnswerKey:
    SAMPLE_PASTE = (
        "QUESTÃO GABARITO\n"
        "INGLÊS ESPANHOL\n"
        "1 D B\n2 D A\n3 D D\n4 E D\n5 E E\n"
        "6 A\n7 B\n8 C\n9 D\n10 E\n"
    )

    def test_unauth(self):
        r = requests.post(
            f"{API}/admin/paste-answer-key",
            json={"year": 2099, "day": 1, "color": "Rosa", "raw_text": self.SAMPLE_PASTE},
            timeout=30,
        )
        assert r.status_code in (401, 403)

    def test_paste_creates_exam(self, auth_client):
        year = 2099
        color = f"Test-{uuid.uuid4().hex[:6]}"
        r = auth_client.post(
            f"{API}/admin/paste-answer-key",
            json={"year": year, "day": 1, "color": color, "raw_text": self.SAMPLE_PASTE},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 10
        assert body["english"] is True
        assert body["spanish"] is True  # rows 1-5 differ EN vs ES
        exam_id = body["exam_id"]

        # verify listed
        exams = requests.get(f"{API}/exams", timeout=30).json()
        found = [e for e in exams if e["exam_id"] == exam_id]
        assert found and found[0]["total_questions"] == 10 and found[0]["has_spanish"]

        # verify GET returns 10 numbers
        r = requests.get(f"{API}/exams/{exam_id}?language=english", timeout=30)
        assert r.status_code == 200 and len(r.json()["numbers"]) == 10

    def test_paste_upsert_same_key(self, auth_client):
        year = 2098
        color = f"Test-{uuid.uuid4().hex[:6]}"
        first = auth_client.post(
            f"{API}/admin/paste-answer-key",
            json={"year": year, "day": 1, "color": color, "raw_text": self.SAMPLE_PASTE},
            timeout=30,
        ).json()
        second = auth_client.post(
            f"{API}/admin/paste-answer-key",
            json={"year": year, "day": 1, "color": color, "raw_text": self.SAMPLE_PASTE},
            timeout=30,
        ).json()
        assert first["exam_id"] == second["exam_id"], "upsert should reuse exam_id"

    def test_paste_invalid_returns_400(self, auth_client):
        r = auth_client.post(
            f"{API}/admin/paste-answer-key",
            json={"year": 2097, "day": 1, "color": "None", "raw_text": "nothing parseable here\nfoo bar\n"},
            timeout=30,
        )
        assert r.status_code == 400


# ---------- /api/analyses attempts + recycle bin ----------

def _get_d1_exam_id() -> str:
    exams = requests.get(f"{API}/exams", timeout=30).json()
    return next(e for e in exams if e["day"] == 1 and e["color"] == "Azul" and e["year"] == 2023)["exam_id"]


def _submit_answers(client, exam_id, letters_by_number: dict[int, str]):
    payload = {
        "exam_id": exam_id,
        "language": "english",
        "answers": [{"number": n, "letter": l} for n, l in letters_by_number.items()],
    }
    return client.post(f"{API}/analyses", json=payload, timeout=180)


class TestAnalyses:
    def test_submit_requires_auth(self):
        exam_id = _get_d1_exam_id()
        r = requests.post(
            f"{API}/analyses",
            json={"exam_id": exam_id, "language": "english", "answers": []},
            timeout=30,
        )
        assert r.status_code in (401, 403)

    def test_two_submissions_create_independent_attempts(self, auth_client):
        exam_id = _get_d1_exam_id()
        # Build answers based on known D1 Azul sample
        answers = {n: "A" for n in range(1, 91)}

        r1 = _submit_answers(auth_client, exam_id, answers)
        assert r1.status_code == 200, r1.text
        a1 = r1.json()

        r2 = _submit_answers(auth_client, exam_id, answers)
        assert r2.status_code == 200, r2.text
        a2 = r2.json()

        assert a1["analysis_id"] != a2["analysis_id"], "each submission must create a new attempt"

        # Both listed
        listed = auth_client.get(f"{API}/analyses", timeout=30).json()
        ids = {a["analysis_id"] for a in listed}
        assert a1["analysis_id"] in ids and a2["analysis_id"] in ids

        # Fields validation
        for a in (a1, a2):
            assert a["total"] == 90
            assert isinstance(a["score"], int)
            assert isinstance(a["percent"], (int, float))
            assert isinstance(a["by_area"], dict) and len(a["by_area"]) >= 1
            # day 1 areas expected
            assert set(a["by_area"].keys()) & {"LC-Idioma", "LC", "CH"}
            assert a["diagnostic_headline"], "diagnostic_headline should be non-empty"
            assert a["diagnostic_body"], "diagnostic_body should be non-empty"
            assert isinstance(a["study_plan"], list)
            assert isinstance(a["learning_map"], dict)
            assert isinstance(a["cognitive_profile"], dict)

    def test_rename_trash_restore_delete_flow(self, auth_client):
        exam_id = _get_d1_exam_id()
        answers = {n: "B" for n in range(1, 91)}
        aid = _submit_answers(auth_client, exam_id, answers).json()["analysis_id"]

        # Rename
        r = auth_client.patch(f"{API}/analyses/{aid}/rename", json={"label": "My Try 1"}, timeout=30)
        assert r.status_code == 200 and r.json()["label"] == "My Try 1"
        got = auth_client.get(f"{API}/analyses/{aid}", timeout=30).json()
        assert got["label"] == "My Try 1"

        # Trash
        r = auth_client.post(f"{API}/analyses/{aid}/trash", timeout=30)
        assert r.status_code == 200
        main_list = auth_client.get(f"{API}/analyses", timeout=30).json()
        assert aid not in {a["analysis_id"] for a in main_list}
        trash_list = auth_client.get(f"{API}/analyses?trash=true", timeout=30).json()
        trashed = [a for a in trash_list if a["analysis_id"] == aid]
        assert trashed and trashed[0]["deleted"] is True and trashed[0]["deleted_at"]

        # Restore
        r = auth_client.post(f"{API}/analyses/{aid}/restore", timeout=30)
        assert r.status_code == 200
        got = auth_client.get(f"{API}/analyses/{aid}", timeout=30).json()
        assert got["deleted"] is False and got["deleted_at"] is None

        # Permanent delete
        r = auth_client.delete(f"{API}/analyses/{aid}", timeout=30)
        assert r.status_code == 200
        r = auth_client.get(f"{API}/analyses/{aid}", timeout=30)
        assert r.status_code == 404

    def test_ownership_and_missing_ids(self, auth_client, other_client):
        exam_id = _get_d1_exam_id()
        aid = _submit_answers(auth_client, exam_id, {n: "C" for n in range(1, 91)}).json()["analysis_id"]

        # Other user cannot see/modify
        assert other_client.get(f"{API}/analyses/{aid}", timeout=30).status_code == 404
        assert other_client.patch(f"{API}/analyses/{aid}/rename", json={"label": "hack"}, timeout=30).status_code == 404
        assert other_client.post(f"{API}/analyses/{aid}/trash", timeout=30).status_code == 404
        assert other_client.post(f"{API}/analyses/{aid}/restore", timeout=30).status_code == 404
        assert other_client.delete(f"{API}/analyses/{aid}", timeout=30).status_code == 404

        # Non-existent id
        fake = "does-not-exist-xyz"
        assert auth_client.get(f"{API}/analyses/{fake}", timeout=30).status_code == 404
        assert auth_client.patch(f"{API}/analyses/{fake}/rename", json={"label": "x"}, timeout=30).status_code == 404
        assert auth_client.post(f"{API}/analyses/{fake}/trash", timeout=30).status_code == 404
        assert auth_client.post(f"{API}/analyses/{fake}/restore", timeout=30).status_code == 404
        assert auth_client.delete(f"{API}/analyses/{fake}", timeout=30).status_code == 404

        # Unauth on protected endpoints
        assert requests.get(f"{API}/analyses", timeout=30).status_code in (401, 403)
        assert requests.get(f"{API}/analyses/{aid}", timeout=30).status_code in (401, 403)
        assert requests.patch(f"{API}/analyses/{aid}/rename", json={"label": "x"}, timeout=30).status_code in (401, 403)
        assert requests.post(f"{API}/analyses/{aid}/trash", timeout=30).status_code in (401, 403)
        assert requests.post(f"{API}/analyses/{aid}/restore", timeout=30).status_code in (401, 403)
        assert requests.delete(f"{API}/analyses/{aid}", timeout=30).status_code in (401, 403)
