"""A fila de espera da mentoria — chamadas diretas às funções da rota (sem
servidor HTTP nem TestClient, mesmo estilo offline do resto do repo).

Era o teste de "aulas particulares". O que mudou em 2026-09-15 não é o nome:
uma LISTA DE ESPERA tem duas obrigações que um formulário de pedido não tinha,
e são elas que os testes novos protegem —

1. **um aluno ocupa um lugar só** (mandar de novo corrige o pedido, não cria
   um segundo e não empurra ninguém para trás);
2. **a posição é informação honesta** — quem saiu da fila não conta, senão o
   número que o aluno vê só cresceria.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import mentoria_routes as routes  # noqa: E402
from models import CreateMentoriaEsperaRequest, UpdateMentoriaStatusRequest, User  # noqa: E402


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
        descricao="Quero destravar funções e a redação para o ENEM.",
    )
    base.update(kwargs)
    return CreateMentoriaEsperaRequest(**base)


def test_entrar_na_fila(fake_db):
    routes.set_db(fake_db)
    resposta = _run(routes.entrar_na_fila(_payload(), user=_user()))
    assert resposta["user_id"] == "user-1"
    assert resposta["status"] == "pendente"
    assert resposta["areas"] == ["Matemática", "Redação"]
    assert resposta["ja_estava_na_fila"] is False
    assert resposta["posicao"] == 1


def test_a_posicao_segue_a_ordem_de_chegada(fake_db):
    routes.set_db(fake_db)
    primeiro = _run(routes.entrar_na_fila(_payload(), user=_user("a")))
    segundo = _run(routes.entrar_na_fila(_payload(), user=_user("b")))
    assert primeiro["posicao"] == 1
    assert segundo["posicao"] == 2


def test_mandar_de_novo_corrige_o_pedido_sem_ocupar_dois_lugares(fake_db):
    """O aluno que percebe que digitou o WhatsApp errado reenvia. Se isso
    criasse um segundo pedido, a lista do admin mostraria a mesma pessoa duas
    vezes e ela apareceria duas vezes na contagem da fila."""
    routes.set_db(fake_db)
    _run(routes.entrar_na_fila(_payload(), user=_user()))
    segunda = _run(routes.entrar_na_fila(_payload(whatsapp="11999998888"), user=_user()))

    assert segunda["ja_estava_na_fila"] is True
    assert segunda["whatsapp"] == "11999998888"
    assert _run(fake_db.aulas_particulares.count_documents({})) == 1


def test_reenviar_nao_faz_o_aluno_perder_o_lugar(fake_db):
    """Corrigir o próprio pedido não pode mandar a pessoa para o fim da fila."""
    routes.set_db(fake_db)
    _run(routes.entrar_na_fila(_payload(), user=_user("a")))
    _run(routes.entrar_na_fila(_payload(), user=_user("b")))
    corrigido = _run(routes.entrar_na_fila(_payload(descricao="outra coisa"), user=_user("a")))
    assert corrigido["posicao"] == 1


def test_quem_saiu_da_fila_nao_conta_na_posicao(fake_db):
    routes.set_db(fake_db)
    primeiro = _run(routes.entrar_na_fila(_payload(), user=_user("a")))
    _run(routes.entrar_na_fila(_payload(), user=_user("b")))
    _run(routes.atualizar_status(
        primeiro["request_id"], UpdateMentoriaStatusRequest(status="cancelada"), admin=_admin(),
    ))
    meu = _run(routes.meu_lugar_na_fila(user=_user("b")))
    assert meu["posicao"] == 1


def test_area_invalida_e_rejeitada(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.entrar_na_fila(_payload(areas=["Física"]), user=_user()))
    assert exc.value.status_code == 422


def test_sem_areas_e_rejeitado(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.entrar_na_fila(_payload(areas=[]), user=_user()))
    assert exc.value.status_code == 422


def test_quem_nao_entrou_nao_esta_na_fila(fake_db):
    routes.set_db(fake_db)
    assert _run(routes.meu_lugar_na_fila(user=_user()))["na_fila"] is False


def test_admin_ve_a_fila_inteira(fake_db):
    routes.set_db(fake_db)
    _run(routes.entrar_na_fila(_payload(), user=_user("user-1")))
    _run(routes.entrar_na_fila(_payload(), user=_user("user-2")))
    assert len(_run(routes.listar_a_fila(admin=_admin()))) == 2


def test_admin_altera_status(fake_db):
    routes.set_db(fake_db)
    criada = _run(routes.entrar_na_fila(_payload(), user=_user()))
    atualizada = _run(routes.atualizar_status(
        criada["request_id"], UpdateMentoriaStatusRequest(status="em_andamento"), admin=_admin(),
    ))
    assert atualizada["status"] == "em_andamento"
    assert atualizada["updated_at"] >= criada["updated_at"]


def test_status_invalido_e_rejeitado(fake_db):
    routes.set_db(fake_db)
    criada = _run(routes.entrar_na_fila(_payload(), user=_user()))
    with pytest.raises(HTTPException) as exc:
        _run(routes.atualizar_status(
            criada["request_id"], UpdateMentoriaStatusRequest(status="feito"), admin=_admin(),
        ))
    assert exc.value.status_code == 422


def test_atualizar_pedido_inexistente_e_404(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.atualizar_status(
            "aula_inexistente", UpdateMentoriaStatusRequest(status="concluida"), admin=_admin(),
        ))
    assert exc.value.status_code == 404
