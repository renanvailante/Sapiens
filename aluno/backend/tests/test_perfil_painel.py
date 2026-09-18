"""`GET /perfil/painel` — o painel de gráficos do aluno.

Três garantias, e nenhuma delas é visual:

1. **A telemetria sai da varredura que já existia.** Nenhuma leitura nova do
   Firestore por causa dos gráficos (a cota já caiu uma vez por menos que
   isso), e o dia/hora de cada resposta contado no fuso do aluno.
2. **Nada do catálogo interno vaza.** O painel tem números por toda parte, e
   nenhum deles pode ser um percentual de domínio/competência/processo, nem
   carregar nome ou id da ontologia.
3. **Nenhuma leitura da Mentis é inventada.** Toda frase que ela diz sobre o
   aluno tem amostra mínima por trás; sem amostra, ela se cala.
"""
from __future__ import annotations

import asyncio
import re
import sys
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import annotation_service as asvc  # noqa: E402
import perfil_painel as pp  # noqa: E402
import perfil_pedagogico  # noqa: E402
import prioridade_enem  # noqa: E402
from canonical_ontology import load_ontology  # noqa: E402


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --------------------------------------------------------------------------
# Dublê do Firestore: students/{uid}/behavior/*
# --------------------------------------------------------------------------


class _Snap:
    def __init__(self, dados):
        self._d = dados

    def to_dict(self):
        return self._d


class _Colecao:
    def __init__(self, docs):
        self._docs = docs

    def stream(self):
        return iter(self._docs)


class _Documento:
    def __init__(self, docs):
        self._docs = docs

    def collection(self, _nome):
        return _Colecao(self._docs)


class _Cliente:
    def __init__(self, docs):
        self._docs = docs

    def collection(self, _nome):
        return self

    def document(self, _uid):
        return _Documento(self._docs)


def _evento(
    *,
    timestamp,
    acertou=True,
    item_id="ITEM-1",
    tempo=90.0,
    mudou=False,
    contexto="pratica_questoes",
):
    return _Snap({
        "status": "respondida",
        "item_id": item_id,
        "timestamp": timestamp,
        "resposta": {"acertou": acertou},
        "desempenho": {"tempo_resposta_segundos": tempo, "mudou_resposta": mudou},
        "contexto": {"tipo": contexto},
    })


def _varrer(monkeypatch, eventos, index=None):
    monkeypatch.setattr(asvc.fs, "get_firestore", lambda: _Cliente(eventos))
    monkeypatch.setattr(asvc, "_build_item_index", lambda force=False: index or {})
    return asvc._read_firestore_desempenho_detalhado("U1")


_ITEM_MATEMATICA = {
    "ITEM-1": {
        "estrutura_cognitiva": {
            "dominios": ["DOM-01"], "competencias": ["COMP-01"],
            "processos": ["PROC-QUANT-01"],
        },
        "fonte": {"disciplina": "Matemática"},
    }
}


class TestTelemetriaNaMesmaVarredura:
    def test_conta_no_fuso_do_aluno_e_nao_em_utc(self, monkeypatch):
        # 01:00 UTC de 11/09 é 22:00 de 10/09 em São Paulo — o horário em que
        # vestibulando estuda. Contado em UTC, o gráfico de horários jogaria
        # esta resposta para a madrugada do dia seguinte.
        agg = _varrer(monkeypatch, [_evento(timestamp="2026-09-11T01:00:00+00:00")])
        tel = agg["telemetria_descritiva"]
        assert tel["por_dia"] == {"2026-09-10": {"respondidas": 1, "acertos": 1}}
        assert tel["por_hora"]["22"] == {"respondidas": 1, "acertos": 1}
        assert tel["por_dia_semana"]["3"] == {"respondidas": 1, "acertos": 1}  # quinta

    def test_resposta_de_item_sem_anotacao_conta_no_esforco(self, monkeypatch):
        """Treino e questão gerada não estão no catálogo anotado. O aluno
        respondeu assim mesmo — e "quantas questões eu fiz" é sobre ele."""
        agg = _varrer(monkeypatch, [
            _evento(timestamp="2026-09-10T15:00:00+00:00", item_id="FORA-DO-INDICE"),
        ])
        tel = agg["telemetria_descritiva"]
        assert agg["unmatched_events"] == 1
        assert agg["disciplina_stats"] == {}
        assert tel["por_dia"]["2026-09-10"]["respondidas"] == 1
        assert tel["por_origem"]["pratica_questoes"]["respondidas"] == 1

    def test_serie_por_frente_e_semanal_pela_segunda(self, monkeypatch):
        # 10/09/2026 é quinta; 14/09 é a segunda seguinte.
        agg = _varrer(monkeypatch, [
            _evento(timestamp="2026-09-10T15:00:00+00:00"),
            _evento(timestamp="2026-09-15T15:00:00+00:00", acertou=False),
        ], index=_ITEM_MATEMATICA)
        assert agg["telemetria_descritiva"]["frente_por_semana"] == {
            "matematica|2026-09-07": {"respondidas": 1, "acertos": 1},
            "matematica|2026-09-14": {"respondidas": 1, "acertos": 0},
        }

    def test_tempo_nao_registrado_nao_vira_barra(self, monkeypatch):
        """Os fluxos antigos gravavam `tempo_resposta_segundos: 0`. Zero é
        silêncio, não uma resposta instantânea — e silêncio não pode aparecer
        como "respondeu no impulso" nem como "manteve a primeira resposta"."""
        agg = _varrer(monkeypatch, [_evento(timestamp="2026-09-10T15:00:00+00:00", tempo=0)])
        tel = agg["telemetria_descritiva"]
        assert tel["por_faixa_de_tempo"] == {}
        assert tel["por_decisao"] == {}
        assert tel["respostas_com_tempo"] == 0
        assert tel["por_dia"]["2026-09-10"]["respondidas"] == 1

    def test_faixas_de_tempo_e_mudanca_de_resposta(self, monkeypatch):
        agg = _varrer(monkeypatch, [
            _evento(timestamp="2026-09-10T15:00:00+00:00", tempo=20, acertou=False),
            _evento(timestamp="2026-09-10T15:10:00+00:00", tempo=90, mudou=True),
            _evento(timestamp="2026-09-10T15:20:00+00:00", tempo=400),
        ])
        tel = agg["telemetria_descritiva"]
        assert tel["por_faixa_de_tempo"]["rapido"] == {"respondidas": 1, "acertos": 0}
        assert tel["por_faixa_de_tempo"]["medio"] == {"respondidas": 1, "acertos": 1}
        assert tel["por_faixa_de_tempo"]["longo"] == {"respondidas": 1, "acertos": 1}
        assert tel["por_decisao"]["mudou"] == {"respondidas": 1, "acertos": 1}
        assert tel["por_decisao"]["manteve"] == {"respondidas": 2, "acertos": 1}
        assert tel["respostas_com_tempo"] == 3
        assert tel["tempo_total_segundos"] == 510

    def test_telemetria_nao_entra_no_diagnostico(self, monkeypatch):
        """A fronteira do GL-3 é de código: o caminho que forma crença sobre o
        aluno não vê os campos de `desempenho`."""
        agg = _varrer(monkeypatch, [_evento(timestamp="2026-09-10T15:00:00+00:00")],
                      index=_ITEM_MATEMATICA)
        diagnostico = _run(asvc.compute_diagnostico_real("U1", agregado=agg))
        assert "telemetria_descritiva" not in diagnostico
        assert "tempo" not in str(diagnostico).lower()


# --------------------------------------------------------------------------
# As séries
# --------------------------------------------------------------------------


def _dias(mapa: dict[str, tuple[int, int]]) -> dict[str, dict[str, int]]:
    return {d: {"respondidas": r, "acertos": a} for d, (r, a) in mapa.items()}


class TestSeries:
    def test_dia_parado_aparece_com_volume_zero_e_taxa_nula(self):
        serie = pp._serie_diaria(
            _dias({"2026-09-14": (10, 6), "2026-09-16": (4, 4)}), date(2026, 9, 16)
        )
        assert [l["dia"] for l in serie] == ["2026-09-14", "2026-09-15", "2026-09-16"]
        assert serie[1]["respondidas"] == 0
        assert serie[1]["taxa"] is None
        # A linha acumulada não cai no dia de folga: ela é a vida inteira.
        assert serie[1]["acumulada"] == 60.0
        assert serie[2]["acumulada"] == round(100 * 10 / 14, 1)

    def test_semana_comeca_na_segunda_como_no_resto_do_produto(self):
        serie = pp._serie_semanal(
            _dias({"2026-09-13": (5, 3), "2026-09-14": (5, 5)}), date(2026, 9, 16)
        )
        # 13/09 é domingo: pertence à semana de 07/09, não à de 14/09.
        assert [l["semana"] for l in serie] == ["2026-09-07", "2026-09-14"]
        assert serie[0]["respondidas"] == 5
        assert serie[1]["respondidas"] == 5
        assert serie[1]["corrente"] is True

    def test_comparativo_corta_pela_metade_das_respostas_e_nao_do_tempo(self):
        # 100 respostas em março (50%) e 10 em setembro (90%). O corte por
        # tempo compararia 100 contra 10; o corte por volume compara 55 a 55.
        por_dia = _dias({"2026-03-02": (100, 50), "2026-09-14": (10, 9)})
        c = pp._comparativo(por_dia)
        assert c["suficiente"] is True
        assert c["inicio"]["respondidas"] == 100
        assert c["agora"]["respondidas"] == 10
        assert c["delta"] == round(90.0 - 50.0, 1)

    def test_abaixo_do_minimo_nao_compara_nada(self):
        c = pp._comparativo(_dias({"2026-09-14": (10, 5)}))
        assert c == {"suficiente": False, "minimo": pp.MIN_COMPARATIVO, "respondidas": 10}

    def test_sequencia_continua_viva_no_dia_em_que_ainda_nao_estudou(self):
        con = pp._constancia(
            _dias({"2026-09-14": (3, 2), "2026-09-15": (3, 2)}), date(2026, 9, 16)
        )
        assert con["sequencia"] == 2
        assert con["melhor_sequencia"] == 2
        assert con["dias_ativos"] == 2

    def test_sequencia_zera_depois_de_dois_dias_parados(self):
        con = pp._constancia(_dias({"2026-09-10": (3, 2)}), date(2026, 9, 16))
        assert con["sequencia"] == 0
        assert con["melhor_sequencia"] == 1

    def test_evolucao_por_frente_ignora_matéria_com_amostra_curta(self):
        serie = pp._evolucao_por_frente({
            "matematica|2026-09-07": {"respondidas": 8, "acertos": 4},
            "fisica|2026-09-07": {"respondidas": 1, "acertos": 0},
        }, date(2026, 9, 16))
        assert [s["chave"] for s in serie["series"]] == ["matematica"]
        assert serie["linhas"][0]["matematica"] == 50.0


# --------------------------------------------------------------------------
# A Mentis lendo o painel
# --------------------------------------------------------------------------


def _telemetria_rica() -> dict:
    """Um aluno com história: começou errando, melhorou, estuda à noite e
    perde questão quando responde no impulso."""
    por_dia = {}
    # 30 respostas antigas a 40%.
    por_dia["2026-06-01"] = {"respondidas": 30, "acertos": 12}
    # 30 recentes a 70%.
    por_dia["2026-09-14"] = {"respondidas": 30, "acertos": 21}
    return {
        "por_dia": por_dia,
        "por_hora": {
            **{str(h): {"respondidas": 5, "acertos": 2} for h in (8, 9, 10)},   # manhã: 40%
            **{str(h): {"respondidas": 5, "acertos": 4} for h in (19, 20, 21)},  # noite: 80%
        },
        "por_dia_semana": {"0": {"respondidas": 20, "acertos": 10}},
        "por_faixa_de_tempo": {
            "rapido": {"respondidas": 20, "acertos": 6},   # 30%
            "medio": {"respondidas": 20, "acertos": 12},
            "longo": {"respondidas": 20, "acertos": 14},   # 70%
        },
        "por_decisao": {
            "manteve": {"respondidas": 40, "acertos": 28},  # 70%
            "mudou": {"respondidas": 20, "acertos": 8},     # 40%
        },
        "por_origem": {
            "pratica_questoes": {"respondidas": 50, "acertos": 28},
            "treino_habilidade": {"respondidas": 10, "acertos": 5},
        },
        "frente_por_semana": {"matematica|2026-09-14": {"respondidas": 30, "acertos": 21}},
        "tempo_total_segundos": 4800.0,
        "respostas_com_tempo": 60,
    }


def _painel_rico(**extra):
    prioridades = prioridade_enem.ranking({"matematica": {"respondidas": 30, "acertos": 21}})
    forcas = {
        "pontos_fortes": [{"rotulo": "Ler nas entrelinhas", "explicacao": "Você deduz bem."}],
        "pontos_a_desenvolver": [{"rotulo": "Raciocínio proporcional", "explicacao": "Ainda escapa."}],
    }
    return pp.montar(
        telemetria=_telemetria_rica(),
        prioridades=prioridades,
        forcas=forcas,
        hoje=date(2026, 9, 16),
        **extra,
    )


def _ids(painel) -> list[str]:
    return [l["id"] for l in painel["mentis"]["leituras"]]


class TestLeiturasDaMentis:
    def test_a_primeira_leitura_e_a_mudanca(self):
        painel = _painel_rico()
        primeira = painel["mentis"]["leituras"][0]
        assert primeira["id"] == "evolucao"
        assert primeira["tom"] == "bom"
        assert "30" in primeira["texto"]  # cita a amostra dos dois lados

    def test_le_horario_pressa_e_decisao_quando_ha_amostra(self):
        assert {"horario", "pressa", "decisao"} <= set(_ids(_painel_rico()))

    def test_toda_leitura_tem_ancora_em_um_grafico(self):
        # Os mesmos ids que os cartões de gráfico usam em `components/perfil`.
        ancoras = {"evolucao", "volume", "comparativo", "tendencia", "frentes",
                   "prioridade", "redacao", "ritmo", "tempo", "habitos",
                   "constancia", "forcas"}
        for leitura in _painel_rico()["mentis"]["leituras"]:
            assert leitura["ancora"] in ancoras, leitura
            assert leitura["titulo"] and leitura["texto"]

    def test_aluno_sem_amostra_nao_ouve_palpite(self):
        painel = pp.montar(
            telemetria={"por_dia": {"2026-09-16": {"respondidas": 3, "acertos": 1}},
                        "por_origem": {"pratica_questoes": {"respondidas": 3, "acertos": 1}}},
            prioridades=prioridade_enem.ranking({}),
            forcas={"pontos_fortes": [], "pontos_a_desenvolver": []},
            hoje=date(2026, 9, 16),
        )
        assert painel["amostra_insuficiente"] is True
        # Sem medida não existe leitura sobre horário, pressa ou decisão.
        assert not {"horario", "pressa", "decisao", "evolucao"} & set(_ids(painel))

    def test_queda_e_dita_sem_alarme_e_com_saida(self):
        telemetria = _telemetria_rica()
        telemetria["por_dia"] = {
            "2026-06-01": {"respondidas": 30, "acertos": 24},  # 80%
            "2026-09-14": {"respondidas": 30, "acertos": 12},  # 40%
        }
        painel = pp.montar(
            telemetria=telemetria,
            prioridades=prioridade_enem.ranking({}),
            forcas={"pontos_fortes": [], "pontos_a_desenvolver": []},
            hoje=date(2026, 9, 16),
        )
        queda = next(l for l in painel["mentis"]["leituras"] if l["id"] == "evolucao")
        assert queda["tom"] == "atencao"
        assert queda["acao"]["href"] == "/revisoes"


class TestPainelNaoVazaOntologia:
    """A checagem varre o CATÁLOGO real, como em `test_perfil_pedagogico`: o
    painel tem número por toda parte, e nenhum deles pode ser da ontologia."""

    def _catalogo(self, campo: str) -> list[str]:
        onto = load_ontology()
        valores = []
        for chave in ("dominios", "competencias", "processos_cognitivos",
                      "habilidades_observaveis", "tipos_erro", "intervencoes_pedagogicas"):
            valores.extend(item[campo] for item in (onto.get(chave) or []) if item.get(campo))
        return valores

    def _painel_com_diagnostico_real(self) -> dict:
        onto = load_ontology()
        processos = [p["id"] for p in onto["processos_cognitivos"]]
        stats = {
            pid: {"respondidas": 10, "acertos": 9 if i % 2 == 0 else 1}
            for i, pid in enumerate(processos)
        }
        diagnostico = _run(asvc.compute_diagnostico_real("U1", agregado={
            "dominio_stats": {}, "competencia_stats": {}, "processo_stats": stats,
            "disciplina_stats": {"matematica": {"respondidas": 30, "acertos": 21}},
            "total_events": 250, "matched_events": 250, "unmatched_events": 0,
        }))
        return pp.montar(
            telemetria=_telemetria_rica(),
            prioridades=prioridade_enem.ranking(diagnostico["por_disciplina"]),
            forcas=perfil_pedagogico.perfil_de(diagnostico),
            diagnostico=diagnostico,
            hoje=date(2026, 9, 16),
        )

    def test_nenhum_id_ou_nome_interno_no_painel(self):
        bruto = str(self._painel_com_diagnostico_real())
        for valor in self._catalogo("id") + self._catalogo("nome"):
            assert valor not in bruto, f"vazou {valor!r}"

    def test_as_forcas_continuam_sem_numero_ao_lado(self):
        painel = self._painel_com_diagnostico_real()
        for item in painel["forcas"]["pontos_fortes"] + painel["forcas"]["pontos_a_desenvolver"]:
            assert set(item.keys()) == {"rotulo", "explicacao"}
            assert not re.search(r"\d+%", str(item))

    def test_os_numeros_que_existem_sao_de_frente_e_de_esforco(self):
        painel = self._painel_com_diagnostico_real()
        assert painel["resumo"]["respondidas"] == 60
        assert painel["frentes"]["linhas"][0]["nome"] in {d["nome"] for d in prioridade_enem.DISCIPLINAS}
        assert painel["evolucao"]["comparativo"]["suficiente"] is True


# --------------------------------------------------------------------------
# Tendência, pulso, consistência e redação
# --------------------------------------------------------------------------


class TestTendencia:
    def _semanas(self, frente, pares):
        """`pares` é [(segunda, respondidas, acertos)]."""
        return {f"{frente}|{s}": {"respondidas": r, "acertos": a} for s, r, a in pares}

    def test_compara_quatro_semanas_contra_as_quatro_anteriores(self):
        # hoje = 16/09/2026 (quarta). Bloco recente: 24/08 a 14/09.
        dados = self._semanas("biologia", [
            ("2026-07-27", 10, 4),   # antes: 40%
            ("2026-08-17", 10, 4),
            ("2026-08-31", 10, 7),   # agora: 70%
            ("2026-09-14", 10, 7),
        ])
        linhas = pp._tendencia_por_frente(dados, date(2026, 9, 16))
        assert len(linhas) == 1
        assert linhas[0]["antes"]["taxa"] == 40.0
        assert linhas[0]["agora"]["taxa"] == 70.0
        assert linhas[0]["delta"] == 30.0

    def test_um_lado_com_amostra_curta_nao_vira_tendencia(self):
        """Duas questões no mês passado contra vinte neste não é queda: é
        amostra. A linha some em vez de afirmar."""
        dados = self._semanas("fisica", [
            ("2026-08-17", 2, 2),
            ("2026-09-14", 20, 10),
        ])
        assert pp._tendencia_por_frente(dados, date(2026, 9, 16)) == []

    def test_ordena_do_que_mais_subiu_para_o_que_mais_caiu(self):
        dados = {
            **self._semanas("biologia", [("2026-08-17", 10, 2), ("2026-09-14", 10, 8)]),
            **self._semanas("quimica", [("2026-08-17", 10, 8), ("2026-09-14", 10, 2)]),
        }
        linhas = pp._tendencia_por_frente(dados, date(2026, 9, 16))
        assert [l["chave"] for l in linhas] == ["biologia", "quimica"]
        assert linhas[0]["delta"] > 0 > linhas[-1]["delta"]


class TestPulsoEConsistencia:
    def test_delta_so_existe_com_amostra_dos_dois_lados(self):
        pulso = pp._pulso(_dias({"2026-09-15": (30, 24)}), date(2026, 9, 16))
        assert pulso["taxa_7"] == 80.0
        assert pulso["delta_taxa"] is None, "uma semana sozinha não é comparação"

    def test_delta_compara_a_semana_com_a_anterior(self):
        pulso = pp._pulso(
            _dias({"2026-09-05": (10, 4), "2026-09-15": (10, 7)}), date(2026, 9, 16)
        )
        assert pulso["taxa_7_anterior"] == 40.0
        assert pulso["taxa_7"] == 70.0
        assert pulso["delta_taxa"] == 30.0

    def test_a_minilinha_tem_sempre_catorze_dias(self):
        pulso = pp._pulso(_dias({"2026-09-15": (3, 2)}), date(2026, 9, 16))
        assert len(pulso["dias"]) == 14
        assert pulso["dias"][-1]["dia"] == "2026-09-16"

    def test_consistencia_conta_semanas_com_presenca_nao_questoes(self):
        # Uma questão por semana em 3 semanas vale mais que 100 num dia só.
        con = pp._constancia(
            _dias({"2026-09-01": (1, 1), "2026-09-08": (1, 0), "2026-09-15": (1, 1)}),
            date(2026, 9, 16),
        )
        assert con["semanas_com_estudo"] == 3
        assert con["semanas_na_janela"] == pp.JANELA_CONSISTENCIA

        maratona = pp._constancia(_dias({"2026-09-15": (100, 60)}), date(2026, 9, 16))
        assert maratona["semanas_com_estudo"] == 1


def _avaliacao(nota, criada, comps=None, estimados=0):
    return {
        "nota_total": nota,
        "nota_pontos_estimados": estimados,
        "created_at": criada,
        "estado_geral": "AVALIAVEL",
        "competencias": [
            {"id": cid, "nivel_pontos": pts} for cid, pts in (comps or {}).items()
        ],
    }


class TestRedacao:
    def test_serie_na_ordem_com_melhor_media_e_ultima(self):
        r = pp._redacao([
            _avaliacao(600, "2026-08-01T10:00:00+00:00"),
            _avaliacao(840, "2026-08-20T10:00:00+00:00"),
            _avaliacao(720, "2026-09-10T10:00:00+00:00"),
        ])
        assert r["corrigidas"] == 3
        assert [s["nota"] for s in r["serie"]] == [600, 840, 720]
        assert r["melhor"] == 840
        assert r["ultima"] == 720
        assert r["media"] == 720
        assert r["serie"][0]["rotulo"] == "01/08"

    def test_media_por_competencia_com_amostra(self):
        r = pp._redacao([
            _avaliacao(600, "2026-08-01T10:00:00+00:00", {"COMP-I": 160, "COMP-V": 80}),
            _avaliacao(800, "2026-09-01T10:00:00+00:00", {"COMP-I": 200, "COMP-V": 120}),
        ])
        por_id = {c["id"]: c for c in r["competencias"]}
        assert por_id["COMP-I"]["media"] == 180
        assert por_id["COMP-I"]["ultima"] == 200
        assert por_id["COMP-V"]["media"] == 100
        assert por_id["COMP-V"]["amostra"] == 2
        # Competência que o corretor não devolveu não vira barra zerada.
        assert "COMP-III" not in por_id

    def test_aluno_sem_redacao_devolve_o_mesmo_formato(self):
        """As chaves não podem depender de o aluno ter escrito ou não: a tela
        de quem nunca corrigiu redação é justamente a que precisa montar."""
        vazio = pp._redacao([])
        cheio = pp._redacao([_avaliacao(600, "2026-08-01T10:00:00+00:00")])
        assert set(vazio) == set(cheio)
        assert vazio["corrigidas"] == 0
        assert vazio["melhor"] is None

    def test_a_mentis_convida_quem_nunca_corrigiu(self):
        painel = pp.montar(
            telemetria=_telemetria_rica(),
            prioridades=prioridade_enem.ranking({}),
            forcas={"pontos_fortes": [], "pontos_a_desenvolver": []},
            avaliacoes_redacao=[],
            hoje=date(2026, 9, 16),
        )
        leitura = next(l for l in painel["mentis"]["leituras"] if l["id"] == "redacao")
        assert leitura["acao"]["href"] == "/redacao"

    def test_a_mentis_aponta_a_competencia_mais_fraca(self):
        painel = pp.montar(
            telemetria=_telemetria_rica(),
            prioridades=prioridade_enem.ranking({}),
            forcas={"pontos_fortes": [], "pontos_a_desenvolver": []},
            avaliacoes_redacao=[
                _avaliacao(680, "2026-09-01T10:00:00+00:00",
                           {"COMP-I": 200, "COMP-II": 160, "COMP-V": 40}),
            ],
            hoje=date(2026, 9, 16),
        )
        leitura = next(l for l in painel["mentis"]["leituras"] if l["id"] == "redacao")
        assert "proposta de intervenção" in leitura["texto"].lower()
        assert "680" in leitura["titulo"]


class TestFixtureDoFrontendContinuaEmDia:
    """`frontend/src/components/perfil/__fixtures__/painel.json` é a saída real
    desta função, e o teste da tela monta os onze gráficos contra ele. Se o
    formato daqui mudar e o arquivo não for regerado, a tela passa a ser
    testada contra um contrato que não existe mais — e é justamente aí que o
    campo renomeado atravessa sem ninguém ver."""

    def _fixture(self) -> dict:
        import json

        caminho = (
            BACKEND.parent / "frontend/src/components/perfil/__fixtures__/painel.json"
        )
        return json.loads(caminho.read_text(encoding="utf-8"))

    def test_as_chaves_do_painel_sao_as_mesmas(self):
        atual = _painel_rico()
        antigo = self._fixture()
        assert set(antigo) == set(atual), (
            "regere o fixture: python tests/gerar_fixture_do_painel.py"
        )
        for secao in ("resumo", "evolucao", "frentes", "ritmo", "habitos", "constancia", "redacao"):
            assert set(antigo[secao]) == set(atual[secao]), (
                f"a seção {secao} mudou de formato — regere o fixture"
            )

    def test_o_fixture_tem_historico_de_verdade(self):
        """Um fixture magro passaria nos testes da tela sem exercitar nada: é
        com série cheia que rótulo sobreposto e eixo apertado aparecem."""
        painel = self._fixture()
        assert painel["resumo"]["respondidas"] > 300
        assert len(painel["evolucao"]["diaria"]) >= 60
        assert len(painel["mentis"]["leituras"]) >= 6
        assert painel["redacao"]["corrigidas"] >= 2
