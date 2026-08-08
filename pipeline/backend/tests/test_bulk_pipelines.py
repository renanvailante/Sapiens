"""Tests for POST /api/pipelines/bulk_get and /api/pipelines/bulk_delete.

Because the Emergent LLM budget is currently exhausted we bypass /pipeline/generate
and seed test pipelines directly into MongoDB, prefixed with TEST_.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _mkdoc(name: str) -> dict:
    pid = str(uuid.uuid4())
    return {
        "id": pid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ontology_version": "1.0.0-seed",
        "artifacts": {
            "originals": [{"filename": f"TEST_{name}.pdf", "path": "n/a", "content_type": "application/pdf", "size": 1}],
            "extraction": "n/a",
            "pipeline": "n/a",
        },
        "pipeline": {
            "questao": {"disciplina": "TEST", "tema": name, "resposta_correta": "B"},
            "classificacao": {"dominios": ["DOM-TEST"], "competencias": [], "processos_cognitivos": []},
        },
        "disciplina": "TEST",
        "tema": name,
        "processos": [],
        "competencias": [],
        "dominios": ["DOM-TEST"],
    }


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def two_ids():
    async def _seed():
        cli = AsyncIOMotorClient(MONGO_URL)
        db = cli[DB_NAME]
        docs = [_mkdoc("bulk_A"), _mkdoc("bulk_B")]
        await db.pipelines.insert_many(docs)
        cli.close()
        return [d["id"] for d in docs]

    ids = asyncio.get_event_loop().run_until_complete(_seed())
    yield ids

    async def _cleanup():
        cli = AsyncIOMotorClient(MONGO_URL)
        db = cli[DB_NAME]
        await db.pipelines.delete_many({"id": {"$in": ids}})
        cli.close()

    asyncio.get_event_loop().run_until_complete(_cleanup())


class TestBulkGet:
    def test_returns_in_order_ignoring_missing(self, s, two_ids):
        a, b = two_ids
        fake = str(uuid.uuid4())
        r = s.post(f"{API}/pipelines/bulk_get", json={"ids": [b, fake, a]}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert [d["id"] for d in data] == [b, a]
        assert "artifacts" in data[0] and "pipeline" in data[0]

    def test_empty_ids(self, s):
        r = s.post(f"{API}/pipelines/bulk_get", json={"ids": []}, timeout=30)
        assert r.status_code == 200
        assert r.json() == []

    def test_all_missing(self, s):
        r = s.post(
            f"{API}/pipelines/bulk_get",
            json={"ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
            timeout=30,
        )
        assert r.status_code == 200
        assert r.json() == []


class TestBulkDelete:
    def test_deletes_and_returns_count(self, s, two_ids):
        a, b = two_ids
        fake = str(uuid.uuid4())
        r = s.post(
            f"{API}/pipelines/bulk_delete",
            json={"ids": [a, b, fake]},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"deleted": 2}
        for pid in (a, b):
            assert s.get(f"{API}/pipeline/{pid}", timeout=30).status_code == 404

    def test_delete_empty_returns_zero(self, s):
        r = s.post(f"{API}/pipelines/bulk_delete", json={"ids": []}, timeout=30)
        assert r.status_code == 200
        assert r.json() == {"deleted": 0}
