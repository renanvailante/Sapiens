"""Sapiens learning feed backend tests (iteration 3).

Covers:
- GET /api/feed pagination (cursor/limit, has_more, next_cursor)
- Feed item schema (flexible fields present)
- POST /api/feed/interactions (auth required, create + accumulate)
- GET/POST /api/feed/progress persistence
- completed=true auto-adds to progress.completed_content_ids
- Admin CRUD (create, patch, delete, unpublished not in /feed, auto sequence)
- Regression: /api/exams still returns >=2 seeded, login works, analyses trash filter
"""
from __future__ import annotations

import os
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

QA_EMAIL = "qa@sapiens.app"
QA_PASSWORD = "qa12345"
QA_NAME = "QA"


def _ensure_user(email: str, password: str, name: str) -> str:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code == 200:
        return r.json()["token"]
    r = s.post(f"{API}/auth/signup", json={"email": email, "name": name, "password": password}, timeout=30)
    assert r.status_code in (200, 201), f"signup failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def qa_token() -> str:
    return _ensure_user(QA_EMAIL, QA_PASSWORD, QA_NAME)


@pytest.fixture(scope="module")
def fresh_token() -> str:
    # Fresh user to test default progress
    email = f"feed_{uuid.uuid4().hex[:8]}@sapiens.app"
    return _ensure_user(email, "freshpass1", "Fresh User")


@pytest.fixture
def auth_client(qa_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {qa_token}"})
    return s


@pytest.fixture
def fresh_client(fresh_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {fresh_token}"})
    return s


# ---------- Feed listing / pagination ----------

class TestFeedListing:
    def test_default_page_returns_6_items(self):
        r = requests.get(f"{API}/feed", params={"cursor": 0, "limit": 6}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 6
        assert data["has_more"] is True
        assert data["next_cursor"] == data["items"][-1]["sequence_order"]
        # ensure ascending sequence_order
        seqs = [it["sequence_order"] for it in data["items"]]
        assert seqs == sorted(seqs)

    def test_pagination_cursor_middle_and_end(self):
        r = requests.get(f"{API}/feed", params={"cursor": 6, "limit": 6}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 6
        assert [it["sequence_order"] for it in data["items"]] == [7, 8, 9, 10, 11, 12]

        r2 = requests.get(f"{API}/feed", params={"cursor": 12, "limit": 6}, timeout=30)
        d2 = r2.json()
        # tolerate additional admin-created items beyond 15, but at least 3 (13,14,15)
        seqs = [it["sequence_order"] for it in d2["items"]]
        assert 13 in seqs and 14 in seqs and 15 in seqs
        # if only baseline 15 items exist, has_more should be False
        if len(d2["items"]) == 3:
            assert d2["has_more"] is False

    def test_limit_1(self):
        r = requests.get(f"{API}/feed", params={"cursor": 0, "limit": 1}, timeout=30)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_limit_over_30_rejected(self):
        r = requests.get(f"{API}/feed", params={"cursor": 0, "limit": 31}, timeout=30)
        assert r.status_code == 422

    def test_feed_item_flexible_schema(self):
        r = requests.get(f"{API}/feed", params={"cursor": 0, "limit": 3}, timeout=30)
        assert r.status_code == 200
        required = [
            "content_id", "content_type", "sequence_order",
            "question_data", "answer_options", "explanation_data",
            "multimedia_assets", "metadata", "cognitive_mapping_reference",
            "difficulty_reference", "learning_objectives", "background_theme",
            "published", "created_at",
        ]
        for item in r.json()["items"]:
            for field in required:
                assert field in item, f"missing field {field} in {item.get('content_id')}"
            # _id must NOT leak
            assert "_id" not in item


# ---------- Interactions ----------

class TestFeedInteractions:
    def test_interaction_requires_auth(self):
        r = requests.post(f"{API}/feed/interactions", json={"content_id": "x"}, timeout=30)
        assert r.status_code == 401

    def test_interaction_create_and_accumulate(self, auth_client):
        # pick a real content_id
        r = requests.get(f"{API}/feed", params={"cursor": 0, "limit": 1}, timeout=30)
        content_id = r.json()["items"][0]["content_id"]

        # First POST: creates
        p1 = auth_client.post(f"{API}/feed/interactions", json={
            "content_id": content_id,
            "time_spent_ms": 1500,
            "completed": False,
            "user_response": {"selected": "A"},
            "is_correct": False,
            "event": {"event": "answer", "value": "A"},
        }, timeout=30)
        assert p1.status_code == 200, p1.text

        # Second POST: same (user, content) -> UPDATE (accumulate + append event)
        p2 = auth_client.post(f"{API}/feed/interactions", json={
            "content_id": content_id,
            "time_spent_ms": 2500,
            "completed": True,
            "user_response": {"selected": "B"},
            "is_correct": True,
            "event": {"event": "complete"},
        }, timeout=30)
        assert p2.status_code == 200, p2.text

        # Verify via progress: completed_content_ids contains content_id
        prog = auth_client.get(f"{API}/feed/progress", timeout=30).json()
        assert content_id in prog["completed_content_ids"]

        # Third POST completing again should be idempotent for completed_ids (deduped via $addToSet)
        p3 = auth_client.post(f"{API}/feed/interactions", json={
            "content_id": content_id,
            "time_spent_ms": 100,
            "completed": True,
        }, timeout=30)
        assert p3.status_code == 200
        prog2 = auth_client.get(f"{API}/feed/progress", timeout=30).json()
        assert prog2["completed_content_ids"].count(content_id) == 1

    def test_interaction_unknown_content(self, auth_client):
        r = auth_client.post(f"{API}/feed/interactions", json={
            "content_id": "does-not-exist-xxx",
            "time_spent_ms": 0,
        }, timeout=30)
        assert r.status_code == 404


# ---------- Progress ----------

class TestFeedProgress:
    def test_progress_defaults_for_fresh_user(self, fresh_client):
        r = fresh_client.get(f"{API}/feed/progress", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["last_position"] == 0
        assert d["last_content_id"] is None
        assert d["completed_content_ids"] == []

    def test_progress_persistence(self, fresh_client):
        # get a valid content_id
        r = requests.get(f"{API}/feed", params={"cursor": 0, "limit": 1}, timeout=30)
        content_id = r.json()["items"][0]["content_id"]

        s = fresh_client.post(f"{API}/feed/progress", json={
            "last_position": 4, "last_content_id": content_id,
        }, timeout=30)
        assert s.status_code == 200

        g = fresh_client.get(f"{API}/feed/progress", timeout=30).json()
        assert g["last_position"] == 4
        assert g["last_content_id"] == content_id

    def test_progress_requires_auth(self):
        r = requests.get(f"{API}/feed/progress", timeout=30)
        assert r.status_code == 401


# ---------- Admin CRUD ----------

class TestAdminFeedItems:
    def test_create_patch_delete(self, auth_client):
        # Create with sequence_order=0 -> auto-assign (max+1)
        payload = {
            "content_type": "explanation",
            "sequence_order": 0,
            "question_data": {"prompt": "TEST admin item"},
            "explanation_data": {"text": "test"},
            "background_theme": "slate",
            "published": True,
        }
        c = auth_client.post(f"{API}/admin/feed-items", json=payload, timeout=30)
        assert c.status_code == 200, c.text
        created = c.json()
        assert created["sequence_order"] >= 16  # after baseline 15
        cid = created["content_id"]

        # Confirm it appears in /feed near the tail
        r = requests.get(f"{API}/feed", params={"cursor": created["sequence_order"] - 1, "limit": 5}, timeout=30)
        assert any(it["content_id"] == cid for it in r.json()["items"])

        # PATCH: toggle published to False + change sequence_order
        new_seq = created["sequence_order"] + 100
        p = auth_client.patch(f"{API}/admin/feed-items/{cid}",
                              json={"published": False, "sequence_order": new_seq}, timeout=30)
        assert p.status_code == 200

        # Unpublished must NOT appear in /feed
        r2 = requests.get(f"{API}/feed", params={"cursor": new_seq - 1, "limit": 5}, timeout=30)
        assert not any(it["content_id"] == cid for it in r2.json()["items"])

        # Admin list still contains it
        lst = auth_client.get(f"{API}/admin/feed-items", timeout=30).json()
        assert any(it["content_id"] == cid for it in lst)

        # DELETE
        d = auth_client.delete(f"{API}/admin/feed-items/{cid}", timeout=30)
        assert d.status_code == 200

        # Confirm gone from admin list
        lst2 = auth_client.get(f"{API}/admin/feed-items", timeout=30).json()
        assert not any(it["content_id"] == cid for it in lst2)

        # DELETE again -> 404
        d2 = auth_client.delete(f"{API}/admin/feed-items/{cid}", timeout=30)
        assert d2.status_code == 404

    def test_admin_requires_auth(self):
        r = requests.get(f"{API}/admin/feed-items", timeout=30)
        assert r.status_code == 401
        r2 = requests.post(f"{API}/admin/feed-items",
                           json={"content_type": "explanation"}, timeout=30)
        assert r2.status_code == 401


# ---------- Regression: existing endpoints untouched ----------

class TestRegression:
    def test_login_still_works(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": QA_EMAIL, "password": QA_PASSWORD}, timeout=30)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_exams_list(self):
        r = requests.get(f"{API}/exams", timeout=30)
        assert r.status_code == 200
        exams = r.json()
        assert isinstance(exams, list)
        assert len(exams) >= 2

    def test_analyses_trash_filter(self, auth_client):
        r_active = auth_client.get(f"{API}/analyses", timeout=30)
        assert r_active.status_code == 200
        r_trash = auth_client.get(f"{API}/analyses", params={"trash": "true"}, timeout=30)
        assert r_trash.status_code == 200
        assert isinstance(r_active.json(), list)
        assert isinstance(r_trash.json(), list)
