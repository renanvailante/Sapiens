"""Motor Cognitivo — produção e agregação de Error Trace, offline.

O que estes testes travam (nesta ordem de importância):

1. **A ordem da cadeia manda.** A intervenção sai da RAIZ (`ordem: 1`), nunca
   da manifestação. É a única regra do Error Trace v1.0 que altera
   comportamento pedagógico (§1.1) e a que mais fácil se perde numa refatoração.
2. **R-1: nada de vínculo inventado.** Par (erro, processo) fora do catálogo é
   descartado, não "aproximado".
3. **R-3: nada de determinismo.** Elo sem confiança não vira elo com confiança 1.
4. **O portão de crença tem efeito.** Item sem revisão humana não move o perfil
   (§6 / EXT-WP1-1.0 L13b) — que é exatamente o que não acontecia antes.
5. **Nenhuma chamada de IA.** O módulo não importa `ai_service`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import motor_cognitivo as motor  # noqa: E402
import portao_crenca  # noqa: E402


@pytest.fixture(autouse=True)
def _sem_memoria_entre_testes():
    """`_ler_historico` memoriza o histórico por aluno para não estourar a
    cota de leitura do Firestore. Entre testes isso vazaria estado."""
    motor.esquecer_historico()
    yield
    motor.esquecer_historico()


def _evento(event_id="e1", alternativa="B", acertou=False, item_id="I-1", ts="2026-09-01T10:00:00Z"):
    return {
        "event_id": event_id,
        "item_id": item_id,
        "ontology_version": "1.4.1",
        "status": "respondida",
        "timestamp": ts,
        "resposta": {"alternativa_escolhida": alternativa, "acertou": acertou},
    }


def _item(cadeia, *, apto=True, item_id="I-1", alternativa="B"):
    return {
        "item_id": item_id,
        "item_hash": f"h-{item_id}",
        "ontology_version": "1.4.1",
        "fonte": {"banca": "ENEM", "ano": 2023, "prova": "AMARELO", "numero": 93, "tema": "Ondulatória"},
        "estrutura_cognitiva": {"processos": [{"id": "PROC-SIMB-01"}]},
        "qualidade": {"apto_para_camada_de_crenca": {"valor": apto}, "revisado": apto},
        "distratores": [
            {"alternativa": alternativa, "erros_esperados": cadeia, "explicacao": "Confunde área com raio."}
        ],
        "intervencoes": [
            {"id": "INT-02", "gatilho": {"processo": "PROC-SIMB-01", "erro": "ERR-03"},
             "acao": "Diagrama de tradução enunciado→fórmula."}
        ],
        "pedagogia": {"passos": ["Converter unidades.", "Montar a área."], "erros_comuns": ["Esquecer o quadrado."]},
    }


# Cadeia realista: raiz de modelagem (ERR-03/PROC-SIMB-01) que se manifesta
# como inconsistência dimensional (ERR-04/PROC-QUANT-04).
CADEIA = [
    {"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01", "confianca": 0.7, "mecanismo": "MEC-02"},
    {"ordem": 2, "erro": "ERR-04", "processo_afetado": "PROC-QUANT-04", "confianca": 0.4},
]


class TestValidacaoDaCadeia:
    def test_cadeia_valida_preserva_ordem(self):
        elos, motivos = motor._validar_cadeia(CADEIA)
        assert [e["ordem"] for e in elos] == [1, 2]
        assert motivos == []

    def test_par_erro_processo_fora_do_catalogo_e_descartado(self):
        # ERR-03 é catalogado para PROC-SIMB-01, nunca para PROC-TEXT-01 (R-1).
        elos, motivos = motor._validar_cadeia(
            [{"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-TEXT-01", "confianca": 0.7}]
        )
        assert elos == []
        assert any(m.startswith("par-nao-autorizado") for m in motivos)

    def test_elo_sem_confianca_e_invalido_e_nao_vira_1(self):
        elos, motivos = motor._validar_cadeia(
            [{"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01"}]
        )
        assert elos == []
        assert "confianca-ausente-ou-invalida" in motivos

    def test_rotulo_de_confianca_vira_o_bin_declarado(self):
        elos, _ = motor._validar_cadeia(
            [{"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01", "confianca": "alta"}]
        )
        assert elos[0]["confianca"] == 0.7

    def test_ordem_nao_contigua_derruba_a_cadeia_inteira(self):
        elos, motivos = motor._validar_cadeia(
            [
                {"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01", "confianca": 0.7},
                {"ordem": 3, "erro": "ERR-04", "processo_afetado": "PROC-QUANT-04", "confianca": 0.4},
            ]
        )
        assert elos == []
        assert "ordem-nao-contigua" in motivos

    def test_par_repetido_na_mesma_cadeia_e_recusado(self):
        elos, motivos = motor._validar_cadeia(
            [
                {"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01", "confianca": 0.7},
                {"ordem": 2, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01", "confianca": 0.4},
            ]
        )
        assert [e["ordem"] for e in elos] == [1]
        assert "par-repetido-na-cadeia" in motivos

    def test_sentinela_e_elo_valido(self):
        elos, motivos = motor._validar_cadeia(
            [{"ordem": 1, "erro": "erro-nao-catalogado-nesta-versao",
              "processo_afetado": "PROC-ESPACO-01", "confianca": 0.4}]
        )
        assert len(elos) == 1 and motivos == []


class TestProducaoDoTraco:
    def test_acerto_nao_produz_traco(self):
        assert motor.produzir_traco("u1", _evento(acertou=True), _item(CADEIA)) is None

    def test_alternativa_sem_distrator_anotado_nao_produz_traco(self):
        assert motor.produzir_traco("u1", _evento(alternativa="E"), _item(CADEIA)) is None

    def test_traco_tem_os_campos_do_contrato(self):
        t = motor.produzir_traco("u1", _evento(), _item(CADEIA))
        assert t["produtor"] == "regra"
        assert t["etrace_version"] == "1.0"
        assert t["ontology_version"] == "1.4.1"
        assert t["alternativa_escolhida"] == "B"
        assert [e["ordem"] for e in t["cadeia"]] == [1, 2]
        # §5: a confiança global é a da raiz — nunca a soma nem a média.
        assert t["confianca_global"] == 0.7

    def test_trace_id_e_estavel(self):
        a = motor.produzir_traco("u1", _evento(), _item(CADEIA))
        b = motor.produzir_traco("u1", _evento(), _item(CADEIA))
        assert a["trace_id"] == b["trace_id"]
        outro = motor.produzir_traco("u2", _evento(), _item(CADEIA))
        assert outro["trace_id"] != a["trace_id"]


class TestAgregacao:
    def test_raiz_prescreve_intervencao_e_manifestacao_nao(self):
        t = motor.produzir_traco("u1", _evento(), _item(CADEIA))
        mapa = motor._agregar_erros([t])
        raiz = mapa["raizes"][0]
        assert raiz["erro_id"] == "ERR-03"
        assert raiz["intervencao_id"] == "INT-02"  # catálogo: ERR-03 -> INT-02
        manifestacao = mapa["manifestacoes"][0]
        assert manifestacao["erro_id"] == "ERR-04"
        # ERR-04 tem INT-07 no catálogo, mas como manifestação NÃO prescreve nada.
        assert manifestacao["intervencao_id"] is None

    def test_peso_soma_confianca_em_vez_de_contar_ocorrencia(self):
        tracos = [
            motor.produzir_traco("u1", _evento(event_id=f"e{i}"), _item(CADEIA))
            for i in range(3)
        ]
        raiz = motor._agregar_erros(tracos)["raizes"][0]
        assert raiz["ocorrencias"] == 3
        assert raiz["peso"] == pytest.approx(2.1)  # 3 x 0.7, não 3

    def test_sentinela_vai_para_balde_proprio(self):
        cadeia = [{"ordem": 1, "erro": "erro-nao-catalogado-nesta-versao",
                   "processo_afetado": "PROC-ESPACO-01", "confianca": 0.4}]
        t = motor.produzir_traco("u1", _evento(), _item(cadeia))
        mapa = motor._agregar_erros([t])
        assert mapa["raizes"] == []
        assert mapa["sem_catalogo"][0]["ocorrencias"] == 1


class TestPriorizacao:
    def _tracos(self, n):
        return [motor.produzir_traco("u1", _evento(event_id=f"e{i}"), _item(CADEIA)) for i in range(n)]

    def test_uma_ocorrencia_nao_sustenta_padrao(self):
        fila = motor._priorizar(self._tracos(1), {})
        assert [l for l in fila if l["origem"] == "error_trace"] == []

    def test_duas_ocorrencias_entram_com_intervencao(self):
        fila = motor._priorizar(self._tracos(2), {"PROC-SIMB-01": {"respondidas": 4, "acertos": 1}})
        linha = fila[0]
        assert linha["processo_id"] == "PROC-SIMB-01"
        assert linha["origem"] == "error_trace"
        assert linha["intervencao"]["id"] == "INT-02"
        assert linha["percentual_acerto"] == 25.0
        assert linha["dominio_id"] and linha["competencia_id"]

    def test_desempenho_puro_vem_depois_e_sem_intervencao(self):
        stats = {
            "PROC-SIMB-01": {"respondidas": 4, "acertos": 1},
            "PROC-TEXT-01": {"respondidas": 10, "acertos": 1},   # abaixo da média -> entra
            "PROC-LOGICO-01": {"respondidas": 10, "acertos": 10},  # acima da média -> não entra
        }
        fila = motor._priorizar(self._tracos(2), stats)
        origens = [l["origem"] for l in fila]
        assert origens[0] == "error_trace"
        assert "desempenho" in origens
        assert origens.index("error_trace") < origens.index("desempenho")
        por_desempenho = [l for l in fila if l["origem"] == "desempenho"]
        assert [l["processo_id"] for l in por_desempenho] == ["PROC-TEXT-01"]
        assert all(l["intervencao"] is None for l in por_desempenho)


class TestPortaoDeCrenca:
    def test_item_sem_revisao_nao_move_o_perfil(self, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_CRENCA, raising=False)
        t = motor.produzir_traco("u1", _evento(), _item(CADEIA, apto=False))
        aptos, barrados = motor._particionar_pelo_portao([t])
        assert aptos == [] and len(barrados) == 1

    def test_modo_desligado_deixa_passar(self, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_DESLIGADO, raising=False)
        t = motor.produzir_traco("u1", _evento(), _item(CADEIA, apto=False))
        aptos, barrados = motor._particionar_pelo_portao([t])
        assert len(aptos) == 1 and barrados == []


class TestPerfilCompleto:
    def test_perfil_avisa_quando_o_portao_barrou_tudo(self, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_CRENCA, raising=False)
        tracos = [motor.produzir_traco("u1", _evento(event_id=f"e{i}"), _item(CADEIA, apto=False)) for i in range(2)]
        monkeypatch.setattr(
            motor, "_ler_historico",
            lambda uid: {
                "tracos": tracos, "processo_stats": {}, "itens_respondidos": set(),
                "eventos": 5, "respondidos": 5, "eventos_com_item": 5, "erros": 2,
            },
        )
        p = motor.perfil("u1")
        assert p["portao"]["tracos_barrados"] == 2
        assert p["portao"]["tracos_no_perfil"] == 0
        assert p["habilidades_prioritarias"] == []
        assert p["aviso"] and "revisão humana" in p["aviso"]

    def test_perfil_com_tracos_aptos_lista_habilidade_e_intervencao(self, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_CRENCA, raising=False)
        tracos = [motor.produzir_traco("u1", _evento(event_id=f"e{i}"), _item(CADEIA)) for i in range(2)]
        monkeypatch.setattr(
            motor, "_ler_historico",
            lambda uid: {
                "tracos": tracos, "processo_stats": {"PROC-SIMB-01": {"respondidas": 4, "acertos": 1}},
                "itens_respondidos": {"I-1"},
                "eventos": 4, "respondidos": 4, "eventos_com_item": 4, "erros": 2,
            },
        )
        p = motor.perfil("u1")
        assert p["aviso"] is None
        assert p["cobertura"]["percentual"] == 100.0
        assert p["habilidades_prioritarias"][0]["intervencao"]["id"] == "INT-02"
        assert p["mapa_de_erros"]["mecanismos_observados"] == {"MEC-02": 2}


class TestSemIA:
    def test_modulo_nao_depende_de_ai_service(self):
        fonte = (BACKEND / "motor_cognitivo.py").read_text(encoding="utf-8")
        assert "import ai_service" not in fonte
        assert "gemini" not in fonte.lower()
        fonte_int = (BACKEND / "intervencoes.py").read_text(encoding="utf-8")
        assert "import ai_service" not in fonte_int


class TestIntervencao:
    """A intervenção só pode ser montada a partir do catálogo e do que o
    próprio aluno já respondeu — e a sugestão de prática nunca pode carregar
    resolução junto (seria gabarito antecipado)."""

    @pytest.fixture()
    def indexado(self, monkeypatch):
        import annotation_service
        respondido = _item(CADEIA, item_id="I-1")
        futuro = _item(CADEIA, item_id="I-2")
        futuro["fonte"] = {**futuro["fonte"], "numero": 94}
        monkeypatch.setattr(
            annotation_service, "_build_item_index",
            lambda force=False: {"I-1": respondido, "h-I-1": respondido, "I-2": futuro, "h-I-2": futuro},
        )
        return None

    def test_plano_usa_a_acao_escrita_para_o_item_errado(self, indexado):
        import intervencoes
        tracos = [motor.produzir_traco("u1", _evento(event_id=f"e{i}"), _item(CADEIA)) for i in range(2)]
        plano = intervencoes.montar(processo_id="PROC-SIMB-01", tracos=tracos, itens_respondidos={"I-1"})
        assert plano["intervencao_id"] == "INT-02"
        assert plano["intervencao_nome"]  # vem do catálogo, não deste módulo
        assert plano["acoes_do_seu_historico"][0]["acao"].startswith("Diagrama de tradução")
        assert plano["resolucoes_do_seu_historico"][0]["passos"]

    def test_pratica_sugerida_nao_carrega_resolucao(self, indexado):
        import intervencoes
        pratica = intervencoes.sugerir_pratica("PROC-SIMB-01", itens_respondidos={"I-1"})
        assert [i["item_id"] for i in pratica["itens"]] == ["I-2"]
        sugerido = pratica["itens"][0]
        assert set(sugerido) == {"item_id", "banca", "ano", "prova", "numero", "tema"}

    def test_sem_traco_degrada_sem_inventar_intervencao(self, indexado):
        import intervencoes
        plano = intervencoes.montar(processo_id="PROC-SIMB-01", tracos=[], itens_respondidos=set())
        assert plano["origem"] == "sem_traco"
        assert plano["intervencao_id"] is None
        assert plano["como_praticar"]


class TestProvisorioComPortaoDesligado:
    """Com `PORTAO_CRENCA_MODO=desligado` (modo do piloto), traço sem revisão
    humana ENTRA no perfil — mas nunca como fato. O rótulo `provisorio` é o
    que impede que desligar o bloqueio equivalha a revogar a regra do §6."""

    @pytest.fixture(autouse=True)
    def _desligado(self, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_DESLIGADO, raising=False)

    def _historico(self, apto):
        tracos = [
            motor.produzir_traco("u1", _evento(event_id=f"e{i}"), _item(CADEIA, apto=apto))
            for i in range(2)
        ]
        return {
            "tracos": tracos,
            "processo_stats": {"PROC-SIMB-01": {"respondidas": 4, "acertos": 1}},
            "itens_respondidos": {"I-1"},
            "eventos": 4, "respondidos": 4, "eventos_com_item": 4, "erros": 2,
        }

    def test_traco_sem_revisao_entra_mas_marcado(self, monkeypatch):
        monkeypatch.setattr(motor, "_ler_historico", lambda uid: self._historico(apto=False))
        p = motor.perfil("u1")
        assert p["portao"]["tracos_no_perfil"] == 2
        assert p["portao"]["tracos_barrados"] == 0
        assert p["portao"]["tracos_provisorios"] == 2
        assert p["provisorio"] is True
        assert "provisória" in p["aviso"]
        linha = p["habilidades_prioritarias"][0]
        assert linha["provisorio"] is True
        assert linha["ocorrencias_provisorias"] == 2
        # A intervenção continua saindo da raiz — a regra do motor não mudou.
        assert linha["intervencao"]["id"] == "INT-02"

    def test_corpus_revisado_nao_e_marcado_provisorio(self, monkeypatch):
        monkeypatch.setattr(motor, "_ler_historico", lambda uid: self._historico(apto=True))
        p = motor.perfil("u1")
        assert p["provisorio"] is False
        assert p["portao"]["tracos_provisorios"] == 0
        assert p["aviso"] is None
        assert p["habilidades_prioritarias"][0]["provisorio"] is False

    def test_linha_de_desempenho_nunca_e_provisoria(self, monkeypatch):
        """Contagem de acerto não é atribuição de causa: ela não depende de
        revisão de anotação para ser verdadeira."""
        hist = self._historico(apto=False)
        hist["processo_stats"]["PROC-TEXT-01"] = {"respondidas": 10, "acertos": 1}
        hist["processo_stats"]["PROC-LOGICO-01"] = {"respondidas": 10, "acertos": 10}
        monkeypatch.setattr(motor, "_ler_historico", lambda uid: hist)
        p = motor.perfil("u1")
        por_desempenho = [l for l in p["habilidades_prioritarias"] if l["origem"] == "desempenho"]
        assert por_desempenho and all(l["provisorio"] is False for l in por_desempenho)


class TestFalhaDeLeitura:
    """Firestore fora do ar não pode virar "você ainda não praticou".

    O custo de leitura em si (não varrer o histórico duas vezes) é travado por
    `TestMemoriaDoMotor`, em `tests/test_custo_firestore.py`, contando leituras
    reais — não se duplica a garantia aqui.
    """

    def test_cota_estourada_vira_indisponivel_e_nao_aluno_sem_dados(self, monkeypatch):
        chamadas = {"n": 0}

        def _explode(uid):
            chamadas["n"] += 1
            raise RuntimeError("429 Quota exceeded")

        monkeypatch.setattr(motor, "_ler_historico", _explode)
        p1 = motor.perfil("u1")
        p2 = motor.perfil("u1")
        assert chamadas["n"] == 2, "a falha nunca pode ser memorizada"
        assert p1["indisponivel"] is True
        assert "tente de novo" in p1["aviso"]
        assert p2["indisponivel"] is True

    def test_leitura_boa_nao_escreve_na_memoria_de_ler_historico(self, monkeypatch):
        """`falha_de_leitura` é do envelope, não do dicionário memorizado."""
        memorizado = {
            "tracos": [], "processo_stats": {}, "itens_respondidos": set(),
            "eventos": 0, "respondidos": 0, "eventos_com_item": 0, "erros": 0,
        }
        monkeypatch.setattr(motor, "_ler_historico", lambda uid: memorizado)
        assert motor._historico("u1")["falha_de_leitura"] is False
        assert "falha_de_leitura" not in memorizado


class TestSentinelaNaFila:
    """Sentinela como raiz é evidência legítima (R-2) mas não prescreve nada.
    Ela aparece — esconder evidência seria pior — porém abaixo das linhas que
    têm intervenção catalogada, para o aluno não abrir primeiro a que não tem
    o que fazer."""

    def _traco_sentinela(self, i):
        cadeia = [{"ordem": 1, "erro": "erro-nao-catalogado-nesta-versao",
                   "processo_afetado": "PROC-ESPACO-01", "confianca": 0.7}]
        return motor.produzir_traco("u1", _evento(event_id=f"s{i}"), _item(cadeia))

    def test_sentinela_vem_depois_mesmo_com_peso_maior(self):
        tracos = [self._traco_sentinela(i) for i in range(3)]  # peso 2.1
        tracos += [motor.produzir_traco("u1", _evento(event_id=f"e{i}"), _item(CADEIA)) for i in range(2)]  # peso 1.4
        fila = motor._priorizar(tracos, {})
        assert fila[0]["processo_id"] == "PROC-SIMB-01"
        assert fila[0]["sem_intervencao_catalogada"] is False
        assert fila[1]["processo_id"] == "PROC-ESPACO-01"
        assert fila[1]["sem_intervencao_catalogada"] is True
        assert fila[1]["erro_dominante"]["sem_catalogo"] is True
        assert fila[1]["intervencao"] is None


class TestPanoramaNaoMenteQuandoTrunca:
    """`/motor/panorama` tem teto de leitura porque a cota é finita. Um teto
    que corta a base em silêncio produz um retrato falso com cara de completo
    — o mesmo defeito que fazia alunos sumirem de `list_students_with_behavior`."""

    class _Snap:
        def __init__(self, dados):
            self._d = dados

        def to_dict(self):
            return self._d

    class _Query:
        def __init__(self, docs):
            self._docs = docs

        def limit(self, n):
            return TestPanoramaNaoMenteQuandoTrunca._Query(self._docs[:n])

        def stream(self):
            return iter(self._docs)

    class _Cliente:
        def __init__(self, docs):
            self._docs = docs

        def collection_group(self, _nome):
            return TestPanoramaNaoMenteQuandoTrunca._Query(self._docs)

    def _montar(self, monkeypatch, n_eventos):
        import annotation_service
        docs = [
            self._Snap({"student_id": "U1", "status": "respondida",
                        "resposta": {"acertou": True}})
            for _ in range(n_eventos)
        ]
        monkeypatch.setattr(motor.fs, "get_firestore", lambda: self._Cliente(docs))
        monkeypatch.setattr(annotation_service, "_build_item_index", lambda force=False: {})

    def test_avisa_quando_bate_no_teto(self, monkeypatch):
        self._montar(monkeypatch, n_eventos=50)
        p = motor.panorama(limite_eventos=10)
        assert p["truncado"] is True
        assert p["eventos_vistos"] == 10
        assert p["limite_eventos"] == 10

    def test_base_inteira_lida_nao_e_marcada_truncada(self, monkeypatch):
        self._montar(monkeypatch, n_eventos=5)
        p = motor.panorama(limite_eventos=10)
        assert p["truncado"] is False
        assert p["eventos_vistos"] == 5
