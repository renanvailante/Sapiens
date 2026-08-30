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
from google.api_core import exceptions as gcloud_exceptions

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


SPARKS_INITIAL_BALANCE = 255  # saldo inicial de todo aluno novo (Sparks — economia de recompensa).


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
        "sparks_balance": SPARKS_INITIAL_BALANCE,
    })
    return True


def ensure_sparks_balance(uid: str) -> int:
    """Garante que students/{uid} tenha `sparks_balance`, inicializando com
    `SPARKS_INITIAL_BALANCE` se ausente — cobre perfis criados antes desta
    feature existir. Idempotente: não sobrescreve um saldo já existente.
    Retorna o saldo atual (após garantir que existe).
    """
    ref = _student_doc_ref(uid)
    snap = ref.get()
    data = snap.to_dict() or {}
    if "sparks_balance" in data:
        return data["sparks_balance"]
    ref.set({"sparks_balance": SPARKS_INITIAL_BALANCE}, merge=True)
    return SPARKS_INITIAL_BALANCE


def read_sparks_balance(uid: str) -> int:
    snap = _student_doc_ref(uid).get()
    return (snap.to_dict() or {}).get("sparks_balance", SPARKS_INITIAL_BALANCE)


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


def count_answers_for_item(uid: str, item_id: str) -> int:
    """Quantos eventos de resposta (`status="respondida"`) este aluno já tem
    para ESTE item — a base de `numero_tentativas` (1ª vez, 2ª vez, ...).

    Nunca confia no cliente para esse número: reiniciar uma prova (opção do
    aluno no card do caderno, `ExamSelect.jsx`) produz um NOVO evento a cada
    resposta — o histórico nunca é apagado nem sobrescrito —, então contar
    os eventos já gravados é a única forma de saber em qual tentativa o
    aluno está.
    """
    docs = (
        _behavior_collection_ref(uid)
        .where(filter=firestore.FieldFilter("item_id", "==", item_id))
        .where(filter=firestore.FieldFilter("status", "==", "respondida"))
        .stream()
    )
    return sum(1 for _ in docs)


# Bloco canônico ENEM (45 questões por prova/área). Compartilhado entre
# `server.py` (`/api/provas`, agrupamento público) e `firestore_routes.py`
# (`/students/me/provas-progresso`, mesmo agrupamento cruzado com o que o
# aluno já respondeu) — mora aqui pra nenhum dos dois importar o outro.
BLOCO_TAMANHO = 45


def bloco_enem(numero: Optional[int]) -> Optional[tuple[int, int]]:
    """`(inicio, fim)` do bloco canônico de 45 que contém `numero` — sempre
    `(1,45)`, `(46,90)`, `(91,135)`, `(136,180)`, ... nunca o min/max do que
    por acaso está persistido (uma questão faltando não deve encolher o
    bloco nem misturá-lo com o vizinho)."""
    if numero is None:
        return None
    try:
        n = int(numero)
    except (TypeError, ValueError):
        return None
    if n < 1:
        return None
    idx = (n - 1) // BLOCO_TAMANHO
    inicio = idx * BLOCO_TAMANHO + 1
    return (inicio, inicio + BLOCO_TAMANHO - 1)


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


def get_activity_dates(uid: str, limit: int = 3000) -> list[str]:
    """Datas (YYYY-MM-DD, UTC) em que o aluno respondeu ao menos uma questão,
    mais recente primeiro — derivado do `timestamp` de cada evento de behavior.
    Base para sequência de estudos (streak) e progresso semanal no painel;
    nunca inventa atividade que não tenha evento real por trás.
    """
    eventos = get_student_behavior_history(uid, limit)
    dates = {e["timestamp"][:10] for e in eventos if e.get("timestamp")}
    return sorted(dates, reverse=True)


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


# ======================================================================
# Sparks — recompensa por rodada (10 questões; a última rodada do bloco de
# 45 fecha com 5). Estrutura:
#   students/{uid}.sparks_balance              -> saldo corrente (int)
#   students/{uid}/sparks_rounds/{round_key}   -> UM doc por rodada concluída,
#                                                  auditável (prova/rodada/itens)
#                                                  e a própria prova de que a
#                                                  rodada já foi paga.
# ======================================================================

def _sparks_round_ref(uid: str, round_key: str):
    return _student_doc_ref(uid).collection("sparks_rounds").document(round_key)


def read_round(uid: str, round_key: str) -> Optional[dict[str, Any]]:
    snap = _sparks_round_ref(uid, round_key).get()
    return snap.to_dict() if snap.exists else None


def list_sparks_rounds(uid: str, limit: int = 200) -> list[dict[str, Any]]:
    """Histórico de resumos de rodada (10 questões, 5 na última do bloco) do
    aluno, mais recente primeiro — cada doc já tem `created_at`, `bloco`
    (banca/ano/prova) e `padroes_de_erro`, gravados por `grant_round_sparks`.
    """
    docs = (
        _student_doc_ref(uid)
        .collection("sparks_rounds")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]


def grant_round_sparks(
    uid: str,
    *,
    round_key: str,
    bloco: dict[str, Any],
    rodada: int,
    item_ids: list[str],
    acertos: int,
    erros: int,
    total: int,
    percentual_acerto: float,
    padroes_de_erro: list[dict[str, Any]],
) -> dict[str, Any]:
    """Credita +1 Spark por acerto da rodada, UMA única vez, de forma atômica.

    A garantia de "nunca duplicar" não vem de uma checagem prévia no cliente
    nem de uma transação — vem de `DocumentReference.create()`: o Firestore só
    deixa UMA chamada concorrente criar com sucesso um documento num caminho
    que ainda não existe; todas as outras recebem `AlreadyExists` e não
    escrevem nada. Isso cobre retomada, refresh e corrida de requisições
    repetidas com a mesma garantia (create é atômico no servidor).
    """
    ref = _sparks_round_ref(uid, round_key)
    round_doc = {
        "round_key": round_key,
        "student_id": uid,
        "bloco": bloco,
        "rodada": rodada,
        "item_ids": item_ids,
        "acertos": acertos,
        "erros": erros,
        "total": total,
        "percentual_acerto": percentual_acerto,
        "padroes_de_erro": padroes_de_erro,
        "sparks_ganhos": acertos,
        "created_at": _now_iso(),
    }
    try:
        ref.create(round_doc)
    except gcloud_exceptions.AlreadyExists:
        existente = ref.get().to_dict() or {}
        return {"ja_concedido": True, **existente}

    if acertos:
        _student_doc_ref(uid).update({"sparks_balance": firestore.Increment(acertos)})
    return {"ja_concedido": False, **round_doc}


def _purchase_ref(uid: str, payment_id: str):
    return _student_doc_ref(uid).collection("sparks_purchases").document(payment_id)


def grant_purchase_sparks(
    uid: str,
    *,
    payment_id: str,
    package_id: str,
    sparks_amount: int,
    price_cents: int,
    currency: str,
    source: str,
) -> dict[str, Any]:
    """Credita Sparks de uma compra (avulsa ou ciclo de recarga automática)
    aprovada no Mercado Pago, UMA única vez, de forma atômica.

    Mesma garantia de `grant_round_sparks`: `payment_id` (id do pagamento no
    Mercado Pago, globalmente único) vira a chave do documento, e só a
    primeira chamada de `DocumentReference.create()` para esse caminho tem
    sucesso — webhook entregue mais de uma vez, ou dois processos
    concorrentes tratando a mesma notificação, não creditam Sparks duas
    vezes. Chamar isto só depois de confirmar `status == "approved"` no
    próprio Mercado Pago (nunca a partir do corpo bruto do webhook).
    """
    ref = _purchase_ref(uid, payment_id)
    doc = {
        "payment_id": payment_id,
        "student_id": uid,
        "package_id": package_id,
        "sparks_amount": sparks_amount,
        "price_cents": price_cents,
        "currency": currency,
        "source": source,
        "created_at": _now_iso(),
    }
    try:
        ref.create(doc)
    except gcloud_exceptions.AlreadyExists:
        existente = ref.get().to_dict() or {}
        return {"ja_creditado": True, **existente}

    _student_doc_ref(uid).update({"sparks_balance": firestore.Increment(sparks_amount)})
    return {"ja_creditado": False, **doc}


class InsufficientSparksError(Exception):
    """Saldo de Sparks do aluno é menor que o custo da ação."""

    def __init__(self, balance: int, needed: int):
        self.balance = balance
        self.needed = needed
        super().__init__(f"saldo insuficiente: {balance} < {needed}")


def deduct_sparks(uid: str, amount: int) -> int:
    """Debita `amount` Sparks do saldo do aluno, atomicamente (transação
    Firestore) para evitar corrida entre requisições concorrentes. Lança
    `InsufficientSparksError` se o saldo não cobrir o custo. Retorna o novo
    saldo.
    """
    ref = _student_doc_ref(uid)
    transaction = get_firestore().transaction()

    @firestore.transactional
    def _run(transaction):
        snap = ref.get(transaction=transaction)
        balance = (snap.to_dict() or {}).get("sparks_balance", SPARKS_INITIAL_BALANCE)
        if balance < amount:
            raise InsufficientSparksError(balance, amount)
        new_balance = balance - amount
        transaction.update(ref, {"sparks_balance": new_balance})
        return new_balance

    return _run(transaction)


# ======================================================================
# Mapa de Habilidades — camada cosmética de gamificação (ver
# cosmetic_skills_map.py). Persistido separado de qualquer dado real da
# ontologia: students/{uid}.skills_map = {hexagon, updated_at}.
# ======================================================================

def read_skills_map(uid: str) -> Optional[dict[str, Any]]:
    snap = _student_doc_ref(uid).get()
    return (snap.to_dict() or {}).get("skills_map")


def write_skills_map(uid: str, hexagon: list[dict[str, Any]], feedback: dict[str, Any]) -> str:
    updated_at = _now_iso()
    _student_doc_ref(uid).set(
        {"skills_map": {"hexagon": hexagon, "feedback": feedback, "updated_at": updated_at}},
        merge=True,
    )
    return updated_at
