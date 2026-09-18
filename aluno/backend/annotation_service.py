"""Read helpers that expose the annotation layer to any platform feature.

Rule: NEVER mutate the annotation. Just query and aggregate observed
performance on the client (student) side.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

import firestore_service as fs
import prioridade_enem
from cognitive_ontology import build_ontology_tree, ontology_version
# Só o índice domínio->eixo: a contagem por eixo precisa acontecer evento a
# evento, aqui, para que uma questão não conte duas vezes no mesmo eixo.
# Nenhuma decisão pedagógica desta camada depende do módulo cosmético.
from cosmetic_skills_map import DOMAIN_TO_HUB

logger = logging.getLogger("sapiens.cognitive")

# Cache: item_id | item_hash -> estrutura_cognitiva (Firestore `itens`).
_ITEM_INDEX: dict[str, dict] | None = None


_db = None
def set_db(db):
    global _db
    _db = db


async def find_annotation_for_question(banca: str, ano: int, prova: str, numero: int) -> dict | None:
    """Busca pelos quatro campos de `fonte` que identificam a questão na prova.

    `prova` substitui o antigo `caderno`: é o nome do campo no Schema 2.2, e é
    um dos quatro componentes do `item_id` determinístico.
    """
    return await _db.question_annotations.find_one(
        {"banca": banca, "ano": ano, "prova": prova, "numero": numero},
        {"_id": 0},
    )


async def find_annotation_by_id(item_id: str) -> dict | None:
    return await _db.question_annotations.find_one({"item_id": item_id}, {"_id": 0})


async def list_annotations(filters: dict | None = None, limit: int = 500) -> list[dict]:
    q = filters or {}
    cursor = _db.question_annotations.find(q, {"_id": 0}).sort("received_at", -1).limit(limit)
    return await cursor.to_list(limit)


def _build_item_index(force: bool = False) -> dict[str, dict]:
    """Indexa a estrutura cognitiva dos itens por `item_id` **e** por `item_hash`.

    Chave de junção com o evento de behavior, em ordem de preferência:

    * `item_id` — identidade estável do item, invariável por contrato entre
      pipeline, Firestore, aluno e professor (Schema 2.2).
    * `item_hash` — conteúdo respondido; ainda usado porque um item pode ter sido
      editado depois da resposta, e o evento aponta para o conteúdo daquele
      momento.

    Até 2026-08-21 este índice **recalculava** o hash sobre `pipeline.questao` e
    lia `pipeline.estrutura_cognitiva`, chave que o pipeline nunca escrevia —
    resultado: nenhum evento casava com nenhum item, e todo perfil cognitivo saía
    vazio sem nenhum erro visível. Agora o hash é LIDO do item, que é onde o
    contrato manda que ele esteja.
    """
    global _ITEM_INDEX
    if _ITEM_INDEX is not None and not force:
        return _ITEM_INDEX
    mapping: dict[str, dict] = {}
    client = fs.get_firestore()
    for snap in client.collection("itens").stream():
        doc = snap.to_dict() or {}
        # `item` é a chave canônica (Schema 2.2); `pipeline` é a forma anterior,
        # lida para não perder itens sincronizados antes da migração.
        item = doc.get("item") or doc.get("pipeline") or {}
        if not item.get("estrutura_cognitiva"):
            continue
        # Guarda o item inteiro (não só `estrutura_cognitiva`): o resumo de
        # sessão (`montar_contexto_sessao`) também precisa de `distratores`
        # para citar por que uma alternativa errada é um engano plausível.
        for chave in (item.get("item_id") or doc.get("item_id"),
                      item.get("item_hash") or doc.get("item_hash")):
            if chave:
                mapping[chave] = item
    _ITEM_INDEX = mapping
    return mapping


# ---------------------------------------------------------------------------
# Cache do agregado derivado do Firestore — 1 leitura no lugar de N
# ---------------------------------------------------------------------------
#
# `_read_firestore_answered` e `_read_firestore_desempenho_detalhado` varrem a
# coleção `students/{uid}/behavior` INTEIRA, sem limite, e são chamadas por
# `/diagnostico`, `/cognitive-profile`, `/skills-map`, o laço diário de perfil
# cognitivo e a abertura de sessão da Mentis. Um aluno com 400 respostas
# custava 400 leituras do Firestore POR ABERTURA de qualquer uma dessas telas —
# e recarregar a página pagava tudo de novo.
#
# Isso é exatamente a forma do incidente de 2026-09-04 (cota diária do Firestore
# esgotada, 429 em toda rota autenticada), só que na dimensão do aluno em vez da
# do acervo: ali era um laço relendo 268 itens a cada 5 min, aqui é a tela mais
# usada do produto relendo o histórico a cada clique. Com dez alunos ativos
# revisitando o diagnóstico, a cota vai embora do mesmo jeito.
#
# A chave de invalidação é `total_respostas`, que `firestore_service.ler_agregado`
# devolve em UMA leitura e que `_atualizar_agregado` incrementa a cada resposta:
# aluno respondeu algo novo -> contagem muda -> chave muda -> recalcula. É o
# mesmo princípio que `perfil_cognitivo_service.atualizar_todos_os_perfis` já
# usava para decidir se valia a pena reprocessar alguém; aqui ele passa a valer
# para toda leitura, não só para o laço diário.
#
# Duas salvaguardas contra cache velho:
#  * `ontology_version()` entra na chave — reanotação do catálogo invalida tudo;
#  * TTL de 6h, porque `_atualizar_agregado` pode falhar em silêncio (ele loga e
#    segue, para não perder a resposta do aluno). Sem o TTL, uma contagem que
#    parou de subir congelaria o perfil para sempre.
#
# O cache vive no Mongo, não no Firestore: é justamente o banco que não tem cota
# de leitura para estourar.

_CACHE_DERIVADO_TTL_SEGUNDOS = 6 * 3600
# v2 (2026-09-12): o agregado detalhado passou a contar também por DISCIPLINA
# (`disciplina_stats`, insumo de `prioridade_enem`). Um documento gravado pela
# v1 não tem esse campo, e servi-lo daria a todo aluno com cache quente um
# cronograma montado como se ele nunca tivesse respondido nada. A versão na
# chave é o que garante que cache velho simplesmente não é encontrado.
# v3 (2026-09-15): o agregado "answered" passou a contar também por EIXO
# cosmético (`hub_stats`), que é o insumo do percentual do Mapa de
# Habilidades. Documento gravado pela v2 não tem o campo, e servi-lo daria
# mapa zerado a todo aluno com cache quente.
# v4 (2026-09-17): o agregado "desempenho" passou a carregar também a
# TELEMETRIA DESCRITIVA (`telemetria_descritiva`) — as séries por dia, hora,
# dia da semana, faixa de tempo e origem que alimentam os gráficos do painel
# do aluno. Documento gravado pela v3 não tem o campo, e servi-lo daria
# painel vazio a todo aluno com cache quente.
_CACHE_DERIVADO_VERSAO = "v4"


async def _agregado_com_cache(escopo: str, user_id: str, ler_do_firestore) -> dict[str, Any]:
    """Devolve o agregado derivado de `escopo`, do cache quando possível.

    Nunca é o caminho crítico: qualquer falha do cache (Mongo ausente, leitura
    ou gravação com erro) cai de volta na leitura direta do Firestore. Cache é
    otimização de custo, jamais uma dependência para o resultado existir.
    """
    if _db is None:  # testes offline e qualquer chamador sem Mongo ligado
        return await asyncio.to_thread(ler_do_firestore, user_id)

    try:
        agregado = await asyncio.to_thread(fs.ler_agregado, user_id)
        contagem = int(agregado.get("total_respostas") or 0)
    except Exception as exc:  # noqa: BLE001
        # Sem a contagem não há chave de invalidação confiável. Recalcular é
        # caro, mas servir dado potencialmente errado é pior.
        logger.warning("cache derivado (%s): agregado indisponível para %s: %s", escopo, user_id, exc)
        return await asyncio.to_thread(ler_do_firestore, user_id)

    chave = ":".join((_CACHE_DERIVADO_VERSAO, escopo, user_id, str(contagem), ontology_version() or ""))
    agora = datetime.now(timezone.utc)
    try:
        doc = await _db.perfil_derivado_cache.find_one({"_id": chave})
        if doc and (doc.get("expira_em") or "") > agora.isoformat():
            return doc["valor"]
    except Exception:  # noqa: BLE001
        logger.exception("cache derivado (%s): leitura falhou — seguindo para o Firestore", escopo)

    valor = await asyncio.to_thread(ler_do_firestore, user_id)
    try:
        await _db.perfil_derivado_cache.update_one(
            {"_id": chave},
            {"$set": {
                "valor": valor,
                "user_id": user_id,
                "escopo": escopo,
                "total_respostas": contagem,
                "expira_em": (agora + timedelta(seconds=_CACHE_DERIVADO_TTL_SEGUNDOS)).isoformat(),
                # Campo BSON de data só para o TTL do Mongo — sobre string ISO o
                # TTL não roda (mesma armadilha documentada em `db_indexes`).
                "expurgo_em_dt": agora + timedelta(days=7),
            }},
            upsert=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("cache derivado (%s): gravação falhou — a próxima chamada relê o Firestore", escopo)
    return valor


def _read_firestore_answered(user_id: str) -> dict[str, Any]:
    """Le os eventos de resposta do aluno em students/{uid}/behavior e retorna
    os processos cognitivos acionados.

    Sem IA/LLM. So consulta e agrega — nenhuma inferencia cognitiva e derivada
    daqui. Em particular, o bloco `desempenho` do evento (tempo de resposta,
    numero de tentativas, mudanca de resposta) e deliberadamente IGNORADO: o
    contrato de behavior 1.1 declara que esses campos sao coletados e nao
    alimentam crenca sobre o estado do estudante, por forca de GL-3, aberto.

    `domain_stats`: contagem pura de respondidas/acertos por domínio (id) —
    mesmo princípio acima (agregação determinística, sem atribuição causal).
    Alimenta o mapa de habilidades cosmético (ver cosmetic_skills_map.py),
    nunca a camada de crença real.

    `hub_stats`: a mesma contagem colapsada nos 6 eixos cosméticos, com uma
    diferença que importa — cada questão conta UMA vez por eixo. Um item
    anotado com dois domínios do mesmo eixo (o eixo 5 agrupa três) aparece
    duas vezes em `domain_stats` e uma só aqui; é esta a contagem que vira o
    percentual do mapa, e somar domínios lá dava um "40 acertos" que se
    atingia com menos da metade das questões. Chave em string porque este
    agregado é gravado no cache do Mongo.
    """
    client = fs.get_firestore()
    index = _build_item_index()

    answered_procs: set[str] = set()
    answered_comps: set[str] = set()
    answered_doms: set[str] = set()
    matched_items: set[str] = set()
    domain_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"respondidas": 0, "acertos": 0})
    hub_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"respondidas": 0, "acertos": 0})
    total_events = 0
    unmatched = 0

    events = client.collection("students").document(user_id).collection("behavior").stream()
    for e in events:
        ev = e.to_dict() or {}
        # considera apenas eventos de resposta efetiva
        if ev.get("status") not in (None, "respondida"):
            continue
        total_events += 1
        chave = next(
            (k for k in (ev.get("item_id"), ev.get("item_hash")) if k and k in index),
            None,
        )
        item = index.get(chave) if chave else None
        ec = item.get("estrutura_cognitiva") if item else None
        if not ec:
            unmatched += 1
            continue
        matched_items.add(chave)
        acertou = bool((ev.get("resposta") or {}).get("acertou"))
        for p in ec.get("processos", []) or []:
            pid = p.get("id") if isinstance(p, dict) else p
            if pid:
                answered_procs.add(pid)
        for cmp in ec.get("competencias", []) or []:
            cid = cmp.get("id") if isinstance(cmp, dict) else cmp
            if cid:
                answered_comps.add(cid)
        doms_do_item = {
            (dom.get("id") if isinstance(dom, dict) else dom)
            for dom in ec.get("dominios", []) or []
        } - {None, ""}
        for did in doms_do_item:
            answered_doms.add(did)
            stats = domain_stats[did]
            stats["respondidas"] += 1
            if acertou:
                stats["acertos"] += 1
        for hub_id in {DOMAIN_TO_HUB[d] for d in doms_do_item if d in DOMAIN_TO_HUB}:
            stats = hub_stats[str(hub_id)]
            stats["respondidas"] += 1
            if acertou:
                stats["acertos"] += 1

    return {
        "processes": sorted(answered_procs),
        "competencias": sorted(answered_comps),
        "dominios": sorted(answered_doms),
        "domain_stats": dict(domain_stats),
        "hub_stats": dict(hub_stats),
        "answered_items": len(matched_items),
        "total_events": total_events,
        "unmatched_events": unmatched,
    }


async def compute_cognitive_profile(user_id: str) -> dict[str, Any]:
    """Perfil cognitivo do aluno a partir do FIRESTORE (fonte de verdade das
    respostas: students/{uid}/behavior/{event_id}).

    Um no da ontologia fica `answered=true` quando o aluno respondeu ao menos
    uma questao que aciona o processo correspondente. Sem IA/LLM.
    """
    try:
        agg = await _agregado_com_cache("answered", user_id, _read_firestore_answered)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cognitive-profile: leitura do Firestore falhou para %s: %s", user_id, exc)
        return {
            "processes": [], "error_types": [], "misconceptions": [],
            "answered_items": 0, "total_events": 0, "coverage": 0,
            "domain_stats": {},
            "hub_stats": {},
            "ontology_version": ontology_version(),
            "ontology_tree": build_ontology_tree(set()),
        }

    answered_processes = set(agg["processes"])
    return {
        # `error_types` e `misconceptions` permanecem vazios de propósito: a
        # atribuição de causa de erro a um estudante real é o Error Trace, que
        # tem contrato próprio (ETRACE-1.0) e exige confiança ponderada por elo.
        # Derivá-la aqui, do simples fato de o aluno ter respondido, produziria
        # atribuição determinística — proibida pela Constituição §4.4.
        "processes": [],
        "error_types": [],
        "misconceptions": [],
        "ontology_version": ontology_version(),
        "answered_processes": agg["processes"],
        "answered_competencias": agg["competencias"],
        "answered_dominios": agg["dominios"],
        "answered_items": agg["answered_items"],
        "total_events": agg["total_events"],
        "unmatched_events": agg["unmatched_events"],
        "domain_stats": agg["domain_stats"],
        "hub_stats": agg.get("hub_stats") or {},
        "ontology_tree": build_ontology_tree(answered_processes),
    }


# ---------- Resumo de sessão (narrativa, não determinística) ----------
#
# Diferente de `compute_cognitive_profile` acima: isto NÃO fica em
# `answered_processes`/`error_types` vazios. A saída é texto de apresentação
# gerado por LLM (ver `ai_service.diagnose_sessao`), no mesmo limite de
# contrato que `ai_service.diagnose` já documenta — nunca IDs de catálogo,
# nunca persistido como estrutura cognitiva, nunca framing de certeza. A
# garantia não depende só do prompt: os IDs são trocados por nomes ANTES de
# chegar ao modelo, aqui.

_NOMES_CATALOGO: dict[str, str] | None = None


def _catalogo_nomes() -> dict[str, str]:
    """`id` -> `nome` de todo processo/domínio/competência da ontologia
    canônica. Só para dar nome legível ao aluno — nunca para reescrever a
    anotação (que continua guardada só por ID, como o contrato exige)."""
    global _NOMES_CATALOGO
    if _NOMES_CATALOGO is not None:
        return _NOMES_CATALOGO
    from canonical_ontology import load_ontology

    onto = load_ontology()
    out: dict[str, str] = {}
    for chave in ("processos_cognitivos", "dominios", "competencias"):
        for node in onto.get(chave) or []:
            if isinstance(node, dict) and node.get("id"):
                out[node["id"]] = node.get("nome") or node["id"]
    _NOMES_CATALOGO = out
    return out


def _nomes_de(ids: list[Any], catalogo: dict[str, str]) -> list[str]:
    return sorted({catalogo.get(i, i) for i in ids if i})


def _distrator_explicacao(item: dict, alternativa: str) -> str | None:
    for d in item.get("distratores") or []:
        if isinstance(d, dict) and d.get("alternativa") == alternativa:
            explicacao = d.get("explicacao")
            if explicacao:
                return explicacao
    return None


def montar_contexto_sessao(respostas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`respostas`: `[{item_id, alternativa_escolhida, acertou}]`, na ordem em
    que o aluno respondeu nesta sessão.

    Devolve o mesmo número de entradas, cada uma já sem ID de catálogo algum
    — só nomes em português e, quando errou, a explicação (já em texto
    natural, escrita por quem anotou o item) de por que aquela alternativa é
    um engano plausível. É essa lista, e não os eventos brutos, que vira o
    prompt de `ai_service.diagnose_sessao`.
    """
    index = _build_item_index()
    catalogo = _catalogo_nomes()
    contexto: list[dict[str, Any]] = []
    for r in respostas:
        item = index.get(r.get("item_id")) or {}
        ec = item.get("estrutura_cognitiva") or {}
        entrada: dict[str, Any] = {
            "acertou": bool(r.get("acertou")),
            "processos": _nomes_de([p.get("id") for p in (ec.get("processos") or []) if isinstance(p, dict)], catalogo),
            "dominios": _nomes_de([d.get("id") for d in (ec.get("dominios") or []) if isinstance(d, dict)], catalogo),
            "competencias": _nomes_de([c.get("id") for c in (ec.get("competencias") or []) if isinstance(c, dict)], catalogo),
        }
        if not entrada["acertou"]:
            explicacao = _distrator_explicacao(item, r.get("alternativa_escolhida") or "")
            if explicacao:
                entrada["porque_essa_escolha_e_um_engano_comum"] = explicacao
        contexto.append(entrada)
    return contexto


# ---------- Resumo de rodada (determinístico, sem IA) ----------
#
# Diferente de `montar_contexto_sessao`/`ai_service.diagnose_sessao` (narrativo,
# gerado por LLM): isto é contagem pura sobre o que já está anotado no item,
# sem nenhuma chamada a modelo e sem nenhuma explicação causal do erro. Um
# domínio/processo/competência só vira "padrão" quando aparece em >=2 erros da
# rodada — um único erro isolado não sustenta a afirmação de um padrão, é só
# dado insuficiente (por isso a rodada nunca "inventa" um padrão a partir de 1
# ocorrência).
_PADRAO_FREQUENCIA_MINIMA = 2


def resumo_rodada(respostas: list[dict[str, Any]]) -> dict[str, Any]:
    """`respostas`: `[{item_id, alternativa_escolhida, acertou}]` da rodada.

    Devolve acertos/erros/percentual e, só quando sustentado por repetição
    real nos dados, os domínios/competências/processos mais associados aos
    ERROS da rodada — nunca uma explicação de por que o aluno errou.
    """
    index = _build_item_index()
    catalogo = _catalogo_nomes()

    total = len(respostas)
    acertos = sum(1 for r in respostas if r.get("acertou"))
    erros = total - acertos

    contagem: dict[str, dict[str, int]] = {
        "processo": defaultdict(int),
        "dominio": defaultdict(int),
        "competencia": defaultdict(int),
    }
    erros_com_anotacao = 0
    chave_por_tipo = {"processo": "processos", "dominio": "dominios", "competencia": "competencias"}

    for r in respostas:
        if r.get("acertou"):
            continue
        item = index.get(r.get("item_id")) or {}
        ec = item.get("estrutura_cognitiva") or {}
        if not ec:
            continue
        erros_com_anotacao += 1
        for tipo, chave_ec in chave_por_tipo.items():
            for node in ec.get(chave_ec) or []:
                nid = node.get("id") if isinstance(node, dict) else node
                if nid:
                    contagem[tipo][nid] += 1

    padroes: list[dict[str, Any]] = []
    for tipo in ("processo", "dominio", "competencia"):
        ranking = sorted(contagem[tipo].items(), key=lambda kv: -kv[1])
        for nid, freq in ranking:
            if freq >= _PADRAO_FREQUENCIA_MINIMA:
                # `id` fica no registro para permitir agregação futura (ex.: o
                # mapa de habilidades cosmético) sem precisar casar por nome —
                # mas o nome real nunca é enviado a esse mapa, só o `id`.
                padroes.append({"tipo": tipo, "id": nid, "nome": catalogo.get(nid, nid), "frequencia": freq})

    return {
        "acertos": acertos,
        "erros": erros,
        "total": total,
        "percentual_acerto": round(100 * acertos / total, 1) if total else 0.0,
        "padroes_de_erro": padroes,
        "dados_suficientes_padrao": erros_com_anotacao >= _PADRAO_FREQUENCIA_MINIMA,
    }


# ---------- Diagnóstico real (determinístico, nomes reais, sem IA) ----------
#
# Diferente do mapa de habilidades cosmético (`cosmetic_skills_map.py`), que
# expõe só rótulos genéricos de hub por decisão de produto: isto mostra nome
# real de domínio/competência/processo, com amostra mínima declarada antes de
# afirmar um ponto fraco ou forte — mesmo princípio de `compute_feedback`
# (`_FEEDBACK_MIN_RESPOSTAS`), aplicado num nível mais fino que domínio.
#
# NÃO é um Error Trace (contrato ETRACE-1.0, `pipeline/docs/error-trace/`): não
# atribui causa de erro a uma resposta individual do aluno. O produtor de
# Error Trace está deliberadamente fora de escopo (`DEPLOY.md` §7) até haver
# especificação estatística. O que `padroes_associados` faz abaixo é mais
# modesto e não exige essa especificação: quando um PROCESSO tem desempenho
# real fraco (medido, com amostra) e esse processo tem exatamente um Tipo de
# Erro catalogado (sem ambiguidade — nunca escolhido por chute entre
# candidatos), mostra o fato geral do catálogo ("processos assim costumam
# falhar por X") e a intervenção já catalogada para ele. Isso nunca vira "você
# cometeu este erro" — só "seu desempenho aqui é fraco, e a causa catalogada
# mais comum para este processo é X".
_DIAGNOSTICO_MIN_AMOSTRA = 3


def _erros_por_processo() -> dict[str, list[dict]]:
    """`processo_id` -> Tipos de Erro catalogados para ele (0, 1 ou mais)."""
    from canonical_ontology import load_ontology

    onto = load_ontology()
    idx: dict[str, list[dict]] = defaultdict(list)
    for erro in onto.get("tipos_erro") or []:
        for pid in erro.get("processos_cognitivos") or []:
            idx[pid].append(erro)
    return dict(idx)


def _intervencoes_por_id() -> dict[str, dict]:
    from canonical_ontology import load_ontology

    onto = load_ontology()
    return {i["id"]: i for i in (onto.get("intervencoes_pedagogicas") or []) if i.get("id")}


# ---------------------------------------------------------------------------
# TELEMETRIA DESCRITIVA — o insumo dos gráficos do painel do aluno
#
# Fronteira declarada, porque ela é sutil e fácil de atravessar sem perceber:
# o bloco `desempenho` do evento (tempo de resposta, número de tentativas,
# mudança de resposta) é **coletado e não alimenta crença sobre o estado
# cognitivo do estudante** — GL-3, aberto, contrato de behavior 1.1. É por
# isso que `_read_firestore_answered` o ignora, e continua ignorando.
#
# O que este bloco faz é outra coisa, e a diferença não é de grau: ele
# DESCREVE ao aluno o que o aluno fez ("você respondeu 40 questões esta
# semana", "você responde mais à noite"), sem inferir nada sobre o que ele
# sabe. Nenhum número daqui entra em ranking de ponto forte/fraco, em fila de
# revisão, em cronograma, no dossiê da Mentis ou em qualquer caminho que
# atribua causa a um erro. Por isso a telemetria sai do agregado numa chave
# própria (`telemetria_descritiva`) que `compute_diagnostico_real` não lê: a
# separação é de código, não só de intenção.
#
# Ela viaja junto do agregado caro de propósito — é a MESMA varredura de
# eventos que o diagnóstico já fazia. Um painel de gráficos que custasse uma
# segunda varredura do histórico por aluno é exatamente o que derrubou o app
# em 04/09 (ver `project_aluno_disciplina_leitura_firestore`).
# ---------------------------------------------------------------------------

# Faixas de tempo por questão. Não são juízo sobre o aluno: são três gavetas
# para uma pergunta que ele consegue responder sozinho olhando o gráfico —
# "eu acerto mais quando vou rápido ou quando penso mais?".
FAIXA_RAPIDA_SEGUNDOS = 45
FAIXA_LONGA_SEGUNDOS = 150

# Abaixo disto o tempo não foi registrado (fluxos antigos e o banco de treino
# gravavam 0). Zero não é "respondeu em zero segundo" — é silêncio, e silêncio
# não pode virar barra de gráfico.
_TEMPO_MINIMO_CONFIAVEL = 2


def _zero_contagem() -> dict[str, int]:
    return {"respondidas": 0, "acertos": 0}


def _nova_telemetria() -> dict[str, Any]:
    return {
        "por_dia": defaultdict(_zero_contagem),
        "por_hora": defaultdict(_zero_contagem),
        "por_dia_semana": defaultdict(_zero_contagem),
        "por_faixa_de_tempo": defaultdict(_zero_contagem),
        "por_decisao": defaultdict(_zero_contagem),
        "por_origem": defaultdict(_zero_contagem),
        "frente_por_semana": defaultdict(_zero_contagem),
        "tempo_total_segundos": 0.0,
        "respostas_com_tempo": 0,
    }


def _momento_local(timestamp_iso: Any) -> datetime | None:
    """O instante do evento no fuso do aluno, ou None se não der para saber.

    Mesmo fuso do resto do produto (`firestore_service.dia_local`): em UTC,
    quem responde às 22h apareceria estudando no dia seguinte, e o gráfico de
    horários — que é justamente sobre a noite — sairia deslocado em 3 horas.
    """
    if not isinstance(timestamp_iso, str) or not timestamp_iso:
        return None
    try:
        momento = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(fs.ZONA_BRASIL)


def segunda_da_semana(dia_iso: str) -> str:
    """`YYYY-MM-DD` de qualquer dia -> `YYYY-MM-DD` da segunda daquela semana.

    A semana do aluno começa na segunda em todo o produto (cronograma, liga,
    missões); um gráfico semanal que começasse no domingo mostraria outra
    divisão da mesma vida.
    """
    d = date.fromisoformat(dia_iso)
    return (d - timedelta(days=d.weekday())).isoformat()


def _faixa_de_tempo(segundos: float) -> str | None:
    if segundos < _TEMPO_MINIMO_CONFIAVEL:
        return None
    if segundos < FAIXA_RAPIDA_SEGUNDOS:
        return "rapido"
    if segundos <= FAIXA_LONGA_SEGUNDOS:
        return "medio"
    return "longo"


def _somar_telemetria(tel: dict[str, Any], ev: dict[str, Any], *, acertou: bool) -> str | None:
    """Acumula UM evento respondido. Devolve o dia local do evento (ou None),
    porque quem chama usa esse dia para a série por frente."""
    def _marcar(balde: dict[str, dict[str, int]], chave: str) -> None:
        alvo = balde[chave]
        alvo["respondidas"] += 1
        if acertou:
            alvo["acertos"] += 1

    momento = _momento_local(ev.get("timestamp"))
    dia = None
    if momento is not None:
        dia = momento.date().isoformat()
        _marcar(tel["por_dia"], dia)
        _marcar(tel["por_hora"], str(momento.hour))
        _marcar(tel["por_dia_semana"], str(momento.weekday()))

    desempenho = ev.get("desempenho") or {}
    try:
        segundos = float(desempenho.get("tempo_resposta_segundos") or 0)
    except (TypeError, ValueError):
        segundos = 0.0
    faixa = _faixa_de_tempo(segundos)
    if faixa:
        _marcar(tel["por_faixa_de_tempo"], faixa)
        tel["tempo_total_segundos"] += segundos
        tel["respostas_com_tempo"] += 1
        # Só quem tem tempo registrado entra na conta de "mudou de resposta":
        # os fluxos que não medem tempo também não medem mudança, e contá-los
        # como "manteve" inventaria uma decisão que ninguém observou.
        _marcar(tel["por_decisao"], "mudou" if desempenho.get("mudou_resposta") else "manteve")

    origem = (ev.get("contexto") or {}).get("tipo") or "outro"
    _marcar(tel["por_origem"], str(origem))
    return dia


def _fechar_telemetria(tel: dict[str, Any]) -> dict[str, Any]:
    """Converte os `defaultdict` em dicionários simples — o agregado é gravado
    no Mongo, e `defaultdict` não atravessa BSON como dict puro."""
    return {
        chave: (dict(valor) if isinstance(valor, defaultdict) else valor)
        for chave, valor in tel.items()
    }


def _read_firestore_desempenho_detalhado(user_id: str) -> dict[str, Any]:
    """Como `_read_firestore_answered`, mas guarda respondidas/acertos por
    PROCESSO além de domínio/competência — granularidade que o diagnóstico
    real precisa e que o mapa cosmético não expõe. Mesma regra: sem IA, sem
    inferência causal, só contagem determinística por evento."""
    client = fs.get_firestore()
    index = _build_item_index()

    def _zero():
        return {"respondidas": 0, "acertos": 0}

    dominio_stats: dict[str, dict[str, int]] = defaultdict(_zero)
    competencia_stats: dict[str, dict[str, int]] = defaultdict(_zero)
    processo_stats: dict[str, dict[str, int]] = defaultdict(_zero)
    # Por DISCIPLINA (Matemática, Biologia, ...), no mesmo laço e sem nenhuma
    # leitura a mais. É o insumo de `prioridade_enem`: a ontologia é cognitiva
    # (processo, domínio, competência) e nunca soube dizer "este aluno vai mal
    # em Química" — que é justamente a unidade em que a prova é dividida e em
    # que o ganho de ponto se decide.
    disciplina_stats: dict[str, dict[str, int]] = defaultdict(_zero)
    telemetria = _nova_telemetria()
    total_events = 0
    matched_events = 0
    unmatched_events = 0

    events = client.collection("students").document(user_id).collection("behavior").stream()
    for e in events:
        ev = e.to_dict() or {}
        if ev.get("status") not in (None, "respondida"):
            continue
        total_events += 1
        acertou = bool((ev.get("resposta") or {}).get("acertou"))
        # A telemetria conta TODA resposta, inclusive a de item que a ontologia
        # não alcança (banco de treino, questão gerada, curso). "Quantas
        # questões eu respondi esta semana" é uma pergunta sobre o esforço do
        # aluno, e o esforço não some porque o item não está anotado.
        dia = _somar_telemetria(telemetria, ev, acertou=acertou)

        chave = next(
            (k for k in (ev.get("item_id"), ev.get("item_hash")) if k and k in index),
            None,
        )
        item = index.get(chave) if chave else None
        ec = item.get("estrutura_cognitiva") if item else None
        if not ec:
            unmatched_events += 1
            continue
        matched_events += 1

        frente = prioridade_enem.classificar_disciplina(((item or {}).get("fonte") or {}).get("disciplina"))
        if frente:
            disciplina_stats[frente]["respondidas"] += 1
            if acertou:
                disciplina_stats[frente]["acertos"] += 1
            if dia:
                alvo = telemetria["frente_por_semana"][f"{frente}|{segunda_da_semana(dia)}"]
                alvo["respondidas"] += 1
                if acertou:
                    alvo["acertos"] += 1

        for chave_ec, alvo in (
            ("dominios", dominio_stats),
            ("competencias", competencia_stats),
            ("processos", processo_stats),
        ):
            for node in ec.get(chave_ec) or []:
                nid = node.get("id") if isinstance(node, dict) else node
                if not nid:
                    continue
                stats = alvo[nid]
                stats["respondidas"] += 1
                if acertou:
                    stats["acertos"] += 1

    return {
        "dominio_stats": dict(dominio_stats),
        "competencia_stats": dict(competencia_stats),
        "processo_stats": dict(processo_stats),
        "disciplina_stats": dict(disciplina_stats),
        "telemetria_descritiva": _fechar_telemetria(telemetria),
        "total_events": total_events,
        "matched_events": matched_events,
        "unmatched_events": unmatched_events,
    }


def _ranking_real(
    stats: dict[str, dict[str, int]],
    catalogo: dict[str, str],
    *,
    min_amostra: int,
    ascending: bool,
) -> list[dict[str, Any]]:
    linhas = []
    for nid, s in stats.items():
        respondidas = s.get("respondidas", 0)
        if respondidas < min_amostra:
            continue
        acertos = s.get("acertos", 0)
        pct = round(100 * acertos / respondidas, 1) if respondidas else 0.0
        linhas.append({
            "id": nid,
            "nome": catalogo.get(nid, nid),
            "acertos": acertos,
            "respondidas": respondidas,
            "percentual_acerto": pct,
        })
    linhas.sort(key=lambda r: r["percentual_acerto"], reverse=not ascending)
    return linhas


def _fortes_fracos(stats: dict[str, dict[str, int]], catalogo: dict[str, str]) -> dict[str, list[dict]]:
    return {
        "fracos": _ranking_real(stats, catalogo, min_amostra=_DIAGNOSTICO_MIN_AMOSTRA, ascending=True)[:8],
        "fortes": _ranking_real(stats, catalogo, min_amostra=_DIAGNOSTICO_MIN_AMOSTRA, ascending=False)[:8],
    }


async def agregado_desempenho(user_id: str) -> dict[str, Any]:
    """O agregado caro de desempenho, servido do cache quando possível.

    Público porque UMA varredura de eventos serve duas telas: o diagnóstico
    (`compute_diagnostico_real`) e o painel de gráficos do aluno
    (`perfil_painel`). Quem precisa dos dois pede o agregado uma vez e passa
    adiante, em vez de pedir cada leitura por conta própria — no cache quente
    cada pedido ainda custa uma leitura do documento do aluno no Firestore só
    para descobrir a chave de invalidação.
    """
    return await _agregado_com_cache("desempenho", user_id, _read_firestore_desempenho_detalhado)


def telemetria_de(agregado: dict[str, Any] | None) -> dict[str, Any]:
    """A telemetria descritiva de dentro do agregado, ou `{}`.

    Deliberadamente NÃO é devolvida por `compute_diagnostico_real`: o caminho
    que forma crença sobre o aluno não deve nem ver estes campos (ver a nota
    de fronteira acima de `_nova_telemetria`).
    """
    return (agregado or {}).get("telemetria_descritiva") or {}


async def compute_diagnostico_real(
    user_id: str, *, agregado: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Diagnóstico real do aluno: desempenho medido (com amostra mínima) por
    domínio/competência/processo, com nomes reais da ontologia, mais os
    processos fracos que têm exatamente um Tipo de Erro catalogado sem
    ambiguidade — ver nota de escopo acima da seção.

    `agregado` já lido por quem chama evita repetir a leitura; omitido, é
    buscado aqui como sempre foi.
    """
    try:
        agg = agregado if agregado is not None else await agregado_desempenho(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("diagnostico-real: leitura do Firestore falhou para %s: %s", user_id, exc)
        vazio = {"fortes": [], "fracos": []}
        return {
            "por_dominio": vazio, "por_competencia": vazio, "por_processo": vazio,
            "por_disciplina": {},
            "padroes_associados": [],
            "total_events": 0, "matched_events": 0, "unmatched_events": 0,
            "coverage": 0.0, "amostra_minima": _DIAGNOSTICO_MIN_AMOSTRA,
            "ontology_version": ontology_version(),
        }

    catalogo = _catalogo_nomes()
    disciplina_stats = agg.get("disciplina_stats") or {}
    por_dominio = _fortes_fracos(agg["dominio_stats"], catalogo)
    por_competencia = _fortes_fracos(agg["competencia_stats"], catalogo)
    por_processo = _fortes_fracos(agg["processo_stats"], catalogo)

    erros_idx = _erros_por_processo()
    intervencoes_idx = _intervencoes_por_id()
    padroes_associados = []
    for ponto in por_processo["fracos"]:
        candidatos = erros_idx.get(ponto["id"]) or []
        if len(candidatos) != 1:
            continue  # 0 = não catalogado nesta versão; >1 = ambíguo — nunca escolhido por chute
        erro = candidatos[0]
        intervencao = intervencoes_idx.get(erro.get("intervencao"))
        padroes_associados.append({
            "processo_id": ponto["id"],
            "processo_nome": ponto["nome"],
            "percentual_acerto": ponto["percentual_acerto"],
            "respondidas": ponto["respondidas"],
            "erro_id": erro["id"],
            "erro_nome": erro.get("nome", erro["id"]),
            "erro_evidencia_observavel": erro.get("evidencia_observavel", ""),
            "intervencao_id": erro.get("intervencao"),
            "intervencao_nome": (intervencao or {}).get("nome", erro.get("intervencao")),
        })

    total = agg["total_events"]
    coverage = round(100 * agg["matched_events"] / total, 1) if total else 0.0

    return {
        "por_dominio": por_dominio,
        "por_competencia": por_competencia,
        "por_processo": por_processo,
        "por_disciplina": disciplina_stats,
        "padroes_associados": padroes_associados[:8],
        "total_events": total,
        "matched_events": agg["matched_events"],
        "unmatched_events": agg["unmatched_events"],
        "coverage": coverage,
        "amostra_minima": _DIAGNOSTICO_MIN_AMOSTRA,
        "ontology_version": ontology_version(),
    }
