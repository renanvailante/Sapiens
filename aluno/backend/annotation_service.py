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
from cognitive_ontology import build_ontology_tree

logger = logging.getLogger("sapiens.cognitive")

# Cache: item_hash -> estrutura_cognitiva (built once from Firestore `itens`).
_ITEM_HASH_TO_EC: dict[str, dict] | None = None


_db = None
def set_db(db):
    global _db
    _db = db


async def find_annotation_for_question(banca: str, ano: int, caderno: str, numero: int) -> dict | None:
    return await _db.question_annotations.find_one(
        {"banca": banca, "ano": ano, "caderno": caderno, "numero": numero},
        {"_id": 0},
    )


async def find_annotation_by_id(item_id: str) -> dict | None:
    return await _db.question_annotations.find_one({"item_id": item_id}, {"_id": 0})


async def list_annotations(filters: dict | None = None, limit: int = 500) -> list[dict]:
    q = filters or {}
    cursor = _db.question_annotations.find(q, {"_id": 0}).sort("received_at", -1).limit(limit)
    return await cursor.to_list(limit)


def _build_item_hash_map(force: bool = False) -> dict[str, dict]:
    """Mapeia item_hash -> estrutura_cognitiva a partir da colecao Firestore `itens`.

    A chave de juncao e o hash deterministico do conteudo da questao
    (fs.compute_item_hash sobre `pipeline.questao`), que e EXATAMENTE o
    `item_hash` gravado em cada evento de behavior.
    """
    global _ITEM_HASH_TO_EC
    if _ITEM_HASH_TO_EC is not None and not force:
        return _ITEM_HASH_TO_EC
    mapping: dict[str, dict] = {}
    client = fs.get_firestore()
    for snap in client.collection("itens").stream():
        doc = snap.to_dict() or {}
        pipeline = doc.get("pipeline") or {}
        questao = pipeline.get("questao")
        ec = pipeline.get("estrutura_cognitiva") or {}
        if questao is None or not ec:
            continue
        try:
            h = fs.compute_item_hash(questao)
        except Exception:  # noqa: BLE001
            continue
        mapping[h] = ec
    _ITEM_HASH_TO_EC = mapping
    return mapping


def _read_firestore_answered(user_id: str) -> dict[str, Any]:
    """Le os eventos de resposta do aluno em students/{uid}/behavior e retorna
    os processos cognitivos acionados (via item_hash -> itens.estrutura_cognitiva).

    Sem IA/LLM. So consulta e agrega.
    """
    client = fs.get_firestore()
    hmap = _build_item_hash_map()

    answered_procs: set[str] = set()
    answered_comps: set[str] = set()
    answered_doms: set[str] = set()
    matched_hashes: set[str] = set()
    total_events = 0
    unmatched = 0

    events = client.collection("students").document(user_id).collection("behavior").stream()
    for e in events:
        ev = e.to_dict() or {}
        # considera apenas eventos de resposta efetiva
        if ev.get("status") not in (None, "respondida"):
            continue
        total_events += 1
        h = ev.get("item_hash")
        ec = hmap.get(h) if h else None
        if not ec:
            unmatched += 1
            continue
        matched_hashes.add(h)
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
        "answered_items": len(matched_hashes),
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
            "ontology_tree": build_ontology_tree(set()),
        }

    answered_processes = set(agg["processes"])
    return {
        "processes": [],
        "error_types": [],
        "misconceptions": [],
        "answered_processes": agg["processes"],
        "answered_competencias": agg["competencias"],
        "answered_dominios": agg["dominios"],
        "answered_items": agg["answered_items"],
        "total_events": agg["total_events"],
        "unmatched_events": agg["unmatched_events"],
        "ontology_tree": build_ontology_tree(answered_processes),
    }
