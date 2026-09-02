"""Rotas de `/aulas-particulares` — chamadas diretas às funções da rota (sem
servidor HTTP nem TestClient, mesmo estilo offline do resto do repo)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import aulas_particulares_routes as routes  # noqa: E402
from models import CreateAulaParticularRequest, UpdateAulaParticularStatusRequest, User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user(uid="user-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno")


def _admin() -> User:
    return User(user_id="admin-1", email="admin@exemplo.com", name="Admin", is_admin=True)


def _payload(**kwargs):
    base = dict(
        nome_completo="Maria Silva",
        whatsapp="11987654321",
        areas=["Matemática", "Redação"],
        descricao="Preciso de ajuda com funções e um texto dissertativo.",
    )
    base.update(kwargs)
    return CreateAulaParticularRequest(**base)


def test_criar_solicitacao(fake_db):
    routes.set_db(fake_db)
    resposta = _run(routes.create_request(_payload(), user=_user()))
    assert resposta["user_id"] == "user-1"
    assert resposta["status"] == "pendente"
    assert resposta["areas"] == ["Matemática", "Redação"]
    assert resposta["request_id"].startswith("aula_")


def test_area_invalida_e_rejeitada(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.create_request(_payload(areas=["Física"]), user=_user()))
    assert exc.value.status_code == 422


def test_sem_areas_e_rejeitado(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.create_request(_payload(areas=[]), user=_user()))
    assert exc.value.status_code == 422


def test_aluno_ve_apenas_as_proprias_solicitacoes(fake_db):
    routes.set_db(fake_db)
    _run(routes.create_request(_payload(), user=_user("user-1")))
    _run(routes.create_request(_payload(), user=_user("user-2")))

    minhas = _run(routes.list_my_requests(user=_user("user-1")))
    assert len(minhas) == 1
    assert minhas[0]["user_id"] == "user-1"


def test_admin_ve_todas_as_solicitacoes(fake_db):
    routes.set_db(fake_db)
    _run(routes.create_request(_payload(), user=_user("user-1")))
    _run(routes.create_request(_payload(), user=_user("user-2")))

    todas = _run(routes.list_all_requests(admin=_admin()))
    assert len(todas) == 2


def test_admin_altera_status(fake_db):
    routes.set_db(fake_db)
    criada = _run(routes.create_request(_payload(), user=_user()))
    atualizada = _run(routes.update_status(
        criada["request_id"], UpdateAulaParticularStatusRequest(status="em_andamento"), admin=_admin(),
    ))
    assert atualizada["status"] == "em_andamento"
    assert atualizada["updated_at"] >= criada["updated_at"]


def test_status_invalido_e_rejeitado(fake_db):
    routes.set_db(fake_db)
    criada = _run(routes.create_request(_payload(), user=_user()))
    with pytest.raises(HTTPException) as exc:
        _run(routes.update_status(
            criada["request_id"], UpdateAulaParticularStatusRequest(status="feito"), admin=_admin(),
        ))
    assert exc.value.status_code == 422


def test_atualizar_solicitacao_inexistente_e_404(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.update_status(
            "aula_inexistente", UpdateAulaParticularStatusRequest(status="concluida"), admin=_admin(),
        ))
    assert exc.value.status_code == 404
