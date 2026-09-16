"""Rotas do Mural de Dúvidas.

A lógica toda mora em `comunidade.py`; aqui só ficam contrato de entrada,
autenticação, limite de requisições e a tradução de "não deu" para o código
HTTP certo.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import comunidade
import firestore_service as fs
import rate_limit
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.comunidade")

router = APIRouter(prefix="/comunidade", tags=["comunidade"])


class DuvidaRequest(BaseModel):
    area: str = Field(..., max_length=60)
    titulo: str = Field(..., min_length=8, max_length=160)
    corpo: str = Field(..., min_length=10, max_length=4000)
    item_id: str | None = Field(default=None, max_length=120)
    # "geral" (todo aluno) ou "vip" (só quem comprou o pacote de R$119,90).
    # O padrão é a geral: um cliente que não conhece a VIP nunca publica
    # sem querer numa sala fechada.
    sala: str = Field(default="geral", max_length=10)


class RespostaRequest(BaseModel):
    corpo: str = Field(..., min_length=5, max_length=4000)


class ReporteRequest(BaseModel):
    motivo: str = Field(default="", max_length=500)


def _ehVip(user: User) -> bool:
    """Admin entra na VIP sem comprar: ele MODERA a sala, e moderar uma sala
    que não se pode abrir é impossível."""
    return bool(user.is_admin) or fs.tem_comunidade_vip(user.user_id)


def _exigir_vip(user: User) -> None:
    if not _ehVip(user):
        # 403 e não 404: esconder a existência da sala seria esconder também
        # o motivo de ela estar fechada, e o motivo é justamente o que a
        # tela precisa dizer para vender o acesso.
        raise HTTPException(
            status_code=403,
            detail="A Comunidade VIP é do pacote de 4.000 Sparks (R$119,90).",
        )


@router.get("")
async def mural(
    area: str | None = None,
    filtro: str = "recentes",
    pular: int = 0,
    sala: str = comunidade.SALA_GERAL,
    user: User = Depends(require_user),
):
    if sala == comunidade.SALA_VIP:
        _exigir_vip(user)
    return await comunidade.listar(
        area=area, filtro=filtro, uid=user.user_id, pular=pular, sala=sala,
    )


@router.get("/vip/acesso")
async def acesso_vip(user: User = Depends(require_user)):
    """A tela pergunta ANTES de tentar abrir a sala — assim ela mostra o
    convite de compra em vez de um erro 403 no meio da navegação."""
    return {"vip": _ehVip(user)}


@router.get("/duvidas/{duvida_id}")
async def uma_duvida(duvida_id: str, user: User = Depends(require_user)):
    dados = await comunidade.ler_duvida(duvida_id, uid=user.user_id)
    if dados is None:
        raise HTTPException(status_code=404, detail="Dúvida não encontrada.")
    # O link de uma dúvida da VIP circula (alguém cola no WhatsApp): a porta
    # precisa estar aqui também, não só na listagem. `ler_duvida` devolve
    # `{duvida, respostas, meus_votos}` — a sala está no documento de dentro.
    if (dados.get("duvida") or {}).get("sala") == comunidade.SALA_VIP:
        _exigir_vip(user)
    return dados


@router.post("/duvidas")
async def publicar(
    payload: DuvidaRequest,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("comunidade")),
):
    if payload.sala == comunidade.SALA_VIP:
        _exigir_vip(user)
    return await comunidade.publicar_duvida(
        student_id=user.user_id,
        autor_nome=user.name,
        area=payload.area,
        titulo=payload.titulo,
        corpo=payload.corpo,
        item_id=payload.item_id,
        sala=payload.sala,
    )


@router.post("/duvidas/{duvida_id}/respostas")
async def responder(
    duvida_id: str,
    payload: RespostaRequest,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("comunidade")),
):
    alvo = await comunidade.ler_duvida(duvida_id, uid=user.user_id)
    if alvo and (alvo.get("duvida") or {}).get("sala") == comunidade.SALA_VIP:
        _exigir_vip(user)
    resultado = await comunidade.responder(
        duvida_id=duvida_id, student_id=user.user_id, autor_nome=user.name, corpo=payload.corpo
    )
    if not resultado["ok"]:
        raise HTTPException(status_code=409, detail=resultado["motivo"])
    return resultado


@router.post("/{tipo}/{alvo_id}/voto")
async def votar(
    tipo: str,
    alvo_id: str,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("comunidade")),
):
    if tipo not in ("duvida", "resposta"):
        raise HTTPException(status_code=422, detail="Tipo inválido.")
    resultado = await comunidade.votar(tipo=tipo, alvo_id=alvo_id, uid=user.user_id)
    if not resultado["ok"]:
        raise HTTPException(status_code=409, detail=resultado["motivo"])
    return resultado


@router.post("/duvidas/{duvida_id}/melhor/{resposta_id}")
async def marcar_melhor(duvida_id: str, resposta_id: str, user: User = Depends(require_user)):
    resultado = await comunidade.marcar_melhor(duvida_id=duvida_id, resposta_id=resposta_id, uid=user.user_id)
    if not resultado["ok"]:
        raise HTTPException(status_code=409, detail=resultado["motivo"])
    return resultado


@router.post("/duvidas/{duvida_id}/destacar")
async def destacar(
    duvida_id: str,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("comunidade")),
):
    resultado = await comunidade.destacar(duvida_id=duvida_id, uid=user.user_id)
    if not resultado["ok"]:
        raise HTTPException(status_code=402 if "faltam" in resultado else 409, detail=resultado["motivo"])
    return resultado


@router.post("/{tipo}/{alvo_id}/reportar")
async def reportar(
    tipo: str,
    alvo_id: str,
    payload: ReporteRequest,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("comunidade")),
):
    if tipo not in ("duvida", "resposta"):
        raise HTTPException(status_code=422, detail="Tipo inválido.")
    resultado = await comunidade.reportar(tipo=tipo, alvo_id=alvo_id, uid=user.user_id, motivo=payload.motivo)
    if not resultado["ok"]:
        raise HTTPException(status_code=404, detail=resultado["motivo"])
    # Quantos reportes o conteúdo tem é informação de moderação: devolver isso
    # ao aluno transformaria a tela num placar de "quantos faltam para derrubar".
    return {"ok": True}


# ---------- Moderação (admin) ----------

@router.get("/admin/fila")
async def fila(admin: User = Depends(require_admin)):
    return await comunidade.fila_de_moderacao()


@router.post("/admin/{tipo}/{alvo_id}/{acao}")
async def moderar(tipo: str, alvo_id: str, acao: str, admin: User = Depends(require_admin)):
    if tipo not in ("duvida", "resposta"):
        raise HTTPException(status_code=422, detail="Tipo inválido.")
    resultado = await comunidade.moderar(tipo=tipo, alvo_id=alvo_id, acao=acao)
    if not resultado["ok"]:
        raise HTTPException(status_code=422, detail=resultado["motivo"])
    logger.info("Moderação: %s %s -> %s por %s", tipo, alvo_id, acao, admin.email)
    return resultado
