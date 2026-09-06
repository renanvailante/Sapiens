"""Rotas de códigos promocionais — bônus de Sparks no cadastro.

Um código é opcional no signup (e-mail/senha ou Google). Sem código válido, a
conta nova recebe o bônus padrão (`firestore_service.SPARKS_INITIAL_BALANCE`,
hoje 100). Com um código ativo, recebe a quantidade programada pelo admin em
vez do padrão — nunca as duas coisas somadas.

O catálogo vive no Mongo (`promo_codes`), não no Firestore: é configuração de
produto (como o catálogo de `sparks_store.py`), não estado do aluno.

Gestão é 100% admin (`/admin/promo-codes`); a validação em si
(`validar_e_registrar_uso`) é chamada só por `auth.py` no momento do signup —
não existe rota pública que aceite um código, então não há como sondar quais
códigos existem tentando um por um.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin
from models import CreatePromoCodeRequest, UpdatePromoCodeRequest, User, _now_iso

router = APIRouter(prefix="/admin/promo-codes", tags=["promo-codes"])

_db = None
def set_db(db):
    global _db
    _db = db


def _normalizar(code: str) -> str:
    return (code or "").strip().upper()


@router.get("")
async def list_promo_codes(admin: User = Depends(require_admin)):
    return await _db.promo_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@router.post("")
async def create_promo_code(payload: CreatePromoCodeRequest, admin: User = Depends(require_admin)):
    code = _normalizar(payload.code)
    if not code:
        raise HTTPException(status_code=422, detail="Código vazio.")
    if await _db.promo_codes.find_one({"code": code}, {"_id": 1}):
        raise HTTPException(status_code=400, detail="Já existe um código com esse nome.")
    doc = {
        "code": code,
        "sparks_amount": payload.sparks_amount,
        "active": True,
        "usos": 0,
        "created_at": _now_iso(),
    }
    await _db.promo_codes.insert_one(doc)
    return doc


@router.patch("/{code}")
async def update_promo_code(code: str, payload: UpdatePromoCodeRequest, admin: User = Depends(require_admin)):
    campos = payload.model_dump(exclude_none=True)
    if not campos:
        raise HTTPException(status_code=422, detail="Nada para atualizar.")
    alvo = _normalizar(code)
    res = await _db.promo_codes.update_one({"code": alvo}, {"$set": campos})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Código não encontrado.")
    return await _db.promo_codes.find_one({"code": alvo}, {"_id": 0})


@router.delete("/{code}")
async def delete_promo_code(code: str, admin: User = Depends(require_admin)):
    res = await _db.promo_codes.delete_one({"code": _normalizar(code)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Código não encontrado.")
    return {"ok": True}


async def validar_e_registrar_uso(code: str | None) -> int | None:
    """Valida um código informado no signup e conta o uso.

    Retorna a quantidade de Sparks do código se ele existir e estiver ativo,
    ou `None` se o código for vazio, inexistente ou desativado — nesse caso
    quem chamou aplica o bônus padrão. Um código digitado errado nunca vira
    erro de cadastro: só faz a conta nova entrar sem o bônus especial.
    """
    normalizado = _normalizar(code) if code else ""
    if not normalizado:
        return None
    doc = await _db.promo_codes.find_one_and_update(
        {"code": normalizado, "active": True},
        {"$inc": {"usos": 1}},
    )
    if not doc:
        return None
    return doc.get("sparks_amount")
