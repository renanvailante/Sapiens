"""Testes offline (sem rede, sem Mongo real, sem chave de API) da 2ª rodada
da auditoria de custo (2026-08-22) — ver `auditoria/AUDITORIA-OTIMIZACAO-
CUSTO-GEMINI-2.md`:

1. `run_cognitive_pipeline_adaptive` — escalonamento LOW → MEDIUM quando
   `judge()` reprova a saída, nunca mais que 2 chamadas, e as duas rotas de
   desligamento (`thinking_level` explícito, `GEMINI_THINKING_STRATEGY=FIXED`).
2. `book_cache_key` em `run_cognitive_pipeline` — cache combinado (ontologia
   + PDF do caderno), reuso entre chamadas do mesmo caderno, e fallback para
   o cache só-de-ontologia quando a criação do cache de caderno falha.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import cognitive_engine  # noqa: E402
from ontology_seed import DEFAULT_ONTOLOGY  # noqa: E402


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


_FAKE_JSON = (
    '{"fonte": {}, "questao": {"enunciado": "x", "alternativas": []}, '
    '"estrutura_cognitiva": {"processos": []}, '
    '"incerteza": {"marcadores": [], "detalhe": null, "requer_arbitragem": false}, '
    '"distratores": [], "intervencoes": [], "pedagogia": {}, "qualidade": {}}'
)


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.usage_metadata = None


class _FakeModels:
    def __init__(self):
        self.calls: list[dict] = []

    async def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return _FakeResponse(_FAKE_JSON)


class _FakeCachedContent:
    def __init__(self, name: str):
        self.name = name
        # A API real sempre devolve `expire_time` quando `ttl` é passado —
        # sem isso, `gemini_cache.get_or_create_cached_content` nunca acha o
        # registro reutilizável na 2ª chamada (ver `_parse_iso`/margem de
        # segurança) e recriaria o cache toda vez.
        self.expire_time = datetime.now(timezone.utc) + timedelta(hours=1)


class _FakeCaches:
    """Dublê de `client.aio.caches` — cria sempre com sucesso, salvo quando
    `should_fail` está ligado (simula um modelo/projeto sem suporte a cache
    de um conteúdo específico, sem propagar exceção até a chamada real)."""

    def __init__(self, should_fail: bool = False):
        self.create_calls: list[dict] = []
        self.should_fail = should_fail
        self._counter = 0

    async def create(self, *, model, config):
        self.create_calls.append({"model": model, "config": config})
        if self.should_fail:
            raise RuntimeError("cache indisponível para este conteúdo (simulado)")
        self._counter += 1
        return _FakeCachedContent(name=f"cachedContents/fake-{self._counter}")


class _FakeAio:
    def __init__(self, caches_should_fail: bool = False):
        self.models = _FakeModels()
        self.caches = _FakeCaches(should_fail=caches_should_fail)


class _FakeClient:
    def __init__(self, caches_should_fail: bool = False):
        self.aio = _FakeAio(caches_should_fail=caches_should_fail)


class _FakeCacheCollection:
    """Dublê mínimo de `db.gemini_caches` — mesmo contrato do usado em
    `tests/test_gemini_retry_and_cache.py`."""

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


_FILES = [("questao.md", b"conteudo minimo de teste, sem PDF real")]


class TestRunCognitivePipelineAdaptive:
    def test_judge_aprova_de_primeira_uma_chamada_so_em_low(self, monkeypatch):
        monkeypatch.setenv("GEMINI_THINKING_STRATEGY", "ADAPTIVE")
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)

        raw, meta = _run(
            cognitive_engine.run_cognitive_pipeline_adaptive(
                DEFAULT_ONTOLOGY, _FILES,
                judge=lambda _raw: True,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=None,
            )
        )
        assert len(fake_client.aio.models.calls) == 1
        assert meta == {"attempts": ["LOW"], "escalated": False}
        assert fake_client.aio.models.calls[0]["config"].thinking_config.thinking_level.name == "LOW"

    def test_judge_reprova_escalona_uma_vez_para_medium_nunca_mais(self, monkeypatch):
        monkeypatch.setenv("GEMINI_THINKING_STRATEGY", "ADAPTIVE")
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)

        raw, meta = _run(
            cognitive_engine.run_cognitive_pipeline_adaptive(
                DEFAULT_ONTOLOGY, _FILES,
                judge=lambda _raw: False,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=None,
            )
        )
        assert len(fake_client.aio.models.calls) == 2
        assert meta == {"attempts": ["LOW", "MEDIUM"], "escalated": True}
        levels = [c["config"].thinking_config.thinking_level.name for c in fake_client.aio.models.calls]
        assert levels == ["LOW", "MEDIUM"]

    def test_judge_que_levanta_excecao_nao_escalona(self, monkeypatch):
        monkeypatch.setenv("GEMINI_THINKING_STRATEGY", "ADAPTIVE")
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)

        def _judge_quebrado(_raw):
            raise ValueError("boom")

        raw, meta = _run(
            cognitive_engine.run_cognitive_pipeline_adaptive(
                DEFAULT_ONTOLOGY, _FILES,
                judge=_judge_quebrado,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=None,
            )
        )
        assert len(fake_client.aio.models.calls) == 1
        assert meta == {"attempts": ["LOW"], "escalated": False}

    def test_thinking_level_explicito_desliga_adaptativo(self, monkeypatch):
        monkeypatch.setenv("GEMINI_THINKING_STRATEGY", "ADAPTIVE")
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)

        judge_chamado = []

        def _judge(_raw):
            judge_chamado.append(True)
            return False  # mesmo reprovando, não deve haver 2ª chamada

        raw, meta = _run(
            cognitive_engine.run_cognitive_pipeline_adaptive(
                DEFAULT_ONTOLOGY, _FILES,
                judge=_judge,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=None,
                thinking_level="HIGH",
            )
        )
        assert len(fake_client.aio.models.calls) == 1
        assert fake_client.aio.models.calls[0]["config"].thinking_config.thinking_level.name == "HIGH"
        assert judge_chamado == []  # thinking_level explícito nem chama judge
        assert meta == {"attempts": ["HIGH"], "escalated": False}

    def test_estrategia_fixed_desliga_globalmente(self, monkeypatch):
        monkeypatch.setenv("GEMINI_THINKING_STRATEGY", "FIXED")
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)

        raw, meta = _run(
            cognitive_engine.run_cognitive_pipeline_adaptive(
                DEFAULT_ONTOLOGY, _FILES,
                judge=lambda _raw: False,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=None,
            )
        )
        assert len(fake_client.aio.models.calls) == 1
        assert meta["escalated"] is False

    def test_niveis_low_e_escalado_configuraveis_por_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_THINKING_STRATEGY", "ADAPTIVE")
        monkeypatch.setenv("GEMINI_THINKING_LEVEL_LOW", "MINIMAL")
        monkeypatch.setenv("GEMINI_THINKING_LEVEL_ESCALATED", "HIGH")
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)

        raw, meta = _run(
            cognitive_engine.run_cognitive_pipeline_adaptive(
                DEFAULT_ONTOLOGY, _FILES,
                judge=lambda _raw: False,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=None,
            )
        )
        assert meta == {"attempts": ["MINIMAL", "HIGH"], "escalated": True}


class TestBookCacheKey:
    def test_sem_book_cache_key_comportamento_identico_ao_anterior(self, monkeypatch):
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)
        collection = _FakeCacheCollection()

        _run(
            cognitive_engine.run_cognitive_pipeline(
                DEFAULT_ONTOLOGY, _FILES,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=collection,
            )
        )
        # 1 cache criado (só ontologia) — nenhum cache de caderno.
        assert len(fake_client.aio.caches.create_calls) == 1
        call_contents = fake_client.aio.models.calls[0]["contents"]
        # Sem book_cache_key, os arquivos continuam indo inline na chamada.
        assert len(call_contents) == len(_FILES) + 1  # arquivo(s) + texto do usuário

    def test_book_cache_key_cria_cache_combinado_e_nao_reenvia_arquivo(self, monkeypatch):
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)
        collection = _FakeCacheCollection()

        _run(
            cognitive_engine.run_cognitive_pipeline(
                DEFAULT_ONTOLOGY, _FILES,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=collection,
                book_cache_key="book-123",
            )
        )
        assert len(fake_client.aio.caches.create_calls) == 1
        cache_contents = fake_client.aio.caches.create_calls[0]["config"].contents
        # A ontologia (1 Part de texto) + os arquivos do caderno vão para o cache.
        assert len(cache_contents) == 1 + len(_FILES)

        call_contents = fake_client.aio.models.calls[0]["contents"]
        # O PDF já está no cache — a chamada real só carrega o texto do usuário.
        assert len(call_contents) == 1

    def test_segunda_questao_do_mesmo_caderno_reusa_cache_sem_recriar(self, monkeypatch):
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)
        collection = _FakeCacheCollection()

        for _ in range(2):
            _run(
                cognitive_engine.run_cognitive_pipeline(
                    DEFAULT_ONTOLOGY, _FILES,
                    schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                    cache_collection=collection,
                    book_cache_key="book-123",
                )
            )
        assert len(fake_client.aio.caches.create_calls) == 1
        assert len(fake_client.aio.models.calls) == 2
        for call in fake_client.aio.models.calls:
            assert len(call["contents"]) == 1  # nenhuma das 2 chamadas reenvia o arquivo

    def test_cadernos_diferentes_nunca_compartilham_cache(self, monkeypatch):
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)
        collection = _FakeCacheCollection()

        for book_id in ("book-A", "book-B"):
            _run(
                cognitive_engine.run_cognitive_pipeline(
                    DEFAULT_ONTOLOGY, _FILES,
                    schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                    cache_collection=collection,
                    book_cache_key=book_id,
                )
            )
        assert len(fake_client.aio.caches.create_calls) == 2

    def test_falha_ao_criar_cache_de_caderno_cai_para_cache_de_ontologia(self, monkeypatch):
        fake_client = _FakeClient(caches_should_fail=True)
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)
        collection = _FakeCacheCollection()

        _run(
            cognitive_engine.run_cognitive_pipeline(
                DEFAULT_ONTOLOGY, _FILES,
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=collection,
                book_cache_key="book-123",
            )
        )
        # Tentou 2x criar cache (caderno, depois só-ontologia), as 2 falharam
        # no dublê — nunca deve bloquear a anotação por isso.
        assert len(fake_client.aio.caches.create_calls) == 2
        call_contents = fake_client.aio.models.calls[0]["contents"]
        # Sem NENHUM cache disponível, o arquivo volta a ir inline.
        assert len(call_contents) == len(_FILES) + 1
