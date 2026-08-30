"""Orquestra a correção completa — ponto de entrada único do módulo, chamado
por `redacao_routes.py`.

`elegibilidade.py` + `heuristicas.py` (100% local, via `avaliador_local.py`)
→ se sobrar item indeterminado, `escalonamento_redacao.py` resolve só esses
→ `pontuacao.py` monta o resultado final. Uma redação claramente limpa e no
tema nunca chama o Gemini.
"""
from __future__ import annotations

import logging
from typing import Any

import decision_gate as dg
from redacao import avaliador_local as av
from redacao import canon, pontuacao
from redacao.escalonamento_redacao import NAO_ESCALONAVEL, resolver_itens
from redacao.tipos import RedacaoEntrada

logger = logging.getLogger("sapiens.redacao.service")


def _motivo(c: dg.Classificacao) -> str:
    return f"{c.estado.value}: {c.motivo}"


def _pode_escalonar(item_id: str, c: dg.Classificacao, entrada: RedacaoEntrada) -> bool:
    if item_id in NAO_ESCALONAVEL:
        return False
    if c.estado in (dg.EstadoOperacional.AMBIGUO, dg.EstadoOperacional.CONFLITANTE):
        return True
    if c.estado == dg.EstadoOperacional.INSUFICIENTE:
        # INSUFICIENTE só é escalonável se houver algo para o LLM raciocinar
        # em cima — ex.: falta a decomposição do tema em elementos, mas o
        # tema em si foi informado, então o LLM pode julgar aderência ao
        # tema lendo a frase temática direto, sem depender da nossa
        # decomposição local (que é só um atalho de custo, não o único
        # jeito de avaliar aderência ao tema).
        if item_id in ("ZERO-01", "TEMA-02", "COMP-II") and entrada.tema_frase:
            return True
    return False


def _ja_anulada_localmente(classificacoes: dict[str, dg.Classificacao]) -> bool:
    """Algum gatilho de zero-redação-inteira já saiu `DETERMINADO`+disparado
    só com evidência mecânica/heurística (ex.: texto em branco). Quando
    isso acontece, `pontuacao.py` vai zerar a redação de qualquer jeito —
    escalonar qualquer outro item pendente seria pagar por uma resposta que
    nunca entra no resultado final."""
    return any(
        classificacoes[item_id].estado == dg.EstadoOperacional.DETERMINADO
        and classificacoes[item_id].candidato_final is True
        for item_id in av.GATILHOS_ZERO_REDACAO_INTEIRA
    )


async def corrigir_redacao(entrada: RedacaoEntrada, *, db: Any, redacao_id: str) -> dict[str, Any]:
    canon_versao = canon.versao()
    classificacoes = av.avaliar(entrada)

    if _ja_anulada_localmente(classificacoes):
        resultado = pontuacao.montar_resultado(classificacoes)
        resultado["itens_escalonados_llm"] = []
        return resultado

    pendentes = [item_id for item_id, c in classificacoes.items() if _pode_escalonar(item_id, c, entrada)]

    if pendentes:
        motivos = {item_id: _motivo(classificacoes[item_id]) for item_id in pendentes}
        try:
            evidencias_llm = await resolver_itens(
                entrada, pendentes, db=db, canon_versao=canon_versao,
                motivo_por_item=motivos, redacao_id=redacao_id,
            )
        except Exception:  # noqa: BLE001
            logger.exception("service.corrigir_redacao: escalonamento falhou — itens seguem sem confirmação")
            evidencias_llm = {}
        for item_id, ev_llm in evidencias_llm.items():
            evidencias_originais = list(classificacoes[item_id].evidencias)
            classificacoes[item_id] = dg.classificar(item_id, evidencias_originais + [ev_llm])

    resultado = pontuacao.montar_resultado(classificacoes)
    resultado["itens_escalonados_llm"] = pendentes
    return resultado
