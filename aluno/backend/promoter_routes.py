"""Painel do promoter — só o que ele precisa para conferir a própria comissão.

Um promoter não é uma segunda flag de usuário: é qualquer conta cujo e-mail
está gravado em `promo_codes.promoter_email` (o admin gerencia isso em
`/admin/promo-codes`, ver `promo_codes_routes.py`). O acesso e o ESCOPO nascem
do mesmo lugar — o filtro `{"promoter_email": <e-mail de quem está logado>}` —
o que faz o isolamento entre promoters uma propriedade da consulta, não uma
checagem que alguém pode esquecer de repetir numa rota nova. Um promoter só
enxerga: quantos alunos usaram O CUPOM DELE, o saldo de Sparks de cada um e
quanto cada um gastou comprando Sparks — nunca a lista completa de alunos,
nunca outro cupom, nunca dado de outro promoter.

Saldo de Sparks vem do Firestore, **um `read_sparks_balance` por aluno do
promoter** (não uma varredura de `students` inteira, como o painel de admin
faz) — o custo escala com o tamanho da carteira do promoter, não com a base
inteira de alunos (ver `project_aluno_disciplina_leitura_firestore`).
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

import firestore_service as fs
from auth import require_user
from models import User

logger = logging.getLogger("sapiens.promoter")

router = APIRouter(prefix="/promoter", tags=["promoter"])

_db = None
def set_db(db):
    global _db
    _db = db


async def require_promoter(user: User = Depends(require_user)) -> User:
    email = (user.email or "").strip().lower()
    tem_cupom = await _db.promo_codes.find_one({"promoter_email": email}, {"_id": 1})
    if not tem_cupom:
        raise HTTPException(status_code=403, detail="Acesso de promoter não concedido para esta conta.")
    return user


async def _saldo_de(uid: str) -> int | None:
    try:
        return await asyncio.to_thread(fs.read_sparks_balance, uid)
    except Exception:  # noqa: BLE001
        logger.warning("Saldo de Sparks indisponível para %s no painel do promoter.", uid)
        return None


@router.get("/dashboard")
async def dashboard(promoter: User = Depends(require_promoter)):
    email = promoter.email.strip().lower()
    cupons = await _db.promo_codes.find(
        {"promoter_email": email}, {"_id": 0, "code": 1, "sparks_amount": 1, "active": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(200)
    codigos = [c["code"] for c in cupons]

    alunos = await _db.users.find(
        {"promo_code": {"$in": codigos}},
        {"_id": 0, "user_id": 1, "name": 1, "promo_code": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(5000)
    ids = [a["user_id"] for a in alunos]

    saldos: dict[str, int | None] = {}
    if ids:
        resultados = await asyncio.gather(*(_saldo_de(uid) for uid in ids))
        saldos = dict(zip(ids, resultados))

    # Dinheiro gasto vem do Mongo (`sparks_payments`), não do Firestore: é a
    # mesma auditoria de cobrança que o admin usa em `/admin/users/{id}/detalhe`
    # — só compras já CREDITADAS contam, porque só essas o aluno pagou de
    # verdade (um Pix pendente ou recusado não é dinheiro que passou a mão).
    gastos: dict[str, int] = {}
    if ids:
        pagamentos = await _db.sparks_payments.find(
            {"user_id": {"$in": ids}, "credited": True}, {"_id": 0, "user_id": 1, "price_cents": 1},
        ).to_list(20000)
        for p in pagamentos:
            uid = p["user_id"]
            gastos[uid] = gastos.get(uid, 0) + int(p.get("price_cents") or 0)

    por_codigo: dict[str, list[dict]] = {c: [] for c in codigos}
    for a in alunos:
        por_codigo.setdefault(a["promo_code"], []).append({
            "name": a.get("name"),
            "sparks_balance": saldos.get(a["user_id"]),
            "gasto_centavos": gastos.get(a["user_id"], 0),
            "desde": a.get("created_at"),
        })

    cupons_view = []
    for c in cupons:
        linhas = por_codigo.get(c["code"], [])
        cupons_view.append({
            "code": c["code"],
            "active": c.get("active", True),
            "alunos": linhas,
            "alunos_count": len(linhas),
            "gasto_total_centavos": sum(x["gasto_centavos"] for x in linhas),
        })

    return {
        "promoter_email": email,
        "cupons": cupons_view,
        "total_alunos": len(alunos),
        "total_gasto_centavos": sum(c["gasto_total_centavos"] for c in cupons_view),
    }
