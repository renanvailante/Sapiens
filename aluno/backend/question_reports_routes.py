"""Sugestões de correção de questão — a "bandeira" que o aluno vê em toda
questão, para avisar quando algo parece errado (enunciado, gabarito,
alternativa, imagem etc.).

Fluxo: o aluno reporta (`POST /questoes/{item_id}/reportar`), o pedido entra
como `pendente` numa fila só de admin (`GET /admin/reportes-questoes`,
indexada por questão). Se um admin aprova, o aluno que reportou ganha 5
Sparks — creditados com a MESMA garantia atômica que todo o resto da
economia de Sparks já usa (`DocumentReference.create()` no Firestore), nunca
duas vezes pelo mesmo reporte, mesmo em duplo clique.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import firestore_service as fs
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.question_reports")

router = APIRouter(prefix="", tags=["question-reports"])

RECOMPENSA_APROVACAO = 5

_db = None


def set_db(db):
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReportarRequest(BaseModel):
    texto: str = Field(..., min_length=3, max_length=1000)


@router.post("/questoes/{item_id}/reportar")
async def reportar_questao(item_id: str, payload: ReportarRequest, user: User = Depends(require_user)):
    doc = {
        "report_id": uuid.uuid4().hex,
        "item_id": item_id,
        "student_id": user.user_id,
        "student_nome": user.name,
        "texto": payload.texto.strip(),
        "status": "pendente",
        "created_at": _now_iso(),
        "resolved_at": None,
        "resolved_by": None,
    }
    await _db.question_reports.insert_one(doc)
    return {"ok": True, "report_id": doc["report_id"]}


@router.get("/admin/reportes-questoes")
async def listar_reportes(status: str | None = None, admin: User = Depends(require_admin)):
    """Lista todos os reportes, ordenados por questão (`item_id`) e depois
    por data — o "índice por questão" pedido: quem revisa vê, uma embaixo da
    outra, todas as reclamações da MESMA questão."""
    filtro: dict = {}
    if status:
        filtro["status"] = status
    cursor = _db.question_reports.find(filtro, {"_id": 0}).sort([("item_id", 1), ("created_at", 1)])
    itens = await cursor.to_list(length=2000)
    return {"items": itens, "count": len(itens)}


@router.post("/admin/reportes-questoes/{report_id}/aprovar")
async def aprovar_reporte(report_id: str, admin: User = Depends(require_admin)):
    # Guarda em duas camadas, como o resto da economia de Sparks:
    # 1) Mongo só deixa UMA aprovação sair de "pendente" (flip atômico);
    # 2) mesmo que isso falhasse, o crédito no Firestore é create()-once por
    #    report_id — duplo clique nunca credita duas vezes.
    resultado = await _db.question_reports.find_one_and_update(
        {"report_id": report_id, "status": "pendente"},
        {"$set": {"status": "aprovada", "resolved_at": _now_iso(), "resolved_by": admin.user_id}},
    )
    if resultado is None:
        doc = await _db.question_reports.find_one({"report_id": report_id}, {"_id": 0})
        if doc is None:
            raise HTTPException(status_code=404, detail="Reporte não encontrado.")
        raise HTTPException(status_code=409, detail=f"Reporte já está '{doc['status']}'.")

    ganho = fs.grant_report_sparks(resultado["student_id"], report_id, RECOMPENSA_APROVACAO)
    return {"ok": True, "sparks_creditados": 0 if ganho["ja_concedido"] else ganho["sparks_ganhos"]}


@router.post("/admin/reportes-questoes/{report_id}/rejeitar")
async def rejeitar_reporte(report_id: str, admin: User = Depends(require_admin)):
    resultado = await _db.question_reports.find_one_and_update(
        {"report_id": report_id, "status": "pendente"},
        {"$set": {"status": "rejeitada", "resolved_at": _now_iso(), "resolved_by": admin.user_id}},
    )
    if resultado is None:
        doc = await _db.question_reports.find_one({"report_id": report_id}, {"_id": 0})
        if doc is None:
            raise HTTPException(status_code=404, detail="Reporte não encontrado.")
        raise HTTPException(status_code=409, detail=f"Reporte já está '{doc['status']}'.")
    return {"ok": True}
