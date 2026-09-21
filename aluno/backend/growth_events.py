"""Eventos de aquisição/growth — funil de marketing, NÃO o registro cognitivo.

**Por que isto não é `events_routes.py`/`behavior`.** O schema canônico de
`students/{uid}/behavior` (ver `pipeline/docs/behavior`) é sobre o que o
aluno RESPONDEU e como o motor cognitivo interpreta isso — misturar clique de
anúncio ou cadastro por indicação ali quebraria o contrato canônico que o
próprio `events_routes.py` já recusou reabrir uma vez ("não há contrato
canônico para X, reinventar seria pior"). `growth_events` é deliberadamente
uma coleção separada, pequena, só para o funil de aquisição — influencer,
cupom, campanha — e não guarda nenhum dado de desempenho pedagógico.

**O que entra aqui.** Só os tipos em `TIPOS`. Nenhum dado sensível (sem IP
cru, sem conteúdo de mensagem) — o suficiente para reconstruir o funil
(clique → cadastro → compra → comissão) e medir CTR/conversão, nunca um log
de comportamento.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("sapiens.growth_events")

TIPOS = (
    "influencer_created",
    "referral_click",
    "referral_signup",
    "referral_activation",
    "referral_purchase",
    "influencer_revenue",
    "influencer_commission",
    "coupon_created",
    "coupon_redeemed",
    "campaign_created",
    "campaign_click",
    "campaign_conversion",
    # Pesquisador IA de Aquisição (2026-09-21) — trilha de auditoria de cada
    # rodada de descoberta (quem disparou, quando, quantos leads). Não
    # impede abuso por si só (ver `rate_limit.LIMITES["pesquisa_aquisicao"]`),
    # mas torna qualquer uso fora do padrão detectável.
    "acquisition_research_run",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def registrar(
    db,
    tipo: str,
    *,
    influencer_id: str | None = None,
    aluno_id: str | None = None,
    campanha_id: str | None = None,
    codigo: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if tipo not in TIPOS:
        logger.warning("growth_events: tipo desconhecido '%s' — não registrado.", tipo)
        return
    await db.growth_events.insert_one({
        "tipo": tipo,
        "influencer_id": influencer_id,
        "aluno_id": aluno_id,
        "campanha_id": campanha_id,
        "codigo": codigo,
        "meta": meta or {},
        "created_at": _now_iso(),
    })


async def resumo_funil(db, *, influencer_id: str | None = None, campanha_id: str | None = None) -> dict:
    """Contagem por tipo de evento, filtrada por influencer ou campanha — a
    base de CTR/conversão que os agentes `analytics`/`marketing` pedem.
    Agrupamento em memória: o volume de eventos de UM influencer/campanha é
    pequeno; não é o acervo de behavior de todos os alunos."""
    filtro: dict[str, Any] = {}
    if influencer_id:
        filtro["influencer_id"] = influencer_id
    if campanha_id:
        filtro["campanha_id"] = campanha_id
    eventos = await db.growth_events.find(filtro, {"_id": 0, "tipo": 1}).to_list(200_000)
    contagem: dict[str, int] = {t: 0 for t in TIPOS}
    for e in eventos:
        contagem[e["tipo"]] = contagem.get(e["tipo"], 0) + 1

    cliques = contagem.get("referral_click", 0) + contagem.get("campaign_click", 0)
    cadastros = contagem.get("referral_signup", 0)
    compras = contagem.get("referral_purchase", 0) + contagem.get("influencer_revenue", 0)
    return {
        "eventos": contagem,
        "ctr_cadastro": round(cadastros / cliques, 4) if cliques else None,
        "conversao_cadastro_compra": round(compras / cadastros, 4) if cadastros else None,
    }
