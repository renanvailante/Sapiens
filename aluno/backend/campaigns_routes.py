"""Rotas de campanhas (tráfego pago + conteúdo orgânico) e rastreio de clique.

Duas partes bem separadas:

* `/admin/campaigns/*` — CRUD, só admin.
* `POST /track/click` — PÚBLICA, sem auth (quem clica ainda não tem conta).
  Serve tanto o link de um influencer (`?ref=CODIGO`) quanto de uma campanha
  paga (`?campanha_id=...&utm_source=...`). Rate limit por IP: um clique
  legítimo não repete dezenas de vezes por segundo, e é a única defesa que
  esta rota tem contra flood (ver `rate_limit.py`).
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends

import campaigns
import rate_limit
from auth import require_admin
from models import User

router = APIRouter(prefix="/admin/campaigns", tags=["campaigns"])
router_publico = APIRouter(tags=["campaigns-publico"])

_db = None
def set_db(db):
    global _db
    _db = db


@router.get("")
async def listar(admin: User = Depends(require_admin)):
    return {"items": await campaigns.listar(_db)}


@router.post("")
async def criar(payload: dict = Body(...), admin: User = Depends(require_admin)):
    return await campaigns.criar(_db, payload)


@router.patch("/{campanha_id}")
async def atualizar(campanha_id: str, payload: dict = Body(...), admin: User = Depends(require_admin)):
    return await campaigns.atualizar(_db, campanha_id, payload)


@router.get("/comparativo")
async def comparativo(admin: User = Depends(require_admin)):
    """Tráfego pago vs influencer vs orgânico — seção 13 do programa."""
    return await campaigns.resumo_comparativo(_db)


@router_publico.post("/track/click")
async def track_click(
    campanha_id: str | None = Body(default=None, embed=True),
    utm_source: str | None = Body(default=None, embed=True),
    codigo: str | None = Body(default=None, embed=True),
    _: None = Depends(rate_limit.por_ip("acervo")),
):
    await campaigns.registrar_clique(_db, campanha_id=campanha_id, utm_source=utm_source, codigo=codigo)
    return {"ok": True}
