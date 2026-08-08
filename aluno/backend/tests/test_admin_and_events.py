"""Iteration 7 backend tests — Admin role gate + Response Event Store.

Covers:
- ADMIN_EMAILS bootstrap (qa@sapiens.app auto-admin)
- 403 for non-admin on all /admin/* endpoints
- /admin/summary shape
- /admin/users list + PATCH promote/demote + self-demote guard
- Response event store: append-only, JOIN correctness, bulk, interventions,
  history aggregates, no mutation verbs, and access control.
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "qa@sapiens.app"
ADMIN_PASS = "qa12345"


# ----------------- helpers -----------------

def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _login_or_signup(email: str, password: str, name: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    if r.status_code == 200:
        return r.json()["token"]
    r = requests.post(f"{API}/auth/signup", json={"email": email, "password": password, "name": name}, timeout=15)
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login_or_signup(ADMIN_EMAIL, ADMIN_PASS, "QA")


@pytest.fixture(scope="module")
def admin_me(admin_token: str) -> dict:
    r = requests.get(f"{API}/auth/me", headers=_auth_headers(admin_token), timeout=15)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def student_ctx() -> dict:
    email = f"TEST_student_{uuid.uuid4().hex[:8]}@test.com"
    password = "pass1234"
    r = requests.post(f"{API}/auth/signup", json={"email": email, "password": password, "name": "Student"}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    return {"email": email, "token": data["token"], "user": data["user"]}


# ----------------- Admin role gate -----------------

class TestAdminRoleGate:
    def test_admin_login_is_admin_true(self, admin_me):
        assert admin_me["email"].lower() == ADMIN_EMAIL
        assert admin_me.get("is_admin") is True

    def test_non_admin_signup_is_admin_false(self, student_ctx):
        assert student_ctx["user"]["is_admin"] is False

    @pytest.mark.parametrize("method,path,body", [
        ("GET", "/admin/summary", None),
        ("POST", "/admin/annotations", {"item_id": "ITEM-X", "disciplina": "M"}),
        ("POST", "/admin/paste-answer-key", {"exam_year": 2022, "exam_variant": "AZUL", "raw_text": "1 A"}),
        ("POST", "/admin/feed-items", {"title": "x", "type": "reels", "body_markdown": "y"}),
    ])
    def test_non_admin_gets_403(self, student_ctx, method, path, body):
        r = requests.request(method, f"{API}{path}", headers=_auth_headers(student_ctx["token"]),
                             json=body, timeout=15)
        assert r.status_code == 403, f"{method} {path} expected 403 got {r.status_code}: {r.text}"

    def test_anon_gets_401(self):
        r = requests.get(f"{API}/admin/summary", timeout=15)
        assert r.status_code == 401


class TestAdminSummary:
    def test_summary_shape(self, admin_token):
        r = requests.get(f"{API}/admin/summary", headers=_auth_headers(admin_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        for k in ["exams", "answer_keys", "analyses_active", "analyses_trashed",
                  "users", "admins", "feed_items", "feed_items_published",
                  "annotations", "feed_interactions"]:
            assert k in data, f"missing {k}"
            assert isinstance(data[k], int)
        assert data["admins"] >= 1
        assert data["users"] >= 1


class TestAdminUsers:
    def test_list_users_includes_admin(self, admin_token):
        r = requests.get(f"{API}/admin/users", headers=_auth_headers(admin_token), timeout=15)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        qa = next((u for u in users if u["email"].lower() == ADMIN_EMAIL), None)
        assert qa is not None
        assert qa["is_admin"] is True

    def test_promote_and_demote_other_user(self, admin_token, student_ctx):
        uid = student_ctx["user"]["user_id"]
        r = requests.patch(f"{API}/admin/users/{uid}",
                           headers=_auth_headers(admin_token),
                           json={"is_admin": True}, timeout=15)
        assert r.status_code == 200
        assert r.json()["is_admin"] is True
        # GET to verify persisted
        r2 = requests.get(f"{API}/admin/users", headers=_auth_headers(admin_token), timeout=15)
        row = next(u for u in r2.json() if u["user_id"] == uid)
        assert row["is_admin"] is True
        # demote
        r = requests.patch(f"{API}/admin/users/{uid}",
                           headers=_auth_headers(admin_token),
                           json={"is_admin": False}, timeout=15)
        assert r.status_code == 200
        assert r.json()["is_admin"] is False

    def test_self_demote_returns_400(self, admin_token, admin_me):
        r = requests.patch(f"{API}/admin/users/{admin_me['user_id']}",
                           headers=_auth_headers(admin_token),
                           json={"is_admin": False}, timeout=15)
        assert r.status_code == 400
        assert "admin" in r.text.lower() or "próprio" in r.text.lower()


# ----------------- Response Event Store -----------------

ITEM_ID = "ITEM-ENEM-2022-MAT-137"


@pytest.fixture(scope="module")
def seeded_annotation(admin_token) -> dict:
    """Ensure a question_annotation exists for JOIN correctness tests."""
    payload = {
        "schema_version": "1.0",
        "item": {
            "id": ITEM_ID,
            "fonte": {"banca": "ENEM", "ano": 2022, "caderno": "AZUL", "numero": 137},
            "disciplina": "Matemática",
        },
        "payload": {
            "processos_ativados": ["raciocinio_logico", "modelagem"],
            "error_type_id": "err_001",
            "estrutura_cognitiva": {"nivel": "medio"},
        },
    }
    r = requests.post(f"{API}/admin/annotations", headers=_auth_headers(admin_token),
                      json=payload, timeout=20)
    assert r.status_code in (200, 201), r.text
    return payload


@pytest.fixture(scope="module")
def aluno_id() -> str:
    return f"TEST_aluno_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def attempt_id() -> str:
    return f"TEST_att_{uuid.uuid4().hex[:12]}"


class TestResponseEventAppend:
    def test_append_single_response(self, admin_token, aluno_id, attempt_id, seeded_annotation):
        body = {
            "attempt_id": attempt_id,
            "aluno_id": aluno_id,
            "turma": "TEST_3A",
            "item_id": ITEM_ID,
            "item_schema_version": "v1",
            "item_hash": "sha256:abc123",
            "contexto": {"origem": "simulado", "avaliacao_id": "AV1"},
            "data_hora_resposta": "2026-01-15T10:00:00+00:00",
            "alternativa_escolhida": "c",
            "acertou": True,
            "tempo_resposta_seg": 42.5,
            "status": "respondida",
            "metadata_tecnica": {"device": "web"},
        }
        r = requests.post(f"{API}/events/responses", headers=_auth_headers(admin_token),
                          json=body, timeout=15)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["evento_id"]
        assert doc["attempt_id"] == attempt_id
        assert doc["alternativa_escolhida"] == "C"  # normalized to upper
        assert doc["status"] == "respondida"
        assert "written_at" in doc
        # No cognitive fields duplicated in the event itself
        for forbidden in ("processos_ativados", "error_type_id", "estrutura_cognitiva", "disciplina"):
            assert forbidden not in doc, f"forbidden field {forbidden} present in event"

    def test_status_transition_same_attempt(self, admin_token, aluno_id, attempt_id):
        body = {
            "attempt_id": attempt_id,
            "aluno_id": aluno_id,
            "item_id": ITEM_ID,
            "item_schema_version": "v1",
            "item_hash": "sha256:abc123",
            "contexto": {"origem": "simulado"},
            "data_hora_resposta": "2026-01-15T10:05:00+00:00",
            "alternativa_escolhida": "C",
            "acertou": False,
            "tempo_resposta_seg": 0,
            "status": "anulada",
        }
        r = requests.post(f"{API}/events/responses", headers=_auth_headers(admin_token),
                          json=body, timeout=15)
        assert r.status_code == 200, r.text
        # Both should coexist
        r2 = requests.get(f"{API}/students/{aluno_id}/history",
                          headers=_auth_headers(admin_token), timeout=15)
        assert r2.status_code == 200
        data = r2.json()
        by_status = data["summary"]["by_status"]
        assert by_status.get("respondida", 0) >= 1
        assert by_status.get("anulada", 0) >= 1
        attempts = [r["event"]["attempt_id"] for r in data["responses"]]
        assert attempts.count(attempt_id) == 2

    @pytest.mark.parametrize("method", ["PATCH", "PUT", "DELETE"])
    def test_no_mutation_verbs(self, admin_token, method):
        # try both collection root and a fake id
        for path in ["/events/responses", "/events/responses/anything"]:
            r = requests.request(method, f"{API}{path}",
                                 headers=_auth_headers(admin_token),
                                 json={"x": 1}, timeout=15)
            assert r.status_code in (404, 405), f"{method} {path} -> {r.status_code}"

    def test_bulk_insert(self, admin_token, aluno_id):
        events = []
        for i in range(3):
            events.append({
                "aluno_id": aluno_id,
                "item_id": ITEM_ID,
                "item_schema_version": "v1",
                "item_hash": "sha256:bulk",
                "contexto": {"origem": "revisao"},
                "data_hora_resposta": f"2026-01-1{i}T10:00:00+00:00",
                "alternativa_escolhida": "A",
                "acertou": bool(i % 2),
                "tempo_resposta_seg": 10 + i,
                "status": "respondida",
            })
        r = requests.post(f"{API}/events/responses/bulk",
                          headers=_auth_headers(admin_token),
                          json={"events": events}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["inserted"] == 3


class TestInterventions:
    def test_intervention_creates_in_separate_collection(self, admin_token, aluno_id):
        body = {
            "aluno_id": aluno_id,
            "cognitive_process_id": "cp_raciocinio_logico",
            "tipo_intervencao": "video_micro",
            "data_hora_aplicacao": "2026-01-16T09:00:00+00:00",
            "aplicada_por": "sistema:auto",
        }
        r = requests.post(f"{API}/events/interventions",
                          headers=_auth_headers(admin_token),
                          json=body, timeout=15)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["evento_id"]
        # GET interventions returns it
        r2 = requests.get(f"{API}/events/interventions?aluno_id={aluno_id}",
                          headers=_auth_headers(admin_token), timeout=15)
        assert r2.status_code == 200
        data = r2.json()
        assert data["count"] >= 1
        # And it does NOT appear in /events/responses
        r3 = requests.get(f"{API}/events/responses?aluno_id={aluno_id}",
                          headers=_auth_headers(admin_token), timeout=15)
        assert r3.status_code == 200
        for r_ev in r3.json()["items"]:
            assert r_ev["event"].get("cognitive_process_id") is None


class TestJoinCorrectness:
    def test_history_joins_item_annotation(self, admin_token, aluno_id, seeded_annotation):
        r = requests.get(f"{API}/students/{aluno_id}/history",
                         headers=_auth_headers(admin_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data["responses"]) > 0
        first = data["responses"][0]
        assert first["item"] is not None
        assert first["item"]["disciplina"] == "Matemática"
        assert "processos_ativados" in first["item"]["payload"]
        # response event must NOT carry those fields
        ev = first["event"]
        for forbidden in ("processos_ativados", "error_type_id", "estrutura_cognitiva", "disciplina"):
            assert forbidden not in ev

    def test_filter_disciplina_and_origem(self, admin_token, aluno_id):
        r = requests.get(
            f"{API}/students/{aluno_id}/history",
            params={"disciplina": "Matemática", "origem": "simulado"},
            headers=_auth_headers(admin_token), timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        for row in data["responses"]:
            assert row["event"]["contexto"].get("origem") == "simulado"
            assert (row["item"] or {}).get("disciplina") == "Matemática"


class TestStudentsList:
    def test_list_students_shape(self, admin_token, aluno_id):
        r = requests.get(f"{API}/students", headers=_auth_headers(admin_token), timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        ours = next((x for x in rows if x["aluno_id"] == aluno_id), None)
        assert ours is not None
        assert ours["count"] >= 1
        assert "last_at" in ours
        # sorted desc by last_at
        last_ats = [x["last_at"] for x in rows if x.get("last_at")]
        assert last_ats == sorted(last_ats, reverse=True)


class TestEventsAccessControl:
    def test_events_read_non_admin_403(self, student_ctx):
        for path in ["/events/responses", "/events/interventions",
                     f"/students/anything/history", "/students"]:
            r = requests.get(f"{API}{path}", headers=_auth_headers(student_ctx["token"]), timeout=15)
            assert r.status_code == 403, f"{path} -> {r.status_code}"

    def test_events_anon_401(self):
        for path in ["/events/responses", "/events/interventions", "/students"]:
            r = requests.get(f"{API}{path}", timeout=15)
            assert r.status_code == 401, f"{path} -> {r.status_code}"

    def test_events_write_non_admin(self, student_ctx):
        """Review request says all /events/* require admin. Current code uses
        require_user for POSTs — expect 403 to enforce that contract."""
        body = {
            "aluno_id": "x", "item_id": ITEM_ID, "item_schema_version": "v1",
            "item_hash": "h", "data_hora_resposta": "2026-01-01T00:00:00+00:00",
            "alternativa_escolhida": "A", "acertou": True, "tempo_resposta_seg": 1,
        }
        r = requests.post(f"{API}/events/responses",
                          headers=_auth_headers(student_ctx["token"]),
                          json=body, timeout=15)
        assert r.status_code == 403, f"POST /events/responses non-admin -> {r.status_code}"


# ----------------- Regressions -----------------

class TestRegressions:
    def test_login_logout(self, admin_token):
        r = requests.get(f"{API}/auth/me", headers=_auth_headers(admin_token), timeout=15)
        assert r.status_code == 200

    def test_feed_public_endpoints(self, admin_token):
        r = requests.get(f"{API}/feed", headers=_auth_headers(admin_token), timeout=15)
        assert r.status_code == 200

    def test_analyses_list(self, admin_token):
        r = requests.get(f"{API}/analyses", headers=_auth_headers(admin_token), timeout=15)
        assert r.status_code == 200

    def test_annotation_get(self, admin_token):
        r = requests.get(f"{API}/annotations/{ITEM_ID}",
                         headers=_auth_headers(admin_token), timeout=15)
        assert r.status_code == 200
        assert r.json()["item_id"] == ITEM_ID
