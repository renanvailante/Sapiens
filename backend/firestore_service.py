"""Firestore integration for Sapiens (backend-only).

Read:  pipeline/questao, pipeline/fonte, pipeline/config/behavior_schema
Write: students_behavior/students_id/{uid}/behavior_student

Does NOT use Firebase Auth. Existing Emergent Auth remains the only auth layer.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger("sapiens.firestore")

_FS_CLIENT = None


def _load_credentials() -> credentials.Certificate:
    raw_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    if raw_json:
        return credentials.Certificate(json.loads(raw_json))
    if path:
        return credentials.Certificate(path)
    raise RuntimeError(
        "Firebase credentials not configured. Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON."
    )


def get_firestore():
    """Return a cached Firestore client (lazy init)."""
    global _FS_CLIENT
    if _FS_CLIENT is not None:
        return _FS_CLIENT
    try:
        app = firebase_admin.get_app()
    except ValueError:
        options = {}
        if pid := os.environ.get("FIREBASE_PROJECT_ID"):
            options["projectId"] = pid
        app = firebase_admin.initialize_app(_load_credentials(), options=options)
        logger.info("Firebase Admin initialized for project=%s", app.project_id)
    _FS_CLIENT = firestore.client(app)
    return _FS_CLIENT


# ---------- Read helpers ----------

def read_collection(path: str, limit: int = 100) -> list[dict[str, Any]]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    docs = get_firestore().collection(path).limit(limit).stream()
    return [{"id": snap.id, **(snap.to_dict() or {})} for snap in docs]


def read_document(collection_path: str, document_id: str) -> Optional[dict[str, Any]]:
    snap = get_firestore().collection(collection_path).document(document_id).get()
    if not snap.exists:
        return None
    return {"id": snap.id, **(snap.to_dict() or {})}


# ---------- Student behavior (nested path) ----------

def _behavior_ref(uid: str):
    return (
        get_firestore()
        .collection("students_behavior")
        .document("students_id")
        .collection(uid)
        .document("behavior_student")
    )


def write_student_behavior(uid: str, data: dict[str, Any]) -> dict[str, Any]:
    ref = _behavior_ref(uid)
    ref.set(data, merge=True)
    return {"path": ref.path, **data}


def read_student_behavior(uid: str) -> Optional[dict[str, Any]]:
    snap = _behavior_ref(uid).get()
    if not snap.exists:
        return None
    return {"id": snap.id, **(snap.to_dict() or {})}


# ---------- Seed / provisioning ----------

def _initial_behavior_doc(uid: str, email: Optional[str] = None, name: Optional[str] = None) -> dict[str, Any]:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    return {
        "user_id": uid,
        "email": email,
        "name": name,
        "profile": {
            "reading_speed": None,
            "confidence_level": None,
            "attention_span": None,
            "error_pattern": None,
        },
        "stats": {
            "total_answered": 0,
            "total_correct": 0,
            "total_incorrect": 0,
            "avg_time_seconds": 0,
        },
        "flags": {
            "onboarded": False,
            "first_exam_done": False,
        },
        "events": [],
        "created_at": now,
        "updated_at": now,
    }


def ensure_student_behavior(uid: str, email: Optional[str] = None, name: Optional[str] = None) -> bool:
    """Create the behavior_student doc if it does not yet exist. Returns True if created."""
    ref = _behavior_ref(uid)
    if ref.get().exists:
        return False
    ref.set(_initial_behavior_doc(uid, email, name))
    return True


async def seed_all_students(mongo_db) -> dict[str, int]:
    """Idempotently create behavior docs for every non-admin user in MongoDB."""
    created = 0
    skipped = 0
    async for u in mongo_db.users.find({}, {"_id": 0, "user_id": 1, "email": 1, "name": 1, "is_admin": 1}):
        if u.get("is_admin"):
            skipped += 1
            continue
        try:
            if ensure_student_behavior(u["user_id"], u.get("email"), u.get("name")):
                created += 1
            else:
                skipped += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed_all_students failed for %s: %s", u.get("user_id"), exc)
    logger.info("Firestore student seed: created=%d skipped=%d", created, skipped)
    return {"created": created, "skipped": skipped}
