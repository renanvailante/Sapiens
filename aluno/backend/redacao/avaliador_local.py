"""Combina evidência mecânica (`elegibilidade.py`) e heurística local
(`heuristicas.py`) para os 11 gatilhos de zero-redação-inteira, o gatilho
localizado (`DH-ZERO-01`), o sinal de tangenciamento (`TEMA-02`), o sinal de
cópia (`COPIA-02`) e as 5 competências — passando cada um pelo Decision
Gate. **Nenhuma chamada de rede acontece aqui.**

Devolve `{item_id: decision_gate.Classificacao}`. `service.py` olha o
resultado e só manda para `escalonamento_redacao.py` os itens que não
saíram `DETERMINADO` — o que pode ser a lista vazia, e nesse caso a
correção termina sem gastar nenhuma chamada de API paga.
"""
from __future__ import annotations

from dataclasses import replace

import decision_gate as dg
from redacao import elegibilidade, heuristicas
from redacao.tipos import RedacaoEntrada

GATILHOS_ZERO_REDACAO_INTEIRA = [
    "ZERO-01", "ZERO-02", "ZERO-03", "ZERO-04", "ZERO-05", "ZERO-06",
    "ZERO-07", "ZERO-08", "ZERO-09", "ZERO-10", "ZERO-11",
]
GATILHOS_ZERO_LOCALIZADO = ["DH-ZERO-01"]
COMPETENCIAS = ["COMP-I", "COMP-II", "COMP-III", "COMP-IV", "COMP-V"]
# Não são gatilhos de zero, mas alimentam `pontuacao.py` (cap de tangenciamento
# e penalização por cópia) e passam pelo mesmo Decision Gate por consistência.
AUXILIARES = ["TEMA-02", "COPIA-02"]

TODOS_OS_ITENS = GATILHOS_ZERO_REDACAO_INTEIRA + GATILHOS_ZERO_LOCALIZADO + COMPETENCIAS + AUXILIARES


def _com_criterio(ev: dg.Evidencia, novo_id: str) -> dg.Evidencia:
    return replace(ev, criterio_id=novo_id)


def avaliar(entrada: RedacaoEntrada) -> dict[str, dg.Classificacao]:
    mec = elegibilidade.avaliar_mecanico(entrada)
    heur_gatilhos = heuristicas.avaliar_heuristicas_gatilhos(entrada)
    heur_comp = heuristicas.avaliar_heuristicas_competencias(entrada)

    evidencias_por_item: dict[str, list[dg.Evidencia]] = {item: [] for item in TODOS_OS_ITENS}

    evidencias_por_item["ZERO-01"].append(heur_gatilhos["ZERO-01"])
    # ZERO-02/ZERO-10 compartilham o mesmo sinal local — ver docstring de
    # heuristicas.checar_tipo_dissertativo_argumentativo sobre por quê.
    evidencias_por_item["ZERO-02"].append(_com_criterio(heur_gatilhos["TIPO-TEXTUAL"], "ZERO-02"))
    evidencias_por_item["ZERO-10"].append(_com_criterio(heur_gatilhos["TIPO-TEXTUAL"], "ZERO-10"))
    evidencias_por_item["ZERO-03"].append(mec["ZERO-03"])
    evidencias_por_item["ZERO-04"].append(mec["ZERO-04"])
    evidencias_por_item["ZERO-04"].append(_com_criterio(heur_gatilhos["ZERO-04-PROXY"], "ZERO-04"))
    evidencias_por_item["ZERO-05"].append(heur_gatilhos["ZERO-05"])
    evidencias_por_item["ZERO-06"].append(heur_gatilhos["ZERO-06"])
    evidencias_por_item["ZERO-07"].append(mec["ZERO-07"])
    evidencias_por_item["ZERO-08"].append(mec["ZERO-08"])
    evidencias_por_item["ZERO-09"].append(mec["ZERO-09"])
    evidencias_por_item["ZERO-11"].append(heur_gatilhos["ZERO-11"])
    evidencias_por_item["DH-ZERO-01"].append(heur_gatilhos["DH-ZERO-01"])
    evidencias_por_item["TEMA-02"].append(heur_gatilhos["TEMA-02"])
    evidencias_por_item["COPIA-02"].append(heur_gatilhos["COPIA-02"])
    for comp_id in COMPETENCIAS:
        evidencias_por_item[comp_id].append(heur_comp[comp_id])

    return {item_id: dg.classificar(item_id, evs) for item_id, evs in evidencias_por_item.items()}


def itens_nao_determinados(classificacoes: dict[str, dg.Classificacao]) -> list[str]:
    return [
        item_id for item_id, c in classificacoes.items()
        if c.estado != dg.EstadoOperacional.DETERMINADO
    ]
