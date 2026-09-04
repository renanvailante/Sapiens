"""Perfil cognitivo automático (`perfil_cognitivo_service`) — offline, sem
Firestore/Gemini real: as dependências são substituídas por dublês.

Garantias centrais testadas aqui:
- narrativa (a única chamada Gemini de todo o pipeline) é gerada NO MÁXIMO
  uma vez por período — uma segunda chamada na MESMA semana reaproveita o
  texto salvo; só uma semana nova dispara uma narrativa nova;
- nenhum ID de catálogo sobrevive ao que é mandado para a narrativa;
- o lote (`atualizar_todos_os_perfis`) só recomputa quem teve evento novo
  desde o último snapshot, e a falha de um aluno não derruba os demais.
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import ai_service  # noqa: E402
import annotation_service  # noqa: E402
import firestore_service as fs  # noqa: E402
import perfil_cognitivo_service as pcs  # noqa: E402

_ID_CATALOGO = re.compile(r"\b(PROC|DOM|COMP|ERR|MEC|HAB|INT)-[A-Z0-9-]+\b")

_PERFIL_COM_DADO = {
    "por_dominio": {
        "fortes": [{"id": "DOM-QUANT", "nome": "Quantidade", "percentual_acerto": 90.0, "respondidas": 10}],
        "fracos": [],
    },
    "por_competencia": {"fortes": [], "fracos": []},
    "por_processo": {
        "fortes": [],
        "fracos": [{"id": "PROC-QUANT-02", "nome": "Relação proporcional", "percentual_acerto": 20.0, "respondidas": 10}],
    },
    "padroes_associados": [{
        "processo_id": "PROC-QUANT-02", "processo_nome": "Relação proporcional",
        "percentual_acerto": 20.0, "respondidas": 10,
        "erro_id": "ERR-05", "erro_nome": "Confusão de direção proporcional",
        "erro_evidencia_observavel": "Inverte a relação", "intervencao_id": "INT-03",
        "intervencao_nome": "Prática guiada de proporção",
    }],
    "total_events": 20, "matched_events": 20, "unmatched_events": 0,
    "coverage": 100.0, "amostra_minima": 3, "ontology_version": "1.4.1",
}

_PERFIL_VAZIO = {
    "por_dominio": {"fortes": [], "fracos": []},
    "por_competencia": {"fortes": [], "fracos": []},
    "por_processo": {"fortes": [], "fracos": []},
    "padroes_associados": [],
    "total_events": 1, "matched_events": 1, "unmatched_events": 0,
    "coverage": 100.0, "amostra_minima": 3, "ontology_version": "1.4.1",
}


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestPeriodoAtual:
    def test_formato_zero_padded(self):
        periodo = pcs.periodo_atual()
        assert re.fullmatch(r"\d{4}-W\d{2}", periodo), periodo


class TestSanitizarParaNarrativa:
    def test_nenhum_id_de_catalogo_sobrevive(self):
        import json

        limpo = pcs._sanitizar_para_narrativa(_PERFIL_COM_DADO)
        bruto = json.dumps(limpo, ensure_ascii=False)
        assert not _ID_CATALOGO.search(bruto), f"ID de catálogo vazou: {bruto}"

    def test_nomes_e_numeros_preservados(self):
        limpo = pcs._sanitizar_para_narrativa(_PERFIL_COM_DADO)
        assert limpo["por_dominio"]["fortes"][0]["nome"] == "Quantidade"
        assert limpo["por_dominio"]["fortes"][0]["percentual_acerto"] == 90.0
        assert limpo["padroes_associados"][0]["erro_nome"] == "Confusão de direção proporcional"


class TestGerarESalvarSnapshot:
    def test_sem_amostra_devolve_none_e_nao_grava(self, monkeypatch):
        async def _perfil_vazio(uid):
            return dict(_PERFIL_VAZIO)

        gravou = []
        monkeypatch.setattr(annotation_service, "compute_diagnostico_real", _perfil_vazio)
        monkeypatch.setattr(fs, "write_perfil_cognitivo", lambda uid, periodo, doc: gravou.append(doc))

        resultado = _run(pcs.gerar_e_salvar_snapshot("user-1"))
        assert resultado is None
        assert gravou == []

    def test_primeira_vez_gera_narrativa(self, monkeypatch):
        async def _perfil(uid):
            return dict(_PERFIL_COM_DADO)

        chamadas_narrativa = []

        async def _narrativa(payload):
            chamadas_narrativa.append(payload)
            return "briefing novo"

        gravado = {}
        monkeypatch.setattr(annotation_service, "compute_diagnostico_real", _perfil)
        monkeypatch.setattr(fs, "read_ultimo_perfil", lambda uid: None)
        monkeypatch.setattr(ai_service, "gerar_narrativa_perfil", _narrativa)
        monkeypatch.setattr(fs, "write_perfil_cognitivo", lambda uid, periodo, doc: gravado.update(doc))

        resultado = _run(pcs.gerar_e_salvar_snapshot("user-1"))
        assert len(chamadas_narrativa) == 1
        assert resultado["narrativa"] == "briefing novo"
        assert gravado["narrativa"] == "briefing novo"
        assert gravado["periodo"] == pcs.periodo_atual()

    def test_mesma_semana_reaproveita_narrativa_sem_chamar_ia(self, monkeypatch):
        async def _perfil(uid):
            return dict(_PERFIL_COM_DADO)

        chamadas_narrativa = []

        async def _narrativa(payload):
            chamadas_narrativa.append(payload)
            return "não deveria ser chamada"

        anterior = {"periodo": pcs.periodo_atual(), "narrativa": "briefing da semana"}
        monkeypatch.setattr(annotation_service, "compute_diagnostico_real", _perfil)
        monkeypatch.setattr(fs, "read_ultimo_perfil", lambda uid: anterior)
        monkeypatch.setattr(ai_service, "gerar_narrativa_perfil", _narrativa)
        monkeypatch.setattr(fs, "write_perfil_cognitivo", lambda uid, periodo, doc: None)

        resultado = _run(pcs.gerar_e_salvar_snapshot("user-1"))
        assert chamadas_narrativa == []
        assert resultado["narrativa"] == "briefing da semana"

    def test_semana_nova_gera_narrativa_nova(self, monkeypatch):
        async def _perfil(uid):
            return dict(_PERFIL_COM_DADO)

        chamadas_narrativa = []

        async def _narrativa(payload):
            chamadas_narrativa.append(payload)
            return "briefing atualizado"

        anterior = {"periodo": "2000-W01", "narrativa": "briefing bem antigo"}
        monkeypatch.setattr(annotation_service, "compute_diagnostico_real", _perfil)
        monkeypatch.setattr(fs, "read_ultimo_perfil", lambda uid: anterior)
        monkeypatch.setattr(ai_service, "gerar_narrativa_perfil", _narrativa)
        monkeypatch.setattr(fs, "write_perfil_cognitivo", lambda uid, periodo, doc: None)

        resultado = _run(pcs.gerar_e_salvar_snapshot("user-1"))
        assert len(chamadas_narrativa) == 1
        assert resultado["narrativa"] == "briefing atualizado"

    def test_falha_na_narrativa_nao_impede_salvar_o_snapshot(self, monkeypatch):
        async def _perfil(uid):
            return dict(_PERFIL_COM_DADO)

        async def _narrativa_falha(payload):
            return ""  # ai_service já degrada internamente para string vazia

        gravado = {}
        monkeypatch.setattr(annotation_service, "compute_diagnostico_real", _perfil)
        monkeypatch.setattr(fs, "read_ultimo_perfil", lambda uid: None)
        monkeypatch.setattr(ai_service, "gerar_narrativa_perfil", _narrativa_falha)
        monkeypatch.setattr(fs, "write_perfil_cognitivo", lambda uid, periodo, doc: gravado.update(doc))

        resultado = _run(pcs.gerar_e_salvar_snapshot("user-1"))
        assert resultado is not None
        assert gravado["narrativa"] == ""
        assert gravado["por_processo"]["fracos"][0]["nome"] == "Relação proporcional"


class TestAtualizarTodosOsPerfis:
    def test_pula_quem_nao_tem_evento_novo(self, monkeypatch):
        monkeypatch.setattr(fs, "list_students_with_behavior", lambda: [{"student_id": "a", "count": 5}])
        monkeypatch.setattr(fs, "read_ultimo_perfil", lambda uid: {"fonte_event_count": 5})

        chamado = []

        async def _fake_gerar(uid, fonte_event_count=None):
            chamado.append(uid)
            return {}

        monkeypatch.setattr(pcs, "gerar_e_salvar_snapshot", _fake_gerar)

        resultado = _run(pcs.atualizar_todos_os_perfis())
        assert chamado == []
        assert resultado["pulados"] == 1
        assert resultado["processados"] == 0

    def test_processa_quem_tem_evento_novo(self, monkeypatch):
        monkeypatch.setattr(fs, "list_students_with_behavior", lambda: [{"student_id": "a", "count": 8}])
        monkeypatch.setattr(fs, "read_ultimo_perfil", lambda uid: {"fonte_event_count": 5})

        async def _fake_gerar(uid, fonte_event_count=None):
            return {"periodo": "x"}

        monkeypatch.setattr(pcs, "gerar_e_salvar_snapshot", _fake_gerar)

        resultado = _run(pcs.atualizar_todos_os_perfis())
        assert resultado["processados"] == 1
        assert resultado["pulados"] == 0

    def test_sem_amostra_e_contado_separado(self, monkeypatch):
        monkeypatch.setattr(fs, "list_students_with_behavior", lambda: [{"student_id": "a", "count": 1}])
        monkeypatch.setattr(fs, "read_ultimo_perfil", lambda uid: None)

        async def _fake_gerar(uid, fonte_event_count=None):
            return None

        monkeypatch.setattr(pcs, "gerar_e_salvar_snapshot", _fake_gerar)

        resultado = _run(pcs.atualizar_todos_os_perfis())
        assert resultado["sem_amostra"] == 1
        assert resultado["processados"] == 0

    def test_falha_de_um_aluno_nao_impede_os_outros(self, monkeypatch):
        monkeypatch.setattr(fs, "list_students_with_behavior", lambda: [
            {"student_id": "quebra", "count": 9},
            {"student_id": "ok", "count": 9},
        ])
        monkeypatch.setattr(fs, "read_ultimo_perfil", lambda uid: None)

        async def _fake_gerar(uid, fonte_event_count=None):
            if uid == "quebra":
                raise RuntimeError("boom")
            return {"periodo": "x"}

        monkeypatch.setattr(pcs, "gerar_e_salvar_snapshot", _fake_gerar)

        resultado = _run(pcs.atualizar_todos_os_perfis())
        assert resultado["falhas"] == 1
        assert resultado["processados"] == 1
