"""Recebe erros de JavaScript do navegador do aluno.

O frontend não relatava nada: uma tela branca só chegava à equipe se o aluno
avisasse, e num beta a maioria desiste em silêncio. Isto é o mínimo que fecha
o laço, sem acrescentar fornecedor externo nem contrato de privacidade novo a
um produto que atende menores de idade.

Guarda em `client_errors`, com TTL de 30 dias (ver `db_indexes`): erro de
frontend é sinal operacional de curto prazo, não histórico.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

import rate_limit
from auth import _resolve_user

logger = logging.getLogger("sapiens.client_errors")

router = APIRouter(prefix="/client-errors", tags=["monitoring"])

_db = None


def set_db(db):
    global _db
    _db = db


class ClientErrorPayload(BaseModel):
    mensagem: str = Field(..., max_length=500)
    stack: str = Field(default="", max_length=4_000)
    rota: str = Field(default="", max_length=300)
    user_agent: str = Field(default="", max_length=300)
    contexto: dict = Field(default_factory=dict)


@router.post("")
async def registrar_erro_de_cliente(
    payload: ClientErrorPayload,
    request: Request,
    _: None = Depends(rate_limit.por_ip("client_error")),
):
    """Aceita relato com ou sem sessão.

    Sem sessão de propósito: os erros mais valiosos são os das telas de entrada
    (landing, login), onde ainda não há usuário. O rate limit por IP é o que
    impede a rota de virar depósito de lixo.
    """
    user = await _resolve_user(request)
    documento = {
        **payload.model_dump(),
        "user_id": user.user_id if user else None,
        "recebido_em": datetime.now(timezone.utc).isoformat(),
        "recebido_em_dt": datetime.now(timezone.utc),  # campo BSON para o TTL
    }
    try:
        await _db.client_errors.insert_one(documento)
    except Exception:  # noqa: BLE001
        # Falhar aqui não pode devolver erro ao navegador: o aluno já está numa
        # tela quebrada, e um 500 no relator só piora o quadro.
        logger.exception("Não foi possível gravar erro de cliente.")
    logger.warning(
        "Erro de frontend em %s (user=%s): %s",
        payload.rota, documento["user_id"], payload.mensagem,
    )
    return {"ok": True}
