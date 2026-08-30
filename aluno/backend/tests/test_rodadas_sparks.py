"""Testes da camada de progressão/devolutiva/Sparks por rodada (prova de 45
questões dividida em rodadas de 10, a última fechando com 5).

Offline — sem Mongo, sem Firestore real: `_build_item_index`, o cliente
Firestore e o Mongo são substituídos por dublês mínimos, no mesmo estilo de
`test_contratos_aluno.py` e `test_resumo_sessao.py`.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import annotation_service as asvc  # noqa: E402
import firestore_service as fs  # noqa: E402
import firestore_routes as fr  # noqa: E402


# ------------------------------------------------------------- item fixtures

_ITEM_A = {
    "item_id": "ITEM-A",
    "estrutura_cognitiva": {
        "processos": [{"id": "PROC-QUANT-02"}],
        "dominios": [{"id": "DOM-QUANT"}],
        "competencias": [{"id": "COMP-01"}],
    },
}
_ITEM_B = {
    "item_id": "ITEM-B",
    "estrutura_cognitiva": {
        "processos": [{"id": "PROC-QUANT-02"}],
        "dominios": [{"id": "DOM-QUANT"}],
        "competencias": [{"id": "COMP-01"}],
    },
}
_ITEM_C = {
    "item_id": "ITEM-C",
    "estrutura_cognitiva": {
        "processos": [{"id": "PROC-TEXT-01"}],
        "dominios": [{"id": "DOM-LING"}],
        "competencias": [{"id": "COMP-02"}],
    },
}
_INDEX = {i["item_id"]: i for i in (_ITEM_A, _ITEM_B, _ITEM_C)}


# ============================================================= resumo_rodada

class TestResumoRodada:
    def test_acertos_erros_e_percentual(self, monkeypatch):
        monkeypatch.setattr(asvc, "_build_item_index", lambda: _INDEX)
        respostas = [
            {"item_id": "ITEM-A", "acertou": True},
            {"item_id": "ITEM-B", "acertou": False},
            {"item_id": "ITEM-C", "acertou": True},
        ]
        r = asvc.resumo_rodada(respostas)
        assert r["acertos"] == 2
        assert r["erros"] == 1
        assert r["total"] == 3
        assert r["percentual_acerto"] == pytest.approx(66.7, abs=0.1)

    def test_rodada_de_5_funciona_igual_a_de_10(self, monkeypatch):
        """A rodada final (41-45) tem só 5 questões — mesma lógica, sem caso especial."""
        monkeypatch.setattr(asvc, "_build_item_index", lambda: _INDEX)
        respostas = [{"item_id": "ITEM-A", "acertou": True}] * 3 + [{"item_id": "ITEM-B", "acertou": False}] * 2
        r = asvc.resumo_rodada(respostas)
        assert (r["acertos"], r["erros"], r["total"]) == (3, 2, 5)
        assert r["percentual_acerto"] == 60.0

    def test_erro_isolado_nao_vira_padrao_falso(self, monkeypatch):
        """Um único erro anotado não sustenta a afirmação de um padrão —
        dado insuficiente não deve produzir falsa inferência (requisito 9)."""
        monkeypatch.setattr(asvc, "_build_item_index", lambda: _INDEX)
        respostas = [
            {"item_id": "ITEM-A", "acertou": True},
            {"item_id": "ITEM-B", "acertou": False},  # só 1 erro anotado
        ]
        r = asvc.resumo_rodada(respostas)
        assert r["padroes_de_erro"] == []
        assert r["dados_suficientes_padrao"] is False

    def test_erro_repetido_produz_padrao_com_nome_legivel(self, monkeypatch):
        monkeypatch.setattr(asvc, "_build_item_index", lambda: _INDEX)
        respostas = [
            {"item_id": "ITEM-A", "acertou": False},
            {"item_id": "ITEM-B", "acertou": False},  # mesmo domínio/competência/processo de A
        ]
        r = asvc.resumo_rodada(respostas)
        assert r["dados_suficientes_padrao"] is True
        tipos = {p["tipo"] for p in r["padroes_de_erro"]}
        assert tipos == {"processo", "dominio", "competencia"}
        for p in r["padroes_de_erro"]:
            assert not p["nome"].startswith(("PROC-", "DOM-", "COMP-"))
            assert p["frequencia"] == 2

    def test_item_sem_anotacao_nao_quebra_e_nao_gera_padrao(self, monkeypatch):
        monkeypatch.setattr(asvc, "_build_item_index", lambda: {})
        r = asvc.resumo_rodada([{"item_id": "ITEM-SUMIU", "acertou": False}] * 3)
        assert r["padroes_de_erro"] == []
        assert r["erros"] == 3

    def test_rodada_vazia_nao_divide_por_zero(self, monkeypatch):
        monkeypatch.setattr(asvc, "_build_item_index", lambda: {})
        r = asvc.resumo_rodada([])
        assert r["total"] == 0
        assert r["percentual_acerto"] == 0.0


# ==================================================== round_key / rodada_range

class TestRoundKeyERange:
    def test_round_key_e_deterministica(self):
        bloco = {"banca": "INEP", "ano": 2024, "prova": "ENEM-CAD01", "numero_min": 1, "numero_max": 45}
        assert fr._round_key(bloco, 1) == fr._round_key(dict(bloco), 1)
        assert fr._round_key(bloco, 1) != fr._round_key(bloco, 2)

    def test_round_key_varia_por_bloco(self):
        b1 = {"banca": "INEP", "ano": 2024, "prova": "ENEM-CAD01", "numero_min": 1, "numero_max": 45}
        b2 = {"banca": "INEP", "ano": 2023, "prova": "ENEM-CAD01", "numero_min": 1, "numero_max": 45}
        assert fr._round_key(b1, 1) != fr._round_key(b2, 1)

    @pytest.mark.parametrize("rodada,esperado", [
        (1, (1, 10)), (2, (11, 20)), (3, (21, 30)), (4, (31, 40)), (5, (41, 45)),
    ])
    def test_rodada_range_cobre_o_bloco_de_45_sem_sobrepor(self, rodada, esperado):
        assert fr._rodada_range(1, 45, rodada) == esperado


# ============================================================= Sparks — saldo

class _FakeStudentDoc:
    def __init__(self, data=None):
        self._data = dict(data or {})
        self.updates = []

    def get(self):
        return self

    def to_dict(self):
        return dict(self._data) if self._data else None

    @property
    def exists(self):
        return bool(self._data)

    def set(self, data, merge=False):
        if merge:
            self._data.update(data)
        else:
            self._data = dict(data)

    def update(self, data):
        self.updates.append(dict(data))
        for k, v in data.items():
            # Emula firestore.Increment o suficiente para o teste.
            if hasattr(v, "value"):
                self._data[k] = self._data.get(k, 0) + v.value
            else:
                self._data[k] = v


class TestSparksBalance:
    def test_aluno_novo_comeca_com_255(self, monkeypatch):
        doc = _FakeStudentDoc()
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: doc)
        criado = fs.ensure_student_profile("uid-1", "Nome", "n@x.com")
        assert criado is True
        assert doc.to_dict()["sparks_balance"] == 255

    def test_ensure_sparks_balance_nao_sobrescreve_saldo_existente(self, monkeypatch):
        doc = _FakeStudentDoc({"sparks_balance": 300})
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: doc)
        assert fs.ensure_sparks_balance("uid-1") == 300

    def test_ensure_sparks_balance_faz_backfill_de_perfil_antigo(self, monkeypatch):
        """Perfil criado antes desta feature (sem `sparks_balance`) recebe o
        saldo inicial na primeira vez que é consultado — nunca fica sem saldo."""
        doc = _FakeStudentDoc({"nome": "Antigo"})
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: doc)
        assert fs.ensure_sparks_balance("uid-1") == 255
        assert doc.to_dict()["sparks_balance"] == 255
        assert doc.to_dict()["nome"] == "Antigo"  # backfill não apaga o resto do doc


# ========================================================= Sparks — idempotência

class _FakeRoundDoc:
    """Simula DocumentReference.create() lançando AlreadyExists na 2ª chamada —
    a mesma garantia atômica que o Firestore real oferece no servidor."""
    def __init__(self):
        self._data = None

    def create(self, data):
        if self._data is not None:
            from google.api_core import exceptions as gcloud_exceptions
            raise gcloud_exceptions.AlreadyExists("já existe")
        self._data = dict(data)

    def get(self):
        return self

    def to_dict(self):
        return dict(self._data) if self._data else None

    @property
    def exists(self):
        return self._data is not None


def _grant_kwargs(**over):
    base = dict(
        round_key="B-r1",
        bloco={"banca": "INEP", "ano": 2024, "prova": "ENEM-CAD01", "numero_min": 1, "numero_max": 45},
        rodada=1,
        item_ids=[f"ITEM-{i}" for i in range(10)],
        acertos=7,
        erros=3,
        total=10,
        percentual_acerto=70.0,
        padroes_de_erro=[],
    )
    base.update(over)
    return base


class TestGrantRoundSparksIdempotente:
    def test_primeira_chamada_concede_um_spark_por_acerto(self, monkeypatch):
        round_doc = _FakeRoundDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 255})
        monkeypatch.setattr(fs, "_sparks_round_ref", lambda uid, key: round_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        resultado = fs.grant_round_sparks("uid-1", **_grant_kwargs(acertos=7))

        assert resultado["ja_concedido"] is False
        assert resultado["sparks_ganhos"] == 7
        assert student_doc.to_dict()["sparks_balance"] == 262  # 255 + 7

    def test_segunda_chamada_nao_duplica_sparks(self, monkeypatch):
        """Repetir a MESMA rodada (retomada, refresh, requisição repetida) não
        credita de novo — requisito central desta feature."""
        round_doc = _FakeRoundDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 255})
        monkeypatch.setattr(fs, "_sparks_round_ref", lambda uid, key: round_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        fs.grant_round_sparks("uid-1", **_grant_kwargs(acertos=7))
        assert student_doc.to_dict()["sparks_balance"] == 262

        resultado_2 = fs.grant_round_sparks("uid-1", **_grant_kwargs(acertos=7))
        assert resultado_2["ja_concedido"] is True
        assert student_doc.to_dict()["sparks_balance"] == 262  # inalterado

    def test_chamadas_concorrentes_repetidas_nao_duplicam(self, monkeypatch):
        """Simula N chamadas repetidas em sequência (aproximação offline de
        concorrência: cada uma bate no mesmo doc, só a 1ª escreve)."""
        round_doc = _FakeRoundDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 255})
        monkeypatch.setattr(fs, "_sparks_round_ref", lambda uid, key: round_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        resultados = [fs.grant_round_sparks("uid-1", **_grant_kwargs(acertos=10)) for _ in range(5)]
        assert [r["ja_concedido"] for r in resultados] == [False, True, True, True, True]
        assert student_doc.to_dict()["sparks_balance"] == 265  # 255 + 10, uma vez só

    def test_rodada_final_de_5_concede_ate_5_sparks(self, monkeypatch):
        round_doc = _FakeRoundDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 255})
        monkeypatch.setattr(fs, "_sparks_round_ref", lambda uid, key: round_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        resultado = fs.grant_round_sparks("uid-1", **_grant_kwargs(
            round_key="B-r5", rodada=5, item_ids=[f"ITEM-{i}" for i in range(5)],
            acertos=5, erros=0, total=5, percentual_acerto=100.0,
        ))
        assert resultado["sparks_ganhos"] == 5
        assert student_doc.to_dict()["sparks_balance"] == 260

    def test_zero_acertos_nao_credita_nem_falha(self, monkeypatch):
        round_doc = _FakeRoundDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 255})
        monkeypatch.setattr(fs, "_sparks_round_ref", lambda uid, key: round_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        resultado = fs.grant_round_sparks("uid-1", **_grant_kwargs(acertos=0, erros=10))
        assert resultado["sparks_ganhos"] == 0
        assert student_doc.to_dict()["sparks_balance"] == 255
        assert student_doc.updates == []  # nenhuma escrita de saldo disparada à toa

    def test_round_doc_e_auditavel(self, monkeypatch):
        """O documento gravado liga os Sparks à prova/rodada/itens de origem."""
        round_doc = _FakeRoundDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 255})
        monkeypatch.setattr(fs, "_sparks_round_ref", lambda uid, key: round_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        fs.grant_round_sparks("uid-1", **_grant_kwargs(acertos=7))
        gravado = round_doc.to_dict()
        assert gravado["student_id"] == "uid-1"
        assert gravado["rodada"] == 1
        assert gravado["bloco"]["prova"] == "ENEM-CAD01"
        assert gravado["item_ids"] == [f"ITEM-{i}" for i in range(10)]
        assert gravado["sparks_ganhos"] == 7
        assert "created_at" in gravado


# ==================================================== payload / validação

class TestRodadaConcluirPayload:
    def test_rodada_fora_de_1_a_5_e_rejeitada(self):
        with pytest.raises(ValidationError):
            fr.RodadaConcluirPayload(
                bloco={"banca": "INEP", "ano": 2024, "prova": "X", "numero_min": 1, "numero_max": 45},
                rodada=6,
            )

    def test_rodada_1_a_5_e_aceita(self):
        for r in range(1, 6):
            p = fr.RodadaConcluirPayload(
                bloco={"banca": "INEP", "ano": 2024, "prova": "X", "numero_min": 1, "numero_max": 45},
                rodada=r,
            )
            assert p.rodada == r


# ==================================================== progresso 0 -> 45/45

class TestProgressoDoBloco:
    """A barra de progresso não tem estado próprio: é sempre `respondidas ∩
    itens_do_bloco`, a mesma fonte que já é usada para retomar a prova
    (`GET /students/me/respondidas`) — aqui testamos essa contagem base, que é
    o que o frontend usa para renderizar `N/45`."""

    def test_zero_respondidas_e_zero_de_45(self):
        itens_bloco = [f"ITEM-{i}" for i in range(45)]
        respondidas: set[str] = set()
        respondidas_no_bloco = sum(1 for i in itens_bloco if i in respondidas)
        assert respondidas_no_bloco == 0

    def test_45_respondidas_e_100_por_cento(self):
        itens_bloco = [f"ITEM-{i}" for i in range(45)]
        respondidas = set(itens_bloco)
        respondidas_no_bloco = sum(1 for i in itens_bloco if i in respondidas)
        assert respondidas_no_bloco == 45
        assert respondidas_no_bloco / len(itens_bloco) == 1.0

    def test_progresso_intermediario_reflete_so_o_que_foi_persistido(self):
        """Nunca fictício: um item fora do conjunto persistido não conta."""
        itens_bloco = [f"ITEM-{i}" for i in range(45)]
        respondidas = set(itens_bloco[:12])
        respondidas_no_bloco = sum(1 for i in itens_bloco if i in respondidas)
        assert respondidas_no_bloco == 12


# ==================================================== count_answers_for_item
#
# Base de `numero_tentativas` ao reiniciar uma prova: reiniciar nunca apaga
# nem sobrescreve o histórico, só acrescenta eventos — então "em qual
# tentativa esta resposta está" só pode vir de contar o que já foi gravado.

class _FakeQuery:
    def __init__(self, docs):
        self._docs = docs

    def where(self, *args, **kwargs):
        filtro = kwargs.get("filter")
        campo, _op, valor = filtro.field_path, filtro.op_string, filtro.value
        return _FakeQuery([d for d in self._docs if d.get(campo) == valor])

    def stream(self):
        return iter(self._docs)


class TestCountAnswersForItem:
    def test_primeira_resposta_conta_zero_anteriores(self, monkeypatch):
        monkeypatch.setattr(fs, "_behavior_collection_ref", lambda uid: _FakeQuery([]))
        assert fs.count_answers_for_item("uid-1", "ITEM-A") == 0

    def test_conta_so_eventos_respondidos_deste_item(self, monkeypatch):
        docs = [
            {"item_id": "ITEM-A", "status": "respondida"},
            {"item_id": "ITEM-A", "status": "respondida"},
            {"item_id": "ITEM-B", "status": "respondida"},  # outro item: não conta
            {"item_id": "ITEM-A", "status": "abandonada"},  # não é resposta efetiva: não conta
        ]
        monkeypatch.setattr(fs, "_behavior_collection_ref", lambda uid: _FakeQuery(docs))
        assert fs.count_answers_for_item("uid-1", "ITEM-A") == 2

    def test_reiniciar_prova_incrementa_a_cada_nova_resposta(self, monkeypatch):
        """Simula 3 respostas seguidas ao MESMO item (prova reiniciada): a
        contagem cresce 0 -> 1 -> 2 a cada evento novo gravado, nunca reseta."""
        gravados: list[dict] = []
        monkeypatch.setattr(fs, "_behavior_collection_ref", lambda uid: _FakeQuery(gravados))
        vistos = []
        for _ in range(3):
            vistos.append(fs.count_answers_for_item("uid-1", "ITEM-A"))
            gravados.append({"item_id": "ITEM-A", "status": "respondida"})
        assert vistos == [0, 1, 2]
