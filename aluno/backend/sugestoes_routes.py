"""Reclamações e sugestões — o canal direto do aluno com quem faz o Sapiens.

Não confundir com `question_reports_routes.py`: aquele é a bandeira de UMA
questão ("o gabarito desta parece errado") e paga Sparks quando o reporte é
aprovado. Este é sobre o PRODUTO — uma tela confusa, um preço que não fez
sentido, uma ideia de funcionalidade, um elogio. Não paga nada, de propósito:
o dia em que reclamar render Spark, a fila vira ruído e as reclamações de
verdade somem no meio.

Fluxo: o aluno manda (`POST /sugestoes`), vê o que já mandou e o estado de
cada uma (`GET /sugestoes/me`), e a equipe lê e responde numa fila só de
admin (`/admin/sugestoes`). A resposta do admin volta para a lista do aluno —
sem isso o canal é uma caixa de correio sem carteiro, e o aluno para de usar
na segunda vez.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import rate_limit
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.sugestoes")

router = APIRouter(prefix="", tags=["sugestoes"])

# Os quatro tipos que o aluno escolhe. Fechados numa lista porque a fila de
# admin é ordenada por eles — um campo de texto livre aqui viraria 40 rótulos
# diferentes para a mesma coisa.
TIPOS = ("reclamacao", "sugestao", "problema", "elogio")
ESTADOS = ("nova", "lida", "respondida")

_MAX_MENSAGEM = 2000
_MAX_LISTA_ALUNO = 20

_db = None


def set_db(db):
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SugestaoRequest(BaseModel):
    tipo: str = Field(..., description="reclamacao | sugestao | problema | elogio")
    mensagem: str = Field(..., min_length=5, max_length=_MAX_MENSAGEM)
    # De onde o aluno mandou (a rota em que ele estava). Serve para a equipe
    # entender "a tela X confunde" sem precisar perguntar de volta.
    contexto: Optional[str] = Field(default=None, max_length=200)


class RespostaRequest(BaseModel):
    resposta: str = Field(..., min_length=1, max_length=2000)


@router.post("/sugestoes")
async def enviar_sugestao(
    payload: SugestaoRequest,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("sugestoes")),
):
    if payload.tipo not in TIPOS:
        raise HTTPException(status_code=422, detail=f"Tipo inválido. Use um de: {', '.join(TIPOS)}.")
    doc = {
        "sugestao_id": uuid.uuid4().hex,
        "student_id": user.user_id,
        "student_nome": user.name,
        "student_email": user.email,
        "tipo": payload.tipo,
        "mensagem": payload.mensagem.strip(),
        "contexto": (payload.contexto or "").strip() or None,
        "status": "nova",
        "created_at": _now_iso(),
        "resposta": None,
        "respondida_em": None,
        "respondida_por": None,
    }
    await _db.sugestoes.insert_one(doc)
    logger.info("Sugestão %s recebida de %s (%s).", doc["sugestao_id"], user.user_id, payload.tipo)
    return {"ok": True, "sugestao_id": doc["sugestao_id"]}


@router.get("/sugestoes/me")
async def minhas_sugestoes(user: User = Depends(require_user)):
    """O que ESTE aluno já mandou, do mais recente para o mais antigo. Nunca
    devolve dado de outro aluno — o filtro por `student_id` é a única
    fronteira que impede a caixa de sugestões de virar um mural público."""
    cursor = (
        _db.sugestoes.find({"student_id": user.user_id}, {"_id": 0, "student_email": 0})
        .sort("created_at", -1)
        .limit(_MAX_LISTA_ALUNO)
    )
    itens = await cursor.to_list(length=_MAX_LISTA_ALUNO)
    return {"items": itens, "count": len(itens)}


@router.get("/admin/sugestoes")
async def listar_sugestoes(
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    admin: User = Depends(require_admin),
):
    filtro: dict = {}
    if status:
        filtro["status"] = status
    if tipo:
        filtro["tipo"] = tipo
    cursor = _db.sugestoes.find(filtro, {"_id": 0}).sort("created_at", -1)
    itens = await cursor.to_list(length=2000)
    return {"items": itens, "count": len(itens)}


@router.post("/admin/sugestoes/{sugestao_id}/lida")
async def marcar_lida(sugestao_id: str, admin: User = Depends(require_admin)):
    resultado = await _db.sugestoes.find_one_and_update(
        {"sugestao_id": sugestao_id, "status": "nova"},
        {"$set": {"status": "lida"}},
    )
    if resultado is None:
        doc = await _db.sugestoes.find_one({"sugestao_id": sugestao_id}, {"_id": 0})
        if doc is None:
            raise HTTPException(status_code=404, detail="Sugestão não encontrada.")
        raise HTTPException(status_code=409, detail=f"Esta mensagem já está '{doc['status']}'.")
    return {"ok": True}


@router.post("/admin/sugestoes/{sugestao_id}/responder")
async def responder(sugestao_id: str, payload: RespostaRequest, admin: User = Depends(require_admin)):
    """Responder é o ÚNICO caminho para o estado final: uma mensagem só sai
    da fila quando alguém escreveu algo de volta para o aluno."""
    resultado = await _db.sugestoes.find_one_and_update(
        {"sugestao_id": sugestao_id},
        {"$set": {
            "status": "respondida",
            "resposta": payload.resposta.strip(),
            "respondida_em": _now_iso(),
            "respondida_por": admin.user_id,
        }},
    )
    if resultado is None:
        raise HTTPException(status_code=404, detail="Sugestão não encontrada.")
    return {"ok": True}
