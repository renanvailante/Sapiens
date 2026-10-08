"""Rotas da notificação no celular: a chave pública, inscrever, desinscrever.

O pedido de permissão e a decisão de quando mostrá-lo são do frontend
(`lib/push.js`): nunca no primeiro acesso, só depois do primeiro fechamento de
série ou pelo interruptor do Menu. O servidor só guarda o aparelho que o
navegador já autorizou — e esquece quando o aluno desliga.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import push
import push_service as servico
import rate_limit
from auth import require_user
from models import User

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/chave")
async def chave_publica():
    """A `applicationServerKey` do VAPID. Pública por natureza (o navegador a
    entrega a qualquer serviço de push), por isso sem sessão: é também como
    se confere de fora que o secret chegou à máquina — `disponivel: false`
    quer dizer que `VAPID_PRIVATE_KEY` não está configurado."""
    chave = servico.chave_publica()
    return {"disponivel": bool(chave), "chave_publica": chave}


class _Chaves(BaseModel):
    p256dh: str
    auth: str


class InscricaoPayload(BaseModel):
    endpoint: str
    keys: _Chaves


class DesinscricaoPayload(BaseModel):
    endpoint: str


@router.post("/inscrever")
async def inscrever(
    payload: InscricaoPayload,
    request: Request,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("push")),
):
    if not push.endpoint_valido(payload.endpoint):
        # O servidor vai fazer POST neste endereço todo dia: só serviço de push
        # de navegador de verdade (ver `push._HOSTS_DE_PUSH`).
        raise HTTPException(status_code=400, detail="Endereço de notificação não reconhecido.")
    if not (
        push.chave_valida(payload.keys.p256dh, minimo=80, maximo=100)
        and push.chave_valida(payload.keys.auth, minimo=16, maximo=32)
    ):
        raise HTTPException(status_code=400, detail="Chaves de notificação inválidas.")
    if servico.chave_publica() is None:
        raise HTTPException(status_code=503, detail="Notificações indisponíveis no momento.")
    return await servico.inscrever(
        user.user_id,
        payload.endpoint,
        payload.keys.p256dh,
        payload.keys.auth,
        aparelho=request.headers.get("user-agent"),
    )


@router.post("/desinscrever")
async def desinscrever(
    payload: DesinscricaoPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("push")),
):
    return await servico.desinscrever(user.user_id, payload.endpoint)
