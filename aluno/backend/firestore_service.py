"""Firestore integration for Sapiens (backend-only).

Read:  pipeline/questao, pipeline/fonte, pipeline/config/behavior_schema
Write: students_behavior/students_id/{uid}/behavior_student

Nao usa Firebase Authentication. A autenticacao e a sessao em cookie do
proprio backend (auth.require_user), unica camada de auth desde a remocao da
Emergent em 2026-08-21.
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


BEHAVIOR_SCHEMA_VERSION = "1.1"


def write_behavior_event(
    uid: str,
    *,
    item_id: str,
    ontology_version: Optional[str] = None,
    alternativa_escolhida: Optional[str] = None,
    acertou: Optional[bool] = None,
    item_schema_version: Optional[str] = None,
    item_content: Any = None,
    item_hash: Optional[str] = None,
    contexto_tipo: Optional[str] = None,
    prova_id: Optional[str] = None,
    origem: str = "firestore",
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

    Contrato: `pipeline/docs/behavior/07 behavior student 1.4.md`, versão
    **1.1** (o "1.4" do nome do arquivo é resíduo de nomeação e nunca foi versão
    deste contrato — GOV-1.0 §6.1).

    `ontology_version` é **obrigatório** desde a 1.1: é a versão da ontologia
    contra a qual o ITEM estava anotado no momento da resposta, não a versão
    ativa hoje. Sem ela, o evento não pode ser reinterpretado depois de a
    ontologia mudar de versão MAIOR, porque não há como saber contra qual
    catálogo o item estava anotado quando o estudante respondeu.

    Nota sobre o bloco `desempenho` (estatuto declarado na 1.1): esses campos são
    o que o White Paper 1.0 chamava de Indicador Comportamental, nível removido
    na arquitetura vigente. Eles são **coletados e registrados**, e **não**
    alimentam atualização de crença sobre o estado cognitivo do estudante — o
    canal de evidência além de acerto/erro segue regido por GL-3, aberto.
    """
    event_id = event_id or uuid.uuid4().hex
    if item_hash is None and item_content is not None:
        item_hash = compute_item_hash(item_content)
    if not ontology_version:
        raise ValueError(
            "ontology_version é obrigatório no contrato de behavior 1.1 "
            "(GOV-1.0 §6.1). Ele vem do item respondido — a versão contra a qual "
            "o item estava anotado —, nunca da ontologia ativa no momento da escrita."
        )

    event = {
        "schema_version": BEHAVIOR_SCHEMA_VERSION,
        "ontology_version": ontology_version,
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
            "origem": origem,
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


def get_student_behavior_history(uid: str, limit: int = 1000) -> list[dict[str, Any]]:
    """Lê o histórico de eventos de behavior (schema canônico) de um aluno,
    do mais recente para o mais antigo."""
    docs = (
        _behavior_collection_ref(uid)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]


def list_students_with_behavior(limit: int = 500) -> list[dict[str, Any]]:
    """Agrega, via collection group query, todos os alunos com pelo menos um
    evento de behavior registrado (schema canônico), com contagem e último evento."""
    events = get_firestore().collection_group("behavior").limit(5000).stream()
    by_student: dict[str, dict[str, Any]] = {}
    for snap in events:
        ev = snap.to_dict() or {}
        sid = ev.get("student_id")
        if not sid:
            continue
        agg = by_student.setdefault(sid, {"student_id": sid, "count": 0, "last_at": None})
        agg["count"] += 1
        ts = ev.get("timestamp")
        if ts and (agg["last_at"] is None or ts > agg["last_at"]):
            agg["last_at"] = ts
    rows = sorted(by_student.values(), key=lambda r: r["last_at"] or "", reverse=True)
    return rows[:limit]
