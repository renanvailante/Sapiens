"""Fila de processamento em lote com retry/backoff e dead-letter.

Existe porque uma chamada síncrona por questão (`/api/pipeline/generate`)
não sobrevive a um 429 de cota diária no meio de um lote de ~200: o processo
tentaria a próxima questão imediatamente e receberia o mesmo 429, na volta.

Modelo: cada questão enfileirada é um documento em `pipeline_queue`
(status `pending` → `processing` → `succeeded` | `dead_letter`, ou de volta a
`pending` com `next_attempt_at` no futuro). Os arquivos originais vão para o
mesmo object storage (`storage.py`) usado pelo resto do pipeline — o
documento Mongo guarda só os caminhos, nunca os bytes (limite de 16MB por
documento do Mongo, e os PDFs de prova passam disso fácil).

`drain()` processa os itens já no prazo (`next_attempt_at <= agora`), até
`limit`. Não é um scheduler: alguém (um cron, um loop externo, ou uma chamada
manual) precisa chamar `drain()` repetidamente. Essa escolha é deliberada —
nenhum laço em background é iniciado sozinho, então nada consome cota sem uma
ação explícita, o que é exatamente o que se quer enquanto a cota diária real
não está confirmada disponível.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from annotation_pipeline import generate_and_persist
from cognitive_engine import GeminiQuotaExhaustedError
from storage import build_path, build_prefix, delete_prefix, get_object, put_object

logger = logging.getLogger("sapiens.batch_queue")

COLLECTION_NAME = "pipeline_queue"

DEFAULT_MAX_ATTEMPTS = 5
# Backoff exponencial por tentativa (segundos): 30s, 2min, 8min, 32min, 2h8min.
_BACKOFF_BASE_SECONDS = 30
_BACKOFF_FACTOR = 4
_BACKOFF_CAP_SECONDS = 3 * 3600


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _backoff_seconds(attempts: int) -> int:
    return min(_BACKOFF_BASE_SECONDS * (_BACKOFF_FACTOR ** max(attempts - 1, 0)), _BACKOFF_CAP_SECONDS)


async def enqueue(
    db: Any,
    *,
    files: list[tuple[str, bytes, str]],
    fonte_conhecida: dict | None = None,
    focus_hint: str | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> str:
    """Enfileira uma questão. Devolve o `id` do item na fila.

    `files` é a mesma forma usada em `/api/pipeline/generate`: uma lista de
    (filename, bytes, content_type) — os arquivos originais da questão
    (PDF/imagem). Ficam salvos no storage sob `queue/{item_id}/...` até o
    item ser processado com sucesso (então passam a viver, deduplicados por
    conteúdo, no artefato final via `annotation_pipeline.persist_artifacts`,
    e o staging da fila é removido — ver `drain`).
    """
    item_id = str(uuid.uuid4())
    stored: list[dict] = []
    for filename, data, content_type in files:
        path = build_path("queue", item_id, filename)
        put_object(path, data, content_type)
        stored.append({"filename": filename, "path": path, "content_type": content_type})

    now = _now()
    doc = {
        "id": item_id,
        "status": "pending",
        "files": stored,
        "fonte": fonte_conhecida,
        "focus_hint": focus_hint,
        "attempts": 0,
        "max_attempts": max_attempts,
        "last_error": None,
        "result_pipeline_id": None,
        "created_at": _iso(now),
        "updated_at": _iso(now),
        "next_attempt_at": _iso(now),
    }
    await db.pipeline_queue.insert_one(doc)
    return item_id


def _load_files(doc: dict) -> list[tuple[str, bytes, str]]:
    result: list[tuple[str, bytes, str]] = []
    for f in doc["files"]:
        data, _ = get_object(f["path"])
        result.append((f["filename"], data, f["content_type"]))
    return result


async def _claim_next(db: Any, now_iso: str) -> dict | None:
    """Reivindica atomicamente o próximo item devido, para que dois `drain()`
    concorrentes nunca processem o mesmo item duas vezes."""
    return await db.pipeline_queue.find_one_and_update(
        {"status": "pending", "next_attempt_at": {"$lte": now_iso}},
        {"$set": {"status": "processing", "updated_at": now_iso}},
        sort=[("created_at", 1)],
    )


async def drain(
    db: Any,
    *,
    ontology: dict[str, Any],
    schema: dict[str, Any],
    limit: int = 20,
    cache_collection: Any = None,
) -> dict[str, Any]:
    """Processa até `limit` itens devidos. Uma chamada = um lote de tentativas.

    Para imediatamente (sem consumir os itens restantes) ao primeiro 429 de
    cota DIÁRIA: continuar bateria no mesmo muro para cada item seguinte, e
    cada tentativa reiterada pelo SDK antes de chegar aqui já custou minutos
    de backoff. O item que revelou a cota esgotada volta para `pending` sem
    gastar uma tentativa — não foi ele que falhou, foi a cota.
    """
    summary = {
        "processed": 0, "succeeded": 0, "requeued": 0, "dead_letter": 0,
        "quota_exhausted": False, "quota_id": None, "retry_delay_seconds": None,
    }
    for _ in range(limit):
        now = _now()
        doc = await _claim_next(db, _iso(now))
        if not doc:
            break
        summary["processed"] += 1
        try:
            record = await generate_and_persist(
                db,
                ontology=ontology,
                schema=schema,
                files=_load_files(doc),
                fonte_conhecida=doc.get("fonte"),
                focus_hint=doc.get("focus_hint"),
                cache_collection=cache_collection,
            )
        except GeminiQuotaExhaustedError as exc:
            await db.pipeline_queue.update_one(
                {"id": doc["id"]},
                {"$set": {
                    "status": "pending",
                    "last_error": str(exc),
                    "updated_at": _iso(_now()),
                    # Não força uma nova tentativa antes de 1h — a cota diária
                    # não se recompõe em minutos; se o SDK devolveu um
                    # retry_delay explícito, é só uma sugestão do server, não
                    # necessariamente quando a cota diária de fato libera.
                    "next_attempt_at": _iso(_now() + timedelta(seconds=max(exc.retry_delay_seconds or 3600, 3600))),
                }},
            )
            summary["quota_exhausted"] = True
            summary["quota_id"] = exc.quota_id
            summary["retry_delay_seconds"] = exc.retry_delay_seconds
            logger.warning(
                "batch_queue: cota diária esgotada (quotaId=%s) — parando o dreno em %d itens processados",
                exc.quota_id, summary["processed"],
            )
            break
        except Exception as exc:  # noqa: BLE001 — captura ampla e deliberada: qualquer falha vira retry/dead-letter, nunca derruba o worker
            attempts = doc.get("attempts", 0) + 1
            max_attempts = doc.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
            if attempts >= max_attempts:
                await db.pipeline_queue.update_one(
                    {"id": doc["id"]},
                    {"$set": {
                        "status": "dead_letter", "attempts": attempts,
                        "last_error": str(exc), "updated_at": _iso(_now()),
                    }},
                )
                summary["dead_letter"] += 1
                logger.error("batch_queue: item %s em dead_letter após %d tentativas: %s", doc["id"], attempts, exc)
            else:
                wait = _backoff_seconds(attempts)
                await db.pipeline_queue.update_one(
                    {"id": doc["id"]},
                    {"$set": {
                        "status": "pending", "attempts": attempts,
                        "last_error": str(exc), "updated_at": _iso(_now()),
                        "next_attempt_at": _iso(_now() + timedelta(seconds=wait)),
                    }},
                )
                summary["requeued"] += 1
                logger.warning(
                    "batch_queue: item %s falhou (tentativa %d/%d), retry em %ds: %s",
                    doc["id"], attempts, max_attempts, wait, exc,
                )
        else:
            await db.pipeline_queue.update_one(
                {"id": doc["id"]},
                {"$set": {
                    "status": "succeeded", "result_pipeline_id": record["id"],
                    "updated_at": _iso(_now()),
                }},
            )
            summary["succeeded"] += 1
            # O conteúdo já foi persistido (deduplicado) no artefato final;
            # o staging da fila não serve mais a nenhum propósito — sem isso
            # ele fica órfão para sempre, já que só `dead_letter` é revisitado
            # manualmente (via `requeue`, que não reenvia arquivo nenhum).
            try:
                delete_prefix(build_prefix("queue", doc["id"]))
            except Exception as exc:  # noqa: BLE001 — best-effort, não desfaz o sucesso já registrado
                logger.warning("batch_queue: falha ao limpar staging de %s: %s", doc["id"], exc)
    return summary


async def status(db: Any) -> dict[str, Any]:
    counts: dict[str, int] = {}
    async for row in db.pipeline_queue.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        counts[row["_id"]] = row["n"]
    recent_errors = await db.pipeline_queue.find(
        {"status": "dead_letter"}, {"_id": 0, "id": 1, "last_error": 1, "attempts": 1, "updated_at": 1}
    ).sort("updated_at", -1).limit(10).to_list(10)
    return {"counts": counts, "recent_dead_letter": recent_errors}


async def requeue(db: Any, item_id: str) -> bool:
    """Zera tentativas e devolve um item (tipicamente `dead_letter`) para `pending`."""
    result = await db.pipeline_queue.update_one(
        {"id": item_id},
        {"$set": {
            "status": "pending", "attempts": 0, "last_error": None,
            "next_attempt_at": _iso(_now()), "updated_at": _iso(_now()),
        }},
    )
    return result.matched_count > 0
