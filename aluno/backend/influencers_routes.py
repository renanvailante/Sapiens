"""Rotas do programa de influencers/afiliados.

Tudo aqui é admin, exceto o painel do próprio influencer (que já mora em
`promoter_routes.py`, estendido para incluir comissão — ver lá) e o rastreio
de clique (público, sem auth, porque quem clica ainda não tem conta — mora em
`campaigns_routes.py` por ser genérico a influencer E campanha paga).

A lógica de verdade mora em `influencers.py`; aqui só contrato HTTP, admin e
tradução de "não achei"/"valor inválido" para o código certo.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

import acquisition_research
import influencers
import rate_limit
from auth import require_admin
from models import (
    AtivarInfluencerRequest,
    CreateInfluencerLeadRequest,
    PesquisarAquisicaoRequest,
    User,
    UpdateInfluencerRequest,
)

_STATUS_PATCH_VALIDOS = influencers.STATUS_PARADO | {
    influencers.STATUS_LEAD, influencers.STATUS_QUALIFICADO, influencers.STATUS_MENSAGEM_PRONTA,
    influencers.STATUS_CONTATO, influencers.STATUS_RESPONDEU,
}

router = APIRouter(prefix="/admin/influencers", tags=["influencers"])

_db = None
def set_db(db):
    global _db
    _db = db


@router.get("/resumo")
async def resumo_admin(admin: User = Depends(require_admin)):
    return await influencers.resumo_admin(_db)


@router.get("")
async def listar(
    status: str | None = None,
    plataforma: str | None = None,
    nicho: str | None = None,
    prioridade: str | None = None,
    busca: str | None = None,
    incluir_descartados: bool = False,
    skip: int = 0,
    limit: int = 200,
    admin: User = Depends(require_admin),
):
    leads = await influencers.listar(
        _db, status=status, plataforma=plataforma, nicho=nicho, prioridade=prioridade,
        busca=busca, incluir_descartados=incluir_descartados, skip=skip, limit=limit,
    )
    return {"items": influencers.priorizar(leads), "total": len(leads)}


@router.post("")
async def criar_lead(payload: CreateInfluencerLeadRequest, admin: User = Depends(require_admin)):
    return await influencers.criar_lead(_db, payload.model_dump())


@router.get("/{influencer_id}")
async def obter(influencer_id: str, admin: User = Depends(require_admin)):
    doc = await influencers.resumo(_db, influencer_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Influencer não encontrado.")
    return doc


@router.patch("/{influencer_id}")
async def atualizar(influencer_id: str, payload: UpdateInfluencerRequest, admin: User = Depends(require_admin)):
    campos = payload.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=422, detail="Nada para atualizar.")
    if "status" in campos and campos["status"] not in _STATUS_PATCH_VALIDOS:
        raise HTTPException(status_code=422, detail="Status inválido.")
    if "prioridade" in campos and campos["prioridade"] not in acquisition_research.PRIORIDADES_VALIDAS:
        raise HTTPException(status_code=422, detail="Prioridade inválida — use alta, media ou baixa.")
    res = await influencers.atualizar(_db, influencer_id, campos)
    if res is None:
        raise HTTPException(status_code=404, detail="Influencer não encontrado.")
    return res


@router.delete("/{influencer_id}")
async def remover(influencer_id: str, admin: User = Depends(require_admin)):
    """Exclusão de verdade, não mudança de status — é o caminho manual de
    remoção que a LGPD do programa de afiliados exige funcionando de fato
    (seção 18 do pedido; ver `Cerebro/produto/afiliados.md`). Recusa se o
    influencer já tem lançamento de comissão (registro financeiro — nesse
    caso, marque `status=removido` via PATCH em vez de apagar)."""
    try:
        apagou = await influencers.remover(_db, influencer_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not apagou:
        raise HTTPException(status_code=404, detail="Influencer não encontrado.")
    return {"removido": True}


@router.post("/{influencer_id}/ativar")
async def ativar(influencer_id: str, payload: AtivarInfluencerRequest, admin: User = Depends(require_admin)):
    try:
        res = await influencers.ativar(
            _db, influencer_id,
            email_login=payload.email_login,
            percentual_comissao=payload.percentual_comissao,
            sparks_boas_vindas=payload.sparks_boas_vindas,
            codigo=payload.codigo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if res is None:
        raise HTTPException(status_code=404, detail="Influencer não encontrado.")
    return res


@router.post("/{influencer_id}/comissao/pagar")
async def marcar_comissao_paga(
    influencer_id: str,
    mp_payment_ids: list[str] | None = Body(default=None, embed=True),
    admin: User = Depends(require_admin),
):
    return await influencers.marcar_comissao_paga(_db, influencer_id, mp_payment_ids=mp_payment_ids)


@router.get("/{influencer_id}/kit")
async def kit(influencer_id: str, admin: User = Depends(require_admin)):
    doc = await influencers.obter(_db, influencer_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Influencer não encontrado.")
    if not doc.get("codigo"):
        raise HTTPException(status_code=409, detail="Influencer ainda não foi ativado — não tem código nem link.")
    return influencers.gerar_kit(doc)


@router.get("/{influencer_id}/mensagem-prospeccao")
async def mensagem_prospeccao(influencer_id: str, variacao: int = 0, admin: User = Depends(require_admin)):
    doc = await influencers.obter(_db, influencer_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Influencer não encontrado.")
    return {"mensagem": influencers.gerar_mensagem_prospeccao(doc, variacao=variacao)}


@router.get("/{influencer_id}/followup/{dia}")
async def followup(influencer_id: str, dia: int, admin: User = Depends(require_admin)):
    doc = await influencers.obter(_db, influencer_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Influencer não encontrado.")
    texto = influencers.gerar_followup(doc, dia)
    if texto is None:
        raise HTTPException(status_code=422, detail="Só existe follow-up programado para os dias 3 e 7.")
    return {"mensagem": texto}


@router.post("/classificar-resposta")
async def classificar_resposta(texto: str = Body(..., embed=True), admin: User = Depends(require_admin)):
    """Sugestão de classificação para uma resposta recebida manualmente —
    nunca dispara envio nenhum. Ver `influencers.classificar_resposta`."""
    classe = influencers.classificar_resposta(texto)
    return {"classificacao": classe, "confiavel": classe is not None}


# ------------------------------------------ Pesquisador IA de Aquisição
#
# Ver `acquisition_research.py` para a lógica completa (descoberta em lote,
# validação de fonte, dedup) e `Cerebro/produto/aquisicao.md` para o desenho.
# As duas rotas abaixo são as únicas de todo este arquivo atrás de rate
# limit — são as únicas que gastam dinheiro em IA por chamada de admin.

@router.post("/pesquisar")
async def pesquisar(
    payload: PesquisarAquisicaoRequest | None = None,
    admin: User = Depends(require_admin),
    _: None = Depends(rate_limit.por_usuario("pesquisa_aquisicao")),
):
    payload = payload or PesquisarAquisicaoRequest()
    return await acquisition_research.executar_rodada_descoberta(
        _db,
        admin_email=admin.email,
        nichos_instagram=payload.nichos_instagram,
        nichos_whatsapp=payload.nichos_whatsapp,
        nichos_telegram=payload.nichos_telegram,
    )


@router.post("/{influencer_id}/mensagem-ia")
async def mensagem_ia(
    influencer_id: str,
    admin: User = Depends(require_admin),
    _: None = Depends(rate_limit.por_usuario("pesquisa_aquisicao_mensagem")),
):
    """Gera (e persiste) uma mensagem personalizada para ESTE lead — uma
    chamada de IA sob demanda, nunca em lote. Nunca envia nada: o texto volta
    pro admin copiar e mandar manualmente."""
    try:
        mensagem = await acquisition_research.gerar_mensagem_personalizada(_db, influencer_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"mensagem": mensagem}
