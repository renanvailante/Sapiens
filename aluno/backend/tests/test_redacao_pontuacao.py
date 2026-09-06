"""`pontuacao.montar_resultado` — curto-circuito de zero-redação-inteira,
DH-ZERO-01 localizado, cap de tangenciamento (AMB-07: só II/III/V). Entrada
sintética (Classificacao construída à mão) — não depende de heurística real
nem de LLM."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import decision_gate as dg  # noqa: E402
from redacao import avaliador_local as av  # noqa: E402
from redacao import pontuacao  # noqa: E402


def _limpo(item_id: str) -> dg.Classificacao:
    ev = dg.Evidencia(item_id, "heuristica_local", candidatos=[(False, 2.0)], suporte_minimo_forte=1.0)
    return dg.classificar(item_id, [ev])


def _disparado(item_id: str) -> dg.Classificacao:
    ev = dg.Evidencia(item_id, "llm", candidatos=[(True, 1.5)], suporte_minimo_forte=1.0)
    return dg.classificar(item_id, [ev])


def _nivel(item_id: str, pontos: int) -> dg.Classificacao:
    ev = dg.Evidencia(item_id, "heuristica_local", candidatos=[(pontos, 2.0)], suporte_minimo_forte=1.0)
    return dg.classificar(item_id, [ev])


def _base_limpa() -> dict[str, dg.Classificacao]:
    classificacoes = {item_id: _limpo(item_id) for item_id in av.GATILHOS_ZERO_REDACAO_INTEIRA}
    classificacoes["DH-ZERO-01"] = _limpo("DH-ZERO-01")
    classificacoes["TEMA-02"] = _limpo("TEMA-02")
    classificacoes["COPIA-02"] = _limpo("COPIA-02")
    for comp_id in av.COMPETENCIAS:
        classificacoes[comp_id] = _nivel(comp_id, 160)
    return classificacoes


def test_gatilho_zero_redacao_inteira_zera_tudo_e_nao_avalia_competencias():
    classificacoes = _base_limpa()
    classificacoes["ZERO-01"] = _disparado("ZERO-01")
    resultado = pontuacao.montar_resultado(classificacoes)
    assert resultado["estado_geral"] == "ANULADA"
    assert resultado["nota_total"] == 0
    assert resultado["competencias"] == []


def test_dh_zero_01_zera_so_competencia_v():
    classificacoes = _base_limpa()
    classificacoes["DH-ZERO-01"] = _disparado("DH-ZERO-01")
    resultado = pontuacao.montar_resultado(classificacoes)
    assert resultado["estado_geral"] == "AVALIAVEL"
    comp_v = next(c for c in resultado["competencias"] if c["id"] == "COMP-V")
    assert comp_v["nivel_pontos"] == 0
    outras = [c for c in resultado["competencias"] if c["id"] != "COMP-V"]
    assert all(c["nivel_pontos"] == 160 for c in outras)
    assert resultado["nota_total"] == 160 * 4


def test_texto_limpo_soma_as_5_competencias():
    resultado = pontuacao.montar_resultado(_base_limpa())
    assert resultado["estado_geral"] == "AVALIAVEL"
    assert resultado["nota_total"] == 160 * 5


def test_tangenciamento_capa_so_ii_iii_v_nunca_i_iv():
    classificacoes = _base_limpa()
    classificacoes["TEMA-02"] = _disparado("TEMA-02")
    for comp_id in av.COMPETENCIAS:
        classificacoes[comp_id] = _nivel(comp_id, 200)
    resultado = pontuacao.montar_resultado(classificacoes)
    por_id = {c["id"]: c for c in resultado["competencias"]}
    assert por_id["COMP-I"]["nivel_pontos"] == 200 and por_id["COMP-I"]["cap_aplicado"] is None
    assert por_id["COMP-IV"]["nivel_pontos"] == 200 and por_id["COMP-IV"]["cap_aplicado"] is None
    for comp_id in ("COMP-II", "COMP-III", "COMP-V"):
        assert por_id[comp_id]["nivel_pontos"] == 40
        assert por_id[comp_id]["cap_aplicado"] == 40


def test_item_conflitante_nao_zera_e_marca_revisao_humana():
    classificacoes = _base_limpa()
    conflito = dg.classificar("ZERO-05", [
        dg.Evidencia("ZERO-05", "heuristica_local", candidatos=[(False, 0.3)], suporte_minimo_forte=1.0),
        dg.Evidencia("ZERO-05", "llm", candidatos=[(True, 1.5)], suporte_minimo_forte=1.0),
    ])
    classificacoes["ZERO-05"] = conflito
    resultado = pontuacao.montar_resultado(classificacoes)
    assert resultado["estado_geral"] == "AVALIAVEL"  # nunca zera por conflito não resolvido
    assert resultado["necessita_revisao_humana"] is True
    assert "ZERO-05" in resultado["itens_para_revisao"]


def _ambiguo(item_id: str, pontos: int) -> dg.Classificacao:
    """Candidato existe, mas o suporte local não alcança o mínimo — é o estado
    mais comum das competências numa correção real."""
    ev = dg.Evidencia(item_id, "heuristica_local", candidatos=[(pontos, 0.4)], suporte_minimo_forte=1.0)
    return dg.classificar(item_id, [ev])


def test_competencia_nao_confirmada_entra_na_nota_como_estimativa():
    """A soma antiga era `nivel if confirmado else 0`: uma competência AMBIGUA
    virava zero na nota, e uma redação boa saía com 560/1000 sem nada na tela
    explicando o buraco. `AMBIGUO` significa "o método não fechou", nunca "o
    aluno tirou zero"."""
    classificacoes = _base_limpa()
    classificacoes["COMP-I"] = _ambiguo("COMP-I", 160)
    resultado = pontuacao.montar_resultado(classificacoes)

    comp_i = next(c for c in resultado["competencias"] if c["id"] == "COMP-I")
    assert comp_i["nivel_pontos"] == 160
    assert comp_i["confirmado"] is False
    assert resultado["nota_total"] == 800
    assert resultado["nota_pontos_estimados"] == 160
    assert "COMP-I" in resultado["itens_para_revisao"]


def test_nota_total_sempre_bate_com_a_soma_das_competencias_mostradas():
    """Invariante de tela: o aluno soma as cinco barras e tem que chegar na
    nota grande. Qualquer divergência aqui é a nota mentindo para ele."""
    classificacoes = _base_limpa()
    classificacoes["COMP-II"] = _ambiguo("COMP-II", 120)
    classificacoes["COMP-V"] = _ambiguo("COMP-V", 80)
    resultado = pontuacao.montar_resultado(classificacoes)
    assert resultado["nota_total"] == sum(c["nivel_pontos"] for c in resultado["competencias"])


def test_zero_decidido_continua_zerando():
    """O único zero que a nota respeita é zero DECIDIDO — afrouxar a soma não
    pode afrouxar `DH-ZERO-01`."""
    classificacoes = _base_limpa()
    classificacoes["DH-ZERO-01"] = _disparado("DH-ZERO-01")
    resultado = pontuacao.montar_resultado(classificacoes)
    comp_v = next(c for c in resultado["competencias"] if c["id"] == "COMP-V")
    assert comp_v["nivel_pontos"] == 0
    assert comp_v["confirmado"] is True
    assert resultado["nota_total"] == 640
