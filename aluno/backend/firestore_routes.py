"""FastAPI routes for Firestore-backed pipeline & student behavior.

Todas as rotas sao protegidas pela sessao do proprio backend
(`auth.require_user`). Nao se usa Firebase Authentication.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from auth import require_user, require_admin
from models import User
import firestore_service as fs
from feedback_templates import build_feedback

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


class BehaviorProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reading_speed: Optional[str] = None
    confidence_level: Optional[str] = None
    attention_span: Optional[str] = None
    error_pattern: Optional[str] = None


class BehaviorFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")
    onboarded: Optional[bool] = None
    first_exam_done: Optional[bool] = None


class BehaviorPayload(BaseModel):
    """Only self-declared fields are writable by the student. Server-derived
    blocks (stats, events, identity) are never accepted from the client."""
    model_config = ConfigDict(extra="forbid")
    profile: Optional[BehaviorProfile] = None
    flags: Optional[BehaviorFlags] = None

    def to_update(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.profile:
            p = self.profile.model_dump(exclude_none=True)
            if p:
                out["profile"] = p
        if self.flags:
            f = self.flags.model_dump(exclude_none=True)
            if f:
                out["flags"] = f
        return out


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

@router.get("/students/me/respondidas")
async def minhas_respondidas(user: User = Depends(require_user)):
    """`item_id`s que este aluno já respondeu, do histórico de behavior real
    (Firestore, `students/{uid}/behavior`) — nunca inferido de outro lugar.

    Usado para retomar uma prova exatamente de onde o aluno parou: o
    frontend cruza esta lista com os itens do bloco que está exibindo e pula
    para o primeiro ainda não respondido. Não existe um "ponto de parada"
    gravado à parte — cada resposta já é um evento de behavior persistido no
    instante em que é enviada (`POST /students/me/answer`), então abandonar
    no meio nunca perde progresso: só não respondeu o que não respondeu.
    """
    eventos = _safe_call(fs.get_student_behavior_history, user.user_id, 5000)
    item_ids = sorted({e.get("item_id") for e in eventos if e.get("item_id")})
    return {"item_ids": item_ids}


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
    o chamador e autenticado pela sessao do proprio backend (require_user).
    """
    # Nova estrutura (Fase 1): cria students/{uid} (profile) no login se não existir.
    _safe_call(fs.ensure_student_profile, user.user_id, user.name, user.email)
    created = _safe_call(fs.ensure_student_behavior, user.user_id, user.email, user.name)
    doc = _safe_call(fs.read_student_behavior, user.user_id)
    return {"created": created, "user_id": user.user_id, "path": f"students_behavior/students_id/{user.user_id}/behavior_student", "doc": doc}


@router.put("/students/me/behavior")
async def upsert_my_behavior(payload: BehaviorPayload, user: User = Depends(require_user)):
    return _safe_call(fs.write_student_behavior, user.user_id, payload.to_update())


@router.post("/students/me/answer")
async def register_answer(payload: AnswerPayload, user: User = Depends(require_user)):
    """Registra a resposta do aluno a uma questão.

    Determina certo/errado **no servidor** a partir de `questoes_public` e grava
    o evento de behavior (contrato **1.1**) em `students/{uid}/behavior`.

    `ontology_version` e `item_hash` vêm do ITEM respondido, não da ontologia
    ativa nem de um recálculo: o contrato 1.1 pede a versão contra a qual o item
    **estava anotado no momento da resposta**, e o hash do conteúdo **daquele**
    momento. Recalcular o hash aqui produziria um valor que só por acaso
    coincidiria com o do item, e o casamento item↔evento falharia em silêncio.
    """
    doc = await _db.questoes_public.find_one({"item_id": payload.item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    questao = doc.get("questao") or {}
    alternativas = questao.get("alternativas") or []
    correta_letra = next((a.get("letra") for a in alternativas if a.get("correta") is True), None)
    acertou = (payload.alternativa_escolhida == correta_letra) if correta_letra is not None else None

    ontology_version = doc.get("ontology_version")
    if not ontology_version:
        # Item sincronizado antes da migração 2.2: não sabemos contra qual
        # catálogo ele foi anotado. Recusar é a única resposta correta —
        # gravar um evento sem versão o tornaria indatável para sempre.
        raise HTTPException(
            status_code=409,
            detail=(
                "Este item não declara 'ontology_version' e foi anotado antes do "
                "Schema 2.2. Rode a sincronização do pipeline (POST /admin/firestore/sync) "
                "para reingeri-lo sob o contrato vigente antes de aceitar respostas."
            ),
        )

    # Feedback qualitativo por TEMPLATES (sem IA): lookup no master.
    master = await _db.questoes_master.find_one({"id": doc.get("master_id")}, {"_id": 0})
    feedback = build_feedback(master, payload.alternativa_escolhida, acertou)

    _safe_call(fs.ensure_student_profile, user.user_id, user.name, user.email)
    _safe_call(
        fs.write_behavior_event,
        user.user_id,
        item_id=payload.item_id,
        ontology_version=ontology_version,
        alternativa_escolhida=payload.alternativa_escolhida,
        acertou=acertou,
        item_schema_version=doc.get("item_schema_version"),
        item_hash=doc.get("item_hash"),
        item_content=questao,
        contexto_tipo=payload.contexto_tipo,
        prova_id=payload.prova_id,
        tempo_resposta_segundos=payload.tempo_resposta_segundos,
        numero_tentativas=payload.numero_tentativas,
        mudou_resposta=payload.mudou_resposta,
        dispositivo=payload.dispositivo,
        versao_aplicacao=payload.versao_aplicacao,
    )
    return {"acertou": acertou, "correta": correta_letra, "feedback": feedback}


# Admin-only: access by arbitrary uid (e.g. teacher/admin viewing a student)
@router.get("/students/{uid}/behavior")
async def get_behavior_by_uid(uid: str, _: User = Depends(require_admin)):
    doc = _safe_call(fs.read_student_behavior, uid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Behavior document not found")
    return doc
