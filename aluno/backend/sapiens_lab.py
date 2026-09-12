"""Sapiens Lab — instrumento INTERNO de investigação, não funcionalidade do aluno.

Por que não é do aluno
----------------------
A proposta original desenhava o Lab como "hipótese → teste → resultado →
próximo teste" na tela do estudante. Três razões para não construir isso:

1. **Mecanicamente já é a Fase 2.** "Hipótese → teste → resultado → próximo
   teste" é gatilho → reteste → resultado → reagendamento, com vocabulário de
   laboratório por cima. Duas implementações do mesmo laço divergem.
2. **A oferta de itens não sustenta.** Cinco situações variadas por hipótese,
   por aluno, sem repetir item — o relatório da Fase 0 mostra que o acervo não
   tem isso para a maioria dos processos. Repetir item transforma o experimento
   em teste de memória.
3. **"Padrão confirmado" em 5 itens viola R-3.** Cinco observações não
   confirmam nada, e imprimir "confirmado" para o aluno é exatamente a
   determinização de causa que o motor foi construído para não fazer.

O que ele é
-----------
O alvo não é o aluno: é o **par (erro, processo) do catálogo**, agregado sobre
todos os alunos. Uma hipótese típica: *"ERR-08 × PROC-12 está mal anotado — os
alunos que marcam esse distrator relatam outra coisa"*. A evidência vem de três
lugares que já existem, cruzados aqui pela primeira vez:

* **autorrelato** (Fase 3) — contradição sistemática entre o que o aluno diz e
  o que o anotador supôs;
* **dispensa** (Fase 2) — o aluno vendo a intervenção e dizendo "não é isto";
* **reteste** (Fase 1) — o par que não melhora depois da intervenção.

E o resultado tem um destino só: **a fila de revisão humana da Fase 0**. Isso
reposiciona o Lab de "a camada mais experimental" para o motor que destrava o
portão de crença — que é o gargalo real do produto inteiro.

R-7, escrito em letra grande: **o Lab PROPÕE revisão; nunca altera a ontologia,
nem sozinho nem com aprovação de admin.** O que um humano pode fazer a partir
daqui é revisar itens (`curadoria.revisar_item`), que é ato registrado item a
item. Mudar catálogo continua sendo GOV-1.0 §11.2, fora do software.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import firestore_service as fs
import microdiagnostico
import motor_cognitivo
import revisao_espacada as rev

logger = logging.getLogger("sapiens.lab")

# Abaixo disto uma hipótese não é hipótese, é anedota. Deliberadamente maior
# que `MIN_TRACOS_RAIZ` (que é o limiar para agir sobre UM aluno): afirmar algo
# sobre a ANOTAÇÃO exige mais evidência do que apontar onde um aluno olha
# primeiro.
MIN_ALUNOS = 3
MIN_OBSERVACOES = 8

# Frações a partir das quais o sinal pesa. Não são veredito — são a ordem da
# fila que um humano vai ler.
_FRACAO_DISPENSA = 0.5
_FRACAO_RETESTE_FALHO = 0.6


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _balde(chave: str) -> dict[str, Any]:
    erro_id, _, processo_id = chave.partition("|")
    return {
        "par": chave,
        "erro_id": erro_id,
        "erro_nome": motor_cognitivo._nome_erro(erro_id),
        "processo_id": processo_id,
        "processo_nome": motor_cognitivo._nome_processo(processo_id),
        "alunos": 0,
        "raizes": 0,
        "intervencoes_mostradas": 0,
        "dispensas": 0,
        "retestes": 0,
        "retestes_ok": 0,
        "autorrelatos": 0,
        "autorrelatos_contraditorios": 0,
    }


def _agregar_revisoes(limite_alunos: int) -> dict[str, dict[str, Any]]:
    """Soma os blocos de revisão de todos os alunos por par (erro, processo).

    O bloco guarda o estado POR PROCESSO, com `pesos_raiz` por erro; o par sai
    do cruzamento dos dois. Um processo com dois erros raiz distribui as
    ocorrências entre eles pelo peso, porque o bloco não guarda a série
    completa — é uma aproximação declarada, e serve: a fila de revisão humana
    precisa de ordem, não de precisão decimal.
    """
    baldes: dict[str, dict[str, Any]] = {}
    for linha in fs.varrer_revisoes(limite_alunos):
        bloco = rev._clonar(linha.get("revisao"))
        for pid, e in (bloco.get("processos") or {}).items():
            pesos = e.get("pesos_raiz") or {}
            if not pesos:
                continue
            total_peso = sum(pesos.values()) or 1.0
            raizes = e.get("raizes_recentes") or []
            ocorrencias_por_erro: dict[str, int] = {}
            for r in raizes:
                ocorrencias_por_erro[r.get("erro")] = ocorrencias_por_erro.get(r.get("erro"), 0) + 1
            for erro_id, peso in pesos.items():
                chave = rev.par(erro_id, pid)
                b = baldes.setdefault(chave, _balde(chave))
                fatia = peso / total_peso
                b["alunos"] += 1
                b["raizes"] += ocorrencias_por_erro.get(erro_id, 0) or round(fatia * len(raizes)) or 1
                b["dispensas"] += round(int(e.get("dispensas") or 0) * fatia)
                b["retestes"] += round(int((e.get("retestes") or {}).get("total") or 0) * fatia)
                b["retestes_ok"] += round(int((e.get("retestes") or {}).get("acertos") or 0) * fatia)
                b["intervencoes_mostradas"] += sum(
                    1 for m in (e.get("marcos") or [])
                    if m.get("tipo") == rev.MARCO_INTERVENCAO and (m.get("erro") in (None, erro_id))
                )
    return baldes


def _sinais(b: dict[str, Any]) -> list[dict[str, Any]]:
    """As afirmações que a evidência sustenta — cada uma com o número que a
    sustenta ao lado. Nunca "confirmado": é uma fila de leitura humana."""
    sinais: list[dict[str, Any]] = []
    if b["autorrelatos"] >= MIN_OBSERVACOES:
        fracao = b["autorrelatos_contraditorios"] / b["autorrelatos"]
        if fracao >= microdiagnostico._FRACAO_DE_CHUTE_SUSPEITA:
            sinais.append(
                {
                    "tipo": "autorrelato_contradiz",
                    "peso": round(fracao, 3),
                    "texto": (
                        f"{b['autorrelatos_contraditorios']} de {b['autorrelatos']} alunos que marcaram "
                        "este distrator dizem ter chutado sem ideia — a cadeia anotada descreve um "
                        "raciocínio que eles não relatam ter feito."
                    ),
                }
            )
    if b["intervencoes_mostradas"] >= MIN_OBSERVACOES:
        fracao = b["dispensas"] / b["intervencoes_mostradas"]
        if fracao >= _FRACAO_DISPENSA:
            sinais.append(
                {
                    "tipo": "intervencao_dispensada",
                    "peso": round(fracao, 3),
                    "texto": (
                        f"{b['dispensas']} de {b['intervencoes_mostradas']} alunos dispensaram a "
                        "intervenção deste par — ela não descreve o que eles reconhecem como o próprio erro."
                    ),
                }
            )
    if b["retestes"] >= MIN_OBSERVACOES:
        falhos = b["retestes"] - b["retestes_ok"]
        fracao = falhos / b["retestes"]
        if fracao >= _FRACAO_RETESTE_FALHO:
            sinais.append(
                {
                    "tipo": "reteste_nao_melhora",
                    "peso": round(fracao, 3),
                    "texto": (
                        f"{falhos} de {b['retestes']} retestes deste par falharam — ou a intervenção "
                        "catalogada não trata a causa, ou a causa anotada não é a causa."
                    ),
                }
            )
    return sinais


async def hipoteses(limite_alunos: int = 500) -> dict[str, Any]:
    """A fila de investigação: pares que merecem olho humano, e por quê.

    Custo: O(alunos) leituras do Firestore (uma por documento de aluno) mais o
    Mongo dos autorrelatos, que não tem cota. Nunca O(eventos) — o Lab lê
    estado agregado, não histórico.
    """
    baldes = _agregar_revisoes(limite_alunos)

    relato = await microdiagnostico.concordancia()
    for linha in relato.get("pares") or []:
        b = baldes.setdefault(linha["par"], _balde(linha["par"]))
        b["autorrelatos"] = linha["total"]
        b["autorrelatos_contraditorios"] = linha["contradizem"]
        b["distribuicao_autorrelato"] = linha["por_opcao"]

    saida = []
    for b in baldes.values():
        sinais = _sinais(b)
        observacoes = max(b["raizes"], b["autorrelatos"], b["intervencoes_mostradas"])
        saida.append(
            {
                **b,
                "sinais": sinais,
                "prioridade": round(sum(s["peso"] for s in sinais), 3),
                "amostra_suficiente": b["alunos"] >= MIN_ALUNOS and observacoes >= MIN_OBSERVACOES,
                # O destino de toda linha desta fila. O Lab não conclui: ele
                # entrega ao revisor humano, que é quem pode abrir o portão.
                "acao": "revisar_anotacao" if sinais else "observar",
            }
        )
    saida.sort(key=lambda l: (-int(bool(l["sinais"])), -l["prioridade"], -l["alunos"]))

    com_sinal = [l for l in saida if l["sinais"] and l["amostra_suficiente"]]
    return {
        "gerado_em": _now_iso(),
        "alvo": "par (erro, processo) do catálogo — nunca o aluno",
        "criterio": {"min_alunos": MIN_ALUNOS, "min_observacoes": MIN_OBSERVACOES},
        "pares": saida,
        "para_revisao_humana": [l["par"] for l in com_sinal],
        "veredito": (
            f"{len(com_sinal)} par(es) com evidência suficiente para entrar na fila de revisão humana "
            f"da Fase 0, de {len(saida)} par(es) observados."
        ),
        # R-7, repetido onde o consumidor da API vai ler.
        "nao_altera_ontologia": True,
    }
