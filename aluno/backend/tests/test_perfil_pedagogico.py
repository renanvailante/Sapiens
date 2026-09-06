"""`GET /perfil` — a garantia central é arquitetural, não visual: nenhum
campo da resposta pode carregar nome ou ID interno da ontologia
(domínio/competência/processo/habilidade/tipo de erro/intervenção) nem
percentual. `annotation_service.compute_diagnostico_real` (engenharia real,
intocada) continua devolvendo tudo isso — a fronteira é `perfil_pedagogico`.
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import annotation_service  # noqa: E402
import perfil_pedagogico as pp  # noqa: E402
from canonical_ontology import load_ontology  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _ids_reais() -> list[str]:
    onto = load_ontology()
    ids = []
    for chave in ("dominios", "competencias", "processos_cognitivos", "habilidades_observaveis", "tipos_erro", "intervencoes_pedagogicas"):
        ids.extend(item["id"] for item in (onto.get(chave) or []) if item.get("id"))
    return ids


def _nomes_reais() -> list[str]:
    onto = load_ontology()
    nomes = []
    for chave in ("dominios", "competencias", "processos_cognitivos", "habilidades_observaveis", "tipos_erro", "intervencoes_pedagogicas"):
        nomes.extend(item["nome"] for item in (onto.get(chave) or []) if item.get("nome"))
    return nomes


class TestGlossarioCobreOCatalogo:
    def test_todas_as_25_chaves_de_processo_tem_glossario(self):
        onto = load_ontology()
        ids_processo = {p["id"] for p in onto["processos_cognitivos"]}
        assert ids_processo == set(pp.GLOSSARIO_PROCESSO.keys())

    def test_cada_entrada_tem_rotulo_e_as_duas_descricoes(self):
        for pid, entrada in pp.GLOSSARIO_PROCESSO.items():
            assert entrada.get("rotulo"), pid
            assert entrada.get("descricao_forte"), pid
            assert entrada.get("descricao_fraca"), pid


class TestRespostaNuncaVazaOntologia:
    """A checagem varre o CATÁLOGO real (não uma lista manual) — se um ID ou
    nome interno aparecer em qualquer string da resposta, o teste acusa."""

    async def _perfil_com_agregado_fake(self, agg: dict) -> dict:
        async def _fake_desempenho(uid: str):
            return agg

        original = annotation_service._read_firestore_desempenho_detalhado
        annotation_service._read_firestore_desempenho_detalhado = lambda uid: agg
        try:
            return await pp.perfil_publico("user-1")
        finally:
            annotation_service._read_firestore_desempenho_detalhado = original

    def _agregado_rico(self) -> dict:
        onto = load_ontology()
        processos = [p["id"] for p in onto["processos_cognitivos"]]
        stats = {}
        # Metade forte (90%), metade fraca (10%) — amostra acima do mínimo.
        for i, pid in enumerate(processos):
            acertos = 9 if i % 2 == 0 else 1
            stats[pid] = {"respondidas": 10, "acertos": acertos}
        return {
            "dominio_stats": {}, "competencia_stats": {}, "processo_stats": stats,
            "total_events": 250, "matched_events": 250, "unmatched_events": 0,
        }

    def test_nenhum_id_ou_nome_interno_na_resposta(self):
        resultado = _run(self._perfil_com_agregado_fake(self._agregado_rico()))
        bruto = str(resultado)
        for id_real in _ids_reais():
            assert id_real not in bruto, f"vazou o id {id_real!r}: {bruto}"
        for nome_real in _nomes_reais():
            assert nome_real not in bruto, f"vazou o nome {nome_real!r}: {bruto}"

    def test_nenhum_percentual_ou_contagem_de_respostas(self):
        resultado = _run(self._perfil_com_agregado_fake(self._agregado_rico()))
        bruto = str(resultado)
        assert "percentual" not in bruto.lower()
        assert "respondidas" not in bruto.lower()
        assert not re.search(r"\d+%", bruto)
        assert not re.search(r"\d+\.\d+", bruto)  # nenhum float solto (percentual arredondado)

    def test_devolve_no_maximo_5_de_cada(self):
        resultado = _run(self._perfil_com_agregado_fake(self._agregado_rico()))
        assert len(resultado["pontos_fortes"]) <= 5
        assert len(resultado["pontos_a_desenvolver"]) <= 5
        assert len(resultado["pontos_fortes"]) == 5  # 12-13 processos fortes disponíveis nesta amostra
        assert len(resultado["pontos_a_desenvolver"]) == 5

    def test_cada_item_tem_so_rotulo_e_explicacao(self):
        resultado = _run(self._perfil_com_agregado_fake(self._agregado_rico()))
        for item in resultado["pontos_fortes"] + resultado["pontos_a_desenvolver"]:
            assert set(item.keys()) == {"rotulo", "explicacao"}

    def test_aluno_sem_historico_e_amostra_insuficiente(self):
        vazio = {
            "dominio_stats": {}, "competencia_stats": {}, "processo_stats": {},
            "total_events": 0, "matched_events": 0, "unmatched_events": 0,
        }
        resultado = _run(self._perfil_com_agregado_fake(vazio))
        assert resultado["amostra_insuficiente"] is True
        assert resultado["pontos_fortes"] == []
        assert resultado["pontos_a_desenvolver"] == []


class TestExplicacaoFracaPreferaEvidenciaEspecifica:
    def test_usa_evidencia_observavel_quando_disponivel_sem_nome_do_erro(self):
        padroes = {"PROC-CAUSAL-01": {
            "processo_id": "PROC-CAUSAL-01",
            "erro_id": "ERR-01", "erro_nome": "Confunde correlação com causalidade",
            "erro_evidencia_observavel": "você tende a supor causa quando só há duas coisas acontecendo juntas",
        }}
        explicacao = pp._explicacao_fraca("PROC-CAUSAL-01", padroes)
        assert explicacao == "você tende a supor causa quando só há duas coisas acontecendo juntas"
        assert "ERR-01" not in explicacao
        assert "Confunde correlação" not in explicacao

    def test_cai_no_generico_do_glossario_sem_evidencia(self):
        explicacao = pp._explicacao_fraca("PROC-CAUSAL-01", {})
        assert explicacao == pp.GLOSSARIO_PROCESSO["PROC-CAUSAL-01"]["descricao_fraca"]
