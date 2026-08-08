"""Tests for the Firestore sync layer.

Covers the four required scenarios:
1. Criar questão → Firestore criado
2. Editar questão → Firestore atualizado
3. Apagar questão → Firestore removido
4. sync_all_questions upserts + remove orphans (no duplicate ids)

Two suites:
* ``TestFirestoreSyncUnit``  → in-process unit tests of the sync module
                                (no HTTP, no LLM, no Mongo). Fast and isolated.
* ``TestFirestoreSyncHTTP``  → integration tests via the running FastAPI
                                server + real Mongo. Uses the sync endpoints
                                added to the API surface.

Uses the default in-memory MockFirestoreClient (FIRESTORE_MODE=mock).
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Make ``backend`` importable when pytest runs from /app.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _seed_doc(name: str) -> dict:
    pid = str(uuid.uuid4())
    return {
        "id": pid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ontology_version": "1.0.0-seed",
        "artifacts": {
            "originals": [
                {
                    "filename": f"TEST_{name}.pdf",
                    "path": "n/a",
                    "content_type": "application/pdf",
                    "size": 1,
                }
            ],
            "extraction": "n/a",
            "pipeline": "n/a",
        },
        "pipeline": {
            "questao": {
                "disciplina": "TEST",
                "tema": name,
                "resposta_correta": "B",
                "enunciado": f"Enunciado de teste {name}",
            },
            "classificacao": {
                "dominios": ["DOM-TEST"],
                "competencias": ["C1"],
                "processos_cognitivos": [{"id": "P1", "label": "analisar"}],
            },
        },
        "disciplina": "TEST",
        "tema": name,
        "banca": "TEST",
        "ano": "2026",
        "resposta_correta": "B",
        "processos": ["P1"],
        "competencias": ["C1"],
        "dominios": ["DOM-TEST"],
    }


async def _mongo_insert(doc: dict) -> None:
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.insert_one(doc)
    cli.close()


async def _mongo_update(pid: str, patch: dict) -> None:
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.update_one({"id": pid}, {"$set": patch})
    cli.close()


async def _mongo_delete(pid: str) -> None:
    cli = AsyncIOMotorClient(MONGO_URL)
    await cli[DB_NAME].pipelines.delete_one({"id": pid})
    cli.close()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(scope="module")
def s() -> requests.Session:
    return requests.Session()


# ===========================================================================
# UNIT TESTS — direct module usage (no HTTP)
# ===========================================================================
class TestFirestoreSyncUnit:
    """In-process tests of the sync layer against the MockFirestoreClient."""

    def setup_method(self) -> None:
        # Fresh mock between tests
        from firestore_sync import _reset_client_for_tests

        _reset_client_for_tests()

    def test_1_create_mirrors_and_strips_artifacts(self):
        """1. Criar questão → Firestore criado (mesmo id, sem artifacts)."""
        from firestore_sync import create_question_sync, peek_document

        doc = _seed_doc("unit_create")
        ok = create_question_sync(doc["id"], doc)

        assert ok is True
        mirror = peek_document(doc["id"])
        assert mirror is not None, "mirror deve existir após create"
        assert mirror["id"] == doc["id"], "ID espelhado deve ser idêntico (sem duplicação)"
        assert "artifacts" not in mirror, "artifacts DEVEM ser removidos (opção 4c)"
        assert "_id" not in mirror
        assert mirror["tema"] == "unit_create"
        assert mirror["pipeline"]["classificacao"]["dominios"] == ["DOM-TEST"]
        assert "_synced_at" in mirror

    def test_2_update_replaces_mirror(self):
        """2. Editar questão → Firestore atualizado."""
        from firestore_sync import (
            create_question_sync,
            update_question_sync,
            peek_document,
        )

        doc = _seed_doc("unit_update")
        assert create_question_sync(doc["id"], doc)

        updated = {**doc, "tema": "EDITED", "resposta_correta": "C"}
        assert update_question_sync(doc["id"], updated)

        mirror = peek_document(doc["id"])
        assert mirror["id"] == doc["id"], "ID não muda no update"
        assert mirror["tema"] == "EDITED"
        assert mirror["resposta_correta"] == "C"
        assert "artifacts" not in mirror

    def test_3_delete_removes_mirror(self):
        """3. Apagar questão → Firestore removido."""
        from firestore_sync import (
            create_question_sync,
            delete_question_sync,
            peek_document,
        )

        doc = _seed_doc("unit_delete")
        create_question_sync(doc["id"], doc)
        assert peek_document(doc["id"]) is not None

        assert delete_question_sync(doc["id"]) is True
        assert peek_document(doc["id"]) is None

        # delete is idempotent
        assert delete_question_sync(doc["id"]) is True

    def test_4_sync_all_upserts_and_removes_orphans(self):
        """4. sync_all_questions faz upsert e remove órfãos."""
        from firestore_sync import (
            create_question_sync,
            sync_all_questions,
            peek_document,
            list_mirrored_ids,
        )

        # An orphan lives in the mirror only (not in the "internal" list below)
        orphan = _seed_doc("orphan")
        create_question_sync(orphan["id"], orphan)

        # Real internal docs
        d1 = _seed_doc("realA")
        d2 = _seed_doc("realB")
        report = sync_all_questions([d1, d2])

        assert report["upserts"] == 2
        assert report["orphans_removed"] == 1
        assert report["internal_total"] == 2

        # Orphan gone, reals present, no duplicates
        assert peek_document(orphan["id"]) is None
        assert peek_document(d1["id"])["id"] == d1["id"]
        assert peek_document(d2["id"])["id"] == d2["id"]
        assert sorted(list_mirrored_ids()) == sorted([d1["id"], d2["id"]])

    def test_5_no_duplicate_ids_on_repeated_create(self):
        """Repeated create with same id must NOT create a second document."""
        from firestore_sync import (
            create_question_sync,
            peek_document,
            list_mirrored_ids,
        )

        doc = _seed_doc("dup")
        create_question_sync(doc["id"], doc)
        create_question_sync(doc["id"], {**doc, "tema": "v2"})

        ids = list_mirrored_ids()
        assert ids.count(doc["id"]) == 1
        assert peek_document(doc["id"])["tema"] == "v2"


# ===========================================================================
# HTTP INTEGRATION TESTS — real FastAPI + Mongo
# ===========================================================================
class TestFirestoreSyncHTTP:
    """Exercises CRUD endpoints and verifies the mirror via the API."""

    def test_status_endpoint(self, s):
        r = s.get(f"{API}/firestore/status", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] in ("mock", "admin")
        # Collection name is env-driven (FIRESTORE_COLLECTION). Just check it's set.
        assert isinstance(body["collection"], str) and body["collection"]
        assert "stats" in body and "retry_queue" in body

    def test_sync_all_then_delete_via_endpoint(self, s):
        """Full CRUD-through-sync happy path.

        Seeds a doc directly into Mongo (avoids LLM), then:
          - POST /firestore/sync-all → mirror created
          - GET  /firestore/document/{id} → 200 + no artifacts
          - DELETE /pipeline/{id} → mirror removed
          - GET  /firestore/document/{id} → 404 (no orphan)
        """
        doc = _seed_doc("http_flow")
        _run(_mongo_insert(doc))
        try:
            r = s.post(f"{API}/firestore/sync-all", timeout=30)
            assert r.status_code == 200, r.text
            assert r.json()["upserts"] >= 1

            r = s.get(f"{API}/firestore/document/{doc['id']}", timeout=30)
            assert r.status_code == 200, "mirror deveria existir após sync-all"
            mirror = r.json()
            assert mirror["id"] == doc["id"]
            assert "artifacts" not in mirror

            # Delete via CRUD → mirror must go
            r = s.delete(f"{API}/pipeline/{doc['id']}", timeout=30)
            assert r.status_code == 200
            assert r.json() == {"deleted": True, "id": doc["id"]}

            r = s.get(f"{API}/firestore/document/{doc['id']}", timeout=30)
            assert r.status_code == 404, "mirror deveria ser removido após delete"
        finally:
            _run(_mongo_delete(doc["id"]))
            s.post(f"{API}/firestore/sync-all", timeout=30)

    def test_update_via_mongo_then_resync_updates_mirror(self, s):
        """Simulates an edit flow that ends with sync-all (safer than /pipeline PUT
        which needs real artifact paths)."""
        doc = _seed_doc("http_update")
        _run(_mongo_insert(doc))
        try:
            s.post(f"{API}/firestore/sync-all", timeout=30)
            r = s.get(f"{API}/firestore/document/{doc['id']}", timeout=30)
            assert r.status_code == 200
            assert r.json()["tema"] == "http_update"

            _run(
                _mongo_update(
                    doc["id"],
                    {"tema": "http_update_EDITED", "resposta_correta": "D"},
                )
            )
            s.post(f"{API}/firestore/sync-all", timeout=30)

            r = s.get(f"{API}/firestore/document/{doc['id']}", timeout=30)
            assert r.status_code == 200
            mirror = r.json()
            assert mirror["id"] == doc["id"], "ID preservado (sem duplicação)"
            assert mirror["tema"] == "http_update_EDITED"
            assert mirror["resposta_correta"] == "D"
        finally:
            _run(_mongo_delete(doc["id"]))
            s.post(f"{API}/firestore/sync-all", timeout=30)

    def test_bulk_delete_removes_all_mirrors(self, s):
        docs = [_seed_doc("bulk1"), _seed_doc("bulk2")]
        for d in docs:
            _run(_mongo_insert(d))
        try:
            s.post(f"{API}/firestore/sync-all", timeout=30)
            for d in docs:
                assert (
                    s.get(f"{API}/firestore/document/{d['id']}", timeout=30).status_code == 200
                )

            r = s.post(
                f"{API}/pipelines/bulk_delete",
                json={"ids": [d["id"] for d in docs]},
                timeout=30,
            )
            assert r.status_code == 200
            assert r.json() == {"deleted": 2}

            for d in docs:
                assert (
                    s.get(f"{API}/firestore/document/{d['id']}", timeout=30).status_code == 404
                )
        finally:
            for d in docs:
                _run(_mongo_delete(d["id"]))

    def test_sync_all_removes_orphans_via_http(self, s):
        """After a doc is deleted directly from Mongo, sync-all should clean
        the corresponding orphan in the Firestore mirror."""
        doc = _seed_doc("http_orphan")
        _run(_mongo_insert(doc))
        s.post(f"{API}/firestore/sync-all", timeout=30)
        assert s.get(f"{API}/firestore/document/{doc['id']}", timeout=30).status_code == 200

        # Delete directly from Mongo (bypassing the CRUD sync) to leave an orphan
        _run(_mongo_delete(doc["id"]))

        r = s.post(f"{API}/firestore/sync-all", timeout=30)
        assert r.status_code == 200
        assert r.json()["orphans_removed"] >= 1

        assert s.get(f"{API}/firestore/document/{doc['id']}", timeout=30).status_code == 404
