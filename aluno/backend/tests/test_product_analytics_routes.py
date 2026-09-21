"""Rotas de analytics de produto — chamada direta da função da rota, sem
servidor HTTP, com `fake_db` (ver `tests/conftest.py`)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import product_analytics_routes as par  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user(**over) -> User:
    base = dict(user_id="u1", email="a@a.com", name="Aluno")
    base.update(over)
    return User(**base)


@pytest.fixture
def routes_com_db(fake_db):
    par.set_db(fake_db)
    yield fake_db
    par.set_db(None)


class TestProximoPassoIniciado:
    def test_primeira_chamada_grava_e_devolve_novo_true(self, routes_com_db):
        resultado = _run(par.proximo_passo_iniciado(user=_user()))
        assert resultado == {"ok": True, "novo": True}
        marco = _run(routes_com_db.product_events.find_one({"_id": "u1:primeiro_proximo_passo"}))
        assert marco is not None

    def test_segunda_chamada_nao_duplica_nem_quebra(self, routes_com_db):
        _run(par.proximo_passo_iniciado(user=_user()))
        resultado = _run(par.proximo_passo_iniciado(user=_user()))
        assert resultado == {"ok": True, "novo": False}
        assert _run(routes_com_db.product_events.count_documents({"uid": "u1"})) == 1

    def test_falha_ao_gravar_nunca_devolve_erro_pro_aluno(self, routes_com_db, monkeypatch):
        async def explode(*a, **k):
            raise RuntimeError("Mongo fora do ar")

        monkeypatch.setattr(par.product_analytics, "registrar", explode)
        resultado = _run(par.proximo_passo_iniciado(user=_user()))
        assert resultado == {"ok": True, "novo": False}


class TestResumoAnalyticsProduto:
    def test_devolve_ativacao_e_cohort(self, routes_com_db):
        resultado = _run(par.resumo_analytics_produto(dias=30, semanas=4, admin=_user(is_admin=True)))
        assert "ativacao" in resultado
        assert "cohort" in resultado
        assert len(resultado["cohort"]) == 4
