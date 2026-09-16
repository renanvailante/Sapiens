"""A sala VIP do mural — o segundo direito do pacote de R$119,90.

Duas coisas podem dar errado aqui, e as duas são graves de formas diferentes:

1. **Vazar a sala fechada.** Quem não comprou não pode ler nem escrever nela,
   e a porta precisa estar em TODOS os caminhos — a listagem, o link direto de
   uma dúvida (que circula no WhatsApp) e a resposta.
2. **Sumir com o mural antigo.** As dúvidas publicadas antes de 2026-09-15 não
   têm o campo `sala`. Se a consulta da geral fosse `sala == "geral"`, o mural
   inteiro desapareceria no dia do deploy, sem erro nenhum na tela.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import comunidade
import comunidade_routes as rotas
import engajamento_service
from models import User


def roda(coro):
    return asyncio.run(coro)


def _user(uid="aluno-1", admin=False) -> User:
    return User(user_id=uid, email=f"{uid}@x.com", name="Aluno", is_admin=admin)


@pytest.fixture
def mural(fake_db, monkeypatch):
    comunidade.set_db(fake_db)
    rotas.comunidade = comunidade
    engajamento_service.set_db(fake_db)
    monkeypatch.setattr(engajamento_service, "_hoje", lambda: "2026-09-15")
    monkeypatch.setattr(comunidade.fs, "dia_local", lambda *a, **k: "2026-09-15")
    monkeypatch.setattr(
        comunidade.fs, "grant_sparks_evento",
        lambda uid, *, categoria, chave, amount, meta=None: {"ja_concedido": False, "sparks_ganhos": amount},
    )
    yield fake_db
    comunidade.set_db(None)
    engajamento_service.set_db(None)


@pytest.fixture
def vips(monkeypatch):
    """Quem tem o direito, nesta rodada de teste."""
    conjunto: set[str] = set()
    monkeypatch.setattr(rotas.fs, "tem_comunidade_vip", lambda uid: uid in conjunto)
    return conjunto


def _publicar(uid="aluno-1", sala=comunidade.SALA_GERAL, titulo="Não entendi essa função"):
    return roda(comunidade.publicar_duvida(
        student_id=uid, autor_nome="Autor", area="Matemática",
        titulo=titulo, corpo="Alguém explica o passo 3?", sala=sala,
    ))


class TestAPortaDaSala:
    def test_quem_nao_comprou_nao_lista_a_vip(self, mural, vips):
        with pytest.raises(HTTPException) as exc:
            roda(rotas.mural(sala=comunidade.SALA_VIP, user=_user()))
        assert exc.value.status_code == 403

    def test_quem_comprou_lista(self, mural, vips):
        vips.add("aluno-1")
        _publicar(sala=comunidade.SALA_VIP, titulo="Dúvida da sala fechada")
        dados = roda(rotas.mural(sala=comunidade.SALA_VIP, user=_user()))
        assert [d["titulo"] for d in dados["items"]] == ["Dúvida da sala fechada"]

    def test_admin_entra_sem_comprar(self, mural, vips):
        """Ele modera a sala; moderar uma sala que não se pode abrir é
        impossível."""
        dados = roda(rotas.mural(sala=comunidade.SALA_VIP, user=_user("admin-1", admin=True)))
        assert dados["sala"] == comunidade.SALA_VIP

    def test_publicar_na_vip_exige_o_direito(self, mural, vips):
        pedido = rotas.DuvidaRequest(
            area="Matemática", titulo="Uma dúvida bem grande", corpo="Corpo suficiente aqui",
            sala=comunidade.SALA_VIP,
        )
        with pytest.raises(HTTPException) as exc:
            roda(rotas.publicar(pedido, user=_user(), _=None))
        assert exc.value.status_code == 403

    def test_o_link_direto_de_uma_duvida_vip_tambem_e_barrado(self, mural, vips):
        """O link circula: alguém cola no WhatsApp. A porta não pode existir
        só na listagem."""
        vips.add("dono")
        duvida = _publicar(uid="dono", sala=comunidade.SALA_VIP)
        with pytest.raises(HTTPException) as exc:
            roda(rotas.uma_duvida(duvida["duvida_id"], user=_user("intruso")))
        assert exc.value.status_code == 403

    def test_responder_numa_duvida_vip_exige_o_direito(self, mural, vips):
        vips.add("dono")
        duvida = _publicar(uid="dono", sala=comunidade.SALA_VIP)
        pedido = rotas.RespostaRequest(corpo="Minha resposta aqui")
        with pytest.raises(HTTPException) as exc:
            roda(rotas.responder(duvida["duvida_id"], pedido, user=_user("intruso"), _=None))
        assert exc.value.status_code == 403

    def test_a_geral_continua_aberta_a_todo_mundo(self, mural, vips):
        _publicar(titulo="Dúvida de todo mundo")
        dados = roda(rotas.mural(user=_user("qualquer-um")))
        assert [d["titulo"] for d in dados["items"]] == ["Dúvida de todo mundo"]


class TestAsDuasSalasNaoSeMisturam:
    def test_duvida_vip_nao_aparece_na_geral(self, mural, vips):
        vips.add("dono")
        _publicar(uid="dono", sala=comunidade.SALA_VIP, titulo="Só para quem pagou")
        _publicar(uid="outro", titulo="Aberta para todos")
        geral = roda(rotas.mural(user=_user("qualquer-um")))
        assert [d["titulo"] for d in geral["items"]] == ["Aberta para todos"]

    def test_duvida_antiga_sem_campo_sala_continua_na_geral(self, mural, vips):
        """A migração que NÃO foi feita: o mural anterior à VIP não tem o
        campo, e a consulta precisa casar com o documento em que ele falta."""
        roda(mural.comunidade_duvidas.insert_one({
            "duvida_id": "antiga", "student_id": "velho", "autor_nome": "Velho",
            "area": "Matemática", "titulo": "Publicada antes da VIP existir",
            "corpo": "x", "status": "publicada", "respostas": 0, "votos": 0,
            "resolvida": False, "melhor_resposta_id": None, "destacada_ate": None,
            "reportada_por": [], "created_at": "2026-09-01T00:00:00+00:00",
            "atualizado_em": "2026-09-01T00:00:00+00:00",
        }))
        geral = roda(rotas.mural(user=_user("qualquer-um")))
        assert "Publicada antes da VIP existir" in [d["titulo"] for d in geral["items"]]

    def test_sala_inventada_cai_na_geral(self, mural, vips):
        """Um cliente que mande `sala: "premium"` não cria uma terceira sala
        invisível — ele publica na geral."""
        duvida = _publicar(sala="premium")
        assert duvida["sala"] == comunidade.SALA_GERAL


class TestOAvisoDeAcesso:
    def test_a_tela_pergunta_antes_de_bater_na_porta(self, mural, vips):
        assert roda(rotas.acesso_vip(user=_user()))["vip"] is False
        vips.add("aluno-1")
        assert roda(rotas.acesso_vip(user=_user()))["vip"] is True
