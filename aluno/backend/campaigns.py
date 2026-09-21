"""Campanhas de aquisição (tráfego pago + conteúdo orgânico) — só estrutura.

**O que este módulo NÃO faz, de propósito.** Não chama nenhuma API de Meta
Ads/Google Ads, não cria anúncio, não gasta dinheiro. `custo_real_cents` é
digitado pelo admin depois de olhar o painel de cada plataforma — o pedido
original é explícito: "não gastar dinheiro automaticamente nesta primeira
implementação". Isto é só o registro que permite comparar canais.

**Por que existe além de `growth_events`.** Uma campanha é a UNIDADE de
custo (o admin sabe quanto gastou numa campanha, não num clique isolado);
`growth_events` é o rastro de eventos que se agrega POR campanha. Sem esta
coleção não haveria onde pendurar `custo_real_cents` para calcular CAC/ROAS.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

CANAIS = ("meta_ads", "google_ads", "organico", "conteudo", "influencer")
TIPOS = ("pago", "organico")
STATUS = ("rascunho", "ativa", "pausada", "encerrada")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def criar(db, payload: dict) -> dict:
    campanha_id = f"camp_{uuid.uuid4().hex[:10]}"
    doc = {
        "_id": campanha_id,
        "campanha_id": campanha_id,
        "nome": payload["nome"],
        "canal": payload["canal"],
        "tipo": payload.get("tipo") or ("pago" if payload["canal"] in ("meta_ads", "google_ads") else "organico"),
        "utm_source": payload.get("utm_source"),
        "utm_medium": payload.get("utm_medium"),
        "utm_campaign": payload.get("utm_campaign"),
        "utm_content": payload.get("utm_content"),
        "orcamento_previsto_cents": payload.get("orcamento_previsto_cents"),
        "custo_real_cents": 0,
        "status": payload.get("status") or "rascunho",
        # Campos de conteúdo orgânico (seção 14) — vazios para campanha paga.
        "ideia": payload.get("ideia"),
        "roteiro": payload.get("roteiro"),
        "cta": payload.get("cta"),
        "plataforma": payload.get("plataforma"),
        "data_publicacao": payload.get("data_publicacao"),
        "link": payload.get("link"),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.campaigns.insert_one(doc)
    import growth_events

    await growth_events.registrar(db, "campaign_created", campanha_id=campanha_id)
    doc.pop("_id", None)
    return doc


async def listar(db) -> list[dict]:
    return await db.campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)


async def atualizar(db, campanha_id: str, campos: dict) -> dict | None:
    campos = {**campos, "updated_at": _now_iso()}
    res = await db.campaigns.find_one_and_update(
        {"_id": campanha_id}, {"$set": campos}, return_document=True,
    )
    if res:
        res.pop("_id", None)
    return res


async def registrar_clique(db, *, campanha_id: str | None, utm_source: str | None, codigo: str | None) -> None:
    """Endpoint público (sem auth — quem clica ainda não tem conta) chama
    isto. Rate limit por IP mora na rota, não aqui — este módulo só grava."""
    import growth_events

    tipo = "campaign_click" if campanha_id else "referral_click"
    await growth_events.registrar(
        db, tipo, campanha_id=campanha_id, codigo=codigo, meta={"utm_source": utm_source},
    )


async def resumo_comparativo(db) -> dict:
    """Compara tráfego pago vs influencer vs orgânico — seção 13. CAC/CPA só
    saem para canais com custo registrado; influencer usa comissão acumulada
    como "custo" (é o que a aquisição custou de fato); orgânico sem custo
    monetário direto some do denominador, não vira zero disfarçado de bom."""
    import influencers as inf_module

    campanhas = await listar(db)
    linhas = []
    for c in campanhas:
        funil = await _funil_campanha(db, c["campanha_id"])
        custo = c.get("custo_real_cents") or 0
        cadastros = funil["eventos"].get("campaign_click", 0) and funil["eventos"].get("referral_signup", 0)
        linhas.append({
            "campanha_id": c["campanha_id"],
            "nome": c["nome"],
            "canal": c["canal"],
            "tipo": c["tipo"],
            "custo_real_cents": custo,
            **funil,
            "cac_cents": round(custo / cadastros) if cadastros else None,
        })

    resumo_influencers = await inf_module.resumo_admin(db)
    linhas.append({
        "campanha_id": None,
        "nome": "Influencers (agregado)",
        "canal": "influencer",
        "tipo": "pago",
        "custo_real_cents": resumo_influencers["comissao_acumulada_total_cents"],
        "alunos_atribuidos": sum(i["alunos_atribuidos"] for i in resumo_influencers["items"]),
    })
    return {"canais": linhas}


async def _funil_campanha(db, campanha_id: str) -> dict:
    import growth_events

    return await growth_events.resumo_funil(db, campanha_id=campanha_id)
