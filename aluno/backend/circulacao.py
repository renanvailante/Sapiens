"""Cerco de circulação — retira itens BLOQUEADOS da prova sem migrar dado.

Durante o saneamento do corpus (auditoria de 2026-08-26) existem itens que não
podem chegar ao aluno: gabarito divergente do oficial do INEP, enunciado ou
alternativa vazia, questão anulada pela banca. Tirá-los de circulação é um
**filtro de leitura**, nunca uma migração:

- não escreve nada em Mongo nem no Firestore;
- não apaga nem marca documento nenhum;
- desliga-se removendo uma variável de ambiente.

Isso importa porque `_auto_sync_loop` reconstrói `questoes_public` a partir do
Firestore a cada poucos minutos: qualquer marca gravada só no Mongo seria
apagada no ciclo seguinte. Um filtro em memória não tem esse problema.

A lista vem de `SANEAMENTO_BLOQUEADOS_PATH` — o `bloqueados.json` que
`pipeline/scripts/audit_corpus.py` emite — ou, para um bloqueio pontual, de
`SANEAMENTO_BLOQUEADOS` com `item_id`s separados por vírgula.

Quando a Fase 2 fizer `qualidade.apto_para_camada_de_crenca` valer de fato,
este módulo deixa de ser necessário e sai junto com a variável.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ENV_PATH = "SANEAMENTO_BLOQUEADOS_PATH"
_ENV_LISTA = "SANEAMENTO_BLOQUEADOS"

_cache: frozenset[str] | None = None


def _carregar() -> frozenset[str]:
    ids: set[str] = set()

    bruto = os.environ.get(_ENV_LISTA, "")
    ids.update(p.strip() for p in bruto.split(",") if p.strip())

    caminho = os.environ.get(_ENV_PATH, "")
    if caminho:
        p = Path(caminho)
        try:
            dados = json.loads(p.read_text(encoding="utf-8"))
            # Aceita tanto a lista crua quanto o envelope emitido pelo auditor.
            itens = dados.get("item_ids", []) if isinstance(dados, dict) else dados
            ids.update(str(i) for i in itens if i)
        except FileNotFoundError:
            logger.warning("Cerco de circulação: %s não encontrado (%s); nada bloqueado.", _ENV_PATH, p)
        except (OSError, ValueError) as exc:
            logger.warning("Cerco de circulação: %s ilegível (%s); nada bloqueado.", _ENV_PATH, exc)

    if ids:
        logger.info("Cerco de circulação ativo: %d itens fora da prova.", len(ids))
    return frozenset(ids)


def bloqueados() -> frozenset[str]:
    """Conjunto de `item_id` fora de circulação. Lido uma vez por processo."""
    global _cache
    if _cache is None:
        _cache = _carregar()
    return _cache


def recarregar() -> frozenset[str]:
    """Descarta o cache — usado por testes e pelo fim do saneamento."""
    global _cache
    _cache = None
    return bloqueados()


def ativo() -> bool:
    return bool(bloqueados())


def aplicar(filtro: dict[str, Any]) -> dict[str, Any]:
    """Acrescenta a exclusão a um filtro do Mongo, sem alterar o original."""
    ids = bloqueados()
    if not ids:
        return filtro
    return {**filtro, "item_id": {"$nin": sorted(ids)}}


def esta_bloqueado(item_id: str | None) -> bool:
    return bool(item_id) and item_id in bloqueados()
