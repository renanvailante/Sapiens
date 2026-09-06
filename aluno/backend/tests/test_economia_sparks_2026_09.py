"""Nova economia de Sparks (2026-09): saldo inicial 100 (ou o valor de um
código de promoção válido), +1 por questão de
treino de habilidade concluída (nunca duplicado), sugestão de correção
aprovada credita 5, catálogo da loja com 4 pacotes, ID de aluno legível.

Offline — sem servidor, sem Mongo/Firestore reais — mesmo estilo de
`test_rodadas_sparks.py` (dublês mínimos do client Firestore).
"""
from __future__ import annotations

import sys
from pathlib import Path

from google.api_core import exceptions as gcloud_exceptions

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402
import models  # noqa: E402
import skills_map_routes  # noqa: E402
import sparks_store  # noqa: E402


# ================================================================= dublês

class _FakeStudentDoc:
    def __init__(self, data=None):
        self._data = dict(data or {})

    def get(self):
        return self

    def to_dict(self):
        return dict(self._data) if self._data else None

    @property
    def exists(self):
        return bool(self._data)

    def update(self, data):
        for k, v in data.items():
            if hasattr(v, "value"):
                self._data[k] = self._data.get(k, 0) + v.value
            else:
                self._data[k] = v


class _FakeCreateOnceDoc:
    """`DocumentReference.create()` só tem sucesso na primeira chamada —
    mesma garantia atômica usada em toda a economia de Sparks."""
    def __init__(self):
        self._data = None

    def create(self, data):
        if self._data is not None:
            raise gcloud_exceptions.AlreadyExists("já existe")
        self._data = dict(data)

    def get(self):
        return self

    def to_dict(self):
        return dict(self._data) if self._data else None

    @property
    def exists(self):
        return self._data is not None


# ================================================== saldo inicial e catálogo

def test_saldo_inicial_e_100():
    assert fs.SPARKS_INITIAL_BALANCE == 100


class TestCatalogoLoja:
    def test_quatro_pacotes_com_precos_aprovados(self):
        catalogo = {p.package_id: p for p in sparks_store.list_packages()}
        assert len(catalogo) == 4
        assert (catalogo["spark_200"].sparks_amount, catalogo["spark_200"].price_cents) == (200, 990)
        assert (catalogo["spark_600"].sparks_amount, catalogo["spark_600"].price_cents) == (600, 2490)
        assert (catalogo["spark_1500"].sparks_amount, catalogo["spark_1500"].price_cents) == (1500, 5490)
        assert (catalogo["spark_4000"].sparks_amount, catalogo["spark_4000"].price_cents) == (4000, 11990)

    def test_destaques_nos_pacotes_certos(self):
        catalogo = {p.package_id: p for p in sparks_store.list_packages()}
        assert catalogo["spark_1500"].highlight == "Mais escolhido"
        assert catalogo["spark_4000"].highlight == "Melhor valor"
        assert catalogo["spark_200"].highlight is None
        assert catalogo["spark_600"].highlight is None


def test_feedback_geral_da_trilha_custa_20_flat():
    assert skills_map_routes.SKILLS_MAP_FIRST_COST == 20
    assert skills_map_routes.SKILLS_MAP_COST == 20
    assert skills_map_routes._next_cost(None) == 20
    assert skills_map_routes._next_cost({"hexagon": [1]}) == 20


# ======================================== ganho por questão de treino (+1)

class TestGrantQuestionSparksIdempotente:
    def test_primeira_chamada_credita_1_spark(self, monkeypatch):
        item_doc = _FakeCreateOnceDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 150})
        monkeypatch.setattr(fs, "_question_spark_ref", lambda uid, item_id: item_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        resultado = fs.grant_question_sparks("uid-1", "TREINO:HAB-01:1")

        assert resultado["ja_concedido"] is False
        assert resultado["sparks_ganhos"] == 1
        assert student_doc.to_dict()["sparks_balance"] == 151

    def test_responder_a_mesma_questao_de_novo_nao_credita_de_novo(self, monkeypatch):
        item_doc = _FakeCreateOnceDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 150})
        monkeypatch.setattr(fs, "_question_spark_ref", lambda uid, item_id: item_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        fs.grant_question_sparks("uid-1", "TREINO:HAB-01:1")
        resultado_2 = fs.grant_question_sparks("uid-1", "TREINO:HAB-01:1")

        assert resultado_2["ja_concedido"] is True
        assert student_doc.to_dict()["sparks_balance"] == 151  # não dobrou

    def test_questoes_diferentes_creditam_cada_uma(self, monkeypatch):
        docs = {}

        def _ref(uid, item_id):
            return docs.setdefault(item_id, _FakeCreateOnceDoc())

        student_doc = _FakeStudentDoc({"sparks_balance": 150})
        monkeypatch.setattr(fs, "_question_spark_ref", _ref)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        fs.grant_question_sparks("uid-1", "TREINO:HAB-01:1")
        fs.grant_question_sparks("uid-1", "TREINO:HAB-01:2")

        assert student_doc.to_dict()["sparks_balance"] == 152


# ============================ sugestão de correção aprovada credita 5 Sparks

class TestGrantReportSparksIdempotente:
    def test_aprovacao_credita_5_sparks(self, monkeypatch):
        report_doc = _FakeCreateOnceDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 150})
        monkeypatch.setattr(fs, "_report_spark_ref", lambda uid, report_id: report_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        resultado = fs.grant_report_sparks("uid-1", "report-abc")

        assert resultado["ja_concedido"] is False
        assert resultado["sparks_ganhos"] == 5
        assert student_doc.to_dict()["sparks_balance"] == 155

    def test_dupla_aprovacao_nao_credita_de_novo(self, monkeypatch):
        report_doc = _FakeCreateOnceDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 150})
        monkeypatch.setattr(fs, "_report_spark_ref", lambda uid, report_id: report_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        fs.grant_report_sparks("uid-1", "report-abc")
        resultado_2 = fs.grant_report_sparks("uid-1", "report-abc")

        assert resultado_2["ja_concedido"] is True
        assert student_doc.to_dict()["sparks_balance"] == 155


# ===================================================== user_id legível

class TestGenerateUserId:
    def test_contem_o_nome_no_inicio(self):
        uid = models.generate_user_id("Renan Vailante")
        assert uid.startswith("renan_vailante_")

    def test_remove_acento_e_carateres_especiais(self):
        uid = models.generate_user_id("João da Conceição-Ç")
        assert uid.split("_")[0] == "joao"
        assert all(c.isalnum() or c == "_" for c in uid)

    def test_termina_com_poucos_digitos_hex(self):
        uid = models.generate_user_id("Ana")
        sufixo = uid.rsplit("_", 1)[-1]
        assert len(sufixo) == 4
        assert all(c in "0123456789abcdef" for c in sufixo)

    def test_nome_vazio_cai_em_aluno(self):
        assert models.generate_user_id("").startswith("aluno_")

    def test_dois_alunos_de_mesmo_nome_tem_ids_diferentes(self):
        a = models.generate_user_id("Maria Silva")
        b = models.generate_user_id("Maria Silva")
        assert a != b
        assert a.startswith("maria_silva_") and b.startswith("maria_silva_")
