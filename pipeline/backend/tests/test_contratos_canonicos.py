"""Testes dos contratos canônicos — Schema Sapiens 2.2 e Error Trace v1.0.

Cada teste cita a cláusula que verifica. Um teste que falhe aqui indica
divergência entre o código e `pipeline/docs/`, nunca "expectativa desatualizada":
o documento é a fonte, o teste é derivado.

Estes testes não dependem de rede, Mongo, Firestore nem Gemini.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from item_contract import build_item_id, compute_item_hash, index_fields, normalize_item  # noqa: E402
from ontology_validator import (  # noqa: E402
    MAX_ELOS,
    MAX_PROCESSOS_COM_PESO,
    OntologyRegistry,
    derivar_estrutura,
    pode_alimentar_crenca,
    validate_error_trace,
    validate_item_annotation,
)


@pytest.fixture(scope="module")
def reg() -> OntologyRegistry:
    return OntologyRegistry()


@pytest.fixture
def item_valido() -> dict:
    """Exemplo 3 do Manual §9: leitura de gráfico + relação proporcional."""
    return {
        "fonte": {"banca": "INEP", "ano": 2024, "prova": "ENEM-CAD01", "numero": 23,
                  "disciplina": "Química", "tema": "Cinética química"},
        "questao": {
            "enunciado": "O gráfico mostra a concentração do reagente ao longo do tempo.",
            "alternativas": [
                {"letra": "A", "texto": "0,5 mol", "correta": False},
                {"letra": "B", "texto": "1,0 mol", "correta": True},
                {"letra": "C", "texto": "2,0 mol", "correta": False},
            ],
            "recursos": {"graficos": [{"id": "GRA-01", "descricao": "concentração x tempo"}]},
        },
        "estrutura_cognitiva": {
            "processos": [
                {
                    "id": "PROC-QUANT-02", "papel": "nuclear", "peso_no_item": 0.7,
                    "confianca": "alta",
                    "habilidades": [{"id": "HAB-03", "peso_no_processo": 1.0,
                                     "confianca": "alta", "aproximado": False}],
                    "evidencias": {"trechos": ["quantidade de produto formado"],
                                   "figuras": ["GRA-01"]},
                    "justificativa": "A resposta exige aplicar relação proporcional "
                                     "sobre o valor lido no gráfico.",
                },
                {
                    "id": "PROC-TEXT-01", "papel": "secundario", "peso_no_item": 0.3,
                    "confianca": "media", "habilidades": [],
                    "evidencias": {"trechos": ["o gráfico mostra"], "figuras": ["GRA-01"]},
                },
            ]
        },
        "distratores": [
            {
                "alternativa": "C",
                "erros_esperados": [
                    {"ordem": 1, "erro": "ERR-01", "processo_afetado": "PROC-TEXT-01",
                     "confianca": "media"},
                    {"ordem": 2, "erro": "ERR-05", "processo_afetado": "PROC-QUANT-02",
                     "confianca": "alta", "mecanismo": "MEC-02"},
                ],
                "plausibilidade": {"valor": "alta"},
                "explicacao": "Lê o valor errado no gráfico e aplica a proporção sobre ele.",
            }
        ],
        "intervencoes": [
            {"id": "INT-01", "gatilho": {"processo": "PROC-TEXT-01", "erro": "ERR-01"},
             "acao": "Prática de leitura literal com verificação de dado explícito."},
        ],
    }


def _norm(item: dict, reg: OntologyRegistry) -> dict:
    return normalize_item(item, reg.data, registry=reg)


# ---------------------------------------------------------------- catálogo
def test_catalogo_e_1_4_1_com_128_ids(reg):
    """Ontologia v1.4.1: 11 + 12 + 25 + 56 + 13 + 11 = 128 identificadores."""
    assert reg.version == "1.4.1"
    total = (len(reg.dominios) + len(reg.competencias) + len(reg.processos)
             + len(reg.habilidades) + len(reg.tipos_erro) + len(reg.intervencoes))
    assert (len(reg.dominios), len(reg.competencias), len(reg.processos)) == (11, 12, 25)
    assert (len(reg.habilidades), len(reg.tipos_erro), len(reg.intervencoes)) == (56, 13, 11)
    assert total == 128


def test_err13_desvinculado_de_proc_espaco_03(reg):
    """TX-2026-08-17T043240Z-patch-err13 — a única mudança de conteúdo da 1.4.1.

    A Ontologia registra explicitamente que PROC-ESPACO-03 ainda não tem Tipo de
    Erro catalogado; o vínculo indevido vinha do artefato JSON.
    """
    proc = reg.get("processos_cognitivos", "PROC-ESPACO-03")
    assert proc["tipos_erro"] == []
    assert reg.get("tipos_erro", "ERR-13")["processos_cognitivos"] == ["PROC-CLASSIF-01"]


def test_treze_de_vinte_e_cinco_processos_sem_tipo_erro(reg):
    """Manual §11 lista nominalmente os 13 processos sem erro catalogado."""
    esperado = {
        "PROC-QUANT-01", "PROC-ESPACO-01", "PROC-ESPACO-02", "PROC-ESPACO-03",
        "PROC-MUD-01", "PROC-MUD-02", "PROC-INC-01", "PROC-INC-02", "PROC-INC-04",
        "PROC-TEXT-03", "PROC-EXP-01", "PROC-SIST-01", "PROC-SIST-02",
    }
    assert reg.processos_sem_tipo_erro() == esperado


def test_relacao_erro_processo_e_bidirecional(reg):
    """Um vínculo declarado num sentido e não no outro é a falha que a 1.4.1 corrigiu."""
    for err in reg.data["tipos_erro"]:
        for pid in err.get("processos_cognitivos", []):
            assert err["id"] in (reg.get("processos_cognitivos", pid) or {}).get("tipos_erro", []), (
                f"{err['id']} lista {pid}, mas {pid} não lista {err['id']}"
            )


# ------------------------------------------------ carimbo obrigatório
def test_ontology_version_e_carimbada_pelo_servidor(item_valido, reg):
    """GOV-1.0 §6.1 — nenhum artefato pode referir-se a 'a ontologia vigente'."""
    item_valido["ontology_version"] = "9.9.9-mentira-do-modelo"
    item = _norm(item_valido, reg)
    assert item["ontology_version"] == reg.version
    assert item["schema_version"] == "2.2"


def test_ontology_version_ausente_invalida(item_valido, reg):
    item = _norm(item_valido, reg)
    del item["ontology_version"]
    res = validate_item_annotation(item, reg)
    assert not res.valid
    assert any("ontology_version" in e for e in res.errors)


# ------------------------------------------------------------ identidade
def test_item_id_deterministico_quando_a_fonte_esta_completa(item_valido, reg):
    """Schema 2.2: formato determinístico baseado em fonte/ano/prova/número."""
    a = _norm(copy.deepcopy(item_valido), reg)
    b = _norm(copy.deepcopy(item_valido), reg)
    assert a["item_id"] == b["item_id"] == "ITEM-INEP-2024-ENEMCAD01-Q023"


def test_item_id_e_estavel_quando_o_conteudo_muda(item_valido, reg):
    """`item_id` rastreia identidade; `item_hash` rastreia conteúdo.

    Se o id fosse derivado do conteúdo, corrigir uma vírgula do enunciado criaria
    um item novo e romperia todo evento de behavior já gravado contra ele.
    """
    antes = _norm(copy.deepcopy(item_valido), reg)
    mudado = copy.deepcopy(item_valido)
    mudado["questao"]["enunciado"] += " (revisado)"
    depois = _norm(mudado, reg)
    assert depois["item_id"] == antes["item_id"]
    assert depois["item_hash"] != antes["item_hash"]


def test_item_id_opaco_e_preservado_quando_a_fonte_e_incompleta(item_valido, reg):
    sem_fonte = copy.deepcopy(item_valido)
    sem_fonte["fonte"] = {"disciplina": "Química"}
    primeiro = _norm(sem_fonte, reg)
    assert primeiro["item_id"].startswith("ITEM-")
    reprocessado = normalize_item(sem_fonte, reg.data, item_id=primeiro["item_id"], registry=reg)
    assert reprocessado["item_id"] == primeiro["item_id"]


def test_item_hash_ignora_a_classificacao_cognitiva(item_valido, reg):
    """Reanotar um item não muda o item que o estudante respondeu."""
    antes = _norm(copy.deepcopy(item_valido), reg)
    reanotado = copy.deepcopy(item_valido)
    reanotado["estrutura_cognitiva"]["processos"][0]["justificativa"] = "outra redação"
    assert _norm(reanotado, reg)["item_hash"] == antes["item_hash"]


def test_build_item_id_sem_fonte_gera_ids_distintos():
    assert build_item_id({}) != build_item_id({})


def test_compute_item_hash_independe_da_ordem_das_chaves():
    assert compute_item_hash({"a": 1, "b": 2}) == compute_item_hash({"b": 2, "a": 1})


# ------------------------------------------------------------- derivação
def test_dominios_e_competencias_sao_derivados_nao_atribuidos(item_valido, reg):
    """Constituição §4.4 proíbe atribuição direta de Domínio a Competência."""
    item_valido["estrutura_cognitiva"]["dominios"] = [{"id": "DOM-CAUSAL"}]
    item_valido["estrutura_cognitiva"]["competencias"] = [{"id": "COMP-09"}]
    item = _norm(item_valido, reg)
    ec = item["estrutura_cognitiva"]
    assert [d["id"] for d in ec["dominios"]] == ["DOM-QUANT", "DOM-TEXTUAL"]
    assert [c["id"] for c in ec["competencias"]] == ["COMP-01", "COMP-09"]
    assert validate_item_annotation(item, reg).valid


def test_peso_derivado_soma_o_peso_dos_processos_sustentadores(item_valido, reg):
    ec = _norm(item_valido, reg)["estrutura_cognitiva"]
    pesos = {d["id"]: d["peso_no_item"] for d in ec["dominios"]}
    assert pesos == {"DOM-QUANT": 0.7, "DOM-TEXTUAL": 0.3}
    assert {d["id"]: d["derivado_de"] for d in ec["dominios"]} == {
        "DOM-QUANT": ["PROC-QUANT-02"], "DOM-TEXTUAL": ["PROC-TEXT-01"],
    }


def test_derivacao_de_lista_vazia_nao_quebra(reg):
    assert derivar_estrutura([], reg) == ([], [])


def test_peso_derivado_e_declarado_nao_evidencial(item_valido, reg):
    """Constituição §4.5 — Processo↔Domínio e Processo↔Competência são relações
    de **classificação/organização**: "peso é opcional e reservado a refinamento
    futuro (ex.: centralidade), nunca obrigatório, porque a função destas
    relações é navegação e agrupamento, **não evidência**".

    Emitir esses números nus faria um consumidor tomá-los por quantidades
    evidenciais. O estatuto viaja junto com o dado em vez de depender de o
    consumidor conhecer a Constituição.
    """
    ec = _norm(item_valido, reg)["estrutura_cognitiva"]
    for bloco in ec["dominios"] + ec["competencias"]:
        assert bloco["_estatuto"]["evidencial"] is False
        assert bloco["_estatuto"]["natureza"] == "classificacao_organizacao"
        assert "4.5" in bloco["_estatuto"]["autoridade"]


def test_funcao_de_heranca_de_confianca_e_declarada_provisoria(item_valido, reg):
    """GOV-1.0 §6.4 — regra de não-antecipação.

    O Schema 2.2 diz "confiança herdada dos processos" e não define a função de
    herança; nenhum documento de camada superior a define — o White Paper 2.0.1
    §4.2 registra que o Axioma da Crença Calibrada "não exige nenhuma família
    matemática específica". A média é decisão de engenharia, e o §6.4 exige que
    ela seja marcada explicitamente em vez de inserida silenciosamente.
    """
    dom = _norm(item_valido, reg)["estrutura_cognitiva"]["dominios"][0]
    assert dom["_estatuto"]["metodo_confianca_provisorio"] is True
    assert dom["_estatuto"]["metodo_confianca"] == "media_dos_processos_sustentadores"


def test_unica_confianca_evidencial_e_a_do_elo_de_erro(item_valido, reg):
    """A distinção que a 2.1 colapsava: `probabilidade_estimada` é sobre ESCOLHA
    da alternativa pela população; a distribuição sobre causas candidatas vive em
    `erros_esperados[].confianca`. Confundir as duas foi a razão pela qual a 2.1
    parecia satisfazer o Axioma da Crença Calibrada sem satisfazê-lo.
    """
    item = _norm(item_valido, reg)
    elo = item["distratores"][0]["erros_esperados"][0]
    assert "_estatuto" not in elo  # confiança de elo é evidencial, sem ressalva
    assert isinstance(elo["confianca"], float)


# ------------------------------------------------------- regras do Manual
def test_item_bem_formado_e_valido(item_valido, reg):
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert res.valid, res.errors
    assert not res.warnings, res.warnings


def test_papel_facilitador_foi_removido_na_2_2(item_valido, reg):
    """Manual §5: processo que apenas facilita falha o teste de necessidade."""
    item_valido["estrutura_cognitiva"]["processos"][1]["papel"] = "facilitador"
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("facilitador" in e for e in res.errors)


@pytest.mark.parametrize("rotulo", ["Central", "Secundário Necessário", "nucleo", ""])
def test_vocabulario_de_papel_e_fechado(item_valido, reg, rotulo):
    """Error Trace §7 — reconciliação: prevalece `nuclear` | `secundario`."""
    item_valido["estrutura_cognitiva"]["processos"][0]["papel"] = rotulo
    assert not validate_item_annotation(_norm(item_valido, reg), reg).valid


def test_no_maximo_dois_processos_com_peso(item_valido, reg):
    """Manual §4 — um terceiro candidato vira ambiguidade, não terceiro peso."""
    item_valido["estrutura_cognitiva"]["processos"].append(
        {"id": "PROC-MUD-01", "papel": "secundario", "peso_no_item": 0.2, "habilidades": []}
    )
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any(str(MAX_PROCESSOS_COM_PESO) in e and "Manual §4" in e for e in res.errors)


def test_pesos_somam_um(item_valido, reg):
    item_valido["estrutura_cognitiva"]["processos"][1]["peso_no_item"] = 0.5
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("somar 1.0" in e for e in res.errors)


def test_exatamente_um_processo_nuclear(item_valido, reg):
    item_valido["estrutura_cognitiva"]["processos"][1]["papel"] = "nuclear"
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("nuclear" in e and "exatamente 1" in e for e in res.errors)


def test_justificativa_obrigatoria_no_processo_nuclear(item_valido, reg):
    """Manual §12, regra 4."""
    item_valido["estrutura_cognitiva"]["processos"][0]["justificativa"] = "   "
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("justificativa" in e for e in res.errors)


def test_habilidade_deve_pertencer_ao_catalogo_do_processo_pai(item_valido, reg):
    """Manual §6, regra 1 — HAB-46 é de leitura de gráfico, não de proporção."""
    item_valido["estrutura_cognitiva"]["processos"][0]["habilidades"].append({"id": "HAB-46"})
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("HAB-46" in e and "PROC-QUANT-02" in e for e in res.errors)


def test_id_inexistente_e_rejeitado(item_valido, reg):
    item_valido["estrutura_cognitiva"]["processos"][0]["id"] = "PROC-QUANT-99"
    assert not validate_item_annotation(_norm(item_valido, reg), reg).valid


def test_truncamento_de_id_g1_para_g3_e_rejeitado(item_valido, reg):
    """NS-3, BLOQUEANTE — `PROC-QUANT-001` (G1) não é `PROC-QUANT-01` (G3)."""
    item_valido["estrutura_cognitiva"]["processos"][0]["id"] = "PROC-QUANT-001"
    assert not validate_item_annotation(_norm(item_valido, reg), reg).valid


# ---------------------------------------------------- cadeia de erro (2.2)
def test_campo_erro_unico_da_2_1_e_rejeitado(item_valido, reg):
    """Constituição §4.4 — proibida cardinalidade determinística de valor único."""
    item_valido["distratores"][0]["erro"] = "ERR-05"
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("REMOVIDO na 2.2" in e for e in res.errors)


def test_processos_afetados_da_2_1_e_rejeitado(item_valido, reg):
    item_valido["distratores"][0]["processos_afetados"] = ["PROC-QUANT-02"]
    assert not validate_item_annotation(_norm(item_valido, reg), reg).valid


def test_confianca_obrigatoria_em_todo_elo(item_valido, reg):
    """Error Trace §3, R-3 — Axioma da Crença Calibrada."""
    del item_valido["distratores"][0]["erros_esperados"][0]["confianca"]
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("R-3" in e for e in res.errors)


def test_ordem_deve_ser_contigua_a_partir_de_um(item_valido, reg):
    """Error Trace R-5 — um traço de dois elos usa 1 e 2, nunca 1 e 3."""
    item_valido["distratores"][0]["erros_esperados"][1]["ordem"] = 3
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("R-5" in e for e in res.errors)


def test_cadeia_nao_passa_de_tres_elos(item_valido, reg):
    """Error Trace R-4 — profundidade máxima [DE, provisório]."""
    elos = item_valido["distratores"][0]["erros_esperados"]
    elos.append({"ordem": 3, "erro": "ERR-03", "processo_afetado": "PROC-QUANT-03",
                 "confianca": "baixa"})
    elos.append({"ordem": 4, "erro": "ERR-04", "processo_afetado": "PROC-QUANT-04",
                 "confianca": "baixa"})
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any(f"máximo {MAX_ELOS}" in e for e in res.errors)


def test_erro_emprestado_de_outro_processo_e_rejeitado(item_valido, reg):
    """Error Trace R-1 / Manual §7, regra 4 — o catálogo é a fonte da possibilidade."""
    item_valido["distratores"][0]["erros_esperados"][1]["processo_afetado"] = "PROC-TEXT-01"
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert not res.valid
    assert any("não existe no catálogo" in e for e in res.errors)


def test_sentinelas_sao_valores_de_primeira_classe(item_valido, reg):
    """Error Trace R-2 — sentinela é elo válido e informativo, não dado ausente."""
    item_valido["estrutura_cognitiva"]["processos"] = [
        {"id": "PROC-EXP-01", "papel": "nuclear", "peso_no_item": 1.0, "confianca": "alta",
         "habilidades": [], "justificativa": "O item pede formular hipótese testável."}
    ]
    item_valido["distratores"][0]["erros_esperados"] = [
        {"ordem": 1, "erro": "erro-nao-catalogado-nesta-versao",
         "processo_afetado": "PROC-EXP-01", "confianca": "media"}
    ]
    item_valido["intervencoes"] = []
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert res.valid, res.errors


def test_sentinela_em_processo_com_catalogo_gera_aviso(item_valido, reg):
    item_valido["distratores"][0]["erros_esperados"][1]["erro"] = "erro-nao-catalogado-nesta-versao"
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert res.valid
    assert any("sentinela" in w for w in res.warnings)


def test_validacao_rejeita_mecanismo_fora_de_mec_01_13(item_valido, reg):
    """Error Trace §4.3 — prefixo MEC- escolhido para não recriar a colisão NS-1.

    Verificado direto no validador: a normalização remove o valor inválido antes
    (teste seguinte), mas a regra de contrato tem de valer para quem grave o item
    por outro caminho.
    """
    item = _norm(item_valido, reg)
    item["distratores"][0]["erros_esperados"][1]["mecanismo"] = "ERR-02"
    assert not validate_item_annotation(item, reg).valid


def test_normalizacao_descarta_mecanismo_invalido_sem_perder_o_item(item_valido, reg):
    """`mecanismo` é OPCIONAL e PROVISÓRIO (Error Trace §4.2): "nenhuma anotação
    é inválida por omiti-lo".

    Quando o modelo escreve prosa ali — e escreve: numa prova real devolveu
    "Falha em localizar dado explicito" —, descartar o campo preserva a anotação
    inteira. Invalidar o item por um campo que poderia simplesmente não existir
    jogaria fora a classificação cognitiva toda por nada.
    """
    item_valido["distratores"][0]["erros_esperados"][1]["mecanismo"] = "Falha em localizar dado"
    item = _norm(item_valido, reg)
    assert "mecanismo" not in item["distratores"][0]["erros_esperados"][1]
    assert validate_item_annotation(item, reg).valid


def test_normalizacao_preserva_mecanismo_valido(item_valido, reg):
    item = _norm(item_valido, reg)
    assert item["distratores"][0]["erros_esperados"][1]["mecanismo"] == "MEC-02"


def test_letra_da_alternativa_e_normalizada_para_maiuscula(item_valido, reg):
    """O modelo devolve ora 'A', ora 'a'. A letra é comparada com o gabarito
    oficial e com a resposta do aluno — divergir por caixa marca errado quem
    acertou, sem erro visível."""
    for alt in item_valido["questao"]["alternativas"]:
        alt["letra"] = alt["letra"].lower()
    item_valido["distratores"][0]["alternativa"] = "c"
    item = _norm(item_valido, reg)
    assert [a["letra"] for a in item["questao"]["alternativas"]] == ["A", "B", "C"]
    assert index_fields(item)["resposta_correta"] == "B"
    # os dois lados do par: normalizar só um faz o distrator deixar de casar
    # com a alternativa que ele descreve, e a validação acusa 'não é uma
    # alternativa incorreta do item'
    assert item["distratores"][0]["alternativa"] == "C"
    assert validate_item_annotation(item, reg).valid


def test_fonte_conhecida_sobrescreve_a_inferida_pelo_modelo(item_valido, reg):
    """Numa prova de 2023 o modelo devolveu ano 2010 e 2016 lendo o cabeçalho.

    Banca, ano e prova são metadado de procedência (Manual §8) — quem ingere
    sabe, o modelo adivinha. E são eles que tornam o `item_id` determinístico.
    """
    item_valido["fonte"]["ano"] = 2010
    item_valido["fonte"]["prova"] = "CHUTE-DO-MODELO"
    item = normalize_item(
        item_valido, reg.data, registry=reg,
        fonte_conhecida={"banca": "INEP", "ano": 2023, "prova": "ENEM-2023-D2-CD11", "numero": 137},
    )
    assert item["fonte"]["ano"] == 2023
    assert item["item_id"] == "ITEM-INEP-2023-ENEM2023D2CD11-Q137"


def test_mecanismo_e_opcional(item_valido, reg):
    """Error Trace §4.2 — nenhuma anotação é inválida por omiti-lo."""
    del item_valido["distratores"][0]["erros_esperados"][1]["mecanismo"]
    assert validate_item_annotation(_norm(item_valido, reg), reg).valid


def test_par_erro_processo_nao_se_repete_na_cadeia(item_valido, reg):
    """Error Trace R-6."""
    elos = item_valido["distratores"][0]["erros_esperados"]
    elos[1] = dict(elos[0], ordem=2)
    assert not validate_item_annotation(_norm(item_valido, reg), reg).valid


# ------------------------------------------------------------- incerteza
def test_marcador_de_incerteza_fora_do_vocabulario_e_rejeitado(item_valido, reg):
    """Schema 2.2 / Manual §13 — vocabulário fechado, idêntico nos dois."""
    item_valido["incerteza"] = {"marcadores": ["nao-sei-bem"]}
    assert not validate_item_annotation(_norm(item_valido, reg), reg).valid


def test_marcadores_do_vocabulario_sao_aceitos(item_valido, reg):
    item_valido["incerteza"] = {
        "marcadores": ["ambiguidade-fronteira", "tres-ou-mais-processos-necessarios"],
        "detalhe": "Fronteira DOM-CAUSAL × DOM-EXPERIMENTAL (Manual §11).",
        "requer_arbitragem": True,
    }
    assert validate_item_annotation(_norm(item_valido, reg), reg).valid


# ------------------------------------------------------------- intervenção
def test_intervencao_sai_do_elo_de_ordem_um(item_valido, reg):
    """Error Trace §1.1 — a raiz, nunca a manifestação de superfície."""
    item_valido["intervencoes"] = [
        {"id": "INT-03", "gatilho": {"processo": "PROC-QUANT-02", "erro": "ERR-05"}, "acao": "..."}
    ]
    res = validate_item_annotation(_norm(item_valido, reg), reg)
    assert any("ordem 1" in w for w in res.warnings)


# --------------------------------------------- governança de ingestão
def test_pipeline_nunca_marca_item_como_apto_a_alimentar_crenca(item_valido, reg):
    """EXT-WP1-1.0, L13b — armazenar sim, influenciar estado de estudante não."""
    item = _norm(item_valido, reg)
    assert item["qualidade"]["apto_para_camada_de_crenca"]["valor"] is False


def test_apto_sem_revisao_humana_e_rejeitado(item_valido, reg):
    item = _norm(item_valido, reg)
    item["qualidade"]["apto_para_camada_de_crenca"] = {"valor": True}
    res = validate_item_annotation(item, reg)
    assert not res.valid
    assert any("L13b" in e for e in res.errors)


def test_item_invalido_continua_normalizavel_e_armazenavel(item_valido, reg):
    """`EXT-WP1-1.0` L13, risco de reintrodução indevida nº 3: **ler a regra 1
    como proibição de armazenamento**.

    "O item pode ser armazenado; não pode ser exposto ao motor. A distinção é o
    que permite ingestão em massa com enriquecimento posterior." A validação é
    registro, nunca porta de entrada — quem protege a camada de crença é
    `apto_para_camada_de_crenca`.
    """
    item_valido["estrutura_cognitiva"]["processos"][0]["papel"] = "facilitador"
    item = _norm(item_valido, reg)  # não levanta
    assert validate_item_annotation(item, reg).valid is False
    assert item["item_id"] and item["item_hash"]        # normalizado apesar de inválido
    assert item["qualidade"]["apto_para_camada_de_crenca"]["valor"] is False


# ------------------------------------------------------------ Error Trace
@pytest.fixture
def traco() -> dict:
    return {
        "trace_id": "TR-1", "event_id": "EV-1", "item_id": "ITEM-INEP-2024-ENEMCAD01-Q023",
        "item_hash": "abc", "ontology_version": "1.4.1", "etrace_version": "1.0",
        "alternativa_escolhida": "C", "confianca_global": 0.4,
        "produtor": "modelo", "revisado_por_humano": False,
        "cadeia": [
            {"ordem": 1, "erro": "ERR-01", "processo_afetado": "PROC-TEXT-01",
             "confianca": "media", "evidencia": {"trechos": ["o gráfico mostra"]},
             "justificativa": "A resposta ignora o dado central lido no gráfico."},
            {"ordem": 2, "erro": "ERR-05", "processo_afetado": "PROC-QUANT-02",
             "confianca": "alta", "mecanismo": "MEC-13"},
        ],
    }


def test_traco_bem_formado_e_valido(traco, reg):
    res = validate_error_trace(traco, reg)
    assert res.valid, res.errors


def test_traco_exige_justificativa_no_elo_raiz(traco, reg):
    """Error Trace §2.2 — obrigatória para `ordem: 1`."""
    del traco["cadeia"][0]["justificativa"]
    assert not validate_error_trace(traco, reg).valid


def test_traco_exige_ontology_version(traco, reg):
    del traco["ontology_version"]
    assert not validate_error_trace(traco, reg).valid


def test_traco_avisa_quando_a_versao_diverge_do_catalogo(traco, reg):
    """Uma anotação de outra geração não pode ser lida sem remapeamento explícito."""
    traco["ontology_version"] = "1.4"
    res = validate_error_trace(traco, reg)
    assert any("remapeamento" in w for w in res.warnings)


@pytest.mark.parametrize("produtor", ["modelo", "regra"])
def test_traco_de_maquina_nao_alimenta_crenca_sem_revisao(traco, produtor):
    """Error Trace §6 (EXT-WP1-1.0, L13b) — regra de governança de ingestão."""
    traco["produtor"] = produtor
    assert pode_alimentar_crenca(traco) is False
    traco["revisado_por_humano"] = True
    assert pode_alimentar_crenca(traco) is True


def test_traco_humano_alimenta_crenca(traco):
    traco["produtor"] = "humano"
    assert pode_alimentar_crenca(traco) is True


def test_traco_nao_inventa_vinculo_fora_do_catalogo(traco, reg):
    """Error Trace R-1 — o catálogo é a fonte da possibilidade."""
    traco["cadeia"][1]["processo_afetado"] = "PROC-TEXT-01"
    assert not validate_error_trace(traco, reg).valid


def test_traco_exige_confianca_em_todo_elo(traco, reg):
    del traco["cadeia"][1]["confianca"]
    assert not validate_error_trace(traco, reg).valid


# ------------------------------------------------- ativos protegidos (WP §15)
def test_error_trace_preserva_a_ordem_causal(traco, reg):
    """White Paper 2.0.1 §15 — o Error Trace é o primeiro ativo protegido, e
    "qualquer arquitetura futura derivada deste documento deve preservá-lo".

    A errata da 2.0.1 registra que ele **não estava preservado**: perdeu a ordem
    causal em dois saltos (Constituição §4.3 removeu a ordem; Schema 2.1 reduziu
    a um erro único por alternativa). Este teste falha se a ordem voltar a ser
    tratada como conjunto — `{ERR-01, ERR-05}` e `[ERR-01 → ERR-05]` não são o
    mesmo objeto (§1.2).
    """
    assert validate_error_trace(traco, reg).valid
    raiz = next(e for e in traco["cadeia"] if e["ordem"] == 1)
    assert raiz["erro"] == "ERR-01" and raiz["processo_afetado"] == "PROC-TEXT-01"
    # embaralhar a lista não muda qual elo é a raiz: a ordem é do campo, não da posição
    traco["cadeia"].reverse()
    assert validate_error_trace(traco, reg).valid
    assert next(e for e in traco["cadeia"] if e["ordem"] == 1) == raiz


def test_disciplina_e_metadado_de_manifestacao(item_valido, reg):
    """WP §15, ativo "inversão disciplinar" — disciplina é metadado de
    manifestação, nunca estrutura organizadora. Constituição §2.2 e Manual §8
    proíbem inferir Domínio/Processo/Erro a partir dela.

    Verificação estrutural: trocar a disciplina não muda nada da classificação.
    """
    base = _norm(copy.deepcopy(item_valido), reg)
    outro = copy.deepcopy(item_valido)
    outro["fonte"]["disciplina"] = "História"
    trocado = _norm(outro, reg)
    assert trocado["estrutura_cognitiva"] == base["estrutura_cognitiva"]
    assert trocado["distratores"] == base["distratores"]


# ------------------------------------------------------------------ índice
def test_index_fields_nao_infere_nada(item_valido, reg):
    idx = index_fields(_norm(item_valido, reg))
    assert idx["resposta_correta"] == "B"
    assert idx["disciplina"] == "Química"
    assert idx["processos"] == ["PROC-QUANT-02", "PROC-TEXT-01"]
    assert idx["dominios"] == ["DOM-QUANT", "DOM-TEXTUAL"]
    assert idx["item_id"] == "ITEM-INEP-2024-ENEMCAD01-Q023"
