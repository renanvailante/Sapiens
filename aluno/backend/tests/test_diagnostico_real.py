"""Diagnóstico real (`annotation_service.compute_diagnostico_real`) — offline,
sem Firestore real: a leitura bruta de eventos é substituída por um dublê.

Garantias centrais testadas aqui:
- amostra mínima é respeitada (um nó com poucas respostas nunca vira "ponto
  fraco/forte", mesmo com 0% ou 100% de acerto);
- um processo fraco só ganha "padrão associado" a um Tipo de Erro quando o
  catálogo tem exatamente UM candidato para aquele processo — nunca por
  chute entre vários, nunca quando não há nenhum;
- isto nunca produz um Error Trace (não há `trace_id`, `cadeia`, `produtor`
  nem atribuição de causa a uma resposta individual) — é agregação de
  desempenho medido cruzada com fato geral do catálogo.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import annotation_service as asvc  # noqa: E402


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestRankingReal:
    def test_respeita_amostra_minima(self):
        stats = {
            "PROC-A": {"respondidas": 2, "acertos": 0},  # abaixo do mínimo — nunca aparece
            "PROC-B": {"respondidas": 3, "acertos": 1},
        }
        catalogo = {"PROC-A": "Processo A", "PROC-B": "Processo B"}
        linhas = asvc._ranking_real(stats, catalogo, min_amostra=3, ascending=True)
        assert [l["id"] for l in linhas] == ["PROC-B"]

    def test_ordem_ascendente_e_descendente(self):
        stats = {
            "PROC-A": {"respondidas": 10, "acertos": 2},   # 20%
            "PROC-B": {"respondidas": 10, "acertos": 9},   # 90%
        }
        catalogo = {}
        fracos = asvc._ranking_real(stats, catalogo, min_amostra=3, ascending=True)
        fortes = asvc._ranking_real(stats, catalogo, min_amostra=3, ascending=False)
        assert [l["id"] for l in fracos] == ["PROC-A", "PROC-B"]
        assert [l["id"] for l in fortes] == ["PROC-B", "PROC-A"]

    def test_nome_cai_para_o_id_quando_fora_do_catalogo(self):
        stats = {"PROC-X": {"respondidas": 5, "acertos": 1}}
        linhas = asvc._ranking_real(stats, {}, min_amostra=3, ascending=True)
        assert linhas[0]["nome"] == "PROC-X"


class TestErrosPorProcesso:
    def test_processo_com_exatamente_um_erro_catalogado(self):
        idx = asvc._erros_por_processo()
        assert [e["id"] for e in idx.get("PROC-QUANT-02", [])] == ["ERR-05"]

    def test_processo_ambiguo_tem_mais_de_um_candidato(self):
        idx = asvc._erros_por_processo()
        assert len(idx.get("PROC-TEXT-01", [])) >= 2

    def test_processo_sem_tipo_erro_catalogado(self):
        idx = asvc._erros_por_processo()
        assert idx.get("PROC-ESPACO-01") in (None, [])


class TestComputeDiagnosticoReal:
    def test_padrao_associado_so_aparece_para_processo_fraco_e_inequivoco(self, monkeypatch):
        agg = {
            # PROC-QUANT-02: fraco (30%) e tem exatamente 1 tipo de erro (ERR-05) -> deve aparecer.
            "processo_stats": {
                "PROC-QUANT-02": {"respondidas": 10, "acertos": 3},
                # PROC-TEXT-01: fraco também, mas tem 2 candidatos (ambíguo) -> não deve aparecer.
                "PROC-TEXT-01": {"respondidas": 10, "acertos": 2},
            },
            "dominio_stats": {},
            "competencia_stats": {},
            "total_events": 20,
            "matched_events": 20,
            "unmatched_events": 0,
        }
        monkeypatch.setattr(asvc, "_read_firestore_desempenho_detalhado", lambda uid: agg)
        resultado = _run(asvc.compute_diagnostico_real("user-1"))

        ids_com_padrao = {p["processo_id"] for p in resultado["padroes_associados"]}
        assert "PROC-QUANT-02" in ids_com_padrao
        assert "PROC-TEXT-01" not in ids_com_padrao

        padrao = next(p for p in resultado["padroes_associados"] if p["processo_id"] == "PROC-QUANT-02")
        assert padrao["erro_id"] == "ERR-05"
        assert padrao["intervencao_id"]
        assert padrao["intervencao_nome"]

    def test_nao_e_um_error_trace(self, monkeypatch):
        agg = {
            "processo_stats": {"PROC-QUANT-02": {"respondidas": 10, "acertos": 1}},
            "dominio_stats": {}, "competencia_stats": {},
            "total_events": 10, "matched_events": 10, "unmatched_events": 0,
        }
        monkeypatch.setattr(asvc, "_read_firestore_desempenho_detalhado", lambda uid: agg)
        resultado = _run(asvc.compute_diagnostico_real("user-1"))
        padrao = resultado["padroes_associados"][0]
        for campo_etrace in ("trace_id", "cadeia", "produtor", "confianca_global", "revisado_por_humano"):
            assert campo_etrace not in padrao

    def test_amostra_insuficiente_nao_gera_pontos_nem_padroes(self, monkeypatch):
        agg = {
            "processo_stats": {"PROC-QUANT-02": {"respondidas": 1, "acertos": 0}},
            "dominio_stats": {}, "competencia_stats": {},
            "total_events": 1, "matched_events": 1, "unmatched_events": 0,
        }
        monkeypatch.setattr(asvc, "_read_firestore_desempenho_detalhado", lambda uid: agg)
        resultado = _run(asvc.compute_diagnostico_real("user-1"))
        assert resultado["por_processo"]["fracos"] == []
        assert resultado["padroes_associados"] == []

    def test_falha_de_leitura_degrada_sem_propagar(self, monkeypatch):
        def _quebra(uid):
            raise RuntimeError("Firestore indisponível")

        monkeypatch.setattr(asvc, "_read_firestore_desempenho_detalhado", _quebra)
        resultado = _run(asvc.compute_diagnostico_real("user-1"))
        assert resultado["por_processo"] == {"fortes": [], "fracos": []}
        assert resultado["padroes_associados"] == []
        assert resultado["coverage"] == 0.0

    def test_coverage_calculado_sobre_eventos_totais(self, monkeypatch):
        agg = {
            "processo_stats": {}, "dominio_stats": {}, "competencia_stats": {},
            "total_events": 8, "matched_events": 6, "unmatched_events": 2,
        }
        monkeypatch.setattr(asvc, "_read_firestore_desempenho_detalhado", lambda uid: agg)
        resultado = _run(asvc.compute_diagnostico_real("user-1"))
        assert resultado["coverage"] == 75.0
