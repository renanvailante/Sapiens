"""Instrumentação de custo por chamada Gemini — nunca bloqueia a anotação.

Motivação: a auditoria de 2026-08-22 (`auditoria/AUDITORIA-ECONOMICA-E-CORPUS-
2026-08-22.md`) encontrou que nenhuma chamada ao Gemini jamais persistia
`usage_metadata` (tokens de entrada/saída/thinking/cache) em lugar nenhum —
o custo real de um lote só era descoberto na fatura, dias depois. Este módulo
grava, por chamada, exatamente os números necessários para reconstruir custo
sem nunca gravar conteúdo de prompt, PDF ou segredo algum.

Isolado do motor de anotação pelo mesmo motivo do `gemini_cache.py`: uma
falha aqui é best-effort, nunca propaga.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("sapiens.gemini_telemetry")

COLLECTION_NAME = "gemini_usage"

# Campos vindos de `resp.usage_metadata` — só contagens, nunca conteúdo.
_USAGE_FIELDS = (
    "prompt_token_count",
    "cached_content_token_count",
    "candidates_token_count",
    "thoughts_token_count",
    "total_token_count",
)


def usage_from_response(
    resp: Any,
    *,
    model: str,
    cached: bool,
    thinking_level: str | None,
    duration_ms: float,
) -> dict[str, Any]:
    """Extrai só números de `resp.usage_metadata`. Nunca lê `resp.text`."""
    um = getattr(resp, "usage_metadata", None)
    doc: dict[str, Any] = {
        "model": model,
        "cached": cached,
        "thinking_level": thinking_level,
        "duration_ms": round(duration_ms, 1),
        "success": True,
        "error_type": None,
        "http_status": None,
    }
    for field in _USAGE_FIELDS:
        doc[field] = getattr(um, field, None) if um is not None else None
    return doc


def usage_from_error(
    exc: Exception,
    *,
    model: str,
    cached: bool,
    thinking_level: str | None,
    duration_ms: float,
) -> dict[str, Any]:
    """Registro de tentativa que falhou — sem tokens (a API não devolveu resposta)."""
    doc: dict[str, Any] = {
        "model": model,
        "cached": cached,
        "thinking_level": thinking_level,
        "duration_ms": round(duration_ms, 1),
        "success": False,
        "error_type": type(exc).__name__,
        "http_status": getattr(exc, "code", None),
    }
    for field in _USAGE_FIELDS:
        doc[field] = None
    return doc


async def persist(
    collection: Any,
    usage: dict[str, Any],
    *,
    context: str,
    book_id: str | None = None,
    question_number: str | None = None,
    item_id: str | None = None,
) -> None:
    """Grava um registro de uso. Falha aqui é logada e engolida — telemetria
    de custo não pode derrubar uma anotação que já foi paga ao modelo."""
    if collection is None:
        return
    doc = {
        **usage,
        "context": context,
        "book_id": book_id,
        "question_number": question_number,
        "item_id": item_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await collection.insert_one(doc)
    except Exception:  # noqa: BLE001 — telemetria nunca pode quebrar a anotação
        logger.exception("gemini_telemetry: falha ao persistir uso (ignorada)")
