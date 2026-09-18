"""O feed fim a fim: colar texto vira feed no ar, responder vira comportamento.

O que estes testes protegem, na ordem em que doeria:

1. **Publicar por texto compila, valida e grava** — e republicar o MESMO
   texto atualiza os cards no lugar, sem duplicar nem reordenar o que já
   estava no ar (o id é o hash do conteúdo, ver `test_feed_ingestao.py`).
2. **`GET /feed` nunca serve gabarito.** Mesma regra de
   `test_gabarito_nao_vaza.py`, do outro lado da casa.
3. **`POST /feed/interactions` corrige no servidor e espelha a resposta no
   registro comportamental canônico** (`firestore_service.write_behavior_event`,
   contrato BEH-1.1) — SEM criar um segundo sistema de tracking. Uma
   chamada de só-tempo-de-tela (sem resposta) não gera evento nenhum.

Offline, com o dublê de Mongo do `conftest.py` e um Firestore de mentira —
nenhuma rede.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import feed_comportamento as fb  # noqa: E402
import feed_conteudo as fc  # noqa: E402
import feed_routes as routes  # noqa: E402
import firestore_service as fs  # noqa: E402
from feed_models import FeedInteractionIn  # noqa: E402
from feed_routes import TextoDeFeed  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user(uid="aluno-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno Teste")


def _admin() -> User:
    return User(user_id="admin-1", email="admin@exemplo.com", name="Admin", is_admin=True)


@pytest.fixture
def db(fake_db):
    routes.set_db(fake_db)
    return fake_db


@pytest.fixture(autouse=True)
def firestore_de_mentira(monkeypatch):
    """Evento de behavior sem tocar o Firestore — mesma receita de
    `test_cursos_estudo.py`. O dublê guarda o que foi pedido, e é sobre ele
    que os testes de contrato fazem suas afirmações."""
    eventos: list[dict] = []

    def _behavior(uid, **kwargs):
        if not kwargs.get("ontology_version"):
            raise ValueError("ontology_version é obrigatório no contrato de behavior 1.1")
        eventos.append({"uid": uid, **kwargs})
        return {"event_id": f"ev-{len(eventos)}"}

    monkeypatch.setattr(fs, "write_behavior_event", _behavior)
    return eventos


TEXTO_INICIAL = """
## QUESTÃO — Proporcionalidade
Se 3 xícaras fazem 12 biscoitos, quantas fazem 20?
A) 4
B) 5
C) 6
**Resposta:** B
**Feedback:** Cada biscoito pede 0,25 xícara.

## FLASHCARD
Capital da França?
Verso: Paris
"""


# ---------------------------------------------------------------------------
# Publicar por texto
# ---------------------------------------------------------------------------


def test_publicar_grava_os_cards_e_atribui_ordem_crescente(db):
    resultado = _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    assert resultado["novos"] == 2
    assert resultado["atualizados"] == 0

    salvos = _run(db.feed_items.find({}).sort("sequence_order", 1).to_list(10))
    assert [d["sequence_order"] for d in salvos] == [1, 2]
    assert {d["content_type"] for d in salvos} == {"question", "flashcard"}


def test_republicar_exatamente_o_mesmo_texto_e_idempotente(db):
    """Um duplo clique em "publicar" (ou reenviar o mesmo lote por engano)
    não pode duplicar o feed — o id é o hash do conteúdo, e o mesmo conteúdo
    reafirma o card na mesma posição em vez de criar um segundo."""
    _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    antes = _run(db.feed_items.find({}).sort("sequence_order", 1).to_list(10))
    ordem_antes = {d["content_id"]: d["sequence_order"] for d in antes}

    resultado = _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    assert resultado["novos"] == 0
    assert resultado["atualizados"] == 2

    depois = _run(db.feed_items.find({}).sort("sequence_order", 1).to_list(10))
    assert len(depois) == 2  # não duplicou
    for doc in depois:
        assert doc["sequence_order"] == ordem_antes[doc["content_id"]]  # posição preservada


def test_editar_o_texto_de_um_card_publica_um_card_novo_sem_apagar_o_antigo(db):
    """O id é o hash do conteúdo: reescrever uma frase muda o hash, e o
    resultado é um card NOVO no fim da fila — o antigo continua no ar até
    alguém apagá-lo pela lista. Publicar nunca apaga por conta própria."""
    _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    texto_editado = TEXTO_INICIAL.replace("Paris", "Paris, a Cidade Luz")
    resultado = _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=texto_editado), admin=_admin()))
    assert resultado["novos"] == 1
    assert resultado["atualizados"] == 1  # a questão, que não mudou

    todos = _run(db.feed_items.find({}).to_list(10))
    assert len(todos) == 3  # o flashcard antigo continua, ao lado do editado
    versos = {d["explanation_data"].get("text") for d in todos if d["content_type"] == "flashcard"}
    assert versos == {"Paris", "Paris, a Cidade Luz"}


def test_publicar_texto_com_card_novo_acrescenta_no_fim(db):
    _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    texto_maior = TEXTO_INICIAL + "\n## INSIGHT\nUm fato novo.\n"
    resultado = _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=texto_maior), admin=_admin()))
    assert resultado["novos"] == 1
    assert resultado["atualizados"] == 2
    novo = _run(db.feed_items.find_one({"content_type": "insight"}))
    assert novo["sequence_order"] == 3


def test_texto_que_nao_compila_nenhum_card_e_recusado(db):
    with pytest.raises(Exception) as excinfo:
        _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto="nada disso é um card"), admin=_admin()))
    assert excinfo.value.status_code == 422


def test_compilar_nao_grava_nada(db):
    resultado = _run(routes.admin_compilar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    assert len(resultado["cards"]) == 2
    assert resultado["pode_publicar"] is True
    assert _run(db.feed_items.count_documents({})) == 0
    # a prévia mostra o gabarito — é para isso que ela existe
    pergunta = next(c for c in resultado["cards"] if c["content_type"] == "question")
    assert any(o["is_correct"] for o in pergunta["answer_options"])


# ---------------------------------------------------------------------------
# GET /feed nunca serve gabarito
# ---------------------------------------------------------------------------


def test_get_feed_nao_revela_gabarito(db):
    _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    resposta = _run(routes.get_feed(cursor=0, limit=10))
    pergunta = next(i for i in resposta["items"] if i["content_type"] == "question")
    for opcao in pergunta["answer_options"]:
        assert "is_correct" not in opcao
        assert "feedback" not in opcao
    assert "explanation_data" not in pergunta


# ---------------------------------------------------------------------------
# POST /feed/interactions: corrige, revela e espelha no comportamento
# ---------------------------------------------------------------------------


def test_responder_corrige_no_servidor_e_grava_evento_canonico(db, firestore_de_mentira):
    _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    pergunta = _run(db.feed_items.find_one({"content_type": "question"}))
    certa = next(o["key"] for o in pergunta["answer_options"] if o["is_correct"])

    resultado = _run(routes.log_interaction(
        payload=FeedInteractionIn(content_id=pergunta["content_id"], completed=True,
                                   user_response={"selected": certa}),
        user=_user(),
    ))
    assert resultado["is_correct"] is True
    assert resultado["correct_key"] == certa

    assert len(firestore_de_mentira) == 1
    evento = firestore_de_mentira[0]
    assert evento["uid"] == "aluno-1"
    assert evento["item_id"] == f"FEED:{pergunta['content_id']}"
    assert evento["ontology_version"] == fb.ONTOLOGY_VERSION_FEED
    assert evento["contexto_tipo"] == "feed"
    assert evento["acertou"] is True
    assert evento["alternativa_escolhida"] == certa


def test_visualizar_sem_responder_nao_gera_evento_de_behavior(db, firestore_de_mentira):
    _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    pergunta = _run(db.feed_items.find_one({"content_type": "question"}))

    resultado = _run(routes.log_interaction(
        payload=FeedInteractionIn(content_id=pergunta["content_id"], time_spent_ms=1500,
                                   event={"event": "view", "ms": 1500}),
        user=_user(),
    ))
    assert resultado == {"ok": True}
    assert firestore_de_mentira == []


def test_enquete_nao_gera_evento_de_behavior_mas_registra_o_voto(db, firestore_de_mentira):
    _run(db.feed_items.insert_one({
        "content_id": "fc_enquete", "content_type": "enquete", "sequence_order": 1,
        "question_data": {"prompt": "Qual matéria você mais treina?"},
        "answer_options": [
            {"key": "a", "label": "Matemática", "is_correct": False, "feedback": ""},
            {"key": "b", "label": "Redação", "is_correct": False, "feedback": ""},
        ],
        "metadata": {}, "background_theme": "rose", "published": True,
    }))
    resultado = _run(routes.log_interaction(
        payload=FeedInteractionIn(content_id="fc_enquete", completed=True, user_response={"selected": "a"}),
        user=_user(),
    ))
    assert resultado["is_correct"] is None
    assert firestore_de_mentira == []
    doc = _run(db.feed_interactions.find_one({"user_id": "aluno-1", "content_id": "fc_enquete"}))
    assert doc["user_response"] == {"selected": "a"}


def test_flashcard_autoavaliado_gera_evento_com_o_julgamento_do_aluno(db, firestore_de_mentira):
    _run(routes.admin_publicar_feed(pedido=TextoDeFeed(texto=TEXTO_INICIAL), admin=_admin()))
    flash = _run(db.feed_items.find_one({"content_type": "flashcard"}))

    _run(routes.log_interaction(
        payload=FeedInteractionIn(content_id=flash["content_id"], completed=True,
                                   user_response={"lembrou": False}),
        user=_user(),
    ))
    assert len(firestore_de_mentira) == 1
    evento = firestore_de_mentira[0]
    assert evento["acertou"] is False
    assert evento["alternativa_escolhida"] is None  # autoavaliação não é escolha entre opções
