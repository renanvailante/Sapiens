"""Observability reads over the CANONICAL behavior/response-event store.

Source of truth: pipeline/docs/behavior/07 behavior student 1.4.md, written
via firestore_service.write_behavior_event() at Firestore
`students/{uid}/behavior/{event_id}`.

This module no longer writes events nor maintains a parallel Mongo schema
(`response_events`/`intervention_events` were eliminated — they duplicated,
with incompatible field names, the same concept already defined canonically
in pipeline/docs). There is no canonical "intervention event" app contract in
pipeline/docs (Intervenção Pedagógica there is only an ontology catalog node),
so that surface was removed rather than reinvented.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin
from models import User
import firestore_service as fs

router = APIRouter(prefix="", tags=["events"])


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Firestore error: {exc}")


@router.get("/students")
async def list_students(admin: User = Depends(require_admin)):
    """Alunos com pelo menos um evento de behavior (schema canônico), via
    Firestore collection group query — não depende de nenhum Mongo local."""
    return _safe(fs.list_students_with_behavior)


@router.get("/students/{student_id}/history")
async def student_history(student_id: str, admin: User = Depends(require_admin)):
    """Linha do tempo de eventos de behavior de um aluno, no schema canônico
    exato (sem reshape de campos, sem join com contratos não-canônicos)."""
    events = _safe(fs.get_student_behavior_history, student_id)
    total = len(events)
    correct = sum(1 for e in events if (e.get("resposta") or {}).get("acertou"))
    by_status: dict[str, int] = {}
    tempos: list[float] = []
    for e in events:
        status = e.get("status", "respondida")
        by_status[status] = by_status.get(status, 0) + 1
        t = (e.get("desempenho") or {}).get("tempo_resposta_segundos")
        if isinstance(t, (int, float)):
            tempos.append(t)
    return {
        "student_id": student_id,
        "events": events,
        "summary": {
            "total": total,
            "correct": correct,
            "accuracy": round(100 * correct / total, 1) if total else 0.0,
            "by_status": by_status,
            "avg_tempo_resposta_segundos": round(sum(tempos) / len(tempos), 1) if tempos else 0.0,
        },
    }
