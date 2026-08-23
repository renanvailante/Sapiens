"""Núcleo compartilhado: roda o motor cognitivo e persiste o resultado.

Extraído para que a rota síncrona (`/api/pipeline/generate`) e o worker da
fila de lote (`batch_queue.py`) produzam exatamente o mesmo registro — mesmo
Schema 2.2, mesma normalização, mesmo espelho Firestore — sem duas
implementações que podem divergir.

A rota HTTP original em `server.py` não foi tocada: ela continua com sua
própria cópia desta lógica, para não arriscar uma regressão num caminho já em
produção. Este módulo é o caminho usado pela fila de lote, que é novo.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import gemini_telemetry
from cognitive_engine import run_cognitive_pipeline_adaptive
from firestore_sync import create_question_sync
from item_contract import index_fields, normalize_item, validate as validate_item
from ontology_validator import OntologyRegistry
from storage import build_path, put_object

logger = logging.getLogger("sapiens.annotation_pipeline")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def persist_annotation(record: dict, item: dict, ontology: dict, registry: OntologyRegistry) -> None:
    record["item"] = item
    record["schema_version"] = item.get("schema_version")
    record["ontology_version"] = item.get("ontology_version") or ontology.get("version")
    record["validacao"] = validate_item(item, registry)
    record.update(index_fields(item))


async def persist_artifacts(
    question_id: str, files: list[tuple[str, bytes, str]], extraction: dict, pipeline_json: dict
) -> dict:
    original_paths: list[dict] = []
    for filename, data, content_type in files:
        p = build_path("original", question_id, filename)
        put_object(p, data, content_type)
        original_paths.append(
            {"filename": filename, "path": p, "content_type": content_type, "size": len(data)}
        )
    extraction_path = build_path("extraction", question_id, "extraction.json")
    put_object(
        extraction_path, json.dumps(extraction, ensure_ascii=False, indent=2).encode(), "application/json"
    )
    pipeline_path = build_path("pipeline", question_id, "pipeline.json")
    put_object(
        pipeline_path, json.dumps(pipeline_json, ensure_ascii=False, indent=2).encode(), "application/json"
    )
    return {"originals": original_paths, "extraction": extraction_path, "pipeline": pipeline_path}


async def generate_and_persist(
    db: Any,
    *,
    ontology: dict[str, Any],
    schema: dict[str, Any],
    files: list[tuple[str, bytes, str]],
    fonte_conhecida: dict | None = None,
    focus_hint: str | None = None,
    cache_collection: Any = None,
) -> dict:
    """Roda o motor cognitivo + normaliza + persiste um item (Schema 2.2).

    Propaga qualquer exceção do motor (incluindo `GeminiQuotaExhaustedError`)
    sem tratar — quem chama decide o que fazer: a rota HTTP devolveria 502, a
    fila de lote agenda retry ou marca dead-letter.

    Ordem deliberada: primeiro grava o registro cognitivo em `pipelines`
    (resultado já pago ao modelo), só depois tenta os artefatos binários —
    uma falha de storage nunca deve custar a classificação que já saiu do
    Gemini.
    """
    question_id = str(uuid.uuid4())
    registry = OntologyRegistry.from_dict(ontology)

    async def _usage_sink(u: dict) -> None:
        await gemini_telemetry.persist(
            db.gemini_usage, u, context="batch_queue",
            question_number=(fonte_conhecida or {}).get("numero"), item_id=question_id,
        )

    def _judge(raw_candidate: dict) -> bool:
        candidate_item = normalize_item(
            raw_candidate, ontology, arquivo_origem=files[0][0] if files else None,
            fonte_conhecida=fonte_conhecida, registry=registry,
        )
        return validate_item(candidate_item, registry)["valid"]

    raw, _thinking_meta = await run_cognitive_pipeline_adaptive(
        ontology,
        [(n, d) for n, d, _ in files],
        focus_hint=focus_hint,
        schema=schema,
        cache_collection=cache_collection,
        on_usage=_usage_sink,
        judge=_judge,
    )

    if fonte_conhecida and isinstance(raw, dict):
        fonte = raw.setdefault("fonte", {})
        if isinstance(fonte, dict):
            fonte.update({k: v for k, v in fonte_conhecida.items() if v is not None})

    item = normalize_item(
        raw,
        ontology,
        arquivo_origem=files[0][0] if files else None,
        fonte_conhecida=fonte_conhecida,
        registry=registry,
    )

    extraction = {"questao": item.get("questao"), "arquivos": [n for n, _, _ in files]}
    record: dict[str, Any] = {
        "id": question_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "artifacts": {},
    }
    persist_annotation(record, item, ontology, registry)
    await db.pipelines.insert_one(record)

    try:
        artifacts = await persist_artifacts(question_id, files, extraction, item)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Artefatos não persistidos para %s: %s", question_id, exc)
        record["artifacts_error"] = str(exc)
        await db.pipelines.update_one({"id": question_id}, {"$set": {"artifacts_error": str(exc)}})
    else:
        record["artifacts"] = artifacts
        await db.pipelines.update_one(
            {"id": question_id}, {"$set": {"artifacts": artifacts, "updated_at": _now_iso()}}
        )

    create_question_sync(question_id, record)
    return record
