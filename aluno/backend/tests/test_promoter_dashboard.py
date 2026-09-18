"""Isolamento do painel do promoter.

Um promoter é qualquer conta cujo e-mail está gravado em
`promo_codes.promoter_email` (o admin faz isso em `/admin/promo-codes`). O
requisito de segurança que importa aqui não é "a tela mostra os números
certos" — é "o promoter A NUNCA recebe um byte sobre o aluno ou o dinheiro do
promoter B". Estes testes rodam offline, com o dublê de Mongo de `conftest.py`.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException, Response

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import auth  # noqa: E402
import firestore_service as fs  # noqa: E402
import promo_codes_routes as promo  # noqa: E402
import promoter_routes as promoter  # noqa: E402
import rate_limit  # noqa: E402
from models import SignupRequest, User  # noqa: E402


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
    promoter.set_db(fake_db)
    monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: True)
    # Saldo de Sparks determinístico por aluno, sem tocar o Firestore de
    # verdade — cada aluno de teste recebe 10 Sparks por letra do e-mail dele
    # só para os valores não baterem por acaso entre alunos diferentes.
    monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: len(uid) * 10)
    return fake_db


def _cadastrar(db, email: str, promo_code: str | None = None) -> dict:
    _run(auth.signup(
        SignupRequest(
            email=email, name=f"Aluno {email}", password="senha-forte-1",
            whatsapp="(11) 91234-5678", promo_code=promo_code,
        ),
        Response(),
    ))
    return _run(db.users.find_one({"email": email}))


def _pagamento(db, user_id: str, price_cents: int, *, credited: bool = True):
    _run(db.sparks_payments.insert_one({
        "purchase_id": f"p-{user_id}-{price_cents}",
        "user_id": user_id,
        "price_cents": price_cents,
        "credited": credited,
        "status": "approved" if credited else "pending",
    }))


class TestIsolamentoEntrePromoters:
    def test_promoter_so_ve_os_alunos_do_proprio_cupom(self, db):
        _run(db.promo_codes.insert_one({
            "code": "PROMO1", "sparks_amount": 100, "active": True, "usos": 0,
            "promoter_email": "promoter1@x.com",
        }))
        _run(db.promo_codes.insert_one({
            "code": "PROMO2", "sparks_amount": 100, "active": True, "usos": 0,
            "promoter_email": "promoter2@x.com",
        }))
        aluno1 = _cadastrar(db, "aluno1@x.com", "PROMO1")
        aluno2 = _cadastrar(db, "aluno2@x.com", "PROMO2")
        _pagamento(db, aluno1["user_id"], 5000)
        _pagamento(db, aluno2["user_id"], 9999)

        p1 = User(user_id="u1", email="promoter1@x.com", name="Promoter 1")
        resultado = _run(promoter.dashboard(p1))

        assert resultado["total_alunos"] == 1
        assert len(resultado["cupons"]) == 1
        assert resultado["cupons"][0]["code"] == "PROMO1"
        alunos = resultado["cupons"][0]["alunos"]
        assert len(alunos) == 1
        assert alunos[0]["gasto_centavos"] == 5000
        # Nada do outro cupom/promoter/aluno vaza para cá — nem o valor, nem
        # o nome, nem a existência do cupom PROMO2.
        assert resultado["total_gasto_centavos"] == 5000
        assert "PROMO2" not in {c["code"] for c in resultado["cupons"]}

    def test_gasto_nao_creditado_nao_conta_como_dinheiro_recebido(self, db):
        """Um Pix pendente ou recusado não é dinheiro que passou a mão — se
        entrasse na soma, o promoter veria (e cobraria) uma comissão sobre
        uma venda que não aconteceu."""
        _run(db.promo_codes.insert_one({
            "code": "PROMO1", "sparks_amount": 100, "active": True, "usos": 0,
            "promoter_email": "promoter1@x.com",
        }))
        aluno = _cadastrar(db, "aluno1@x.com", "PROMO1")
        _pagamento(db, aluno["user_id"], 5000, credited=True)
        _pagamento(db, aluno["user_id"], 12345, credited=False)

        p1 = User(user_id="u1", email="promoter1@x.com", name="Promoter 1")
        resultado = _run(promoter.dashboard(p1))

        assert resultado["total_gasto_centavos"] == 5000

    def test_promoter_sem_alunos_ainda_ve_o_proprio_cupom_zerado(self, db):
        _run(db.promo_codes.insert_one({
            "code": "NOVO", "sparks_amount": 100, "active": True, "usos": 0,
            "promoter_email": "promoter1@x.com",
        }))
        p1 = User(user_id="u1", email="promoter1@x.com", name="Promoter 1")
        resultado = _run(promoter.dashboard(p1))
        assert resultado["cupons"][0]["alunos_count"] == 0
        assert resultado["total_gasto_centavos"] == 0


class TestAcessoDeQuemNaoEhPromoter:
    def test_conta_sem_cupom_vinculado_e_recusada(self, db):
        aluno_comum = User(user_id="u2", email="ninguem@x.com", name="Aluno")
        with pytest.raises(HTTPException) as exc:
            _run(promoter.require_promoter(aluno_comum))
        assert exc.value.status_code == 403

    def test_email_do_promoter_e_comparado_sem_diferenciar_caixa(self, db):
        """O catálogo sempre guarda o e-mail do promoter em minúsculas (é o
        que `_normalizar_promoter_email` garante ao salvar); esta conta loga
        com o e-mail em outra caixa, e ainda assim tem que ser reconhecida."""
        _run(db.promo_codes.insert_one({
            "code": "PROMO1", "sparks_amount": 100, "active": True, "usos": 0,
            "promoter_email": "promoter1@x.com",
        }))
        # `EmailStr` do Pydantic já normaliza o DOMÍNIO para minúsculas —
        # o que sobrevive em caixa alta aqui é só a parte local, e é
        # exatamente essa diferença de caixa que `require_promoter` precisa
        # ignorar para casar com o catálogo.
        promoter_user = User(user_id="u1", email="Promoter1@X.com", name="Promoter 1")
        assert promoter_user.email == "Promoter1@x.com"
        aprovado = _run(promoter.require_promoter(promoter_user))
        assert aprovado.email == "Promoter1@x.com"


class TestEmailDoPromoterNoCupom:
    def _admin(self):
        return User(user_id="admin", email="admin@x.com", name="Admin", is_admin=True)

    def test_admin_vincula_promoter_ao_criar_o_cupom(self, db):
        from models import CreatePromoCodeRequest

        criado = _run(promo.create_promo_code(
            CreatePromoCodeRequest(code="NOVO", sparks_amount=50, promoter_email="  Fulano@X.com "),
            self._admin(),
        ))
        assert criado["promoter_email"] == "fulano@x.com"

    def test_admin_limpa_o_promoter_com_email_nulo(self, db):
        from models import UpdatePromoCodeRequest

        _run(db.promo_codes.insert_one({
            "code": "X", "sparks_amount": 50, "active": True, "usos": 0,
            "promoter_email": "alguem@x.com",
        }))
        atualizado = _run(promo.update_promo_code("X", UpdatePromoCodeRequest(promoter_email=None), self._admin()))
        assert atualizado["promoter_email"] is None

    def test_email_de_promoter_sem_arroba_e_recusado(self, db):
        from models import CreatePromoCodeRequest

        with pytest.raises(HTTPException) as exc:
            _run(promo.create_promo_code(
                CreatePromoCodeRequest(code="X23", sparks_amount=50, promoter_email="nao-e-email"),
                self._admin(),
            ))
        assert exc.value.status_code == 422
