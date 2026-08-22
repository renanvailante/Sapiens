"""Cognitive annotation ingestion + read endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ValidationError

from auth import require_admin, require_user
from annotation_models import AnnotationPayload, AnnotationRecord
import annotation_service
from canonical_ontology import normalize_item, validate_item
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
    """Monta o registro a partir do item 2.2 recebido.

    A validação canônica é **registrada, nunca bloqueante**, por exigência do
    corpus: `EXT-WP1-1.0`, item L13, lista "ler a regra 1 como proibição de
    armazenamento" entre os riscos de reintrodução indevida — "o item pode ser
    armazenado; não pode ser exposto ao motor. A distinção é o que permite
    ingestão em massa com enriquecimento posterior."

    O que protege a camada de crença é `qualidade.apto_para_camada_de_crenca`
    (L13b), não a recusa de ingestão.
    """
    raw = payload.model_dump()
    try:
        # A derivação de domínios/competências e o `item_hash` são mecânicos:
        # aplicados aqui em vez de exigidos do remetente.
        raw = normalize_item(raw)
        validacao = validate_item(raw)
    except Exception as exc:  # noqa: BLE001
        validacao = {"valid": None, "errors": [f"validação indisponível: {exc}"], "warnings": []}
    fonte = raw.get("fonte") or {}
    return AnnotationRecord(
        item_id=raw.get("item_id"),
        schema_version=raw.get("schema_version"),
        ontology_version=raw.get("ontology_version"),
        item_hash=raw.get("item_hash"),
        banca=fonte.get("banca"),
        ano=fonte.get("ano"),
        prova=fonte.get("prova"),
        numero=fonte.get("numero"),
        disciplina=fonte.get("disciplina"),
        payload=raw,
        validacao=validacao,
    ).model_dump()


class BulkAnnotationRequest(BaseModel):
    items: list[dict[str, Any]]


@router.post("/admin/annotations")
async def upsert_annotation(payload: dict[str, Any], admin: User = Depends(require_admin)):
    """Ingere UM item anotado no Schema Sapiens 2.2.

    Valida a forma mínima, guarda o payload VERBATIM e faz upsert por `item_id`
    — que é estável por contrato, o que torna a reingestão idempotente.
    """
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
    return {
        "ok": True,
        "item_id": record["item_id"],
        "schema_version": record["schema_version"],
        "ontology_version": record["ontology_version"],
        "validacao": record["validacao"],
    }


@router.post("/admin/annotations/bulk")
async def upsert_bulk(request: BulkAnnotationRequest, admin: User = Depends(require_admin)):
    ok, errors, invalidos = 0, [], []
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
        if record["validacao"] and record["validacao"].get("valid") is False:
            invalidos.append({"index": i, "item_id": record["item_id"],
                              "errors": record["validacao"]["errors"]})
    return {"imported": ok, "errors": errors, "invalidos_contra_o_catalogo": invalidos}


@router.delete("/admin/annotations/{item_id}")
async def delete_annotation(item_id: str, admin: User = Depends(require_admin)):
    res = await _db.question_annotations.delete_one({"item_id": item_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return {"ok": True}


@router.get("/annotations")
async def list_annotations(
    banca: str | None = None,
    ano: int | None = None,
    disciplina: str | None = None,
    prova: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    user: User = Depends(require_user),
):
    q: dict[str, Any] = {}
    if banca: q["banca"] = banca
    if ano: q["ano"] = ano
    if disciplina: q["disciplina"] = disciplina
    if prova: q["prova"] = prova
    items = await annotation_service.list_annotations(q, limit)
    total = await _db.question_annotations.count_documents(q)
    return {"items": items, "total": total}


@router.get("/annotations/{item_id}")
async def get_annotation(item_id: str, user: User = Depends(require_user)):
    doc = await annotation_service.find_annotation_by_id(item_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return doc


@router.get("/annotations/by-question/{banca}/{ano}/{prova}/{numero}")
async def get_annotation_by_question(banca: str, ano: int, prova: str, numero: int, user: User = Depends(require_user)):
    doc = await annotation_service.find_annotation_for_question(banca, ano, prova, numero)
    if not doc:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return doc


@router.get("/cognitive-profile")
async def cognitive_profile(user: User = Depends(require_user)):
    return await annotation_service.compute_cognitive_profile(user.user_id)
