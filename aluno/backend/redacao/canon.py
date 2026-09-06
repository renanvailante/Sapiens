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


def _candidatos() -> list[Path]:
    """Todos os lugares onde o canon pode estar, em ordem de preferência.

    Existe uma lista (e não um caminho único) porque o arquivo mora em dois
    layouts diferentes e incompatíveis:

      * ÁRVORE DO REPO — `pipeline/docs/enem-redacao/`, quatro níveis acima
        deste arquivo. É o que vale em desenvolvimento e nos testes.
      * IMAGEM DE PRODUÇÃO — o Dockerfile copia só `aluno/backend/` para
        `/app` mais três arquivos de `pipeline/` para `/app/contracts/`. Não
        existe `pipeline/` dentro do contêiner, e `/app/redacao/canon.py` tem
        apenas TRÊS ancestrais (`/app/redacao`, `/app`, `/`) — a versão antiga
        deste módulo indexava `parents[3]` e estourava `IndexError` antes
        mesmo de tentar abrir arquivo nenhum. Como `_carregar` só trata
        `FileNotFoundError`/`JSONDecodeError`, o erro subia cru e a rota de
        redação respondia 500 em TODA submissão em produção — nunca o 503
        "corretor indisponível" que o código pretendia dar.

    `ENEM_CANON_PATH`, quando definido, vem primeiro e sozinho decide.
    """
    override = os.environ.get("ENEM_CANON_PATH")
    if override:
        return [Path(override)]

    caminhos: list[Path] = []
    contracts = os.environ.get("SAPIENS_CONTRACTS_PATH")
    if contracts:
        caminhos.append(Path(contracts) / "enem-redacao" / _ARQUIVO_PADRAO)

    aqui = Path(__file__).resolve()
    for ancestral in aqui.parents:
        caminhos.append(ancestral / "pipeline" / "docs" / "enem-redacao" / _ARQUIVO_PADRAO)
        caminhos.append(ancestral / "contracts" / "enem-redacao" / _ARQUIVO_PADRAO)
    return caminhos


def _caminho_canon() -> Path:
    """O primeiro candidato que existe — ou o primeiro da lista, para que a
    mensagem de erro cite um caminho concreto em vez de sumir."""
    candidatos = _candidatos()
    for caminho in candidatos:
        if caminho.is_file():
            return caminho
    return candidatos[0]


_CANON: dict[str, Any] | None = None


def _carregar() -> dict[str, Any]:
    caminho = _caminho_canon()
    try:
        with caminho.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        procurados = ", ".join(str(c) for c in _candidatos()[:6])
        raise CanonIndisponivelError(
            f"Canon do Enem não encontrado em {caminho} (procurado em: {procurados})"
        ) from exc
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
