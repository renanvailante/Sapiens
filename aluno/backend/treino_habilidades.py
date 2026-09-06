"""Carrega e serve o banco canônico de questões de treino, uma base de 4-5
questões por habilidade observável (`HAB-01`..`HAB-56`, ver
`pipeline/docs/treino-habilidades/README.md`).

Local-first, sem IA, sem Firestore `itens`/Mongo `questoes_public`: é um
corpus autoral próprio, versionado à parte do acervo Enem. Este módulo só
LÊ o banco; nunca o reescreve.

Resolução de caminho no mesmo padrão de `redacao/canon.py` (mesma classe de
bug já custou dois incidentes de produção: `IndexError` por contar níveis
de diretório errado, ou arquivo nunca copiado para a imagem Docker). Ver
`Dockerfile` (`TREINO_HABILIDADES_PATH`) e
`tests/test_prontidao_producao.py`.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("sapiens.treino_habilidades")

_ARQUIVO_PADRAO = "banco_treino_habilidades_v1.json"

ONTOLOGY_VERSION_TREINO = "treino-habilidades-1.0"
CUSTO_POR_QUESTAO_NOVA = 3


class BancoTreinoIndisponivelError(RuntimeError):
    """O banco de treino não pôde ser carregado — ausente, ilegível ou JSON
    inválido. Nunca derruba o boot do app: só a rota de treino vira 503."""


def _candidatos() -> list[Path]:
    override = os.environ.get("TREINO_HABILIDADES_PATH")
    if override:
        return [Path(override)]

    caminhos: list[Path] = []
    contracts = os.environ.get("SAPIENS_CONTRACTS_PATH")
    if contracts:
        caminhos.append(Path(contracts) / "treino-habilidades" / _ARQUIVO_PADRAO)

    aqui = Path(__file__).resolve()
    for ancestral in aqui.parents:
        caminhos.append(ancestral / "pipeline" / "docs" / "treino-habilidades" / _ARQUIVO_PADRAO)
        caminhos.append(ancestral / "contracts" / "treino-habilidades" / _ARQUIVO_PADRAO)
    return caminhos


def _caminho_banco() -> Path:
    for caminho in _candidatos():
        if caminho.is_file():
            return caminho
    return _candidatos()[0]


_BANCO: dict[str, Any] | None = None
_POR_HAB: dict[str, dict[str, Any]] | None = None


def _carregar() -> dict[str, Any]:
    caminho = _caminho_banco()
    try:
        with caminho.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        procurados = ", ".join(str(c) for c in _candidatos()[:6])
        raise BancoTreinoIndisponivelError(
            f"Banco de treino não encontrado em {caminho} (procurado em: {procurados})"
        ) from exc
    except json.JSONDecodeError as exc:
        raise BancoTreinoIndisponivelError(f"Banco de treino em {caminho} não é JSON válido: {exc}") from exc
    habilidades = data.get("habilidades")
    if not isinstance(habilidades, list) or len(habilidades) != 56:
        raise BancoTreinoIndisponivelError(
            f"Banco de treino carregado, mas com {len(habilidades) if isinstance(habilidades, list) else '?'} "
            "habilidades em vez de 56."
        )
    return data


def banco() -> dict[str, Any]:
    """Singleton em memória, carregado sob demanda (lazy) na 1ª chamada."""
    global _BANCO, _POR_HAB
    if _BANCO is None:
        _BANCO = _carregar()
        _POR_HAB = {h["hab_id"]: h for h in _BANCO["habilidades"]}
        logger.info("Banco de treino carregado: %d habilidades.", len(_BANCO["habilidades"]))
    return _BANCO


def recarregar() -> dict[str, Any]:
    """Força releitura do arquivo — usado por testes que trocam `TREINO_HABILIDADES_PATH`."""
    global _BANCO, _POR_HAB
    _BANCO = None
    _POR_HAB = None
    return banco()


def _habilidade(hab_id: str) -> dict[str, Any]:
    banco()
    assert _POR_HAB is not None
    h = _POR_HAB.get(hab_id)
    if h is None:
        raise KeyError(f"habilidade desconhecida: {hab_id}")
    return h


def listar_habilidades() -> list[dict[str, Any]]:
    """`[{hab_id, nome, total_base}]`, na ordem canônica HAB-01..HAB-56."""
    return [
        {"hab_id": h["hab_id"], "nome": h["nome"], "total_base": len(h["questoes"])}
        for h in banco()["habilidades"]
    ]


def _sem_gabarito(questao: dict[str, Any]) -> dict[str, Any]:
    """Projeção enviada ANTES de o aluno responder — nunca inclui gabarito
    nem elucidação (que entrega a resposta)."""
    return {
        "indice": questao["indice"],
        "dificuldade": questao["dificuldade"],
        "enunciado_antes": questao["enunciado_antes"],
        "tabela": questao["tabela"],
        "enunciado_depois": questao["enunciado_depois"],
        "alternativas": questao["alternativas"],
    }


def obter_base(hab_id: str) -> dict[str, Any]:
    """Questões-base da habilidade (sem gabarito) — o que abre ao clicar
    num balão."""
    h = _habilidade(hab_id)
    return {
        "hab_id": h["hab_id"],
        "nome": h["nome"],
        "questoes": [_sem_gabarito(q) for q in h["questoes"]],
    }


def checar_resposta(hab_id: str, indice: int, alternativa: str) -> dict[str, Any]:
    """Corrige localmente — nunca confia no `acertou` do cliente. Uma
    habilidade com gabarito de mais de uma letra (caso real, ver
    `HAB-27` questão 2, conjunto bimodal) conta como acerto se o aluno
    marcou QUALQUER uma das letras corretas."""
    h = _habilidade(hab_id)
    questao = next((q for q in h["questoes"] if q["indice"] == indice), None)
    if questao is None:
        raise KeyError(f"questão {indice} não existe em {hab_id}")
    letras_validas = {a["letra"] for a in questao["alternativas"]}
    if alternativa not in letras_validas:
        raise ValueError(f"alternativa {alternativa!r} não existe nesta questão")
    acertou = alternativa in questao["gabarito"]
    return {
        "acertou": acertou,
        "gabarito": questao["gabarito"],
        "elucidacao": questao["elucidacao"],
    }


DIFICULDADES_VALIDAS = ("FACIL", "MEDIO_FACIL", "MEDIO", "DIFICIL")
