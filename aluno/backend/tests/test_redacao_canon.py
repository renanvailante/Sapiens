"""Canon do corretor de redação Enem — carregamento e acessores. Offline:
lê o JSON real do repo (é dado versionado, não precisa de mock)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from redacao import canon  # noqa: E402


def test_canon_carrega_com_5_competencias_e_versao():
    assert len(canon.competencias()) == 5
    assert canon.versao() == "1.0.1"


def test_11_gatilhos_zero_redacao_inteira_e_1_localizado():
    assert len(canon.gatilhos_zero_redacao_inteira()) == 11
    assert len(canon.gatilhos_zero_localizado()) == 1
    assert canon.gatilhos_zero_localizado()[0]["id"] == "DH-ZERO-01"


def test_cada_competencia_tem_6_niveis():
    for c in canon.competencias():
        assert len(canon.niveis(c["id"])) == 6
        pontos = {n["pontos"] for n in canon.niveis(c["id"])}
        assert pontos == {0, 40, 80, 120, 160, 200}


def test_cap_tangenciamento_so_para_II_III_V_nunca_I_IV():
    """Convenção de engenharia AMB-07: leitura literal, não extensiva."""
    assert canon.cap_tangenciamento("COMP-I") is None
    assert canon.cap_tangenciamento("COMP-IV") is None
    assert canon.cap_tangenciamento("COMP-II") == 40
    assert canon.cap_tangenciamento("COMP-III") == 40
    assert canon.cap_tangenciamento("COMP-V") == 40


def test_regra_titulo_redacao_contorna_a_chave_duplicada_do_json():
    """Ver docstring de `canon.py`: `data["titulo"]` colide no JSON-fonte;
    este acessor sempre devolve o objeto TITULO-01, nunca a string perdida."""
    regra = canon.regra_titulo_redacao()
    assert regra["id"] == "TITULO-01"


def test_canon_indisponivel_nao_derruba_processo(tmp_path, monkeypatch):
    monkeypatch.setenv("ENEM_CANON_PATH", str(tmp_path / "nao-existe.json"))
    with pytest.raises(canon.CanonIndisponivelError):
        canon.recarregar()
    monkeypatch.delenv("ENEM_CANON_PATH", raising=False)
    canon.recarregar()  # restaura o singleton para os demais testes do processo
