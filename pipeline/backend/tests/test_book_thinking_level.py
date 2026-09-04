"""`thinking_level` por processamento de caderno — sem chamar o Gemini real.

Cobre dois pontos, ambos offline (cliente Gemini substituído por um dublê
mínimo, sem rede, sem chave de API):

1. `BookProcessRequest` (o corpo de `POST /book/{id}/process`) só aceita
   LOW/MEDIUM/HIGH — as 3 opções do seletor da tela do caderno.
2. O valor escolhido chega intacto até `types.GenerateContentConfig.
   thinking_config` — a mesma cadeia usada em produção
   (`run_cognitive_pipeline` → `_generate_json` → `generate_content`) — sem
   alterar `GEMINI_THINKING_LEVEL` nem `DEFAULT_THINKING_LEVEL` (o padrão
   global, usado quando nenhum override é enviado, continua intacto).

Não usa Mongo nem Firestore: chama `cognitive_engine.run_cognitive_pipeline`
diretamente, sem `cache_collection` e sem passar pela persistência de
`server.book_process_question` — não há por que gravar nada em `pipelines`
nem sincronizar Firestore só para testar propagação de um parâmetro.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import cognitive_engine  # noqa: E402
from google.genai import types  # noqa: E402
from ontology_seed import DEFAULT_ONTOLOGY  # noqa: E402
from server import BookProcessRequest  # noqa: E402


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.usage_metadata = None


_FAKE_JSON = (
    '{"fonte": {}, "questao": {"enunciado": "x", "alternativas": []}, '
    '"estrutura_cognitiva": {"processos": []}, '
    '"incerteza": {"marcadores": [], "detalhe": null, "requer_arbitragem": false}, '
    '"distratores": [], "intervencoes": [], "pedagogia": {}, "qualidade": {}}'
)


class _FakeModels:
    def __init__(self):
        self.calls: list[dict] = []

    async def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "config": config})
        return _FakeResponse(_FAKE_JSON)


class _FakeAio:
    def __init__(self):
        self.models = _FakeModels()


class _FakeClient:
    """Dublê do `genai.Client` — nenhuma chamada sai da máquina."""

    def __init__(self):
        self.aio = _FakeAio()


class TestBookProcessRequestThinkingLevel:
    def test_aceita_as_3_opcoes_do_seletor(self):
        for level in ("LOW", "MEDIUM", "HIGH"):
            req = BookProcessRequest(question_number="1", thinking_level=level)
            assert req.thinking_level == level

    def test_ausente_fica_none_sem_forcar_nenhum_valor(self):
        req = BookProcessRequest(question_number="1")
        assert req.thinking_level is None

    def test_valor_fora_das_3_opcoes_e_rejeitado(self):
        with pytest.raises(ValidationError):
            BookProcessRequest(question_number="1", thinking_level="ULTRA")

    def test_minusculo_tambem_e_rejeitado_pydantic_e_case_sensitive(self):
        # O seletor do frontend só envia MAIÚSCULO — este teste documenta que
        # `Literal` é sensível a caixa, então um valor minúsculo não passa
        # pela validação do Pydantic antes mesmo de chegar a
        # `cognitive_engine` (que também normaliza para maiúsculo, mas seria
        # tarde demais se algo diferente do seletor mandasse "low").
        with pytest.raises(ValidationError):
            BookProcessRequest(question_number="1", thinking_level="low")


class TestThinkingLevelChegaNoSDK:
    """`run_cognitive_pipeline(..., thinking_level=X)` até
    `GenerateContentConfig.thinking_config` — mesma cadeia de produção."""

    @staticmethod
    def _run(coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    def _call_with(self, monkeypatch, thinking_level: str | None) -> _FakeClient:
        fake_client = _FakeClient()
        monkeypatch.setattr(cognitive_engine, "_get_client", lambda: fake_client)
        self._run(
            cognitive_engine.run_cognitive_pipeline(
                DEFAULT_ONTOLOGY,
                [("t.md", b"conteudo minimo de teste, sem PDF real")],
                schema=cognitive_engine.DEFAULT_PIPELINE_SCHEMA,
                cache_collection=None,  # sem cache: sem chamada extra a testar
                thinking_level=thinking_level,
            )
        )
        return fake_client

    @pytest.mark.parametrize(
        "escolhido,esperado",
        [("LOW", types.ThinkingLevel.LOW), ("MEDIUM", types.ThinkingLevel.MEDIUM), ("HIGH", types.ThinkingLevel.HIGH)],
    )
    def test_override_explicito_e_o_que_chega_no_generate_content(self, monkeypatch, escolhido, esperado):
        fake_client = self._call_with(monkeypatch, escolhido)
        assert len(fake_client.aio.models.calls) == 1
        config = fake_client.aio.models.calls[0]["config"]
        assert config.thinking_config is not None
        assert config.thinking_config.thinking_level == esperado

    def test_sem_override_usa_o_padrao_global_sem_precisar_de_env_var(self, monkeypatch):
        """Confirma que o padrão global (`DEFAULT_THINKING_LEVEL`, decidido
        na auditoria de custo) continua valendo para quem não manda
        `thinking_level` — ex.: `/pipeline/generate`, `/pipeline/{id}/regenerate`
        — e que testar o seletor do caderno não alterou esse comportamento."""
        fake_client = self._call_with(monkeypatch, None)
        config = fake_client.aio.models.calls[0]["config"]
        assert config.thinking_config.thinking_level == types.ThinkingLevel(
            cognitive_engine.DEFAULT_THINKING_LEVEL
        )

    def test_dois_niveis_diferentes_nao_interferem_entre_si(self, monkeypatch):
        """Simula 2 cadernos processados 'ao mesmo tempo' com níveis
        diferentes — como pode acontecer com `runInParallel(concurrency=3)`
        no frontend. Como `thinking_level` nunca toca `os.environ`, uma
        chamada em HIGH não pode vazar para uma chamada em LOW concorrente."""
        client_low = self._call_with(monkeypatch, "LOW")
        client_high = self._call_with(monkeypatch, "HIGH")
        assert client_low.aio.models.calls[0]["config"].thinking_config.thinking_level == types.ThinkingLevel.LOW
        assert client_high.aio.models.calls[0]["config"].thinking_config.thinking_level == types.ThinkingLevel.HIGH
