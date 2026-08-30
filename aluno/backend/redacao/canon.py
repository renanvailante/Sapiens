"""Carrega `13 enem_regras_computaveis.json` — apoio_externo, GOV-1.0 §1.1.

Este módulo só LÊ o canon; nunca o reescreve nem interpreta o que não está
explícito nele (ambiguidades ficam como ambiguidades — ver os módulos que
consomem este loader para as convenções de engenharia adotadas, cada uma
citando o `AMB-xx` correspondente).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("sapiens.redacao.canon")

_ARQUIVO_PADRAO = "13 enem_regras_computaveis.json"


class CanonIndisponivelError(RuntimeError):
    """O canon do Enem não pôde ser carregado — ausente, ilegível ou JSON
    inválido. Nunca derruba o boot do app: só a rota de redação vira 503."""


def _caminho_canon() -> Path:
    override = os.environ.get("ENEM_CANON_PATH")
    if override:
        return Path(override)
    # aluno/backend/redacao/canon.py -> ... -> raiz do monorepo -> pipeline/docs/enem-redacao/
    raiz = Path(__file__).resolve().parents[3]
    return raiz / "pipeline" / "docs" / "enem-redacao" / _ARQUIVO_PADRAO


_CANON: dict[str, Any] | None = None


def _carregar() -> dict[str, Any]:
    caminho = _caminho_canon()
    try:
        with caminho.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise CanonIndisponivelError(f"Canon do Enem não encontrado em {caminho}") from exc
    except json.JSONDecodeError as exc:
        raise CanonIndisponivelError(f"Canon do Enem em {caminho} não é JSON válido: {exc}") from exc
    if not isinstance(data.get("competencias"), list) or len(data["competencias"]) != 5:
        raise CanonIndisponivelError("Canon do Enem carregado, mas sem as 5 competências esperadas.")
    return data


def canon() -> dict[str, Any]:
    """Singleton em memória, carregado sob demanda (lazy) na 1ª chamada."""
    global _CANON
    if _CANON is None:
        _CANON = _carregar()
        logger.info("Canon Enem carregado: %s (versão %s)", _CANON.get("id"), _CANON.get("versao"))
    return _CANON


def recarregar() -> dict[str, Any]:
    """Força releitura do arquivo — usado por testes que trocam `ENEM_CANON_PATH`."""
    global _CANON
    _CANON = None
    return canon()


def versao() -> str:
    return str(canon().get("versao") or "desconhecida")


def gatilhos_zero_redacao_inteira() -> list[dict[str, Any]]:
    return canon()["etapa_0_elegibilidade"]["gatilhos_zero_redacao_inteira"]


def gatilhos_zero_localizado() -> list[dict[str, Any]]:
    return canon()["etapa_0_elegibilidade"]["gatilhos_zero_localizado"]


def partes_desconectadas() -> dict[str, Any]:
    return canon()["etapa_0_elegibilidade"]["partes_desconectadas"]


def regra_copia() -> dict[str, Any]:
    return canon()["etapa_0_elegibilidade"]["copia"]


def competencias() -> list[dict[str, Any]]:
    return canon()["competencias"]


def competencia(competencia_id: str) -> dict[str, Any]:
    for c in competencias():
        if c["id"] == competencia_id:
            return c
    raise KeyError(f"Competência desconhecida no canon: {competencia_id}")


def niveis(competencia_id: str) -> list[dict[str, Any]]:
    """6 níveis (0/40/80/120/160/200), do maior para o menor, como no canon."""
    return competencia(competencia_id)["niveis"]


def cap_tangenciamento(competencia_id: str) -> int | None:
    """Teto de pontos por tangenciamento (`TEMA-02`) para esta competência,
    ou `None` se o canon não define um cap para ela.

    Convenção de engenharia (AMB-07 — fonte silente sobre I e IV): o cap só
    é aplicado a II, III e V. I e IV nunca são limitadas por tangenciamento
    nesta implementação — leitura literal, não extensiva, da fonte.
    """
    cap = competencia(competencia_id).get("cap_por_tangenciamento") or {}
    valor = cap.get("pontos_maximos")
    if isinstance(valor, (int, float)):
        return int(valor)
    return None


def tema() -> dict[str, Any]:
    return canon()["tema"]


def tipo_textual() -> dict[str, Any]:
    return canon()["tipo_textual"]


def regra_titulo_redacao() -> dict[str, Any]:
    """Objeto `TITULO-01` — regra sobre título anulável de redação."""
    return canon()["titulo"]


def ambiguidades() -> list[dict[str, Any]]:
    return canon().get("ambiguidades", [])
