"""`generate_json_resiliente` diante de HTTP 429 da Gemini API.

**Por que este arquivo existe.** A quota do free tier da Gemini é contada
**por modelo** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, 20
requisições/dia — medido em produção em 2026-09-21). Um 429 no modelo primário
é, portanto, exatamente o caso em que trocar de modelo resolve. O fallback só
disparava em `GeminiIndisponivelError` e `ServerError` (5xx); `ClientError`
(4xx, onde mora o 429) passava reto e a chamada morria ali. Foi o que derrubou
a geração de mensagem do Pesquisador de Aquisição, com 500 mudo na tela.

O que estes testes travam:

1. 429 no primário → tenta o modelo reserva (era o bug).
2. 429 nos DOIS → `GeminiQuotaExcedidaError`, com o tempo de retry que a
   própria API informou, para a mensagem ao usuário poder dizer QUANDO tentar.
3. 400/403/404 continuam subindo direto, sem retry — repetir em outro modelo
   não conserta prompt inválido, só gasta uma segunda chamada.
4. `GeminiQuotaExcedidaError` é subclasse de `GeminiIndisponivelError`, para
   que todo chamador que já tratava indisponibilidade siga funcionando.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import ai_service  # noqa: E402
from google.genai import errors as genai_errors  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _erro_429(retry_delay: str | None = "43s"):
    detalhes = [{
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                        "quotaValue": "20"}],
    }]
    if retry_delay:
        detalhes.append({"@type": "type.googleapis.com/google.rpc.RetryInfo",
                         "retryDelay": retry_delay})
    corpo = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                       "message": "You exceeded your current quota", "details": detalhes}}
    return genai_errors.ClientError(429, corpo)


def _erro_400():
    return genai_errors.ClientError(
        400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "bad request"}})


class TestQuota:
    def test_429_no_primario_cai_no_modelo_reserva(self, monkeypatch):
        """O bug de origem: `ClientError` não estava na lista de fallback."""
        chamados = []

        async def fake(system, user, *, model, **kwargs):
            chamados.append(model)
            if model == "primario":
                raise _erro_429()
            return {"ok": True}

        monkeypatch.setattr(ai_service, "_generate_json", fake)
        resposta = _run(ai_service.generate_json_resiliente(
            "s", "u", modelo="primario", modelo_fallback="reserva", timeout=30.0))

        assert resposta == {"ok": True}
        assert chamados == ["primario", "reserva"], "a reserva tem que ser tentada"

    def test_429_nos_dois_modelos_vira_erro_de_quota_com_tempo_de_retry(self, monkeypatch):
        async def fake(system, user, *, model, **kwargs):
            raise _erro_429("43s")

        monkeypatch.setattr(ai_service, "_generate_json", fake)
        with pytest.raises(ai_service.GeminiQuotaExcedidaError) as erro:
            _run(ai_service.generate_json_resiliente(
                "s", "u", modelo="primario", modelo_fallback="reserva", timeout=30.0))

        assert erro.value.modelos == ("primario", "reserva")
        assert erro.value.segundos_para_retry == 43.0

    def test_429_sem_reserva_configurada_ja_vira_erro_de_quota(self, monkeypatch):
        async def fake(system, user, *, model, **kwargs):
            raise _erro_429()

        monkeypatch.setattr(ai_service, "_generate_json", fake)
        with pytest.raises(ai_service.GeminiQuotaExcedidaError):
            _run(ai_service.generate_json_resiliente(
                "s", "u", modelo="unico", modelo_fallback="", timeout=30.0))

    def test_erro_de_quota_continua_sendo_indisponibilidade_para_quem_ja_tratava(self):
        assert issubclass(ai_service.GeminiQuotaExcedidaError, ai_service.GeminiIndisponivelError)

    def test_400_nao_vira_retry_nem_erro_de_quota(self, monkeypatch):
        """Prompt inválido não melhora em outro modelo — repetir só gasta uma
        segunda chamada por um erro que a repetição não conserta."""
        chamados = []

        async def fake(system, user, *, model, **kwargs):
            chamados.append(model)
            raise _erro_400()

        monkeypatch.setattr(ai_service, "_generate_json", fake)
        with pytest.raises(genai_errors.ClientError):
            _run(ai_service.generate_json_resiliente(
                "s", "u", modelo="primario", modelo_fallback="reserva", timeout=30.0))
        assert chamados == ["primario"], "400 não pode disparar segunda chamada"

    def test_retry_info_ausente_nao_quebra(self, monkeypatch):
        async def fake(system, user, *, model, **kwargs):
            raise _erro_429(retry_delay=None)

        monkeypatch.setattr(ai_service, "_generate_json", fake)
        with pytest.raises(ai_service.GeminiQuotaExcedidaError) as erro:
            _run(ai_service.generate_json_resiliente(
                "s", "u", modelo="p", modelo_fallback="r", timeout=30.0))
        assert erro.value.segundos_para_retry is None

    def test_503_continua_caindo_na_reserva_como_antes(self, monkeypatch):
        chamados = []

        async def fake(system, user, *, model, **kwargs):
            chamados.append(model)
            if model == "primario":
                raise ai_service.GeminiIndisponivelError("503")
            return {"ok": True}

        monkeypatch.setattr(ai_service, "_generate_json", fake)
        assert _run(ai_service.generate_json_resiliente(
            "s", "u", modelo="primario", modelo_fallback="reserva", timeout=30.0)) == {"ok": True}
        assert chamados == ["primario", "reserva"]
