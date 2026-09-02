"""Agregado do aluno e datas no fuso de São Paulo.

Itens 07 e 17 da auditoria pré-beta:
  * `/students/me/respondidas` e `/students/me/activity` liam TODO o histórico
    de eventos (5.000 e 3.000 documentos) a cada carregamento do painel;
  * as datas de atividade eram calculadas em UTC, e o Brasil está em UTC-3 —
    quem respondia depois das 21h tinha a atividade contada no dia seguinte.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402


# ================================================================= fuso

def test_noite_brasileira_conta_no_dia_certo():
    """22h de 10/03 em São Paulo é 01h de 11/03 em UTC. Em UTC o evento caía no
    dia 11 — a bolinha de 'hoje' ficava apagada depois de estudar e a sequência
    podia zerar sozinha, no horário em que vestibulando mais estuda."""
    assert fs.dia_local("2026-03-11T01:30:00+00:00") == "2026-03-10"


def test_manha_brasileira_conta_no_proprio_dia():
    assert fs.dia_local("2026-03-10T13:00:00+00:00") == "2026-03-10"


def test_virada_do_dia_local():
    """03h UTC = meia-noite em São Paulo: já é o dia seguinte para o aluno."""
    assert fs.dia_local("2026-03-11T03:00:00+00:00") == "2026-03-11"


def test_timestamp_sem_fuso_e_lido_como_utc():
    """Eventos gravados antes de o formato incluir offset não podem mudar de
    dia por causa da leitura."""
    assert fs.dia_local("2026-03-11T01:30:00") == "2026-03-10"


# ============================================================= agregado

class _FakeDoc:
    """Documento de aluno com merge raso, o suficiente para `agregado`."""

    def __init__(self, dados=None):
        self.dados = dados or {}
        self.exists = bool(dados)
        self.escritas = 0

    def get(self):
        return self

    def to_dict(self):
        return self.dados

    def set(self, novo, merge=False):
        self.escritas += 1
        if merge:
            for chave, valor in novo.items():
                if isinstance(valor, dict) and isinstance(self.dados.get(chave), dict):
                    self.dados[chave].update(valor)
                else:
                    self.dados[chave] = valor
        else:
            self.dados = novo
        self.exists = True


def test_ler_agregado_nao_toca_o_historico_quando_ja_existe(monkeypatch):
    """O ponto do agregado: UMA leitura, não uma varredura. Se o histórico for
    consultado aqui, o custo que motivou a mudança voltou."""
    doc = _FakeDoc({"agregado": {"item_ids_respondidos": ["A", "B"], "dias_ativos": ["2026-03-10"]}})
    monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: doc)

    def _proibido(*a, **k):
        raise AssertionError("ler_agregado varreu o histórico com agregado presente")

    monkeypatch.setattr(fs, "get_student_behavior_history", _proibido)

    assert fs.ler_agregado("uid-1")["item_ids_respondidos"] == ["A", "B"]


def test_agregado_ausente_e_reconstruido_do_historico(monkeypatch):
    """Quem já respondia antes do agregado existir não pode ficar sem dado: a
    primeira leitura paga o preço uma vez e grava o resultado."""
    doc = _FakeDoc({"nome": "Aluno"})
    monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: doc)
    monkeypatch.setattr(fs, "get_student_behavior_history", lambda uid, limite: [
        {"item_id": "A", "status": "respondida", "timestamp": "2026-03-11T01:30:00+00:00"},
        {"item_id": "B", "status": "respondida", "timestamp": "2026-03-10T13:00:00+00:00"},
        {"item_id": "C", "status": "abandonada", "timestamp": "2026-03-10T14:00:00+00:00"},
    ])

    agregado = fs.ler_agregado("uid-1")

    # "abandonada" não é resposta e não entra na lista de respondidos.
    assert agregado["item_ids_respondidos"] == ["A", "B"]
    # Os dois primeiros eventos caem no MESMO dia local (10/03), apesar de
    # estarem em dias diferentes em UTC.
    assert agregado["dias_ativos"] == ["2026-03-10"]
    assert doc.dados["agregado"]["item_ids_respondidos"] == ["A", "B"]


def test_falha_ao_atualizar_agregado_nao_derruba_a_resposta(monkeypatch):
    """O evento já foi gravado — que é o dado que importa. Um agregado
    desatualizado é recuperável; perder a resposta do aluno não é."""
    class _Explode:
        def set(self, *a, **k):
            raise RuntimeError("Firestore indisponível")

    monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: _Explode())
    fs._atualizar_agregado("uid-1", item_id="A", timestamp="2026-03-10T13:00:00+00:00")  # não levanta
