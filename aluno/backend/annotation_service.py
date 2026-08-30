"""Read helpers that expose the annotation layer to any platform feature.

Rule: NEVER mutate the annotation. Just query and aggregate observed
performance on the client (student) side.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

import firestore_service as fs
import portao_crenca
from cognitive_ontology import build_ontology_tree, ontology_version

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
    # NOTA (2026-08-25): este índice ficava cacheado para sempre depois da
    # 1ª chamada, mesmo com `_auto_sync_loop` (server.py) trazendo itens
    # novos do Firestore a cada 5min — qualquer questão sincronizada depois
    # da 1ª geração de perfil cognitivo nunca casava com o índice, e o mapa
    # de habilidades / devolutiva de rodada ficavam travados no snapshot
    # antigo pro resto da vida do processo. `invalidate_item_index()` é
    # chamada por `admin_routes.run_firestore_sync` toda vez que itens novos
    # chegam, então o índice nunca fica mais velho que a última sincronização.
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


def invalidate_item_index() -> None:
    """Descarta o cache de `_build_item_index`. Chamar sempre que itens novos
    chegarem ao Firestore (ver `admin_routes.run_firestore_sync`) — sem isto,
    questões sincronizadas depois da 1ª leitura nunca casam com nenhum
    evento de behavior, pelo resto da vida do processo."""
    global _ITEM_INDEX
    _ITEM_INDEX = None


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
    """
    client = fs.get_firestore()
    index = _build_item_index()

    answered_procs: set[str] = set()
    answered_comps: set[str] = set()
    answered_doms: set[str] = set()
    matched_items: set[str] = set()
    domain_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"respondidas": 0, "acertos": 0})
    total_events = 0
    unmatched = 0
    barrados_pelo_portao = 0

    eventos = [e.to_dict() or {} for e in
               client.collection("students").document(user_id).collection("behavior").stream()]

    # Saneamento 2026-08-26: um evento gravado contra gabarito errado não é
    # editado — recebe um evento de RETIFICAÇÃO que o referencia. Aqui o
    # agregado honra essa correção: o `acertou` da retificação substitui o do
    # original, e o evento de retificação NÃO conta como resposta nova (senão
    # o aluno apareceria tendo respondido a mesma questão duas vezes).
    retificacoes = {
        (ev.get("retificacao") or {}).get("retifica_event_id"): ev
        for ev in eventos
        if ev.get("status") == "retificada" and (ev.get("retificacao") or {}).get("retifica_event_id")
    }

    for ev in eventos:
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
        # EXT-WP1-1.0 L13b: um item sem revisão humana pode ser praticado, e
        # não pode mover o estado cognitivo do aluno. É aqui que o portão tem
        # efeito — no agregado, não na tela.
        if not portao_crenca.pode_alimentar_crenca(item):
            barrados_pelo_portao += 1
            continue
        matched_items.add(chave)
        efetivo = retificacoes.get(ev.get("event_id"), ev)
        acertou = bool((efetivo.get("resposta") or {}).get("acertou"))
        for p in ec.get("processos", []) or []:
            pid = p.get("id") if isinstance(p, dict) else p
            if pid:
                answered_procs.add(pid)
        for cmp in ec.get("competencias", []) or []:
            cid = cmp.get("id") if isinstance(cmp, dict) else cmp
            if cid:
                answered_comps.add(cid)
        for dom in ec.get("dominios", []) or []:
            did = dom.get("id") if isinstance(dom, dict) else dom
            if did:
                answered_doms.add(did)
                stats = domain_stats[did]
                stats["respondidas"] += 1
                if acertou:
                    stats["acertos"] += 1

    return {
        "processes": sorted(answered_procs),
        "competencias": sorted(answered_comps),
        "dominios": sorted(answered_doms),
        "domain_stats": dict(domain_stats),
        "answered_items": len(matched_items),
        "total_events": total_events,
        "barrados_pelo_portao": barrados_pelo_portao,
        "eventos_retificados": len(retificacoes),
        "unmatched_events": unmatched,
    }


async def compute_cognitive_profile(user_id: str) -> dict[str, Any]:
    """Perfil cognitivo do aluno a partir do FIRESTORE (fonte de verdade das
    respostas: students/{uid}/behavior/{event_id}).

    Um no da ontologia fica `answered=true` quando o aluno respondeu ao menos
    uma questao que aciona o processo correspondente. Sem IA/LLM.
    """
    try:
        agg = await asyncio.to_thread(_read_firestore_answered, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cognitive-profile: leitura do Firestore falhou para %s: %s", user_id, exc)
        return {
            "processes": [], "error_types": [], "misconceptions": [],
            "answered_items": 0, "total_events": 0, "coverage": 0,
            "domain_stats": {},
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
