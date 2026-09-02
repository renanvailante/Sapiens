"""Rotas de solicitação de aulas particulares.

O aluno pede aula particular (nome, WhatsApp, áreas de interesse, descrição
livre); o admin vê todas as solicitações e altera o status. Não há
agendamento nem cobrança aqui — é só a fila de contato; combinar horário e
valor acontece fora do produto, direto no WhatsApp do aluno.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin, require_user
from models import (
    AULAS_PARTICULARES_AREAS,
    AULAS_PARTICULARES_STATUS,
    AulaParticularRequest,
    CreateAulaParticularRequest,
    UpdateAulaParticularStatusRequest,
    User,
    _now_iso,
)

router = APIRouter(prefix="/aulas-particulares", tags=["aulas-particulares"])

_db = None
def set_db(db):
    global _db
    _db = db


@router.post("")
async def create_request(payload: CreateAulaParticularRequest, user: User = Depends(require_user)):
    if not payload.areas:
        raise HTTPException(status_code=422, detail="Selecione ao menos uma área.")
    invalidas = [a for a in payload.areas if a not in AULAS_PARTICULARES_AREAS]
    if invalidas:
        raise HTTPException(status_code=422, detail=f"Área(s) inválida(s): {', '.join(invalidas)}")
    if not payload.nome_completo.strip() or not payload.whatsapp.strip():
        raise HTTPException(status_code=422, detail="Nome completo e WhatsApp são obrigatórios.")

    req = AulaParticularRequest(
        user_id=user.user_id,
        nome_completo=payload.nome_completo.strip(),
        whatsapp=payload.whatsapp.strip(),
        areas=payload.areas,
        descricao=payload.descricao.strip(),
    )
    await _db.aulas_particulares.insert_one(req.model_dump())
    return req.model_dump()


@router.get("/me")
async def list_my_requests(user: User = Depends(require_user)):
    docs = await _db.aulas_particulares.find(
        {"user_id": user.user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return docs


@router.get("")
async def list_all_requests(admin: User = Depends(require_admin)):
    docs = await _db.aulas_particulares.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return docs


@router.patch("/{request_id}")
async def update_status(
    request_id: str,
    payload: UpdateAulaParticularStatusRequest,
    admin: User = Depends(require_admin),
):
    if payload.status not in AULAS_PARTICULARES_STATUS:
        raise HTTPException(status_code=422, detail=f"Status inválido: {payload.status}")
    res = await _db.aulas_particulares.update_one(
        {"request_id": request_id},
        {"$set": {"status": payload.status, "updated_at": _now_iso()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    doc = await _db.aulas_particulares.find_one({"request_id": request_id}, {"_id": 0})
    return doc
