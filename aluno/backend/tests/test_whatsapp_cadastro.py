"""O WhatsApp do aluno: normalização, cadastro e o que o admin enxerga.

O campo existe por um motivo operacional: é o único canal em que a equipe
alcança um estudante de verdade — e é por ele que o link da aula ao vivo de
quinta chega a quem pagou. Um número guardado como texto livre não serve para
isso: não vira `wa.me`, não dá para comparar, e o mesmo aluno cadastrado duas
vezes vira dois números diferentes.

Por isso o contrato testado aqui é sempre o par: `whatsapp` (o que a pessoa
digitou, que ela reconhece) e `whatsapp_e164` (o número discável).
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
import rate_limit  # noqa: E402
import whatsapp as wa  # noqa: E402
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


def _cadastrar(db, email="aluno@x.com", whatsapp="(11) 91234-5678"):
    _run(auth.signup(
        SignupRequest(email=email, name="Aluno Teste", password="senha-forte-1", whatsapp=whatsapp),
        Response(),
    ))
    return _run(db.users.find_one({"email": email}))


class TestNormalizacao:
    @pytest.mark.parametrize("digitado", [
        "(11) 91234-5678",
        "11912345678",
        "+55 11 91234-5678",
        "55 11 91234 5678",
        "0055 11 912345678",
        "11 9 1234 5678",
    ])
    def test_todas_as_formas_do_mesmo_numero_chegam_no_mesmo_e164(self, digitado):
        """O aluno digita de seis jeitos; o painel precisa de um só. Sem isto,
        o mesmo número entra no banco em seis formatos e nenhum deles abre
        conversa."""
        _, e164 = wa.normalizar(digitado)
        assert e164 == "5511912345678"

    def test_o_texto_do_titular_e_preservado(self):
        digitado, _ = wa.normalizar("  (11)  91234-5678 ")
        assert digitado == "(11) 91234-5678"

    def test_fixo_de_oito_digitos_ganha_ddi(self):
        _, e164 = wa.normalizar("(11) 3123-4567")
        assert e164 == "551131234567"

    def test_numero_de_outro_pais_passa_sem_ddi_brasileiro(self):
        _, e164 = wa.normalizar("+351 912 345 678")
        assert e164 == "351912345678"

    @pytest.mark.parametrize("invalido", ["", "   ", "12345", "abc", "9999999999999999999"])
    def test_numero_que_nao_disca_e_recusado(self, invalido):
        with pytest.raises(wa.WhatsAppInvalido):
            wa.normalizar(invalido)

    def test_link_de_conversa_e_o_wa_me_do_numero(self):
        assert wa.link_conversa("5511912345678") == "https://wa.me/5511912345678"

    def test_sem_numero_nao_ha_link_quebrado(self):
        """`None` e não um `wa.me/` vazio: a tela do admin distingue "não
        temos o número" de "temos e não abre"."""
        assert wa.link_conversa(None) is None
        assert wa.formatar_br(None) is None

    def test_formatacao_brasileira_para_leitura(self):
        assert wa.formatar_br("5511912345678") == "(11) 91234-5678"
        assert wa.formatar_br("551131234567") == "(11) 3123-4567"

    def test_numero_estrangeiro_nao_ganha_parenteses_inventados(self):
        assert wa.formatar_br("351912345678") == "+351912345678"


class TestCadastro:
    def test_cadastro_grava_os_dois_formatos(self, db):
        conta = _cadastrar(db)
        assert conta["whatsapp"] == "(11) 91234-5678"
        assert conta["whatsapp_e164"] == "5511912345678"

    def test_cadastro_com_numero_invalido_e_422(self, db):
        # 8 dígitos passa pelo `min_length` do schema (que só barra campo
        # vazio) e morre na validação de verdade, em `whatsapp.normalizar` —
        # que é onde mora a mensagem que o aluno lê.
        with pytest.raises(HTTPException) as exc:
            _cadastrar(db, whatsapp="12345678")
        assert exc.value.status_code == 422

    def test_numero_invalido_nao_deixa_conta_pela_metade(self, db):
        """A validação acontece ANTES do `insert_one`. Se acontecesse depois,
        o aluno veria um erro e teria uma conta criada que ele não sabe que
        existe — e o e-mail já estaria "em uso" na segunda tentativa."""
        with pytest.raises(HTTPException):
            _cadastrar(db, email="meio@x.com", whatsapp="12345678")
        assert _run(db.users.find_one({"email": "meio@x.com"})) is None

    def test_o_campo_e_obrigatorio_no_cadastro_por_email(self):
        with pytest.raises(Exception):  # ValidationError do Pydantic
            SignupRequest(email="a@x.com", name="A", password="senha-forte-1")


class TestContaSemNumero:
    """Contas do Google e as anteriores a 2026-09-15 entram sem número —
    e são justamente as mais antigas, ou seja, as mais engajadas."""

    def test_login_com_google_sem_numero_nao_inventa_campo(self):
        assert auth._campos_de_whatsapp(None) == {}

    def test_numero_invalido_no_google_e_ignorado_em_vez_de_barrar_a_entrada(self):
        """Recusar a autenticação por causa de um telefone mal digitado
        trocaria um dado que falta por uma pessoa que não consegue entrar."""
        assert auth._campos_de_whatsapp("123") == {}

    def test_numero_valido_no_google_e_gravado(self):
        assert auth._campos_de_whatsapp("11912345678") == {
            "whatsapp": "11912345678",
            "whatsapp_e164": "5511912345678",
        }
