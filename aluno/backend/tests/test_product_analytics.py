"""Analytics de produto — activation, time-to-first-value, cohort.

Offline, com `fake_db` (ver `tests/conftest.py`), no mesmo estilo do resto
da casa. Foco: idempotência por `_id` determinístico (o que garante "uma
vez na vida" sem checar antes de gravar) e as contas de ativação/cohort não
inventarem número quando falta dado.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import product_analytics as pa  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class TestRegistrar:
    def test_tipo_desconhecido_nao_grava_e_devolve_false(self, fake_db):
        ok = _run(pa.registrar(fake_db, "u1", "tipo_inventado"))
        assert ok is False
        assert _run(fake_db.product_events.count_documents({})) == 0

    def test_marco_unico_so_grava_uma_vez(self, fake_db):
        primeiro = _run(pa.registrar(fake_db, "u1", "primeira_microvitoria"))
        segundo = _run(pa.registrar(fake_db, "u1", "primeira_microvitoria"))
        assert primeiro is True
        assert segundo is False
        assert _run(fake_db.product_events.count_documents({"uid": "u1"})) == 1

    def test_marco_unico_e_por_aluno_nao_global(self, fake_db):
        _run(pa.registrar(fake_db, "u1", "primeira_compra"))
        outro = _run(pa.registrar(fake_db, "u2", "primeira_compra"))
        assert outro is True

    def test_recompra_pode_acontecer_mais_de_uma_vez_por_chave_diferente(self, fake_db):
        a = _run(pa.registrar(fake_db, "u1", "recompra", chave="pagamento-1"))
        b = _run(pa.registrar(fake_db, "u1", "recompra", chave="pagamento-2"))
        repetido = _run(pa.registrar(fake_db, "u1", "recompra", chave="pagamento-1"))
        assert a is True and b is True
        assert repetido is False  # mesmo pagamento não duplica
        assert _run(fake_db.product_events.count_documents({"uid": "u1", "tipo": "recompra"})) == 2


class TestTempoParaPrimeiroValor:
    def test_sem_data_de_cadastro_nao_calcula(self, fake_db):
        assert _run(pa.tempo_para_primeiro_valor(fake_db, "u1", None)) is None

    def test_sem_nenhum_marco_ainda_nao_calcula(self, fake_db):
        assert _run(pa.tempo_para_primeiro_valor(fake_db, "u1", "2026-09-01T10:00:00+00:00")) is None

    def test_calcula_horas_entre_cadastro_e_primeiro_marco(self, fake_db):
        _run(fake_db.product_events.insert_one({
            "_id": "u1:primeira_microvitoria", "uid": "u1", "tipo": "primeira_microvitoria",
            "chave": None, "meta": {}, "created_at": "2026-09-01T13:00:00+00:00",
        }))
        horas = _run(pa.tempo_para_primeiro_valor(fake_db, "u1", "2026-09-01T10:00:00+00:00"))
        assert horas == 3.0


class TestResumoAtivacao:
    def test_sem_cadastrado_nenhum_taxa_e_none_nao_zero(self, fake_db):
        resumo = _run(pa.resumo_ativacao(fake_db, dias=30))
        assert resumo["cadastrados"] == 0
        assert resumo["taxa_ativacao"] is None  # "não sei" nunca é 0

    def test_conta_so_quem_cadastrou_na_janela_e_tem_marco(self, fake_db):
        from datetime import datetime, timedelta, timezone
        agora = datetime.now(timezone.utc)
        _run(fake_db.users.insert_one({"user_id": "novo", "created_at": agora.isoformat()}))
        _run(fake_db.users.insert_one({
            "user_id": "antigo", "created_at": (agora - timedelta(days=400)).isoformat(),
        }))
        _run(pa.registrar(fake_db, "novo", "primeira_microvitoria"))
        _run(pa.registrar(fake_db, "antigo", "primeira_microvitoria"))  # fora da janela

        resumo = _run(pa.resumo_ativacao(fake_db, dias=30))
        assert resumo["cadastrados"] == 1
        assert resumo["ativados"] == 1
        assert resumo["taxa_ativacao"] == 1.0
        assert resumo["marcos_por_tipo"]["primeira_microvitoria"] == 1


class TestResumoCohort:
    def test_semana_sem_cadastro_devolve_zeros_sem_inventar(self, fake_db):
        linhas = _run(pa.resumo_cohort(fake_db, semanas=2))
        assert len(linhas) == 2
        assert all(l["cadastrados"] == 0 and l["ativados"] == 0 for l in linhas)

    def test_ordem_e_cronologica_mais_antiga_primeiro(self, fake_db):
        linhas = _run(pa.resumo_cohort(fake_db, semanas=3))
        datas = [l["semana_inicio"] for l in linhas]
        assert datas == sorted(datas)
