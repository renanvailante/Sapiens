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

_db = None


def set_db(db):
    global _db
    _db = db


class AnswerPayload(BaseModel):
    item_id: str
    alternativa_escolhida: str
    tempo_resposta_segundos: float = 0
    numero_tentativas: int = 1
    mudou_resposta: bool = False
    contexto_tipo: str = "pratica_questoes"
    prova_id: Optional[str] = None
    dispositivo: Optional[str] = None
    versao_aplicacao: Optional[str] = None


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
    # Nova estrutura (Fase 1): cria students/{uid} (profile) no login se não existir.
    _safe_call(fs.ensure_student_profile, user.user_id, user.name, user.email)
    created = _safe_call(fs.ensure_student_behavior, user.user_id, user.email, user.name)
    doc = _safe_call(fs.read_student_behavior, user.user_id)
    return {"created": created, "user_id": user.user_id, "path": f"students_behavior/students_id/{user.user_id}/behavior_student", "doc": doc}


@router.put("/students/me/behavior")
async def upsert_my_behavior(payload: BehaviorPayload, user: User = Depends(require_user)):
    return _safe_call(fs.write_student_behavior, user.user_id, payload.data)


@router.post("/students/me/answer")
async def register_answer(payload: AnswerPayload, user: User = Depends(require_user)):
    """Registra a resposta do aluno a uma questão (Fase 2).
    Determina certo/errado no servidor a partir de 'questoes_public' e grava o
    evento de behavior (schema 1.0) em students/{uid}/behavior via Fase 1.
    Retorna apenas certo/errado (sem feedback qualitativo — isso é a Fase 3).
    """
    doc = await _db.questoes_public.find_one({"item_id": payload.item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    questao = doc.get("questao") or {}
    alternativas = questao.get("alternativas") or []
    correta_letra = next((a.get("letra") for a in alternativas if a.get("correta") is True), None)
    acertou = (payload.alternativa_escolhida == correta_letra) if correta_letra is not None else None

    # Garante o profile (Fase 1) antes de gravar na subcoleção behavior.
    _safe_call(fs.ensure_student_profile, user.user_id, user.name, user.email)
    _safe_call(
        fs.write_behavior_event,
        user.user_id,
        item_id=payload.item_id,
        alternativa_escolhida=payload.alternativa_escolhida,
        acertou=acertou,
        item_schema_version=doc.get("item_schema_version"),
        item_content=questao,
        contexto_tipo=payload.contexto_tipo,
        prova_id=payload.prova_id,
        tempo_resposta_segundos=payload.tempo_resposta_segundos,
        numero_tentativas=payload.numero_tentativas,
        mudou_resposta=payload.mudou_resposta,
        dispositivo=payload.dispositivo,
        versao_aplicacao=payload.versao_aplicacao,
    )
    return {"acertou": acertou, "correta": correta_letra}


# Admin-only: access by arbitrary uid (e.g. teacher/admin viewing a student)
@router.get("/students/{uid}/behavior")
async def get_behavior_by_uid(uid: str, _: User = Depends(require_admin)):
    doc = _safe_call(fs.read_student_behavior, uid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Behavior document not found")
    return doc
