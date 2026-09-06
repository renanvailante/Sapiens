"""Motor Cognitivo — rotas.

**Gratuito, como o `/diagnostico`:** isto é leitura e agregação sobre dados
que o próprio aluno gerou respondendo questões, com custo de inferência zero.
Nada aqui chama LLM, então nada aqui cobra Sparks. O que custa Sparks no app
continua sendo geração de conteúdo (Mentis, mapa cosmético), não medida
pedagógica.

Divisão de trabalho com o que já existia:

* `/diagnostico`  — desempenho medido + fato geral do catálogo. Não explica o
  erro de ninguém.
* `/skills-map`   — gamificação cosmética, nomes genéricos, custa Sparks.
* `/motor/*`      — **este**: Error Trace por resposta errada, mapa de causas
  raiz e intervenção catalogada para a habilidade que o aluno clicar.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

import firestore_service as fs
import motor_cognitivo
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.motor")

router = APIRouter(prefix="/motor", tags=["motor-cognitivo"])


@router.get("/perfil")
async def meu_perfil(user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    return await asyncio.to_thread(motor_cognitivo.perfil, user.user_id)


@router.get("/habilidade/{processo_id}")
async def minha_habilidade(processo_id: str, user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    detalhe = await asyncio.to_thread(motor_cognitivo.detalhe, user.user_id, processo_id)
    if detalhe is None:
        raise HTTPException(status_code=404, detail=f"Processo '{processo_id}' não existe no catálogo vigente.")
    return detalhe


# ---------------------------------------------------------------------------
# Visão interna (admin) — o motor olhando a base inteira
# ---------------------------------------------------------------------------


@router.get("/alunos/{uid}/perfil")
async def perfil_de_aluno(uid: str, _: User = Depends(require_admin)):
    return await asyncio.to_thread(motor_cognitivo.perfil, uid)


@router.get("/panorama")
async def panorama(
    limite_eventos: int = Query(1500, ge=100, le=5000),
    _: User = Depends(require_admin),
):
    """Visão da base inteira — uma varredura só (ver `motor_cognitivo.panorama`).

    `limite_eventos` é teto de LEITURA do Firestore, não de resultado. Os
    números são deliberadamente pequenos: a cota do plano gratuito é de 50 mil
    leituras/dia e foi estourada em produção em 2026-09-04 — com um teto de
    20 mil, um único clique de admin queimava 40% do dia. 1.500 por padrão,
    5.000 no máximo (3% e 10% da cota).
    """
    return await asyncio.to_thread(motor_cognitivo.panorama, limite_eventos)
