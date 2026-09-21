"""Persistência de UTM/campanha no cadastro — a ponta que
`Cerebro/produto/landings-de-anuncio.md` documentava como faltante: os
parâmetros de origem chegavam até a URL do `/login` e paravam ali, porque o
backend nunca gravava nada no usuário.

Offline, com o dublê de Mongo do `conftest.py`, no mesmo padrão de
`test_influencers.py`.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import Response

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import auth  # noqa: E402
import firestore_service as fs  # noqa: E402
import promo_codes_routes as promo  # noqa: E402
import rate_limit  # noqa: E402
from models import SignupRequest  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _sem_limites_residuais():
    rate_limit.limpar()
    yield
    rate_limit.limpar()


@pytest.fixture
def db(fake_db, monkeypatch):
    auth.set_db(fake_db)
    promo.set_db(fake_db)
    monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: True)
    return fake_db


def _cadastrar(db, email: str, **origem) -> dict:
    _run(auth.signup(
        SignupRequest(
            email=email, name="Aluno Novo", password="senha-forte-1",
            whatsapp="(11) 91234-5678", **origem,
        ),
        Response(),
    ))
    return _run(db.users.find_one({"email": email}))


class TestOrigemNoCadastroPorEmail:
    def test_grava_os_utm_e_a_campanha_do_signup(self, db):
        conta = _cadastrar(
            db, "aluno@x.com",
            utm_source="meta", utm_medium="paid", utm_campaign="diagnostico",
            campanha_id="camp_abc123", fbclid="XYZ",
        )
        assert conta["utm_source"] == "meta"
        assert conta["utm_medium"] == "paid"
        assert conta["utm_campaign"] == "diagnostico"
        assert conta["campanha_id"] == "camp_abc123"
        assert conta["fbclid"] == "XYZ"

    def test_cadastro_organico_nao_grava_nada_de_origem(self, db):
        conta = _cadastrar(db, "aluno@x.com")
        assert conta["utm_source"] is None
        assert conta["campanha_id"] is None

    def test_um_parametro_so_nao_apaga_o_resto_do_documento(self, db):
        """`_registrar_origem` é um `$set` com só as chaves não-vazias — não
        pode zerar outros campos do usuário nem os UTM que não vieram."""
        conta = _cadastrar(db, "aluno@x.com", utm_source="meta")
        assert conta["utm_source"] == "meta"
        assert conta["name"] == "Aluno Novo"
        assert conta["whatsapp"] is not None


class TestOrigemNoCadastroPorGoogle:
    def _google(self, db, monkeypatch, email: str, origem: dict | None):
        claims = {"email": email, "email_verified": True, "name": "Aluno Google"}

        class _FakeFbAuth:
            @staticmethod
            def verify_id_token(_token):
                return claims

        import sys as _sys
        import types

        fake_module = types.SimpleNamespace(auth=_FakeFbAuth)
        monkeypatch.setitem(_sys.modules, "firebase_admin", fake_module)
        monkeypatch.setattr(fs, "get_firestore", lambda: None)

        # `google_sign_in` é a rota do FastAPI: chamada direta (sem o app
        # rodando) não passa pela injeção que resolveria os `Body(...)` não
        # informados, então todo parâmetro com default `Body(...)` precisa
        # vir explícito aqui — inclusive os que a rota trataria como ausentes.
        return _run(auth.google_sign_in(
            Response(), id_token="qualquer", promo_code=None, whatsapp=None,
            menor_de_idade=False, responsavel_nome=None, responsavel_whatsapp=None,
            origem=origem,
        ))

    def test_grava_origem_na_conta_criada_pelo_google(self, db, monkeypatch):
        self._google(db, monkeypatch, "aluno@x.com", {"utm_source": "meta", "campanha_id": "camp_abc"})
        conta = _run(db.users.find_one({"email": "aluno@x.com"}))
        assert conta["utm_source"] == "meta"
        assert conta["campanha_id"] == "camp_abc"

    def test_filtra_chaves_fora_da_lista_branca(self, db, monkeypatch):
        """Um `dict` solto no corpo da requisição não passa pelo Pydantic —
        `_origem_filtrada` é quem garante que só `PARAMS_DE_ORIGEM` entra."""
        self._google(db, monkeypatch, "aluno@x.com", {"utm_source": "meta", "senha_hash": "nao_deveria_entrar"})
        conta = _run(db.users.find_one({"email": "aluno@x.com"}))
        assert conta["utm_source"] == "meta"
        assert "senha_hash" not in conta

    def test_sem_origem_nao_grava_nada(self, db, monkeypatch):
        self._google(db, monkeypatch, "aluno@x.com", None)
        conta = _run(db.users.find_one({"email": "aluno@x.com"}))
        assert conta.get("utm_source") is None
