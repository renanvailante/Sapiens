"""Rotas de analytics de produto — ver `product_analytics.py` para o porquê
da coleção existir separada de `growth_events`/`behavior`.

Duas rotas só:
- `POST /analytics/proximo-passo-iniciado` — o aluno, sob demanda, quando
  age sobre a recomendação de Hoje pela primeira vez.
- `GET /admin/analytics/produto` — o painel do admin (ativação, TTFV
  agregado, cohort). As outras marcos (`primeira_compra`/`recompra`/
  `primeira_microvitoria`) nascem direto em `sparks_payments_service.py`/
  `engajamento_service.py`, nos pontos que já são a fonte de verdade — não
  precisam de rota própria.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

import product_analytics
import rate_limit
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.product_analytics.routes")

router = APIRouter(tags=["analytics"])

_db = None


def set_db(db):
    global _db
    _db = db


@router.post("/analytics/proximo-passo-iniciado")
async def proximo_passo_iniciado(
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("analytics_produto")),
):
    """`primeiro_proximo_passo` — grava só na primeira vez (`_id` = `{uid}:
    primeiro_proximo_passo`); chamadas seguintes são no-op barato. Falha
    aqui nunca pode voltar erro pro aluno: é telemetria, não uma ação que
    ele pediu."""
    try:
        novo = await product_analytics.registrar(_db, user.user_id, "primeiro_proximo_passo")
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar primeiro_proximo_passo para %s.", user.user_id)
        novo = False
    return {"ok": True, "novo": novo}


@router.get("/admin/analytics/produto")
async def resumo_analytics_produto(
    dias: int = 30,
    semanas: int = 8,
    admin: User = Depends(require_admin),
):
    ativacao = await product_analytics.resumo_ativacao(_db, dias=dias)
    cohort = await product_analytics.resumo_cohort(_db, semanas=semanas)
    return {"ativacao": ativacao, "cohort": cohort}
