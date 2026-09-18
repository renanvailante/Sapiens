"""A fila de espera da mentoria — chamadas diretas às funções da rota (sem
servidor HTTP nem TestClient, mesmo estilo offline do resto do repo).

Era o teste de "aulas particulares". O que mudou em 2026-09-15 não é o nome:
uma LISTA DE ESPERA tem duas obrigações que um formulário de pedido não tinha,
e são elas que os testes novos protegem —

1. **um aluno ocupa um lugar só** (mandar de novo corrige o pedido, não cria
   um segundo e não empurra ninguém para trás);
2. **a posição é informação honesta** — quem saiu da fila não conta, senão o
   número que o aluno vê só cresceria.

Em 2026-09-17 entrar passou a custar `ENTRADA_COST` Sparks, e isso acrescenta
uma terceira obrigação, que é de dinheiro:

3. **cobra-se UMA vez, na entrada.** Corrigir o próprio pedido é de graça para
   sempre — cobrar por uma correção faria o aluno preferir deixar o telefone
   errado, que é exatamente o dado pelo qual a fila existe. E entrar sem saldo
   não pode deixar meio pedido gravado.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402
import mentoria_routes as routes  # noqa: E402
from models import CreateMentoriaEsperaRequest, UpdateMentoriaStatusRequest, User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class _Carteira:
    """Saldo de Sparks em memória. Mesmo dublê de `test_cursos`: o Firestore
    real nunca é tocado, e o teste consegue afirmar QUANTO foi debitado."""

    def __init__(self, saldo=1000):
        self.saldo = saldo
        self.debitos = []
        self.reembolsos = []

    def deduct(self, uid: str, quantia: int) -> int:
        if self.saldo < quantia:
            raise fs.InsufficientSparksError(balance=self.saldo, needed=quantia)
        self.saldo -= quantia
        self.debitos.append(quantia)
        return self.saldo

    def refund(self, uid: str, quantia: int) -> int:
        self.saldo += quantia
        self.reembolsos.append(quantia)
        return self.saldo


@pytest.fixture(autouse=True)
def carteira(monkeypatch):
    """Toda entrada na fila cobra — então toda função deste arquivo precisa de
    uma carteira. `autouse` para que um teste novo não passe por acidente
    tocando o Firestore de verdade."""
    c = _Carteira()
    monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: c.saldo)
    monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: c.saldo)
    monkeypatch.setattr(fs, "deduct_sparks", c.deduct)
    monkeypatch.setattr(fs, "refund_sparks", c.refund)
    return c


def _user(uid="user-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno", whatsapp="11987654321")


def _admin() -> User:
    return User(user_id="admin-1", email="admin@exemplo.com", name="Admin", is_admin=True)


def _payload(**kwargs):
    base = dict(
        nome_completo="Maria Silva",
        whatsapp="11987654321",
        areas=["Matemática", "Redação"],
        descricao="Quero destravar funções e a redação para o ENEM.",
    )
    base.update(kwargs)
    return CreateMentoriaEsperaRequest(**base)


def test_entrar_na_fila(fake_db, carteira):
    routes.set_db(fake_db)
    resposta = _run(routes.entrar_na_fila(_payload(), user=_user()))
    assert resposta["user_id"] == "user-1"
    assert resposta["status"] == "pendente"
    assert resposta["areas"] == ["Matemática", "Redação"]
    assert resposta["ja_estava_na_fila"] is False
    assert resposta["posicao"] == 1
    # O e-mail da CONTA viaja com o pedido: é o que o painel do admin lê.
    assert resposta["email"] == "user-1@exemplo.com"
    assert carteira.debitos == [routes.ENTRADA_COST]
    assert resposta["cobrado"] == routes.ENTRADA_COST
    assert resposta["sparks_cobrados"] == routes.ENTRADA_COST


def test_corrigir_o_pedido_nao_cobra_de_novo(fake_db, carteira):
    """A regra de dinheiro da fila: cobra-se na ENTRADA, e só nela.

    Se corrigir custasse, o aluno que digitou o número errado escolheria
    deixá-lo errado — e o dado pelo qual a fila existe é justamente o contato.
    """
    routes.set_db(fake_db)
    _run(routes.entrar_na_fila(_payload(), user=_user()))
    segunda = _run(routes.entrar_na_fila(_payload(descricao="mudei de ideia"), user=_user()))
    assert segunda["ja_estava_na_fila"] is True
    assert segunda["cobrado"] == 0
    assert carteira.debitos == [routes.ENTRADA_COST]  # uma só, a da entrada


def test_sem_saldo_nao_entra_e_nao_grava(fake_db, carteira):
    """402 e a fila continua vazia. Um pedido gravado sem cobrança é uma
    pessoa que entrou de graça; uma cobrança sem pedido é pior ainda."""
    routes.set_db(fake_db)
    carteira.saldo = routes.ENTRADA_COST - 1
    with pytest.raises(HTTPException) as exc:
        _run(routes.entrar_na_fila(_payload(), user=_user()))
    assert exc.value.status_code == 402
    assert _run(fake_db.aulas_particulares.count_documents({})) == 0


def test_dados_incompletos_nao_chegam_a_cobrar(fake_db, carteira):
    """Nome e WhatsApp são checados ANTES do débito: o aluno nunca paga por
    uma entrada que o servidor já sabe que vai recusar."""
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.entrar_na_fila(_payload(nome_completo="   "), user=_user()))
    assert exc.value.status_code == 422
    assert carteira.debitos == []


def test_whatsapp_impossivel_e_recusado_antes_do_debito(fake_db, carteira):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.entrar_na_fila(_payload(whatsapp="12345678"), user=_user()))
    assert exc.value.status_code == 422
    assert carteira.debitos == []


def test_a_posicao_segue_a_ordem_de_chegada(fake_db):
    routes.set_db(fake_db)
    primeiro = _run(routes.entrar_na_fila(_payload(), user=_user("a")))
    segundo = _run(routes.entrar_na_fila(_payload(), user=_user("b")))
    assert primeiro["posicao"] == 1
    assert segundo["posicao"] == 2


def test_mandar_de_novo_corrige_o_pedido_sem_ocupar_dois_lugares(fake_db, carteira):
    """O aluno que percebe que digitou o WhatsApp errado reenvia. Se isso
    criasse um segundo pedido, a lista do admin mostraria a mesma pessoa duas
    vezes e ela apareceria duas vezes na contagem da fila."""
    routes.set_db(fake_db)
    _run(routes.entrar_na_fila(_payload(), user=_user()))
    segunda = _run(routes.entrar_na_fila(_payload(whatsapp="11999998888"), user=_user()))

    assert segunda["ja_estava_na_fila"] is True
    assert segunda["whatsapp"] == "11999998888"
    assert _run(fake_db.aulas_particulares.count_documents({})) == 1
    assert carteira.debitos == [routes.ENTRADA_COST]


def test_reenviar_nao_faz_o_aluno_perder_o_lugar(fake_db):
    """Corrigir o próprio pedido não pode mandar a pessoa para o fim da fila."""
    routes.set_db(fake_db)
    _run(routes.entrar_na_fila(_payload(), user=_user("a")))
    _run(routes.entrar_na_fila(_payload(), user=_user("b")))
    corrigido = _run(routes.entrar_na_fila(_payload(descricao="outra coisa"), user=_user("a")))
    assert corrigido["posicao"] == 1


def test_quem_saiu_da_fila_nao_conta_na_posicao(fake_db):
    routes.set_db(fake_db)
    primeiro = _run(routes.entrar_na_fila(_payload(), user=_user("a")))
    _run(routes.entrar_na_fila(_payload(), user=_user("b")))
    _run(routes.atualizar_status(
        primeiro["request_id"], UpdateMentoriaStatusRequest(status="cancelada"), admin=_admin(),
    ))
    meu = _run(routes.meu_lugar_na_fila(user=_user("b")))
    assert meu["posicao"] == 1


def test_area_invalida_e_rejeitada(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.entrar_na_fila(_payload(areas=["Física"]), user=_user()))
    assert exc.value.status_code == 422


def test_sem_areas_e_rejeitado(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.entrar_na_fila(_payload(areas=[]), user=_user()))
    assert exc.value.status_code == 422


def test_quem_nao_entrou_nao_esta_na_fila(fake_db):
    routes.set_db(fake_db)
    meu = _run(routes.meu_lugar_na_fila(user=_user()))
    assert meu["na_fila"] is False
    # A tela decide com isto se pede dados antes de cobrar — e o preço vem do
    # servidor, nunca de um número escrito no React.
    assert meu["custo_entrada"] == routes.ENTRADA_COST
    assert meu["conta"]["email"] == "user-1@exemplo.com"


def test_admin_ve_a_fila_inteira(fake_db):
    routes.set_db(fake_db)
    _run(routes.entrar_na_fila(_payload(), user=_user("user-1")))
    _run(routes.entrar_na_fila(_payload(), user=_user("user-2")))
    assert len(_run(routes.listar_a_fila(admin=_admin()))) == 2


def test_admin_altera_status(fake_db):
    routes.set_db(fake_db)
    criada = _run(routes.entrar_na_fila(_payload(), user=_user()))
    atualizada = _run(routes.atualizar_status(
        criada["request_id"], UpdateMentoriaStatusRequest(status="em_andamento"), admin=_admin(),
    ))
    assert atualizada["status"] == "em_andamento"
    assert atualizada["updated_at"] >= criada["updated_at"]


def test_status_invalido_e_rejeitado(fake_db):
    routes.set_db(fake_db)
    criada = _run(routes.entrar_na_fila(_payload(), user=_user()))
    with pytest.raises(HTTPException) as exc:
        _run(routes.atualizar_status(
            criada["request_id"], UpdateMentoriaStatusRequest(status="feito"), admin=_admin(),
        ))
    assert exc.value.status_code == 422


def test_atualizar_pedido_inexistente_e_404(fake_db):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.atualizar_status(
            "aula_inexistente", UpdateMentoriaStatusRequest(status="concluida"), admin=_admin(),
        ))
    assert exc.value.status_code == 404
