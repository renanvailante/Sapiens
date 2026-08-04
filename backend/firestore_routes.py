"""FastAPI routes for Firestore-backed pipeline & student behavior.

All routes are protected by the EXISTING Emergent Auth (`auth.require_user`).
No Firebase Authentication is used.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import require_user, require_admin
from models import User
import firestore_service as fs

logger = logging.getLogger("sapiens.firestore.routes")

router = APIRouter(prefix="/firestore", tags=["firestore"])


class BehaviorPayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict, description="Arbitrary behavior fields; merged into behavior_student doc.")


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Firestore call failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Firestore error: {exc}")


# ---------- Reads: pipeline ----------

@router.get("/pipeline/questao")
async def list_questoes(limit: int = Query(100, ge=1, le=500), _: User = Depends(require_user)):
    return {"items": _safe_call(fs.read_collection, "pipeline/questao", limit)}


@router.get("/pipeline/questao/{doc_id}")
async def get_questao(doc_id: str, _: User = Depends(require_user)):
    doc = _safe_call(fs.read_document, "pipeline/questao", doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Questao not found")
    return doc


@router.get("/pipeline/fonte")
async def list_fontes(limit: int = Query(100, ge=1, le=500), _: User = Depends(require_user)):
    return {"items": _safe_call(fs.read_collection, "pipeline/fonte", limit)}


@router.get("/pipeline/fonte/{doc_id}")
async def get_fonte(doc_id: str, _: User = Depends(require_user)):
    doc = _safe_call(fs.read_document, "pipeline/fonte", doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Fonte not found")
    return doc


# ---------- Config: behavior_schema ----------

@router.get("/pipeline/config/behavior-schema")
async def get_behavior_schema(limit: int = Query(100, ge=1, le=500), _: User = Depends(require_user)):
    return {"items": _safe_call(fs.read_collection, "pipeline/config/behavior_schema", limit)}


# ---------- Student behavior ----------

@router.get("/students/me/behavior")
async def get_my_behavior(user: User = Depends(require_user)):
    # Auto-provision on first access — no Firebase Auth involved.
    _safe_call(fs.ensure_student_behavior, user.user_id, user.email, user.name)
    doc = _safe_call(fs.read_student_behavior, user.user_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Behavior document not found")
    return doc


@router.post("/students/me/ensure")
async def ensure_my_behavior(user: User = Depends(require_user)):
    """Idempotently create the student's behavior_student document.
    Called by the frontend on every successful login/session load. No Firebase Auth used —
    the caller is authenticated via the existing Emergent Auth (require_user).
    """
    created = _safe_call(fs.ensure_student_behavior, user.user_id, user.email, user.name)
    doc = _safe_call(fs.read_student_behavior, user.user_id)
    return {"created": created, "user_id": user.user_id, "path": f"students_behavior/students_id/{user.user_id}/behavior_student", "doc": doc}


@router.put("/students/me/behavior")
async def upsert_my_behavior(payload: BehaviorPayload, user: User = Depends(require_user)):
    return _safe_call(fs.write_student_behavior, user.user_id, payload.data)


# Admin-only: access by arbitrary uid (e.g. teacher/admin viewing a student)
@router.get("/students/{uid}/behavior")
async def get_behavior_by_uid(uid: str, _: User = Depends(require_admin)):
    doc = _safe_call(fs.read_student_behavior, uid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Behavior document not found")
    return doc
