"""Lógica de negócio da loja de Sparks — compra avulsa e recarga automática.

Camadas separadas, de propósito:
  * **payment** (`sparks_payments`, Mongo) — auditoria de cada cobrança
    (manual ou gerada por um ciclo de assinatura). Nunca é a fonte de
    verdade dos Sparks.
  * **subscription** (`sparks_auto_recharge`, Mongo) — a configuração de
    recarga automática (calendário, pacote, autorização no Mercado Pago).
  * **crédito de Sparks** (Firestore, `firestore_service.grant_purchase_sparks`)
    — efeito colateral de um pagamento aprovado, aplicado só pelo webhook,
    nunca na resposta síncrona do checkout, com garantia atômica de "uma
    vez só" por `mp_payment_id`.

Todas as funções recebem `db` (Motor) explicitamente — nada de estado de
módulo — para serem chamáveis tanto pelas rotas quanto pelos testes offline
com um dublê de banco.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import pymongo.errors

import firestore_service as fs
import mercadopago_client as mp
import sparks_store
from models import User

logger = logging.getLogger("sapiens.sparks")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MissingCardTokenError(Exception):
    """Método de pagamento não-Pix sem `token` de cartão."""


class UnknownPackageError(Exception):
    def __init__(self, package_id: str):
        self.package_id = package_id
        super().__init__(f"pacote desconhecido: {package_id}")


class InvalidFrequencyError(Exception):
    def __init__(self, days: int):
        self.days = days
        super().__init__(f"frequência inválida: {days} dias")


class NoActiveAutoRechargeError(Exception):
    pass


class PurchaseNotFoundError(Exception):
    pass


def _frontend_url(path: str) -> str:
    import settings

    base = (settings.CORS_ORIGINS or ["http://localhost:3000"])[0].rstrip("/")
    return f"{base}{path}"


def _notification_url() -> str | None:
    """URL de notificação enviada em cada pagamento. `None` em
    desenvolvimento (a variável não é obrigatória) — o campo é então removido
    do payload, e o Mercado Pago cai no que estiver cadastrado no painel."""
    import settings

    return settings.MERCADOPAGO_NOTIFICATION_URL or None


# ---------------------------------------------------------------- compra avulsa

async def create_purchase(db, user: User, package_id: str, brick_payload: dict) -> dict:
    pkg = sparks_store.get_package(package_id)
    if pkg is None:
        raise UnknownPackageError(package_id)

    payment_method_id = brick_payload.get("payment_method_id")
    is_pix = payment_method_id == "pix"

    purchase_id = uuid.uuid4().hex
    payload = {
        "transaction_amount": round(pkg.price_cents / 100, 2),
        "description": f"Sapiens — {pkg.label}",
        "payment_method_id": payment_method_id,
        "payer": {
            "email": (brick_payload.get("payer") or {}).get("email") or user.email,
            "identification": (brick_payload.get("payer") or {}).get("identification"),
        },
        "external_reference": purchase_id,
        "notification_url": _notification_url(),
        "metadata": {
            "purchase_id": purchase_id,
            "user_id": user.user_id,
            "package_id": pkg.package_id,
            "source": "manual",
        },
    }
    if is_pix:
        # Pix não usa token nem parcelamento — só método + valor + pagador.
        # Enviar `installments`/`token` aqui não é o formato documentado
        # para Pix e não faz sentido (não há cartão nenhum envolvido).
        pass
    else:
        if not brick_payload.get("token"):
            raise MissingCardTokenError()
        payload["token"] = brick_payload["token"]
        payload["installments"] = int(brick_payload.get("installments") or 1)
        payload["issuer_id"] = brick_payload.get("issuer_id")

    payload = {k: v for k, v in payload.items() if v is not None}

    response = mp.create_payment(payload)

    pix = None
    if is_pix:
        # Formato oficial da Checkout API clássica (`POST /v1/payments`,
        # mesmo endpoint que o cartão já usa) para o retorno do Pix: o QR
        # Code em si (`qr_code_base64`, PNG sem o prefixo `data:image/...`,
        # acrescentado pelo frontend) e o código copia-e-cola (`qr_code`).
        transacao = (response.get("point_of_interaction") or {}).get("transaction_data") or {}
        pix = {
            "qr_code": transacao.get("qr_code"),
            "qr_code_base64": transacao.get("qr_code_base64"),
            "ticket_url": transacao.get("ticket_url"),
        }

    doc = {
        "purchase_id": purchase_id,
        "user_id": user.user_id,
        "package_id": pkg.package_id,
        "sparks_amount": pkg.sparks_amount,
        "price_cents": pkg.price_cents,
        "currency": pkg.currency,
        "source": "manual",
        "payment_method_id": payment_method_id,
        "mp_payment_id": str(response.get("id")),
        "status": response.get("status"),
        "status_detail": response.get("status_detail"),
        "pix": pix,
        "credited": False,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.sparks_payments.insert_one(doc)
    return {
        "purchase_id": purchase_id,
        "status": doc["status"],
        "status_detail": doc["status_detail"],
        "pix": pix,
    }


# Status em que o Mercado Pago já decidiu o destino do dinheiro. Qualquer
# outro (`pending`, `in_process`, `authorized`) ainda pode virar `approved` —
# e enquanto puder, temos que continuar perguntando.
_STATUS_FINAIS = {"rejected", "cancelled", "refunded", "charged_back"}


def _aguardando_confirmacao(doc: dict) -> bool:
    """O pagamento ainda pode virar Sparks e ainda não virou.

    `approved` sem `credited` entra aqui de propósito: significa que o
    dinheiro entrou e o crédito não completou — exatamente o estado que
    precisa ser reparado, não ignorado.
    """
    return (
        not doc.get("credited")
        and doc.get("status") not in _STATUS_FINAIS
        and bool(doc.get("mp_payment_id"))
    )


async def _reconciliar(db, mp_payment_id: str) -> None:
    """Repergunta o status ao Mercado Pago e credita se já foi pago.

    Uma falha aqui nunca pode derrubar quem chamou: o pior caso é devolver o
    estado local desatualizado, que é o que já acontecia antes.
    """
    try:
        await process_payment_webhook(db, mp_payment_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao reconciliar pagamento %s: %s", mp_payment_id, exc)


async def get_purchase_status(db, purchase_id: str, user_id: str) -> dict:
    """Estado da compra — reperguntando ao Mercado Pago enquanto o pagamento
    ainda estiver em aberto.

    Antes isto lia só o Mongo, então a tela de "aguardando pagamento" só
    mudava se o webhook tivesse chegado. Com Pix isso é o caminho comum e não
    a exceção: o aluno sai para o app do banco, paga, volta — e se a
    notificação se perdeu, ele fica olhando uma tela que nunca ia mudar,
    tendo pago de verdade. Agora a própria consulta que a tela já fazia é o
    que credita, em segundos, sem depender de o webhook chegar.
    """
    doc = await db.sparks_payments.find_one(
        {"purchase_id": purchase_id, "user_id": user_id}, {"_id": 0}
    )
    if doc is None:
        raise PurchaseNotFoundError(purchase_id)
    if _aguardando_confirmacao(doc):
        await _reconciliar(db, doc["mp_payment_id"])
        doc = await db.sparks_payments.find_one(
            {"purchase_id": purchase_id, "user_id": user_id}, {"_id": 0}
        )
    return doc


async def reconciliar_pendentes(db, limite: int = 100) -> dict:
    """Varre as compras em aberto e credita as que o Mercado Pago já aprovou.

    É a garantia de última instância do crédito: o webhook é o caminho
    rápido, este laço é o que torna o crédito inevitável. Sem ele, uma única
    notificação perdida deixa um aluno que pagou sem Sparks para sempre e sem
    ninguém saber — foi exatamente o que aconteceu em 2026-09-07.

    Não há janela de tempo, e isso é deliberado: um pagamento pendente sempre
    termina em algum estado final no Mercado Pago — um Pix não pago expira em
    24h (o padrão da Checkout API, que não alteramos) e vira `cancelled` —, e
    ao receber esse estado ele sai desta consulta sozinho. O conjunto se
    esvazia por si; o que uma janela faria era abandonar em silêncio
    justamente o caso raro que este laço existe para salvar. Ordena do mais
    antigo para o mais novo para que nada fique preso atrás do teto de
    `limite`.

    O custo é limitado por essas 24h: um QR Code gerado e abandonado é
    reperguntado a cada ciclo até expirar, e some. Se o volume de checkouts
    abandonados crescer a ponto de isso pesar, o caminho é encurtar o prazo do
    Pix (`date_of_expiration` na criação), não afrouxar esta varredura.
    """
    cursor = db.sparks_payments.find(
        {"credited": False, "status": {"$nin": list(_STATUS_FINAIS)},
         "mp_payment_id": {"$exists": True}},
        {"_id": 0, "mp_payment_id": 1},
    ).sort("created_at", 1).limit(limite)
    pendentes = await cursor.to_list(length=limite)

    creditados = 0
    situacao: dict[str, str] = {}
    for doc in pendentes:
        try:
            resultado = await process_payment_webhook(db, doc["mp_payment_id"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reconciliação falhou para %s: %s", doc["mp_payment_id"], exc)
            situacao[doc["mp_payment_id"]] = f"erro: {exc}"
            continue
        if resultado.get("credited"):
            creditados += 1
            situacao[doc["mp_payment_id"]] = "creditado agora"
            logger.info(
                "Reconciliação creditou o pagamento %s — o webhook não tinha chegado.",
                doc["mp_payment_id"],
            )
        else:
            situacao[doc["mp_payment_id"]] = str(resultado.get("status"))
    return {"verificados": len(pendentes), "creditados": creditados, "situacao": situacao}


async def list_purchases(db, user_id: str, limit: int = 100) -> list[dict]:
    cursor = db.sparks_payments.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


# ------------------------------------------------------------ recarga automática

async def create_auto_recharge(
    db, user: User, *, package_id: str, frequency_days: int, baseline: int, card_token_id: str
) -> dict:
    pkg = sparks_store.get_package(package_id)
    if pkg is None:
        raise UnknownPackageError(package_id)
    if not sparks_store.is_valid_frequency(frequency_days):
        raise InvalidFrequencyError(frequency_days)

    existing = await db.sparks_auto_recharge.find_one({"user_id": user.user_id})
    if existing and existing.get("active") and existing.get("mp_preapproval_id"):
        # Já tem uma assinatura ativa — cancela a antiga primeiro (o MP não
        # deixa reaproveitar a mesma assinatura para trocar de frequência).
        try:
            mp.update_preapproval(existing["mp_preapproval_id"], {"status": "cancelled"})
        except mp.MercadoPagoError:
            logger.warning("Falha ao cancelar assinatura anterior de %s antes de recriar.", user.user_id)

    payload = {
        "reason": f"Sapiens — recarga automática ({pkg.label} a cada {frequency_days} dias)",
        "auto_recurring": {
            "frequency": frequency_days,
            "frequency_type": "days",
            "transaction_amount": round(pkg.price_cents / 100, 2),
            "currency_id": pkg.currency,
        },
        "payer_email": user.email,
        "card_token_id": card_token_id,
        "back_url": _frontend_url("/sparks"),
        "external_reference": user.user_id,
        "status": "authorized",
    }
    response = mp.create_preapproval(payload)

    doc = {
        "user_id": user.user_id,
        "active": response.get("status") == "authorized",
        "package_id": pkg.package_id,
        "frequency_days": frequency_days,
        "baseline": baseline,
        "mp_preapproval_id": str(response.get("id")),
        "status": response.get("status"),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.sparks_auto_recharge.update_one(
        {"user_id": user.user_id}, {"$set": doc}, upsert=True
    )
    return doc


async def get_auto_recharge(db, user_id: str) -> dict | None:
    """Config local + status/valor/`próxima cobrança` relidos do Mercado Pago
    — nunca só o cache local, que pode estar desatualizado se um ciclo já
    rodou ou se o MP cancelou por falha de pagamento repetida."""
    doc = await db.sparks_auto_recharge.find_one({"user_id": user_id}, {"_id": 0})
    if doc is None:
        return None
    if doc.get("mp_preapproval_id"):
        try:
            live = mp.get_preapproval(doc["mp_preapproval_id"])
            doc["status"] = live.get("status", doc.get("status"))
            doc["next_payment_date"] = (live.get("auto_recurring") or {}).get("next_payment_date")
            doc["transaction_amount"] = (live.get("auto_recurring") or {}).get("transaction_amount")
            doc["active"] = live.get("status") == "authorized"
        except (mp.MercadoPagoError, mp.MercadoPagoNotConfiguredError):
            # `MercadoPagoNotConfiguredError` é RuntimeError, não
            # MercadoPagoError: escapava daqui e transformava uma LEITURA em
            # 500 sempre que a loja estivesse desligada. Cair para o documento
            # local é a degradação correta — mostra o que sabemos, sem inventar.
            logger.warning("Falha ao reler assinatura %s no Mercado Pago.", doc["mp_preapproval_id"])
    return doc


async def update_auto_recharge(db, user: User, *, package_id: str | None, baseline: int | None) -> dict:
    doc = await db.sparks_auto_recharge.find_one({"user_id": user.user_id})
    if not doc or not doc.get("active"):
        raise NoActiveAutoRechargeError()

    updates: dict[str, Any] = {"updated_at": _now_iso()}
    if baseline is not None:
        updates["baseline"] = baseline
    if package_id is not None and package_id != doc.get("package_id"):
        pkg = sparks_store.get_package(package_id)
        if pkg is None:
            raise UnknownPackageError(package_id)
        mp.update_preapproval(
            doc["mp_preapproval_id"],
            {"auto_recurring": {"transaction_amount": round(pkg.price_cents / 100, 2)}},
        )
        updates["package_id"] = pkg.package_id

    await db.sparks_auto_recharge.update_one({"user_id": user.user_id}, {"$set": updates})
    return await db.sparks_auto_recharge.find_one({"user_id": user.user_id}, {"_id": 0})


async def cancel_auto_recharge(db, user: User) -> None:
    doc = await db.sparks_auto_recharge.find_one({"user_id": user.user_id})
    if not doc or not doc.get("active"):
        raise NoActiveAutoRechargeError()
    mp.update_preapproval(doc["mp_preapproval_id"], {"status": "cancelled"})
    await db.sparks_auto_recharge.update_one(
        {"user_id": user.user_id},
        {"$set": {"active": False, "status": "cancelled", "updated_at": _now_iso()}},
    )


# --------------------------------------------------------------------- webhook

async def registrar_recebimento_webhook(
    db, *, tipo: str | None, data_id: str | None, assinatura_valida: bool, tinha_assinatura: bool
) -> None:
    """Prova de que o Mercado Pago chamou (ou nunca chamou) este endpoint.

    Gravado antes de qualquer decisão, para que uma notificação recusada
    apareça igual a uma aceita. Nunca falha para quem chamou: perder a
    auditoria não pode impedir o processamento de um pagamento real.
    """
    try:
        await db.webhook_recebimentos.insert_one({
            "tipo": tipo,
            "data_id": data_id,
            "assinatura_valida": assinatura_valida,
            "tinha_assinatura": tinha_assinatura,
            "received_at": _now_iso(),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao registrar recebimento de webhook: %s", exc)


async def dedupe_or_skip(db, dedupe_key: str, raw_type: str) -> bool:
    """`True` na primeira vez que essa notificação é vista; `False` numa
    entrega duplicada (o Mercado Pago reenvia em caso de timeout/retry).
    Garantia atômica: índice único em `webhook_events.dedupe_key`, criado no
    startup do servidor — `insert_one` falha com `DuplicateKeyError` na
    segunda tentativa, nunca há corrida entre elas.
    """
    try:
        await db.webhook_events.insert_one(
            {"dedupe_key": dedupe_key, "type": raw_type, "received_at": _now_iso()}
        )
        return True
    except pymongo.errors.DuplicateKeyError:
        return False


async def process_payment_webhook(db, mp_payment_id: str) -> dict:
    """Rebusca o pagamento no Mercado Pago pelo id (nunca confia no corpo do
    webhook) e credita Sparks se `status == "approved"`.

    Cobre dois casos:
      * compra manual — já existe `sparks_payments` com esse `mp_payment_id`
        (gravado por `create_purchase` na hora da criação).
      * ciclo de recarga automática — o MP gera o pagamento sozinho; o
        registro é criado aqui, ligado à assinatura via `preapproval_id` (o
        campo que o MP devolve nos pagamentos gerados por uma assinatura) ou,
        em segundo lugar, `external_reference`. Se nenhum dos dois casar com
        uma assinatura conhecida, o pagamento fica registrado como
        não-identificado — nunca credita saldo de um usuário adivinhado.
    """
    payment = mp.get_payment(mp_payment_id)
    mp_payment_id = str(payment.get("id"))
    status = payment.get("status")

    existing = await db.sparks_payments.find_one({"mp_payment_id": mp_payment_id})

    if existing is None:
        metadata = payment.get("metadata") or {}
        user_id = metadata.get("user_id")
        package_id = metadata.get("package_id")
        source = metadata.get("source", "manual")
        subscription_id = None

        if not user_id:
            # Não veio de create_purchase (metadata vazio) — é provavelmente
            # um ciclo de assinatura gerado pelo próprio Mercado Pago.
            preapproval_id = payment.get("preapproval_id") or payment.get("external_reference")
            sub = None
            if preapproval_id:
                sub = await db.sparks_auto_recharge.find_one({"mp_preapproval_id": preapproval_id})
            if sub is None:
                logger.warning(
                    "Pagamento %s aprovado sem correspondência de assinatura/compra conhecida — "
                    "registrado sem crédito para revisão manual.", mp_payment_id,
                )
                await db.sparks_payments.insert_one({
                    "mp_payment_id": mp_payment_id,
                    "status": status,
                    "unmatched": True,
                    "raw_metadata": metadata,
                    "raw_preapproval_id": payment.get("preapproval_id"),
                    "raw_external_reference": payment.get("external_reference"),
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                    "credited": False,
                })
                return {"matched": False}
            user_id = sub["user_id"]
            package_id = sub["package_id"]
            source = "auto_recharge"
            subscription_id = sub["user_id"]

        pkg = sparks_store.get_package(package_id)
        existing = {
            "purchase_id": uuid.uuid4().hex,
            "user_id": user_id,
            "package_id": package_id,
            "sparks_amount": pkg.sparks_amount if pkg else 0,
            "price_cents": pkg.price_cents if pkg else 0,
            "currency": pkg.currency if pkg else "BRL",
            "source": source,
            "subscription_id": subscription_id,
            "mp_payment_id": mp_payment_id,
            "status": status,
            "credited": False,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await db.sparks_payments.insert_one(existing)

    await db.sparks_payments.update_one(
        {"mp_payment_id": mp_payment_id}, {"$set": {"status": status, "updated_at": _now_iso()}}
    )

    if status == "approved" and not existing.get("credited") and existing.get("user_id"):
        resultado = fs.grant_purchase_sparks(
            existing["user_id"],
            payment_id=mp_payment_id,
            package_id=existing["package_id"],
            sparks_amount=existing["sparks_amount"],
            price_cents=existing["price_cents"],
            currency=existing["currency"],
            source=existing["source"],
        )
        await db.sparks_payments.update_one(
            {"mp_payment_id": mp_payment_id}, {"$set": {"credited": True, "updated_at": _now_iso()}}
        )
        return {"matched": True, "credited": True, "ja_creditado": resultado.get("ja_creditado", False)}

    return {"matched": True, "credited": False, "status": status}


async def process_subscription_webhook(db, mp_preapproval_id: str) -> dict:
    """Sincroniza `status`/`active` de `sparks_auto_recharge` com o estado
    real da assinatura no Mercado Pago — cobre o caso do MP cancelar sozinho
    depois de falhas repetidas de cobrança."""
    preapproval = mp.get_preapproval(mp_preapproval_id)
    status = preapproval.get("status")
    res = await db.sparks_auto_recharge.update_one(
        {"mp_preapproval_id": mp_preapproval_id},
        {"$set": {"status": status, "active": status == "authorized", "updated_at": _now_iso()}},
    )
    return {"matched": res.matched_count > 0, "status": status}
