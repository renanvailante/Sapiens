"""Rotas da indicação de amigo.

Só duas, e as duas são de leitura do PRÓPRIO aluno:

* `GET /indicacoes/me` — o código dele e quem entrou por ele;
* `GET /admin/indicacoes` — a mesma coisa, da cadeira do admin, para todas
  as contas de uma vez.

Não existe rota pública que valide um código, nem aqui nem em
`promo_codes_routes.py`, e pelo mesmo motivo: uma rota dessas é um oráculo
para enumerar quais códigos existem — e aqui cada código é um ALUNO. O código
só é interpretado no cadastro (`auth._bonus_de_cadastro`), onde errar não dá
nenhum sinal de volta além de a conta entrar sem vínculo.

A regra do prêmio não mora aqui: ela é cobrada no webhook de pagamento
aprovado (`sparks_payments_service.process_payment_webhook`), que é o único
ponto do produto em que dinheiro vira Spark.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

import indicacoes
from auth import require_admin, require_user
from models import User

router = APIRouter(tags=["indicacoes"])

_db = None


def set_db(db):
    global _db
    _db = db


@router.get("/indicacoes/me")
async def minhas_indicacoes(user: User = Depends(require_user)):
    """O código do aluno — criado agora, se ele ainda não tinha — mais a
    lista de quem se cadastrou com ele e quanto cada um já rendeu."""
    return await indicacoes.resumo(_db, user.user_id, user.name)


@router.get("/admin/indicacoes")
async def painel_de_indicacoes(admin: User = Depends(require_admin)):
    """Quem indicou quem, e quanto já foi pago em Sparks.

    Duas consultas ao Mongo no total (vínculos + contas envolvidas), e não uma
    por linha: a tela é uma lista e cresce com a base.
    """
    vinculos = await _db.indicacoes.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    ids = {v["indicador_id"] for v in vinculos} | {v["indicado_id"] for v in vinculos}
    contas = await _db.users.find(
        {"user_id": {"$in": list(ids)}},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1},
    ).to_list(5000) if ids else []
    por_id = {c["user_id"]: c for c in contas}

    def ficha(user_id: str) -> dict:
        c = por_id.get(user_id) or {}
        return {"user_id": user_id, "name": c.get("name"), "email": c.get("email")}

    linhas = [
        {
            "indicador": ficha(v["indicador_id"]),
            "indicado": ficha(v["indicado_id"]),
            "codigo": v.get("codigo"),
            "created_at": v.get("created_at"),
            "premio_sparks": int(v.get("premio_sparks") or 0),
            "premio_em": v.get("premio_em"),
        }
        for v in vinculos
    ]
    return {
        "items": linhas,
        "total": len(linhas),
        "ja_converteram": sum(1 for l in linhas if l["premio_em"]),
        "sparks_pagos": sum(l["premio_sparks"] for l in linhas),
    }
