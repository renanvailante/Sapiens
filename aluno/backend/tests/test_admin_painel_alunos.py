"""O painel de alunos do admin: saldo, volume de respostas, ficha e transações.

Três rotas, uma pergunta cada:
  * `GET /admin/users`            — quem são, com quanto de Spark e quantas questões;
  * `GET /admin/users/{id}/detalhe` — tudo que se sabe sobre UM aluno;
  * `GET /admin/transacoes`       — toda cobrança de Sparks já registrada.

O que se protege aqui é o que não aparece em teste manual: a tela de
PERMISSÕES não pode cair junto com o Firestore (é ela que revoga um admin), e
a tela de transações não pode inventar um saldo que ninguém registrou.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import admin_routes  # noqa: E402
import firestore_service as fs  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


ADMIN = User(user_id="admin", email="admin@x.com", name="Admin", is_admin=True)


@pytest.fixture
def db(fake_db, monkeypatch):
    admin_routes.set_db(fake_db)
    monkeypatch.setattr(fs, "resumo_dos_alunos", lambda: {})
    return fake_db


def _aluno(db, user_id: str, **campos):
    doc = {"user_id": user_id, "email": f"{user_id}@x.com", "name": user_id,
           "provider": "email", "is_admin": False, "created_at": "2026-09-01"}
    doc.update(campos)
    _run(db.users.insert_one(doc))
    return doc


class TestListaDeAlunos:
    def test_junta_saldo_e_questoes_do_firestore(self, db, monkeypatch):
        _aluno(db, "ana")
        monkeypatch.setattr(fs, "resumo_dos_alunos", lambda: {
            "ana": {"sparks_balance": 420, "questoes_respondidas": 87,
                    "dias_ativos": 9, "ultima_atividade": "2026-09-14"},
        })
        linha = _run(admin_routes.list_users(ADMIN))[0]
        assert linha["sparks_balance"] == 420
        assert linha["questoes_respondidas"] == 87
        assert linha["dias_ativos"] == 9

    def test_firestore_fora_do_ar_nao_derruba_a_tela_de_permissoes(self, db, monkeypatch):
        """Cota estourada (2026-09-04) fazia toda rota que lê o Firestore
        responder erro. Esta é a tela que REVOGA um admin: ela tem de abrir
        mesmo assim, dizendo que o saldo está indisponível."""
        _aluno(db, "ana")

        def _quebrado():
            raise RuntimeError("cota esgotada")

        monkeypatch.setattr(fs, "resumo_dos_alunos", _quebrado)
        linha = _run(admin_routes.list_users(ADMIN))[0]
        assert linha["email"] == "ana@x.com"
        assert linha["sparks_balance"] is None
        assert linha["sparks_indisponivel"] is True

    def test_aluno_sem_perfil_no_firestore_ainda_aparece(self, db):
        """Conta criada e nunca usada não tem documento em `students` — e
        continua sendo uma conta que o admin precisa enxergar."""
        _aluno(db, "fantasma")
        linha = _run(admin_routes.list_users(ADMIN))[0]
        assert linha["user_id"] == "fantasma"
        assert linha["sparks_balance"] is None

    def test_senha_nunca_sai_na_resposta(self, db):
        _aluno(db, "ana", password_hash="$2b$12$nao-pode-vazar")
        assert "password_hash" not in _run(admin_routes.list_users(ADMIN))[0]

    def test_cupom_usado_no_cadastro_acompanha_a_linha(self, db):
        _aluno(db, "ana", promo_code="BEMVINDO2026", promo_sparks=500)
        linha = _run(admin_routes.list_users(ADMIN))[0]
        assert linha["promo_code"] == "BEMVINDO2026"
        assert linha["promo_sparks"] == 500


class TestFichaDoAluno:
    def test_reune_conta_perfil_e_atividade(self, db, monkeypatch):
        _aluno(db, "ana")
        _run(db.redacoes.insert_one({"user_id": "ana"}))
        _run(db.redacoes.insert_one({"user_id": "ana"}))
        _run(db.sugestoes.insert_one({"user_id": "outro"}))
        monkeypatch.setattr(fs, "resumo_de_um_aluno", lambda uid: {
            "existe": True, "sparks_balance": 300, "questoes_respondidas": 12,
        })

        ficha = _run(admin_routes.detalhe_usuario("ana", ADMIN))
        assert ficha["conta"]["email"] == "ana@x.com"
        assert ficha["perfil"]["sparks_balance"] == 300
        assert ficha["atividade"]["redacoes"] == 2
        assert ficha["atividade"]["sugestoes"] == 0

    def test_soma_so_o_que_foi_de_fato_pago(self, db, monkeypatch):
        """Um Pix abandonado aparece na lista de transações do aluno, mas não
        pode entrar em "quanto ele gastou" — não houve dinheiro."""
        _aluno(db, "ana")
        monkeypatch.setattr(fs, "resumo_de_um_aluno", lambda uid: {"existe": True})
        _run(db.sparks_payments.insert_one({
            "user_id": "ana", "price_cents": 5490, "sparks_amount": 1500,
            "credited": True, "created_at": "2026-09-10",
        }))
        _run(db.sparks_payments.insert_one({
            "user_id": "ana", "price_cents": 9900, "sparks_amount": 4000,
            "credited": False, "status": "pending", "created_at": "2026-09-11",
        }))

        ficha = _run(admin_routes.detalhe_usuario("ana", ADMIN))
        assert ficha["financeiro"]["transacoes"] == 2
        assert ficha["financeiro"]["transacoes_pagas"] == 1
        assert ficha["financeiro"]["gasto_centavos"] == 5490
        assert ficha["financeiro"]["sparks_comprados"] == 1500

    def test_firestore_fora_do_ar_nao_derruba_a_ficha(self, db, monkeypatch):
        _aluno(db, "ana")

        def _quebrado(uid):
            raise RuntimeError("cota esgotada")

        monkeypatch.setattr(fs, "resumo_de_um_aluno", _quebrado)
        ficha = _run(admin_routes.detalhe_usuario("ana", ADMIN))
        assert ficha["perfil"] == {"indisponivel": True}
        assert ficha["conta"]["email"] == "ana@x.com"

    def test_usuario_inexistente_e_404(self, db):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as e:
            _run(admin_routes.detalhe_usuario("ninguem", ADMIN))
        assert e.value.status_code == 404


class TestTransacoes:
    def test_mostra_quem_pagou_o_que_e_como(self, db):
        _aluno(db, "ana")
        _run(db.sparks_payments.insert_one({
            "user_id": "ana", "package_id": "spark_1500", "sparks_amount": 1500,
            "price_cents": 5490, "payment_method_id": "pix", "status": "approved",
            "credited": True, "saldo_antes": 40, "saldo_apos": 1540,
            "created_at": "2026-09-10T12:00:00+00:00",
        }))
        linha = _run(admin_routes.listar_transacoes(admin=ADMIN))["items"][0]
        assert linha["aluno_nome"] == "ana"
        assert linha["aluno_email"] == "ana@x.com"
        assert linha["pacote_label"] == "1.500 Sparks"
        assert linha["payment_method_id"] == "pix"
        assert linha["saldo_antes"] == 40
        assert linha["created_at"] == "2026-09-10T12:00:00+00:00"

    def test_cobranca_nao_aprovada_continua_na_lista(self, db):
        """É justamente o caso que se investiga: o pagamento que não virou
        Spark. Uma tela que só mostrasse compras creditadas o esconderia."""
        _aluno(db, "ana")
        _run(db.sparks_payments.insert_one({
            "user_id": "ana", "package_id": "spark_200", "sparks_amount": 200,
            "price_cents": 990, "payment_method_id": "master", "status": "rejected",
            "credited": False, "created_at": "2026-09-10",
        }))
        resultado = _run(admin_routes.listar_transacoes(admin=ADMIN))
        assert resultado["count"] == 1
        assert resultado["resumo"]["creditadas"] == 0
        assert resultado["resumo"]["receita_centavos"] == 0

    def test_saldo_nao_registrado_vem_nulo_e_nao_zero(self, db):
        """Pagamentos creditados antes de 2026-09-15 não têm o carimbo de
        saldo. `None` vira "—" na tela; `0` seria uma afirmação falsa."""
        _aluno(db, "ana")
        _run(db.sparks_payments.insert_one({
            "user_id": "ana", "package_id": "spark_200", "sparks_amount": 200,
            "price_cents": 990, "payment_method_id": "pix", "status": "approved",
            "credited": True, "created_at": "2026-09-01",
        }))
        linha = _run(admin_routes.listar_transacoes(admin=ADMIN))["items"][0]
        assert linha.get("saldo_antes") is None

    def test_receita_soma_so_o_creditado(self, db):
        _aluno(db, "ana")
        for creditado, centavos in ((True, 5490), (True, 990), (False, 11990)):
            _run(db.sparks_payments.insert_one({
                "user_id": "ana", "package_id": "spark_200", "sparks_amount": 200,
                "price_cents": centavos, "credited": creditado, "created_at": "2026-09-10",
            }))
        resumo = _run(admin_routes.listar_transacoes(admin=ADMIN))["resumo"]
        assert resumo["total"] == 3
        assert resumo["creditadas"] == 2
        assert resumo["receita_centavos"] == 6480

    def test_pagamento_sem_aluno_conhecido_nao_quebra_a_tela(self, db):
        """`process_payment_webhook` grava pagamentos `unmatched` — sem
        `user_id` — de propósito, para revisão manual. A tela que existe para
        revisá-los não pode ser a que engasga com eles."""
        _run(db.sparks_payments.insert_one({
            "mp_payment_id": "mp-1", "status": "approved", "unmatched": True,
            "credited": False, "created_at": "2026-09-10",
        }))
        linha = _run(admin_routes.listar_transacoes(admin=ADMIN))["items"][0]
        assert linha["aluno_nome"] is None
        assert linha["pacote_label"] == "—"
