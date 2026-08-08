"""Tests for the new ontology reset endpoint + multi-format import (PDF/DOCX/MD/TXT)."""
import io
import json
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
API = f"{BASE_URL}/api"

TXT_ONTOLOGY = (
    "DOMÍNIOS\n"
    "DOM-A - Álgebra: manipulação de expressões\n"
    "DOM-B - Geometria: figuras planas\n"
    "COMPETÊNCIAS\n"
    "COMP-01 - Resolver equação (DOM-A)\n"
    "PROCESSOS COGNITIVOS\n"
    "PROC-01 - Aplicar fórmula\n"
    "TIPOS DE ERRO\n"
    "ERR-01 - Erro algébrico\n"
    "INTERVENÇÕES\n"
    "INT-01 - Revisão\n"
)


@pytest.fixture(scope="module")
def s():
    return requests.Session()


class TestOntologyReset:
    def test_reset_endpoint_restores_seed(self, s):
        # First import a small custom ontology to switch active
        payload = {
            "version": "TEST-BEFORE-RESET",
            "dominios": [{"id": "DOM-X", "nome": "X", "descricao": "x"}],
            "competencias": [], "processos_cognitivos": [],
            "tipos_erro": [], "intervencoes_pedagogicas": [],
        }
        files = {"file": ("pre.json", json.dumps(payload).encode(), "application/json")}
        r = s.post(f"{API}/ontology/import", files=files, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["version"] == "TEST-BEFORE-RESET"

        # Now reset
        r = s.post(f"{API}/ontology/reset", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["version"] == "1.0.0-seed"
        assert d["counts"] == {
            "dominios": 8,
            "competencias": 16,
            "processos_cognitivos": 28,
            "tipos_erro": 13,
            "intervencoes_pedagogicas": 7,
        }

        # Summary confirms active seed
        r2 = s.get(f"{API}/ontology/summary", timeout=30)
        assert r2.status_code == 200
        assert r2.json()["version"] == "1.0.0-seed"


class TestOntologyImportGuards:
    def test_import_json_ok(self, s):
        payload = {
            "version": "TEST-JSON-OK",
            "dominios": [{"id": "DOM-A", "nome": "A", "descricao": "a"}],
        }
        files = {"file": ("ok.json", json.dumps(payload).encode(), "application/json")}
        r = s.post(f"{API}/ontology/import", files=files, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["version"] == "TEST-JSON-OK"
        assert d["counts"]["dominios"] == 1

    def test_import_empty_json_returns_400(self, s):
        payload = {"version": "TEST-EMPTY"}  # no elements
        files = {"file": ("empty.json", json.dumps(payload).encode(), "application/json")}
        r = s.post(f"{API}/ontology/import", files=files, timeout=60)
        assert r.status_code == 400, r.text
        assert "Nenhum elemento cognitivo encontrado" in r.json()["detail"]


class TestOntologyImportGemini:
    def test_import_txt_via_gemini(self, s):
        files = {"file": ("mini_ontology.txt", TXT_ONTOLOGY.encode("utf-8"), "text/plain")}
        r = s.post(f"{API}/ontology/import", files=files, timeout=300)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["counts"]["dominios"] >= 1
        assert d["counts"]["processos_cognitivos"] >= 1


class TestFinalReset:
    """Leave the seed 1.0.0-seed active for the user."""
    def test_final_reset(self, s):
        r = s.post(f"{API}/ontology/reset", timeout=60)
        assert r.status_code == 200
        assert r.json()["version"] == "1.0.0-seed"
