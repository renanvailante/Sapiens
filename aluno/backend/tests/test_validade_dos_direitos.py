"""O mês que a loja vende tem de ser o mês que o servidor concede.

Desde 2026-09-16 o card de 4.000 Sparks anuncia "Mentis ILIMITADA por um mês".
Antes disso anunciava "para sempre", e o servidor concedia uma flag sem data —
o que agora seria propaganda errada dos dois lados possíveis: cobrar de quem
comprou ontem, ou liberar de graça para sempre quem comprou um mês.

Estes testes fecham os dois, e mais um que é o mais fácil de quebrar sem
perceber: **quem comprou quando a loja vendia "para sempre" não pode perder o
acesso**. O sinal disso no documento é a ausência de `mentis_ilimitada_ate`.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402
import sparks_store  # noqa: E402


def _agora():
    return datetime.now(timezone.utc)


class _DocFalso:
    """Documento de aluno em memória, com a mesma cara do do Firestore."""

    def __init__(self, dados=None, explode_na_leitura=False):
        self.dados = dict(dados or {})
        self.explode_na_leitura = explode_na_leitura

    def get(self):
        if self.explode_na_leitura:
            raise RuntimeError("Firestore fora do ar")
        dados = self.dados

        class _Snap:
            @staticmethod
            def to_dict():
                return dict(dados)

        return _Snap()

    def set(self, campos, merge=False):  # noqa: ARG002
        self.dados.update(campos)


@pytest.fixture
def doc(monkeypatch):
    d = _DocFalso()
    monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: d)
    return d


class TestOCatalogoMandaNoPrazo:
    def test_a_mentis_vence_e_a_comunidade_nao(self):
        assert sparks_store.prazo_do_direito_dias("mentis_ilimitada") == 30
        assert sparks_store.prazo_do_direito_dias("comunidade_vip") is None

    def test_todo_direito_com_prazo_existe_na_lista_fechada(self):
        assert set(sparks_store.PRAZO_DOS_DIREITOS_DIAS) <= set(sparks_store.DIREITOS)

    def test_o_texto_da_loja_fala_em_mes_e_nao_em_sempre(self):
        """O par que este módulo existe para manter junto: se alguém trocar o
        prazo para 365 dias, este teste obriga a trocar o texto também."""
        pkg = sparks_store.get_package("spark_4000")
        linha = next(b for b in pkg.beneficios if "Mentis" in b)
        assert "para sempre" not in linha.lower()
        assert "por um mês" in linha.lower()
        assert sparks_store.prazo_do_direito_dias("mentis_ilimitada") == 30


class TestConcederGravaOVencimento:
    def test_a_mentis_ganha_data_daqui_a_trinta_dias(self, doc):
        fs.conceder_direitos("aluno-1", ("mentis_ilimitada",))
        assert doc.dados["mentis_ilimitada"] is True
        vence = datetime.fromisoformat(doc.dados["mentis_ilimitada_ate"])
        assert timedelta(days=29, hours=23) < vence - _agora() < timedelta(days=30, minutes=1)

    def test_direito_sem_prazo_nao_ganha_data(self, doc):
        fs.conceder_direitos("aluno-1", ("comunidade_vip",))
        assert doc.dados["comunidade_vip"] is True
        assert "comunidade_vip_ate" not in doc.dados

    def test_comprar_de_novo_ESTENDE_em_vez_de_zerar(self, doc):
        """Quem renova faltando dez dias termina com quarenta, não com trinta.
        Zerar seria cobrar de novo pelo que a pessoa ainda não usou."""
        faltando10 = _agora() + timedelta(days=10)
        doc.dados.update({
            "mentis_ilimitada": True,
            "mentis_ilimitada_ate": faltando10.isoformat(),
        })
        fs.conceder_direitos("aluno-1", ("mentis_ilimitada",))
        vence = datetime.fromisoformat(doc.dados["mentis_ilimitada_ate"])
        assert timedelta(days=39, hours=23) < vence - _agora() < timedelta(days=40, minutes=1)

    def test_comprar_depois_de_vencido_conta_do_zero(self, doc):
        """Prazo vencido não é saldo negativo: quem sumiu por seis meses volta
        com trinta dias, não com trinta menos o tempo parado."""
        doc.dados.update({
            "mentis_ilimitada": True,
            "mentis_ilimitada_ate": (_agora() - timedelta(days=180)).isoformat(),
        })
        fs.conceder_direitos("aluno-1", ("mentis_ilimitada",))
        vence = datetime.fromisoformat(doc.dados["mentis_ilimitada_ate"])
        assert timedelta(days=29, hours=23) < vence - _agora() < timedelta(days=30, minutes=1)


class TestLerRespeitaOVencimento:
    def test_dentro_do_prazo_o_direito_vale(self, doc):
        doc.dados.update({
            "mentis_ilimitada": True,
            "mentis_ilimitada_ate": (_agora() + timedelta(days=1)).isoformat(),
        })
        assert fs.tem_mentis_ilimitada("aluno-1") is True

    def test_depois_do_prazo_a_mentis_volta_a_cobrar(self, doc):
        doc.dados.update({
            "mentis_ilimitada": True,
            "mentis_ilimitada_ate": (_agora() - timedelta(minutes=1)).isoformat(),
        })
        assert fs.tem_mentis_ilimitada("aluno-1") is False

    def test_comunidade_vip_nao_vence_nunca(self, doc):
        doc.dados.update({"comunidade_vip": True})
        assert fs.tem_comunidade_vip("aluno-1") is True


class TestQuemComprouParaSempreNaoPerde:
    """O teste mais importante do arquivo: a loja mudou de promessa, e quem
    pagou pela promessa antiga continua com ela. O sinal é a AUSÊNCIA de data."""

    def test_flag_sem_data_vale_para_sempre(self, doc):
        doc.dados.update({"mentis_ilimitada": True, "mentis_ilimitada_em": "2026-09-01T00:00:00+00:00"})
        assert fs.tem_mentis_ilimitada("aluno-1") is True
        assert fs.vencimento_do_direito("aluno-1", "mentis_ilimitada") is None

    def test_data_ilegivel_nao_tira_o_direito_de_quem_pagou(self, doc):
        """Falha de leitura do Firestore inteiro nega o direito (é a regra de
        `ler_direitos`, para não dar o produto caro à base inteira num
        incidente). Um campo corrompido no documento de UMA pessoa que pagou é
        o caso oposto, e vai para o lado dela."""
        doc.dados.update({"mentis_ilimitada": True, "mentis_ilimitada_ate": "ontem de tarde"})
        assert fs.tem_mentis_ilimitada("aluno-1") is True

    def test_sem_a_flag_a_data_nao_inventa_direito(self, doc):
        doc.dados.update({"mentis_ilimitada_ate": (_agora() + timedelta(days=9999)).isoformat()})
        assert fs.tem_mentis_ilimitada("aluno-1") is False
        assert fs.vencimento_do_direito("aluno-1", "mentis_ilimitada") is None


class TestOVencimentoQueAtelaEscreve:
    def test_devolve_a_data_de_quem_tem_prazo(self, doc):
        quando = _agora() + timedelta(days=12)
        doc.dados.update({"mentis_ilimitada": True, "mentis_ilimitada_ate": quando.isoformat()})
        lido = fs.vencimento_do_direito("aluno-1", "mentis_ilimitada")
        assert datetime.fromisoformat(lido) == quando

    def test_firestore_fora_do_ar_nao_inventa_data(self, monkeypatch):
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: _DocFalso(explode_na_leitura=True))
        assert fs.vencimento_do_direito("aluno-1", "mentis_ilimitada") is None

    def test_leitura_quebrada_na_concessao_ainda_grava_prazo(self, monkeypatch):
        """Sem conseguir ler o vencimento atual, conta-se a partir de agora —
        o que nunca pode acontecer é não gravar data nenhuma, porque isso
        daria acesso perpétuo de graça."""
        d = _DocFalso(explode_na_leitura=True)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: d)
        fs.conceder_direitos("aluno-1", ("mentis_ilimitada",))
        assert "mentis_ilimitada_ate" in d.dados
