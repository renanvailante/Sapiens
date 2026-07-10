"""Cognitive annotation ingestion + read endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ValidationError

from auth import require_user
from annotation_models import AnnotationPayload, AnnotationRecord
import annotation_service
from models import User

router = APIRouter(prefix="", tags=["annotations"])

_db = None
def set_db(db):
    global _db
    _db = db
    annotation_service.set_db(db)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_from_payload(payload: AnnotationPayload) -> dict:
    raw = payload.model_dump()
    item = raw.get("item") or {}
    fonte = item.get("fonte") or {}
    return AnnotationRecord(
        item_id=item.get("id"),
        schema_version=raw.get("schema_version"),
        banca=fonte.get("banca"),
        ano=fonte.get("ano"),
        caderno=fonte.get("caderno"),
        numero=fonte.get("numero"),
        disciplina=item.get("disciplina"),
        payload=raw,
    ).model_dump()


class BulkAnnotationRequest(BaseModel):
    items: list[dict[str, Any]]


@router.post("/admin/annotations")
async def upsert_annotation(payload: dict[str, Any], user: User = Depends(require_user)):
    """Ingest one annotation. Validates minimum shape, stores payload VERBATIM.
    Upserts by `item.id`."""
    try:
        parsed = AnnotationPayload.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={"validation": e.errors()})
    record = _record_from_payload(parsed)
    record["updated_at"] = _now()
    record.pop("received_at", None)  # avoid conflict with $setOnInsert
    await _db.question_annotations.update_one(
        {"item_id": record["item_id"]},
        {"$set": record, "$setOnInsert": {"received_at": _now()}},
        upsert=True,
    )
    return {"ok": True, "item_id": record["item_id"], "schema_version": record["schema_version"]}


@router.post("/admin/annotations/bulk")
async def upsert_bulk(request: BulkAnnotationRequest, user: User = Depends(require_user)):
    ok, errors = 0, []
    for i, raw in enumerate(request.items):
        try:
            parsed = AnnotationPayload.model_validate(raw)
        except ValidationError as e:
            errors.append({"index": i, "detail": e.errors()})
            continue
        record = _record_from_payload(parsed)
        record["updated_at"] = _now()
        record.pop("received_at", None)
        await _db.question_annotations.update_one(
            {"item_id": record["item_id"]},
            {"$set": record, "$setOnInsert": {"received_at": _now()}},
            upsert=True,
        )
        ok += 1
    return {"imported": ok, "errors": errors}


@router.delete("/admin/annotations/{item_id}")
async def delete_annotation(item_id: str, user: User = Depends(require_user)):
    res = await _db.question_annotations.delete_one({"item_id": item_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return {"ok": True}


@router.get("/annotations")
async def list_annotations(
    banca: str | None = None,
    ano: int | None = None,
    disciplina: str | None = None,
    caderno: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
):
    q: dict[str, Any] = {}
    if banca: q["banca"] = banca
    if ano: q["ano"] = ano
    if disciplina: q["disciplina"] = disciplina
    if caderno: q["caderno"] = caderno
    items = await annotation_service.list_annotations(q, limit)
    total = await _db.question_annotations.count_documents(q)
    return {"items": items, "total": total}


@router.get("/annotations/{item_id}")
async def get_annotation(item_id: str):
    doc = await annotation_service.find_annotation_by_id(item_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return doc


@router.get("/annotations/by-question/{banca}/{ano}/{caderno}/{numero}")
async def get_annotation_by_question(banca: str, ano: int, caderno: str, numero: int):
    doc = await annotation_service.find_annotation_for_question(banca, ano, caderno, numero)
    if not doc:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return doc


@router.get("/cognitive-profile")
async def cognitive_profile(user: User = Depends(require_user)):
    return await annotation_service.compute_cognitive_profile(user.user_id)
