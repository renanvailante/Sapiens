"""End-to-end backend tests for Sapiens Cognitive Annotator."""
import io
import json
import os
import time
import pytest
import requests
from reportlab.pdfgen import canvas

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
           "https://view-preview-14.preview.emergentagent.com"
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def sample_pdf():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Helvetica", 12)
    c.drawString(72, 780, "ENEM - Questao 1")
    c.drawString(72, 760, "Qual o valor de 2 + 2?")
    c.drawString(72, 740, "A) 3   B) 4   C) 5   D) 6   E) 7")
    c.drawString(72, 720, "Gabarito: B")
    c.showPage()
    c.save()
    return buf.getvalue()


# ---------------- Ontology ----------------
class TestOntology:
    def test_get_ontology(self, s):
        r = s.get(f"{API}/ontology", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["version"] == "1.0.0-seed"
        assert len(d["dominios"]) == 8
        assert len(d["competencias"]) == 16
        assert len(d["processos_cognitivos"]) == 28
        assert len(d["tipos_erro"]) == 13
        assert len(d["intervencoes_pedagogicas"]) == 7

    def test_ontology_summary(self, s):
        r = s.get(f"{API}/ontology/summary", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["version"] == "1.0.0-seed"
        assert d["source_filename"] == "seed_default.json"
        assert d["counts"]["dominios"] == 8
        assert d["counts"]["processos_cognitivos"] == 28

    def test_stats(self, s):
        r = s.get(f"{API}/stats", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "total_pipelines" in d
        assert d["ontology"]["version"] == "1.0.0-seed"

    def test_import_and_reactivate_seed(self, s):
        payload = {
            "version": "TEST-1.0",
            "dominios": [{"id": "DOM-TEST", "nome": "Teste", "descricao": "x"}],
            "competencias": [], "processos_cognitivos": [],
            "tipos_erro": [], "intervencoes_pedagogicas": [],
        }
        files = {"file": ("test_ontology.json", json.dumps(payload).encode(), "application/json")}
        r = s.post(f"{API}/ontology/import", files=files, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["version"] == "TEST-1.0"

        r2 = s.get(f"{API}/ontology", timeout=30)
        assert r2.json()["version"] == "TEST-1.0"

        # find seed id and re-activate
        versions = s.get(f"{API}/ontology/versions", timeout=30).json()
        seed = next(v for v in versions if v["version"] == "1.0.0-seed")
        r3 = s.post(f"{API}/ontology/activate/{seed['id']}", timeout=30)
        assert r3.status_code == 200
        assert r3.json()["version"] == "1.0.0-seed"


# ---------------- Pipeline ----------------
PIPELINE_ID = {}


class TestPipeline:
    def test_generate_pipeline(self, s, sample_pdf):
        files = {"files": ("q1.pdf", sample_pdf, "application/pdf")}
        r = s.post(f"{API}/pipeline/generate", files=files, timeout=300)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d
        assert "artifacts" in d
        assert "originals" in d["artifacts"]
        assert "extraction" in d["artifacts"]
        assert "pipeline" in d["artifacts"]
        pj = d["pipeline"]
        assert "questao" in pj and "classificacao" in pj

        # ontology IDs only
        ontology = s.get(f"{API}/ontology").json()
        valid_dom = {x["id"] for x in ontology["dominios"]}
        valid_comp = {x["id"] for x in ontology["competencias"]}
        valid_proc = {x["id"] for x in ontology["processos_cognitivos"]}
        cl = pj["classificacao"]
        for d_id in cl.get("dominios", []):
            assert d_id in valid_dom, f"invalid dominio id: {d_id}"
        for c_id in cl.get("competencias", []):
            assert c_id in valid_comp, f"invalid competencia id: {c_id}"
        for p in cl.get("processos_cognitivos", []):
            assert p["id"] in valid_proc, f"invalid processo id: {p['id']}"
            assert p.get("papel") in ("nuclear", "secundario", "facilitador")
        PIPELINE_ID["id"] = d["id"]

    def test_list_pipelines(self, s):
        r = s.get(f"{API}/pipelines", timeout=30)
        assert r.status_code == 200
        assert any(p["id"] == PIPELINE_ID.get("id") for p in r.json())

    def test_list_pipelines_with_filter(self, s):
        # Filter with an obviously wrong dominio -> should be empty
        r = s.get(f"{API}/pipelines?dominio=DOM-DOESNOTEXIST", timeout=30)
        assert r.status_code == 200
        assert r.json() == []

    def test_get_pipeline(self, s):
        pid = PIPELINE_ID["id"]
        r = s.get(f"{API}/pipeline/{pid}", timeout=30)
        assert r.status_code == 200
        assert r.json()["id"] == pid

    def test_get_artifact_original(self, s):
        pid = PIPELINE_ID["id"]
        r = s.get(f"{API}/pipeline/{pid}/artifact/original", timeout=60)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_get_artifact_extraction(self, s):
        pid = PIPELINE_ID["id"]
        r = s.get(f"{API}/pipeline/{pid}/artifact/extraction", timeout=60)
        assert r.status_code == 200
        assert "questao" in r.json()

    def test_get_artifact_pipeline(self, s):
        pid = PIPELINE_ID["id"]
        r = s.get(f"{API}/pipeline/{pid}/artifact/pipeline", timeout=60)
        assert r.status_code == 200
        assert "classificacao" in r.json()

    def test_update_pipeline(self, s):
        pid = PIPELINE_ID["id"]
        current = s.get(f"{API}/pipeline/{pid}").json()
        pj = current["pipeline"]
        pj.setdefault("questao", {})["tema"] = "Novo tema"
        r = s.put(f"{API}/pipeline/{pid}", json={"pipeline": pj}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["tema"] == "Novo tema"
        # confirm persisted index
        r2 = s.get(f"{API}/pipeline/{pid}").json()
        assert r2["tema"] == "Novo tema"

    def test_delete_pipeline(self, s):
        pid = PIPELINE_ID["id"]
        r = s.delete(f"{API}/pipeline/{pid}", timeout=30)
        assert r.status_code == 200
        assert r.json()["deleted"] is True
        r2 = s.get(f"{API}/pipeline/{pid}", timeout=30)
        assert r2.status_code == 404


# regenerate: separate test that creates its own pipeline (delete above removed prior)
class TestRegenerate:
    def test_regenerate(self, s, sample_pdf):
        files = {"files": ("q2.pdf", sample_pdf, "application/pdf")}
        r = s.post(f"{API}/pipeline/generate", files=files, timeout=300)
        assert r.status_code == 200
        pid = r.json()["id"]
        try:
            r2 = s.post(f"{API}/pipeline/{pid}/regenerate", timeout=300)
            assert r2.status_code == 200
            assert r2.json()["id"] == pid
            assert "classificacao" in r2.json()["pipeline"]
        finally:
            s.delete(f"{API}/pipeline/{pid}", timeout=30)
