"""A régua do Mapa de Habilidades.

O que este arquivo existe para impedir: o mapa voltar a dizer "Dominado" para
quem respondeu meia dúzia de questões. A escala antiga era COBERTURA (processos
tocados sobre processos do domínio), e um domínio com três processos ficava
"coberto" — 80%+ — na primeira rodada. A âncora abaixo é o contrato do produto:
80% de exibição exige 40 acertos NAQUELE eixo.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cosmetic_skills_map as mapa  # noqa: E402


def _pct(hexagon, hub_id):
    return next(h["mastery"] for h in hexagon if h["hub"] == hub_id) * 100


def test_ancora_quarenta_acertos_vale_oitenta_por_cento():
    hexagon = mapa.compute_hexagon({"1": {"respondidas": 40, "acertos": 40}})
    assert round(_pct(hexagon, 1)) == 80


def test_punhado_de_questoes_nao_chega_perto_de_dominado():
    """O caso que motivou a recalibração: 3 e 5 acertos exibiam ~80%."""
    for acertos, teto in ((3, 20), (5, 25), (10, 40)):
        hexagon = mapa.compute_hexagon({"1": {"respondidas": acertos, "acertos": acertos}})
        assert _pct(hexagon, 1) < teto, f"{acertos} acertos exibindo {_pct(hexagon, 1):.1f}%"


def test_faixas_intermediarias_exigem_volume():
    """As faixas de `frontend/src/lib/dominio.js` lidas em número de acertos:
    Familiar (30) e Proficiente (55) também deixam de ser de graça."""
    def acertos_para(alvo):
        return next(n for n in range(0, 500) if mapa.mastery_por_acertos(n) * 100 >= alvo)

    assert acertos_para(30) >= 8
    assert acertos_para(55) >= 18
    assert acertos_para(80) == 40


def test_curva_e_monotonica_e_respeita_o_teto():
    anterior = -1.0
    for n in range(0, 2000, 7):
        atual = mapa.mastery_por_acertos(n)
        assert atual >= anterior
        assert atual <= mapa.MASTERY_CEILING
        anterior = atual
    assert mapa.mastery_por_acertos(0) == 0.0
    # 100 acertos num eixo ainda não é o teto: o teto é assintótico, não uma
    # meta alcançável por volume.
    assert mapa.mastery_por_acertos(100) < mapa.MASTERY_CEILING


def test_erro_nao_desconta_mas_tambem_nao_soma():
    """A régua é volume de acerto. Responder muito e errar muito não sobe o
    mapa; e não é taxa de acerto, senão 4/4 valeria mais que 39/40."""
    muitos_erros = mapa.compute_hexagon({"1": {"respondidas": 200, "acertos": 10}})
    poucas_certas = mapa.compute_hexagon({"1": {"respondidas": 10, "acertos": 10}})
    assert _pct(muitos_erros, 1) == _pct(poucas_certas, 1)
    assert _pct(mapa.compute_hexagon({"1": {"respondidas": 4, "acertos": 4}}), 1) < _pct(
        mapa.compute_hexagon({"1": {"respondidas": 40, "acertos": 39}}), 1
    )


def test_eixo_sem_acerto_fica_zerado_do_vertice_a_folha():
    hexagon = mapa.compute_hexagon({})
    assert all(h["mastery"] == 0.0 for h in hexagon)
    arvore = mapa.build_hub_tree("aluno-x", hexagon)
    folhas = [f["percent"] for h in arvore for b in h["branches"] for f in b["leaves"]]
    assert folhas and all(p == 0.0 for p in folhas), "eixo não explorado exibindo folha com percentual"


def test_folha_nunca_promete_mais_que_o_proprio_eixo():
    hexagon = mapa.compute_hexagon({"1": {"respondidas": 40, "acertos": 40}})
    arvore = mapa.build_hub_tree("aluno-x", hexagon)
    hub = next(h for h in arvore if h["hub"] == 1)
    for branch in hub["branches"]:
        for folha in branch["leaves"]:
            assert 0 < folha["percent"] <= hub["mastery"]


def test_chave_do_hub_serve_como_int_ou_string():
    """O agregado passa pelo cache do Mongo, que só guarda chave string."""
    por_string = mapa.compute_hexagon({"3": {"respondidas": 40, "acertos": 40}})
    por_int = mapa.compute_hexagon({3: {"respondidas": 40, "acertos": 40}})
    assert _pct(por_string, 3) == _pct(por_int, 3) == 80


def test_snapshot_antigo_volta_zerado_e_sinalizado():
    """Hexágono gravado na escala de cobertura não tem `acertos` — não dá para
    converter, e exibi-lo seria manter a mentira que esta escala veio remover."""
    legado = [{"hub": 1, "label": "Raciocínio Numérico", "mastery": 0.8741}]
    reescalado, escala_antiga = mapa.rescale_hexagon(legado)
    assert escala_antiga is True
    assert reescalado[0]["mastery"] == 0.0


def test_snapshot_novo_e_reescalado_sem_reler_nada():
    """Contagem gravada no snapshot é o que permite trocar a régua depois."""
    gravado = mapa.compute_hexagon({"2": {"respondidas": 50, "acertos": 40}})
    reescalado, escala_antiga = mapa.rescale_hexagon(gravado)
    assert escala_antiga is False
    assert round(_pct(reescalado, 2)) == 80


def test_feedback_usa_contagem_por_eixo_e_exige_amostra():
    rodadas = [{"total": 10, "acertos": 8, "percentual_acerto": 80.0, "padroes_de_erro": []}]
    poucas = mapa.compute_feedback(rodadas, {"1": {"respondidas": 5, "acertos": 5}})
    assert poucas["pontos_fortes"] == [], "ponto forte declarado com 5 questões"
    muitas = mapa.compute_feedback(rodadas, {"1": {"respondidas": 40, "acertos": 30}})
    assert muitas["pontos_fortes"][0]["accuracy"] == 75.0


def test_indice_inverso_cobre_todo_dominio_do_mapa():
    """Domínio fora do índice some da contagem sem ninguém notar."""
    for hub_id, dom_ids in mapa.HUB_DOMAIN_MAP.items():
        for dom_id in dom_ids:
            assert mapa.DOMAIN_TO_HUB[dom_id] == hub_id
