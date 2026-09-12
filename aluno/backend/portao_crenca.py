"""Portão da camada de crença — `qualidade.apto_para_camada_de_crenca` com efeito.

Até 2026-08-26 o campo não gatilhava nada: aparecia numa docstring e num campo
Pydantic, e nenhuma consulta o lia. Um item com o portão fechado circulava
exatamente como um item aprovado.

O contrato distingue duas coisas que é fácil confundir (EXT-WP1-1.0 L13b,
Error Trace §6):

    "um item pode ser ARMAZENADO sem revisão humana; não pode INFLUENCIAR o
     estado de um estudante real sem ela"

Ou seja: o portão fechado proíbe o item de **alimentar crença**, não de ser
praticado. Praticar uma questão não revisada é legítimo; deixar o acerto dela
mover o mapa cognitivo do aluno, não.

Daí os três modos:

    crenca      (padrão) item não apto continua na prova, mas seus eventos não
                entram no agregado que alimenta o mapa de habilidades.
    circulacao  item não apto também sai da prova. É a leitura mais estrita;
                mede-se o custo antes de ligar (ver o relatório da Fase 2).
    desligado   comportamento anterior. Depuração — e, desde 2026-09-04, o
                modo do piloto: com o corpus inteiro sem revisão humana, o
                Motor Cognitivo ficava vazio para todo aluno. O bloqueio saiu,
                a regra não: `motor_cognitivo` marca como `provisorio` todo
                traço que entra sem revisão, e a tela do aluno declara isso.
                Reverter é `fly secrets unset PORTAO_CRENCA_MODO`.

`PORTAO_CRENCA_MODO` escolhe. Como todo o corpus está hoje com o portão
fechado — e vai continuar até haver revisão humana registrada —, ligar
`circulacao` sem antes revisar itens esvazia a prova. O modo é explícito
justamente para essa decisão não acontecer por acidente.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

MODO_CRENCA = "crenca"
MODO_CIRCULACAO = "circulacao"
MODO_DESLIGADO = "desligado"
MODOS = (MODO_CRENCA, MODO_CIRCULACAO, MODO_DESLIGADO)

_ENV = "PORTAO_CRENCA_MODO"
_cache: str | None = None

# Piso de confiança — o substituto PROVISÓRIO da revisão humana
# ------------------------------------------------------------
#
# Revisar 268 itens à mão é caro, e a pergunta óbvia é "dá para usar a
# confiança que a própria anotação declara?". Dá, com uma condição e um
# esclarecimento.
#
# A condição: o piso NUNCA grava `revisado`/`apto_para_camada_de_crenca`. Ele
# não transforma a afirmação da IA em revisão humana — isso seria falsificar o
# dado que L13b existe para proteger, e a tela do aluno continuaria (com razão)
# chamando o perfil de provisório. O piso só decide o que ENTRA enquanto o
# portão está desligado.
#
# O esclarecimento: ligar o piso é mais ESTRITO que produção hoje, não mais
# frouxo. Com `desligado` puro, todo traço entra — inclusive os 130 elos raiz
# que o próprio anotador marcou com confiança 0.15 (medido em 2026-09-12). Um
# piso é a primeira filtragem que esse corpus recebe.
#
# Cuidado com o campo errado: `qualidade.confianca_global` é 0.7 em TODOS os
# 268 itens do acervo — é constante, não carrega informação. O que varia é a
# confiança do ELO RAIZ (0.7 / 0.4 / 0.15), e é sobre ela que o piso incide.
#
# Revisão humana SUPERSEDE o piso: item revisado passa qualquer que seja a
# confiança anotada. O piso é um substituto de revisão, não um requisito a mais.
_ENV_PISO = "PORTAO_CONFIANCA_MINIMA"
_cache_piso: float | None = None


def modo() -> str:
    global _cache
    if _cache is None:
        bruto = (os.environ.get(_ENV) or MODO_CRENCA).strip().lower()
        if bruto not in MODOS:
            logger.warning("%s='%s' inválido; usando '%s'.", _ENV, bruto, MODO_CRENCA)
            bruto = MODO_CRENCA
        _cache = bruto
    return _cache


def confianca_minima() -> float:
    """Piso de confiança do elo raiz. `0.0` (padrão) = sem piso, que é o
    comportamento anterior a este campo existir."""
    global _cache_piso
    if _cache_piso is None:
        bruto = (os.environ.get(_ENV_PISO) or "").strip()
        try:
            valor = float(bruto) if bruto else 0.0
        except ValueError:
            logger.warning("%s='%s' não é número; usando 0.0 (sem piso).", _ENV_PISO, bruto)
            valor = 0.0
        if not 0.0 <= valor <= 1.0:
            logger.warning("%s=%s fora de [0,1]; usando 0.0 (sem piso).", _ENV_PISO, valor)
            valor = 0.0
        _cache_piso = valor
    return _cache_piso


def alcanca_o_piso(confianca_da_raiz: float | None) -> bool:
    """O elo raiz é confiável o bastante para entrar sem revisão humana?"""
    piso = confianca_minima()
    if piso <= 0.0:
        return True
    return confianca_da_raiz is not None and confianca_da_raiz >= piso


def pode_mover_o_perfil(*, revisado: bool, confianca_da_raiz: float | None) -> bool:
    """A regra completa, num lugar só — usada pelo motor e pela revisão espaçada.

    Revisão humana passa sempre. Sem ela, só entra com o portão desligado E
    com a raiz alcançando o piso.
    """
    if revisado:
        return True
    if modo() != MODO_DESLIGADO:
        return False
    return alcanca_o_piso(confianca_da_raiz)


def recarregar() -> str:
    global _cache, _cache_piso
    _cache = None
    _cache_piso = None
    return modo()


def _valor(bloco: Any) -> bool:
    if isinstance(bloco, dict):
        return bloco.get("valor") is True
    return bloco is True


def apto(doc: dict | None) -> bool:
    """O item pode influenciar o estado cognitivo do aluno?

    Aceita tanto o documento achatado de `questoes_public` quanto o completo
    (`{item: {qualidade: ...}}`), porque os dois formatos circulam no backend.
    """
    if not doc:
        return False
    if "apto_para_camada_de_crenca" in doc:
        return _valor(doc.get("apto_para_camada_de_crenca"))
    qual = ((doc.get("item") or {}).get("qualidade")) or doc.get("qualidade") or {}
    return _valor(qual.get("apto_para_camada_de_crenca"))


def pode_alimentar_crenca(doc: dict | None) -> bool:
    """Gate do agregado cognitivo. Só `desligado` dispensa o portão."""
    if modo() == MODO_DESLIGADO:
        return True
    return apto(doc)


def aplicar_a_prova(filtro: dict[str, Any]) -> dict[str, Any]:
    """Acrescenta o portão ao filtro da prova — só no modo `circulacao`."""
    if modo() != MODO_CIRCULACAO:
        return filtro
    return {**filtro, "apto_para_camada_de_crenca.valor": True}
