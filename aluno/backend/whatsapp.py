"""Número de WhatsApp do aluno — normalização, validação e link de conversa.

Um número de WhatsApp só serve para uma coisa: **alguém da equipe abrir uma
conversa com aquele aluno**. Guardar o que a pessoa digitou ("(11) 9 1234
5678", "11987654321", "+55 11 98765-4321") resolve a gravação e quebra o uso:
o painel do admin não consegue montar um `wa.me/...` a partir de texto livre,
e dois cadastros do mesmo número viram dois números diferentes.

Por isso a gravação guarda DOIS campos, sempre juntos:

* ``whatsapp``      — como a pessoa digitou (só limpo de espaço duplo). É o
  que ela reconhece se precisarmos confirmar com ela.
* ``whatsapp_e164`` — só dígitos, com DDI, pronto para virar `wa.me/<e164>`.
  É o campo que o admin usa, e o único que serve para comparar.

**DDI 55 implícito.** O público é brasileiro e ninguém digita "+55" no próprio
celular. Um número de 10 ou 11 dígitos é tratado como brasileiro (DDD + linha);
12 a 15 dígitos são aceitos como já internacionais e ficam como estão. Fora
dessa faixa é erro do titular, e a mensagem diz o que fazer em vez de gravar
um número que nunca vai tocar.
"""
from __future__ import annotations

import re

# Menor: 10 dígitos (DDD + 8, fixo antigo). Maior: 15, o teto do E.164.
MIN_DIGITOS = 10
MAX_DIGITOS = 15
DDI_PADRAO = "55"

ERRO_PADRAO = (
    "WhatsApp inválido. Escreva com DDD, como (11) 91234-5678 — "
    "é por ele que a gente te manda o link da aula ao vivo."
)


class WhatsAppInvalido(ValueError):
    """Número que não dá para discar. Quem chama traduz em 422."""


def _so_digitos(bruto: str) -> str:
    return re.sub(r"\D", "", bruto or "")


def normalizar(bruto: str) -> tuple[str, str]:
    """`(como_digitado, e164)` — ou `WhatsAppInvalido`.

    O primeiro elemento é o texto do titular, apenas com espaços colapsados; o
    segundo é o número discável, só dígitos e com DDI.
    """
    digitado = re.sub(r"\s+", " ", (bruto or "").strip())
    digitos = _so_digitos(digitado)

    # "00" é o prefixo internacional discado em várias operadoras; quem escreve
    # "005511..." quis dizer "+5511...".
    if digitos.startswith("00"):
        digitos = digitos[2:]

    if len(digitos) in (10, 11):
        digitos = DDI_PADRAO + digitos

    if not (MIN_DIGITOS <= len(digitos) <= MAX_DIGITOS):
        raise WhatsAppInvalido(ERRO_PADRAO)

    return digitado, digitos


def link_conversa(e164: str | None) -> str | None:
    """Endereço que abre a conversa no WhatsApp Web ou no aplicativo.

    `None` em vez de um link quebrado quando o aluno é de antes do campo
    existir — a tela do admin distingue "sem número" de "número inválido".
    """
    if not e164:
        return None
    return f"https://wa.me/{_so_digitos(e164)}"


def formatar_br(e164: str | None) -> str | None:
    """`5511987654321` -> `(11) 98765-4321`, para leitura humana no painel.

    Número de outro país volta com um "+" na frente e sem mais formatação:
    inventar grupos de dígitos para um plano de numeração que não conhecemos
    produziria um número com cara de certo e impossível de conferir.
    """
    if not e164:
        return None
    digitos = _so_digitos(e164)
    if digitos.startswith(DDI_PADRAO) and len(digitos) in (12, 13):
        ddd, linha = digitos[2:4], digitos[4:]
        return f"({ddd}) {linha[:-4]}-{linha[-4:]}"
    return f"+{digitos}"
