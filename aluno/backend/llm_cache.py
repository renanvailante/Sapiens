"""Cache de resultado de LLM por hash de conteúdo — dedup, não o cache nativo
de prompt do Gemini (que exige um bloco de conteúdo fixo grande para
compensar, ver `pipeline/backend/gemini_cache.py`). Genérico: qualquer
chamador guarda um valor JSON-serializável sob uma chave estável, numa
coleção Mongo à sua escolha — sem saber nada de Gemini nem de nenhum domínio.

Isolado por design: uma falha aqui nunca derruba quem chama — cache é
otimização de custo, nunca uma dependência para o resultado existir.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("sapiens.llm_cache")


def cache_key(*parts: str) -> str:
    """Chave estável e determinística — muda sozinha quando qualquer parte
    muda (ex.: versão do canon, id do critério, texto normalizado, tema)."""
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()


async def get(collection: Any, key: str) -> Any | None:
    try:
        doc = await collection.find_one({"_id": key})
    except Exception:  # noqa: BLE001
        logger.exception("llm_cache.get falhou — tratando como cache miss")
        return None
    return doc["valor"] if doc else None


async def set(collection: Any, key: str, valor: Any) -> None:
    try:
        await collection.update_one(
            {"_id": key},
            {"$set": {"valor": valor, "atualizado_em": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("llm_cache.set falhou — resultado não fica em cache, a próxima chamada repete")
