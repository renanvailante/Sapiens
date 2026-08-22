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
    mapping: dict[str, dict] = {}
    client = fs.get_firestore()
    for snap in client.collection("itens").stream():
        doc = snap.to_dict() or {}
        # `item` é a chave canônica (Schema 2.2); `pipeline` é a forma anterior,
        # lida para não perder itens sincronizados antes da migração.
        item = doc.get("item") or doc.get("pipeline") or {}
        ec = item.get("estrutura_cognitiva") or {}
        if not ec:
            continue
        for chave in (item.get("item_id") or doc.get("item_id"),
                      item.get("item_hash") or doc.get("item_hash")):
            if chave:
                mapping[chave] = ec
    _ITEM_INDEX = mapping
    return mapping


def _read_firestore_answered(user_id: str) -> dict[str, Any]:
    """Le os eventos de resposta do aluno em students/{uid}/behavior e retorna
    os processos cognitivos acionados.

    Sem IA/LLM. So consulta e agrega — nenhuma inferencia cognitiva e derivada
    daqui. Em particular, o bloco `desempenho` do evento (tempo de resposta,
    numero de tentativas, mudanca de resposta) e deliberadamente IGNORADO: o
    contrato de behavior 1.1 declara que esses campos sao coletados e nao
    alimentam crenca sobre o estado do estudante, por forca de GL-3, aberto.
    """
    client = fs.get_firestore()
    index = _build_item_index()

    answered_procs: set[str] = set()
    answered_comps: set[str] = set()
    answered_doms: set[str] = set()
    matched_items: set[str] = set()
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
        ec = index.get(chave) if chave else None
        if not ec:
            unmatched += 1
            continue
        matched_items.add(chave)
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

    return {
        "processes": sorted(answered_procs),
        "competencias": sorted(answered_comps),
        "dominios": sorted(answered_doms),
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
        agg = await asyncio.to_thread(_read_firestore_answered, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cognitive-profile: leitura do Firestore falhou para %s: %s", user_id, exc)
        return {
            "processes": [], "error_types": [], "misconceptions": [],
            "answered_items": 0, "total_events": 0, "coverage": 0,
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
        "ontology_tree": build_ontology_tree(answered_processes),
    }
