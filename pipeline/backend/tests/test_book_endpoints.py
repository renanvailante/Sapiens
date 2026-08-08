"""Tests for the new /api/book endpoints (caderno mode).

Covers:
- POST /api/book/upload happy path + rejects invalid extension.
- GET /api/book/{book_id} shows manifest:null before manifest step.
- POST /api/book/{id}/manifest returns 404 for unknown id.
- POST /api/book/{id}/process returns 404 for unknown id.

Manifest + process require the LLM (EMERGENT_LLM_KEY); if the LLM call fails
(budget exhausted or 5xx) we only assert the endpoint reached the model layer
by ensuring the HTTP status is either 200 (real success) or 502 (upstream LLM
error) — a 500 or exception would signal a code bug.
"""
import io
import os
import uuid

import pytest
import requests
from reportlab.pdfgen import canvas

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def small_pdf():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Helvetica", 12)
    c.drawString(72, 780, "Prova ENEM - Caderno Amarelo")
    c.drawString(72, 760, "Q1) Qual o valor de 2 + 2? A)3 B)4 C)5 D)6 E)7  (Gab: B)")
    c.drawString(72, 740, "Q2) Capital do Brasil? A)SP B)RJ C)Brasilia D)MG E)PR  (Gab: C)")
    c.showPage()
    c.save()
    return buf.getvalue()


class TestBookUpload:
    def test_upload_creates_book_with_manifest_null(self, s, small_pdf):
        files = {"files": ("prova.pdf", small_pdf, "application/pdf")}
        r = s.post(f"{API}/book/upload", files=files, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d and isinstance(d["id"], str)
        assert "files" in d and len(d["files"]) == 1
        assert d["files"][0]["filename"] == "prova.pdf"
        assert d["manifest"] is None
        assert "created_at" in d
        # persistence check
        g = s.get(f"{API}/book/{d['id']}", timeout=30)
        assert g.status_code == 200
        assert g.json()["id"] == d["id"]
        assert g.json()["manifest"] is None
        # store for downstream
        TestBookUpload.book_id = d["id"]

    def test_upload_rejects_invalid_ext(self, s):
        files = {"files": ("bad.txt", b"hello world", "text/plain")}
        r = s.post(f"{API}/book/upload", files=files, timeout=30)
        assert r.status_code == 400
        assert "não suportada" in r.json()["detail"].lower() or "supor" in r.json()["detail"].lower()

    def test_upload_rejects_empty(self, s):
        r = s.post(f"{API}/book/upload", timeout=30)
        # FastAPI returns 422 when required field is missing
        assert r.status_code in (400, 422)


class TestBookNotFound:
    def test_manifest_unknown_id_returns_404(self, s):
        fake = str(uuid.uuid4())
        r = s.post(f"{API}/book/{fake}/manifest", timeout=30)
        assert r.status_code == 404

    def test_process_unknown_id_returns_404(self, s):
        fake = str(uuid.uuid4())
        r = s.post(
            f"{API}/book/{fake}/process",
            json={"question_number": "1", "question_title": "x"},
            timeout=30,
        )
        assert r.status_code == 404

    def test_get_unknown_id_returns_404(self, s):
        fake = str(uuid.uuid4())
        r = s.get(f"{API}/book/{fake}", timeout=30)
        assert r.status_code == 404


class TestBookLLMFlow:
    """These call the real LLM. Accept 200 (success) OR 502 (upstream LLM budget)."""

    def test_manifest_call_returns_200_or_502(self, s, small_pdf):
        # Ensure we have a book
        files = {"files": ("prova2.pdf", small_pdf, "application/pdf")}
        up = s.post(f"{API}/book/upload", files=files, timeout=60).json()
        r = s.post(f"{API}/book/{up['id']}/manifest", timeout=300)
        assert r.status_code in (200, 502), r.text
        if r.status_code == 200:
            data = r.json()
            assert data["book_id"] == up["id"]
            assert isinstance(data["manifest"], list)
            # confirm persistence
            g = s.get(f"{API}/book/{up['id']}").json()
            assert g["manifest"] is not None
            TestBookLLMFlow._book_id = up["id"]
            TestBookLLMFlow._manifest = data["manifest"]
        else:
            pytest.skip("LLM budget/upstream failure — manifest cannot be exercised.")

    def test_process_creates_pipeline_linked_to_book(self, s):
        book_id = getattr(TestBookLLMFlow, "_book_id", None)
        manifest = getattr(TestBookLLMFlow, "_manifest", None)
        if not book_id or not manifest:
            pytest.skip("Manifest step did not succeed.")
        q = manifest[0]
        r = s.post(
            f"{API}/book/{book_id}/process",
            json={"question_number": str(q.get("numero", "1")), "question_title": q.get("titulo", "")},
            timeout=300,
        )
        assert r.status_code in (200, 502), r.text
        if r.status_code != 200:
            pytest.skip("LLM upstream failure on process.")
        d = r.json()
        assert d["book_id"] == book_id
        assert d["question_number"] == str(q.get("numero", "1"))
        assert "pipeline" in d and "questao" in d["pipeline"]
        # cleanup pipeline
        s.post(f"{API}/pipelines/bulk_delete", json={"ids": [d["id"]]})
