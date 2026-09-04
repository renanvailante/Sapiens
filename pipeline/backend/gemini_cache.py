"""Cache explícito de conteúdo fixo (prompt de sistema + ontologia) no Gemini.

Motivação: numa anotação típica, ~92% dos tokens de entrada são a mesma
ontologia + o mesmo prompt de sistema, reenviados a cada questão. A API do
Gemini permite subir esse bloco fixo uma vez (`client.caches.create`) e
referenciá-lo por nome nas chamadas seguintes — que passam a enviar só o
conteúdo específico da questão.

Confirmado em `ai.google.dev/gemini-api/docs/pricing` (2026-08-22): para
`gemini-3-flash-preview`, caching é gratuito no Free tier (`Not available` é
o texto usado para o que de fato falta — caching não está nessa lista).

Isolado do motor de anotação por design: qualquer falha aqui devolve `None`
em vez de propagar — cache é uma otimização de custo/latência, nunca uma
dependência para a anotação funcionar.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger("sapiens.gemini_cache")

COLLECTION_NAME = "gemini_caches"
DEFAULT_TTL_SECONDS = 3600

# Piso conservador acima do mínimo documentado pelo Gemini para caching
# explícito (2048–4096 tokens, conforme a família do modelo, ~4 chars/token
# em português). Abaixo disso a criação do cache é rejeitada ou não compensa.
MIN_CACHEABLE_CHARS = 10_000

# Reusa um cache existente só se ele ainda tiver esta folga antes de expirar,
# para não arriscar iniciar uma chamada logo antes do TTL vencer.
_EXPIRY_SAFETY_MARGIN = timedelta(seconds=90)


def cache_key(*parts: str) -> str:
    """Chave estável para (model, ontology_version, schema_version, ...).

    Muda automaticamente quando a ontologia ou o schema mudam de versão —
    o cache velho simplesmente para de ser reaproveitado, nunca é lido com
    conteúdo desatualizado.
    """
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:40]


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def get_or_create_cached_content(
    client: genai.Client,
    collection: Any,
    *,
    model: str,
    key: str,
    system_instruction: str,
    contents: list,
    display_name: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> str | None:
    """Nome (`cachedContents/...`) de um cache válido, ou `None` se inviável.

    `None` é uma resposta legítima e esperada — não uma falha — quando o
    conteúdo fixo é curto demais, quando a criação é recusada pela API
    (modelo sem suporte, projeto sem acesso) ou por qualquer outro erro.
    """
    total_chars = len(system_instruction) + sum(
        len(getattr(part, "text", None) or "") for part in contents
    )
    if total_chars < MIN_CACHEABLE_CHARS:
        return None

    now = datetime.now(timezone.utc)
    existing = await collection.find_one({"_id": key})
    if existing:
        expire_time = _parse_iso(existing.get("expire_time"))
        if expire_time and expire_time - _EXPIRY_SAFETY_MARGIN > now:
            return existing["name"]

    try:
        cache = await client.aio.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                display_name=display_name,
                system_instruction=system_instruction,
                contents=contents,
                ttl=f"{ttl_seconds}s",
            ),
        )
    except Exception as exc:  # noqa: BLE001 — cache nunca pode bloquear a anotação
        logger.warning("Gemini cache: criação falhou para key=%s: %s", key, exc)
        return None

    expire_time = getattr(cache, "expire_time", None)
    await collection.update_one(
        {"_id": key},
        {
            "$set": {
                "name": cache.name,
                "model": model,
                "expire_time": expire_time.isoformat() if expire_time else None,
                "created_at": now.isoformat(),
            }
        },
        upsert=True,
    )
    logger.info("Gemini cache: criado key=%s name=%s ttl=%ds chars=%d", key, cache.name, ttl_seconds, total_chars)
    return cache.name


async def invalidate(collection: Any, key: str) -> None:
    """Remove o registro local. Chamado quando a API diz que o cache sumiu
    (expirou do lado do servidor antes do TTL local, ou foi apagado por fora)."""
    await collection.delete_one({"_id": key})
