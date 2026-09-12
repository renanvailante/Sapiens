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
        pkg = sparks_store.get_package("spark_600")
        assert pkg is not None
        assert (pkg.sparks_amount, pkg.price_cents) == (600, 2490)


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
        for campo, esperado in filt.items():
            # Só os operadores que o código sob teste realmente usa. Um
            # operador não suportado explode em vez de casar por engano — um
            # dublê que ignora `$nin` faria um teste de reconciliação passar
            # justamente quando a consulta real estivesse errada.
            if isinstance(esperado, dict):
                for op, valor in esperado.items():
                    if op == "$nin":
                        if doc.get(campo) in valor:
                            return False
                    elif op == "$exists":
                        if (campo in doc) is not valor:
                            return False
                    else:
                        raise NotImplementedError(f"operador não suportado no dublê: {op}")
            elif doc.get(campo) != esperado:
                return False
        return True

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
        self.webhook_recebimentos = FakeCollection()


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

        result = _run(svc.create_purchase(db, user, "spark_600", {
            "token": "card-token-abc", "payment_method_id": "visa", "installments": 1,
        }))

        assert captured["transaction_amount"] == 24.90
        assert "sparks_amount" not in captured  # nunca manda quantidade de Sparks ao MP
        assert result["status"] == "pending"
        stored = _run(db.sparks_payments.find_one({"purchase_id": result["purchase_id"]}))
        assert stored["sparks_amount"] == 600
        assert stored["credited"] is False
        assert stored["source"] == "manual"

    def test_pacote_desconhecido_levanta_erro_de_dominio(self, monkeypatch):
        db = FakeDB()
        with pytest.raises(svc.UnknownPackageError):
            _run(svc.create_purchase(db, _user(), "pacote-fantasma", {"token": "x", "payment_method_id": "visa"}))

    def test_cartao_sem_token_levanta_erro_de_dominio(self, monkeypatch):
        """Só é obrigatório para cartão — Pix não tem token nenhum."""
        db = FakeDB()
        with pytest.raises(svc.MissingCardTokenError):
            _run(svc.create_purchase(db, _user(), "spark_600", {"payment_method_id": "visa"}))


class TestCreatePurchasePix:
    def _payload_pix_da_resposta_mp(self):
        return {
            "id": "mp-pix-1",
            "status": "pending",
            "status_detail": "pending_waiting_transfer",
            "point_of_interaction": {
                "transaction_data": {
                    "qr_code": "00020126580014br.gov.bcb.pix...",
                    "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgA...",
                    "ticket_url": "https://www.mercadopago.com/payments/mp-pix-1/ticket",
                }
            },
        }

    def test_payload_enviado_ao_mp_nao_tem_token_nem_parcelas(self, monkeypatch):
        captured = {}

        def fake_create_payment(payload):
            captured.update(payload)
            return self._payload_pix_da_resposta_mp()

        monkeypatch.setattr(svc.mp, "create_payment", fake_create_payment)
        db = FakeDB()

        result = _run(svc.create_purchase(db, _user(), "spark_200", {
            "payment_method_id": "pix", "payer": {"email": "aluno@exemplo.com"},
        }))

        assert captured["payment_method_id"] == "pix"
        assert captured["transaction_amount"] == 9.90
        assert "token" not in captured
        assert "installments" not in captured
        assert "issuer_id" not in captured
        assert result["status"] == "pending"

    def test_resposta_devolve_qr_code_e_copia_e_cola(self, monkeypatch):
        monkeypatch.setattr(svc.mp, "create_payment", lambda payload: self._payload_pix_da_resposta_mp())
        db = FakeDB()

        result = _run(svc.create_purchase(db, _user(), "spark_200", {
            "payment_method_id": "pix", "payer": {"email": "aluno@exemplo.com"},
        }))

        assert result["pix"]["qr_code"] == "00020126580014br.gov.bcb.pix..."
        assert result["pix"]["qr_code_base64"] == "iVBORw0KGgoAAAANSUhEUgA..."
        assert result["pix"]["ticket_url"].startswith("https://")

    def test_pix_nao_credita_sparks_na_hora(self, monkeypatch):
        """Mesma regra do cartão: crédito só acontece pelo webhook, nunca
        na resposta síncrona — Pix normalmente nem aprova na hora mesmo."""
        monkeypatch.setattr(svc.mp, "create_payment", lambda payload: self._payload_pix_da_resposta_mp())
        db = FakeDB()

        result = _run(svc.create_purchase(db, _user(), "spark_200", {
            "payment_method_id": "pix", "payer": {"email": "aluno@exemplo.com"},
        }))

        stored = _run(db.sparks_payments.find_one({"purchase_id": result["purchase_id"]}))
        assert stored["credited"] is False
        assert stored["pix"]["qr_code"] == "00020126580014br.gov.bcb.pix..."

    def test_cartao_continua_sem_campo_pix(self, monkeypatch):
        """Garantia de que a mudança do Pix não vazou nada pro fluxo de cartão."""
        monkeypatch.setattr(svc.mp, "create_payment", lambda payload: {
            "id": "mp-card-1", "status": "approved", "status_detail": "accredited",
        })
        db = FakeDB()

        result = _run(svc.create_purchase(db, _user(), "spark_200", {
            "token": "card-token-abc", "payment_method_id": "visa", "installments": 1,
        }))

        assert result["pix"] is None
        stored = _run(db.sparks_payments.find_one({"purchase_id": result["purchase_id"]}))
        assert stored["pix"] is None


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
        assert captured["auto_recurring"]["transaction_amount"] == 9.90
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
            "user_id": "user-1", "active": True, "package_id": "spark_600",
            "mp_preapproval_id": "mp-sub-1", "status": "authorized",
        }))

        resultado = _run(svc.process_payment_webhook(db, "mp-cycle-1"))
        assert resultado["credited"] is True
        stored = _run(db.sparks_payments.find_one({"mp_payment_id": "mp-cycle-1"}))
        assert stored["source"] == "auto_recharge"
        assert stored["user_id"] == "user-1"
        assert stored["sparks_amount"] == 600

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


class TestReconciliacao:
    """O crédito não pode depender de o webhook chegar.

    Em 2026-09-07 um Pix de verdade foi pago, o dinheiro entrou na conta do
    Mercado Pago e os Sparks nunca foram creditados: a notificação não chegou,
    e nada no sistema perguntava de novo. Estes testes fixam o comportamento
    que fecha esse buraco — perguntar de novo é obrigação nossa, não favor do
    Mercado Pago.
    """

    def _fake_credit(self, monkeypatch, calls: list):
        def fake_grant(uid, *, payment_id, package_id, sparks_amount, price_cents, currency, source):
            calls.append(payment_id)
            return {"ja_creditado": False}

        monkeypatch.setattr(svc.fs, "grant_purchase_sparks", fake_grant)

    def _pagamento_pendente(self, db, mp_payment_id="mp-1", purchase_id="p1"):
        _run(db.sparks_payments.insert_one({
            "purchase_id": purchase_id, "user_id": "user-1", "package_id": "spark_200",
            "sparks_amount": 200, "price_cents": 1990, "currency": "BRL", "source": "manual",
            "mp_payment_id": mp_payment_id, "status": "pending", "credited": False,
        }))

    def test_consultar_status_credita_pagamento_ja_pago_sem_webhook(self, monkeypatch):
        """O caso do incidente: pago no banco, `pending` no nosso Mongo."""
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(svc.mp, "get_payment", lambda pid: {"id": pid, "status": "approved", "metadata": {}})

        db = FakeDB()
        self._pagamento_pendente(db)

        doc = _run(svc.get_purchase_status(db, "p1", "user-1"))
        assert doc["credited"] is True
        assert doc["status"] == "approved"
        assert calls == ["mp-1"]

    def test_consultar_status_nao_pergunta_ao_mp_se_ja_creditado(self, monkeypatch):
        """Compra encerrada não gera tráfego novo a cada volta do polling."""
        def explode(pid):
            raise AssertionError("não deveria consultar o Mercado Pago")

        monkeypatch.setattr(svc.mp, "get_payment", explode)

        db = FakeDB()
        _run(db.sparks_payments.insert_one({
            "purchase_id": "p1", "user_id": "user-1", "mp_payment_id": "mp-1",
            "status": "approved", "credited": True,
        }))
        assert _run(svc.get_purchase_status(db, "p1", "user-1"))["credited"] is True

    def test_consultar_status_nao_pergunta_ao_mp_se_recusado(self, monkeypatch):
        def explode(pid):
            raise AssertionError("não deveria consultar o Mercado Pago")

        monkeypatch.setattr(svc.mp, "get_payment", explode)

        db = FakeDB()
        _run(db.sparks_payments.insert_one({
            "purchase_id": "p1", "user_id": "user-1", "mp_payment_id": "mp-1",
            "status": "rejected", "credited": False,
        }))
        assert _run(svc.get_purchase_status(db, "p1", "user-1"))["credited"] is False

    def test_mercado_pago_fora_do_ar_nao_quebra_a_consulta(self, monkeypatch):
        """Degradar para o estado local é aceitável; derrubar a tela não."""
        def explode(pid):
            raise RuntimeError("Mercado Pago fora do ar")

        monkeypatch.setattr(svc.mp, "get_payment", explode)

        db = FakeDB()
        self._pagamento_pendente(db)

        doc = _run(svc.get_purchase_status(db, "p1", "user-1"))
        assert doc["status"] == "pending"
        assert doc["credited"] is False

    @pytest.mark.parametrize("status_no_mercado_pago", ["pending", "in_process", "authorized"])
    def test_nao_credita_enquanto_o_dinheiro_nao_entrou(self, monkeypatch, status_no_mercado_pago):
        """A pergunta que decide o crédito é feita ao Mercado Pago, e a única
        resposta que vale é `approved`.

        Reperguntar de propósito e com frequência (que é o que a reconciliação
        faz) só é seguro porque a decisão continua sendo dele: um Pix gerado e
        nunca pago fica `pending` para sempre e nunca vira Spark nenhum. Sem
        esta trava, a rede de segurança viraria uma máquina de dar Sparks de
        graça para quem só abriu o QR Code.
        """
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(
            svc.mp, "get_payment",
            lambda pid: {"id": pid, "status": status_no_mercado_pago, "metadata": {}},
        )

        db = FakeDB()
        self._pagamento_pendente(db)

        resultado = _run(svc.reconciliar_pendentes(db))
        assert (resultado["verificados"], resultado["creditados"]) == (1, 0)
        assert resultado["situacao"] == {"mp-1": status_no_mercado_pago}
        assert calls == []
        doc = _run(svc.get_purchase_status(db, "p1", "user-1"))
        assert doc["credited"] is False
        assert calls == []

    def test_status_aprovado_so_no_nosso_banco_nao_basta(self, monkeypatch):
        """Se o Mongo diz `approved` e o Mercado Pago diz que não, vale o
        Mercado Pago — o nosso banco não é fonte de verdade sobre dinheiro."""
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(svc.mp, "get_payment", lambda pid: {"id": pid, "status": "rejected", "metadata": {}})

        db = FakeDB()
        _run(db.sparks_payments.insert_one({
            "purchase_id": "p1", "user_id": "user-1", "package_id": "spark_200",
            "sparks_amount": 200, "price_cents": 1990, "currency": "BRL", "source": "manual",
            "mp_payment_id": "mp-1", "status": "approved", "credited": False,
        }))

        assert _run(svc.reconciliar_pendentes(db))["creditados"] == 0
        assert calls == []
        assert _run(db.sparks_payments.find_one({"mp_payment_id": "mp-1"}))["status"] == "rejected"

    def test_laco_credita_pendente_aprovado_e_ignora_finalizados(self, monkeypatch):
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(svc.mp, "get_payment", lambda pid: {"id": pid, "status": "approved", "metadata": {}})

        db = FakeDB()
        self._pagamento_pendente(db, mp_payment_id="mp-pago", purchase_id="p1")
        _run(db.sparks_payments.insert_one({
            "purchase_id": "p2", "user_id": "user-1", "package_id": "spark_200",
            "sparks_amount": 200, "price_cents": 1990, "currency": "BRL", "source": "manual",
            "mp_payment_id": "mp-expirado", "status": "cancelled", "credited": False,
        }))
        _run(db.sparks_payments.insert_one({
            "purchase_id": "p3", "user_id": "user-1", "package_id": "spark_200",
            "sparks_amount": 200, "price_cents": 1990, "currency": "BRL", "source": "manual",
            "mp_payment_id": "mp-ok", "status": "approved", "credited": True,
        }))

        resultado = _run(svc.reconciliar_pendentes(db))
        assert (resultado["verificados"], resultado["creditados"]) == (1, 1)
        assert calls == ["mp-pago"]

    def test_laco_nao_derruba_tudo_quando_um_pagamento_falha(self, monkeypatch):
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)

        def get_payment(pid):
            if pid == "mp-quebrado":
                raise RuntimeError("erro do Mercado Pago")
            return {"id": pid, "status": "approved", "metadata": {}}

        monkeypatch.setattr(svc.mp, "get_payment", get_payment)

        db = FakeDB()
        self._pagamento_pendente(db, mp_payment_id="mp-quebrado", purchase_id="p1")
        self._pagamento_pendente(db, mp_payment_id="mp-pago", purchase_id="p2")

        resultado = _run(svc.reconciliar_pendentes(db))
        assert resultado["creditados"] == 1
        assert calls == ["mp-pago"]

    def test_aprovado_mas_nao_creditado_e_reparado(self, monkeypatch):
        """Crédito interrompido no meio (queda entre aprovar e gravar) tem que
        ser recuperado, não tratado como pagamento já resolvido."""
        calls: list[str] = []
        self._fake_credit(monkeypatch, calls)
        monkeypatch.setattr(svc.mp, "get_payment", lambda pid: {"id": pid, "status": "approved", "metadata": {}})

        db = FakeDB()
        _run(db.sparks_payments.insert_one({
            "purchase_id": "p1", "user_id": "user-1", "package_id": "spark_200",
            "sparks_amount": 200, "price_cents": 1990, "currency": "BRL", "source": "manual",
            "mp_payment_id": "mp-1", "status": "approved", "credited": False,
        }))

        assert _run(svc.reconciliar_pendentes(db))["creditados"] == 1
        assert calls == ["mp-1"]


class TestAuditoriaWebhook:
    def test_registra_notificacao_recusada_por_assinatura(self):
        db = FakeDB()
        _run(svc.registrar_recebimento_webhook(
            db, tipo="payment", data_id="123", assinatura_valida=False, tinha_assinatura=True,
        ))
        registros = _run(db.webhook_recebimentos.find({}).to_list())
        assert len(registros) == 1
        assert registros[0]["assinatura_valida"] is False
        # A assinatura em si nunca é gravada — auditoria não é lugar de segredo.
        assert not any("signature" in chave for chave in registros[0])


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
