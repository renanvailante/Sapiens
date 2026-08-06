"""Firestore integration for Sapiens (backend-only).

Read:  pipeline/questao, pipeline/fonte, pipeline/config/behavior_schema
Write: students_behavior/students_id/{uid}/behavior_student

Does NOT use Firebase Auth. Existing Emergent Auth remains the only auth layer.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger("sapiens.firestore")

_FS_CLIENT = None


def _load_credentials() -> credentials.Certificate:
    raw_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    if raw_json:
        return credentials.Certificate(json.loads(raw_json))
    if path:
        return credentials.Certificate(path)
    raise RuntimeError(
        "Firebase credentials not configured. Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON."
    )


def get_firestore():
    """Return a cached Firestore client (lazy init)."""
    global _FS_CLIENT
    if _FS_CLIENT is not None:
        return _FS_CLIENT
    try:
        app = firebase_admin.get_app()
    except ValueError:
        options = {}
        if pid := os.environ.get("FIREBASE_PROJECT_ID"):
            options["projectId"] = pid
        app = firebase_admin.initialize_app(_load_credentials(), options=options)
        logger.info("Firebase Admin initialized for project=%s", app.project_id)
    _FS_CLIENT = firestore.client(app)
    return _FS_CLIENT


# ---------- Read helpers ----------

def read_collection(path: str, limit: int = 100) -> list[dict[str, Any]]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    docs = get_firestore().collection(path).limit(limit).stream()
    return [{"id": snap.id, **(snap.to_dict() or {})} for snap in docs]


def read_document(collection_path: str, document_id: str) -> Optional[dict[str, Any]]:
    snap = get_firestore().collection(collection_path).document(document_id).get()
    if not snap.exists:
        return None
    return {"id": snap.id, **(snap.to_dict() or {})}


# ---------- Student behavior (nested path) ----------

def _behavior_ref(uid: str):
    return (
        get_firestore()
        .collection("students_behavior")
        .document("students_id")
        .collection(uid)
        .document("behavior_student")
    )


def write_student_behavior(uid: str, data: dict[str, Any]) -> dict[str, Any]:
    ref = _behavior_ref(uid)
    ref.set(data, merge=True)
    return {"path": ref.path, **data}


def read_student_behavior(uid: str) -> Optional[dict[str, Any]]:
    snap = _behavior_ref(uid).get()
    if not snap.exists:
        return None
    return {"id": snap.id, **(snap.to_dict() or {})}


# ---------- Seed / provisioning ----------

def _initial_behavior_doc(uid: str, email: Optional[str] = None, name: Optional[str] = None) -> dict[str, Any]:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    return {
        "user_id": uid,
        "email": email,
        "name": name,
        "profile": {
            "reading_speed": None,
            "confidence_level": None,
            "attention_span": None,
            "error_pattern": None,
        },
        "stats": {
            "total_answered": 0,
            "total_correct": 0,
            "total_incorrect": 0,
            "avg_time_seconds": 0,
        },
        "flags": {
            "onboarded": False,
            "first_exam_done": False,
        },
        "events": [],
        "created_at": now,
        "updated_at": now,
    }


def ensure_student_behavior(uid: str, email: Optional[str] = None, name: Optional[str] = None) -> bool:
    """Create the behavior_student doc if it does not yet exist. Returns True if created."""
    ref = _behavior_ref(uid)
    if ref.get().exists:
        return False
    ref.set(_initial_behavior_doc(uid, email, name))
    return True


async def seed_all_students(mongo_db) -> dict[str, int]:
    """Idempotently create behavior docs for every non-admin user in MongoDB."""
    created = 0
    skipped = 0
    async for u in mongo_db.users.find({}, {"_id": 0, "user_id": 1, "email": 1, "name": 1, "is_admin": 1}):
        if u.get("is_admin"):
            skipped += 1
            continue
        try:
            if await asyncio.to_thread(ensure_student_behavior, u["user_id"], u.get("email"), u.get("name")):
                created += 1
            else:
                skipped += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed_all_students failed for %s: %s", u.get("user_id"), exc)
    logger.info("Firestore student seed: created=%d skipped=%d", created, skipped)
    return {"created": created, "skipped": skipped}



# ======================================================================
# NEW student data structure (Fase 1)
#   students/{uid}                      -> documento "profile" do aluno
#   students/{uid}/behavior/{event_id}  -> um documento por evento de resposta
# NÃO usa Firebase Auth. O uid vem da autenticação já existente.
# ======================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _student_doc_ref(uid: str):
    return get_firestore().collection("students").document(uid)


def _behavior_collection_ref(uid: str):
    return _student_doc_ref(uid).collection("behavior")


def ensure_student_profile(uid: str, name: Optional[str] = None, email: Optional[str] = None) -> bool:
    """Cria o documento de profile do aluno em students/{uid} se ainda não existir.
    Deve ser chamado no login (via provisionamento já existente). Retorna True se criou.
    """
    ref = _student_doc_ref(uid)
    if ref.get().exists:
        return False
    ref.set({
        "nome": name,
        "email": email,
        "created_at": _now_iso(),
    })
    return True


def compute_item_hash(item_content: Any) -> str:
    """Hash determinístico do conteúdo da questão no momento da resposta."""
    canonical = json.dumps(item_content, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_behavior_event(
    uid: str,
    *,
    item_id: str,
    alternativa_escolhida: Optional[str] = None,
    acertou: Optional[bool] = None,
    item_schema_version: Optional[str] = None,
    item_content: Any = None,
    item_hash: Optional[str] = None,
    contexto_tipo: Optional[str] = None,
    prova_id: Optional[str] = None,
    tempo_resposta_segundos: float = 0,
    numero_tentativas: int = 1,
    mudou_resposta: bool = False,
    status: str = "respondida",
    dispositivo: Optional[str] = None,
    versao_aplicacao: Optional[str] = None,
    attempt_id: Optional[str] = None,
    event_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Escreve UM evento de behavior em students/{uid}/behavior/{event_id}.

    Segue EXATAMENTE o schema 1.0 definido no produto. Esta função apenas
    escreve — NÃO é chamada em nenhum fluxo ainda (Fase 1).
    """
    event_id = event_id or uuid.uuid4().hex
    if item_hash is None and item_content is not None:
        item_hash = compute_item_hash(item_content)

    event = {
        "schema_version": "1.0",
        "event_id": event_id,
        "attempt_id": attempt_id or uuid.uuid4().hex,
        "student_id": uid,
        "item_id": item_id,
        "item_schema_version": item_schema_version,
        "item_hash": item_hash,
        "timestamp": timestamp or _now_iso(),
        "contexto": {
            "tipo": contexto_tipo,
            "prova_id": prova_id,
            "origem": "firestore",
        },
        "resposta": {
            "alternativa_escolhida": alternativa_escolhida,
            "acertou": acertou,
        },
        "desempenho": {
            "tempo_resposta_segundos": tempo_resposta_segundos,
            "numero_tentativas": numero_tentativas,
            "mudou_resposta": mudou_resposta,
        },
        "status": status,
        "metadados": {
            "dispositivo": dispositivo,
            "versao_aplicacao": versao_aplicacao,
        },
    }

    _behavior_collection_ref(uid).document(event_id).set(event)
    return event
