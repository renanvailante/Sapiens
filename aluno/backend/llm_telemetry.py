"""Auditoria de chamadas LLM — motivo, contexto, resultado. Nunca grava
conteúdo de prompt, redação ou qualquer dado do usuário; nunca bloqueia quem
chama (best-effort, mesmo contrato de `pipeline/backend/gemini_telemetry.py`).

Genérico por design: qualquer chamador (redação hoje, outras áreas do
Sapiens depois) grava aqui o motivo pelo qual uma chamada paga aconteceu —
é isso que a torna auditável, não apenas logada.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("sapiens.llm_telemetry")


async def persist(
    collection: Any,
    *,
    contexto: str,
    motivo: str,
    modelo: str,
    thinking_level: str | None,
    resultado_estado: str,
    duration_ms: float,
    canon_versao: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """`motivo` é obrigatório: por que esta chamada aconteceu — tipicamente
    qual sinal local ficou AMBIGUO/CONFLITANTE/INSUFICIENTE e precisou de
    confirmação. `contexto` identifica o item (ex.: "redacao_id=...
    criterio=COMP-II"), nunca o texto da redação em si."""
    doc = {
        "contexto": contexto,
        "motivo": motivo,
        "modelo": modelo,
        "thinking_level": thinking_level,
        "resultado_estado": resultado_estado,
        "duration_ms": round(duration_ms, 1),
        "canon_versao": canon_versao,
        "criado_em": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }
    try:
        await collection.insert_one(doc)
    except Exception:  # noqa: BLE001
        logger.exception("llm_telemetry.persist falhou — a chamada aconteceu mas não ficou registrada")
