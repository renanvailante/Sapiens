"""O responsável legal de um aluno menor de idade.

Até 2026-09-17 o produto resolvia a questão da menoridade com uma frase dentro
do aceite dos termos ("se eu tiver menos de 18 anos, confirmo ter autorização
do meu responsável"). Essa frase não deixa registro nenhum: não diz QUEM é o
responsável nem COMO alcançá-lo — e a LGPD (art. 14) trata dado de criança e
adolescente à parte, exigindo consentimento de um responsável identificável.

O que estes testes travam:

1. **declarar-se menor sem responsável não cria conta** no cadastro por e-mail.
   Um registro que afirma "sou menor" e não tem contato de responsável é
   exatamente o que a lei não aceita — gravá-lo assim seria pior do que não
   perguntar nada;
2. **quem se declara maior nunca recebe campo de responsável**, mesmo mandando
   um. Guardar dado de terceiro sem finalidade é coleta indevida;
3. **o telefone do responsável é normalizado** como o do aluno, senão o painel
   do admin não consegue abrir conversa nenhuma com ele.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response

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


def _dublê_de_sessao(user):
    """`definir_whatsapp` resolve a sessão chamando `auth.require_user(request)`.
    Nos testes offline não há requisição nenhuma, então o dublê ignora o
    argumento e devolve o usuário direto."""
    async def _require(_request):
        return user
    return _require


def _pedido(**kwargs) -> SignupRequest:
    base = dict(
        email="aluno@x.com",
        name="Aluno Teste",
        password="senha-forte-1",
        whatsapp="(11) 91234-5678",
    )
    base.update(kwargs)
    return SignupRequest(**base)


class TestMenorDeIdade:
    def test_menor_com_responsavel_completo_cria_a_conta(self, db):
        _run(auth.signup(_pedido(
            menor_de_idade=True,
            responsavel_nome="Maria Silva",
            responsavel_whatsapp="(11) 99999-8888",
        ), Response()))
        doc = _run(db.users.find_one({"email": "aluno@x.com"}))
        assert doc["menor_de_idade"] is True
        assert doc["responsavel_nome"] == "Maria Silva"
        # O par de sempre: o que a pessoa digitou e o número discável.
        assert doc["responsavel_whatsapp"] == "(11) 99999-8888"
        assert doc["responsavel_whatsapp_e164"] == "5511999998888"

    @pytest.mark.parametrize("faltando", [
        {"responsavel_nome": None, "responsavel_whatsapp": "(11) 99999-8888"},
        {"responsavel_nome": "Maria Silva", "responsavel_whatsapp": None},
        {"responsavel_nome": "   ", "responsavel_whatsapp": "   "},
    ])
    def test_menor_sem_responsavel_nao_cria_conta(self, db, faltando):
        with pytest.raises(HTTPException) as exc:
            _run(auth.signup(_pedido(menor_de_idade=True, **faltando), Response()))
        assert exc.value.status_code == 422
        assert _run(db.users.count_documents({})) == 0

    def test_whatsapp_impossivel_do_responsavel_e_recusado(self, db):
        with pytest.raises(HTTPException) as exc:
            _run(auth.signup(_pedido(
                menor_de_idade=True,
                responsavel_nome="Maria Silva",
                responsavel_whatsapp="123",
            ), Response()))
        assert exc.value.status_code == 422
        assert "respons" in exc.value.detail.lower()
        assert _run(db.users.count_documents({})) == 0


class TestMaiorDeIdade:
    def test_maior_nao_guarda_responsavel_nenhum(self, db):
        """Quem se declara maior não tem responsável — nem se a requisição
        trouxer um. Guardar o telefone de um terceiro sem finalidade é coleta
        indevida, e o campo viraria dado órfão no inventário da LGPD."""
        _run(auth.signup(_pedido(
            menor_de_idade=False,
            responsavel_nome="Alguém Qualquer",
            responsavel_whatsapp="(11) 99999-8888",
        ), Response()))
        doc = _run(db.users.find_one({"email": "aluno@x.com"}))
        assert doc["menor_de_idade"] is False
        assert doc["responsavel_nome"] is None
        assert doc["responsavel_whatsapp"] is None
        assert doc["responsavel_whatsapp_e164"] is None

    def test_cadastro_normal_continua_funcionando(self, db):
        """A pergunta é nova; o caminho antigo não pode ter mudado. Quem não
        manda nada sobre idade cria conta como sempre."""
        _run(auth.signup(_pedido(), Response()))
        doc = _run(db.users.find_one({"email": "aluno@x.com"}))
        assert doc["menor_de_idade"] is False
        assert doc["whatsapp_e164"] == "5511912345678"


class TestCompletarCadastroPeloGoogle:
    """`POST /auth/whatsapp` — a segunda metade do cadastro de quem entrou pelo
    botão do Google, onde não existe formulário.

    Essa conta nasce com nome e e-mail verificados e SEM telefone. Desde
    2026-09-17 os cartões que pediam o número depois saíram das telas, então
    esta rota é a única porta que sobrou — e `ProtectedRoute` manda todo mundo
    sem telefone para a tela que fala com ela.
    """

    # Chamada direta à função da rota, como todo teste offline deste repo. A
    # diferença aqui é que `definir_whatsapp` tem parâmetros `Body(...)` com
    # default: sem o FastAPI no meio, o default que chega é o próprio objeto
    # `Body`, não `None`. Por isso TODOS os campos são passados explicitamente
    # — é o que a requisição real entrega.
    def _completar(self, **kwargs):
        campos = {
            "whatsapp": "(11) 91234-5678",
            "menor_de_idade": None,
            "responsavel_nome": None,
            "responsavel_whatsapp": None,
        }
        campos.update(kwargs)
        return _run(auth.definir_whatsapp(None, **campos))

    def _conta_do_google(self, db, email="google@x.com"):
        _run(db.users.insert_one({
            "user_id": "u-google", "email": email, "name": "Aluno Google",
            "provider": "google", "email_verificado": True,
            "whatsapp": None, "whatsapp_e164": None, "is_admin": False,
        }))
        return SimpleNamespace(user_id="u-google", email=email, name="Aluno Google")

    def test_grava_o_telefone_e_o_numero_discavel(self, db, monkeypatch):
        u = self._conta_do_google(db)
        monkeypatch.setattr(auth, "require_user", _dublê_de_sessao(u))
        self._completar()
        doc = _run(db.users.find_one({"user_id": "u-google"}))
        assert doc["whatsapp"] == "(11) 91234-5678"
        assert doc["whatsapp_e164"] == "5511912345678"

    def test_menor_pelo_google_tambem_precisa_do_responsavel(self, db, monkeypatch):
        u = self._conta_do_google(db)
        monkeypatch.setattr(auth, "require_user", _dublê_de_sessao(u))
        with pytest.raises(HTTPException) as exc:
            self._completar(menor_de_idade=True)
        assert exc.value.status_code == 422
        # E o telefone NÃO foi gravado pela metade: o `update_one` só acontece
        # depois de os campos do responsável passarem.
        assert _run(db.users.find_one({"user_id": "u-google"}))["whatsapp"] is None

    def test_menor_completo_grava_os_dois_contatos(self, db, monkeypatch):
        u = self._conta_do_google(db)
        monkeypatch.setattr(auth, "require_user", _dublê_de_sessao(u))
        self._completar(
            menor_de_idade=True,
            responsavel_nome="Maria Silva",
            responsavel_whatsapp="(11) 99999-8888",
        )
        doc = _run(db.users.find_one({"user_id": "u-google"}))
        assert doc["menor_de_idade"] is True
        assert doc["responsavel_whatsapp_e164"] == "5511999998888"

    def test_declarar_se_maior_limpa_um_responsavel_antigo(self, db, monkeypatch):
        """Quem se declarou menor por engano e corrige não pode continuar com o
        telefone de um terceiro guardado — vira dado sem finalidade."""
        u = self._conta_do_google(db)
        _run(db.users.update_one({"user_id": "u-google"}, {"$set": {
            "menor_de_idade": True, "responsavel_nome": "Maria",
            "responsavel_whatsapp": "(11) 99999-8888",
            "responsavel_whatsapp_e164": "5511999998888",
        }}))
        monkeypatch.setattr(auth, "require_user", _dublê_de_sessao(u))
        self._completar(menor_de_idade=False)
        doc = _run(db.users.find_one({"user_id": "u-google"}))
        assert doc["menor_de_idade"] is False
        assert doc["responsavel_nome"] is None
        assert doc["responsavel_whatsapp_e164"] is None

    def test_numero_impossivel_nao_grava_nada(self, db, monkeypatch):
        u = self._conta_do_google(db)
        monkeypatch.setattr(auth, "require_user", _dublê_de_sessao(u))
        with pytest.raises(HTTPException) as exc:
            self._completar(whatsapp="123")
        assert exc.value.status_code == 422
        assert _run(db.users.find_one({"user_id": "u-google"}))["whatsapp"] is None
