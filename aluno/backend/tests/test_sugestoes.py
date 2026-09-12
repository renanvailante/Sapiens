"""Canal de reclamações e sugestões — chamadas diretas às funções da rota,
no mesmo estilo offline do resto do repo (sem servidor, sem Mongo real)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import sugestoes_routes as routes  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user(uid="user-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno")


def _admin() -> User:
    return User(user_id="admin-1", email="admin@exemplo.com", name="Admin", is_admin=True)


def _payload(**kwargs) -> routes.SugestaoRequest:
    base = dict(tipo="reclamacao", mensagem="A tela de treino trava quando eu volto do mapa.")
    base.update(kwargs)
    return routes.SugestaoRequest(**base)


def test_enviar_cria_mensagem_nova(fake_db):
    routes.set_db(fake_db)
    resposta = _run(routes.enviar_sugestao(_payload(), user=_user()))
    assert resposta["ok"] is True

    doc = fake_db.sugestoes.docs[0]
    assert doc["status"] == "nova"
    assert doc["tipo"] == "reclamacao"
    assert doc["student_id"] == "user-1"
    assert doc["resposta"] is None


def test_tipo_fora_do_catalogo_e_recusado(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.enviar_sugestao(_payload(tipo="xingamento"), user=_user()))
    assert exc.value.status_code == 422


def test_mensagem_curta_demais_nao_passa_do_schema():
    with pytest.raises(Exception):
        routes.SugestaoRequest(tipo="sugestao", mensagem="oi")


def test_aluno_so_ve_as_proprias_mensagens(fake_db):
    routes.set_db(fake_db)
    _run(routes.enviar_sugestao(_payload(), user=_user("user-1")))
    _run(routes.enviar_sugestao(_payload(tipo="elogio", mensagem="Gostei muito da Mentis!"), user=_user("user-2")))

    minhas = _run(routes.minhas_sugestoes(user=_user("user-1")))
    assert minhas["count"] == 1
    assert minhas["items"][0]["student_id"] == "user-1"


def test_admin_ve_todas_e_filtra_por_status(fake_db):
    routes.set_db(fake_db)
    _run(routes.enviar_sugestao(_payload(), user=_user("user-1")))
    _run(routes.enviar_sugestao(_payload(tipo="sugestao", mensagem="Queria um modo escuro no mapa."), user=_user("user-2")))

    todas = _run(routes.listar_sugestoes(admin=_admin()))
    assert todas["count"] == 2

    novas = _run(routes.listar_sugestoes(status="nova", admin=_admin()))
    assert novas["count"] == 2
    assert _run(routes.listar_sugestoes(status="respondida", admin=_admin()))["count"] == 0


def test_responder_leva_a_resposta_de_volta_para_o_aluno(fake_db):
    routes.set_db(fake_db)
    sid = _run(routes.enviar_sugestao(_payload(), user=_user()))["sugestao_id"]

    _run(routes.responder(sid, routes.RespostaRequest(resposta="Corrigido na versão de hoje, obrigado!"), admin=_admin()))

    minhas = _run(routes.minhas_sugestoes(user=_user()))
    item = minhas["items"][0]
    assert item["status"] == "respondida"
    assert item["resposta"] == "Corrigido na versão de hoje, obrigado!"
    assert item["respondida_por"] == "admin-1"


def test_marcar_lida_duas_vezes_devolve_conflito(fake_db):
    routes.set_db(fake_db)
    sid = _run(routes.enviar_sugestao(_payload(), user=_user()))["sugestao_id"]

    assert _run(routes.marcar_lida(sid, admin=_admin()))["ok"] is True
    with pytest.raises(HTTPException) as exc:
        _run(routes.marcar_lida(sid, admin=_admin()))
    assert exc.value.status_code == 409


def test_responder_mensagem_inexistente_e_404(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.responder("nao-existe", routes.RespostaRequest(resposta="oi"), admin=_admin()))
    assert exc.value.status_code == 404
