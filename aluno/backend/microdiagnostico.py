"""Microdiagnóstico — a única fase que ADICIONA evidência em vez de reorganizar.

O problema
----------
Dois alunos marcam a alternativa C pelo mesmo motivo aparente e por processos
completamente diferentes. Hoje o motor infere a causa a partir de
`distratores[].erros_esperados[]` — a hipótese do ANOTADOR sobre quem marca
aquele distrator. Ninguém pergunta ao aluno.

A correção que governa este módulo
----------------------------------
**O autorrelato não entra na mesma escala de confiança do Error Trace.**

O traço tem `produtor: "regra"` e é derivado do catálogo. O autorrelato é outro
produtor — `proposta: autorrelato` — e outra epistemologia: o aluno
pós-racionaliza, e frequentemente não sabe por que errou. Fundi-lo ao
`peso_raiz` seria exatamente o "inventar vínculo Erro→Processo" que R-1 proíbe,
e o "determinizar causa" que R-3 proíbe. Portanto:

* grava-se **no evento de behavior**, em campo próprio, sem virar elo de cadeia;
* ele **corrobora ou contradiz** uma raiz já atribuída pelo catálogo; nunca
  cria raiz, nunca altera `peso_raiz`, `ocorrencias_raiz` ou `mapa_de_erros`;
* alternativas **fechadas**, nunca texto livre. Texto livre exigiria um LLM
  para classificar — custo recorrente —, e um classificador produzindo vínculo
  causal fora do catálogo é R-1 por outra porta.

O valor de curto prazo é INTERNO: contradição sistemática entre o autorrelato e
a hipótese do anotador é o melhor detector de anotação ruim que o sistema pode
ter, e é o que alimenta a fila de revisão humana da Fase 0. O laço fecha aí.

Custo: zero. Nenhuma IA, uma escrita no evento que já existe, e um contador no
Mongo (que não tem cota de leitura).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("sapiens.microdiagnostico")

PRODUTOR = "proposta: autorrelato"

# As cinco alternativas fechadas. `contradiz` marca a única resposta que
# contradiz QUALQUER cadeia causal: quem chutou sem ideia não executou o
# raciocínio que a anotação descreve. As demais são compatíveis com uma cadeia
# — dizer qual delas confirma qual `ERR-*` exigiria uma taxonomia autoral
# ligando relato a tipo de erro, e essa taxonomia é justamente o que este
# módulo se recusa a inventar.
OPCOES: tuple[dict[str, Any], ...] = (
    {"id": "nao_sabia", "rotulo": "Eu não sabia o conteúdo", "contradiz": False},
    {"id": "outra_leitura", "rotulo": "Entendi o enunciado de outro jeito", "contradiz": False},
    {"id": "errei_o_passo", "rotulo": "Sabia, mas errei a conta / o passo", "contradiz": False},
    {"id": "entre_duas", "rotulo": "Fiquei entre duas e chutei", "contradiz": False},
    {"id": "chute", "rotulo": "Chutei sem ideia", "contradiz": True},
)
IDS_VALIDOS = {o["id"] for o in OPCOES}
_CONTRADIZEM = {o["id"] for o in OPCOES if o["contradiz"]}

# Onde o valor diagnóstico é alto e a amostra é baixa. Passando disto, o par já
# está caracterizado e continuar perguntando só gasta a paciência do aluno — a
# pergunta não aparece em toda questão de propósito.
TETO_AMOSTRA_POR_PAR = 30

# A partir daqui a distribuição significa alguma coisa; abaixo disso, não.
_MIN_PARA_SUSPEITA = 8
_FRACAO_DE_CHUTE_SUSPEITA = 0.5

_COLECAO = "autorrelato_pares"

_db = None


def set_db(db):
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def par(erro_id: str, processo_id: str) -> str:
    return f"{erro_id}|{processo_id}"


# Memória curta das contagens por par, para não bater no Mongo a cada erro do
# aluno. O par é global (não por aluno), então a contagem envelhece devagar e
# um minuto de atraso não muda nenhuma decisão.
_MEMO: dict[str, tuple[float, int]] = {}
_MEMO_TTL_S = 60


def esquecer() -> None:
    _MEMO.clear()


async def _total_do_par(chave: str) -> int:
    memo = _MEMO.get(chave)
    if memo and (time.monotonic() - memo[0]) < _MEMO_TTL_S:
        return memo[1]
    if _db is None:
        return 0
    try:
        doc = await getattr(_db, _COLECAO).find_one({"_id": chave}, {"total": 1})
    except Exception as exc:  # noqa: BLE001
        logger.warning("microdiagnostico: contagem do par %s indisponível: %s", chave, exc)
        return 0
    total = int((doc or {}).get("total") or 0)
    _MEMO[chave] = (time.monotonic(), total)
    return total


async def perguntar_por(
    *, causa_raiz: Optional[dict[str, str]], acertou: Optional[bool], event_id: str
) -> Optional[dict[str, Any]]:
    """A micropergunta a fazer depois desta resposta, ou `None`.

    Critério, barato de propósito: **o distrator marcado tem cadeia anotada** e
    **o par ainda tem poucas confirmações**. É onde o valor diagnóstico é alto e
    a amostra é baixa — perguntar em toda questão treinaria o aluno a fechar a
    pergunta sem ler.
    """
    if acertou is not False or not causa_raiz or not event_id:
        return None
    erro_id, processo_id = causa_raiz.get("erro_id"), causa_raiz.get("processo_id")
    if not erro_id or not processo_id:
        return None
    chave = par(erro_id, processo_id)
    if await _total_do_par(chave) >= TETO_AMOSTRA_POR_PAR:
        return None
    return {
        "event_id": event_id,
        "par": chave,
        "pergunta": "O que te levou a essa alternativa?",
        "opcoes": [{"id": o["id"], "rotulo": o["rotulo"]} for o in OPCOES],
    }


async def registrar(
    *, uid: str, event_id: str, opcao: str, chave_par: str | None
) -> dict[str, Any]:
    """Grava o autorrelato no evento e soma no contador do par.

    A escrita no evento é `merge` num campo próprio: o evento continua válido
    sob o contrato 1.1 de behavior (`extra` é permitido), e nenhum campo do
    contrato é tocado.
    """
    import firestore_service as fs

    if opcao not in IDS_VALIDOS:
        raise ValueError(f"opção '{opcao}' não é uma das alternativas fechadas")

    autorrelato = {
        "opcao": opcao,
        "produtor": PRODUTOR,
        "par": chave_par,
        "em": _now_iso(),
    }
    fs.marcar_autorrelato(uid, event_id, autorrelato)

    if _db is not None and chave_par:
        try:
            await getattr(_db, _COLECAO).update_one(
                {"_id": chave_par},
                {
                    "$inc": {"total": 1, f"por_opcao.{opcao}": 1},
                    "$set": {"atualizado_em": _now_iso()},
                },
                upsert=True,
            )
            _MEMO.pop(chave_par, None)
        except Exception as exc:  # noqa: BLE001
            # O relato do aluno já está no evento, que é o dado que importa. O
            # contador é derivável dele.
            logger.warning("microdiagnostico: contador do par %s não subiu: %s", chave_par, exc)

    return {"ok": True, "opcao": opcao}


# ---------------------------------------------------------------------------
# Relatório de concordância — o instrumento interno
# ---------------------------------------------------------------------------


def _linha(doc: dict[str, Any]) -> dict[str, Any]:
    total = int(doc.get("total") or 0)
    por_opcao = {o["id"]: int((doc.get("por_opcao") or {}).get(o["id"]) or 0) for o in OPCOES}
    chutes = sum(por_opcao[o] for o in _CONTRADIZEM)
    fracao = (chutes / total) if total else 0.0
    chave = str(doc.get("_id") or "")
    erro_id, _, processo_id = chave.partition("|")
    return {
        "par": chave,
        "erro_id": erro_id,
        "processo_id": processo_id,
        "total": total,
        "por_opcao": por_opcao,
        "contradizem": chutes,
        "fracao_contradicao": round(fracao, 3),
        # NÃO é um veredito sobre a anotação — é uma linha da fila de revisão
        # humana. Quem decide continua sendo o revisor (R-7: nada aqui altera
        # a ontologia, nem propõe alteração automática).
        "suspeita_de_anotacao": total >= _MIN_PARA_SUSPEITA and fracao >= _FRACAO_DE_CHUTE_SUSPEITA,
        "amostra_suficiente": total >= _MIN_PARA_SUSPEITA,
    }


async def concordancia(limite: int = 200) -> dict[str, Any]:
    """Autorrelato × raiz atribuída, por par. Ordena pela suspeita mais forte.

    Lê o Mongo, não o Firestore: contadores agregados, nenhuma varredura de
    evento e nenhuma cota envolvida.
    """
    if _db is None:
        return {"gerado_em": _now_iso(), "pares": [], "indisponivel": True}
    docs = await getattr(_db, _COLECAO).find({}).to_list(limite)
    linhas = [_linha(d) for d in docs]
    linhas.sort(key=lambda l: (-int(l["suspeita_de_anotacao"]), -l["fracao_contradicao"], -l["total"]))
    return {
        "gerado_em": _now_iso(),
        "indisponivel": False,
        "pares": linhas,
        "opcoes": [{"id": o["id"], "rotulo": o["rotulo"], "contradiz": o["contradiz"]} for o in OPCOES],
        "criterio": {
            "amostra_minima": _MIN_PARA_SUSPEITA,
            "fracao_de_contradicao": _FRACAO_DE_CHUTE_SUSPEITA,
            "teto_por_par": TETO_AMOSTRA_POR_PAR,
        },
    }
