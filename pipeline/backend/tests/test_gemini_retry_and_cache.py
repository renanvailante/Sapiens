"""Testes offline do retry/backoff e do cache explícito do motor Gemini.

Não dependem de rede, Mongo nem chave de API real: o cliente Gemini e a
collection Mongo são substituídos por dublês mínimos. O formato dos erros
429 (`google.rpc.QuotaFailure` / `RetryInfo`) é o documentado pela própria
API, não inventado aqui — ver `cognitive_engine._classify_client_error`.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from google.genai import errors as genai_errors  # noqa: E402

import gemini_cache  # noqa: E402
from cognitive_engine import GeminiQuotaExhaustedError, _classify_client_error  # noqa: E402


def _quota_error(quota_id: str, retry_delay: str | None = None, code: int = 429) -> genai_errors.ClientError:
    details = [{"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{"quotaId": quota_id}]}]
    if retry_delay:
        details.append({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay})
    return genai_errors.ClientError(
        code, {"error": {"code": code, "message": "quota", "status": "RESOURCE_EXHAUSTED", "details": details}}
    )


class TestClassifyClientError:
    def test_daily_quota_e_classificada_como_daily(self):
        exc = _quota_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier", retry_delay="34s")
        categoria, retry_delay, quota_id = _classify_client_error(exc)
        assert categoria == "daily"
        assert retry_delay == 34.0
        assert quota_id == "GenerateRequestsPerDayPerProjectPerModel-FreeTier"

    def test_quota_por_minuto_e_classificada_como_transient(self):
        exc = _quota_error("GenerateRequestsPerMinutePerProjectPerModel-FreeTier")
        categoria, _, quota_id = _classify_client_error(exc)
        assert categoria == "transient"
        assert quota_id == "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"

    def test_429_sem_quota_failure_e_transient(self):
        exc = genai_errors.ClientError(429, {"error": {"code": 429, "message": "rate limited", "status": "RESOURCE_EXHAUSTED"}})
        categoria, _, quota_id = _classify_client_error(exc)
        assert categoria == "transient"
        assert quota_id is None

    def test_erro_400_nao_e_daily_nem_transient(self):
        exc = genai_errors.ClientError(400, {"error": {"code": 400, "message": "bad request", "status": "INVALID_ARGUMENT"}})
        categoria, _, _ = _classify_client_error(exc)
        assert categoria == "other"

    def test_parsing_nao_quebra_com_details_inesperado(self):
        exc = genai_errors.ClientError(429, {"error": {"code": 429, "message": "x", "status": "RESOURCE_EXHAUSTED", "details": "nao-e-uma-lista"}})
        categoria, retry_delay, quota_id = _classify_client_error(exc)
        assert categoria == "transient"
        assert retry_delay is None
        assert quota_id is None


class TestGeminiQuotaExhaustedError:
    def test_carrega_quota_id_e_retry_delay(self):
        original = _quota_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier")
        err = GeminiQuotaExhaustedError("GenerateRequestsPerDayPerProjectPerModel-FreeTier", 120.0, original)
        assert err.quota_id == "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
        assert err.retry_delay_seconds == 120.0
        assert "PerDay" in str(err) or "GenerateRequestsPerDay" in str(err)


class _FakeCollection:
    """Dublê mínimo de uma collection Motor: só os métodos que o cache usa."""

    def __init__(self):
        self._docs: dict[str, dict] = {}

    async def find_one(self, query: dict):
        return self._docs.get(query["_id"])

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        key = query["_id"]
        doc = self._docs.setdefault(key, {"_id": key})
        doc.update(update["$set"])

    async def delete_one(self, query: dict):
        self._docs.pop(query["_id"], None)


class _FakeCachedContent:
    def __init__(self, name: str, expire_time=None):
        self.name = name
        self.expire_time = expire_time


class _FakeAsyncCaches:
    def __init__(self):
        self.create_calls: list[dict] = []
        self._counter = 0

    async def create(self, *, model, config):
        self._counter += 1
        self.create_calls.append({"model": model, "config": config})
        # A API real sempre devolve `expire_time` quando `ttl` é passado
        # (é `now + ttl`, calculado no servidor) — o dublê replica isso.
        expire_time = datetime.now(timezone.utc) + timedelta(hours=1)
        return _FakeCachedContent(name=f"cachedContents/fake-{self._counter}", expire_time=expire_time)


class _FakeAio:
    def __init__(self):
        self.caches = _FakeAsyncCaches()


class _FakeClient:
    def __init__(self):
        self.aio = _FakeAio()


class TestCacheKey:
    def test_mesmas_partes_geram_mesma_chave(self):
        assert gemini_cache.cache_key("a", "b", "c") == gemini_cache.cache_key("a", "b", "c")

    def test_versao_diferente_gera_chave_diferente(self):
        assert gemini_cache.cache_key("modelo", "1.4.1") != gemini_cache.cache_key("modelo", "1.4.2")


class TestGetOrCreateCachedContent:
    def test_conteudo_curto_nao_cria_cache(self):
        async def _run():
            client = _FakeClient()
            collection = _FakeCollection()
            name = await gemini_cache.get_or_create_cached_content(
                client, collection, model="gemini-3-flash-preview", key="k",
                system_instruction="curto", contents=[], display_name="d",
            )
            assert name is None
            assert client.aio.caches.create_calls == []

        asyncio.run(_run())

    def test_conteudo_longo_cria_e_reusa_cache(self):
        async def _run():
            client = _FakeClient()
            collection = _FakeCollection()
            texto_longo = "x" * gemini_cache.MIN_CACHEABLE_CHARS
            name1 = await gemini_cache.get_or_create_cached_content(
                client, collection, model="gemini-3-flash-preview", key="k",
                system_instruction=texto_longo, contents=[], display_name="d",
            )
            assert name1 == "cachedContents/fake-1"
            assert len(client.aio.caches.create_calls) == 1

            # Segunda chamada, mesma key: reusa sem criar de novo.
            name2 = await gemini_cache.get_or_create_cached_content(
                client, collection, model="gemini-3-flash-preview", key="k",
                system_instruction=texto_longo, contents=[], display_name="d",
            )
            assert name2 == name1
            assert len(client.aio.caches.create_calls) == 1

        asyncio.run(_run())

    def test_criacao_falha_devolve_none_sem_propagar(self):
        class _BoomCaches:
            async def create(self, **kwargs):
                raise RuntimeError("modelo sem suporte a cache")

        async def _run():
            client = _FakeClient()
            client.aio.caches = _BoomCaches()
            collection = _FakeCollection()
            texto_longo = "x" * gemini_cache.MIN_CACHEABLE_CHARS
            name = await gemini_cache.get_or_create_cached_content(
                client, collection, model="gemini-3-flash-preview", key="k",
                system_instruction=texto_longo, contents=[], display_name="d",
            )
            assert name is None

        asyncio.run(_run())

    def test_cache_expirado_e_recriado(self):
        async def _run():
            client = _FakeClient()
            collection = _FakeCollection()
            texto_longo = "x" * gemini_cache.MIN_CACHEABLE_CHARS
            past = datetime.now(timezone.utc) - timedelta(seconds=10)
            await collection.update_one(
                {"_id": "k"}, {"$set": {"name": "cachedContents/velho", "expire_time": past.isoformat()}}, upsert=True,
            )
            name = await gemini_cache.get_or_create_cached_content(
                client, collection, model="gemini-3-flash-preview", key="k",
                system_instruction=texto_longo, contents=[], display_name="d",
            )
            assert name == "cachedContents/fake-1"
            assert len(client.aio.caches.create_calls) == 1

        asyncio.run(_run())

    def test_invalidate_remove_o_registro_local(self):
        async def _run():
            client = _FakeClient()
            collection = _FakeCollection()
            texto_longo = "x" * gemini_cache.MIN_CACHEABLE_CHARS
            await gemini_cache.get_or_create_cached_content(
                client, collection, model="gemini-3-flash-preview", key="k",
                system_instruction=texto_longo, contents=[], display_name="d",
            )
            assert await collection.find_one({"_id": "k"}) is not None
            await gemini_cache.invalidate(collection, "k")
            assert await collection.find_one({"_id": "k"}) is None

        asyncio.run(_run())
