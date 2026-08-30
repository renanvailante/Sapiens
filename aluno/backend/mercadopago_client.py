"""Wrapper fino do SDK oficial `mercadopago` (Python, 3.5.0).

Isola o resto do backend do SDK bruto — `sparks_payments_service.py` chama só
as funções daqui, o que também é o ponto único de monkeypatch nos testes
offline (`tests/test_sparks_payments.py`). Nenhuma função aqui toca Mongo ou
Firestore.

Endpoints usados, todos confirmados na documentação atual do Mercado Pago:
  * `POST /v1/payments`   — pagamento avulso (compra manual de Sparks).
  * `GET  /v1/payments/{id}` — rebusca autoritativa no webhook (nunca confiar
    no corpo da notificação).
  * `POST /preapproval`  — assinatura ("pagamento autorizado") usada só como
    motor de recarga automática por calendário, nunca como acesso Premium.
  * `GET  /preapproval/{id}` / `PUT /preapproval/{id}` — reler status/valor
    atual e pausar/reativar/cancelar.
  * Validação de assinatura de webhook (`x-signature` / `x-request-id`),
    HMAC-SHA256 sobre o manifest `id:{data.id};request-id:{x-request-id};ts:{ts};`,
    formato documentado pelo Mercado Pago.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

import mercadopago

import settings

logger = logging.getLogger("sapiens.mercadopago")

MercadoPagoError = mercadopago.MercadoPagoError

_SDK: mercadopago.SDK | None = None


class MercadoPagoNotConfiguredError(RuntimeError):
    """`MERCADOPAGO_ACCESS_TOKEN` ausente — chamada não pode ser feita."""


def _sdk() -> mercadopago.SDK:
    global _SDK
    if _SDK is not None:
        return _SDK
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise MercadoPagoNotConfiguredError("MERCADOPAGO_ACCESS_TOKEN não configurado.")
    _SDK = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    return _SDK


def create_payment(payload: dict) -> dict:
    result = _sdk().payment().create(payload)
    result.raise_for_status()
    return result["response"]


def get_payment(payment_id: str) -> dict:
    result = _sdk().payment().get(payment_id)
    result.raise_for_status()
    return result["response"]


def create_preapproval(payload: dict) -> dict:
    result = _sdk().preapproval().create(payload)
    result.raise_for_status()
    return result["response"]


def get_preapproval(preapproval_id: str) -> dict:
    result = _sdk().preapproval().get(preapproval_id)
    result.raise_for_status()
    return result["response"]


def update_preapproval(preapproval_id: str, payload: dict) -> dict:
    result = _sdk().preapproval().update(preapproval_id, payload)
    result.raise_for_status()
    return result["response"]


def verify_webhook_signature(
    *, x_signature: str | None, x_request_id: str | None, data_id: str | None, secret: str | None
) -> bool:
    """Valida a assinatura HMAC-SHA256 de uma notificação de webhook.

    Formato oficial: header `x-signature: ts=<ts>,v1=<hash>`; manifest
    assinado = `"id:{data.id};request-id:{x-request-id};ts:{ts};"`, com
    `data_id` em minúsculas. `hmac.compare_digest` evita timing attack.
    """
    if not secret or not x_signature or not data_id:
        return False

    ts = None
    v1 = None
    for part in x_signature.split(","):
        if "=" not in part:
            continue
        key, _, value = part.strip().partition("=")
        if key.strip() == "ts":
            ts = value.strip()
        elif key.strip() == "v1":
            v1 = value.strip()
    if not ts or not v1:
        return False

    manifest = f"id:{data_id.lower()};request-id:{x_request_id or ''};ts:{ts};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)
