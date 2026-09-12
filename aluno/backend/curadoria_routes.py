"""Curadoria — as rotas internas que destravam a evidência (Fases 0, 3 e 5).

Tudo aqui é `require_admin`. Nada aqui aparece para o aluno, e nada aqui chama
LLM. As três famílias:

* `/admin/curadoria/oferta`  — o relatório de oferta de itens por processo. É
  BLOQUEANTE: nenhuma fase entra para um processo que ele reprove.
* `/admin/curadoria/fila`    — revisão humana do elo de ordem 1, item a item.
  O único caminho legítimo para religar o portão de crença.
* `/admin/curadoria/concordancia` e `/admin/curadoria/lab` — o que o
  autorrelato do aluno (Fase 3) e o Sapiens Lab (Fase 5) devolvem para a fila
  de revisão. É o laço externo da proposta fechando: o relato do aluno alimenta
  a revisão humana, a revisão humana abre o portão, e o portão aberto é o que
  autoriza o produto a afirmar causalidade em vez de hipótese.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import curadoria
import microdiagnostico
import portao_crenca
import sapiens_lab
from auth import require_admin
from models import User

logger = logging.getLogger("sapiens.curadoria")

router = APIRouter(prefix="/admin/curadoria", tags=["curadoria"])


@router.get("/oferta")
async def oferta(_: User = Depends(require_admin)):
    """Quantos itens existem por processo, em quantos contextos, com que
    anotação. Anexo obrigatório de qualquer decisão de escopo de fase."""
    return await asyncio.to_thread(curadoria.relatorio_de_oferta)


@router.get("/fila")
async def fila(
    par: Optional[str] = Query(None, description="Filtra por 'ERR-xx|PROC-yy'"),
    apenas_pendentes: bool = Query(True),
    limite: int = Query(50, ge=1, le=200),
    _: User = Depends(require_admin),
):
    return await asyncio.to_thread(
        curadoria.fila_de_revisao, par=par, apenas_pendentes=apenas_pendentes, limite=limite
    )


class RevisaoRequest(BaseModel):
    aprovado: bool
    observacoes: str = Field(default="", max_length=1000)


@router.post("/itens/{item_id}/revisar")
async def revisar(item_id: str, payload: RevisaoRequest, admin: User = Depends(require_admin)):
    """Confirma (ou rejeita) o elo de ordem 1 de UM item.

    `aprovado=True` grava `qualidade.apto_para_camada_de_crenca` e é o que faz
    `portao.tracos_no_perfil` subir quando `PORTAO_CRENCA_MODO=crenca`.
    """
    try:
        return await asyncio.to_thread(
            curadoria.revisar_item,
            item_id,
            aprovado=payload.aprovado,
            revisor=admin.email or admin.user_id,
            observacoes=payload.observacoes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class LoteRequest(BaseModel):
    item_ids: list[str] = Field(..., min_length=1, max_length=100)
    aprovado: bool


@router.post("/itens/revisar-lote")
async def revisar_lote(payload: LoteRequest, admin: User = Depends(require_admin)):
    return await asyncio.to_thread(
        curadoria.revisar_em_lote,
        payload.item_ids,
        aprovado=payload.aprovado,
        revisor=admin.email or admin.user_id,
    )


@router.get("/portao")
async def estado_do_portao(_: User = Depends(require_admin)):
    """O modo vigente e o que ele significa — para a decisão de religar não
    acontecer por acidente."""
    modo = portao_crenca.modo()
    piso = portao_crenca.confianca_minima()
    return {
        "modo": modo,
        "confianca_minima": piso,
        "piso": (
            "sem piso — todo traço entra, inclusive os de confiança 0.15"
            if piso <= 0
            else f"só entra sem revisão humana o traço com raiz de confiança >= {piso}"
        ),
        "significado": {
            portao_crenca.MODO_CRENCA: "Item não revisado continua na prova, mas seus erros não movem o perfil.",
            portao_crenca.MODO_CIRCULACAO: "Item não revisado também sai da prova. A leitura mais estrita.",
            portao_crenca.MODO_DESLIGADO: "Sem bloqueio. Todo traço entra marcado como provisório.",
        }[modo],
        "como_mudar": "fly secrets set PORTAO_CRENCA_MODO=crenca (ou unset para voltar ao padrão)",
    }


# ---------------------------------------------------------------------------
# Fase 3 — concordância autorrelato × raiz atribuída
# ---------------------------------------------------------------------------


@router.get("/concordancia")
async def concordancia(_: User = Depends(require_admin)):
    return await microdiagnostico.concordancia()


# ---------------------------------------------------------------------------
# Fase 5 — Sapiens Lab
# ---------------------------------------------------------------------------


@router.get("/lab")
async def lab(
    limite_alunos: int = Query(200, ge=10, le=1000),
    _: User = Depends(require_admin),
):
    """Hipóteses sobre PARES do catálogo, ordenadas pela evidência.

    `limite_alunos` é teto de LEITURA do Firestore (1 por aluno), não de
    resultado. A cota do plano é de 50 mil leituras/dia e já foi estourada uma
    vez em produção — o padrão é deliberadamente pequeno.
    """
    return await sapiens_lab.hipoteses(limite_alunos)
