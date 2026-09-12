"""Direitos do titular (LGPD art. 18) — exportação e exclusão de conta.

A exclusão é destrutiva e sem volta, então os testes aqui cobrem tanto o que
ela PRECISA apagar quanto o que ela NÃO PODE apagar.
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import dados_pessoais as dp  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class _FakeSnap:
    def __init__(self, data=None):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class _FakeSubcolecao:
    def __init__(self, docs):
        self._docs = docs

    def stream(self):
        return iter([_FakeSnap(d) for d in self._docs])


class _FakeDocRef:
    def __init__(self, data=None, subs=None):
        self._data = data
        self._subs = subs or {}

    def get(self):
        return _FakeSnap(self._data)

    def collection(self, nome):
        return _FakeSubcolecao(self._subs.get(nome, []))


class _FakeFirestore:
    def __init__(self, doc_ref, explode_no_delete=False):
        self._doc_ref = doc_ref
        self.apagou = None
        self._explode = explode_no_delete

    def collection(self, _nome):
        ref = self._doc_ref
        class _Col:
            def document(self, _uid):
                return ref
        return _Col()

    def recursive_delete(self, ref):
        if self._explode:
            raise RuntimeError("Firestore fora do ar")
        self.apagou = ref
        return 42


@pytest.fixture
def firestore_falso(monkeypatch):
    def _montar(doc_ref, explode=False):
        import firestore_service

        fake = _FakeFirestore(doc_ref, explode_no_delete=explode)
        monkeypatch.setattr(firestore_service, "get_firestore", lambda *a, **k: fake)
        return fake

    return _montar


async def _povoar(db, uid="aluno-1"):
    await db.users.insert_one({
        "user_id": uid, "email": "a@x.com", "name": "Aluno",
        "password_hash": "$2b$hash-secreto",
    })
    await db.user_sessions.insert_one({"user_id": uid, "session_token": "tok-secreto"})
    await db.password_resets.insert_one({"user_id": uid, "token_hash": "hash-secreto"})
    await db.redacoes.insert_one({"user_id": uid, "redacao_id": "r1", "texto": "minha redação"})
    await db.redacao_avaliacoes.insert_one({"redacao_id": "r1", "nota": 880})
    await db.sugestoes.insert_one({"user_id": uid, "texto": "achei X confuso"})
    await db.analyses.insert_one({"user_id": uid, "analysis_id": "an1"})
    # De OUTRO aluno — nunca pode ser tocado.
    await db.redacoes.insert_one({"user_id": "outro", "redacao_id": "r9", "texto": "alheia"})
    await db.sugestoes.insert_one({"user_id": "outro", "texto": "alheia"})


class TestExportacao:
    def test_nunca_devolve_senha_nem_token(self, fake_db, firestore_falso):
        """Hash de senha e token de sessão são CREDENCIAL. Entregá-los não
        atende direito nenhum do art. 18 e cria um alvo offline."""
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef({"sparks_balance": 10}))
        _run(_povoar(fake_db))

        export = _run(dp.exportar("aluno-1"))
        bruto = repr(export)
        assert "$2b$hash-secreto" not in bruto
        assert "tok-secreto" not in bruto
        assert "hash-secreto" not in bruto
        # ...mas os dados de verdade estão lá
        assert export["mongo"]["users"][0]["email"] == "a@x.com"

    def test_reune_mongo_e_firestore(self, fake_db, firestore_falso):
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef(
            {"sparks_balance": 10},
            {"behavior": [{"item_id": "Q1", "acertou": True}], "sparks_rounds": [{"rodada": 1}]},
        ))
        _run(_povoar(fake_db))

        export = _run(dp.exportar("aluno-1"))
        assert export["mongo"]["redacoes"][0]["texto"] == "minha redação"
        assert export["firestore"]["students"]["sparks_balance"] == 10
        assert export["firestore"]["behavior"][0]["item_id"] == "Q1"
        assert export["firestore"]["sparks_rounds"][0]["rodada"] == 1

    def test_alcanca_avaliacao_que_nao_tem_user_id(self, fake_db, firestore_falso):
        """`redacao_avaliacoes` pende de `redacao_id`. Sem a resolução, a nota
        da redação do aluno ficaria de fora da cópia."""
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef(None))
        _run(_povoar(fake_db))
        export = _run(dp.exportar("aluno-1"))
        assert export["mongo"]["redacao_avaliacoes"][0]["nota"] == 880

    def test_nao_vaza_dado_de_outro_aluno(self, fake_db, firestore_falso):
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef(None))
        _run(_povoar(fake_db))
        assert "alheia" not in repr(_run(dp.exportar("aluno-1")))


class TestExclusao:
    def test_apaga_o_aluno_e_preserva_os_outros(self, fake_db, firestore_falso):
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef({"sparks_balance": 1}))
        _run(_povoar(fake_db))

        _run(dp.excluir("aluno-1"))

        assert _run(fake_db.users.find_one({"user_id": "aluno-1"})) is None
        assert _run(fake_db.redacoes.find_one({"user_id": "aluno-1"})) is None
        assert _run(fake_db.sugestoes.find_one({"user_id": "aluno-1"})) is None
        assert _run(fake_db.redacao_avaliacoes.find_one({"redacao_id": "r1"})) is None
        # O outro aluno continua inteiro
        assert _run(fake_db.redacoes.find_one({"user_id": "outro"}))["texto"] == "alheia"

    def test_pagamento_e_anonimizado_e_nao_apagado(self, fake_db, firestore_falso):
        """Registro de operação financeira é o que a lei manda guardar
        (art. 16, I). Apagar deixaria a contabilidade sem lastro e uma disputa
        de estorno sem prova — o que sai é o VÍNCULO com a pessoa."""
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef(None))
        _run(fake_db.sparks_payments.insert_one({
            "user_id": "aluno-1", "mp_payment_id": "MP-1",
            "price_cents": 1990, "currency": "BRL", "status": "approved",
        }))

        rel = _run(dp.excluir("aluno-1"))

        assert rel["mongo"]["sparks_payments_anonimizados"] == 1
        assert _run(fake_db.sparks_payments.find_one({"user_id": "aluno-1"})) is None
        sobrou = _run(fake_db.sparks_payments.find_one({"mp_payment_id": "MP-1"}))
        assert sobrou is not None, "o registro financeiro não pode sumir"
        assert sobrou["user_id"] == dp.TOMBSTONE
        assert sobrou["price_cents"] == 1990
        assert sobrou["titular_excluido_em"]

    def test_questao_gerada_por_ia_fica_e_so_o_vinculo_sai(self, fake_db, firestore_falso):
        """A questão é conteúdo, paga por um aluno e reaproveitada por todos.
        Apagá-la puniria os outros; o dado pessoal é só 'este aluno já viu'."""
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef(None))
        _run(fake_db.treino_questoes_ia.insert_one({
            "hab_id": "H1", "enunciado": "questão cara", "mostrada_para": ["aluno-1", "outro"],
        }))

        _run(dp.excluir("aluno-1"))

        q = _run(fake_db.treino_questoes_ia.find_one({"hab_id": "H1"}))
        assert q["enunciado"] == "questão cara"
        assert q["mostrada_para"] == ["outro"]

    def test_apaga_documento_de_id_composto(self, fake_db, firestore_falso):
        """`mentis_intervencoes_abertas` usa `_id = "{uid}|{chave}"` — não tem
        campo `user_id` para casar."""
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef(None))
        _run(fake_db.mentis_intervencoes_abertas.insert_one({"_id": "aluno-1|ERR-05"}))
        _run(fake_db.mentis_intervencoes_abertas.insert_one({"_id": "outro|ERR-05"}))

        _run(dp.excluir("aluno-1"))

        assert _run(fake_db.mentis_intervencoes_abertas.find_one({"_id": "aluno-1|ERR-05"})) is None
        assert _run(fake_db.mentis_intervencoes_abertas.find_one({"_id": "outro|ERR-05"})) is not None

    def test_firestore_apagado_em_arvore(self, fake_db, firestore_falso):
        """Subcoleção NÃO morre com o documento pai no Firestore: apagar só
        `students/{uid}` deixaria `behavior` órfã e legível."""
        dp.set_db(fake_db)
        fake = firestore_falso(_FakeDocRef({"sparks_balance": 1}))
        rel = _run(dp.excluir("aluno-1"))
        assert fake.apagou is not None, "recursive_delete não foi chamado"
        assert rel["firestore"]["documentos_apagados"] == 42

    def test_firestore_fora_do_ar_nao_impede_a_limpeza_do_mongo(self, fake_db, firestore_falso):
        """Falha parcial precisa APARECER, não passar por sucesso — senão o
        pedido é respondido como cumprido com dado de menor ainda no banco."""
        dp.set_db(fake_db)
        firestore_falso(_FakeDocRef(None), explode=True)
        _run(_povoar(fake_db))

        rel = _run(dp.excluir("aluno-1"))

        assert _run(fake_db.users.find_one({"user_id": "aluno-1"})) is None
        assert rel["firestore"]["pendente"] is True
        assert "erro" in rel["firestore"]


class TestInventarioCompleto:
    """A garantia prometida no docstring de `dados_pessoais`.

    Coleção nova que guarde dado de aluno e que ninguém classifique vira dado
    esquecido numa exclusão — sem erro, sem sintoma. Este teste varre o código
    e obriga a decisão."""

    def test_toda_colecao_usada_esta_classificada(self):
        conhecidas = (
            {c for c, _ in dp.COLECOES_POR_USUARIO}
            | set(dp.COLECOES_TRATAMENTO_ESPECIAL)
            | set(dp.COLECOES_SEM_DADO_PESSOAL)
        )
        padrao = re.compile(r'_db\.([a-z][a-z0-9_]+)\.(?:find|insert|update|delete|count|aggregate)')
        encontradas: set[str] = set()
        for arquivo in BACKEND.glob("*.py"):
            encontradas |= set(padrao.findall(arquivo.read_text(encoding="utf-8")))

        nao_classificadas = encontradas - conhecidas
        assert not nao_classificadas, (
            "Coleção(ões) do Mongo sem classificação em `dados_pessoais.py`: "
            f"{sorted(nao_classificadas)}.\n"
            "Toda coleção precisa entrar em COLECOES_POR_USUARIO (apagada com o "
            "aluno), COLECOES_TRATAMENTO_ESPECIAL (regra própria) ou "
            "COLECOES_SEM_DADO_PESSOAL (não guarda dado pessoal). Sem isso, a "
            "exclusão de conta deixa dado para trás em silêncio."
        )


# =============================================================== as rotas
#
# A exclusão é irreversível. Estes testes cobrem os freios — o que impede que
# ela aconteça por clique errado, link malicioso ou requisição repetida.

class _Resp:
    """`Response` mínimo: só o que `delete_cookie` precisa."""

    def __init__(self):
        self.apagou_cookie = False

    def delete_cookie(self, *_a, **_k):
        self.apagou_cookie = True


@pytest.fixture
def rotas(fake_db, monkeypatch):
    import dados_pessoais_routes as r

    r.set_db(fake_db)
    return r


def _usuario(provider="email", uid="aluno-1"):
    from models import User

    return User(user_id=uid, email="a@x.com", name="Aluno", provider=provider)


class TestFreiosDaExclusao:
    def test_sem_a_palavra_de_confirmacao_nao_apaga(self, rotas, fake_db, firestore_falso):
        from fastapi import HTTPException

        firestore_falso(_FakeDocRef(None))
        _run(_povoar(fake_db))

        with pytest.raises(HTTPException) as e:
            _run(rotas.excluir_minha_conta(
                _Resp(), rotas.ExclusaoRequest(confirmacao="sim", senha="x"), _usuario()
            ))
        assert e.value.status_code == 400
        assert _run(fake_db.users.find_one({"user_id": "aluno-1"})) is not None

    def test_senha_errada_nao_apaga_conta_de_email(self, rotas, fake_db, firestore_falso):
        from fastapi import HTTPException
        import auth

        firestore_falso(_FakeDocRef(None))
        _run(fake_db.users.insert_one({
            "user_id": "aluno-1", "email": "a@x.com", "name": "A",
            "password_hash": auth._hash_password("certa"),
        }))

        with pytest.raises(HTTPException) as e:
            _run(rotas.excluir_minha_conta(
                _Resp(), rotas.ExclusaoRequest(confirmacao="EXCLUIR", senha="errada"), _usuario()
            ))
        assert e.value.status_code == 401
        assert _run(fake_db.users.find_one({"user_id": "aluno-1"})) is not None

    def test_senha_certa_apaga_e_encerra_a_sessao(self, rotas, fake_db, firestore_falso):
        import auth

        firestore_falso(_FakeDocRef(None))
        _run(fake_db.users.insert_one({
            "user_id": "aluno-1", "email": "a@x.com", "name": "A",
            "password_hash": auth._hash_password("certa"),
        }))
        resp = _Resp()

        out = _run(rotas.excluir_minha_conta(
            resp, rotas.ExclusaoRequest(confirmacao="EXCLUIR", senha="certa"), _usuario()
        ))

        assert out["ok"] is True
        assert _run(fake_db.users.find_one({"user_id": "aluno-1"})) is None
        assert resp.apagou_cookie, "o cookie precisa morrer junto com a conta"

    def test_conta_google_nao_exige_senha(self, rotas, fake_db, firestore_falso):
        """Quem entrou pelo Google não tem senha para confirmar — exigir uma
        deixaria esse aluno sem forma nenhuma de exercer o art. 18, VI."""
        firestore_falso(_FakeDocRef(None))
        _run(fake_db.users.insert_one({"user_id": "aluno-1", "email": "a@x.com", "name": "A"}))

        out = _run(rotas.excluir_minha_conta(
            _Resp(), rotas.ExclusaoRequest(confirmacao="EXCLUIR"), _usuario(provider="google")
        ))

        assert out["ok"] is True
        assert _run(fake_db.users.find_one({"user_id": "aluno-1"})) is None

    def test_admin_precisa_da_confirmacao_e_do_usuario_existir(self, rotas, fake_db, firestore_falso):
        from fastapi import HTTPException

        firestore_falso(_FakeDocRef(None))
        admin = _usuario(uid="admin-1")

        with pytest.raises(HTTPException) as e:
            _run(rotas.excluir_conta_de("aluno-1", admin, confirmacao="sim"))
        assert e.value.status_code == 400

        with pytest.raises(HTTPException) as e:
            _run(rotas.excluir_conta_de("nao-existe", admin, confirmacao="EXCLUIR"))
        assert e.value.status_code == 404
