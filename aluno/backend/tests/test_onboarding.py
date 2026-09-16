"""O primeiro acesso: o que o aluno declara, e o que o produto faz com isso.

A régua destes testes não é "o formulário salva". É que a declaração tem
consequência REAL e limitada:

  * o tempo que ele diz ter vira a janela do Cronograma na hora;
  * a dificuldade que ele declara muda a ordem das frentes **enquanto não há
    medida** — e some assim que houver;
  * opinião nunca sobrescreve contagem.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import onboarding_routes as ob  # noqa: E402
import prioridade_enem as pe  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user(uid="aluno-1"):
    return User(user_id=uid, email=f"{uid}@x.com", name="Aluno Teste")


@pytest.fixture(autouse=True)
def _sem_firestore(monkeypatch):
    """`concluido: true` escreve o flag no Firestore. Aqui não há Firestore —
    e o contrato é justamente que essa falha não derruba o salvamento."""
    monkeypatch.setattr(ob.fs, "write_student_behavior", lambda *a, **k: None)


@pytest.fixture
def db(fake_db):
    ob.set_db(fake_db)
    yield fake_db
    ob.set_db(None)


# ---------------------------------------------------------------------------
# Salvamento parcial
# ---------------------------------------------------------------------------


def test_etapa_salva_sozinha_e_nao_apaga_a_anterior(db):
    _run(ob.salvar_onboarding(
        ob.OnboardingPayload(dificuldades=ob.DificuldadesPayload(matematica=9)), user=_user()
    ))
    depois = _run(ob.salvar_onboarding(
        ob.OnboardingPayload(dificuldades=ob.DificuldadesPayload(redacao=2)), user=_user()
    ))
    # Fechar o navegador entre as etapas não pode custar o que já foi respondido.
    assert depois["dificuldades"]["matematica"] == 9
    assert depois["dificuldades"]["redacao"] == 2
    assert depois["dificuldades"]["humanas"] is None
    assert depois["concluido"] is False


def test_tempo_fora_do_catalogo_e_recusado(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _run(ob.salvar_onboarding(ob.OnboardingPayload(minutos_por_dia=45), user=_user()))
    assert exc.value.status_code == 422


def test_meta_vem_expandida_em_acertos(db):
    saida = _run(ob.salvar_onboarding(ob.OnboardingPayload(meta="avancado"), user=_user()))
    assert saida["meta"]["acertos_min"] == 160
    assert saida["meta"]["acertos_max"] == 180
    assert saida["meta"]["rotulo"] == "Avançado"


# ---------------------------------------------------------------------------
# A consequência: a semana do aluno
# ---------------------------------------------------------------------------


def test_tempo_declarado_vira_a_janela_do_cronograma(db):
    _run(ob.salvar_onboarding(ob.OnboardingPayload(minutos_por_dia=120), user=_user()))
    doc = _run(db.cronogramas.find_one({"_id": "aluno-1"}))
    prefs = doc["preferencias"]
    assert prefs["blocos_por_dia"] == 3
    assert prefs["bloco_minutos"] == 40
    # E continua sendo uma preferência VÁLIDA para o motor, não um dicionário solto.
    assert prefs["dias_de_folga"] == [6]


def test_dez_minutos_viram_o_menor_bloco_que_o_motor_aceita(db):
    _run(ob.salvar_onboarding(ob.OnboardingPayload(minutos_por_dia=10), user=_user()))
    prefs = _run(db.cronogramas.find_one({"_id": "aluno-1"}))["preferencias"]
    assert prefs["bloco_minutos"] == 20  # `cronograma._BLOCO_MIN`
    assert prefs["blocos_por_dia"] == 1


# ---------------------------------------------------------------------------
# A consequência: a ordem das frentes
# ---------------------------------------------------------------------------


def test_dificuldade_declarada_vira_frente_de_prioridade(db):
    _run(ob.salvar_onboarding(
        ob.OnboardingPayload(dificuldades=ob.DificuldadesPayload(natureza=10, matematica=0)),
        user=_user(),
    ))
    frentes = _run(ob.dificuldade_por_frente("aluno-1"))
    # "Natureza" na tela do aluno são QUATRO frentes no motor.
    assert frentes["biologia"] == frentes["quimica"] == frentes["fisica"] == 10
    assert frentes["matematica"] == 0


def test_declaracao_muda_a_ordem_de_quem_nao_tem_medida():
    sem = pe.ranking()
    com = pe.ranking(None, None, {"biologia": 10, "quimica": 10, "fisica": 10, "matematica": 0})
    chave = lambda linhas: [l["chave"] for l in linhas]  # noqa: E731

    # Sem declaração, Matemática e Redação abrem a lista pelo peso na prova.
    assert chave(sem)[0] in {"matematica", "redacao"}
    # Com "Natureza 10 / Matemática 0", Biologia passa na frente de Matemática —
    # mas Redação, que ele não declarou, continua no topo pelo peso.
    assert chave(com).index("biologia") < chave(com).index("matematica")


def test_declaracao_nao_sobrescreve_medida():
    """O aluno disse que Matemática é fácil (0). Os números dele dizem outra
    coisa. Quem manda é o número."""
    stats = {"matematica": {"respondidas": 20, "acertos": 4}}
    linha = next(l for l in pe.ranking(stats, None, {"matematica": 0}) if l["chave"] == "matematica")
    assert linha["estado"] == "medido"
    assert linha["lacuna"] == pytest.approx(0.8)
    assert linha["declarada"] is None  # a opinião nem aparece: há medida


def test_slider_no_meio_devolve_o_comportamento_de_quem_nao_declarou():
    neutro = next(l for l in pe.ranking(None, None, {"humanas": 5}) if l["chave"] == "humanas")
    padrao = next(l for l in pe.ranking() if l["chave"] == "humanas")
    assert neutro["rendimento"] == padrao["rendimento"]


def test_porque_declarado_diz_que_e_opiniao():
    linha = next(l for l in pe.ranking(None, None, {"humanas": 9}) if l["chave"] == "humanas")
    assert "9 de 10" in linha["porque"]
    assert "não medida minha" in linha["porque"]


# ---------------------------------------------------------------------------
# O que a Mentis recebe
# ---------------------------------------------------------------------------


def test_resumo_para_modelo_so_existe_depois_de_concluir(db):
    _run(ob.salvar_onboarding(ob.OnboardingPayload(objetivo="Passar em Medicina"), user=_user()))
    assert _run(ob.resumo_para_modelo("aluno-1")) is None

    _run(ob.salvar_onboarding(
        ob.OnboardingPayload(minutos_por_dia=60, meta="medio", concluido=True), user=_user()
    ))
    resumo = _run(ob.resumo_para_modelo("aluno-1"))
    assert "Passar em Medicina" in resumo
    assert "60 min/dia" in resumo
    assert "140-160 acertos" in resumo
    # Rotulado como opinião: o dossiê inteiro é medida, e esta linha não é.
    assert "opinião dele, não medida" in resumo


def test_sem_mongo_nada_explode():
    ob.set_db(None)
    assert _run(ob.dificuldade_por_frente("aluno-1")) == {}
    assert _run(ob.resumo_para_modelo("aluno-1")) is None
