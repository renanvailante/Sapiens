"""Rotas do motor de engajamento.

Quatro endpoints e nada mais: o estado inteiro numa chamada (o painel abre com
uma requisição, não com seis), a liga isolada (para a tela dedicada não pagar a
leitura do Firestore que só a ofensiva precisa), e as duas ações que o aluno
pode tomar — resgatar missão e comprar congelador.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

import engajamento as eng
import engajamento_service as servico
import rate_limit
from auth import require_user
from models import User

logger = logging.getLogger("sapiens.engajamento")

router = APIRouter(prefix="/engajamento", tags=["engajamento"])


@router.get("/me")
async def meu_estado(user: User = Depends(require_user)):
    """Ofensiva, nível, missões de hoje, liga e contagem do ENEM."""
    return await servico.estado(user.user_id, nome=user.name)


@router.get("/liga")
async def minha_liga(user: User = Depends(require_user)):
    """Só o ranking — 100% Mongo, zero leitura do Firestore.

    A tela da liga é a que o aluno mais atualiza no domingo à noite, quando a
    semana está fechando. Fazer isso passar pelo `estado()` completo cobraria
    uma leitura do Firestore por refresh, por aluno, na hora em que todo mundo
    está olhando ao mesmo tempo.
    """
    semana = eng.semana_de(servico._hoje())
    return await servico._liga(user.user_id, semana, nome=user.name)


@router.post("/missoes/{missao_id}/resgatar")
async def resgatar(
    missao_id: str,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("engajamento")),
):
    resultado = await servico.resgatar_missao(user.user_id, missao_id)
    if not resultado["ok"]:
        raise HTTPException(status_code=409, detail=resultado["motivo"])
    return resultado


@router.post("/congelador")
async def comprar_congelador(
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("engajamento")),
):
    """Compra um congelador de ofensiva por `CUSTO_CONGELADOR` Sparks.

    O 402 com `faltam` é o que permite à tela dizer "faltam 12 Sparks" e levar
    à loja — informação honesta sobre uma compra que o aluno pediu, não um
    empurrão sobre alguém que não pediu nada.
    """
    resultado = await servico.comprar_congelador(user.user_id)
    if not resultado["ok"]:
        raise HTTPException(
            status_code=402 if "faltam" in resultado else 409,
            detail=resultado["motivo"],
        )
    return resultado
