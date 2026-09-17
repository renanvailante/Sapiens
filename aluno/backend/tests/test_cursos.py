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
5. **O que o pacote de Sparks já inclui não é cobrado de novo — e o que ele
   não inclui continua custando o preço de tabela.** Desde 2026-09-16 só o
   pacote de 4.000 Sparks concede direito: os cursos E as lives. Todo mundo
   mais paga os 200 Sparks de CADA quinta-feira.

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
import sparks_store  # noqa: E402
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
        self.direitos: dict[str, bool] = {d: False for d in sparks_store.DIREITOS}

    def conceder(self, *direitos: str) -> None:
        """Liga um direito de pacote, como faria o webhook do pagamento."""
        for d in direitos:
            assert d in self.direitos, d  # direito fora da lista fechada
            self.direitos[d] = True

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
    # Aluno sem direito nenhum é o padrão de todo teste deste arquivo: quem
    # não comprou pacote paga o preço de tabela. `direitos` liga o que o
    # teste quiser sem tocar no resto.
    monkeypatch.setattr(fs, "ler_saldo_e_direitos", lambda uid: (c.saldo, dict(c.direitos)))
    monkeypatch.setattr(fs, "ler_direitos", lambda uid: dict(c.direitos))
    monkeypatch.setattr(fs, "tem_lives_inclusas", lambda uid: c.direitos["lives_inclusas"])
    monkeypatch.setattr(fs, "tem_cursos_inclusos", lambda uid: c.direitos["cursos_inclusos"])
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


# ================================= o que cada pacote de Sparks já inclui


class TestDireitosDePacote:
    """Os DOIS direitos deste módulo, os dois do mesmo pacote de 4.000 Sparks
    (R$119,90) desde 2026-09-16:

    * `lives_inclusas` — toda quinta, sem os 200 Sparks da edição;
    * `cursos_inclusos` — os quatro cursos gravados, sem os 500 de cada.

    Eles são concedidos juntos mas são SEPARADOS no backend, e os testes
    abaixo seguram justamente isso: um não pode abrir a porta do outro. O dia
    em que um pacote intermediário vender só um dos dois — como o de 1.500
    vendeu as lives até 2026-09-16 — a separação já está testada.
    """

    # ------------------------------------------------------------- as lives

    def test_com_lives_inclusas_a_pagina_ja_abre_com_a_vaga(self, db, carteira):
        carteira.conceder("lives_inclusas")
        dados = _run(routes.listar(user=_user()))
        assert dados["live"]["tenho_acesso"] is True
        assert dados["live"]["incluso_no_plano"] is True
        assert carteira.debitos == []
        assert carteira.saldo == 1000

    def test_com_lives_inclusas_o_link_da_sala_sai(self, db, carteira):
        """O direito precisa entregar a MESMA coisa que os 200 Sparks
        entregam — senão o pacote vendeu uma vaga sem porta."""
        _run(routes.publicar_live(
            routes.PublicarLiveRequest(link="https://meet.google.com/abc-defg-hij"),
            admin=_admin(),
        ))
        carteira.conceder("lives_inclusas")
        dados = _run(routes.listar(user=_user()))
        assert dados["live"]["link"] == "https://meet.google.com/abc-defg-hij"

    def test_clicar_em_garantir_vaga_nao_cobra_de_quem_ja_tem_o_direito(self, db, carteira):
        carteira.conceder("lives_inclusas")
        resposta = _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        assert resposta["cobrado"] is False
        assert resposta["incluso_no_plano"] is True
        assert carteira.debitos == []

    def test_abrir_a_pagina_varias_vezes_inscreve_uma_vez_so(self, db, carteira):
        carteira.conceder("lives_inclusas")
        _run(routes.listar(user=_user()))
        _run(routes.listar(user=_user()))
        _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        assert _run(db.cursos_live_acessos.count_documents({})) == 1

    def test_o_inscrito_pelo_pacote_aparece_para_o_admin_valendo_zero(self, db, carteira):
        """Ele PRECISA estar na lista: é dela que sai o link no WhatsApp da
        quinta. E precisa valer zero: não foi uma venda desta edição."""
        _run(db.users.insert_one({
            "user_id": "aluno-1", "name": "Maria", "email": "maria@x.com",
            "whatsapp_e164": "5511912345678",
        }))
        carteira.conceder("lives_inclusas")
        _run(routes.listar(user=_user("aluno-1")))

        painel = _run(routes.painel(admin=_admin()))
        assert painel["inscritos_count"] == 1
        assert painel["inscritos_inclusos"] == 1
        assert painel["receita_sparks"] == 0
        inscrito = painel["inscritos"][0]
        assert inscrito["por_direito"] is True
        assert inscrito["whatsapp_link"] == "https://wa.me/5511912345678"

    def test_quem_pagou_antes_de_ter_o_direito_continua_contando_como_venda(self, db, carteira):
        """O direito não pode reescrever a inscrição paga: a receita da
        edição sumiria do painel de quem já tinha vendido a vaga."""
        _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        carteira.conceder("lives_inclusas")
        _run(routes.listar(user=_user()))

        painel = _run(routes.painel(admin=_admin()))
        assert painel["receita_sparks"] == 200
        assert painel["inscritos_inclusos"] == 0

    # ------------------------------------------------------ os cursos (4.000)

    def test_com_cursos_inclusos_os_quatro_ja_sao_meus(self, db, carteira):
        carteira.conceder("cursos_inclusos")
        dados = _run(routes.listar(user=_user()))
        assert all(c["tenho_acesso"] for c in dados["cursos"])
        assert all(c["incluso_no_plano"] for c in dados["cursos"])
        assert carteira.debitos == []

    def test_comprar_curso_incluso_nao_debita_nem_cria_compra(self, db, carteira):
        """Sem documento de compra: o direito é o registro. Um doc de 0 Spark
        por curso apareceria no painel de pré-venda como comprador, e o número
        que importa lá é quanta gente pôs dinheiro num curso que não existe."""
        carteira.conceder("cursos_inclusos")
        resposta = _run(routes.comprar_curso("hackeando-a-tri", user=_user(), _=None))
        assert resposta["cobrado"] is False
        assert resposta["incluso_no_plano"] is True
        assert resposta["tenho_acesso"] is True
        assert carteira.debitos == []
        assert _run(db.cursos_acessos.count_documents({})) == 0

    def test_curso_inventado_continua_404_mesmo_com_o_direito(self, db, carteira):
        carteira.conceder("cursos_inclusos")
        with pytest.raises(HTTPException) as exc:
            _run(routes.comprar_curso("curso-que-nao-existe", user=_user(), _=None))
        assert exc.value.status_code == 404

    # ------------------------------------------------- um não vira o outro

    def test_o_direito_das_lives_nao_libera_os_cursos(self, db, carteira):
        """"Apenas as aulas ao vivo": R$54,90 não pode virar a porta dos
        quatro cursos que custam R$119,90."""
        carteira.conceder("lives_inclusas")
        dados = _run(routes.listar(user=_user()))
        assert not any(c["tenho_acesso"] for c in dados["cursos"])

        _run(routes.comprar_curso("redacao-0-1000", user=_user(), _=None))
        assert carteira.debitos == [cursos.CURSO_CUSTO_SPARKS]

    def test_o_pacote_dos_cursos_nao_libera_a_live(self, db, carteira):
        carteira.conceder("cursos_inclusos")
        dados = _run(routes.listar(user=_user()))
        assert dados["live"]["tenho_acesso"] is False
        assert dados["live"]["incluso_no_plano"] is False

        _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        assert carteira.debitos == [cursos.LIVE_CUSTO_SPARKS]

    def test_sem_direito_nenhum_tudo_continua_custando_o_preco_de_tabela(self, db, carteira):
        dados = _run(routes.listar(user=_user()))
        assert dados["live"]["tenho_acesso"] is False
        assert dados["live"]["incluso_no_plano"] is False
        assert not any(c["tenho_acesso"] or c["incluso_no_plano"] for c in dados["cursos"])
        assert _run(db.cursos_live_acessos.count_documents({})) == 0

    def test_mongo_instavel_nao_tira_a_live_de_quem_pagou_o_pacote(self, db, carteira, monkeypatch):
        """A inscrição é registro, não autorização: se ela falhar, o aluno
        perde o lembrete no WhatsApp — nunca a aula."""
        async def _explode(*_a, **_k):
            raise RuntimeError("Mongo instável")

        _run(routes.publicar_live(
            routes.PublicarLiveRequest(link="https://meet.google.com/abc-defg-hij"),
            admin=_admin(),
        ))
        carteira.conceder("lives_inclusas")
        monkeypatch.setattr(db.cursos_live_acessos, "insert_one", _explode)

        dados = _run(routes.listar(user=_user()))
        assert dados["live"]["tenho_acesso"] is True
        assert dados["live"]["link"] == "https://meet.google.com/abc-defg-hij"


# ======================================= a aula ao vivo como ferramenta própria


class TestATelaDaAulaAoVivo:
    """`GET /cursos/live` — a tela que a aula ganhou em 2026-09-16.

    Ela existe para a aula não depender de uma página de catálogo para ser
    comprada. O que os testes seguram é que a tela nova responde EXATAMENTE o
    mesmo que a aba de Cursos respondia sobre a live: mesmo preço, mesma
    edição, mesma regra de link. Duas telas que divergissem sobre "já paguei?"
    seriam duas verdades sobre a mesma quinta-feira.
    """

    def test_devolve_a_mesma_live_que_a_aba_de_cursos(self, db, carteira):
        so_a_live = _run(routes.ver_live(user=_user()))
        pagina_inteira = _run(routes.listar(user=_user()))
        assert so_a_live["live"] == pagina_inteira["live"]
        # E NÃO traz o catálogo junto: é o motivo de o endereço existir.
        assert "cursos" not in so_a_live

    def test_a_aula_dura_60_minutos(self):
        """Mudou de 90 para 60 em 2026-09-16. O número está em `cursos.py` e
        em `frontend/src/lib/live.js`, e os dois têm de contar a mesma hora de
        fim — é ela que decide quando a edição vira a da semana seguinte."""
        live = cursos.proxima_live()
        assert live["duracao_minutos"] == 60
        inicio = datetime.fromisoformat(live["inicio"])
        fim = datetime.fromisoformat(live["fim"])
        assert (fim - inicio).total_seconds() == 60 * 60

    def test_o_link_so_sai_para_quem_pagou(self, db, carteira):
        _run(routes.publicar_live(
            routes.PublicarLiveRequest(link="https://meet.google.com/abc-defg-hij"),
            admin=_admin(),
        ))
        antes = _run(routes.ver_live(user=_user()))
        assert antes["live"]["link"] is None
        assert antes["live"]["link_publicado"] is True

        _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        depois = _run(routes.ver_live(user=_user()))
        assert depois["live"]["link"] == "https://meet.google.com/abc-defg-hij"


class TestCadaQuintaECobradaDeNovo:
    """**A regra de produto de 2026-09-16.** A aula custa 200 Sparks POR
    EDIÇÃO: quem pagou a desta quinta não pagou a da semana que vem. A única
    exceção é o pacote de 4.000 Sparks (`lives_inclusas`).

    O defeito que estes testes impedem é o mais caro possível dos dois lados:
    cobrar de quem comprou o pacote, ou deixar de cobrar de quem não comprou
    porque "já pagou uma vez".
    """

    def _paga_a_edicao(self, db, quando: datetime, uid="aluno-1"):
        """Compra a aula com o relógio parado numa data — é `proxima_live`
        que traduz o instante em edição."""
        real = cursos.proxima_live
        cursos.proxima_live = lambda agora=None: real(quando.replace(tzinfo=ZONA_BRASIL))
        try:
            return _run(routes.comprar_acesso_live(user=_user(uid), whatsapp=None, _=None))
        finally:
            cursos.proxima_live = real

    def test_a_quinta_seguinte_cobra_os_200_de_novo(self, db, carteira):
        primeira = self._paga_a_edicao(db, datetime(2026, 9, 15, 10, 0))   # terça
        segunda = self._paga_a_edicao(db, datetime(2026, 9, 22, 10, 0))    # terça seguinte

        assert primeira["edicao"] == "2026-09-17"
        assert segunda["edicao"] == "2026-09-24"
        assert primeira["cobrado"] is True and segunda["cobrado"] is True
        assert carteira.debitos == [200, 200]
        assert _run(db.cursos_live_acessos.count_documents({})) == 2

    def test_na_mesma_semana_o_segundo_clique_nao_cobra(self, db, carteira):
        self._paga_a_edicao(db, datetime(2026, 9, 15, 10, 0))
        de_novo = self._paga_a_edicao(db, datetime(2026, 9, 16, 22, 0))
        assert de_novo["cobrado"] is False
        assert carteira.debitos == [200]

    def test_o_pacote_de_4000_nao_paga_em_nenhuma_quinta(self, db, carteira):
        """`lives_inclusas` é o direito, e desde 2026-09-16 só o pacote de
        4.000 Sparks o vende — por isso o teste concede o direito como o
        webhook do pagamento concederia, e não por `package_id`."""
        assert sparks_store.get_package("spark_4000").direitos.count("lives_inclusas") == 1
        carteira.conceder("lives_inclusas")

        for quando in (datetime(2026, 9, 15, 10, 0), datetime(2026, 9, 22, 10, 0)):
            r = self._paga_a_edicao(db, quando)
            assert r["cobrado"] is False
            assert r["incluso_no_plano"] is True
        assert carteira.debitos == []
        # As duas edições continuam na lista da equipe, com 0 Spark: é dela
        # que sai quem recebe o link no WhatsApp.
        inscritos = _run(db.cursos_live_acessos.find({}, {"_id": 0}).to_list(10))
        assert {i["edicao"] for i in inscritos} == {"2026-09-17", "2026-09-24"}
        assert all(i["custo_sparks"] == 0 and i["por_direito"] for i in inscritos)

    def test_o_pacote_de_1500_voltou_a_pagar_os_200(self, db, carteira):
        """R$54,90 deixou de incluir as lives. Quem comprar esse pacote a
        partir de 2026-09-16 não recebe `lives_inclusas` — e sem o direito, a
        carteira é cobrada como a de qualquer aluno."""
        assert sparks_store.get_package("spark_1500").direitos == ()
        r = self._paga_a_edicao(db, datetime(2026, 9, 15, 10, 0))
        assert r["cobrado"] is True
        assert carteira.debitos == [200]


class TestOAdminPublicaOLinkDaSemana:
    def test_o_cartao_do_admin_ve_a_edicao_e_quem_esta_esperando(self, db, carteira):
        """`GET /admin/cursos/live` é o que o campo do link lê — na primeira
        tela do admin e dentro do painel de cursos. Ele precisa dizer se há
        gente paga esperando um link que ainda não existe; é esse número que
        vira o aviso vermelho."""
        antes = _run(routes.estado_da_live(admin=_admin()))
        assert antes["link_publicado"] is False
        assert antes["inscritos_count"] == 0
        assert antes["duracao_minutos"] == 60

        _run(routes.comprar_acesso_live(user=_user(), whatsapp=None, _=None))
        esperando = _run(routes.estado_da_live(admin=_admin()))
        assert esperando["link_publicado"] is False
        assert esperando["inscritos_count"] == 1

        _run(routes.publicar_live(
            routes.PublicarLiveRequest(link="https://meet.google.com/abc-defg-hij", tema="Funções"),
            admin=_admin(),
        ))
        depois = _run(routes.estado_da_live(admin=_admin()))
        assert depois["link"] == "https://meet.google.com/abc-defg-hij"
        assert depois["tema"] == "Funções"
        assert depois["publicado_por"] == "admin@exemplo.com"

    def test_o_link_da_semana_passada_nao_vale_para_a_edicao_de_agora(self, db, carteira):
        """Um documento por edição, e não um "link atual" sobrescrito: quem
        pagou a desta quinta não pode receber a sala da quinta passada."""
        _run(routes.publicar_live(
            routes.PublicarLiveRequest(link="https://meet.google.com/velha-velha-vel", edicao="2026-09-10"),
            admin=_admin(),
        ))
        agora = _run(routes.estado_da_live(admin=_admin()))
        assert agora["edicao"] != "2026-09-10"
        assert agora["link"] is None

    def test_so_aceita_sala_do_google_meet(self, db, carteira):
        with pytest.raises(HTTPException) as exc:
            _run(routes.publicar_live(
                routes.PublicarLiveRequest(link="https://zoom.us/j/123"), admin=_admin(),
            ))
        assert exc.value.status_code == 422
