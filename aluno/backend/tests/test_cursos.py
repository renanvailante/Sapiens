"""A aba de Cursos: catálogo "em breve", e a aula ao vivo de quinta paga em
Sparks.

O que estes testes protegem, na ordem em que doeria:

1. **Ninguém é cobrado duas vezes pela mesma quinta-feira.** Duplo clique,
   retry do axios e duas abas caem na mesma reivindicação.
2. **Ninguém fica sem Sparks e sem vaga.** Saldo insuficiente ou Firestore
   instável desfazem a reivindicação inteira.
3. **Curso em pré-venda cobra UMA vez, para sempre** — 500 Sparks compram
   acesso vitalício, e clicar de novo daqui a um ano não cobra segunda vez.
   Entrar na lista de avisados continua de graça.
4. **A edição vendida é a mesma para todos**: o cálculo de "próxima quinta"
   mora num lugar só e não vira a semana seguinte no meio da aula.

Offline, com o dublê de Mongo do `conftest.py` e um Firestore de mentira.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import cursos  # noqa: E402
import cursos_routes as routes  # noqa: E402
import firestore_service as fs  # noqa: E402
import rate_limit  # noqa: E402
from cursos import ZONA_BRASIL  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user(uid="aluno-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno Teste")


def _admin() -> User:
    return User(user_id="admin-1", email="admin@exemplo.com", name="Admin", is_admin=True)


class _Carteira:
    """Saldo de Sparks em memória, com a MESMA regra do Firestore: débito
    abaixo de zero levanta `InsufficientSparksError`."""

    def __init__(self, saldo: int):
        self.saldo = saldo
        self.debitos: list[int] = []

    def deduct(self, uid: str, quantia: int) -> int:
        if self.saldo < quantia:
            raise fs.InsufficientSparksError(balance=self.saldo, needed=quantia)
        self.saldo -= quantia
        self.debitos.append(quantia)
        return self.saldo


@pytest.fixture(autouse=True)
def _sem_limites_residuais():
    rate_limit.limpar()
    yield
    rate_limit.limpar()


@pytest.fixture
def carteira(monkeypatch):
    c = _Carteira(saldo=1000)
    monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: True)
    monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: c.saldo)
    monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: c.saldo)
    monkeypatch.setattr(fs, "deduct_sparks", c.deduct)
    return c


@pytest.fixture
def db(fake_db):
    routes.set_db(fake_db)
    return fake_db


# ============================================================ o catálogo


class TestCatalogo:
    def test_os_quatro_cursos_existem_e_estao_todos_em_breve(self, db, carteira):
        dados = _run(routes.listar(user=_user()))
        ids = [c["curso_id"] for c in dados["cursos"]]
        assert ids == [
            "matematica-basica",
            "redacao-0-1000",
            "hackeando-a-tri",
            "compreensao-interpretacao-texto",
        ]
        assert all(c["status"] == cursos.EM_BREVE for c in dados["cursos"])

    def test_todo_curso_tem_o_mesmo_preco_de_tabela(self, db, carteira):
        dados = _run(routes.listar(user=_user()))
        assert {c["custo_sparks"] for c in dados["cursos"]} == {cursos.CURSO_CUSTO_SPARKS}
        assert cursos.CURSO_CUSTO_SPARKS == 500

    def test_marcar_interesse_nao_custa_sparks(self, db, carteira):
        _run(routes.marcar_interesse("redacao-0-1000", user=_user()))
        assert carteira.debitos == []
        assert carteira.saldo == 1000

    def test_interesse_repetido_nao_duplica_a_inscricao(self, db, carteira):
        for _ in range(3):
            _run(routes.marcar_interesse("redacao-0-1000", user=_user()))
        assert _run(db.cursos_interesse.count_documents({})) == 1

    def test_interesse_volta_marcado_na_listagem(self, db, carteira):
        _run(routes.marcar_interesse("hackeando-a-tri", user=_user()))
        dados = _run(routes.listar(user=_user()))
        por_id = {c["curso_id"]: c for c in dados["cursos"]}
        assert por_id["hackeando-a-tri"]["tenho_interesse"] is True
        assert por_id["matematica-basica"]["tenho_interesse"] is False

    def test_desmarcar_interesse(self, db, carteira):
        _run(routes.marcar_interesse("matematica-basica", user=_user()))
        _run(routes.desmarcar_interesse("matematica-basica", user=_user()))
        assert _run(db.cursos_interesse.count_documents({})) == 0

    def test_curso_inventado_e_404(self, db, carteira):
        with pytest.raises(HTTPException) as exc:
            _run(routes.marcar_interesse("curso-que-nao-existe", user=_user()))
        assert exc.value.status_code == 404


class TestCompraDeCurso:
    """Pré-venda: cobra uma vez e o acesso é vitalício."""

    def test_primeira_compra_debita_500(self, db, carteira):
        resposta = _run(routes.comprar_curso("redacao-0-1000", user=_user(), _=None))
        assert resposta["cobrado"] is True
        assert resposta["vitalicio"] is True
        assert carteira.debitos == [500]

    def test_o_curso_comprado_ainda_nao_esta_disponivel_e_a_resposta_diz_isso(self, db, carteira):
        """O aluno comprou o acesso, não a aula de hoje. Prometer `disponivel`
        num curso "em breve" seria vender uma entrega que não existe."""
        resposta = _run(routes.comprar_curso("redacao-0-1000", user=_user(), _=None))
        assert resposta["tenho_acesso"] is True
        assert resposta["disponivel"] is False
        assert resposta["status"] == cursos.EM_BREVE

    def test_comprar_o_mesmo_curso_de_novo_nunca_cobra_segunda_vez(self, db, carteira):
        _run(routes.comprar_curso("redacao-0-1000", user=_user(), _=None))
        segunda = _run(routes.comprar_curso("redacao-0-1000", user=_user(), _=None))
        assert segunda["cobrado"] is False
        assert segunda["tenho_acesso"] is True
        assert carteira.debitos == [500]
        assert _run(db.cursos_acessos.count_documents({})) == 1

    def test_cursos_diferentes_sao_compras_diferentes(self, db, carteira):
        _run(routes.comprar_curso("redacao-0-1000", user=_user(), _=None))
        _run(routes.comprar_curso("hackeando-a-tri", user=_user(), _=None))
        assert carteira.debitos == [500, 500]

    def test_saldo_insuficiente_e_402_e_nao_deixa_acesso(self, db, carteira):
        carteira.saldo = 100
        with pytest.raises(HTTPException) as exc:
            _run(routes.comprar_curso("redacao-0-1000", user=_user(), _=None))
        assert exc.value.status_code == 402
        assert _run(db.cursos_acessos.count_documents({})) == 0

    def test_curso_inventado_e_404_antes_de_qualquer_cobranca(self, db, carteira):
        with pytest.raises(HTTPException) as exc:
            _run(routes.comprar_curso("curso-fantasma", user=_user(), _=None))
        assert exc.value.status_code == 404
        assert carteira.debitos == []

    def test_a_listagem_mostra_o_que_ja_e_meu(self, db, carteira):
        _run(routes.comprar_curso("matematica-basica", user=_user(), _=None))
        dados = _run(routes.listar(user=_user()))
        por_id = {c["curso_id"]: c for c in dados["cursos"]}
        assert por_id["matematica-basica"]["tenho_acesso"] is True
        assert por_id["redacao-0-1000"]["tenho_acesso"] is False

    def test_o_acesso_e_por_aluno(self, db, carteira):
        _run(routes.comprar_curso("matematica-basica", user=_user("a"), _=None))
        dados = _run(routes.listar(user=_user("b")))
        por_id = {c["curso_id"]: c for c in dados["cursos"]}
        assert por_id["matematica-basica"]["tenho_acesso"] is False


# ============================================================ a agenda da live


class TestQuandoEAProximaQuinta:
    def _live(self, quando: datetime) -> dict:
        return cursos.proxima_live(quando.replace(tzinfo=ZONA_BRASIL))

    def test_segunda_feira_aponta_para_a_quinta_da_mesma_semana(self):
        live = self._live(datetime(2026, 9, 14, 9, 0))  # segunda
        assert live["edicao"] == "2026-09-17"
        assert live["ao_vivo_agora"] is False

    def test_durante_a_aula_a_edicao_continua_sendo_a_de_hoje(self):
        """Quem paga às 20h30 de quinta está comprando a aula que está
        acontecendo — não a da semana que vem."""
        live = self._live(datetime(2026, 9, 17, 20, 30))
        assert live["edicao"] == "2026-09-17"
        assert live["ao_vivo_agora"] is True

    def test_meia_hora_antes_a_sala_ja_conta_como_ao_vivo(self):
        live = self._live(datetime(2026, 9, 17, 19, 35))
        assert live["edicao"] == "2026-09-17"
        assert live["ao_vivo_agora"] is True

    def test_depois_do_fim_a_venda_passa_para_a_quinta_seguinte(self):
        live = self._live(datetime(2026, 9, 17, 22, 5))
        assert live["edicao"] == "2026-09-24"
        assert live["ao_vivo_agora"] is False

    def test_a_edicao_e_sempre_uma_quinta_feira(self):
        for dia in range(14, 28):
            live = self._live(datetime(2026, 9, dia, 12, 0))
            assert datetime.fromisoformat(live["inicio"]).weekday() == 3


# ============================================================ a compra


class TestAcessoALive:
    def test_primeira_compra_debita_o_preco_de_tabela(self, db, carteira):
        resposta = _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        assert resposta["cobrado"] is True
        assert carteira.debitos == [cursos.LIVE_CUSTO_SPARKS]
        assert carteira.saldo == 1000 - cursos.LIVE_CUSTO_SPARKS
        assert resposta["custo_sparks"] == 200

    def test_segunda_chamada_na_mesma_semana_nao_cobra_de_novo(self, db, carteira):
        _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        segunda = _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        assert segunda["cobrado"] is False
        assert carteira.debitos == [cursos.LIVE_CUSTO_SPARKS]
        assert _run(db.cursos_live_acessos.count_documents({})) == 1

    def test_saldo_insuficiente_e_402_e_nao_deixa_vaga_reservada(self, db, carteira):
        carteira.saldo = 10
        with pytest.raises(HTTPException) as exc:
            _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        assert exc.value.status_code == 402
        # A reivindicação foi desfeita: sem isto o aluno ficaria com a chave da
        # semana queimada e não conseguiria comprar nem depois de recarregar.
        assert _run(db.cursos_live_acessos.count_documents({})) == 0

    def test_falha_no_firestore_devolve_503_sem_cobrar_nem_reservar(self, db, carteira, monkeypatch):
        def _explode(*_a, **_k):
            raise RuntimeError("Firestore fora do ar")

        monkeypatch.setattr(fs, "deduct_sparks", _explode)
        with pytest.raises(HTTPException) as exc:
            _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        assert exc.value.status_code == 503
        assert _run(db.cursos_live_acessos.count_documents({})) == 0

    def test_alunos_diferentes_compram_a_mesma_edicao(self, db, carteira):
        _run(routes.comprar_acesso_live(user=_user("a"), whatsapp=None, _=None))
        _run(routes.comprar_acesso_live(user=_user("b"), whatsapp=None, _=None))
        assert _run(db.cursos_live_acessos.count_documents({})) == 2
        assert carteira.debitos == [200, 200]

    def test_o_link_so_aparece_para_quem_pagou(self, db, carteira):
        edicao = cursos.proxima_live()["edicao"]
        _run(routes.publicar_live(
            routes.PublicarLiveRequest(link="https://meet.google.com/abc-defg-hij"),
            admin=_admin(),
        ))

        antes = _run(routes.listar(user=_user()))
        assert antes["live"]["link"] is None
        assert antes["live"]["link_publicado"] is True  # existe, mas não é seu

        _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        depois = _run(routes.listar(user=_user()))
        assert depois["live"]["link"] == "https://meet.google.com/abc-defg-hij"
        assert depois["live"]["edicao"] == edicao

    def test_compra_antes_do_link_existir_garante_a_vaga(self, db, carteira):
        """A venda abre antes de a sala ser criada — o que o aluno compra é a
        vaga. A resposta precisa dizer que o link ainda não saiu."""
        resposta = _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        assert resposta["cobrado"] is True
        assert resposta["link"] is None
        assert resposta["link_publicado"] is False

    def test_whatsapp_informado_na_compra_fica_gravado_na_conta(self, db, carteira):
        _run(db.users.insert_one({"user_id": "aluno-1", "email": "a@x.com", "name": "A"}))
        _run(routes.comprar_acesso_live(user=_user(), whatsapp="(11) 91234-5678", _=None))
        conta = _run(db.users.find_one({"user_id": "aluno-1"}))
        assert conta["whatsapp_e164"] == "5511912345678"

    def test_whatsapp_invalido_na_compra_e_422_e_nao_cobra(self, db, carteira):
        with pytest.raises(HTTPException) as exc:
            _run(routes.comprar_acesso_live(user=_user(), whatsapp="123", _=None))
        assert exc.value.status_code == 422
        assert carteira.debitos == []


# ============================================================ o painel do admin


class TestPainelDoAdmin:
    def test_link_precisa_ser_do_google_meet(self, db, carteira):
        with pytest.raises(HTTPException) as exc:
            _run(routes.publicar_live(
                routes.PublicarLiveRequest(link="https://exemplo.com/sala"), admin=_admin(),
            ))
        assert exc.value.status_code == 422

    def test_publicar_o_tema_nao_apaga_o_link(self, db, carteira):
        _run(routes.publicar_live(
            routes.PublicarLiveRequest(link="https://meet.google.com/abc-defg-hij"), admin=_admin(),
        ))
        _run(routes.publicar_live(routes.PublicarLiveRequest(tema="Funções"), admin=_admin()))
        painel = _run(routes.painel(admin=_admin()))
        assert painel["live"]["link"] == "https://meet.google.com/abc-defg-hij"
        assert painel["live"]["tema"] == "Funções"

    def test_inscritos_vem_com_o_whatsapp_pronto_para_conversar(self, db, carteira):
        _run(db.users.insert_one({
            "user_id": "aluno-1", "name": "Maria", "email": "maria@x.com",
            "whatsapp": "(11) 91234-5678", "whatsapp_e164": "5511912345678",
        }))
        _run(routes.comprar_acesso_live(user=_user("aluno-1"), whatsapp=None, _=None))

        painel = _run(routes.painel(admin=_admin()))
        assert painel["inscritos_count"] == 1
        inscrito = painel["inscritos"][0]
        assert inscrito["nome"] == "Maria"
        assert inscrito["whatsapp"] == "(11) 91234-5678"
        assert inscrito["whatsapp_link"] == "https://wa.me/5511912345678"
        assert painel["receita_sparks"] == 200

    def test_aluno_sem_numero_aparece_sem_link_em_vez_de_sumir(self, db, carteira):
        """Quem se inscreveu e não tem WhatsApp continua na lista — é
        justamente a pessoa que a equipe precisa alcançar por outro caminho."""
        _run(db.users.insert_one({"user_id": "aluno-1", "name": "Sem Zap", "email": "s@x.com"}))
        _run(routes.comprar_acesso_live(user=_user("aluno-1"), whatsapp=None, _=None))
        painel = _run(routes.painel(admin=_admin()))
        assert painel["inscritos"][0]["nome"] == "Sem Zap"
        assert painel["inscritos"][0]["whatsapp_link"] is None

    def test_o_painel_conta_quem_ja_pagou_por_curso_que_nao_existe(self, db, carteira):
        """O número que importa nesta tela: quantas pessoas a equipe deve."""
        _run(db.users.insert_one({
            "user_id": "aluno-1", "name": "Maria", "email": "maria@x.com",
            "whatsapp_e164": "5511912345678",
        }))
        _run(routes.comprar_curso("redacao-0-1000", user=_user("aluno-1"), _=None))
        _run(routes.comprar_curso("redacao-0-1000", user=_user("aluno-2"), _=None))

        painel = _run(routes.painel(admin=_admin()))
        por_id = {c["curso_id"]: c for c in painel["cursos"]}
        assert por_id["redacao-0-1000"]["compradores"] == 2
        assert por_id["redacao-0-1000"]["sparks_arrecadados"] == 1000
        assert por_id["matematica-basica"]["compradores"] == 0
        nomes = {c["nome"] for c in painel["compradores_por_curso"]["redacao-0-1000"]}
        assert "Maria" in nomes

    def test_interesse_por_curso_e_contado_e_nominal(self, db, carteira):
        _run(db.users.insert_one({
            "user_id": "aluno-1", "name": "Maria", "email": "maria@x.com",
            "whatsapp_e164": "5511912345678",
        }))
        _run(routes.marcar_interesse("redacao-0-1000", user=_user("aluno-1")))
        _run(routes.marcar_interesse("redacao-0-1000", user=_user("aluno-2")))

        painel = _run(routes.painel(admin=_admin()))
        por_id = {c["curso_id"]: c for c in painel["cursos"]}
        assert por_id["redacao-0-1000"]["interessados"] == 2
        assert por_id["matematica-basica"]["interessados"] == 0
        nomes = {i["nome"] for i in painel["interessados_por_curso"]["redacao-0-1000"]}
        assert "Maria" in nomes
