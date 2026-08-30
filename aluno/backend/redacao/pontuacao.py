"""Monta o resultado final a partir das classificações (locais + LLM, quando
houve escalonamento): aplica o curto-circuito de zero-redação-inteira,
`DH-ZERO-01` (zera só a Competência V), o cap de tangenciamento (II/III/V —
convenção de engenharia AMB-07) e soma a nota total.

Monta também o rastro auditável por competência — evidências presentes,
evidências ausentes, estado, motivo, métodos consultados — de forma que a
cadeia redação → evidência → método → regra → canon → decisão → pontuação
seja reconstruível a partir do que fica salvo (`redacao_avaliacoes`).

Um item que nunca saiu `DETERMINADO`, nem depois de escalonar, NUNCA é
tratado como se tivesse decidido a favor do lado mais severo (não zera a
prova, não assume o pior nível) — fica com `nivel_pontos`/`disparado`
mostrando o melhor candidato disponível, `confirmado=False`, e entra em
`itens_para_revisao` para decisão humana.
"""
from __future__ import annotations

from typing import Any

import decision_gate as dg
from redacao import avaliador_local as av
from redacao import canon


def _confirmado(c: dg.Classificacao) -> bool:
    return c.estado == dg.EstadoOperacional.DETERMINADO


def _precisa_revisao(c: dg.Classificacao) -> bool:
    return c.estado in (dg.EstadoOperacional.CONFLITANTE, dg.EstadoOperacional.AMBIGUO)


def _rastro(c: dg.Classificacao) -> dict[str, Any]:
    presentes: list[str] = []
    ausentes: list[str] = []
    metodos: list[str] = []
    for ev in c.evidencias:
        presentes.extend(ev.evidencias_presentes)
        ausentes.extend(ev.evidencias_ausentes)
        if ev.candidatos or ev.qualidade_entrada:
            metodos.append(ev.metodo)
    return {
        "evidencias_presentes": presentes,
        "evidencias_ausentes": ausentes,
        "metodos_consultados": metodos,
        "estado": c.estado.value,
        "motivo": c.motivo,
    }


def _gatilho_dict(item_id: str, escopo: str, c: dg.Classificacao) -> dict[str, Any]:
    return {
        "id": item_id,
        "escopo": escopo,
        "disparado": bool(c.candidato_final) if _confirmado(c) else False,
        "candidato_nao_confirmado": bool(c.candidato_final) if not _confirmado(c) and c.candidato_final is not None else None,
        "confirmado": _confirmado(c),
        **_rastro(c),
    }


def montar_resultado(classificacoes: dict[str, dg.Classificacao]) -> dict[str, Any]:
    itens_revisao: list[str] = []
    gatilhos_info: list[dict[str, Any]] = []
    disparado_redacao_inteira = False

    for item_id in av.GATILHOS_ZERO_REDACAO_INTEIRA:
        c = classificacoes[item_id]
        info = _gatilho_dict(item_id, "redacao_inteira", c)
        gatilhos_info.append(info)
        if info["disparado"]:
            disparado_redacao_inteira = True
        if _precisa_revisao(c):
            itens_revisao.append(item_id)

    dh = classificacoes["DH-ZERO-01"]
    dh_info = _gatilho_dict("DH-ZERO-01", "competencia_v", dh)
    gatilhos_info.append(dh_info)
    if _precisa_revisao(dh):
        itens_revisao.append("DH-ZERO-01")

    if disparado_redacao_inteira:
        return {
            "estado_geral": "ANULADA",
            "gatilhos_disparados": gatilhos_info,
            "tangenciamento_detectado": None,
            "competencias": [],
            "nota_total": 0,
            "necessita_revisao_humana": bool(itens_revisao),
            "itens_para_revisao": itens_revisao,
            "canon_versao": canon.versao(),
        }

    tema_c = classificacoes["TEMA-02"]
    tangenciou = _confirmado(tema_c) and bool(tema_c.candidato_final)
    if _precisa_revisao(tema_c):
        itens_revisao.append("TEMA-02")

    copia_c = classificacoes.get("COPIA-02")
    if copia_c is not None and _precisa_revisao(copia_c):
        itens_revisao.append("COPIA-02")

    competencias_resultado: list[dict[str, Any]] = []
    nota_total = 0
    for comp_id in av.COMPETENCIAS:
        c = classificacoes[comp_id]
        if _precisa_revisao(c):
            itens_revisao.append(comp_id)
        confirmado = _confirmado(c)
        nivel = c.candidato_final  # candidato provisório mesmo se não confirmado — nunca None vira 0 aqui
        cap_aplicado = None

        if comp_id == "COMP-V" and dh_info["confirmado"] and dh_info["disparado"]:
            nivel, confirmado, cap_aplicado = 0, True, None
        elif tangenciou and isinstance(nivel, int):
            cap = canon.cap_tangenciamento(comp_id)
            if cap is not None and nivel > cap:
                cap_aplicado = cap
                nivel = cap

        contribuicao = nivel if (confirmado and isinstance(nivel, int)) else 0
        nota_total += contribuicao
        competencias_resultado.append({
            "id": comp_id,
            "nivel_pontos": nivel if confirmado else None,
            "nivel_candidato_nao_confirmado": nivel if not confirmado else None,
            "confirmado": confirmado,
            "cap_aplicado": cap_aplicado,
            **_rastro(c),
        })

    return {
        "estado_geral": "AVALIAVEL",
        "gatilhos_disparados": gatilhos_info,
        "tangenciamento_detectado": tangenciou,
        "competencias": competencias_resultado,
        "nota_total": nota_total,
        "necessita_revisao_humana": bool(itens_revisao),
        "itens_para_revisao": itens_revisao,
        "canon_versao": canon.versao(),
    }
