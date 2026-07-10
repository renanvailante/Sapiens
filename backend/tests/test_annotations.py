"""Cognitive annotation ingestion pipeline tests (iteration 4).

Covers:
- POST /api/admin/annotations single: happy path, idempotent upsert, extra-field preservation, shape errors (missing schema_version, missing item.id).
- POST /api/admin/annotations/bulk: partial success semantics.
- GET /api/annotations/{item_id}, /api/annotations/by-question/..., /api/annotations with filters.
- DELETE /api/admin/annotations/{item_id}.
- GET /api/cognitive-profile: auth gate, read-only invariant, process aggregation for a seeded ENEM 2023 Azul Q46 annotation.
- Regression: /api/feed, /api/feed/progress, /api/exams, /api/analyses (trash filter).
"""
from __future__ import annotations

import copy
import os
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

QA_EMAIL = "qa@sapiens.app"
QA_PASSWORD = "qa12345"
QA_NAME = "QA"


# ---------- helpers ----------

def _ensure_user(email: str, password: str, name: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code == 200:
        return r.json()["token"]
    r = requests.post(f"{API}/auth/signup", json={"email": email, "name": name, "password": password}, timeout=30)
    assert r.status_code in (200, 201), f"signup failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def qa_token() -> str:
    return _ensure_user(QA_EMAIL, QA_PASSWORD, QA_NAME)


@pytest.fixture
def auth_client(qa_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {qa_token}"})
    return s


def _base_payload(item_id: str, banca="ENEM", ano=2022, caderno="Azul", numero=137,
                  disciplina="Matemática", gabarito="C", process_id="RQ-CALC-007") -> dict:
    """Representative ENEM-2022-MAT-137 shape."""
    return {
        "schema_version": "1.0.0",
        "item": {
            "id": item_id,
            "fonte": {"banca": banca, "ano": ano, "caderno": caderno, "numero": numero},
            "disciplina": disciplina,
            "tema_objetivo": "Função afim aplicada",
            "conteudo_curricular": ["funcoes", "funcao_afim"],
            "enunciado": "Um técnico observa que o valor da tarifa...",
            "alternativas": [
                {"id": "A", "texto": "R$ 20,00"},
                {"id": "B", "texto": "R$ 40,00"},
                {"id": "C", "texto": "R$ 50,00"},
                {"id": "D", "texto": "R$ 60,00"},
                {"id": "E", "texto": "R$ 80,00"},
            ],
            "gabarito": gabarito,
        },
        "estrutura_cognitiva": {
            "nivel_abstracao": "concreto-operatorio",
            "carga_cognitiva": "media",
            "dificuldade_global": 0.55,
            "tipo_raciocinio_predominante": ["quantitativo"],
            "operacoes_cognitivas": ["modelagem", "calculo"],
        },
        "processos_ativados": [
            {
                "cognitive_process_id": process_id,
                "papel": "principal",
                "prioridade": 1,
                "peso_ativacao": 0.9,
                "confianca": 0.88,
                "dificuldade_local": 0.5,
                "evidencias": ["expressão linear", "duas condições"],
            }
        ],
        "analise_distratores": [
            {"alternativa": "A", "error_type_id": 12, "cognitive_process_falhou": ["RQ-CALC-007"],
             "explicacao": "Confundiu coeficiente angular"},
            {"alternativa": "D", "error_type_id": 5, "cognitive_process_falhou": [],
             "explicacao": "Erro aritmético"},
        ],
        "caracteristicas_item": {
            "possui_texto": True, "possui_tabela": False, "possui_grafico": False,
            "possui_imagem": False, "possui_formula": True, "contexto_cotidiano": True,
            "necessita_calculo": True, "necessita_estimativa": False,
        },
        "pedagogia": {
            "principal_intervencao": {"cognitive_process_id": process_id, "tipo": "worked_example"},
            "explicacao_resolucao": "Aplique y = ax + b com os dois pontos dados.",
            "misconceptions": ["confusao-coeficientes", "linearidade-espuria"],
        },
        "qualidade_anotacao": {
            "confianca_global": 0.92,
            "revisado_humano": True,
            "revisor": "annot-team",
            "data": "2024-11-01",
        },
    }


@pytest.fixture(scope="module")
def created_ids():
    ids: list[str] = []
    yield ids
    # Cleanup — best-effort, needs a token
    try:
        tok = _ensure_user(QA_EMAIL, QA_PASSWORD, QA_NAME)
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {tok}"})
        for iid in ids:
            s.delete(f"{API}/admin/annotations/{iid}", timeout=15)
    except Exception:
        pass


# ---------- POST /admin/annotations ----------

class TestUpsertSingle:
    def test_happy_path_enem_2022_mat_137(self, auth_client, created_ids):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        payload = _base_payload(item_id)
        r = auth_client.post(f"{API}/admin/annotations", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body == {"ok": True, "item_id": item_id, "schema_version": "1.0.0"}

    def test_idempotent_upsert(self, auth_client, created_ids):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        p = _base_payload(item_id, gabarito="C")
        r1 = auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)
        assert r1.status_code == 200
        p["item"]["gabarito"] = "D"  # change to prove update happened
        r2 = auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)
        assert r2.status_code == 200

        # Only one record in a filter that includes this banca/ano
        listing = auth_client.get(f"{API}/annotations", params={"banca": "ENEM", "ano": 2022}, timeout=30).json()
        matches = [x for x in listing["items"] if x["item_id"] == item_id]
        assert len(matches) == 1
        assert matches[0]["payload"]["item"]["gabarito"] == "D"

    def test_extra_fields_preserved(self, auth_client, created_ids):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        p = _base_payload(item_id)
        p["item"]["new_metadata"] = {"tags": ["novo"], "score": 42}
        p["qualidade_anotacao"]["extra_new_field"] = "future-value"
        p["totally_new_top_level"] = {"nested": True}
        p["processos_ativados"][0]["unknown_prop"] = [1, 2, 3]

        r = auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)
        assert r.status_code == 200, r.text

        got = auth_client.get(f"{API}/annotations/{item_id}", timeout=30).json()
        payload = got["payload"]
        assert payload["item"]["new_metadata"] == {"tags": ["novo"], "score": 42}
        assert payload["qualidade_anotacao"]["extra_new_field"] == "future-value"
        assert payload["totally_new_top_level"] == {"nested": True}
        assert payload["processos_ativados"][0]["unknown_prop"] == [1, 2, 3]

    def test_missing_schema_version_returns_400(self, auth_client):
        p = _base_payload(f"ITEM-TEST-{uuid.uuid4().hex[:8]}")
        p.pop("schema_version")
        r = auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)
        assert r.status_code == 400, r.text
        detail = r.json().get("detail", {})
        assert "validation" in detail
        assert any("schema_version" in str(err.get("loc", ())) for err in detail["validation"])

    def test_missing_item_id_returns_400(self, auth_client):
        p = _base_payload("dummy")
        del p["item"]["id"]
        r = auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)
        assert r.status_code == 400, r.text
        detail = r.json().get("detail", {})
        assert "validation" in detail
        locs = [tuple(err.get("loc", ())) for err in detail["validation"]]
        assert any("item" in loc and "id" in loc for loc in locs)

    def test_requires_auth(self):
        p = _base_payload(f"ITEM-TEST-{uuid.uuid4().hex[:8]}")
        r = requests.post(f"{API}/admin/annotations", json=p, timeout=30)
        assert r.status_code in (401, 403)


# ---------- POST /admin/annotations/bulk ----------

class TestBulk:
    def test_bulk_partial_success(self, auth_client, created_ids):
        good1 = _base_payload(f"ITEM-TEST-{uuid.uuid4().hex[:8]}")
        good2 = _base_payload(f"ITEM-TEST-{uuid.uuid4().hex[:8]}")
        bad = _base_payload(f"ITEM-TEST-{uuid.uuid4().hex[:8]}")
        bad.pop("schema_version")  # invalid
        created_ids.extend([good1["item"]["id"], good2["item"]["id"]])

        r = auth_client.post(f"{API}/admin/annotations/bulk",
                             json={"items": [good1, bad, good2]}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["imported"] == 2
        assert isinstance(body["errors"], list) and len(body["errors"]) == 1
        assert body["errors"][0]["index"] == 1
        assert isinstance(body["errors"][0]["detail"], list) and body["errors"][0]["detail"]

        # Confirm the two valid records were stored
        assert auth_client.get(f"{API}/annotations/{good1['item']['id']}", timeout=30).status_code == 200
        assert auth_client.get(f"{API}/annotations/{good2['item']['id']}", timeout=30).status_code == 200


# ---------- GET read endpoints ----------

class TestReads:
    def test_get_by_item_id_matches_payload(self, auth_client, created_ids):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        p = _base_payload(item_id)
        ingested = copy.deepcopy(p)
        auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)

        got = auth_client.get(f"{API}/annotations/{item_id}", timeout=30).json()
        # payload matches value-wise
        assert got["payload"]["schema_version"] == ingested["schema_version"]
        assert got["payload"]["item"] == ingested["item"]
        assert got["payload"]["processos_ativados"] == ingested["processos_ativados"]
        assert got["payload"]["analise_distratores"] == ingested["analise_distratores"]
        assert got["payload"]["pedagogia"] == ingested["pedagogia"]
        assert got["payload"]["qualidade_anotacao"] == ingested["qualidade_anotacao"]
        # top-level wrapper fields
        assert got["item_id"] == item_id
        assert got["banca"] == "ENEM" and got["ano"] == 2022 and got["caderno"] == "Azul" and got["numero"] == 137
        assert got["disciplina"] == "Matemática"
        assert got["schema_version"] == "1.0.0"

    def test_get_by_question_coordinate(self, auth_client, created_ids):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        p = _base_payload(item_id, ano=2022, caderno="Azul", numero=142)
        auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)

        r = auth_client.get(f"{API}/annotations/by-question/ENEM/2022/Azul/142", timeout=30)
        assert r.status_code == 200
        assert r.json()["item_id"] == item_id

        r404 = auth_client.get(f"{API}/annotations/by-question/ENEM/1900/Rosa/999", timeout=30)
        assert r404.status_code == 404

    def test_list_with_filters(self, auth_client, created_ids):
        # Seed 2 for ENEM 2022 Matemática
        ids = []
        for n in (150, 151):
            iid = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
            ids.append(iid); created_ids.append(iid)
            auth_client.post(f"{API}/admin/annotations",
                             json=_base_payload(iid, ano=2022, numero=n), timeout=30)

        r = auth_client.get(f"{API}/annotations",
                         params={"banca": "ENEM", "ano": 2022, "disciplina": "Matemática"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "total" in body
        assert isinstance(body["total"], int) and body["total"] >= 2
        got_ids = {x["item_id"] for x in body["items"]}
        assert set(ids).issubset(got_ids)
        # every item honors filters
        for x in body["items"]:
            assert x["banca"] == "ENEM"
            assert x["ano"] == 2022
            assert x["disciplina"] == "Matemática"


# ---------- Read endpoint auth gate (iteration 5 fix verification) ----------

class TestReadAuthGate:
    """Verifies main-agent fix: /annotations, /annotations/{item_id},
    /annotations/by-question/{banca}/{ano}/{caderno}/{numero} must require auth."""

    def test_list_annotations_requires_auth(self, auth_client, created_ids):
        # Seed one so list would otherwise return data
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        auth_client.post(f"{API}/admin/annotations", json=_base_payload(item_id), timeout=30)
        r = requests.get(f"{API}/annotations", params={"banca": "ENEM"}, timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 without token, got {r.status_code}"
        # And works with token
        r2 = auth_client.get(f"{API}/annotations", params={"banca": "ENEM"}, timeout=30)
        assert r2.status_code == 200

    def test_get_annotation_by_item_id_requires_auth(self, auth_client, created_ids):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        auth_client.post(f"{API}/admin/annotations", json=_base_payload(item_id), timeout=30)
        r = requests.get(f"{API}/annotations/{item_id}", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 without token, got {r.status_code}"
        r2 = auth_client.get(f"{API}/annotations/{item_id}", timeout=30)
        assert r2.status_code == 200

    def test_get_annotation_by_question_requires_auth(self, auth_client, created_ids):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        p = _base_payload(item_id, ano=2022, caderno="Azul", numero=161)
        auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)
        r = requests.get(f"{API}/annotations/by-question/ENEM/2022/Azul/161", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 without token, got {r.status_code}"
        r2 = auth_client.get(f"{API}/annotations/by-question/ENEM/2022/Azul/161", timeout=30)
        assert r2.status_code == 200


# ---------- DELETE ----------

class TestDelete:
    def test_delete_then_404(self, auth_client):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        auth_client.post(f"{API}/admin/annotations", json=_base_payload(item_id), timeout=30)
        assert auth_client.get(f"{API}/annotations/{item_id}", timeout=30).status_code == 200

        r = auth_client.delete(f"{API}/admin/annotations/{item_id}", timeout=30)
        assert r.status_code == 200 and r.json().get("ok") is True

        assert auth_client.get(f"{API}/annotations/{item_id}", timeout=30).status_code == 404
        # idempotency: deleting again -> 404
        assert auth_client.delete(f"{API}/admin/annotations/{item_id}", timeout=30).status_code == 404


# ---------- /cognitive-profile ----------

def _get_enem_2023_d1_azul():
    exams = requests.get(f"{API}/exams", timeout=30).json()
    return next(e for e in exams if e["year"] == 2023 and e["day"] == 1 and e["color"] == "Azul")


class TestCognitiveProfile:
    def test_requires_auth(self):
        r = requests.get(f"{API}/cognitive-profile", timeout=30)
        assert r.status_code in (401, 403)

    def test_shape_with_token(self, auth_client):
        r = auth_client.get(f"{API}/cognitive-profile", timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("processes", "error_types", "misconceptions", "coverage"):
            assert k in body

    def test_process_aggregation_for_enem_2023_azul_q46(self, auth_client, created_ids):
        exam = _get_enem_2023_d1_azul()

        # Ensure QA has an analysis on this exam answering everything "C"
        submit = auth_client.post(f"{API}/analyses", json={
            "exam_id": exam["exam_id"],
            "language": "english",
            "answers": [{"number": n, "letter": "C"} for n in range(1, 91)],
        }, timeout=180)
        assert submit.status_code == 200, submit.text
        analysis_id = submit.json()["analysis_id"]

        # Ingest an annotation for ENEM/2023/Azul/Q46 with RQ-PROP-003 gabarito C
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        p = _base_payload(item_id, banca="ENEM", ano=2023, caderno="Azul", numero=46,
                          disciplina="Matemática", gabarito="C", process_id="RQ-PROP-003")
        p["processos_ativados"][0]["peso_ativacao"] = 0.9
        r = auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)
        assert r.status_code == 200

        # Also ingest Q47 with same process but QA is wrong (gabarito D, QA marked C)
        item_id2 = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id2)
        p2 = _base_payload(item_id2, banca="ENEM", ano=2023, caderno="Azul", numero=47,
                           disciplina="Matemática", gabarito="D", process_id="RQ-PROP-003")
        p2["processos_ativados"][0]["peso_ativacao"] = 0.9
        # add error type for chosen "C"
        p2["analise_distratores"] = [{"alternativa": "C", "error_type_id": 99,
                                       "cognitive_process_falhou": ["RQ-PROP-003"],
                                       "explicacao": "chose C instead of D"}]
        auth_client.post(f"{API}/admin/annotations", json=p2, timeout=30)

        # Fetch profile
        prof = auth_client.get(f"{API}/cognitive-profile", timeout=60).json()
        pids = {p["cognitive_process_id"]: p for p in prof["processes"]}
        assert "RQ-PROP-003" in pids, f"process missing; got: {list(pids)[:10]}"
        entry = pids["RQ-PROP-003"]
        assert entry["encountered"] >= 2
        # weighted_accuracy present and numeric
        assert isinstance(entry["weighted_accuracy"], (int, float))
        # coverage fields exposed
        assert "matched_questions" in prof and "total_questions" in prof
        assert prof["matched_questions"] >= 2
        # error type 99 should be reflected (QA chose C, gabarito D)
        etids = {e["error_type_id"] for e in prof["error_types"]}
        assert 99 in etids

        # cleanup analysis to avoid growing state
        auth_client.delete(f"{API}/analyses/{analysis_id}", timeout=30)

    def test_read_only_invariant(self, auth_client, created_ids):
        item_id = f"ITEM-TEST-{uuid.uuid4().hex[:8]}"
        created_ids.append(item_id)
        p = _base_payload(item_id, banca="ENEM", ano=2023, caderno="Azul", numero=48,
                          process_id="RQ-RO-001")
        auth_client.post(f"{API}/admin/annotations", json=p, timeout=30)
        before = auth_client.get(f"{API}/annotations/{item_id}", timeout=30).json()

        for _ in range(5):
            r = auth_client.get(f"{API}/cognitive-profile", timeout=60)
            assert r.status_code == 200

        after = auth_client.get(f"{API}/annotations/{item_id}", timeout=30).json()
        assert before["payload"] == after["payload"]
        assert before["updated_at"] == after["updated_at"]
        assert before["received_at"] == after["received_at"]


# ---------- Regression ----------

class TestRegression:
    def test_feed_endpoint(self):
        r = requests.get(f"{API}/feed", params={"limit": 5}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body

    def test_feed_progress_requires_auth(self, auth_client):
        r = requests.get(f"{API}/feed/progress", timeout=30)
        assert r.status_code in (401, 403)
        r2 = auth_client.get(f"{API}/feed/progress", timeout=30)
        assert r2.status_code == 200

    def test_exams_still_seeded(self):
        r = requests.get(f"{API}/exams", timeout=30)
        assert r.status_code == 200
        exams = r.json()
        assert any(e["year"] == 2023 and e["day"] == 1 and e["color"] == "Azul" for e in exams)

    def test_analyses_trash_filter(self, auth_client):
        r = auth_client.get(f"{API}/analyses", timeout=30)
        assert r.status_code == 200
        r2 = auth_client.get(f"{API}/analyses", params={"trash": "true"}, timeout=30)
        assert r2.status_code == 200

    def test_auth_login_regression(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": QA_EMAIL, "password": QA_PASSWORD}, timeout=30)
        assert r.status_code == 200 and "token" in r.json()
