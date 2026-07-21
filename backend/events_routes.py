"""Response Event Store routes — append-only writes + observability reads."""
from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_admin, require_user
from events_models import (
    BulkResponsesIn,
    InterventionEventIn,
    ResponseEventIn,
    StudentInterventionEvent,
    StudentResponseEvent,
)
from models import User

router = APIRouter(prefix="", tags=["events"])

_db = None
def set_db(db):
    global _db
    _db = db


# ---------- Writes (append-only) ----------

@router.post("/events/responses")
async def record_response(event: ResponseEventIn, user: User = Depends(require_user)):
    """Append a single response event. Server never rewrites.
    Status transitions (correction, annulment) MUST be new events with the
    same attempt_id.
    """
    attempt_id = event.attempt_id or f"att_{uuid.uuid4().hex[:16]}"
    stored = StudentResponseEvent(
        attempt_id=attempt_id,
        aluno_id=event.aluno_id,
        turma=event.turma,
        item_id=event.item_id,
        item_schema_version=event.item_schema_version,
        item_hash=event.item_hash,
        contexto=event.contexto,
        data_hora_resposta=event.data_hora_resposta,
        alternativa_escolhida=event.alternativa_escolhida.upper(),
        acertou=event.acertou,
        tempo_resposta_seg=event.tempo_resposta_seg,
        status=event.status,
        metadata_tecnica=event.metadata_tecnica,
    )
    doc = stored.model_dump()
    await _db.response_events.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.post("/events/responses/bulk")
async def record_responses_bulk(request: BulkResponsesIn, user: User = Depends(require_user)):
    docs = []
    for e in request.events:
        stored = StudentResponseEvent(
            attempt_id=e.attempt_id or f"att_{uuid.uuid4().hex[:16]}",
            aluno_id=e.aluno_id, turma=e.turma,
            item_id=e.item_id, item_schema_version=e.item_schema_version, item_hash=e.item_hash,
            contexto=e.contexto,
            data_hora_resposta=e.data_hora_resposta,
            alternativa_escolhida=e.alternativa_escolhida.upper(),
            acertou=e.acertou, tempo_resposta_seg=e.tempo_resposta_seg,
            status=e.status, metadata_tecnica=e.metadata_tecnica,
        )
        docs.append(stored.model_dump())
    if docs:
        await _db.response_events.insert_many(docs)
    return {"inserted": len(docs)}


@router.post("/events/interventions")
async def record_intervention(event: InterventionEventIn, user: User = Depends(require_user)):
    stored = StudentInterventionEvent(
        aluno_id=event.aluno_id,
        cognitive_process_id=event.cognitive_process_id,
        tipo_intervencao=event.tipo_intervencao,
        data_hora_aplicacao=event.data_hora_aplicacao,
        aplicada_por=event.aplicada_por,
        linked_evento_id=event.linked_evento_id,
    )
    doc = stored.model_dump()
    await _db.intervention_events.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------- Reads (observability) ----------

def _build_query(
    aluno_id: str | None, turma: str | None, disciplina: str | None,
    origem: str | None, from_iso: str | None, to_iso: str | None,
) -> dict[str, Any]:
    q: dict[str, Any] = {}
    if aluno_id: q["aluno_id"] = aluno_id
    if turma: q["turma"] = turma
    if origem: q["contexto.origem"] = origem
    time_q: dict[str, Any] = {}
    if from_iso: time_q["$gte"] = from_iso
    if to_iso: time_q["$lte"] = to_iso
    if time_q: q["data_hora_resposta"] = time_q
    return q


async def _enrich_with_items(events: list[dict]) -> list[dict]:
    """JOIN each event with its ITEM annotation (verbatim, read-only). Never
    duplicates fields into events — the annotation is returned alongside."""
    item_ids = list({e["item_id"] for e in events})
    if not item_ids:
        return [{"event": e, "item": None} for e in events]
    annotations = await _db.question_annotations.find(
        {"item_id": {"$in": item_ids}}, {"_id": 0}
    ).to_list(len(item_ids))
    by_id = {a["item_id"]: a for a in annotations}
    return [{"event": e, "item": by_id.get(e["item_id"])} for e in events]


@router.get("/events/responses")
async def list_responses(
    aluno_id: str | None = None,
    turma: str | None = None,
    disciplina: str | None = None,   # filter applied post-join
    origem: str | None = None,
    from_iso: str | None = Query(None, alias="from"),
    to_iso: str | None = Query(None, alias="to"),
    limit: int = Query(200, ge=1, le=2000),
    admin: User = Depends(require_admin),
):
    q = _build_query(aluno_id, turma, disciplina, origem, from_iso, to_iso)
    events = await _db.response_events.find(q, {"_id": 0}).sort("data_hora_resposta", -1).limit(limit).to_list(limit)
    enriched = await _enrich_with_items(events)
    if disciplina:
        enriched = [r for r in enriched if (r["item"] or {}).get("disciplina") == disciplina]
    return {"items": enriched, "count": len(enriched)}


@router.get("/events/interventions")
async def list_interventions(
    aluno_id: str | None = None,
    limit: int = Query(200, ge=1, le=2000),
    admin: User = Depends(require_admin),
):
    q: dict[str, Any] = {}
    if aluno_id: q["aluno_id"] = aluno_id
    events = await _db.intervention_events.find(q, {"_id": 0}).sort("data_hora_aplicacao", -1).limit(limit).to_list(limit)
    return {"items": events, "count": len(events)}


@router.get("/students/{aluno_id}/history")
async def student_history(
    aluno_id: str,
    from_iso: str | None = Query(None, alias="from"),
    to_iso: str | None = Query(None, alias="to"),
    disciplina: str | None = None,
    origem: str | None = None,
    admin: User = Depends(require_admin),
):
    """Consolidated per-student timeline: responses + interventions,
    each joined with the immutable ITEM annotation for cognitive context.
    """
    q = _build_query(aluno_id, None, disciplina, origem, from_iso, to_iso)
    responses = await _db.response_events.find(q, {"_id": 0}).sort("data_hora_resposta", -1).limit(1000).to_list(1000)
    enriched = await _enrich_with_items(responses)
    if disciplina:
        enriched = [r for r in enriched if (r["item"] or {}).get("disciplina") == disciplina]
    interventions = await _db.intervention_events.find({"aluno_id": aluno_id}, {"_id": 0}).sort("data_hora_aplicacao", -1).limit(500).to_list(500)

    # Aggregates
    total = len(enriched)
    correct = sum(1 for r in enriched if r["event"].get("acertou"))
    by_status: dict[str, int] = {}
    for r in enriched:
        s = r["event"].get("status", "respondida")
        by_status[s] = by_status.get(s, 0) + 1
    by_disciplina: dict[str, int] = {}
    for r in enriched:
        d = (r["item"] or {}).get("disciplina") or "—"
        by_disciplina[d] = by_disciplina.get(d, 0) + 1
    avg_time = round(sum((r["event"].get("tempo_resposta_seg") or 0) for r in enriched) / total, 1) if total else 0

    return {
        "aluno_id": aluno_id,
        "responses": enriched,
        "interventions": interventions,
        "summary": {
            "total_responses": total,
            "correct": correct,
            "accuracy": round(100 * correct / total, 1) if total else 0.0,
            "by_status": by_status,
            "by_disciplina": by_disciplina,
            "avg_time_seg": avg_time,
            "interventions_count": len(interventions),
        },
    }


@router.get("/students")
async def list_students(admin: User = Depends(require_admin)):
    """Distinct student ids seen in the event store, with counts."""
    pipeline = [
        {"$group": {
            "_id": {"aluno_id": "$aluno_id", "turma": "$turma"},
            "count": {"$sum": 1},
            "last_at": {"$max": "$data_hora_resposta"},
        }},
        {"$sort": {"last_at": -1}},
        {"$limit": 500},
    ]
    rows = await _db.response_events.aggregate(pipeline).to_list(500)
    return [
        {"aluno_id": r["_id"]["aluno_id"], "turma": r["_id"].get("turma"),
         "count": r["count"], "last_at": r["last_at"]}
        for r in rows
    ]
