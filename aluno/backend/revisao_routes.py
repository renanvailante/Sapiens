"""Revisão espaçada — rotas.

**Gratuito, como `/motor` e `/diagnostico`.** Nada aqui chama LLM, logo nada
aqui cobra Sparks. O que custa Spark no app continua sendo GERAÇÃO de conteúdo
(Mentis, mapa cosmético); isto é agregação sobre dados que o próprio aluno
produziu respondendo questões. Uma fase destas que precisasse cobrar seria
sinal de que ela está gerando conteúdo onde deveria estar medindo.

Divisão de trabalho com o que já existia:

* `/motor/perfil`      — o retrato: quais causas raiz explicam os erros deste
  aluno, com a evidência. Custa uma varredura do histórico (memorizada).
* `/revisao/fila`      — **esta**: o que fazer HOJE, com o eixo do tempo por
  cima da mesma priorização. Custa 1 leitura, sempre.
* `/revisao/trajetoria` — a mudança ao longo do tempo, por habilidade.
"""
from __future__ import annotations

import asyncio
import logging

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import engajamento_service
import firestore_service as fs
import microdiagnostico
import revisao_service
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.revisao")

router = APIRouter(prefix="/revisao", tags=["revisao-espacada"])


@router.get("/fila")
async def minha_fila(
    limite: int = Query(8, ge=1, le=20),
    user: User = Depends(require_user),
):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    return await asyncio.to_thread(revisao_service.fila, user.user_id, limite=limite)


@router.get("/trajetoria")
async def minha_trajetoria(user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    return await asyncio.to_thread(revisao_service.trajetoria, user.user_id)


class IntervencaoRequest(BaseModel):
    processo_id: str = Field(..., min_length=2, max_length=40)


@router.post("/intervencao/dispensar")
async def dispensar(payload: IntervencaoRequest, user: User = Depends(require_user)):
    """"Não é isto." Libera a vaga daquele processo e CONTA a dispensa.

    Dispensar é sinal, não silêncio: um par (erro, processo) dispensado
    repetidamente por vários alunos é a evidência mais barata de anotação ruim
    que o sistema consegue coletar — e alimenta a revisão humana da Fase 0.
    """
    return await asyncio.to_thread(
        revisao_service.dispensar_intervencao, user.user_id, processo_id=payload.processo_id, dispensada=True
    )


@router.post("/intervencao/concluir")
async def concluir(payload: IntervencaoRequest, user: User = Depends(require_user)):
    """O aluno foi trabalhar nisso. Libera a vaga sem contar dispensa."""
    resultado = await asyncio.to_thread(
        revisao_service.dispensar_intervencao, user.user_id, processo_id=payload.processo_id, dispensada=False
    )
    # XP da revisão. Não dá para farmar clicando: existe UMA intervenção ativa
    # por vez, e a próxima só nasce de evidência nova no motor cognitivo — o
    # botão não fabrica trabalho, só declara o que já foi feito.
    await engajamento_service.registrar_acao(
        user.user_id, ["revisao_concluida"], contadores={"revisoes": 1}, nome=user.name
    )
    return resultado


# ---------------------------------------------------------------------------
# Fase 3 — microdiagnóstico
# ---------------------------------------------------------------------------


class AutorrelatoRequest(BaseModel):
    event_id: str = Field(..., min_length=8, max_length=64)
    opcao: str = Field(..., min_length=2, max_length=32)
    par: Optional[str] = Field(default=None, max_length=64)


@router.post("/microdiagnostico")
async def registrar_microdiagnostico(
    payload: AutorrelatoRequest, user: User = Depends(require_user)
):
    """O que levou o aluno àquela alternativa — em alternativas FECHADAS.

    Grava num campo próprio do evento de behavior, com produtor próprio. Não
    vira elo de cadeia, não altera `peso_raiz`, não cria raiz: corrobora ou
    contradiz uma raiz que o catálogo já atribuiu. Ver `microdiagnostico`.

    Pular a pergunta é indistinguível de não a ter recebido — a tela
    simplesmente não chama esta rota, e nada é gravado.
    """
    try:
        return await microdiagnostico.registrar(
            uid=user.user_id, event_id=payload.event_id, opcao=payload.opcao, chave_par=payload.par
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Visão interna
# ---------------------------------------------------------------------------


@router.get("/alunos/{uid}/fila")
async def fila_de_aluno(uid: str, _: User = Depends(require_admin)):
    return await asyncio.to_thread(revisao_service.fila, uid)
