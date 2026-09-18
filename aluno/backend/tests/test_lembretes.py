"""“Lembrar-me com a Mentis” — a fila declarada pelo aluno.

Chamadas diretas às funções da rota, sem servidor HTTP, no mesmo estilo
offline do resto do repo (ver `test_mentoria.py`).

O que estes testes protegem é a promessa de DINHEIRO da funcionalidade, que é
onde ela pode machucar alguém de verdade:

1. **Cobra-se uma vez por trecho, para sempre.** Marcar o mesmo parágrafo de
   novo — no duplo toque, no F5 ou três semanas depois — é a mesma linha da
   fila e custa zero. Sem isto, o gesto mais natural do celular (tocar duas
   vezes num botão que demora) viraria 20 Sparks.
2. **Nunca fica meio guardado.** Sem saldo: 402 e a fila continua vazia. Um
   lembrete gravado sem cobrança é uma linha de graça; uma cobrança sem
   lembrete é pior ainda.
3. **Ver, remover e concluir não custam.** Cobrar para olhar a própria fila
   faria o aluno não olhar.
4. **A fila de um aluno é dele.** O `_id` carrega o dono, então o id de outra
   pessoa não existe para quem pergunta.
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
import lembretes_routes as routes  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class _Carteira:
    """Saldo em memória — o Firestore real nunca é tocado, e o teste consegue
    afirmar QUANTO foi debitado."""

    def __init__(self, saldo=1000):
        self.saldo = saldo
        self.debitos = []

    def deduct(self, uid: str, quantia: int) -> int:
        if self.saldo < quantia:
            raise fs.InsufficientSparksError(balance=self.saldo, needed=quantia)
        self.saldo -= quantia
        self.debitos.append(quantia)
        return self.saldo


@pytest.fixture(autouse=True)
def carteira(monkeypatch):
    c = _Carteira()
    monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: c.saldo)
    monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: c.saldo)
    monkeypatch.setattr(fs, "deduct_sparks", c.deduct)
    monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: None)
    return c


def _user(uid="user-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno")


def _payload(**kwargs):
    base = dict(
        texto="A entalpia de formação é medida a 25 °C e 1 atm.",
        rota="/cursos/termoquimica/estacao/2",
        titulo="Termoquímica · Estação 2",
        contexto="Estudando a aula de termoquímica.",
    )
    base.update(kwargs)
    return routes.LembretePayload(**base)


# ---------------------------------------------------------------------------
# 1. Guardar
# ---------------------------------------------------------------------------


def test_guardar_cobra_uma_vez_e_entra_na_fila(fake_db, carteira):
    routes.set_db(fake_db)
    r = _run(routes.guardar(_payload(), user=_user(), _=None))

    assert r["ja_estava"] is False
    assert r["cobrado"] == routes.LEMBRETE_COST
    assert carteira.debitos == [routes.LEMBRETE_COST]
    assert r["lembrete"]["status"] == "aberto"
    assert r["lembrete"]["rota"] == "/cursos/termoquimica/estacao/2"
    # A origem viaja junto: sem ela, a fila é uma lista de frases soltas que
    # ninguém consegue situar semanas depois.
    assert r["lembrete"]["titulo"] == "Termoquímica · Estação 2"
    assert r["lembrete"]["contexto"] == "Estudando a aula de termoquímica."


def test_marcar_o_mesmo_trecho_de_novo_nao_cobra(fake_db, carteira):
    """A regra de dinheiro inteira: um trecho, uma cobrança, para sempre."""
    routes.set_db(fake_db)
    primeira = _run(routes.guardar(_payload(), user=_user(), _=None))
    segunda = _run(routes.guardar(_payload(), user=_user(), _=None))

    assert segunda["ja_estava"] is True
    assert segunda["cobrado"] == 0
    assert carteira.debitos == [routes.LEMBRETE_COST]
    assert segunda["lembrete"]["lembrete_id"] == primeira["lembrete"]["lembrete_id"]
    assert _run(fake_db.lembretes_revisao.count_documents({})) == 1


def test_selecao_quase_igual_e_o_mesmo_lembrete(fake_db, carteira):
    """Espaço a mais, quebra de linha e caixa diferente são a MESMA seleção.

    Este é o caso real: o navegador raramente devolve a mesma seleção byte a
    byte duas vezes. Se essas diferenças criassem linhas novas, "cobra uma vez
    por trecho" seria falso exatamente onde importa.
    """
    routes.set_db(fake_db)
    _run(routes.guardar(_payload(), user=_user(), _=None))
    quase = _payload(texto="  A ENTALPIA de formação   é medida\na 25 °C e 1 atm. ")
    r = _run(routes.guardar(quase, user=_user(), _=None))

    assert r["ja_estava"] is True
    assert carteira.debitos == [routes.LEMBRETE_COST]


def test_mesmo_trecho_em_outra_tela_e_outro_lembrete(fake_db, carteira):
    """A origem faz parte da identidade: o mesmo conceito marcado na aula e
    depois na questão são duas lembranças, com contextos diferentes."""
    routes.set_db(fake_db)
    _run(routes.guardar(_payload(), user=_user(), _=None))
    r = _run(routes.guardar(_payload(rota="/exam/123"), user=_user(), _=None))

    assert r["ja_estava"] is False
    assert carteira.debitos == [routes.LEMBRETE_COST, routes.LEMBRETE_COST]
    assert _run(fake_db.lembretes_revisao.count_documents({})) == 2


def test_sem_saldo_nao_grava_nada(fake_db, carteira):
    """402, e a fila continua vazia — a reivindicação é desfeita."""
    routes.set_db(fake_db)
    carteira.saldo = routes.LEMBRETE_COST - 1
    with pytest.raises(HTTPException) as exc:
        _run(routes.guardar(_payload(), user=_user(), _=None))

    assert exc.value.status_code == 402
    assert _run(fake_db.lembretes_revisao.count_documents({})) == 0


def test_selecao_minuscula_nao_chega_a_cobrar(fake_db, carteira):
    """Dois caracteres é toque acidental num parágrafo. O aluno nunca paga por
    uma seleção que o servidor já sabe que não dá para rever."""
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.guardar(_payload(texto="  a "), user=_user(), _=None))

    assert exc.value.status_code == 422
    assert carteira.debitos == []
    assert _run(fake_db.lembretes_revisao.count_documents({})) == 0


def test_texto_enorme_e_cortado_em_vez_de_recusado(fake_db, carteira):
    """Recusar depois de o aluno ter selecionado seria perder o gesto por um
    limite que ele não tinha como conhecer."""
    routes.set_db(fake_db)
    r = _run(routes.guardar(_payload(texto="parágrafo inteiro. " * 500), user=_user(), _=None))

    assert len(r["lembrete"]["texto"]) == routes.MAX_TEXTO
    assert r["cobrado"] == routes.LEMBRETE_COST


def test_fila_cheia_recusa_antes_de_cobrar(fake_db, carteira):
    routes.set_db(fake_db)
    for i in range(routes.TETO_DA_FILA):
        _run(fake_db.lembretes_revisao.insert_one(
            {"_id": f"user-1:{i:032d}", "user_id": "user-1", "status": "aberto"}
        ))
    carteira.debitos.clear()

    with pytest.raises(HTTPException) as exc:
        _run(routes.guardar(_payload(), user=_user(), _=None))

    assert exc.value.status_code == 409
    assert carteira.debitos == []


def test_agendamento_nasce_pronto_e_inerte(fake_db, carteira):
    """A revisão programada ainda não existe — mas o campo em que ela vai
    escrever já nasce com a forma certa, para que o dia em que ela existir não
    seja um dia de migração de coleção."""
    routes.set_db(fake_db)
    r = _run(routes.guardar(_payload(), user=_user(), _=None))
    ag = r["lembrete"]["agendamento"]

    assert ag["estado"] == "aguardando"
    assert ag["degrau"] == 0
    assert ag["revisar_em"] is None
    assert ag["revisoes"] == 0


# ---------------------------------------------------------------------------
# 2. Ler, concluir e remover — de graça
# ---------------------------------------------------------------------------


def test_ler_a_fila_nao_custa(fake_db, carteira):
    routes.set_db(fake_db)
    _run(routes.guardar(_payload(), user=_user(), _=None))
    carteira.debitos.clear()

    fila = _run(routes.meus_lembretes(user=_user()))

    assert len(fila["itens"]) == 1
    assert fila["abertos"] == 1
    assert fila["custo"] == routes.LEMBRETE_COST
    assert carteira.debitos == []


def test_marcar_revisado_tira_da_fila_aberta_sem_apagar(fake_db, carteira):
    routes.set_db(fake_db)
    guardado = _run(routes.guardar(_payload(), user=_user(), _=None))
    lid = guardado["lembrete"]["lembrete_id"]
    carteira.debitos.clear()

    _run(routes.marcar_revisado(lid, user=_user()))

    assert _run(routes.meus_lembretes(user=_user()))["itens"] == []
    com_revisados = _run(routes.meus_lembretes(incluir_revisados=True, user=_user()))
    assert len(com_revisados["itens"]) == 1
    assert com_revisados["itens"][0]["status"] == "revisado"
    assert com_revisados["itens"][0]["agendamento"]["revisoes"] == 1
    assert carteira.debitos == []


def test_remover_tira_da_fila_e_permite_guardar_de_novo(fake_db, carteira):
    """Remover não devolve Sparks (ver o docstring da rota) — e guardar de
    novo depois de remover é uma compra nova, não um retry."""
    routes.set_db(fake_db)
    guardado = _run(routes.guardar(_payload(), user=_user(), _=None))
    _run(routes.remover(guardado["lembrete"]["lembrete_id"], user=_user()))
    assert _run(fake_db.lembretes_revisao.count_documents({})) == 0

    de_novo = _run(routes.guardar(_payload(), user=_user(), _=None))
    assert de_novo["cobrado"] == routes.LEMBRETE_COST
    assert carteira.debitos == [routes.LEMBRETE_COST, routes.LEMBRETE_COST]


def test_lembrete_de_outro_aluno_nao_existe_para_mim(fake_db, carteira):
    routes.set_db(fake_db)
    guardado = _run(routes.guardar(_payload(), user=_user("user-1"), _=None))
    lid = guardado["lembrete"]["lembrete_id"]

    with pytest.raises(HTTPException) as exc:
        _run(routes.remover(lid, user=_user("user-2")))
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        _run(routes.marcar_revisado(lid, user=_user("user-2")))
    assert exc.value.status_code == 404

    # E a fila do outro aluno continua intacta.
    assert len(_run(routes.meus_lembretes(user=_user("user-1")))["itens"]) == 1
    assert _run(routes.meus_lembretes(user=_user("user-2")))["itens"] == []


def test_a_fila_e_so_minha(fake_db, carteira):
    routes.set_db(fake_db)
    _run(routes.guardar(_payload(), user=_user("user-1"), _=None))
    _run(routes.guardar(_payload(texto="Outro ponto que não entendi direito."),
                        user=_user("user-2"), _=None))

    minha = _run(routes.meus_lembretes(user=_user("user-1")))
    assert len(minha["itens"]) == 1
    assert minha["itens"][0]["user_id"] == "user-1"


# ---------------------------------------------------------------------------
# 3. A regra da casa: nada aqui chama LLM
# ---------------------------------------------------------------------------


def test_guardar_nao_chama_llm(fake_db, carteira, monkeypatch):
    """O que se compra por 10 Sparks é o LUGAR NA FILA, não geração.

    É esta linha que mantém a regra de `mentis_routes.explicar_trecho` ("o
    texto nunca vem do cliente") intacta: aqui o texto VEM do cliente, e por
    isso não pode virar prompt. Um `ai_service` chamado neste caminho seria um
    chat genérico disfarçado de botão de 10 Sparks.
    """
    import ai_service

    def _proibido(*a, **k):
        raise AssertionError("guardar um lembrete não pode chamar o modelo")

    monkeypatch.setattr(ai_service, "generate_json_resiliente", _proibido)
    routes.set_db(fake_db)
    r = _run(routes.guardar(_payload(), user=_user(), _=None))
    assert r["cobrado"] == routes.LEMBRETE_COST
