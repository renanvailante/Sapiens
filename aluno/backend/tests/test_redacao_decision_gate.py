"""Decision Gate — puramente lógica de combinação de evidências, sem
mockar Gemini nem nada de rede (o módulo não importa LLM algum)."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from decision_gate import EstadoOperacional, Evidencia, classificar  # noqa: E402


def test_sem_evidencia_e_insuficiente():
    c = classificar("X", [])
    assert c.estado == EstadoOperacional.INSUFICIENTE


def test_qualidade_entrada_sem_candidato_e_insuficiente_com_motivo():
    ev = Evidencia("X", "heuristica_local", qualidade_entrada="dado ausente")
    c = classificar("X", [ev])
    assert c.estado == EstadoOperacional.INSUFICIENTE
    assert "dado ausente" in c.motivo


def test_suporte_forte_unico_metodo_e_determinado():
    ev = Evidencia("X", "heuristica_local", candidatos=[(True, 2.0)], suporte_minimo_forte=1.0)
    c = classificar("X", [ev])
    assert c.estado == EstadoOperacional.DETERMINADO
    assert c.candidato_final is True


def test_suporte_fraco_unico_metodo_e_ambiguo():
    ev = Evidencia("X", "heuristica_local", candidatos=[(True, 0.3)], suporte_minimo_forte=1.0)
    c = classificar("X", [ev])
    assert c.estado == EstadoOperacional.AMBIGUO


def test_dois_metodos_concordam_e_determinado():
    e1 = Evidencia("X", "heuristica_local", candidatos=[(160, 0.4)], suporte_minimo_forte=1.0)
    e2 = Evidencia("X", "llm", candidatos=[(160, 1.5)], suporte_minimo_forte=1.0)
    c = classificar("X", [e1, e2])
    assert c.estado == EstadoOperacional.DETERMINADO
    assert c.candidato_final == 160


def test_dois_metodos_discordam_e_conflitante_nunca_decide_pelo_mais_severo():
    e1 = Evidencia("X", "heuristica_local", candidatos=[(False, 0.4)], suporte_minimo_forte=1.0)
    e2 = Evidencia("X", "llm", candidatos=[(True, 1.5)], suporte_minimo_forte=1.0)
    c = classificar("X", [e1, e2])
    assert c.estado == EstadoOperacional.CONFLITANTE
    assert c.candidato_final is None  # nunca assume o lado mais severo por padrão


def test_evidencias_ausentes_nao_bloqueia_determinado_quando_suporte_e_forte():
    """Uma heurística pode declarar limitação do método (ex.: 'não avalia
    registro') sem que isso, sozinho, force AMBIGUO — quem decide se uma
    ausência é bloqueante é o suporte que a própria evidência propõe."""
    ev = Evidencia(
        "COMP-I", "heuristica_local", candidatos=[(200, 1.5)],
        evidencias_ausentes=["registro não avaliado"], suporte_minimo_forte=1.0,
    )
    c = classificar("COMP-I", [ev])
    assert c.estado == EstadoOperacional.DETERMINADO
