"""Resumo de sessão (padrões de erro/domínios/processos/competências) e o
laço de auto-sync do Firestore. Offline — sem Gemini, sem Firestore real: o
índice de itens e o cliente Gemini são substituídos por dublês mínimos.

Garantia central testada aqui: nenhum ID de catálogo (PROC-/DOM-/COMP-/ERR-/
MEC-/HAB-/INT-) chega ao texto que vai para o prompt do Gemini — os IDs são
trocados por nomes ANTES, em `montar_contexto_sessao`, não só por instrução
de prompt (que o modelo poderia ignorar).
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import annotation_service as asvc  # noqa: E402
import ai_service  # noqa: E402
from google.genai import types  # noqa: E402

_ID_CATALOGO = re.compile(r"\b(PROC|DOM|COMP|ERR|MEC|HAB|INT)-[A-Z0-9-]+\b")

_ITEM_FAKE = {
    "item_id": "ITEM-FAKE-001",
    "estrutura_cognitiva": {
        "processos": [{"id": "PROC-QUANT-02"}],
        "dominios": [{"id": "DOM-QUANT"}],
        "competencias": [{"id": "COMP-01"}],
    },
    "distratores": [
        {"alternativa": "B", "explicacao": "Confunde proporcionalidade direta com inversa."},
    ],
}


class TestCatalogoNomes:
    def test_devolve_nomes_para_ids_conhecidos(self):
        catalogo = asvc._catalogo_nomes()
        assert catalogo.get("PROC-QUANT-02")
        assert not catalogo["PROC-QUANT-02"].startswith("PROC-")


class TestMontarContextoSessao:
    def test_resposta_certa_nao_tem_explicacao_de_erro(self, monkeypatch):
        monkeypatch.setattr(asvc, "_build_item_index", lambda: {"ITEM-FAKE-001": _ITEM_FAKE})
        ctx = asvc.montar_contexto_sessao([
            {"item_id": "ITEM-FAKE-001", "alternativa_escolhida": "A", "acertou": True},
        ])
        assert ctx[0]["acertou"] is True
        assert "porque_essa_escolha_e_um_engano_comum" not in ctx[0]

    def test_resposta_errada_traz_explicacao_do_distrator_certo(self, monkeypatch):
        monkeypatch.setattr(asvc, "_build_item_index", lambda: {"ITEM-FAKE-001": _ITEM_FAKE})
        ctx = asvc.montar_contexto_sessao([
            {"item_id": "ITEM-FAKE-001", "alternativa_escolhida": "B", "acertou": False},
        ])
        assert ctx[0]["porque_essa_escolha_e_um_engano_comum"] == "Confunde proporcionalidade direta com inversa."

    def test_nenhum_id_de_catalogo_sobrevive_na_saida(self, monkeypatch):
        monkeypatch.setattr(asvc, "_build_item_index", lambda: {"ITEM-FAKE-001": _ITEM_FAKE})
        ctx = asvc.montar_contexto_sessao([
            {"item_id": "ITEM-FAKE-001", "alternativa_escolhida": "B", "acertou": False},
        ])
        import json
        bruto = json.dumps(ctx, ensure_ascii=False)
        assert not _ID_CATALOGO.search(bruto), f"ID de catálogo vazou para o contexto: {bruto}"

    def test_item_nao_encontrado_no_indice_nao_quebra(self, monkeypatch):
        monkeypatch.setattr(asvc, "_build_item_index", lambda: {})
        ctx = asvc.montar_contexto_sessao([
            {"item_id": "ITEM-SUMIU", "alternativa_escolhida": "A", "acertou": False},
        ])
        assert ctx == [{"acertou": False, "processos": [], "dominios": [], "competencias": []}]


class _FakeResponse:
    def __init__(self, text):
        self.text = text
        self.usage_metadata = None


class _FakeModels:
    def __init__(self):
        self.calls = []

    async def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "config": config})
        return _FakeResponse('{"headline": "x", "body": "y"}')


class _FakeAio:
    def __init__(self):
        self.models = _FakeModels()


class _FakeClient:
    def __init__(self):
        self.aio = _FakeAio()


class TestDiagnoseSessaoThinkingLevel:
    @staticmethod
    def _run(coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    def test_thinking_level_low_chega_no_generate_content(self, monkeypatch):
        fake = _FakeClient()
        monkeypatch.setattr(ai_service, "_client", lambda: fake)
        self._run(ai_service.diagnose_sessao([{"acertou": True, "processos": [], "dominios": [], "competencias": []}] * 10))
        config = fake.aio.models.calls[0]["config"]
        assert config.thinking_config.thinking_level == types.ThinkingLevel.LOW

    def test_falha_do_gemini_degrada_para_fallback_sem_propagar(self, monkeypatch):
        class _Boom:
            aio = None

        def _quebra():
            raise RuntimeError("Gemini indisponível")

        monkeypatch.setattr(ai_service, "_client", _quebra)
        resultado = self._run(ai_service.diagnose_sessao([{"acertou": True}] * 10))
        assert resultado == ai_service._SESSAO_FALLBACK


class TestSessaoDiagnosticoPayload:
    def test_exige_pelo_menos_10_respostas(self):
        import firestore_routes as fr

        with pytest.raises(ValidationError):
            fr.SessaoDiagnosticoPayload(respostas=[
                {"item_id": "X", "alternativa_escolhida": "A"} for _ in range(9)
            ])

    def test_10_respostas_passam(self):
        import firestore_routes as fr

        payload = fr.SessaoDiagnosticoPayload(respostas=[
            {"item_id": "X", "alternativa_escolhida": "A"} for _ in range(10)
        ])
        assert len(payload.respostas) == 10


class TestAutoSyncReusaLogicaDaRota:
    def test_run_firestore_sync_e_a_mesma_funcao_que_a_rota_chama(self):
        import inspect

        import admin_routes as admin_module
        import server

        fonte_rota = inspect.getsource(admin_module.firestore_sync)
        assert "run_firestore_sync" in fonte_rota
        fonte_loop = inspect.getsource(server._auto_sync_loop)
        assert "run_firestore_sync" in fonte_loop
