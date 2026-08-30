"""Cerco de circulação (saneamento do corpus, 2026-08-26).

O que estes testes protegem: o cerco precisa ser um filtro *inerte* quando
desligado. Se `circulacao.aplicar` alterasse o filtro recebido — ou vazasse um
`$nin` vazio — todo endpoint de questão do aluno mudaria de comportamento
mesmo com o saneamento encerrado.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import circulacao  # noqa: E402

Q1 = "ITEM-ENEM-2022-AMARELO-Q136"
Q2 = "ITEM-ENEM-2024-AMARELO-Q102"


@pytest.fixture(autouse=True)
def _limpar_ambiente(monkeypatch):
    monkeypatch.delenv("SANEAMENTO_BLOQUEADOS", raising=False)
    monkeypatch.delenv("SANEAMENTO_BLOQUEADOS_PATH", raising=False)
    circulacao.recarregar()
    yield
    circulacao.recarregar()


def test_desligado_por_padrao():
    assert circulacao.bloqueados() == frozenset()
    assert circulacao.ativo() is False


def test_filtro_inalterado_quando_desligado():
    filtro = {"fonte.ano": 2022}
    assert circulacao.aplicar(filtro) == {"fonte.ano": 2022}
    assert "item_id" not in circulacao.aplicar({})


def test_lista_por_variavel(monkeypatch):
    monkeypatch.setenv("SANEAMENTO_BLOQUEADOS", f"{Q1}, {Q2}")
    circulacao.recarregar()
    assert circulacao.bloqueados() == frozenset({Q1, Q2})
    assert circulacao.esta_bloqueado(Q1) is True
    assert circulacao.esta_bloqueado("ITEM-ENEM-2022-AMARELO-Q137") is False


def test_arquivo_do_auditor(tmp_path, monkeypatch):
    p = tmp_path / "bloqueados.json"
    p.write_text(json.dumps({"total": 2, "item_ids": [Q1, Q2]}), encoding="utf-8")
    monkeypatch.setenv("SANEAMENTO_BLOQUEADOS_PATH", str(p))
    circulacao.recarregar()
    assert circulacao.bloqueados() == frozenset({Q1, Q2})


def test_arquivo_lista_crua(tmp_path, monkeypatch):
    p = tmp_path / "bloqueados.json"
    p.write_text(json.dumps([Q1]), encoding="utf-8")
    monkeypatch.setenv("SANEAMENTO_BLOQUEADOS_PATH", str(p))
    circulacao.recarregar()
    assert circulacao.bloqueados() == frozenset({Q1})


def test_arquivo_ausente_nao_derruba(tmp_path, monkeypatch):
    monkeypatch.setenv("SANEAMENTO_BLOQUEADOS_PATH", str(tmp_path / "nao-existe.json"))
    circulacao.recarregar()
    assert circulacao.bloqueados() == frozenset()
    assert circulacao.aplicar({"a": 1}) == {"a": 1}


def test_arquivo_corrompido_nao_derruba(tmp_path, monkeypatch):
    p = tmp_path / "bloqueados.json"
    p.write_text("{isto não é json", encoding="utf-8")
    monkeypatch.setenv("SANEAMENTO_BLOQUEADOS_PATH", str(p))
    circulacao.recarregar()
    assert circulacao.bloqueados() == frozenset()


def test_aplicar_nao_muta_o_filtro_original(monkeypatch):
    monkeypatch.setenv("SANEAMENTO_BLOQUEADOS", Q1)
    circulacao.recarregar()
    original = {"fonte.ano": 2022}
    saida = circulacao.aplicar(original)
    assert original == {"fonte.ano": 2022}
    assert saida["item_id"] == {"$nin": [Q1]}
    assert saida["fonte.ano"] == 2022


def test_item_id_vazio_nunca_bloqueia(monkeypatch):
    monkeypatch.setenv("SANEAMENTO_BLOQUEADOS", Q1)
    circulacao.recarregar()
    assert circulacao.esta_bloqueado(None) is False
    assert circulacao.esta_bloqueado("") is False
