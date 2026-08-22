"""Testes dos contratos canônicos no app `aluno` — behavior 1.1 e Schema 2.2.

Rodam **offline**: sem servidor, sem Mongo, sem Firestore, sem rede. As funções
testadas são puras ou têm a escrita no Firestore isolada por monkeypatch.

Isso é deliberado. As suítes antigas deste diretório dependem de
`REACT_APP_BACKEND_URL` e de um servidor no ar, e por isso não são executadas há
tempo — falham na coleta. Um contrato que só é verificado por teste que ninguém
roda não é verificado.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402
from admin_routes import _build_public_doc  # noqa: E402
from canonical_ontology import load_ontology, normalize_item, ontology_version, validate_item  # noqa: E402
from cognitive_ontology import build_ontology_tree  # noqa: E402
from feedback_templates import build_feedback  # noqa: E402


# ------------------------------------------------------- ontologia canônica
def test_aluno_le_o_catalogo_canonico_sem_copia_propria():
    """GOV-1.0 §12 — a réplica privada do catálogo foi eliminada.

    O `aluno` mantinha `aluno/backend/docs/ontology JSON v1.4`, duplicata sem
    `derivado_de:` e fora do Conjunto Normativo Indivisível. A comparação campo a
    campo não encontrou divergência, o que permitiu a eliminação sob §12.3.
    """
    assert not (BACKEND / "docs" / "ontology JSON v1.4").exists()
    assert ontology_version() == "1.4.1"


def test_arvore_da_ontologia_tem_a_cardinalidade_do_catalogo():
    tree = build_ontology_tree(set())
    comps = [c for d in tree for c in d["children"]]
    procs = [p for c in comps for p in c["children"]]
    habs = [h for p in procs for h in p["children"]]
    assert (len(tree), len(comps), len(procs), len(habs)) == (11, 12, 25, 56)


def test_taxonomia_chc_nao_canonica_foi_removida():
    """O `ontology.py` do aluno implementava uma taxonomia CHC de 5 níveis cujo
    nível 5 era o **Indicador Comportamental** — nó que a Constituição §4.2 não
    define e que a arquitetura vigente removeu. Era código morto que reintroduzia
    uma geração superseded se alguém voltasse a registrá-lo.
    """
    assert not (BACKEND / "ontology.py").exists()
    assert not (BACKEND / "ontology_routes.py").exists()


# ------------------------------------------------------------ behavior 1.1
@pytest.fixture
def eventos(monkeypatch) -> list[dict]:
    """Isola a escrita no Firestore; devolve a lista de eventos gravados."""
    gravados: list[dict] = []

    class _Doc:
        def set(self, event):
            gravados.append(event)

    class _Col:
        def document(self, _id):
            return _Doc()

    monkeypatch.setattr(fs, "_behavior_collection_ref", lambda uid: _Col())
    return gravados


def _escreve(**kwargs):
    base = dict(
        item_id="ITEM-INEP-2024-ENEMCAD01-Q023",
        ontology_version="1.4.1",
        alternativa_escolhida="C",
        acertou=False,
        item_schema_version="2.2",
        item_hash="abc123",
        contexto_tipo="pratica_questoes",
    )
    base.update(kwargs)
    return fs.write_behavior_event("uid-1", **base)


def test_evento_declara_schema_1_1_e_ontology_version(eventos):
    """behavior 1.1 — `ontology_version` acrescentado e OBRIGATÓRIO."""
    ev = _escreve()
    assert ev["schema_version"] == "1.1"
    assert ev["ontology_version"] == "1.4.1"
    assert eventos == [ev]


def test_evento_sem_ontology_version_e_recusado(eventos):
    """GOV-1.0 §6.1 — sem a versão, o evento é indatável para sempre.

    Recusar é a única resposta correta: gravar com `None` produziria um registro
    que parece completo e não pode ser remapeado numa mudança MAIOR.
    """
    with pytest.raises(ValueError, match="ontology_version"):
        _escreve(ontology_version=None)
    assert eventos == []


def test_evento_reproduz_o_contrato_campo_a_campo(eventos):
    ev = _escreve()
    assert set(ev) == {
        "schema_version", "ontology_version", "event_id", "attempt_id",
        "student_id", "item_id", "item_schema_version", "item_hash", "timestamp",
        "contexto", "resposta", "desempenho", "status", "metadados",
    }
    assert set(ev["contexto"]) == {"tipo", "prova_id", "origem"}
    assert set(ev["resposta"]) == {"alternativa_escolhida", "acertou"}
    assert set(ev["desempenho"]) == {
        "tempo_resposta_segundos", "numero_tentativas", "mudou_resposta"
    }
    assert set(ev["metadados"]) == {"dispositivo", "versao_aplicacao"}


def test_item_hash_informado_e_preservado(eventos):
    """O hash vem do ITEM respondido, não de um recálculo local.

    Recalcular aqui produziria um valor que só por acaso coincidiria com o do
    item, e o casamento item↔evento falharia em silêncio — que é exatamente o
    defeito que o índice do perfil cognitivo tinha.
    """
    ev = _escreve(item_hash="hash-do-item", item_content={"enunciado": "outro"})
    assert ev["item_hash"] == "hash-do-item"


def test_acertou_e_registrado_como_recebido_do_backend(eventos):
    """O contrato diz que `acertou` é calculado exclusivamente pelo backend a
    partir do gabarito canônico — esta função apenas registra o que recebeu."""
    assert _escreve(acertou=True)["resposta"]["acertou"] is True
    assert _escreve(acertou=None)["resposta"]["acertou"] is None


# --------------------------------------------------- item_id estável no sync
def _master(**over) -> dict:
    base = {
        "id": "doc-interno-do-pipeline",
        "item": {
            "schema_version": "2.2",
            "ontology_version": "1.4.1",
            "item_id": "ITEM-INEP-2024-ENEMCAD01-Q023",
            "item_hash": "hash-abc",
            "fonte": {"banca": "INEP", "ano": 2024, "prova": "ENEM-CAD01",
                      "disciplina": "Química", "tema": "Cinética"},
            "questao": {
                "enunciado": "...",
                "alternativas": [
                    {"letra": "A", "texto": "a", "correta": False},
                    {"letra": "B", "texto": "b", "correta": True},
                ],
                "recursos": {},
            },
            "estrutura_cognitiva": {"processos": [{"id": "PROC-QUANT-02", "papel": "nuclear"}]},
            "distratores": [{"alternativa": "A", "erros_esperados": []}],
        },
    }
    base.update(over)
    return base


def test_item_id_e_invariavel_entre_sincronizacoes():
    """Schema 2.2 — `item_id` "deve permanecer invariável entre pipeline,
    Firestore, aluno e professor".

    Até 2026-08-21 `_build_public_doc` sorteava um `uuid4().hex` novo a CADA
    sync, o que impedia ligar um evento de behavior ao item que o originou.
    """
    m = _master()
    a, b = _build_public_doc(m), _build_public_doc(m)
    assert a["item_id"] == b["item_id"] == "ITEM-INEP-2024-ENEMCAD01-Q023"


def test_doc_publico_propaga_o_que_o_behavior_exige():
    pub = _build_public_doc(_master())
    assert pub["ontology_version"] == "1.4.1"
    assert pub["item_schema_version"] == "2.2"
    assert pub["item_hash"] == "hash-abc"
    assert pub["master_id"] == "doc-interno-do-pipeline"


def test_doc_publico_nao_vaza_classificacao_cognitiva():
    """O aluno não vê processo, domínio, competência nem distrator."""
    pub = _build_public_doc(_master())
    assert set(pub) == {
        "item_id", "master_id", "item_schema_version", "ontology_version",
        "item_hash", "questao", "fonte",
    }
    assert "estrutura_cognitiva" not in pub
    assert "distratores" not in pub


def test_doc_publico_le_documentos_pre_migracao():
    """Documentos sincronizados antes da 2.2 gravavam a anotação em `pipeline`."""
    antigo = _master()
    antigo["pipeline"] = antigo.pop("item")
    assert _build_public_doc(antigo)["item_id"] == "ITEM-INEP-2024-ENEMCAD01-Q023"


# ----------------------------------------------------- feedback pela RAIZ
@pytest.fixture
def master_com_cadeia() -> dict:
    """Raiz = ERR-01 (leitura) em PROC-TEXT-01; manifestação = ERR-05 (proporção)."""
    return {
        "item": {
            "estrutura_cognitiva": {"processos": [
                {"id": "PROC-QUANT-02", "papel": "nuclear"},
                {"id": "PROC-TEXT-01", "papel": "secundario"},
            ]},
            "distratores": [{
                "alternativa": "C",
                "erros_esperados": [
                    {"ordem": 2, "erro": "ERR-05", "processo_afetado": "PROC-QUANT-02",
                     "confianca": 0.7},
                    {"ordem": 1, "erro": "ERR-01", "processo_afetado": "PROC-TEXT-01",
                     "confianca": 0.4},
                ],
            }],
        }
    }


def test_feedback_parte_da_raiz_da_cadeia(master_com_cadeia):
    """Error Trace §1.1 — a intervenção sai do elo de ordem 1, nunca do último.

    "Um traço cuja raiz é leitura deficiente e cuja manifestação é erro
    proporcional pede a intervenção da raiz." Tratar apenas a manifestação de
    superfície é pedagogicamente ineficaz — é a razão de a cadeia ser ordenada.
    Note que os elos estão fora de ordem no dado: a seleção é por `ordem`, não
    por posição na lista.
    """
    msgs = " ".join(build_feedback(master_com_cadeia, "C", False)["mensagens"]).lower()
    erros = {e["id"]: e for e in load_ontology()["tipos_erro"]}
    assert erros["ERR-01"]["mecanismo"].lower() in msgs
    assert erros["ERR-05"]["mecanismo"].lower() not in msgs


def test_explicacao_do_erro_vem_do_catalogo_nao_de_mapa_paralelo():
    """Havia aqui um dicionário hard-coded que dava a `ERR-01` o significado
    "parou numa etapa intermediária", enquanto o catálogo o define como "Leitura
    literal deficiente". Era a colisão NS-2 reproduzida dentro do código.
    """
    m = {"item": {"estrutura_cognitiva": {"processos": [{"id": "PROC-TEXT-01", "papel": "nuclear"}]},
                  "distratores": [{"alternativa": "A", "erros_esperados": [
                      {"ordem": 1, "erro": "ERR-01", "processo_afetado": "PROC-TEXT-01",
                       "confianca": 0.7}]}]}}
    msgs = " ".join(build_feedback(m, "A", False)["mensagens"]).lower()
    erro = next(e for e in load_ontology()["tipos_erro"] if e["id"] == "ERR-01")
    assert erro["mecanismo"].lower() in msgs
    assert erro["evidencia_observavel"].lower() in msgs


@pytest.mark.parametrize("sentinela", [
    "erro-nao-catalogado-nesta-versao",
    "sem-mecanismo-cognitivo-identificavel",
])
def test_sentinela_produz_feedback_proprio(sentinela):
    """Error Trace R-2 — sentinela é elo válido e informativo, não dado ausente."""
    m = {"item": {"estrutura_cognitiva": {"processos": [{"id": "PROC-EXP-01", "papel": "nuclear"}]},
                  "distratores": [{"alternativa": "A", "erros_esperados": [
                      {"ordem": 1, "erro": sentinela, "processo_afetado": "PROC-EXP-01",
                       "confianca": 0.4}]}]}}
    msgs = build_feedback(m, "A", False)["mensagens"]
    assert msgs and "não foi dessa vez" not in msgs[0].lower()


def test_feedback_sem_anotacao_degrada_para_generico():
    assert build_feedback(None, "A", False)["mensagens"] == [
        "Não foi dessa vez. Reveja com calma o que a questão pede e tente identificar "
        "em que passo a sua resposta mudou de direção."
    ]


def test_feedback_de_acerto_reforca_o_processo_nuclear(master_com_cadeia):
    fb = build_feedback(master_com_cadeia, "B", True)
    assert fb["acertou"] is True
    assert any("Para fixar" in m for m in fb["mensagens"])


# ------------------------------------------ validação compartilhada (GOV §12)
def test_aluno_e_pipeline_usam_a_mesma_implementacao_de_validacao():
    """Uma única implementação, compartilhada — não uma cópia por app.

    Duas implementações do mesmo contrato divergem com o tempo; é o modo de
    falha que GOV-1.0 §12 existe para impedir, e reproduzi-lo em código seria
    contraditório com o que o corpus exige dos documentos.
    """
    import canonical_ontology

    modulo = canonical_ontology._validator_module()
    esperado = BACKEND.parents[1] / "pipeline" / "backend" / "ontology_validator.py"
    assert Path(modulo.__file__).resolve() == esperado.resolve()


def test_ingestao_manual_deriva_dominios_e_competencias():
    """Constituição §4.4 — a derivação é mecânica; não se exige do remetente."""
    item = normalize_item({
        "schema_version": "2.2", "ontology_version": "1.4.1",
        "item_id": "ITEM-X",
        "questao": {"enunciado": "...", "alternativas": [
            {"letra": "A", "texto": "a", "correta": False},
            {"letra": "B", "texto": "b", "correta": True}]},
        "estrutura_cognitiva": {"processos": [{
            "id": "PROC-QUANT-02", "papel": "nuclear", "peso_no_item": 1.0,
            "confianca": "alta", "habilidades": [{"id": "HAB-03"}],
            "justificativa": "Exige relação proporcional."}]},
        "distratores": [{"alternativa": "A", "erros_esperados": [
            {"ordem": 1, "erro": "ERR-05", "processo_afetado": "PROC-QUANT-02",
             "confianca": "alta"}]}],
    })
    ec = item["estrutura_cognitiva"]
    assert [d["id"] for d in ec["dominios"]] == ["DOM-QUANT"]
    assert [c["id"] for c in ec["competencias"]] == ["COMP-01"]
    assert item["item_id"] == "ITEM-X"  # identidade afirmada pelo remetente
    assert validate_item(item)["valid"] is True
