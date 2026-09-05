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


def modo() -> str:
    global _cache
    if _cache is None:
        bruto = (os.environ.get(_ENV) or MODO_CRENCA).strip().lower()
        if bruto not in MODOS:
            logger.warning("%s='%s' inválido; usando '%s'.", _ENV, bruto, MODO_CRENCA)
            bruto = MODO_CRENCA
        _cache = bruto
    return _cache


def recarregar() -> str:
    global _cache
    _cache = None
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
