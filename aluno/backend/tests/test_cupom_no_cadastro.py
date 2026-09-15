"""O vínculo aluno ↔ cupom, e a contagem de uso por cupom.

Até 2026-09-15 a única memória de promoção era o contador `promo_codes.usos`:
ele diz QUANTAS contas usaram um código e nunca QUAIS. O admin não tinha como
responder "este aluno entrou com cupom?" nem "quem veio pelo BEMVINDO2026?" —
a informação simplesmente não era gravada em lugar nenhum.

Estes testes rodam offline, com o dublê de Mongo de `conftest.py`.
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
    # O cadastro provisiona o perfil no Firestore; aqui só interessa o valor
    # de Sparks que ele RECEBE, então o provisionamento vira um espião.
    monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: True)
    return fake_db


def _cadastrar(db, email: str, promo_code: str | None = None) -> dict:
    _run(auth.signup(
        SignupRequest(email=email, name="Aluno Teste", password="senha-forte-1", promo_code=promo_code),
        Response(),
    ))
    return _run(db.users.find_one({"email": email}))


class TestCupomFicaNaConta:
    def test_cupom_valido_e_gravado_na_conta(self, db):
        _run(db.promo_codes.insert_one(
            {"code": "BEMVINDO2026", "sparks_amount": 500, "active": True, "usos": 0}
        ))
        conta = _cadastrar(db, "a@x.com", "BEMVINDO2026")
        assert conta["promo_code"] == "BEMVINDO2026"
        assert conta["promo_sparks"] == 500

    def test_cupom_e_normalizado_antes_de_gravar(self, db):
        """O aluno digita em minúsculas; o catálogo guarda em maiúsculas. Sem
        normalizar na gravação, o agrupamento por cupom quebraria em dois."""
        _run(db.promo_codes.insert_one(
            {"code": "BEMVINDO2026", "sparks_amount": 500, "active": True, "usos": 0}
        ))
        conta = _cadastrar(db, "b@x.com", "  bemvindo2026 ")
        assert conta["promo_code"] == "BEMVINDO2026"

    def test_cupom_desativado_nao_gruda_na_conta(self, db):
        """Código desativado não vale bônus — e não pode constar como usado,
        senão a tela do admin atribuiria uma conta a uma promoção que não
        aconteceu."""
        _run(db.promo_codes.insert_one(
            {"code": "VELHO", "sparks_amount": 500, "active": False, "usos": 0}
        ))
        conta = _cadastrar(db, "c@x.com", "VELHO")
        assert conta["promo_code"] is None
        assert conta["promo_sparks"] is None

    def test_cadastro_sem_cupom_fica_sem_cupom(self, db):
        conta = _cadastrar(db, "d@x.com")
        assert conta["promo_code"] is None

    def test_o_contador_de_usos_continua_subindo(self, db):
        """O vínculo por conta é acréscimo, não substituição: `usos` é o
        histórico completo (inclusive de antes desta feature) e segue de pé."""
        _run(db.promo_codes.insert_one(
            {"code": "X", "sparks_amount": 10, "active": True, "usos": 7}
        ))
        _cadastrar(db, "e@x.com", "X")
        assert _run(db.promo_codes.find_one({"code": "X"}))["usos"] == 8


class TestUsoPorCodigo:
    def _admin(self):
        from models import User

        return User(user_id="admin", email="admin@x.com", name="Admin", is_admin=True)

    def test_agrupa_os_alunos_por_cupom(self, db):
        _run(db.promo_codes.insert_one(
            {"code": "A", "sparks_amount": 100, "active": True, "usos": 2, "created_at": "2026-09-01"}
        ))
        _run(db.promo_codes.insert_one(
            {"code": "B", "sparks_amount": 200, "active": True, "usos": 0, "created_at": "2026-09-02"}
        ))
        _cadastrar(db, "um@x.com", "A")
        _cadastrar(db, "dois@x.com", "A")

        resultado = _run(promo.uso_por_codigo(self._admin()))
        por_codigo = {l["code"]: l for l in resultado["items"]}
        assert por_codigo["A"]["alunos_count"] == 2
        assert sorted(a["email"] for a in por_codigo["A"]["alunos"]) == ["dois@x.com", "um@x.com"]
        assert por_codigo["B"]["alunos_count"] == 0
        assert resultado["total_alunos_com_cupom"] == 2

    def test_usos_antigos_sem_vinculo_aparecem_como_tais(self, db):
        """Cadastros anteriores a 2026-09-15 contam em `usos` e não têm conta
        vinculada. A diferença precisa ficar VISÍVEL — senão o admin lê os
        dois números divergentes como defeito da tela."""
        _run(db.promo_codes.insert_one(
            {"code": "A", "sparks_amount": 100, "active": True, "usos": 10, "created_at": "2026-09-01"}
        ))
        _cadastrar(db, "novo@x.com", "A")

        linha = _run(promo.uso_por_codigo(self._admin()))["items"][0]
        assert linha["usos"] == 11          # 10 antigos + este
        assert linha["alunos_count"] == 1   # só este tem vínculo
        assert linha["usos_sem_vinculo"] == 10

    def test_cupom_excluido_do_catalogo_nao_esconde_quem_usou(self, db):
        """Excluir o código do catálogo apaga a linha, não a história: as
        contas continuam carregando o cupom e precisam continuar visíveis."""
        _run(db.promo_codes.insert_one(
            {"code": "SUMIU", "sparks_amount": 300, "active": True, "usos": 0, "created_at": "2026-09-01"}
        ))
        _cadastrar(db, "orfao@x.com", "SUMIU")
        _run(db.promo_codes.delete_one({"code": "SUMIU"}))

        linhas = _run(promo.uso_por_codigo(self._admin()))["items"]
        assert len(linhas) == 1
        assert linhas[0]["code"] == "SUMIU"
        assert linhas[0]["excluido"] is True
        assert linhas[0]["alunos_count"] == 1
