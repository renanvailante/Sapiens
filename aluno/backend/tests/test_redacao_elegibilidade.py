"""Etapa 0 mecânica — só ZERO-03/04/07/08/09, sem rede, sem heurística
estatística de fronteira (essas ficam em test_redacao_heuristicas.py)."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from redacao import elegibilidade  # noqa: E402
from redacao.tipos import RedacaoEntrada  # noqa: E402

TEXTO_PT_LONGO = " ".join(["isso é um texto normal em português com muitas palavras comuns"] * 5)


def test_texto_em_branco_dispara_zero_03():
    ev = elegibilidade.checar_texto_em_branco(RedacaoEntrada(texto="   "))
    assert ev.candidatos == [(True, 1.0)]


def test_texto_presente_nao_dispara_zero_03():
    ev = elegibilidade.checar_texto_em_branco(RedacaoEntrada(texto="algo"))
    assert ev.candidatos == [(False, 1.0)]


def test_zero_04_sem_linhas_manuscritas_fica_insuficiente():
    ev = elegibilidade.checar_texto_insuficiente(RedacaoEntrada(texto="x"))
    assert ev.candidatos == []
    assert ev.qualidade_entrada


def test_zero_04_ate_7_linhas_dispara_amb01():
    ev = elegibilidade.checar_texto_insuficiente(RedacaoEntrada(texto="x", linhas_manuscritas=7))
    assert ev.candidatos == [(True, 1.0)]


def test_zero_04_8_linhas_nao_dispara_amb01():
    ev = elegibilidade.checar_texto_insuficiente(RedacaoEntrada(texto="x", linhas_manuscritas=8))
    assert ev.candidatos == [(False, 1.0)]


def test_zero_08_texto_curto_demais_fica_insuficiente():
    ev = elegibilidade.checar_lingua_estrangeira(RedacaoEntrada(texto="poucas palavras aqui"))
    assert ev.candidatos == []
    assert ev.qualidade_entrada


def test_zero_08_texto_em_portugues_nao_dispara():
    ev = elegibilidade.checar_lingua_estrangeira(RedacaoEntrada(texto=TEXTO_PT_LONGO))
    assert ev.candidatos[0][0] is False


def test_zero_08_texto_em_ingles_dispara():
    texto_en = " ".join(["this is an english text with the and of to in that many common words"] * 4)
    ev = elegibilidade.checar_lingua_estrangeira(RedacaoEntrada(texto=texto_en))
    assert ev.candidatos[0][0] is True


def test_zero_07_e_zero_09_inaplicaveis_a_texto_digital():
    entrada = RedacaoEntrada(texto="qualquer coisa")
    assert elegibilidade.checar_identificacao_fora_local(entrada).candidatos == [(False, 10.0)]
    assert elegibilidade.checar_texto_ilegivel(entrada).candidatos == [(False, 10.0)]


def test_avaliar_mecanico_devolve_os_5_itens():
    resultado = elegibilidade.avaliar_mecanico(RedacaoEntrada(texto=TEXTO_PT_LONGO))
    assert set(resultado.keys()) == {"ZERO-03", "ZERO-04", "ZERO-07", "ZERO-08", "ZERO-09"}
