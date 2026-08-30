"""LLM só para o que sobrou indeterminado depois de `avaliador_local.py`.

Nunca chama o Gemini para um item que já saiu `DETERMINADO` localmente —
`service.py` só passa para cá a lista de itens `AMBIGUO`/`CONFLITANTE`/
`INSUFICIENTE`-escalonável desta redação (pode ser vazia). Cada item entra
no prompt nomeado pelo seu `criterio_id`, com o texto literal da regra ou da
rubrica DAQUELE item — nunca o canon inteiro, nunca um "leia tudo e decida
tudo" genérico.

Uma chamada (Nível 3, `thinking_level=LOW`) tenta resolver todos os itens
pendentes de uma vez — evita N chamadas separadas para N itens pequenos.
Um `judge()` estrutural (nunca semântico: só checa se a resposta tem o
formato esperado) decide, ITEM A ITEM, se aquele item ficou bem formado; só
os itens reprovados voltam numa 2ª chamada (Nível 4, `thinking_level=
MEDIUM`) — os que já passaram no Nível 3 nunca são reconsultados. Nenhum
item tem mais que 2 tentativas, via `llm_escalation.run_adaptive`.

A resposta de cada item vira uma `decision_gate.Evidencia(metodo="llm")` e
volta ao Decision Gate JUNTO com a evidência local já existente — duas
tentativas (LOW e, se houver, MEDIUM) do próprio LLM sobre o MESMO item
também passam pelo mesmo mecanismo de concordância: nenhum campo de
confidence é pedido nem lido em lugar nenhum deste módulo.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import ai_service
import decision_gate as dg
import llm_cache
import llm_escalation
import llm_telemetry
from redacao import canon
from redacao.tipos import RedacaoEntrada

logger = logging.getLogger("sapiens.redacao.escalonamento")

_NIVEIS_VALIDOS = {0, 40, 80, 120, 160, 200}

# Itens que nenhuma chamada de LLM consegue resolver sem um insumo que
# simplesmente não foi fornecido (ver `heuristicas.checar_copia_textos_
# motivadores`) — pedir ao modelo para "adivinhar" cópia sem os textos
# motivadores produziria uma resposta sem base, não uma resolução real.
NAO_ESCALONAVEL = {"COPIA-02"}


def _texto_regra(item_id: str) -> str:
    if item_id.startswith("COMP-"):
        c = canon.competencia(item_id)
        niveis = "\n".join(f"- {n['pontos']} pontos: {n['descricao']}" for n in c["niveis"])
        return f"{c['enunciado_oficial']}\n\nNíveis oficiais (use SOMENTE um destes valores em nivel_pontos):\n{niveis}"
    if item_id == "TEMA-02":
        t = canon.tema()["tangenciamento"]
        return f"Tangenciamento ao tema: {t['definicao']}"
    if item_id == "DH-ZERO-01":
        g = next(g for g in canon.gatilhos_zero_localizado() if g["id"] == item_id)
        return g["descricao"]
    g = next((g for g in canon.gatilhos_zero_redacao_inteira() if g["id"] == item_id), None)
    if g is None:
        raise KeyError(f"item sem regra conhecida no canon: {item_id}")
    return g["descricao"]


_SYSTEM = """Você aplica critérios oficiais de correção de redação do Enem, um item por vez.

Para CADA item na lista abaixo, decida usando SOMENTE o texto da redação fornecido e o
critério citado para aquele item — nunca infira um critério que não foi citado, nunca use
conhecimento sobre outras edições do Enem.

Responda EXCLUSIVAMENTE com um JSON no formato:
{"itens": [
  {
    "criterio_id": "<exatamente o id pedido>",
    "disparado": true ou false,           // OBRIGATÓRIO para itens que NÃO começam com "COMP-"
    "nivel_pontos": 0|40|80|120|160|200,  // OBRIGATÓRIO para itens que começam com "COMP-"
    "trecho_citado": "trecho literal da redação que sustenta a decisão (ou vazio se não houver)",
    "evidencias_encontradas": ["fato observado no texto, curto"],
    "evidencias_ausentes": ["critério do item que o texto não permite avaliar, se houver"]
  }
]}

NUNCA inclua um campo de confiança/confidence/probabilidade — não é usado e será ignorado."""


def _montar_prompt(entrada: RedacaoEntrada, item_ids: list[str]) -> str:
    blocos = []
    for item_id in item_ids:
        blocos.append(f"### Item {item_id}\nCritério: {_texto_regra(item_id)}")
    partes = [
        f"Tema da edição: {entrada.tema_frase or '(não informado)'}",
        "Itens a decidir:\n\n" + "\n\n".join(blocos),
        "Texto da redação:\n" + (entrada.texto or ""),
    ]
    return "\n\n".join(partes)


def _item_valido(item_id: str, resultado: dict[str, Any] | None) -> bool:
    if not isinstance(resultado, dict):
        return False
    if not (resultado.get("trecho_citado") or resultado.get("evidencias_encontradas")):
        return False
    if item_id.startswith("COMP-"):
        return resultado.get("nivel_pontos") in _NIVEIS_VALIDOS
    return isinstance(resultado.get("disparado"), bool)


async def _chamar_llm(entrada: RedacaoEntrada, item_ids: list[str], *, thinking_level: str) -> dict[str, dict]:
    if not item_ids:
        return {}
    prompt = _montar_prompt(entrada, item_ids)
    resp = await ai_service.generate_json(_SYSTEM, prompt, thinking_level=thinking_level)
    itens = (resp or {}).get("itens") if isinstance(resp, dict) else resp
    resultado: dict[str, dict] = {}
    for item in itens or []:
        if isinstance(item, dict) and item.get("criterio_id"):
            resultado[str(item["criterio_id"])] = item
    return resultado


def _evidencia_llm(item_id: str, resultado: dict[str, Any] | None) -> dg.Evidencia:
    if not _item_valido(item_id, resultado):
        return dg.Evidencia(
            item_id, "llm", qualidade_entrada="resposta do LLM malformada/incompleta para este item",
        )
    valor = resultado["nivel_pontos"] if item_id.startswith("COMP-") else resultado["disparado"]
    return dg.Evidencia(
        item_id, "llm", candidatos=[(valor, 1.5)],
        evidencias_presentes=list(resultado.get("evidencias_encontradas") or []) + (
            [f"trecho: {resultado['trecho_citado']}"] if resultado.get("trecho_citado") else []
        ),
        evidencias_ausentes=list(resultado.get("evidencias_ausentes") or []),
    )


async def resolver_itens(
    entrada: RedacaoEntrada,
    itens_pendentes: list[str],
    *,
    db: Any,
    canon_versao: str,
    motivo_por_item: dict[str, str],
    redacao_id: str,
) -> dict[str, dg.Evidencia]:
    """Devolve `{item_id: Evidencia(metodo="llm")}` só para os itens em
    `itens_pendentes` (já filtrados de `NAO_ESCALONAVEL` por quem chama).
    Cache por item — uma redação resubmetida sem alteração não paga de
    novo pelos itens já resolvidos antes."""
    if not itens_pendentes:
        return {}

    resultados: dict[str, dict] = {}
    a_chamar: list[str] = []
    chaves: dict[str, str] = {}
    for item_id in itens_pendentes:
        chave = llm_cache.cache_key(canon_versao, item_id, entrada.texto or "", entrada.tema_frase or "")
        chaves[item_id] = chave
        cache_hit = await llm_cache.get(db.redacao_llm_cache, chave)
        if cache_hit is not None:
            resultados[item_id] = cache_hit
        else:
            a_chamar.append(item_id)

    if a_chamar:
        estado_low: dict[str, dict] = {}

        async def call_low() -> dict[str, dict]:
            inicio = time.monotonic()
            try:
                raw = await _chamar_llm(entrada, a_chamar, thinking_level="LOW")
                estado_low.update(raw)
                for item_id in a_chamar:
                    await llm_telemetry.persist(
                        db.redacao_llm_chamadas,
                        contexto=f"redacao_id={redacao_id} criterio={item_id}",
                        motivo=motivo_por_item.get(item_id, "item não determinado localmente"),
                        modelo="gemini (thinking=LOW)", thinking_level="LOW",
                        resultado_estado="ok" if _item_valido(item_id, raw.get(item_id)) else "malformado",
                        duration_ms=(time.monotonic() - inicio) * 1000,
                        canon_versao=canon_versao,
                    )
            except Exception:  # noqa: BLE001
                logger.exception("escalonamento_redacao: chamada LOW falhou para %s", a_chamar)
            return dict(estado_low)

        def judge(parcial: dict[str, dict]) -> bool:
            return all(_item_valido(item_id, parcial.get(item_id)) for item_id in a_chamar)

        async def call_high() -> dict[str, dict]:
            invalidos = [i for i in a_chamar if not _item_valido(i, estado_low.get(i))]
            inicio = time.monotonic()
            try:
                raw = await _chamar_llm(entrada, invalidos, thinking_level="MEDIUM")
                for item_id in invalidos:
                    await llm_telemetry.persist(
                        db.redacao_llm_chamadas,
                        contexto=f"redacao_id={redacao_id} criterio={item_id}",
                        motivo=f"reprovado no judge() do Nível 3 — {motivo_por_item.get(item_id, '')}".strip(" —"),
                        modelo="gemini (thinking=MEDIUM)", thinking_level="MEDIUM",
                        resultado_estado="ok" if _item_valido(item_id, raw.get(item_id)) else "malformado",
                        duration_ms=(time.monotonic() - inicio) * 1000,
                        canon_versao=canon_versao,
                    )
            except Exception:  # noqa: BLE001
                logger.exception("escalonamento_redacao: chamada MEDIUM falhou para %s", invalidos)
                raw = {}
            combinado = dict(estado_low)
            combinado.update(raw)
            return combinado

        try:
            resolvidos, _meta = await llm_escalation.run_adaptive(call_low, judge, call_high)
        except Exception:  # noqa: BLE001
            logger.exception("escalonamento_redacao: run_adaptive falhou — itens ficam sem resolução LLM")
            resolvidos = estado_low

        for item_id in a_chamar:
            resultados[item_id] = resolvidos.get(item_id)
            if _item_valido(item_id, resultados[item_id]):
                await llm_cache.set(db.redacao_llm_cache, chaves[item_id], resultados[item_id])

    return {item_id: _evidencia_llm(item_id, resultados.get(item_id)) for item_id in itens_pendentes}
