"""Rotas de `/redacao` — chamadas diretas às funções da rota (sem servidor
HTTP nem TestClient, mesmo estilo offline do resto do repo). Gemini é
mockado; Mongo é o dublê de `conftest.py`."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import ai_service  # noqa: E402
import redacao_routes as routes  # noqa: E402
from models import RedacaoSubmitRequest, User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user() -> User:
    return User(user_id="user-1", email="aluno@exemplo.com", name="Aluno")


async def _fake_generate_json(system, prompt, model=None, thinking_level=None):
    import re
    itens = []
    for item_id in re.findall(r"### Item (\S+)", prompt):
        if item_id.startswith("COMP-"):
            itens.append({"criterio_id": item_id, "nivel_pontos": 120, "trecho_citado": "t",
                          "evidencias_encontradas": [], "evidencias_ausentes": []})
        else:
            itens.append({"criterio_id": item_id, "disparado": False, "trecho_citado": "t",
                          "evidencias_encontradas": [], "evidencias_ausentes": []})
    return {"itens": itens}


def test_submeter_redacao_vazia_e_rejeitada(fake_db, monkeypatch):
    routes.set_db(fake_db)
    monkeypatch.setattr(ai_service, "generate_json", _fake_generate_json)
    with pytest.raises(HTTPException) as exc:
        _run(routes.submeter_redacao(RedacaoSubmitRequest(texto="   "), user=_user()))
    assert exc.value.status_code == 422


def test_submeter_e_depois_consultar_redacao(fake_db, monkeypatch):
    routes.set_db(fake_db)
    monkeypatch.setattr(ai_service, "generate_json", _fake_generate_json)
    payload = RedacaoSubmitRequest(
        texto="Um texto de teste com conteúdo suficiente para não disparar os gatilhos mecânicos mais óbvios.",
        tema_frase="tema de teste",
    )
    resposta = _run(routes.submeter_redacao(payload, user=_user()))
    assert resposta["avaliacao"]["estado_geral"] in ("AVALIAVEL", "ANULADA")

    redacao_id = resposta["redacao"]["redacao_id"]
    consulta = _run(routes.obter_avaliacao(redacao_id, user=_user()))
    assert consulta["redacao"]["redacao_id"] == redacao_id
    assert consulta["avaliacao"] is not None


def test_usuario_nao_ve_redacao_de_outro(fake_db, monkeypatch):
    routes.set_db(fake_db)
    monkeypatch.setattr(ai_service, "generate_json", _fake_generate_json)
    payload = RedacaoSubmitRequest(texto="texto qualquer com algum conteúdo mínimo aqui para o teste passar bem")
    resposta = _run(routes.submeter_redacao(payload, user=_user()))
    redacao_id = resposta["redacao"]["redacao_id"]

    outro_usuario = User(user_id="user-2", email="outro@exemplo.com", name="Outro")
    with pytest.raises(HTTPException) as exc:
        _run(routes.obter_avaliacao(redacao_id, user=outro_usuario))
    assert exc.value.status_code == 404


def test_historico_lista_so_do_proprio_usuario(fake_db, monkeypatch):
    routes.set_db(fake_db)
    monkeypatch.setattr(ai_service, "generate_json", _fake_generate_json)
    payload = RedacaoSubmitRequest(texto="texto de teste com conteúdo mínimo suficiente para o histórico")
    _run(routes.submeter_redacao(payload, user=_user()))
    _run(routes.submeter_redacao(payload, user=User(user_id="user-2", email="outro@exemplo.com", name="Outro")))

    historico = _run(routes.historico_redacoes(user=_user()))
    assert historico["count"] == 1
    assert historico["items"][0]["redacao"]["user_id"] == "user-1"
