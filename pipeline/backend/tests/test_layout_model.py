"""Modelo de layout — o que substitui `_detect_column_split`.

O caso que motiva este módulo: em 3 das 15 páginas do bloco 136-180 do caderno
de 2022 há uma questão só na página, a heurística antiga não encontra dois
marcadores "QUESTÃO N", devolve `split=None`, e a ordem de leitura passa a
intercalar as duas colunas linha a linha. Estes testes fixam que a detecção por
densidade de glifos não tem esse ponto cego.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import layout_model as lm  # noqa: E402

PDF_2022 = (BACKEND / "_storage/sapiens-cognitive/questions"
            / "6b1c29d5-033e-4a20-9149-64e3179e6d5e/book/2022_PV_impresso_D2_CD5.pdf")

pytestmark = pytest.mark.skipif(
    not PDF_2022.is_file(),
    reason="caderno de 2022 ausente do storage local",
)


@pytest.fixture(scope="module")
def caderno():
    import pymupdf
    doc = pymupdf.open(str(PDF_2022))
    modelos = lm.modelo_documento(doc)
    regioes = lm.regioes_por_questao(doc, modelos)
    yield doc, modelos, regioes
    doc.close()


def test_toda_pagina_tem_duas_colunas(caderno):
    _, modelos, _ = caderno
    largura_unica = {round(m.largura) for m in modelos.values()}
    assert largura_unica == {567}, "o caderno tem largura constante"
    duas = sum(1 for m in modelos.values() if len(m.colunas) == 2)
    assert duas >= 31, f"apenas {duas}/32 páginas com 2 colunas"


def test_calha_e_constante(caderno):
    _, modelos, _ = caderno
    centros = [(m.calhas[0][0] + m.calhas[0][1]) / 2 for m in modelos.values() if m.calhas]
    assert centros, "nenhuma calha detectada"
    assert max(centros) - min(centros) < 12, "a calha deveria ser rigidamente constante"


@pytest.mark.parametrize("pagina_humana,questao", [(25, 163), (28, 171), (30, 177)])
def test_paginas_de_questao_unica_tem_coluna(caderno, pagina_humana, questao):
    """As três páginas em que `_detect_column_split` devolvia `None`."""
    _, modelos, regioes = caderno
    modelo = modelos[pagina_humana - 1]
    assert len(modelo.colunas) == 2
    assert questao in regioes
    assert any(r.pagina == pagina_humana - 1 for r in regioes[questao])


def test_todas_as_90_questoes_tem_regiao(caderno):
    _, _, regioes = caderno
    faltando = [n for n in range(91, 181) if n not in regioes]
    assert not faltando, f"sem região: {faltando}"


def test_regiao_nao_vaza_para_o_rodape(caderno):
    """Uma região que se estica até o rodapé sobrepõe a questão seguinte — foi
    o que fez a checagem de invasão acusar recortes que o olho humano aprovou."""
    _, modelos, regioes = caderno
    for numero, lista in regioes.items():
        for r in lista:
            altura = modelos[r.pagina].altura
            assert r.y1 <= altura, f"Q{numero} ultrapassa a página"
            assert r.y1 > r.y0, f"Q{numero} com região degenerada"


def test_marca_dagua_detectada_antes_da_calha(caderno):
    """A marca d'água ladrilhada atravessa a calha: sem removê-la da projeção,
    nenhuma faixa de x fica vazia e a detecção de coluna nunca funciona."""
    _, modelos, _ = caderno
    total = sum(len(m.marca_dagua) for m in modelos.values())
    assert total > 1000, "o caderno de 2022 é fortemente ladrilhado"
    por_densidade = sum(1 for m in modelos.values() if m.metodo == "densidade_glifos")
    assert por_densidade >= 20, (
        f"só {por_densidade}/32 páginas resolvidas por densidade — a marca "
        "d'água provavelmente voltou a poluir a projeção"
    )


def test_coluna_de_rejeita_intervalo_que_cruza_a_calha(caderno):
    _, modelos, _ = caderno
    modelo = next(m for m in modelos.values() if m.calhas)
    c0, c1 = modelo.calhas[0]
    assert modelo.coluna_de(c0 - 50, c1 + 50) is None
    assert modelo.coluna_de(20, c0 - 5) == 0
