"""Decompõe a frase temática em elementos obrigatórios — sem rede, sem LLM.

Três itens do canon (`ZERO-01` fuga total, `TEMA-02` tangenciamento e
`COMP-II` compreensão da proposta) dependem de
`RedacaoEntrada.tema_elementos_obrigatorios`. Na prática o campo chegava
SEMPRE vazio: a tela de redação pede só a frase do tema, e nenhuma outra
superfície preenche a decomposição. Os três itens caíam então em
`INSUFICIENTE` ("tema_elementos_obrigatorios não informado") e:

  * ou iam para o Gemini em toda submissão — o oposto de local-first, e o
    caminho mais caro possível para uma informação que está inteira na
    própria frase que o aluno digitou;
  * ou, sem escalonamento, ficavam sem candidato e a Competência II somava
    zero na nota final.

A decomposição aqui é léxica e conservadora: as palavras de conteúdo da
frase temática (sem as vazias), normalizadas e reduzidas a um radical curto
para tolerar flexão. Não é interpretação semântica do tema — é exatamente o
que `heuristicas._cobertura_tematica` já faz com a lista quando ela vem
preenchida, só que agora a lista existe.
"""
from __future__ import annotations

import re
import unicodedata

# Palavras que aparecem em quase toda frase temática e não distinguem tema
# nenhum. Uma delas na lista de elementos obrigatórios daria "cobertura
# temática" a qualquer texto em português — inclusive a uma fuga total.
_VAZIAS = {
    "a", "à", "às", "ao", "aos", "as", "o", "os", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "por",
    "pelo", "pela", "pelos", "pelas", "para", "com", "sem", "sob", "sobre",
    "entre", "e", "ou", "que", "se", "como", "mais", "menos", "seu", "sua",
    "seus", "suas", "este", "esta", "esse", "essa", "aquele", "aquela",
    "brasil", "brasileiro", "brasileira", "brasileiros", "brasileiras",
    "atual", "atualmente", "contemporaneo", "contemporanea", "sociedade",
    "seculo", "xxi", "questao", "questoes", "tema", "desafio", "desafios",
    "caminhos", "caminho", "combater", "enfrentar", "enfrentamento",
}

# Abaixo disto o radical vira ruído: "os", "uso", "paz" casariam dentro de
# outras palavras e a cobertura temática deixaria de significar qualquer coisa.
_MIN_RADICAL = 5

# Quantos elementos no máximo. A cobertura é uma fração (encontrados/total):
# com 12 elementos, cada palavra que falta derruba a fração e o texto vira
# candidato a tangenciamento sem motivo. Os primeiros termos de uma frase
# temática do Enem são também os mais específicos.
_MAX_ELEMENTOS = 6


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _radical(palavra: str) -> str:
    """Corta a flexão mais comum do português para que "comunidades" na frase
    temática case com "comunidade" no texto do aluno. Deliberadamente burro:
    remove só sufixo de plural/gênero, nunca reescreve o radical."""
    p = palavra
    for sufixo in ("coes", "aes", "oes", "eis", "ais", "is", "as", "os", "es", "s", "a", "o"):
        if len(p) - len(sufixo) >= _MIN_RADICAL and p.endswith(sufixo):
            return p[: -len(sufixo)]
    return p


def elementos_do_tema(tema_frase: str | None) -> list[str]:
    """Elementos obrigatórios derivados da frase temática, em ordem de
    aparição e sem repetição. Lista vazia quando a frase não tem nenhuma
    palavra de conteúdo aproveitável — nesse caso os itens que dependem dela
    seguem `INSUFICIENTE`, como antes, em vez de receberem um elemento
    inventado que nenhum texto conseguiria cobrir."""
    if not (tema_frase or "").strip():
        return []
    palavras = re.findall(r"[^\W\d_]+", _sem_acento(tema_frase.lower()), flags=re.UNICODE)
    elementos: list[str] = []
    for palavra in palavras:
        if palavra in _VAZIAS or len(palavra) < _MIN_RADICAL:
            continue
        radical = _radical(palavra)
        if len(radical) < _MIN_RADICAL or radical in elementos:
            continue
        elementos.append(radical)
        if len(elementos) >= _MAX_ELEMENTOS:
            break
    return elementos
