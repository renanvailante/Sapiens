"""`escalonamento_redacao.resolver_itens` — Gemini mockado (nunca chama rede
de verdade). Verifica: só os itens pendentes entram no prompt; cache evita
2ª chamada; item que falha o judge() escala sozinho para MEDIUM; item que
passa em LOW nunca é reconsultado; nenhum item tem mais de 2 tentativas.

Sem `pytest-asyncio` no projeto — mesmo padrão de `test_sparks_payments.py`:
`asyncio.run()` dentro de um teste síncrono comum.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import ai_service  # noqa: E402
from redacao import escalonamento_redacao as esc  # noqa: E402
from redacao.tipos import RedacaoEntrada  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


ENTRADA = RedacaoEntrada(texto="um texto de teste qualquer", tema_frase="tema de teste")


def test_so_os_itens_pendentes_entram_no_prompt(monkeypatch, fake_db):
    prompts = []

    async def fake_generate_json(system, prompt, model=None, thinking_level=None):
        prompts.append(prompt)
        return {"itens": [
            {"criterio_id": "ZERO-05", "disparado": False, "trecho_citado": "t",
             "evidencias_encontradas": [], "evidencias_ausentes": []},
        ]}

    monkeypatch.setattr(ai_service, "generate_json", fake_generate_json)
    _run(esc.resolver_itens(
        ENTRADA, ["ZERO-05"], db=fake_db, canon_versao="1.0.0",
        motivo_por_item={"ZERO-05": "ambíguo"}, redacao_id="r1",
    ))
    assert "ZERO-05" in prompts[0]
    assert "COMP-I" not in prompts[0]


def test_cache_evita_segunda_chamada_para_o_mesmo_item(monkeypatch, fake_db):
    chamadas = {"n": 0}

    async def fake_generate_json(system, prompt, model=None, thinking_level=None):
        chamadas["n"] += 1
        return {"itens": [
            {"criterio_id": "ZERO-05", "disparado": False, "trecho_citado": "t",
             "evidencias_encontradas": [], "evidencias_ausentes": []},
        ]}

    monkeypatch.setattr(ai_service, "generate_json", fake_generate_json)
    for _ in range(2):
        _run(esc.resolver_itens(
            ENTRADA, ["ZERO-05"], db=fake_db, canon_versao="1.0.0",
            motivo_por_item={"ZERO-05": "ambíguo"}, redacao_id="r1",
        ))
    assert chamadas["n"] == 1


def test_item_invalido_em_low_escala_para_medium_sozinho(monkeypatch, fake_db):
    niveis_vistos = []

    async def fake_generate_json(system, prompt, model=None, thinking_level=None):
        niveis_vistos.append(thinking_level)
        if thinking_level == "LOW":
            # ZERO-05 malformado (sem "disparado"), ZERO-06 ok — só ZERO-05 deve reescalar.
            return {"itens": [
                {"criterio_id": "ZERO-05", "trecho_citado": "t"},
                {"criterio_id": "ZERO-06", "disparado": False, "trecho_citado": "t",
                 "evidencias_encontradas": [], "evidencias_ausentes": []},
            ]}
        assert "ZERO-05" in prompt and "ZERO-06" not in prompt
        return {"itens": [
            {"criterio_id": "ZERO-05", "disparado": False, "trecho_citado": "t",
             "evidencias_encontradas": [], "evidencias_ausentes": []},
        ]}

    monkeypatch.setattr(ai_service, "generate_json", fake_generate_json)
    evidencias = _run(esc.resolver_itens(
        ENTRADA, ["ZERO-05", "ZERO-06"], db=fake_db, canon_versao="1.0.0",
        motivo_por_item={"ZERO-05": "x", "ZERO-06": "y"}, redacao_id="r1",
    ))
    assert niveis_vistos == ["LOW", "MEDIUM"]  # nunca uma 3ª tentativa
    assert evidencias["ZERO-05"].candidatos == [(False, 1.5)]
    assert evidencias["ZERO-06"].candidatos == [(False, 1.5)]


def test_copia_02_nunca_e_escalonavel():
    assert "COPIA-02" in esc.NAO_ESCALONAVEL
