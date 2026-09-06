"""Motor Cognitivo Sapiens — produtor de Error Trace e priorizador de
habilidades. **Zero IA: nenhuma chamada a LLM, nem paga nem local.**

Por que este módulo existe
--------------------------
O que já havia no app `aluno` cobria dois extremos e deixava o meio vazio:

* `annotation_service.compute_diagnostico_real` mede DESEMPENHO (acertos por
  domínio/competência/processo) e, quando o processo fraco tem exatamente um
  Tipo de Erro catalogado, cita esse erro como *fato geral do catálogo* —
  nunca como causa do erro daquele aluno. O próprio teste do módulo garante
  que ele "nunca produz um Error Trace".
* `cosmetic_skills_map` é gamificação: hexágono genérico, sem nomes reais.

Faltava exatamente o objeto que o corpus canônico chama de **ativo protegido
número 1** (White Paper 2.0 §15): o *Error Trace* — a explicação diagnóstica
de UMA resposta errada de UM aluno a UM item, como cadeia ORDENADA de elos,
cuja raiz (`ordem: 1`) é o que seleciona a Intervenção Pedagógica.

Todo o insumo já estava no banco e ninguém lia:

* `distratores[].erros_esperados[]` de cada item — cadeia ordenada, com
  `erro`, `processo_afetado`, `confianca` e `mecanismo`;
* `resposta.alternativa_escolhida` de cada evento de behavior;
* `intervencoes[]` do item — `{id, gatilho: {processo, erro}, acao}`, com a
  ação escrita **para aquele item**;
* `pedagogia.passos` / `pedagogia.erros_comuns`.

Este módulo faz a junção evento × item × catálogo e nada mais. Determinístico,
reproduzível, custo zero de inferência.

Fronteiras que este módulo NÃO cruza
------------------------------------
1. **Não altera a ontologia** (Error Trace R-7). Padrões observados são
   insumo para revisão humana sob GOV-1.0 §11.2, nunca alteração automática.
2. **Não inventa vínculo Erro→Processo** (R-1). Um elo cujo par
   (`erro`, `processo_afetado`) não exista no catálogo da versão declarada é
   DESCARTADO e contado em `elos_invalidos` — anotação ruim não vira
   diagnóstico silencioso.
3. **Não determiniza causa** (R-3). Toda atribuição carrega `confianca`; a
   agregação soma confianças (atribuição ponderada, Constituição §4.4), nunca
   conta "ocorrências certas".
4. **Não trata manifestação como causa** (§1.1). Elos de `ordem >= 2` entram
   num balde separado (`manifestacoes`) e NUNCA selecionam intervenção.
5. **Não usa `mecanismo` para escolher intervenção** (§4.2): `MEC-*` é
   provisório, não é nó da ontologia e não tem intervenção indexada a si. É
   agregado só para observabilidade, e nunca exibido ao aluno.
6. **Não alimenta crença sem revisão humana** (§6, EXT-WP1-1.0 L13b): ver
   `_PORTAO` abaixo.

O portão de crença
------------------
A regra de ingestão do §6 é literal:

    "Nenhum Error Trace com produtor `modelo` ou `regra` pode alimentar a
     camada de crença sobre o estado de um estudante real sem que seu elo de
     ordem 1 tenha sido confirmado por ao menos um revisor humano."

Este produtor é `regra`. Logo o motor honra `portao_crenca`: traços cujo item
não está `apto_para_camada_de_crenca` são **produzidos e contados**, mas não
entram no perfil enquanto o portão estiver fechado.

**Decisão de operação registrada em 2026-09-04 (piloto).** Como todo o corpus
está sem revisão humana, o portão fechado deixava o motor vazio para todo
mundo. O operador ligou `PORTAO_CRENCA_MODO=desligado` para o piloto. O que
essa chave desliga é o **bloqueio**, não a regra: todo traço que entra sem
revisão é marcado `provisorio` — no perfil (`provisorio`,
`portao.tracos_provisorios`), na linha de cada habilidade
(`provisorio`, `ocorrencias_provisorias`) e em cada traço exposto. A tela é
obrigada a dizer isso ao aluno.

A distinção é a mesma do §6: sem o rótulo, desligar o portão transformaria
hipótese em fato — que é precisamente o que EXT-WP1-1.0 L13b existe para
impedir. Com o rótulo, o aluno vê uma leitura declaradamente provisória, e a
reversão é uma linha: `fly secrets unset PORTAO_CRENCA_MODO`.
"""
from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

import annotation_service
import firestore_service as fs
import portao_crenca
from canonical_ontology import load_ontology, ontology_version

logger = logging.getLogger("sapiens.motor_cognitivo")

ETRACE_VERSION = "1.0"
PRODUTOR = "regra"

# Error Trace §3, R-2 — sentinelas são valores de primeira classe, não
# ausência de dado: registram que houve falha e que o catálogo não a nomeia.
SENTINELAS = {
    "erro-nao-catalogado-nesta-versao",
    "sem-mecanismo-cognitivo-identificavel",
}

# Error Trace §5 — bins declarados. O item pode trazer o rótulo ou o valor.
_CONFIANCA_BINS = {"alta": 0.7, "media": 0.4, "média": 0.4, "baixa": 0.15}

# Error Trace §3, R-4 — profundidade máxima da cadeia.
_ELO_MAX = 3

# Um único erro não sustenta a afirmação de um padrão — mesma disciplina de
# `annotation_service._PADRAO_FREQUENCIA_MINIMA`, aplicada agora à raiz da
# cadeia: uma habilidade só entra na fila de intervenção com >= 2 traços em
# que ela é a RAIZ.
MIN_TRACOS_RAIZ = 2

# Para a fila por desempenho medido (sem traço), o mínimo é o mesmo já
# declarado pelo diagnóstico real — não inventamos um segundo limiar.
MIN_RESPOSTAS = annotation_service._DIAGNOSTICO_MIN_AMOSTRA


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Índices do catálogo canônico (lidos, nunca redefinidos aqui)
# ---------------------------------------------------------------------------

_CACHE: dict[str, Any] = {}


def _catalogo() -> dict[str, Any]:
    """Índices derivados do catálogo canônico vigente.

    `pares_validos` é o que sustenta a restrição R-1: o conjunto de pares
    (Tipo de Erro, Processo) que a ontologia AUTORIZA. Nada fora dele vira
    diagnóstico.
    """
    if _CACHE:
        return _CACHE
    onto = load_ontology()
    erros = {e["id"]: e for e in (onto.get("tipos_erro") or []) if e.get("id")}
    intervencoes = {i["id"]: i for i in (onto.get("intervencoes_pedagogicas") or []) if i.get("id")}
    processos = {p["id"]: p for p in (onto.get("processos_cognitivos") or []) if p.get("id")}
    pares_validos = {
        (eid, pid)
        for eid, e in erros.items()
        for pid in (e.get("processos_cognitivos") or [])
    }
    _CACHE.update(
        {
            "erros": erros,
            "intervencoes": intervencoes,
            "processos": processos,
            "dominios": {d["id"]: d for d in (onto.get("dominios") or []) if d.get("id")},
            "competencias": {c["id"]: c for c in (onto.get("competencias") or []) if c.get("id")},
            "habilidades": {h["id"]: h for h in (onto.get("habilidades_observaveis") or []) if h.get("id")},
            "pares_validos": pares_validos,
            "version": ontology_version(),
        }
    )
    return _CACHE


def recarregar_catalogo() -> None:
    """Só para teste — a ontologia é imutável em produção (é um arquivo)."""
    _CACHE.clear()


def _nome_erro(erro_id: str) -> str:
    if erro_id in SENTINELAS:
        return "Erro fora do catálogo desta versão"
    return (_catalogo()["erros"].get(erro_id) or {}).get("nome") or erro_id


def _nome_processo(pid: str) -> str:
    return (_catalogo()["processos"].get(pid) or {}).get("nome") or pid


def _confianca(bruta: Any) -> float | None:
    """Normaliza `confianca` para os bins do §5. `None` quando ausente ou
    ilegível — e um elo sem confiança é INVÁLIDO (R-3), não vale 1."""
    if isinstance(bruta, (int, float)) and not isinstance(bruta, bool):
        valor = float(bruta)
        return valor if 0.0 < valor <= 1.0 else None
    if isinstance(bruta, str):
        return _CONFIANCA_BINS.get(bruta.strip().lower())
    return None


# ---------------------------------------------------------------------------
# Produção dos traços
# ---------------------------------------------------------------------------


def _validar_cadeia(erros_esperados: Iterable[dict]) -> tuple[list[dict], list[str]]:
    """Aplica R-1 a R-6 a uma cadeia anotada no item.

    Devolve `(elos_validos, motivos_de_descarte)`. Nunca conserta a cadeia:
    um elo que viola o contrato é removido e o motivo fica registrado, porque
    corrigir anotação em tempo de leitura esconderia o defeito de quem tem de
    consertá-lo na anotação.
    """
    cat = _catalogo()
    elos: list[dict] = []
    motivos: list[str] = []
    vistos: set[tuple[str, str]] = set()

    for bruto in erros_esperados or []:
        if not isinstance(bruto, dict):
            motivos.append("elo-nao-e-objeto")
            continue
        ordem = bruto.get("ordem")
        erro = bruto.get("erro")
        processo = bruto.get("processo_afetado")
        confianca = _confianca(bruto.get("confianca"))

        if not isinstance(ordem, int) or not (1 <= ordem <= _ELO_MAX):
            motivos.append("ordem-fora-de-1..3")  # R-4
            continue
        if not erro or not processo:
            motivos.append("elo-incompleto")
            continue
        if confianca is None:
            motivos.append("confianca-ausente-ou-invalida")  # R-3
            continue
        if processo not in cat["processos"]:
            motivos.append(f"processo-fora-do-catalogo:{processo}")
            continue
        if erro not in SENTINELAS:
            if erro not in cat["erros"]:
                motivos.append(f"erro-fora-do-catalogo:{erro}")
                continue
            if (erro, processo) not in cat["pares_validos"]:
                motivos.append(f"par-nao-autorizado:{erro}x{processo}")  # R-1
                continue
        if (erro, processo) in vistos:
            motivos.append("par-repetido-na-cadeia")  # R-6
            continue
        vistos.add((erro, processo))

        elos.append(
            {
                "ordem": ordem,
                "erro": erro,
                "processo_afetado": processo,
                "confianca": confianca,
                "mecanismo": bruto.get("mecanismo") or None,
            }
        )

    elos.sort(key=lambda e: e["ordem"])
    # R-5: ordem contígua começando em 1. Uma cadeia que salta posição não é
    # reordenada — o que se perdeu não é recuperável por adivinhação.
    if elos and [e["ordem"] for e in elos] != list(range(1, len(elos) + 1)):
        return [], motivos + ["ordem-nao-contigua"]
    return elos, motivos


def _trace_id(uid: str, event_id: str) -> str:
    """Estável: o mesmo evento produz sempre o mesmo `trace_id`, então
    reprocessar o histórico não duplica traço."""
    return "ET-" + hashlib.sha256(f"{uid}|{event_id}".encode()).hexdigest()[:24]


def _distrator(item: dict, alternativa: str | None) -> dict | None:
    if not alternativa:
        return None
    alvo = str(alternativa).strip().upper()
    for d in item.get("distratores") or []:
        if isinstance(d, dict) and str(d.get("alternativa") or "").strip().upper() == alvo:
            return d
    return None


def produzir_traco(uid: str, evento: dict, item: dict) -> dict | None:
    """Um Error Trace, conforme a estrutura do §1 da especificação.

    `None` quando não há o que explicar: acerto, alternativa ausente, ou a
    alternativa escolhida não tem distrator anotado no item.
    """
    resposta = evento.get("resposta") or {}
    if resposta.get("acertou") is not False:
        return None
    alternativa = resposta.get("alternativa_escolhida")
    distrator = _distrator(item, alternativa)
    if not distrator:
        return None

    elos, motivos = _validar_cadeia(distrator.get("erros_esperados") or [])
    if not elos:
        return None

    fonte = item.get("fonte") or {}
    return {
        "trace_id": _trace_id(uid, evento.get("event_id") or ""),
        "event_id": evento.get("event_id"),
        "item_id": item.get("item_id") or evento.get("item_id"),
        "item_hash": item.get("item_hash") or evento.get("item_hash"),
        # A versão vem do EVENTO: é a ontologia contra a qual o item estava
        # anotado quando o aluno respondeu, não a vigente hoje (GOV-1.0 §6.1).
        "ontology_version": evento.get("ontology_version") or item.get("ontology_version"),
        "etrace_version": ETRACE_VERSION,
        "alternativa_escolhida": alternativa,
        "cadeia": elos,
        # §5: os elos não são hipóteses concorrentes e não somam 1. A cadeia
        # inteira só se sustenta se a raiz se sustentar — por isso a confiança
        # global é a da raiz, e não uma média que inflaria o conjunto.
        "confianca_global": elos[0]["confianca"],
        "produtor": PRODUTOR,
        "revisado_por_humano": bool(((item.get("qualidade") or {}).get("revisado")) is True),
        "apto_para_camada_de_crenca": portao_crenca.apto(item),
        "timestamp": evento.get("timestamp"),
        "elos_invalidos": motivos,
        "contexto_item": {
            "banca": fonte.get("banca"),
            "ano": fonte.get("ano"),
            "prova": fonte.get("prova"),
            "numero": fonte.get("numero"),
            "tema": fonte.get("tema"),
        },
        "porque_essa_alternativa_engana": distrator.get("explicacao") or None,
    }


# Memória de processo do histórico varrido, por (aluno, nº de respostas).
#
# `_ler_historico` varre `students/{uid}/behavior` INTEIRA: custo O(eventos do
# aluno) por chamada. Sem esta memória havia três multiplicadores, todos reais:
#
#  * `detalhe()` roda logo depois de `perfil()` na mesma navegação (o aluno
#    abre o painel e clica numa habilidade) — o mesmo histórico, duas vezes;
#  * `/motor/panorama` chama `perfil()` para até 200 alunos numa requisição:
#    200 alunos x ~300 eventos = ~60.000 leituras NUM CLIQUE, mais que a cota
#    diária inteira do Firestore (50.000);
#  * o aluno recarregando a página paga tudo de novo.
#
# É a mesma forma do incidente de 2026-09-04, e a chave de invalidação é a
# mesma de `annotation_service._agregado_com_cache`: `total_respostas`, que
# `ler_agregado` devolve em 1 leitura e que sobe a cada resposta. Aqui a
# memória é de PROCESSO (dict), não Mongo, porque `_ler_historico` é síncrona e
# devolve `set`/objetos que não atravessam BSON — e porque o ganho que importa
# (a mesma navegação, o mesmo panorama) acontece dentro de um processo só.
_HISTORICO_MEMO: dict[str, tuple[int, dict[str, Any]]] = {}
_HISTORICO_MEMO_MAX = 256


def esquecer_historico(uid: str | None = None) -> None:
    """Descarta a memória — de um aluno, ou toda. Para testes e para depois de
    uma correção manual de dados em produção."""
    if uid is None:
        _HISTORICO_MEMO.clear()
    else:
        _HISTORICO_MEMO.pop(uid, None)


def _chave_de_invalidacao(uid: str) -> int | None:
    """`total_respostas` do aluno em 1 leitura. `None` quando não dá para
    saber — e sem chave confiável não se serve memória velha."""
    try:
        return int((fs.ler_agregado(uid) or {}).get("total_respostas") or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("motor: agregado indisponível para %s: %s", uid, exc)
        return None


def _ler_historico(uid: str) -> dict[str, Any]:
    """UMA varredura dos eventos do aluno produz as duas coisas de que o motor
    precisa: os traços (dos erros) e o desempenho medido (de tudo). Ler duas
    vezes o mesmo histórico para dois agregados seria pagar Firestore em
    dobro pelo mesmo dado.

    Memorizado por (aluno, nº de respostas) — ver `_HISTORICO_MEMO` acima.
    """
    contagem = _chave_de_invalidacao(uid)
    if contagem is not None:
        memo = _HISTORICO_MEMO.get(uid)
        if memo is not None and memo[0] == contagem:
            return memo[1]

    index = annotation_service._build_item_index()
    client = fs.get_firestore()

    def _zero():
        return {"respondidas": 0, "acertos": 0}

    processo_stats: dict[str, dict[str, int]] = defaultdict(_zero)
    tracos: list[dict] = []
    itens_respondidos: set[str] = set()
    total = respondidos = com_item = erros = 0

    for snap in client.collection("students").document(uid).collection("behavior").stream():
        ev = snap.to_dict() or {}
        if ev.get("status") not in (None, "respondida"):
            continue
        total += 1
        respondidos += 1
        chave = next((k for k in (ev.get("item_id"), ev.get("item_hash")) if k and k in index), None)
        item = index.get(chave) if chave else None
        if not item:
            continue
        com_item += 1
        if item.get("item_id"):
            itens_respondidos.add(item["item_id"])
        acertou = bool((ev.get("resposta") or {}).get("acertou"))
        for node in (item.get("estrutura_cognitiva") or {}).get("processos") or []:
            pid = node.get("id") if isinstance(node, dict) else node
            if not pid:
                continue
            processo_stats[pid]["respondidas"] += 1
            if acertou:
                processo_stats[pid]["acertos"] += 1
        if not acertou:
            erros += 1
            traco = produzir_traco(uid, ev, item)
            if traco:
                tracos.append(traco)

    tracos.sort(key=lambda t: t.get("timestamp") or "")
    resultado = {
        "tracos": tracos,
        "processo_stats": dict(processo_stats),
        "itens_respondidos": itens_respondidos,
        "eventos": total,
        "respondidos": respondidos,
        "eventos_com_item": com_item,
        "erros": erros,
    }

    if contagem is not None:
        # Teto simples em vez de LRU: o que importa é não crescer sem fim num
        # processo de vida longa. Estourou, esvazia — a próxima chamada relê,
        # que é exatamente o comportamento de antes desta memória existir.
        if len(_HISTORICO_MEMO) >= _HISTORICO_MEMO_MAX:
            _HISTORICO_MEMO.clear()
        _HISTORICO_MEMO[uid] = (contagem, resultado)
    return resultado


# ---------------------------------------------------------------------------
# Agregação — do traço individual ao perfil
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Leitura do histórico com falha DECLARADA
# ---------------------------------------------------------------------------
#
# A memória que evita reler o histórico é a de `_ler_historico` (memo por
# `total_respostas`, acima) — não há uma segunda camada aqui de propósito. Um
# cache por tempo na frente daquela memória só faria mal: ela invalida no
# instante em que o aluno responde algo novo, e um TTL a manteria velha por
# minutos em troca de economizar uma leitura do Mongo, que não tem cota.
#
# O que falta lá, e é o que este envelope acrescenta, é a distinção entre
# "sem dados" e "não deu para ler".


def _historico_vazio(falhou: bool) -> dict[str, Any]:
    return {
        "tracos": [], "processo_stats": {}, "itens_respondidos": set(),
        "eventos": 0, "respondidos": 0, "eventos_com_item": 0, "erros": 0,
        "falha_de_leitura": falhou,
    }


def _historico(uid: str) -> dict[str, Any]:
    """Histórico do aluno com a falha declarada em vez de silenciada.

    Firestore fora do ar ou cota estourada NUNCA pode virar "aluno sem
    dados": isso mandaria o aluno responder mais questões atrás de um perfil
    que não ia aparecer de jeito nenhum. A falha volta marcada em
    `falha_de_leitura`, e nada dela entra na memória de `_ler_historico`.

    A cópia rasa existe para não escrever a chave dentro do dicionário
    memorizado, que pertence a `_ler_historico`.
    """
    try:
        dados = _ler_historico(uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("motor: leitura do histórico falhou para %s: %s", uid, exc)
        return _historico_vazio(True)
    return {**dados, "falha_de_leitura": False}


def _agregar_erros(tracos: list[dict]) -> dict[str, Any]:
    """Separa RAIZ de MANIFESTAÇÃO. A separação é a razão de ser do objeto:
    tratar a manifestação de superfície na intervenção é pedagogicamente
    ineficaz (White Paper 1.0 §2.8, citado no Error Trace §1.1)."""
    cat = _catalogo()

    def _balde():
        return {"ocorrencias": 0, "peso": 0.0, "processos": defaultdict(float), "ultima": None}

    raizes: dict[str, dict] = defaultdict(_balde)
    manifestacoes: dict[str, dict] = defaultdict(_balde)
    sentinelas: dict[str, dict] = defaultdict(_balde)
    mecanismos: dict[str, int] = defaultdict(int)

    for t in tracos:
        for elo in t["cadeia"]:
            alvo = raizes if elo["ordem"] == 1 else manifestacoes
            if elo["erro"] in SENTINELAS:
                alvo = sentinelas
            balde = alvo[elo["erro"]]
            balde["ocorrencias"] += 1
            balde["peso"] += elo["confianca"]
            balde["processos"][elo["processo_afetado"]] += elo["confianca"]
            quando = t.get("timestamp")
            if quando and (balde["ultima"] is None or quando > balde["ultima"]):
                balde["ultima"] = quando
            if elo.get("mecanismo"):
                mecanismos[elo["mecanismo"]] += 1

    def _linhas(baldes: dict[str, dict], com_intervencao: bool) -> list[dict]:
        saida = []
        for erro_id, b in baldes.items():
            catalogado = cat["erros"].get(erro_id) or {}
            int_id = catalogado.get("intervencao") if com_intervencao else None
            saida.append(
                {
                    "erro_id": erro_id,
                    "erro_nome": _nome_erro(erro_id),
                    "mecanismo_catalogado": catalogado.get("mecanismo") or "",
                    "evidencia_observavel": catalogado.get("evidencia_observavel") or "",
                    "ocorrencias": b["ocorrencias"],
                    "peso": round(b["peso"], 3),
                    "processos": [
                        {"id": pid, "nome": _nome_processo(pid), "peso": round(p, 3)}
                        for pid, p in sorted(b["processos"].items(), key=lambda kv: -kv[1])
                    ],
                    "intervencao_id": int_id,
                    "intervencao_nome": (cat["intervencoes"].get(int_id) or {}).get("nome") if int_id else None,
                    "ultima_ocorrencia": b["ultima"],
                }
            )
        saida.sort(key=lambda l: (-l["peso"], -l["ocorrencias"]))
        return saida

    return {
        # Só a raiz aponta intervenção (§1.1). A manifestação é informativa e
        # deliberadamente vem SEM `intervencao_id`.
        "raizes": _linhas(raizes, com_intervencao=True),
        "manifestacoes": _linhas(manifestacoes, com_intervencao=False),
        "sem_catalogo": _linhas(sentinelas, com_intervencao=False),
        "mecanismos_observados": dict(sorted(mecanismos.items(), key=lambda kv: -kv[1])),
    }


def _ancoragem(pid: str) -> dict[str, Any]:
    """Domínio e competência do processo, LIDOS do catálogo — a competência
    nunca é atribuída direto ao domínio (Constituição §4.4)."""
    cat = _catalogo()
    proc = cat["processos"].get(pid) or {}
    dom_id = (proc.get("dominios") or [None])[0]
    comp_id = proc.get("competencia")
    return {
        "dominio_id": dom_id,
        "dominio_nome": (cat["dominios"].get(dom_id) or {}).get("nome") if dom_id else None,
        "competencia_id": comp_id,
        "competencia_nome": (cat["competencias"].get(comp_id) or {}).get("nome") if comp_id else None,
        "definicao": proc.get("definicao_operacional") or "",
        "habilidades": [
            {"id": hid, "nome": h.get("nome") or hid}
            for hid, h in cat["habilidades"].items()
            if pid in (h.get("processos_cognitivos") or [])
        ],
    }


def _priorizar(tracos: list[dict], processo_stats: dict[str, dict[str, int]]) -> list[dict]:
    """A fila do que o aluno deve melhorar.

    Duas origens, NUNCA misturadas num mesmo número:

    * `error_trace` — o processo é a RAIZ de >= `MIN_TRACOS_RAIZ` traços. A
      ordem é o peso acumulado de confiança, que é a grandeza calibrada que a
      Constituição §4.4 exige. Só esta origem prescreve intervenção.
    * `desempenho` — sem traço, mas com >= `MIN_RESPOSTAS` respostas e acerto
      abaixo da média do próprio aluno. Ordena por acerto crescente. Aparece
      DEPOIS de todas as de traço, porque somar peso de confiança com taxa de
      acerto seria inventar uma escala comum que não existe.
    """
    cat = _catalogo()
    raiz_peso: dict[str, float] = defaultdict(float)
    raiz_conta: dict[str, int] = defaultdict(int)
    raiz_erro: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    raiz_provisoria: dict[str, int] = defaultdict(int)

    for t in tracos:
        raiz = t["cadeia"][0]
        pid = raiz["processo_afetado"]
        raiz_peso[pid] += raiz["confianca"]
        raiz_conta[pid] += 1
        raiz_erro[pid][raiz["erro"]] += raiz["confianca"]
        if not t["apto_para_camada_de_crenca"]:
            raiz_provisoria[pid] += 1

    def _base(pid: str) -> dict[str, Any]:
        s = processo_stats.get(pid) or {}
        respondidas = s.get("respondidas", 0)
        acertos = s.get("acertos", 0)
        return {
            "processo_id": pid,
            "processo_nome": _nome_processo(pid),
            **_ancoragem(pid),
            "respondidas": respondidas,
            "acertos": acertos,
            "percentual_acerto": round(100 * acertos / respondidas, 1) if respondidas else None,
        }

    fila: list[dict] = []
    for pid, peso in raiz_peso.items():
        if raiz_conta[pid] < MIN_TRACOS_RAIZ:
            continue
        erro_id = max(raiz_erro[pid].items(), key=lambda kv: kv[1])[0]
        catalogado = cat["erros"].get(erro_id) or {}
        int_id = catalogado.get("intervencao")
        # Sentinela como raiz dominante: a evidência é real (o aluno falha
        # mesmo neste processo), mas a v1.4.1 não nomeia a causa — 13 dos 25
        # processos não têm Tipo de Erro. A linha continua aparecendo, porque
        # esconder evidência seria pior; mas vai DEPOIS das que têm
        # intervenção catalogada, senão o aluno abre primeiro justamente a
        # que não tem o que prescrever.
        sem_catalogo = erro_id in SENTINELAS
        linha = _base(pid)
        linha.update(
            {
                "origem": "error_trace",
                "sem_intervencao_catalogada": sem_catalogo,
                "peso_raiz": round(peso, 3),
                "ocorrencias_raiz": raiz_conta[pid],
                # Quantas dessas raízes vieram de anotação ainda não revisada
                # por humano. > 0 significa hipótese provisória, e a tela é
                # obrigada a dizer isso — ver `perfil()`.
                "ocorrencias_provisorias": raiz_provisoria[pid],
                "provisorio": raiz_provisoria[pid] > 0,
                "erro_dominante": {
                    "id": erro_id,
                    "nome": _nome_erro(erro_id),
                    "sem_catalogo": sem_catalogo,
                    "evidencia_observavel": catalogado.get("evidencia_observavel") or "",
                    "peso": round(raiz_erro[pid][erro_id], 3),
                },
                "intervencao": (
                    {"id": int_id, "nome": (cat["intervencoes"].get(int_id) or {}).get("nome") or int_id}
                    if int_id
                    else None
                ),
            }
        )
        fila.append(linha)
    fila.sort(
        key=lambda l: (
            l["sem_intervencao_catalogada"],  # prescritíveis primeiro
            -l["peso_raiz"],
            l["percentual_acerto"] if l["percentual_acerto"] is not None else 100,
        )
    )

    ja_listados = {l["processo_id"] for l in fila}
    medidos = [
        (pid, s)
        for pid, s in processo_stats.items()
        if pid not in ja_listados and s.get("respondidas", 0) >= MIN_RESPOSTAS and pid in cat["processos"]
    ]
    total_resp = sum(s["respondidas"] for _, s in medidos)
    total_acertos = sum(s["acertos"] for _, s in medidos)
    media = (total_acertos / total_resp) if total_resp else 1.0

    por_desempenho = []
    for pid, s in medidos:
        taxa = s["acertos"] / s["respondidas"]
        if taxa >= media:
            continue
        linha = _base(pid)
        linha.update(
            {
                "origem": "desempenho",
                "sem_intervencao_catalogada": True,
                "peso_raiz": 0.0,
                "ocorrencias_raiz": 0,
                "ocorrencias_provisorias": 0,
                # Desempenho medido não é atribuição de causa: contagem de
                # acerto não depende de revisão de anotação para ser verdade.
                "provisorio": False,
                "erro_dominante": None,
                "intervencao": None,
            }
        )
        por_desempenho.append(linha)
    por_desempenho.sort(key=lambda l: l["percentual_acerto"] if l["percentual_acerto"] is not None else 100)

    return fila + por_desempenho


# ---------------------------------------------------------------------------
# Superfície pública
# ---------------------------------------------------------------------------


def _particionar_pelo_portao(tracos: list[dict]) -> tuple[list[dict], list[dict]]:
    """Error Trace §6: traço de produtor `regra` só alimenta crença com o elo
    raiz confirmado por humano. Traços barrados continuam existindo (podem ser
    armazenados) — apenas não movem o perfil."""
    if portao_crenca.modo() == portao_crenca.MODO_DESLIGADO:
        return tracos, []
    aptos = [t for t in tracos if t["apto_para_camada_de_crenca"]]
    barrados = [t for t in tracos if not t["apto_para_camada_de_crenca"]]
    return aptos, barrados


def perfil(uid: str) -> dict[str, Any]:
    """Perfil cognitivo completo do aluno. Uma leitura do histórico, nenhuma
    chamada a modelo, nenhum Spark cobrado."""
    hist = _historico(uid)

    aptos, barrados = _particionar_pelo_portao(hist["tracos"])
    mapa = _agregar_erros(aptos)
    fila = _priorizar(aptos, hist["processo_stats"])

    # Traços que entraram no perfil SEM revisão humana da anotação. Só existem
    # quando o portão está em `desligado` — e, existindo, o perfil inteiro é
    # declarado PROVISÓRIO.
    #
    # Isto não afrouxa a regra do §6: ela continua sendo que anotação não
    # revisada não vira crença. O que o operador pode desligar é o BLOQUEIO;
    # o que ele não pode desligar é a honestidade sobre o que está vendo. Sem
    # este rótulo, desligar o portão transformaria hipótese em fato — que é
    # exatamente o que EXT-WP1-1.0 L13b existe para impedir.
    provisorios = [t for t in aptos if not t["apto_para_camada_de_crenca"]]

    aviso = None
    if hist.get("falha_de_leitura"):
        aviso = (
            "Não foi possível ler o seu histórico agora. Isto não quer dizer que você não "
            "tenha dados — tente de novo em alguns minutos."
        )
    elif barrados and not aptos:
        aviso = (
            f"{len(barrados)} erro(s) seu(s) já têm explicação anotada, mas as questões "
            "correspondentes ainda não passaram por revisão humana — por regra do próprio "
            "método, uma anotação não revisada não pode mover o seu perfil."
        )
    elif provisorios:
        aviso = (
            "Leitura provisória: a anotação das questões por trás destas causas ainda não "
            "passou por revisão humana. Serve para apontar onde olhar primeiro — não é um "
            "veredito sobre você, e pode mudar quando a revisão acontecer."
        )

    return {
        "gerado_em": _now_iso(),
        "ontology_version": _catalogo()["version"],
        "etrace_version": ETRACE_VERSION,
        "produtor": PRODUTOR,
        "provisorio": bool(provisorios),
        "indisponivel": bool(hist.get("falha_de_leitura")),
        "portao": {
            "modo": portao_crenca.modo(),
            "tracos_produzidos": len(hist["tracos"]),
            "tracos_no_perfil": len(aptos),
            "tracos_barrados": len(barrados),
            "tracos_provisorios": len(provisorios),
        },
        "cobertura": {
            "eventos": hist["eventos"],
            "eventos_com_item": hist["eventos_com_item"],
            "erros": hist["erros"],
            "erros_explicados": len(aptos),
            "percentual": round(100 * len(aptos) / hist["erros"], 1) if hist["erros"] else 0.0,
        },
        "mapa_de_erros": mapa,
        "habilidades_prioritarias": fila,
        "amostra_minima": {"tracos_raiz": MIN_TRACOS_RAIZ, "respostas": MIN_RESPOSTAS},
        "aviso": aviso,
    }


def panorama(limite_eventos: int = 5000) -> dict[str, Any]:
    """Quais causas RAIZ dominam a base inteira, e em quantos alunos.

    **Uma** varredura da collection group `behavior`, não uma por aluno. A
    versão óbvia — listar alunos e chamar `perfil()` para cada um — custa a
    varredura da collection group MAIS o histórico completo de cada aluno; com
    50 alunos isso é a cota diária do plano gratuito num único clique de
    admin. Aqui o mesmo stream que descobre quem respondeu já traz o que
    responderam.

    Informa; nunca altera catálogo (Error Trace R-7, GOV-1.0 §11.2 Classe B).
    """
    index = annotation_service._build_item_index()
    client = fs.get_firestore()

    por_aluno: dict[str, list[dict]] = defaultdict(list)
    lidos = vistos = 0
    for snap in client.collection_group("behavior").limit(limite_eventos).stream():
        vistos += 1
        ev = snap.to_dict() or {}
        uid = ev.get("student_id")
        if not uid or ev.get("status") not in (None, "respondida"):
            continue
        lidos += 1
        if (ev.get("resposta") or {}).get("acertou") is not False:
            continue
        chave = next((k for k in (ev.get("item_id"), ev.get("item_hash")) if k and k in index), None)
        item = index.get(chave) if chave else None
        if not item:
            continue
        traco = produzir_traco(uid, ev, item)
        if traco:
            por_aluno[uid].append(traco)

    cat = _catalogo()
    por_erro: dict[str, dict] = {}
    por_processo: dict[str, dict] = {}
    barrados = provisorios = com_traco = 0

    for uid, tracos in por_aluno.items():
        aptos, fora = _particionar_pelo_portao(tracos)
        barrados += len(fora)
        provisorios += sum(1 for t in aptos if not t["apto_para_camada_de_crenca"])
        if not aptos:
            continue
        com_traco += 1
        for linha in _agregar_erros(aptos)["raizes"]:
            balde = por_erro.setdefault(
                linha["erro_id"],
                {
                    "erro_id": linha["erro_id"], "erro_nome": linha["erro_nome"],
                    "intervencao_id": linha["intervencao_id"],
                    "intervencao_nome": linha["intervencao_nome"],
                    "alunos": 0, "ocorrencias": 0, "peso": 0.0,
                },
            )
            balde["alunos"] += 1
            balde["ocorrencias"] += linha["ocorrencias"]
            balde["peso"] = round(balde["peso"] + linha["peso"], 3)
        for linha in _priorizar(aptos, {}):
            if linha["origem"] != "error_trace":
                continue
            balde = por_processo.setdefault(
                linha["processo_id"],
                {
                    "processo_id": linha["processo_id"], "processo_nome": linha["processo_nome"],
                    "dominio_nome": linha["dominio_nome"], "alunos": 0, "peso": 0.0,
                },
            )
            balde["alunos"] += 1
            balde["peso"] = round(balde["peso"] + linha["peso_raiz"], 3)

    # Bateu no teto: a leitura parou no meio da base. Um painel que mostra
    # "as causas raiz da base" a partir de uma amostra truncada SEM avisar é
    # pior que um painel que não existe — foi o mesmo defeito que fazia alunos
    # sumirem calados de `list_students_with_behavior`.
    truncado = vistos >= limite_eventos
    if truncado:
        logger.warning(
            "panorama: teto de %d eventos atingido — o retrato está incompleto. "
            "Suba `limite_eventos` cientes do custo, ou leia por recorte.",
            limite_eventos,
        )

    return {
        "gerado_em": _now_iso(),
        "eventos_lidos": lidos,
        "eventos_vistos": vistos,
        "limite_eventos": limite_eventos,
        "truncado": truncado,
        "alunos_com_erro_anotado": len(por_aluno),
        "alunos_com_traco_valido": com_traco,
        "tracos_barrados_pelo_portao": barrados,
        "tracos_provisorios": provisorios,
        "portao": portao_crenca.modo(),
        "causas_raiz": sorted(por_erro.values(), key=lambda l: (-l["peso"], -l["alunos"])),
        "habilidades": sorted(por_processo.values(), key=lambda l: (-l["peso"], -l["alunos"])),
        "ontology_version": cat["version"],
    }


def detalhe(uid: str, processo_id: str) -> dict[str, Any] | None:
    """O que o aluno vê ao clicar numa habilidade: a evidência (os traços em
    que aquele processo é a raiz), a intervenção e o que praticar.

    `None` quando o processo não existe no catálogo — 404, não uma tela vazia.
    """
    cat = _catalogo()
    if processo_id not in cat["processos"]:
        return None

    hist = _historico(uid)
    aptos, barrados = _particionar_pelo_portao(hist["tracos"])
    do_processo = [t for t in aptos if t["cadeia"][0]["processo_afetado"] == processo_id]
    # A manifestação não seleciona intervenção, mas é evidência legítima de
    # que o processo participou do erro — entra separada e rotulada.
    como_manifestacao = [
        t for t in aptos
        if t not in do_processo and any(e["processo_afetado"] == processo_id for e in t["cadeia"][1:])
    ]

    stats = hist["processo_stats"].get(processo_id) or {"respondidas": 0, "acertos": 0}
    import intervencoes as intervencoes_mod

    plano = intervencoes_mod.montar(
        processo_id=processo_id,
        tracos=do_processo,
        itens_respondidos=hist["itens_respondidos"],
    )

    def _expor(t: dict) -> dict[str, Any]:
        return {
            "trace_id": t["trace_id"],
            "quando": t["timestamp"],
            "item": t["contexto_item"],
            "alternativa_escolhida": t["alternativa_escolhida"],
            "confianca_global": t["confianca_global"],
            "provisorio": not t["apto_para_camada_de_crenca"],
            "porque_essa_alternativa_engana": t["porque_essa_alternativa_engana"],
            "cadeia": [
                {
                    "ordem": e["ordem"],
                    "papel": "raiz" if e["ordem"] == 1 else "consequência",
                    "erro_id": e["erro"],
                    "erro_nome": _nome_erro(e["erro"]),
                    "processo_id": e["processo_afetado"],
                    "processo_nome": _nome_processo(e["processo_afetado"]),
                    "confianca": e["confianca"],
                }
                for e in t["cadeia"]
            ],
        }

    respondidas = stats.get("respondidas", 0)
    return {
        "processo": {"id": processo_id, "nome": _nome_processo(processo_id), **_ancoragem(processo_id)},
        "desempenho": {
            "respondidas": respondidas,
            "acertos": stats.get("acertos", 0),
            "percentual_acerto": round(100 * stats.get("acertos", 0) / respondidas, 1) if respondidas else None,
            "amostra_minima": MIN_RESPOSTAS,
        },
        "provisorio": any(not t["apto_para_camada_de_crenca"] for t in do_processo),
        "evidencia": {
            "como_raiz": [_expor(t) for t in do_processo],
            "como_consequencia": [_expor(t) for t in como_manifestacao],
            "barrados_pelo_portao": len(barrados),
            "sem_revisao_humana": sum(1 for t in do_processo if not t["apto_para_camada_de_crenca"]),
        },
        "intervencao": plano,
        "ontology_version": cat["version"],
        "etrace_version": ETRACE_VERSION,
    }
