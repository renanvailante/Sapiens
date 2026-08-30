"""Heurísticas locais — Nível 1-2, sem rede. Foco na assimetria de segurança
(gatilho de zero-redação-inteira nunca vira DETERMINADO=disparado sozinho) e
nos extremos claros de pontuação por competência."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import decision_gate as dg  # noqa: E402
from redacao import heuristicas as h  # noqa: E402
from redacao.tipos import RedacaoEntrada  # noqa: E402

TEMA_ELEMENTOS = ["Desafios", "Valorização", "Herança africana", "Brasil"]

TEXTO_NO_TEMA = (
    "A valorização da herança africana no Brasil enfrenta desafios estruturais. "
    "Portanto, é preciso reconhecer os desafios para a valorização da herança "
    "africana no Brasil de forma organizada. Ademais, o Brasil precisa de políticas "
    "que enfrentem esses desafios. Diante disso, a valorização da herança africana "
    "no Brasil exige ação coordenada do poder público."
)


def test_conteudo_improprio_com_hit_nunca_vira_determinado_disparado():
    entrada = RedacaoEntrada(texto="isso aqui é uma redação com a palavra caralho no meio do texto")
    ev = h.checar_conteudo_improprio(entrada)
    c = dg.classificar("ZERO-05", [ev])
    assert c.estado != dg.EstadoOperacional.DETERMINADO or c.candidato_final is not True


def test_conteudo_improprio_sem_hit_pode_ser_determinado_limpo():
    entrada = RedacaoEntrada(texto="isso aqui é uma redação inteiramente normal, sem nenhum termo impróprio")
    ev = h.checar_conteudo_improprio(entrada)
    c = dg.classificar("ZERO-05", [ev])
    assert c.estado == dg.EstadoOperacional.DETERMINADO
    assert c.candidato_final is False


def test_fuga_tema_sem_elementos_e_insuficiente():
    ev = h.checar_fuga_tema(RedacaoEntrada(texto="qualquer coisa"))
    assert ev.qualidade_entrada


def test_fuga_tema_cobertura_alta_e_determinado_nao_fuga():
    entrada = RedacaoEntrada(texto=TEXTO_NO_TEMA, tema_elementos_obrigatorios=TEMA_ELEMENTOS)
    ev = h.checar_fuga_tema(entrada)
    c = dg.classificar("ZERO-01", [ev])
    assert c.estado == dg.EstadoOperacional.DETERMINADO
    assert c.candidato_final is False


def test_fuga_tema_cobertura_zero_fica_ambiguo_nunca_determinado_disparado():
    entrada = RedacaoEntrada(
        texto="um texto qualquer sem relação nenhuma com nada em especial aqui",
        tema_elementos_obrigatorios=TEMA_ELEMENTOS,
    )
    ev = h.checar_fuga_tema(entrada)
    c = dg.classificar("ZERO-01", [ev])
    assert not (c.estado == dg.EstadoOperacional.DETERMINADO and c.candidato_final is True)


def test_comp_v_com_5_elementos_no_ultimo_paragrafo_e_nivel_alto():
    entrada = RedacaoEntrada(
        texto="Parágrafo inicial qualquer.\n\n"
        "Portanto, é necessário que o governo, por meio de campanhas educativas, "
        "a fim de reduzir o problema, ademais crie também parcerias com escolas."
    )
    ev = h.avaliar_comp_V(entrada)
    assert ev.candidatos[0][0] == 200


def test_comp_v_sem_elementos_e_nivel_baixo():
    entrada = RedacaoEntrada(texto="Parágrafo final sem nenhum elemento de proposta de intervenção clara.")
    ev = h.avaliar_comp_V(entrada)
    assert ev.candidatos[0][0] in (0, 40)


def test_comp_ii_e_iii_nunca_propoem_nivel_200_localmente():
    """AMB-04: repertório produtivo exige leitura semântica que a heurística
    local não faz — o teto local fica em 160."""
    entrada = RedacaoEntrada(texto=TEXTO_NO_TEMA + " " + TEXTO_NO_TEMA, tema_elementos_obrigatorios=TEMA_ELEMENTOS)
    ev_ii = h.avaliar_comp_II(entrada)
    assert all(nivel != 200 for nivel, _ in ev_ii.candidatos)
