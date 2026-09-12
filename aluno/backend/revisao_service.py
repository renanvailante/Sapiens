"""A junção entre o estado de revisão e o mundo: Firestore, catálogo, itens.

`revisao_espacada` é aritmética pura sobre um dicionário. Este módulo é o que
lê e escreve esse dicionário, traduz `PROC-xx` em nome legível e decide, com o
acervo na mão, se existe item de TRANSFERÊNCIA para aquele processo.

Orçamento de leitura (a regra que governa tudo aqui)
----------------------------------------------------
* `registrar_resposta` — 1 leitura do documento do aluno (memorizada dentro do
  processo, ver `_MEMO`) + 1 escrita. **Nada varre `behavior`.** O traço é
  produzido a partir do item que a rota já tinha carregado do Mongo para
  montar o feedback; o Error Trace sai de graça, como já saía para
  `causa_raiz`.
* `fila` e `trajetoria` — 1 leitura, sempre, independente de quantos eventos o
  aluno tenha.

`annotation_service._build_item_index()` é cache de PROCESSO: depois da
primeira montagem não custa leitura nenhuma, e é o mesmo índice que o motor e
as intervenções já usam.

Onde este módulo para
---------------------
Ele não interpreta erro. Quem valida a cadeia contra o catálogo, aplica R-1 e
descarta par não autorizado é `motor_cognitivo.produzir_traco`, chamado aqui
sem cópia nem variante. Uma segunda leitura do contrato dentro deste arquivo
seria o modo de falha que GOV-1.0 §12 descreve.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import annotation_service
import firestore_service as fs
import intervencoes
import motor_cognitivo
import portao_crenca
import revisao_espacada as rev

logger = logging.getLogger("sapiens.revisao")

# Memória do bloco que ESTE processo acabou de escrever, para que uma sessão de
# prática de 20 questões custe 1 leitura e não 20. Mesma forma da memória de
# `motor_cognitivo._HISTORICO_MEMO`, com uma diferença importante: aqui somos o
# escritor, então a memória é válida enquanto ninguém mais escrever. O TTL curto
# é o que limita a divergência quando o app roda em mais de uma máquina — e o
# pior caso é uma resposta não contada numa janela, nunca uma resposta perdida
# (o evento de behavior já foi gravado antes de chegarmos aqui).
_MEMO: dict[str, tuple[float, dict[str, Any]]] = {}
_MEMO_TTL_S = 600
_MEMO_MAX = 256


def esquecer(uid: str | None = None) -> None:
    if uid is None:
        _MEMO.clear()
    else:
        _MEMO.pop(uid, None)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hoje(quando: str | None = None) -> str:
    """Dia LOCAL do aluno. O fuso importa: `dia_local` existe porque o streak e
    o calendário eram calculados em UTC e quem estudava depois das 21h tinha a
    atividade contada no dia seguinte. Um reteste agendado para "amanhã" tem de
    vencer no amanhã do aluno."""
    return fs.dia_local(quando)


# ---------------------------------------------------------------------------
# Leitura do estado
# ---------------------------------------------------------------------------


def _ler(uid: str, *, usar_memo: bool = True) -> dict[str, Any]:
    if usar_memo:
        memo = _MEMO.get(uid)
        if memo and (time.monotonic() - memo[0]) < _MEMO_TTL_S:
            return memo[1]
    try:
        bloco = fs.ler_revisao(uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("revisao: leitura do estado falhou para %s: %s", uid, exc)
        return rev.bloco_vazio()
    _guardar(uid, bloco)
    return bloco


def _guardar(uid: str, bloco: dict[str, Any]) -> None:
    if len(_MEMO) >= _MEMO_MAX:
        _MEMO.clear()
    _MEMO[uid] = (time.monotonic(), bloco)


# ---------------------------------------------------------------------------
# Contexto do item — o que faz "transferência" significar alguma coisa
# ---------------------------------------------------------------------------


def contexto_do_item(item: dict | None) -> str | None:
    """Chave curta do contexto em que o processo foi exercitado.

    Transferência é o mesmo processo cobrado noutro lugar. A escolha de o que
    conta como "outro lugar" decide se o §12 é mensurável, e a primeira versão
    disto errou: usava o DOMÍNIO anotado como chave primária.

    Por que domínio não serve. A Constituição §4.4 é explícita: domínios e
    competências são **derivados dos processos**. O domínio é, portanto, quase
    uma função do processo — e usá-lo como contexto do processo é tautológico.
    Medido no acervo real em 2026-09-12, o efeito era grosseiro:

        PROC-CAUSAL-01    1 domínio    6 disciplinas   31 temas
        PROC-CLASSIF-01   1 domínio    6 disciplinas   11 temas
        PROC-ESPACO-03    1 domínio    4 disciplinas   16 temas

    Sete processos — entre eles o segundo maior do acervo, com 45 itens —
    apareciam como "sem transferência possível" quando o acervo os cobra em
    meia dúzia de áreas diferentes. O relatório de oferta reprovava todos, e a
    hipótese central da proposta ficava não-mensurável justamente onde havia
    mais dado.

    `fonte.disciplina` é o que discrimina: é declarado pela prova, não derivado
    do processo, e tem granularidade de área do conhecimento — que é o
    significado pretendido de "outro contexto". `tema` NÃO serve como chave
    primária pelo motivo oposto: com 39 temas para um processo, quase toda
    questão seria "transferência" e o sinal não significaria mais nada.

    O domínio fica como segunda opção (item sem `fonte` ainda tem ancoragem) e
    o tema como última. O prefixo mantém as três formas distinguíveis entre si
    num `contextos_da_raiz` que atravesse uma mudança destas.
    """
    if not item:
        return None
    fonte = item.get("fonte") or {}
    disciplina = fonte.get("disciplina")
    if disciplina:
        return f"disciplina:{disciplina}"
    dominios = (item.get("estrutura_cognitiva") or {}).get("dominios") or []
    for d in dominios:
        did = d.get("id") if isinstance(d, dict) else d
        if did:
            return str(did)
    tema = fonte.get("tema")
    return f"tema:{tema}" if tema else None


def _processos_do_item(item: dict | None) -> list[str]:
    nodes = ((item or {}).get("estrutura_cognitiva") or {}).get("processos") or []
    return [n.get("id") if isinstance(n, dict) else n for n in nodes if n]


def raiz_do_evento(uid: str, evento: dict, item: dict) -> Optional[dict[str, Any]]:
    """O elo `ordem: 1` validado, ou `None`.

    Três razões para devolver `None`, e todas são corretas: o aluno acertou, o
    distrator não tem cadeia anotada, ou a cadeia foi descartada por violar o
    contrato (par fora do catálogo, ordem não contígua, confiança ausente).

    **Manifestação nunca chega aqui.** `traco["cadeia"][0]` é a raiz por
    construção — os elos de ordem >= 2 existem no traço e são deliberadamente
    ignorados neste caminho, porque agendar reteste por manifestação de
    superfície é tratar sintoma como causa (Error Trace §1.1).
    """
    traco = motor_cognitivo.produzir_traco(uid, evento, item)
    if not traco:
        return None
    apto = bool(traco.get("apto_para_camada_de_crenca"))
    # Portão de crença §6: com o portão ligado, anotação não revisada não move
    # o estado do aluno — e agendar um reteste É mover o estado dele. Com o
    # portão desligado (o modo do piloto desde 2026-09-04), a raiz entra
    # marcada como provisória e a fila é obrigada a dizer isso.
    if not apto and portao_crenca.modo() != portao_crenca.MODO_DESLIGADO:
        return None
    raiz = traco["cadeia"][0]
    return {
        "erro": raiz["erro"],
        "processo": raiz["processo_afetado"],
        "confianca": raiz["confianca"],
        "provisorio": not apto,
        "trace_id": traco["trace_id"],
    }


# ---------------------------------------------------------------------------
# Escrita — o caminho da resposta
# ---------------------------------------------------------------------------


def registrar_resposta(
    uid: str, *, item: dict | None, evento: dict, avaliar_gatilho: bool = True
) -> dict[str, Any]:
    """Atualiza o estado de revisão e avalia o gatilho da Fase 2.

    Devolve `{"gatilho": ... | None}`. O gatilho sai da MESMA leitura que a
    atualização já pagou: avaliar se há evidência para interromper o aluno não
    custa nenhuma leitura adicional.
    """
    if not item:
        return {"gatilho": None}
    quando = evento.get("timestamp") or _now_iso()
    dia = _hoje(quando)
    acertou = bool((evento.get("resposta") or {}).get("acertou"))

    try:
        raiz = None if acertou else raiz_do_evento(uid, evento, item)
    except Exception as exc:  # noqa: BLE001
        logger.warning("revisao: produção de traço falhou para %s: %s", uid, exc)
        raiz = None

    bloco = _ler(uid)
    novo = rev.registrar(
        bloco,
        processos=_processos_do_item(item),
        acertou=acertou,
        dia=dia,
        quando=quando,
        raiz=raiz,
        contexto=contexto_do_item(item),
    )

    gatilho = None
    if avaliar_gatilho:
        alvo = (raiz or {}).get("processo")
        candidatos = [alvo] if alvo else _processos_do_item(item)
        for pid in candidatos:
            gatilho = rev.avaliar_gatilho(novo, processo_id=pid, hoje=dia)
            if gatilho:
                break
        if gatilho:
            novo = rev.marcar_disparo(novo, gatilho, quando=quando, hoje=dia)
            gatilho = _vestir_gatilho(gatilho)

    _guardar(uid, novo)
    fs.escrever_revisao(uid, novo)
    return {"gatilho": gatilho}


def _vestir_gatilho(gatilho: dict[str, Any]) -> dict[str, Any]:
    """O que a tela precisa para mostrar a intervenção — tudo local, sem IA.

    O texto vem de `intervencoes.previa()`, que é o enquadramento autoral já
    existente sobre a intervenção CATALOGADA do erro raiz. Nada aqui escolhe
    intervenção por semelhança de tema, e nada aqui chama modelo: a Fase 2 é
    push sobre uma máquina de pull que já funcionava.
    """
    previa = intervencoes.previa(gatilho["erro_id"])
    return {
        **gatilho,
        "processo_nome": motor_cognitivo._nome_processo(gatilho["processo_id"]),
        "erro_nome": motor_cognitivo._nome_erro(gatilho["erro_id"]),
        "intervencao": previa,
        "explicacao": _EXPLICACAO_DO_MOTIVO.get(gatilho["motivo"], ""),
        # Enquanto o perfil for provisório, a intervenção se apresenta como
        # HIPÓTESE, com o mesmo rigor do aviso de `motor_cognitivo.perfil()`.
        "aviso": _AVISO_PROVISORIO if gatilho.get("provisorio") else None,
    }


_EXPLICACAO_DO_MOTIVO = {
    rev.GATILHO_RECORRENCIA: "Isto já apareceu antes, em dias diferentes — não foi um deslize isolado.",
    rev.GATILHO_DETERIORACAO: "Você vinha acertando isto e o acerto caiu na sequência mais recente.",
    rev.GATILHO_RETESTE_FALHO: "A questão de revisão que marcamos para hoje não saiu — o ponto ainda não fechou.",
}

_AVISO_PROVISORIO = (
    "Leitura provisória: a anotação das questões por trás desta causa ainda não passou por "
    "revisão humana. Serve para apontar onde olhar primeiro — não é um veredito sobre você."
)


def dispensar_intervencao(uid: str, *, dispensada: bool = True) -> dict[str, Any]:
    """Fecha a intervenção ativa. Dispensar CONTA como sinal — o aluno dizendo
    "não é isto" é informação sobre a anotação, não silêncio."""
    bloco = _ler(uid)
    novo = rev.encerrar_intervencao(bloco, quando=_now_iso(), dispensada=dispensada)
    _guardar(uid, novo)
    fs.escrever_revisao(uid, novo)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Leitura — a fila diária
# ---------------------------------------------------------------------------

_ROTULO_ESTADO = {
    rev.ESTADO_RECORRENTE: "erro recorrente",
    rev.ESTADO_DETERIORACAO: "conceito em deterioração",
    rev.ESTADO_CONSOLIDACAO: "habilidade em consolidação",
}


def fila(uid: str, *, limite: int = rev.FILA_TAMANHO) -> dict[str, Any]:
    """A fila de revisões de hoje — UMA leitura do Firestore, sempre.

    Fechada e curta de propósito. O `/plan/:analysisId` antigo era um snapshot
    preso a uma análise: lia `study_plan` de um documento velho e o desenhava.
    Não reagia ao que o aluno demonstrou ontem, não sabia o que já tinha sido
    trabalhado e não tinha noção de tempo. Esta fila é o contrário disso, e é
    por isso que ela não é um documento — é uma consequência.
    """
    try:
        estado = fs.ler_estado_do_aluno(uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("revisao: leitura da fila falhou para %s: %s", uid, exc)
        return {
            "gerado_em": _now_iso(),
            "indisponivel": True,
            "itens": [],
            "resumo": {},
            "aviso": (
                "Não foi possível ler as suas revisões agora. Isto não quer dizer que você não "
                "tenha nenhuma — tente de novo em alguns minutos."
            ),
        }

    bloco = estado["revisao"]
    _guardar(uid, bloco)
    respondidos = set((estado["agregado"] or {}).get("item_ids_respondidos") or [])
    hoje = _hoje()
    linhas = rev.fila(bloco, hoje, limite=limite)

    itens = [_vestir_linha(l, respondidos) for l in linhas]
    provisorio = any(i["provisorio"] for i in itens)
    return {
        "gerado_em": _now_iso(),
        "hoje": hoje,
        "indisponivel": False,
        "ontology_version": motor_cognitivo._catalogo()["version"],
        "portao": portao_crenca.modo(),
        "provisorio": provisorio,
        "itens": itens,
        "resumo": _resumo(itens),
        "intervencao_ativa": (rev._clonar(bloco)).get("intervencao_ativa"),
        "instrumentacao": rev.instrumentacao(bloco),
        "aviso": _AVISO_PROVISORIO if provisorio else None,
    }


def _vestir_linha(linha: dict[str, Any], respondidos: set[str]) -> dict[str, Any]:
    pid = linha["processo_id"]
    erro_id = linha.get("erro_dominante")
    transferencia = _transferencia(pid, linha.get("contextos_da_raiz") or [], respondidos)
    return {
        **linha,
        "processo_nome": motor_cognitivo._nome_processo(pid),
        "erro_nome": motor_cognitivo._nome_erro(erro_id) if erro_id else None,
        "rotulo": _ROTULO_ESTADO.get(linha["estado"], "revisão"),
        "intervencao": intervencoes.previa(erro_id) if erro_id else None,
        # A linha de transferência só existe quando existe item para ela. Se o
        # acervo não tem o mesmo processo noutro contexto, a linha SOME — nunca
        # se degrada para "mais um item igual", que mediria memória do item em
        # vez de estabilização da habilidade.
        "transferencia": transferencia,
    }


def _transferencia(processo_id: str, contextos_da_raiz: list[str], respondidos: set[str]) -> dict | None:
    """Um item do MESMO processo, num contexto que não é o da raiz, e que o
    aluno ainda não respondeu. `None` quando o acervo não tem — que é o caso
    que o relatório de oferta da Fase 0 existe para prever."""
    if not contextos_da_raiz:
        return None
    index = annotation_service._build_item_index()
    vistos: set[str] = set()
    for item in index.values():
        item_id = item.get("item_id")
        if not item_id or item_id in respondidos or item_id in vistos:
            continue
        vistos.add(item_id)
        if processo_id not in set(_processos_do_item(item)):
            continue
        ctx = contexto_do_item(item)
        if not ctx or ctx in contextos_da_raiz:
            continue
        fonte = item.get("fonte") or {}
        return {
            "item_id": item_id,
            "contexto": ctx,
            "banca": fonte.get("banca"),
            "ano": fonte.get("ano"),
            "prova": fonte.get("prova"),
            "numero": fonte.get("numero"),
            "tema": fonte.get("tema"),
        }
    return None


def _resumo(itens: list[dict[str, Any]]) -> dict[str, Any]:
    """Os números que a tela lê em voz alta ("Revisões de hoje · 8 questões")."""
    conta = {rev.ESTADO_CONSOLIDACAO: 0, rev.ESTADO_RECORRENTE: 0, rev.ESTADO_DETERIORACAO: 0}
    for i in itens:
        if i["estado"] in conta:
            conta[i["estado"]] += 1
    return {
        "questoes": len(itens),
        "em_consolidacao": conta[rev.ESTADO_CONSOLIDACAO],
        "erros_recorrentes": conta[rev.ESTADO_RECORRENTE],
        "em_deterioracao": conta[rev.ESTADO_DETERIORACAO],
        "transferencias": sum(1 for i in itens if i.get("transferencia")),
    }


# ---------------------------------------------------------------------------
# Fase 4 — trajetória
# ---------------------------------------------------------------------------

_MARCO_TEXTO = {
    rev.MARCO_RAIZ: "erro recorrente",
    rev.MARCO_INTERVENCAO: "intervenção",
    rev.MARCO_RETESTE_OK: "revisão em dia",
    rev.MARCO_RETESTE_FALHO: "revisão não saiu",
    rev.MARCO_TRANSFERENCIA: "aplicou em contexto novo",
}


def trajetoria(uid: str) -> dict[str, Any]:
    """A linha do tempo por habilidade — UMA leitura.

    A restrição mais delicada de toda a proposta mora aqui: esta é a tela que
    narra causalidade ("trabalhamos isso, e você melhorou"), que é a afirmação
    mais forte que o produto faz sobre o aluno. Enquanto o perfil for
    provisório, ela DESCREVE o que aconteceu e não afirma por quê — a segunda
    formulação exige o portão de crença em `crenca`. Não é conservadorismo: é
    a diferença entre relatar e alegar. Ver `nexo_causal` no retorno.
    """
    try:
        bloco = fs.ler_revisao(uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("revisao: leitura da trajetória falhou para %s: %s", uid, exc)
        return {"gerado_em": _now_iso(), "indisponivel": True, "habilidades": [], "nexo_causal": False}

    _guardar(uid, bloco)
    b = rev._clonar(bloco)
    habilidades = []
    for pid, e in (b.get("processos") or {}).items():
        marcos = rev.trajetoria(bloco, pid)
        if not marcos:
            continue
        habilidades.append(
            {
                "processo_id": pid,
                "processo_nome": motor_cognitivo._nome_processo(pid),
                "provisorio": bool(e.get("provisorio")),
                "retestes": e.get("retestes"),
                "transferencias": e.get("transferencias"),
                "marcos": [
                    {"tipo": m["tipo"], "quando": m.get("ts"), "rotulo": _MARCO_TEXTO.get(m["tipo"], m["tipo"])}
                    for m in marcos
                ],
            }
        )
    habilidades.sort(key=lambda h: h["marcos"][-1]["quando"] or "", reverse=True)

    provisorio = any(h["provisorio"] for h in habilidades)
    nexo = portao_crenca.modo() != portao_crenca.MODO_DESLIGADO and not provisorio
    return {
        "gerado_em": _now_iso(),
        "indisponivel": False,
        "habilidades": habilidades,
        # Contrato com a tela: `False` obriga a narrativa descritiva.
        "nexo_causal": nexo,
        "provisorio": provisorio,
        "instrumentacao": rev.instrumentacao(bloco),
        "aviso": None if nexo else _AVISO_TRAJETORIA,
    }


_AVISO_TRAJETORIA = (
    "Esta linha do tempo descreve o que aconteceu — o que você errou, o que praticou e o que "
    "acertou depois. Ela não afirma que uma coisa causou a outra: a anotação das questões ainda "
    "não passou por revisão humana."
)
