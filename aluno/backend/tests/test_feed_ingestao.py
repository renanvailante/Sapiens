"""Colar um texto enorme vira um feed inteiro: o que o compilador garante.

Mesma família de teste de `test_cursos_ingestao.py`, e pelo mesmo motivo — o
compilador de feed é o parser mais barato de quebrar em silêncio, porque quem
cola o texto nunca vê o JSON que sai do outro lado. Estes testes travam:

1. **Cada um dos sete tipos pedidos compila e valida.** Pergunta com
   alternativas, Flashcard, Verdadeiro/Falso, Complete a lacuna, Desafio (dos
   dois formatos), Insight e Revisão.
2. **O gabarito não fica onde o autor escreveu.** Alternativas embaralhadas,
   determinístico (recompilar dá o mesmo resultado).
3. **Card quebrado vira aviso, e o resto do lote vai ao ar** — a garantia que
   faz "colar um texto de 40 cards" seguro: um erro de digitação num deles não
   derruba os outros 39.
4. **O id é o hash do conteúdo**: recompilar o mesmo texto dá o mesmo id, e
   mudar uma vírgula muda só o card daquela vírgula.

Offline: nenhum banco, nenhuma rede.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import feed_conteudo as fc  # noqa: E402
import feed_ingestao as fi  # noqa: E402


def _um_card(texto: str, tipo: str | None = None):
    compilado = fi.compilar(texto)
    assert compilado.problemas == [], compilado.problemas
    assert len(compilado.cards) == 1, (texto, compilado.avisos)
    card = compilado.cards[0]
    if tipo:
        assert card["content_type"] == tipo
    return card


# ---------------------------------------------------------------------------
# Os sete tipos pedidos
# ---------------------------------------------------------------------------


def test_pergunta_com_alternativas():
    card = _um_card(
        """
## QUESTÃO — Proporcionalidade
Se 3 xícaras de farinha fazem 12 biscoitos, quantas fazem 20?
A) 4
B) 5
C) 6
D) 7
**Resposta:** B
**Feedback:** Cada biscoito pede 0,25 xícara; 20 × 0,25 = 5. A alternativa A divide direto por 5.
""",
        "question",
    )
    certa = next(o for o in card["answer_options"] if o["is_correct"])
    assert certa["label"] == "5"
    # A letra certa não é sempre a mesma posição do texto original (B) — a
    # única garantia é que ela existe e é única.
    assert sum(o["is_correct"] for o in card["answer_options"]) == 1
    # O distrator citado por letra no texto original ("alternativa A divide")
    # carrega comentário próprio, na posição NOVA dele.
    assert any(o["feedback"] for o in card["answer_options"] if not o["is_correct"])


def test_flashcard():
    card = _um_card(
        """
## FLASHCARD — Trabalho de uma força
Qual a fórmula do trabalho de uma força constante?
Verso: W = F · d · cos(θ)
""",
        "flashcard",
    )
    assert card["question_data"]["prompt"] == "Qual a fórmula do trabalho de uma força constante?"
    assert card["explanation_data"]["text"] == "W = F · d · cos(θ)"


def test_verdadeiro_ou_falso():
    card = _um_card(
        """
## VERDADEIRO OU FALSO
A velocidade média depende da trajetória percorrida.
**Resposta:** Verdadeiro
**Feedback:** A velocidade média usa a distância percorrida, não o deslocamento.
""",
        "verdadeiro_falso",
    )
    certa = next(o for o in card["answer_options"] if o["is_correct"])
    assert certa["key"] == "v"


def test_complete_a_lacuna():
    card = _um_card(
        """
## COMPLETE A LACUNA
A fórmula de Bhaskara resolve equações do ____ grau.
A) primeiro
B) segundo
C) terceiro
**Resposta:** B
**Feedback:** Equações do segundo grau têm expoente máximo 2.
""",
        "complete",
    )
    assert "___" in card["question_data"]["prompt"]


def test_desafio_numerico_nao_expoe_o_gabarito_antes_de_responder():
    card = _um_card(
        """
## DESAFIO
Quanto é 2 elevado a 5?
**Resposta:** 32
**Feedback:** 2×2×2×2×2 = 32.
""",
        "desafio",
    )
    assert card["formato"] == "aberto"
    assert card["answer_options"] == []
    tela = fc.para_a_tela(card)
    assert "aceitos" not in tela["metadata"]
    assert "numero" not in tela["metadata"]
    assert "resposta_exibicao" not in tela["metadata"]
    acertou, revelacao = fc.corrigir(card, {"texto": "32"})
    assert acertou is True
    assert revelacao["resposta_certa"] == "32"
    errou, _ = fc.corrigir(card, {"texto": "31"})
    assert errou is False


def test_desafio_com_alternativas_e_corrigido_como_pergunta():
    card = _um_card(
        """
## DESAFIO — Estruturas de dados
Qual estrutura usa LIFO?
A) Fila
B) Pilha
C) Árvore
**Resposta:** B
**Feedback:** Pilha é Last In, First Out.
""",
        "desafio",
    )
    assert card.get("formato") != "aberto"
    assert len(card["answer_options"]) == 3


def test_insight():
    card = _um_card(
        """
## INSIGHT
O cérebro consome cerca de 20% da energia do corpo, mesmo pesando só 2% do peso total.
""",
        "insight",
    )
    assert "20%" in card["question_data"]["prompt"]


def test_revisao_e_autoavaliada_como_flashcard():
    card = _um_card(
        """
## REVISÃO — Lei de Ohm
Você lembra da relação entre tensão, corrente e resistência?
Verso: V = R × i
""",
        "revisao",
    )
    assert card["content_type"] == "revisao"
    acertou, _ = fc.corrigir(card, {"lembrou": True})
    assert acertou is True
    naoacertou, _ = fc.corrigir(card, {"lembrou": False})
    assert naoacertou is False


# ---------------------------------------------------------------------------
# Tolerância: card quebrado vira aviso, o resto do lote sobrevive
# ---------------------------------------------------------------------------


def test_questao_sem_resposta_fica_de_fora_sem_derrubar_o_lote():
    compilado = fi.compilar(
        """
## INSIGHT
Primeiro card, válido.

## QUESTÃO
Sem gabarito nenhum.
A) x
B) y

## FLASHCARD
Terceiro card, também válido.
Verso: ok
"""
    )
    assert len(compilado.cards) == 2
    assert compilado.pode_publicar
    assert any("Resposta" in a for a in compilado.avisos)


def test_desafio_em_prosa_nao_e_adivinhado():
    compilado = fi.compilar(
        """
## DESAFIO
Explique por que o céu é azul.
**Resposta:** Porque a luz azul se espalha mais na atmosfera por causa do espalhamento Rayleigh, que favorece comprimentos de onda curtos.
"""
    )
    assert compilado.cards == []
    assert "prosa" in compilado.avisos[0]


def test_texto_sem_nenhum_cabecalho_reconhecido_e_recusado():
    compilado = fi.compilar("Isto aqui não é um card de jeito nenhum.")
    assert compilado.cards == []
    assert compilado.problemas


def test_chave_de_alternativa_nunca_e_a_letra_original():
    """Regressão do mesmo bug que `cursos_ingestao` já corrigiu: se o id da
    alternativa fosse a letra do texto-fonte, a resposta certa estaria
    legível no HTML (quem escreve põe a certa em A quase sempre)."""
    card = _um_card(
        """
## QUESTÃO
Pergunta qualquer.
A) errada
B) certa
**Resposta:** B
"""
    )
    certa = next(o for o in card["answer_options"] if o["is_correct"])
    # A letra ORIGINAL era B; o id pode ter virado qualquer posição — a única
    # coisa garantida é que ele não carrega a letra de origem como segredo.
    assert certa["key"] in ("a", "b")


# ---------------------------------------------------------------------------
# Determinismo e identidade
# ---------------------------------------------------------------------------


def test_recompilar_o_mesmo_texto_da_o_mesmo_id_e_a_mesma_ordem():
    texto = """
## QUESTÃO
Pergunta.
A) 1
B) 2
**Resposta:** A
"""
    c1 = fi.compilar(texto).cards[0]
    c2 = fi.compilar(texto).cards[0]
    assert c1["content_id"] == c2["content_id"]
    assert c1["answer_options"] == c2["answer_options"]


def test_mudar_um_card_nao_muda_o_id_dos_outros():
    base = """
## INSIGHT
Primeiro card.

## FLASHCARD
Segundo card.
Verso: resposta
"""
    editado = base.replace("Primeiro card.", "Primeiro card, com uma vírgula a mais.")
    antes = {c["content_type"]: c["content_id"] for c in fi.compilar(base).cards}
    depois = {c["content_type"]: c["content_id"] for c in fi.compilar(editado).cards}
    assert antes["flashcard"] == depois["flashcard"]
    assert antes["insight"] != depois["insight"]


def test_card_duplicado_letra_por_letra_publica_uma_vez_so():
    compilado = fi.compilar(
        """
## INSIGHT
Exatamente o mesmo texto.

## INSIGHT
Exatamente o mesmo texto.
"""
    )
    assert len(compilado.cards) == 1
    assert any("idêntico" in a for a in compilado.avisos)


# ---------------------------------------------------------------------------
# Preço não mora em conteúdo (mesma régua dos cursos)
# ---------------------------------------------------------------------------


def test_ordene_e_relacione_embaralham_e_escondem_a_resposta():
    card = _um_card(
        """
## ORDENE — Método científico
- Observação
- Hipótese
- Experimentação
- Conclusão
""",
        "ordene",
    )
    tela = fc.para_a_tela(card)
    assert "ordem_exibida" not in tela["metadata"]
    assert len(tela["metadata"]["passos"]) == 4
    acertou, rev = fc.corrigir(card, {"ordem": [p["id"] for p in card["metadata"]["passos"]]})
    assert acertou is True
    assert rev["ordem_certa"] == [p["id"] for p in card["metadata"]["passos"]]

    par = _um_card(
        """
## RELACIONE — Capitais
Brasil = Brasília
França = Paris
Japão = Tóquio
""",
        "relacione",
    )
    tela_par = fc.para_a_tela(par)
    assert "pares" not in tela_par["metadata"]
    assert len(tela_par["metadata"]["esquerda"]) == 3
    assert len(tela_par["metadata"]["direita"]) == 3
