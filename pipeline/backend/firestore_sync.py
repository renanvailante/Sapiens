"""Firestore synchronization layer.

The internal MongoDB collection ``pipelines`` is the SOURCE OF TRUTH for
questions. This module provides a thin sync layer that keeps a mirror in
Firestore (collection ``pipelines``) using the SAME UUID as the document id.

Design goals
------------
* **No duplicate ids.** Firestore documents always reuse the internal ``id``.
* **No orphan records.** ``sync_all_questions`` upserts every internal doc AND
  removes Firestore docs that no longer exist internally.
* **Base interna nunca falha por causa do Firestore.** Errors from the
  Firestore layer are logged and pushed into an in-memory retry queue; the
  caller (CRUD endpoint) succeeds regardless.
* **Pluggable backend.** Default backend is an in-memory ``MockFirestoreClient``
  for tests / preview; switching to Firebase Admin SDK only requires setting
  ``FIRESTORE_MODE=admin`` and providing credentials (see
  ``FirebaseAdminFirestoreClient``).

Public API
----------
* ``create_question_sync(question_id, data)``
* ``update_question_sync(question_id, data)``
* ``delete_question_sync(question_id)``
* ``sync_all_questions(all_docs)``
* ``get_status()``
"""

from __future__ import annotations

import copy
import logging
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Iterable

logger = logging.getLogger("firestore_sync")
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COLLECTION_NAME = os.environ.get("FIRESTORE_COLLECTION", "pipelines")
FIRESTORE_MODE = os.environ.get("FIRESTORE_MODE", "mock").lower()

# Fields we DO NOT mirror. Storage paths only make sense inside the internal
# object storage; MongoDB internal `_id` should never leak either.
EXCLUDED_FIELDS = {"artifacts", "_id"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_payload(question_id: str, data: dict) -> dict:
    """Prepare an internal record for Firestore mirroring.

    * Enforces the same id (``question_id``).
    * Strips excluded fields (``artifacts``, Mongo ``_id``).
    * Deep-copies to avoid mutating the caller's dict.
    * Stamps ``_synced_at`` for auditability.
    """
    clean = copy.deepcopy(data)
    for field in EXCLUDED_FIELDS:
        clean.pop(field, None)
    clean["id"] = question_id
    clean["_synced_at"] = _now_iso()
    return clean


# ---------------------------------------------------------------------------
# Client interface
# ---------------------------------------------------------------------------
class FirestoreClient(ABC):
    """Minimal interface that any Firestore backend must implement."""

    @abstractmethod
    def set(self, doc_id: str, data: dict) -> None: ...

    @abstractmethod
    def update(self, doc_id: str, data: dict) -> None: ...

    @abstractmethod
    def delete(self, doc_id: str) -> None: ...

    @abstractmethod
    def get(self, doc_id: str) -> dict | None: ...

    @abstractmethod
    def list_ids(self) -> list[str]: ...

    @abstractmethod
    def clear(self) -> None: ...


class MockFirestoreClient(FirestoreClient):
    """In-memory Firestore stand-in used for tests and the preview build.

    Thread-safe; behaves like ``firestore.Client().collection(COLLECTION).document(id)``:
    * ``set`` fully replaces the document
    * ``update`` merges (shallow) with existing content
    * ``delete`` is idempotent (no-op if missing)
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._lock = threading.RLock()

    def set(self, doc_id: str, data: dict) -> None:
        with self._lock:
            self._store[doc_id] = copy.deepcopy(data)

    def update(self, doc_id: str, data: dict) -> None:
        with self._lock:
            if doc_id not in self._store:
                # Firestore's `update` raises when the doc is missing; we
                # log-and-upsert to mimic the *intended* semantics of the sync
                # layer (base interna já mutou → espelho deve refletir).
                logger.warning(
                    "MockFirestore update on missing doc %s; performing upsert.",
                    doc_id,
                )
                self._store[doc_id] = copy.deepcopy(data)
                return
            self._store[doc_id].update(copy.deepcopy(data))

    def delete(self, doc_id: str) -> None:
        with self._lock:
            self._store.pop(doc_id, None)

    def get(self, doc_id: str) -> dict | None:
        with self._lock:
            v = self._store.get(doc_id)
            return copy.deepcopy(v) if v is not None else None

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class FirebaseAdminFirestoreClient(FirestoreClient):
    """Production backend backed by ``firebase-admin`` + ``google-cloud-firestore``.

    Requirements:
    * ``FIRESTORE_MODE=admin``
    * ``GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json``
    * ``FIRESTORE_COLLECTION`` (defaults to ``pipelines`` — currently set to
      ``itens`` in this project).

    Idempotent: uses ``document(doc_id).set(...)`` which creates or replaces
    the document with the SAME id every time. ``update`` uses ``.set(..., merge=True)``
    to align with the sync-layer semantics (source of truth = MongoDB).
    """

    def __init__(self) -> None:
        import firebase_admin
        from firebase_admin import credentials as _fb_credentials
        from firebase_admin import firestore as _fb_firestore

        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not cred_path or not os.path.isfile(cred_path):
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS não aponta para um JSON de "
                "service account existente. Defina no .env para usar "
                "FIRESTORE_MODE=admin."
            )

        # firebase_admin.initialize_app is a singleton — guard against
        # re-initialization when uvicorn reloads.
        if not firebase_admin._apps:  # noqa: SLF001
            cred = _fb_credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        self._db = _fb_firestore.client()
        self._col = self._db.collection(COLLECTION_NAME)
        logger.info(
            "FirebaseAdminFirestoreClient initialized (project=%s, collection=%s)",
            self._db.project,
            COLLECTION_NAME,
        )

    def set(self, doc_id: str, data: dict) -> None:
        self._col.document(doc_id).set(data)

    def update(self, doc_id: str, data: dict) -> None:
        # merge=True para não apagar campos que o Mongo não mandou
        self._col.document(doc_id).set(data, merge=True)

    def delete(self, doc_id: str) -> None:
        self._col.document(doc_id).delete()

    def get(self, doc_id: str) -> dict | None:
        snap = self._col.document(doc_id).get()
        if not snap.exists:
            return None
        d = snap.to_dict() or {}
        d.setdefault("id", doc_id)
        return d

    def list_ids(self) -> list[str]:
        # stream() is lazy; list-comprehension coerces to list of ids
        return [doc.id for doc in self._col.stream()]

    def clear(self) -> None:
        # Batched delete, 500 per batch (Firestore limit)
        batch = self._db.batch()
        count = 0
        for doc in self._col.list_documents():
            batch.delete(doc)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = self._db.batch()
        if count % 500 != 0:
            batch.commit()


# ---------------------------------------------------------------------------
# Module-level singleton + retry queue
# ---------------------------------------------------------------------------
_client: FirestoreClient | None = None
_retry_queue: list[dict] = []
_retry_lock = threading.RLock()
_stats = {
    "creates_ok": 0,
    "updates_ok": 0,
    "deletes_ok": 0,
    "failures": 0,
    "last_sync_all_at": None,
    "last_sync_all_result": None,
}


def _build_client() -> FirestoreClient:
    if FIRESTORE_MODE == "admin":  # pragma: no cover
        return FirebaseAdminFirestoreClient()
    return MockFirestoreClient()


def get_client() -> FirestoreClient:
    """Lazy singleton getter (main and tests share the same instance)."""
    global _client
    if _client is None:
        _client = _build_client()
        logger.info(
            "Firestore sync initialized (mode=%s, collection=%s)",
            FIRESTORE_MODE,
            COLLECTION_NAME,
        )
    return _client


def _reset_client_for_tests() -> None:
    """Test helper — clear both the client store and stats/queue."""
    global _client
    if _client is not None:
        _client.clear()
    with _retry_lock:
        _retry_queue.clear()
    _stats.update(
        creates_ok=0,
        updates_ok=0,
        deletes_ok=0,
        failures=0,
        last_sync_all_at=None,
        last_sync_all_result=None,
    )


def _enqueue_retry(op: str, doc_id: str, payload: dict | None, err: str) -> None:
    with _retry_lock:
        _retry_queue.append(
            {
                "op": op,
                "id": doc_id,
                "payload": payload,
                "error": err,
                "queued_at": _now_iso(),
            }
        )


# ---------------------------------------------------------------------------
# Public sync API
# ---------------------------------------------------------------------------
def create_question_sync(question_id: str, data: dict) -> bool:
    """Mirror an internal question into Firestore.

    Returns True on success, False on failure (failure is logged and queued for
    retry; the caller MUST NOT rollback the internal write — base interna é
    fonte de verdade).
    """
    payload = _sanitize_payload(question_id, data)
    try:
        get_client().set(question_id, payload)
        _stats["creates_ok"] += 1
        logger.info("Firestore CREATE ok id=%s collection=%s", question_id, COLLECTION_NAME)
        return True
    except Exception as exc:  # noqa: BLE001
        _stats["failures"] += 1
        logger.exception("Firestore CREATE failed id=%s: %s", question_id, exc)
        _enqueue_retry("create", question_id, payload, str(exc))
        return False


def update_question_sync(question_id: str, data: dict) -> bool:
    """Mirror an update. Uses ``set`` semantics (full replace) to guarantee the
    Firestore document ends up identical to the internal one — the specified
    behavior for a source-of-truth mirror.
    """
    payload = _sanitize_payload(question_id, data)
    try:
        get_client().set(question_id, payload)
        _stats["updates_ok"] += 1
        logger.info("Firestore UPDATE ok id=%s", question_id)
        return True
    except Exception as exc:  # noqa: BLE001
        _stats["failures"] += 1
        logger.exception("Firestore UPDATE failed id=%s: %s", question_id, exc)
        _enqueue_retry("update", question_id, payload, str(exc))
        return False


def delete_question_sync(question_id: str) -> bool:
    """Remove the mirrored document. Idempotent (missing doc → success)."""
    try:
        get_client().delete(question_id)
        _stats["deletes_ok"] += 1
        logger.info("Firestore DELETE ok id=%s", question_id)
        return True
    except Exception as exc:  # noqa: BLE001
        _stats["failures"] += 1
        logger.exception("Firestore DELETE failed id=%s: %s", question_id, exc)
        _enqueue_retry("delete", question_id, None, str(exc))
        return False


def sync_all_questions(all_docs: Iterable[dict]) -> dict:
    """Full re-sync (5a): upsert every internal doc AND delete Firestore docs
    that have no internal counterpart.

    ``all_docs`` must be an iterable of dicts containing at least ``id``.
    Returns a report with counts.
    """
    client = get_client()
    internal_ids: set[str] = set()
    upserts = 0
    upsert_failures = 0

    for doc in all_docs:
        qid = doc.get("id")
        if not qid:
            logger.warning("sync_all: skipping doc without id: %r", doc)
            continue
        internal_ids.add(qid)
        try:
            client.set(qid, _sanitize_payload(qid, doc))
            upserts += 1
        except Exception as exc:  # noqa: BLE001
            upsert_failures += 1
            logger.exception("sync_all upsert failed id=%s: %s", qid, exc)
            _enqueue_retry("create", qid, doc, str(exc))

    orphan_ids = [i for i in client.list_ids() if i not in internal_ids]
    orphans_removed = 0
    orphan_failures = 0
    for oid in orphan_ids:
        try:
            client.delete(oid)
            orphans_removed += 1
            logger.info("sync_all removed orphan id=%s", oid)
        except Exception as exc:  # noqa: BLE001
            orphan_failures += 1
            logger.exception("sync_all delete orphan failed id=%s: %s", oid, exc)
            _enqueue_retry("delete", oid, None, str(exc))

    result = {
        "collection": COLLECTION_NAME,
        "mode": FIRESTORE_MODE,
        "internal_total": len(internal_ids),
        "upserts": upserts,
        "upsert_failures": upsert_failures,
        "orphans_removed": orphans_removed,
        "orphan_failures": orphan_failures,
        "completed_at": _now_iso(),
    }
    _stats["last_sync_all_at"] = result["completed_at"]
    _stats["last_sync_all_result"] = result
    logger.info("sync_all completed: %s", result)
    return result


def get_status() -> dict:
    """Introspection helper used by ``/api/firestore/status`` and tests."""
    client = get_client()
    with _retry_lock:
        queue_snapshot = list(_retry_queue)
    return {
        "mode": FIRESTORE_MODE,
        "collection": COLLECTION_NAME,
        "mirrored_count": len(client.list_ids()),
        "retry_queue_size": len(queue_snapshot),
        "retry_queue": queue_snapshot[-20:],  # last 20
        "stats": dict(_stats),
    }


def peek_document(doc_id: str) -> dict | None:
    """Read-only helper (used by tests and the status endpoint)."""
    return get_client().get(doc_id)


def list_mirrored_ids() -> list[str]:
    return get_client().list_ids()


__all__ = [
    "create_question_sync",
    "update_question_sync",
    "delete_question_sync",
    "sync_all_questions",
    "get_status",
    "peek_document",
    "list_mirrored_ids",
    "MockFirestoreClient",
    "FirebaseAdminFirestoreClient",
    "COLLECTION_NAME",
    "FIRESTORE_MODE",
]
