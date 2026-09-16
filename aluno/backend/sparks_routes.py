"""Rotas da loja de Sparks: compra avulsa (Payment Brick) e recarga
automática (assinatura/calendário) via Mercado Pago.

Preço, quantidade de Sparks e frequências vêm sempre de `sparks_store.py` —
nenhuma rota aqui aceita esses valores do cliente. O crédito de Sparks só
acontece em `/sparks/webhook`, nunca na resposta síncrona de compra/ativação
(ver `sparks_payments_service.py`).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

import mercadopago_client as mp
import settings
import sparks_payments_service as svc
import sparks_store
from auth import require_user
from models import User

logger = logging.getLogger("sapiens.sparks.routes")

router = APIRouter(prefix="/sparks", tags=["sparks"])

_db = None


def set_db(db):
    global _db
    _db = db


def _require_mp_configured():
    """Portão único de tudo que mexe em dinheiro.

    Checa a configuração COMPLETA (`settings.MERCADOPAGO_HABILITADO`), não só o
    access token: com token mas sem webhook secret, `create_payment` cobraria o
    cartão e a notificação que credita os Sparks seria rejeitada por assinatura
    inválida — o aluno pagaria e nunca receberia.

    A mensagem é deliberadamente genérica para o cliente. O motivo real
    (que variável falta) fica no log e em `/ready`, que exigem acesso ao
    servidor — nunca numa resposta HTTP pública, que diria a um atacante
    exatamente qual metade da configuração está aberta.
    """
    if not settings.MERCADOPAGO_HABILITADO:
        logger.warning(
            "Compra recusada — loja de Sparks desligada (%s).",
            settings.MERCADOPAGO_MOTIVO_DESLIGADA,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "A compra de Sparks está temporariamente indisponível. "
                "Você continua ganhando Sparks praticando questões."
            ),
        )


# ---------------------------------------------------------------- catálogo

@router.get("/packages")
async def list_packages(_: User = Depends(require_user)):
    return {
        "packages": [
            {
                "package_id": p.package_id,
                "label": p.label,
                "sparks_amount": p.sparks_amount,
                "price_cents": p.price_cents,
                "currency": p.currency,
                "highlight": p.highlight,
                "destaque_tamanho": p.destaque_tamanho,
                "oculto": p.oculto,
                # O direito permanente que a compra concede. A loja ANUNCIA
                # com este campo e o webhook CONCEDE com o mesmo objeto de
                # catálogo (`sparks_store.concede_mentis_ilimitada`) — as
                # duas pontas não podem divergir.
                "beneficios": list(p.beneficios),
                "direitos": list(p.direitos),
            }
            for p in sparks_store.list_packages()
        ],
        "auto_recharge_frequencies_days": list(sparks_store.AUTO_RECHARGE_FREQUENCIES_DAYS),
        "default_baseline": sparks_store.DEFAULT_BASELINE,
    }


@router.get("/config")
async def get_config(_: User = Depends(require_user)):
    _require_mp_configured()
    return {"public_key": settings.MERCADOPAGO_PUBLIC_KEY}


# ------------------------------------------------------------- compra avulsa

class PayerPayload(BaseModel):
    email: EmailStr | None = None
    identification: dict | None = None


class PurchaseRequest(BaseModel):
    package_id: str
    payment_method_id: str
    # Obrigatório para cartão (`payment_method_id` != "pix"); Pix não gera
    # token — o Brick devolve só o método + dados do pagador. Validado em
    # `sparks_payments_service.create_purchase`, não aqui, porque a regra
    # depende do valor de `payment_method_id`.
    token: str | None = None
    installments: int = 1
    issuer_id: str | None = None
    payer: PayerPayload | None = None


@router.post("/purchases")
async def create_purchase(payload: PurchaseRequest, user: User = Depends(require_user)):
    _require_mp_configured()
    try:
        return await svc.create_purchase(_db, user, payload.package_id, payload.model_dump(exclude={"package_id"}))
    except svc.UnknownPackageError:
        raise HTTPException(status_code=400, detail="Pacote de Sparks desconhecido.")
    except svc.MissingCardTokenError:
        raise HTTPException(status_code=400, detail="Token do cartão ausente.")
    except mp.MercadoPagoError as exc:
        raise HTTPException(status_code=502, detail=f"Mercado Pago recusou o pagamento: {exc.message or exc.error}")


@router.get("/purchases/me")
async def my_purchases(user: User = Depends(require_user)):
    return {"items": await svc.list_purchases(_db, user.user_id)}


@router.get("/purchases/{purchase_id}")
async def purchase_status(purchase_id: str, user: User = Depends(require_user)):
    try:
        return await svc.get_purchase_status(_db, purchase_id, user.user_id)
    except svc.PurchaseNotFoundError:
        raise HTTPException(status_code=404, detail="Compra não encontrada.")


# --------------------------------------------------------- recarga automática

class AutoRechargeCreateRequest(BaseModel):
    package_id: str
    frequency_days: int
    baseline: int = sparks_store.DEFAULT_BASELINE
    card_token_id: str


class AutoRechargeUpdateRequest(BaseModel):
    package_id: str | None = None
    baseline: int | None = None


@router.post("/auto-recharge")
async def activate_auto_recharge(payload: AutoRechargeCreateRequest, user: User = Depends(require_user)):
    _require_mp_configured()
    try:
        return await svc.create_auto_recharge(
            _db, user,
            package_id=payload.package_id,
            frequency_days=payload.frequency_days,
            baseline=payload.baseline,
            card_token_id=payload.card_token_id,
        )
    except svc.UnknownPackageError:
        raise HTTPException(status_code=400, detail="Pacote de Sparks desconhecido.")
    except svc.InvalidFrequencyError:
        raise HTTPException(status_code=400, detail="Frequência de recarga inválida.")
    except mp.MercadoPagoError as exc:
        raise HTTPException(status_code=502, detail=f"Mercado Pago recusou a assinatura: {exc.message or exc.error}")


@router.get("/auto-recharge/me")
async def my_auto_recharge(user: User = Depends(require_user)):
    doc = await svc.get_auto_recharge(_db, user.user_id)
    return doc or {"active": False}


@router.patch("/auto-recharge")
async def patch_auto_recharge(payload: AutoRechargeUpdateRequest, user: User = Depends(require_user)):
    # Trocar o pacote muda o valor cobrado no Mercado Pago — mutação de
    # dinheiro, mesmo portão da criação.
    _require_mp_configured()
    try:
        return await svc.update_auto_recharge(_db, user, package_id=payload.package_id, baseline=payload.baseline)
    except svc.NoActiveAutoRechargeError:
        raise HTTPException(status_code=404, detail="Nenhuma recarga automática ativa.")
    except svc.UnknownPackageError:
        raise HTTPException(status_code=400, detail="Pacote de Sparks desconhecido.")
    except mp.MercadoPagoError as exc:
        raise HTTPException(status_code=502, detail=f"Mercado Pago recusou a alteração: {exc.message or exc.error}")


@router.delete("/auto-recharge")
async def deactivate_auto_recharge(user: User = Depends(require_user)):
    try:
        await svc.cancel_auto_recharge(_db, user)
    except svc.NoActiveAutoRechargeError:
        raise HTTPException(status_code=404, detail="Nenhuma recarga automática ativa.")
    except mp.MercadoPagoNotConfiguredError:
        # Cancelar não é bloqueado por política — quem tem cobrança recorrente
        # ativa jamais pode ficar preso nela. Mas sem credencial não há como
        # falar com o Mercado Pago, e um 500 mudo deixaria o aluno achando que
        # cancelou. Melhor dizer a verdade e dar um caminho.
        logger.error("Cancelamento pedido com a loja desligada (%s) — user=%s",
                     settings.MERCADOPAGO_MOTIVO_DESLIGADA, user.user_id)
        raise HTTPException(
            status_code=503,
            detail=(
                "Não conseguimos falar com o Mercado Pago agora. Sua recarga NÃO foi "
                "cancelada — cancele direto no app do Mercado Pago ou fale com o suporte."
            ),
        )
    except mp.MercadoPagoError as exc:
        raise HTTPException(status_code=502, detail=f"Mercado Pago recusou o cancelamento: {exc.message or exc.error}")
    return {"ok": True}


# ------------------------------------------------------------------- webhook

@router.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}

    notif_type = body.get("type") or request.query_params.get("topic")
    data_id = str(
        (body.get("data") or {}).get("id")
        or request.query_params.get("id")
        or request.query_params.get("data.id")
        or ""
    )
    notification_id = body.get("id")

    ok = mp.verify_webhook_signature(
        x_signature=request.headers.get("x-signature"),
        x_request_id=request.headers.get("x-request-id"),
        data_id=data_id,
        secret=settings.MERCADOPAGO_WEBHOOK_SECRET,
    )

    # Registra TODA notificação recebida, inclusive a que falha na assinatura.
    # Sem isto, "o webhook não chegou" e "o webhook chegou e foi rejeitado por
    # assinatura inválida" são indistinguíveis depois do fato — os dois deixam
    # o pagamento parado e o banco idêntico —, e o log do Fly não guarda
    # histórico suficiente para separar os dois. Nenhum segredo é gravado:
    # só se a assinatura conferiu, nunca a assinatura em si.
    await svc.registrar_recebimento_webhook(
        _db, tipo=notif_type, data_id=data_id, assinatura_valida=ok,
        tinha_assinatura=bool(request.headers.get("x-signature")),
    )

    if not ok:
        logger.warning(
            "Webhook do Mercado Pago REJEITADO por assinatura inválida (tipo=%s, data_id=%s). "
            "Se isto se repetir, o MERCADOPAGO_WEBHOOK_SECRET não corresponde ao "
            "cadastrado no painel — nenhum pagamento será creditado pelo webhook.",
            notif_type, data_id,
        )
        raise HTTPException(status_code=401, detail="Assinatura inválida.")

    if not data_id or not notif_type:
        return {"ok": True}

    dedupe_key = f"{notif_type}:{data_id}:{notification_id or ''}"
    first_time = await svc.dedupe_or_skip(_db, dedupe_key, notif_type)
    if not first_time:
        return {"ok": True, "duplicate": True}

    try:
        if notif_type == "payment":
            await svc.process_payment_webhook(_db, data_id)
        elif notif_type in ("subscription_preapproval", "preapproval"):
            await svc.process_subscription_webhook(_db, data_id)
        else:
            logger.info("Webhook Mercado Pago tipo não tratado: %s", notif_type)
    except mp.MercadoPagoError as exc:
        logger.exception("Falha ao processar webhook Mercado Pago (%s/%s): %s", notif_type, data_id, exc)
        raise HTTPException(status_code=500, detail="Falha ao processar notificação.")

    return {"ok": True}
