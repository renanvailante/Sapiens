"""Loja de Sparks (compra avulsa + recarga automática) — Mercado Pago.

Offline — sem servidor, sem Mongo/Firestore reais, sem rede: o SDK do
Mercado Pago (`mercadopago_client`) e o client do Firestore
(`firestore_service`) são substituídos por dublês mínimos, no mesmo estilo
de `test_contratos_aluno.py` e `test_rodadas_sparks.py`.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from google.api_core import exceptions as gcloud_exceptions

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402
import mercadopago_client as mpc  # noqa: E402
import sparks_payments_service as svc  # noqa: E402
import sparks_store  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user(**over) -> User:
    base = dict(user_id="user-1", email="aluno@exemplo.com", name="Aluno")
    base.update(over)
    return User(**base)


# ============================================================== catálogo

class TestCatalogo:
    def test_pacote_desconhecido_e_rejeitado(self):
        assert sparks_store.get_package("nao-existe") is None

    def test_frequencia_fora_da_lista_e_invalida(self):
        assert sparks_store.is_valid_frequency(3) is False
        assert sparks_store.is_valid_frequency(30) is True

    def test_preco_e_quantidade_vem_so_do_catalogo_do_servidor(self):
        pkg = sparks_store.get_package("spark_500")
        assert pkg is not None
        assert (pkg.sparks_amount, pkg.price_cents) == (500, 3990)


# =================================================== assinatura de webhook

class TestVerifyWebhookSignature:
    SECRET = "s3gr3d0"
    DATA_ID = "123456789"
    REQUEST_ID = "req-abc"
    TS = "1700000000"

    def _valid_signature(self) -> str:
        import hashlib
        import hmac

        manifest = f"id:{self.DATA_ID.lower()};request-id:{self.REQUEST_ID};ts:{self.TS};"
        v1 = hmac.new(self.SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        return f"ts={self.TS},v1={v1}"

    def test_assinatura_valida_e_aceita(self):
        ok = mpc.verify_webhook_signature(
            x_signature=self._valid_signature(), x_request_id=self.REQUEST_ID,
            data_id=self.DATA_ID, secret=self.SECRET,
        )
        assert ok is True

    def test_data_id_maiusculo_ainda_bate(self):
        """O manifest usa `data.id` em minúsculas — o header pode chegar com
        letras maiúsculas (ex.: `ORD01JQ...`)."""
        ok = mpc.verify_webhook_signature(
            x_signature=self._valid_signature(), x_request_id=self.REQUEST_ID,
            data_id=self.DATA_ID.upper(), secret=self.SECRET,
        )
        assert ok is True

    def test_corpo_adulterado_e_rejeitado(self):
        ok = mpc.verify_webhook_signature(
            x_signature=self._valid_signature(), x_request_id="outro-id",
            data_id=self.DATA_ID, secret=self.SECRET,
        )
        assert ok is False

    def test_hash_adulterado_e_rejeitado(self):
        sig = self._valid_signature().replace("v1=", "v1=00")
        ok = mpc.verify_webhook_signature(
            x_signature=sig, x_request_id=self.REQUEST_ID, data_id=self.DATA_ID, secret=self.SECRET,
        )
        assert ok is False

    def test_segredo_ausente_e_rejeitado(self):
        ok = mpc.verify_webhook_signature(
            x_signature=self._valid_signature(), x_request_id=self.REQUEST_ID,
            data_id=self.DATA_ID, secret=None,
        )
        assert ok is False

    def test_header_ausente_e_rejeitado(self):
        ok = mpc.verify_webhook_signature(
            x_signature=None, x_request_id=self.REQUEST_ID, data_id=self.DATA_ID, secret=self.SECRET,
        )
        assert ok is False


# ============================================================ dublês Mongo

class _FakeCursor:
    def __init__(self, items):
        self._items = items

    def sort(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    async def to_list(self, length=None):
        return list(self._items)


class _FakeResult:
    def __init__(self, matched_count):
        self.matched_count = matched_count


class FakeCollection:
    def __init__(self, unique_field: str | None = None):
        self._docs: list[dict] = []
        self._unique_field = unique_field

    @staticmethod
    def _matches(doc, filt):
        return all(doc.get(k) == v for k, v in filt.items())

    async def find_one(self, filt, projection=None):
        for doc in self._docs:
            if self._matches(doc, filt):
                return dict(doc)
        return None

    async def insert_one(self, doc):
        if self._unique_field and any(
            d.get(self._unique_field) == doc.get(self._unique_field) for d in self._docs
        ):
            import pymongo.errors

            raise pymongo.errors.DuplicateKeyError("duplicate")
        self._docs.append(dict(doc))
        return doc

    async def update_one(self, filt, update, upsert=False):
        changes = update.get("$set", {})
        for doc in self._docs:
            if self._matches(doc, filt):
                doc.update(changes)
                return _FakeResult(1)
        if upsert:
            new_doc = {**filt, **changes}
            self._docs.append(new_doc)
            return _FakeResult(0)
        return _FakeResult(0)

    def find(self, filt=None, projection=None):
        filt = filt or {}
        return _FakeCursor([dict(d) for d in self._docs if self._matches(d, filt)])


class FakeDB:
    def __init__(self):
        self.sparks_payments = FakeCollection()
        self.sparks_auto_recharge = FakeCollection()
        self.webhook_events = FakeCollection(unique_field="dedupe_key")


# ======================================================= compra avulsa

class TestCreatePurchase:
    def test_payload_enviado_ao_mp_usa_preco_do_catalogo(self, monkeypatch):
        captured = {}

        def fake_create_payment(payload):
            captured.update(payload)
            return {"id": "mp-pay-1", "status": "pending", "status_detail": "pending_waiting"}

        monkeypatch.setattr(svc.mp, "create_payment", fake_create_payment)
        db = FakeDB()
        user = _user()

        result = _run(svc.create_purchase(db, user, "spark_500", {
            "token": "card-token-abc", "payment_method_id": "visa", "installments": 1,
        }))

        assert captured["transaction_amount"] == 39.90
        assert "sparks_amount" not in captured  # nunca manda quantidade de Sparks ao MP
        assert result["status"] == "pending"
        stored = _run(db.sparks_payments.find_one({"purchase_id": result["purchase_id"]}))
        assert stored["sparks_amount"] == 500
        assert stored["credited"] is False
        assert stored["source"] == "manual"

    def test_pacote_desconhecido_levanta_erro_de_dominio(self, monkeypatch):
        db = FakeDB()
        with pytest.raises(svc.UnknownPackageError):
            _run(svc.create_purchase(db, _user(), "pacote-fantasma", {"token": "x", "payment_method_id": "visa"}))


# =================================================== recarga automática

class TestCreateAutoRecharge:
    def test_payload_usa_frequencia_e_preco_do_servidor(self, monkeypatch):
        captured = {}

        def fake_create_preapproval(payload):
            captured.update(payload)
            return {"id": "mp-preapproval-1", "status": "authorized"}

        monkeypatch.setattr(svc.mp, "create_preapproval", fake_create_preapproval)
        db = FakeDB()

        doc = _run(svc.create_auto_recharge(
            db, _user(), package_id="spark_200", frequency_days=30, baseline=50, card_token_id="card-tok",
        ))

        assert captured["auto_recurring"]["frequency"] == 30
        assert captured["auto_recurring"]["frequency_type"] == "days"
        assert captured["auto_recurring"]["transaction_amount"] == 19.90
        assert captured["card_token_id"] == "card-tok"
        assert doc["active"] is True
        assert doc["baseline"] == 50

    def test_frequencia_invalida_e_rejeitada(self):
        db = FakeDB()
        with pytest.raises(svc.InvalidFrequencyError):
            _run(svc.create_auto_recharge(
                db, _user(), package_id="spark_200", frequency_days=3, baseline=50, card_token_id="tok",
            ))

    def test_cancelar_sem_recarga_ativa_levanta_erro(self):
        db = FakeDB()
        with pytest.raises(svc.NoActiveAutoRechargeError):
            _run(svc.cancel_auto_recharge(db, _user()))


# ============================================================ webhook

class TestDedupeWebhook:
    def test_primeira_entrega_processa_segunda_e_bloqueada(self):
        db = FakeDB()
        primeira = _run(svc.dedupe_or_skip(db, "payment:123:evt-1", "payment"))
        segunda = _run(svc.dedupe_or_skip(db, "payment:123:evt-1", "payment"))
        assert primeira is True
        assert segunda is False


class TestProcessPaymentWebhook:
    def _fake_credit(self, monkeypatch, calls: list):
        creditados: set[str] = set()

        def fake_grant(uid, *, payment_id, package_id, sparks_amount, price_cents, currency, source):
            calls.append(payment_id)
            if payment_id in creditados:
                return {"ja_creditado": True}
            creditados.add(payment_id)
            return {"ja_creditado": False}

        monkeypatch.setattr(svc.fs, "grant_purchase_sparks", fake_grant)

    def test_pagamento_aprovado_credita_uma_vez(self, monkeypatch):
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(svc.mp, "get_payment", lambda pid: {"id": pid, "status": "approved", "metadata": {}})

        db = FakeDB()
        _run(db.sparks_payments.insert_one({
            "purchase_id": "p1", "user_id": "user-1", "package_id": "spark_200",
            "sparks_amount": 200, "price_cents": 1990, "currency": "BRL", "source": "manual",
            "mp_payment_id": "mp-1", "status": "pending", "credited": False,
        }))

        resultado = _run(svc.process_payment_webhook(db, "mp-1"))
        assert resultado["credited"] is True
        assert calls == ["mp-1"]
        stored = _run(db.sparks_payments.find_one({"mp_payment_id": "mp-1"}))
        assert stored["credited"] is True

    def test_segunda_notificacao_do_mesmo_pagamento_nao_credita_de_novo(self, monkeypatch):
        """Duas notificações DIFERENTES (ids de notificação distintos) para o
        MESMO `mp_payment_id` já creditado não duplicam o crédito — a garantia
        vem da camada de Firestore (`grant_purchase_sparks`), não do dedupe de
        notificação (que só barra a entrega REPETIDA da mesma notificação)."""
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(svc.mp, "get_payment", lambda pid: {"id": pid, "status": "approved", "metadata": {}})

        db = FakeDB()
        _run(db.sparks_payments.insert_one({
            "purchase_id": "p1", "user_id": "user-1", "package_id": "spark_200",
            "sparks_amount": 200, "price_cents": 1990, "currency": "BRL", "source": "manual",
            "mp_payment_id": "mp-1", "status": "pending", "credited": False,
        }))

        _run(svc.process_payment_webhook(db, "mp-1"))
        # `credited` já está True no doc — uma 2ª notificação (ex.: reenviada
        # pelo MP com outro id de evento) não deveria nem tentar creditar de novo.
        resultado_2 = _run(svc.process_payment_webhook(db, "mp-1"))
        assert resultado_2["credited"] is False
        assert calls == ["mp-1"]  # grant_purchase_sparks só foi chamado uma vez

    def test_pagamento_de_ciclo_de_assinatura_cria_registro_auto_recharge(self, monkeypatch):
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(
            svc.mp, "get_payment",
            lambda pid: {"id": pid, "status": "approved", "metadata": {}, "preapproval_id": "mp-sub-1"},
        )

        db = FakeDB()
        _run(db.sparks_auto_recharge.insert_one({
            "user_id": "user-1", "active": True, "package_id": "spark_500",
            "mp_preapproval_id": "mp-sub-1", "status": "authorized",
        }))

        resultado = _run(svc.process_payment_webhook(db, "mp-cycle-1"))
        assert resultado["credited"] is True
        stored = _run(db.sparks_payments.find_one({"mp_payment_id": "mp-cycle-1"}))
        assert stored["source"] == "auto_recharge"
        assert stored["user_id"] == "user-1"
        assert stored["sparks_amount"] == 500

    def test_pagamento_sem_correspondencia_conhecida_nao_credita_ninguem(self, monkeypatch):
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(
            svc.mp, "get_payment", lambda pid: {"id": pid, "status": "approved", "metadata": {}},
        )

        db = FakeDB()
        resultado = _run(svc.process_payment_webhook(db, "mp-orfao-1"))
        assert resultado == {"matched": False}
        assert calls == []
        stored = _run(db.sparks_payments.find_one({"mp_payment_id": "mp-orfao-1"}))
        assert stored["unmatched"] is True
        assert stored["credited"] is False


class TestProcessSubscriptionWebhook:
    def test_sincroniza_status_cancelado_pelo_mp(self, monkeypatch):
        monkeypatch.setattr(svc.mp, "get_preapproval", lambda pid: {"id": pid, "status": "cancelled"})
        db = FakeDB()
        _run(db.sparks_auto_recharge.insert_one({
            "user_id": "user-1", "active": True, "mp_preapproval_id": "mp-sub-1", "status": "authorized",
        }))

        resultado = _run(svc.process_subscription_webhook(db, "mp-sub-1"))
        assert resultado == {"matched": True, "status": "cancelled"}
        stored = _run(db.sparks_auto_recharge.find_one({"mp_preapproval_id": "mp-sub-1"}))
        assert stored["active"] is False
        assert stored["status"] == "cancelled"


# ================================================ firestore_service (crédito)

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


class _FakePurchaseDoc:
    """Mesma garantia atômica de `_FakeRoundDoc` em test_rodadas_sparks.py —
    `create()` só tem sucesso na primeira chamada."""
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


class TestGrantPurchaseSparksIdempotente:
    def test_primeira_chamada_credita_o_saldo(self, monkeypatch):
        purchase_doc = _FakePurchaseDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 100})
        monkeypatch.setattr(fs, "_purchase_ref", lambda uid, payment_id: purchase_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        resultado = fs.grant_purchase_sparks(
            "uid-1", payment_id="mp-1", package_id="spark_200", sparks_amount=200,
            price_cents=1990, currency="BRL", source="manual",
        )

        assert resultado["ja_creditado"] is False
        assert student_doc.to_dict()["sparks_balance"] == 300

    def test_segunda_chamada_nao_credita_de_novo(self, monkeypatch):
        purchase_doc = _FakePurchaseDoc()
        student_doc = _FakeStudentDoc({"sparks_balance": 100})
        monkeypatch.setattr(fs, "_purchase_ref", lambda uid, payment_id: purchase_doc)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: student_doc)

        fs.grant_purchase_sparks(
            "uid-1", payment_id="mp-1", package_id="spark_200", sparks_amount=200,
            price_cents=1990, currency="BRL", source="manual",
        )
        resultado_2 = fs.grant_purchase_sparks(
            "uid-1", payment_id="mp-1", package_id="spark_200", sparks_amount=200,
            price_cents=1990, currency="BRL", source="manual",
        )

        assert resultado_2["ja_creditado"] is True
        assert student_doc.to_dict()["sparks_balance"] == 300  # não dobrou
