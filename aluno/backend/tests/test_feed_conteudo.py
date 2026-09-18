"""O contrato do card de feed: o que desce para a tela, e quem corrige.

Mesma família de `test_gabarito_nao_vaza.py`, do outro lado da casa: o feed é
lido sem login (GET /feed é público), então `para_a_tela` é a única coisa
entre um card recém-publicado e um `curl` que gabarita o feed inteiro. Estes
testes travam isso tipo por tipo, e travam que `corrigir` nunca lê a
correção que o próprio cliente declarou.

Offline: nenhum banco, nenhuma rede.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import feed_conteudo as fc  # noqa: E402


def _card_de_pergunta():
    return {
        "content_id": "fc_1",
        "content_type": "question",
        "question_data": {"prompt": "2+2?"},
        "answer_options": [
            {"key": "a", "label": "3", "is_correct": False, "feedback": "Subtraiu em vez de somar."},
            {"key": "b", "label": "4", "is_correct": True, "feedback": ""},
        ],
        "explanation_data": {"text": "2+2 = 4."},
        "metadata": {},
        "background_theme": "violet",
    }


# ---------------------------------------------------------------------------
# O que NUNCA desce antes de responder
# ---------------------------------------------------------------------------


def test_pergunta_nao_revela_gabarito_nem_feedback_antes_de_responder():
    tela = fc.para_a_tela(_card_de_pergunta())
    for opcao in tela["answer_options"]:
        assert "is_correct" not in opcao
        assert "feedback" not in opcao
    assert "explanation_data" not in tela


def test_enquete_nao_revela_opiniao_certa_nem_votos():
    card = {
        "content_id": "fc_2", "content_type": "enquete",
        "question_data": {"prompt": "Qual matéria você mais treina?"},
        "answer_options": [
            {"key": "a", "label": "Matemática", "is_correct": False, "feedback": ""},
            {"key": "b", "label": "Redação", "is_correct": False, "feedback": ""},
        ],
        "metadata": {"votos": {"a": 10, "b": 3}, "fecho": "A maioria também acha."},
        "background_theme": "rose",
    }
    tela = fc.para_a_tela(card)
    assert "votos" not in tela["metadata"]
    assert "fecho" not in tela["metadata"]


def test_ordene_nao_revela_a_ordem_certa():
    card = {
        "content_id": "fc_3", "content_type": "ordene",
        "question_data": {"prompt": "Ordene"},
        "metadata": {"passos": [{"id": "p1", "texto": "A"}, {"id": "p2", "texto": "B"}], "ordem_exibida": ["p2", "p1"]},
        "background_theme": "amber",
    }
    tela = fc.para_a_tela(card)
    assert "ordem_exibida" not in tela["metadata"]
    assert [p["id"] for p in tela["metadata"]["passos"]] == ["p2", "p1"]  # já embaralhado


def test_relacione_nao_revela_o_pareamento_certo():
    card = {
        "content_id": "fc_4", "content_type": "relacione",
        "question_data": {"prompt": "Relacione"},
        "metadata": {
            "pares": [
                {"id": "p1", "esquerda": "Brasil", "direita": "Brasília", "direita_id": "d2"},
                {"id": "p2", "esquerda": "França", "direita": "Paris", "direita_id": "d1"},
            ],
            "direita_exibida": ["d1", "d2"],
        },
        "background_theme": "ocean",
    }
    tela = fc.para_a_tela(card)
    assert "pares" not in tela["metadata"]
    assert "direita_exibida" not in tela["metadata"]
    # A esquerda mantém o id do PAR, mas a direita usa o id embaralhado — só
    # assim o pareamento certo não está implícito na ordem.
    ids_direita = [d["id"] for d in tela["metadata"]["direita"]]
    assert ids_direita == ["d1", "d2"]


def test_desafio_aberto_nao_revela_o_gabarito_nem_a_tolerancia():
    card = {
        "content_id": "fc_5", "content_type": "desafio", "formato": "aberto",
        "question_data": {"prompt": "Quanto é 2^5?"},
        "metadata": {"aceitos": ["32"], "numero": {"valor": 32.0, "tolerancia": 0.1}, "resposta_exibicao": "32"},
        "explanation_data": {"text": "32."},
        "background_theme": "rose",
    }
    tela = fc.para_a_tela(card)
    assert tela["metadata"] == {"tem_dica": False}


# ---------------------------------------------------------------------------
# Quem corrige é o servidor, nunca o cliente
# ---------------------------------------------------------------------------


def test_corrigir_ignora_qualquer_alegacao_do_cliente_sobre_acerto():
    card = _card_de_pergunta()
    # O cliente alega ter acertado com a errada — o servidor decide sozinho.
    acertou, revelacao = fc.corrigir(card, {"selected": "a", "is_correct": True})
    assert acertou is False
    assert revelacao["correct_key"] == "b"
    assert revelacao["feedback"] == "Subtraiu em vez de somar."


def test_corrigir_sem_resposta_nao_revela_nada():
    acertou, revelacao = fc.corrigir(_card_de_pergunta(), {})
    assert acertou is None
    assert revelacao == {}


def test_autoavaliacao_registra_o_que_o_aluno_disse_sem_gabarito():
    card = {
        "content_id": "fc_6", "content_type": "flashcard",
        "question_data": {"prompt": "Capital da França?"},
        "explanation_data": {"text": "Paris"},
        "metadata": {}, "background_theme": "emerald",
    }
    acertou, _ = fc.corrigir(card, {"lembrou": True})
    assert acertou is True


def test_leitura_pura_nunca_tem_certo_ou_errado():
    card = {
        "content_id": "fc_7", "content_type": "insight",
        "question_data": {"prompt": "Fato."}, "explanation_data": {}, "metadata": {},
        "background_theme": "rose",
    }
    acertou, _ = fc.corrigir(card, {"qualquer": "coisa"})
    assert acertou is None


# ---------------------------------------------------------------------------
# Validação: preço não mora em conteúdo (mesma régua dos cursos)
# ---------------------------------------------------------------------------


def test_chave_de_preco_em_qualquer_nivel_do_metadata_e_bloqueada():
    card = _card_de_pergunta()
    card["metadata"] = {"aninhado": {"custo_sparks": 20}}
    problemas = fc.validar_card(card)
    assert any("preço" in p for p in problemas)


def test_enquete_com_alternativa_certa_e_invalida():
    card = {
        "content_id": "fc_8", "content_type": "enquete",
        "question_data": {"prompt": "Qual matéria?"},
        "answer_options": [
            {"key": "a", "label": "Matemática", "is_correct": True},
            {"key": "b", "label": "Redação", "is_correct": False},
        ],
        "metadata": {}, "background_theme": "rose",
    }
    problemas = fc.validar_card(card)
    assert any("opinião" in p for p in problemas)
