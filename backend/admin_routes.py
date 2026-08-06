"""Admin-only routes: dashboard summary + user management."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_admin
from models import User
import firestore_service as fs

router = APIRouter(prefix="/admin", tags=["admin"])

_db = None
def set_db(db):
    global _db
    _db = db


@router.get("/summary")
async def summary(admin: User = Depends(require_admin)):
    exams = await _db.exams.count_documents({})
    keys = await _db.answer_keys.count_documents({})
    analyses = await _db.analyses.count_documents({"deleted": False})
    trashed = await _db.analyses.count_documents({"deleted": True})
    users_count = await _db.users.count_documents({})
    admins_count = await _db.users.count_documents({"is_admin": True})
    feed_items = await _db.feed_items.count_documents({})
    feed_published = await _db.feed_items.count_documents({"published": True})
    annotations = await _db.question_annotations.count_documents({})
    interactions = await _db.feed_interactions.count_documents({})
    return {
        "exams": exams,
        "answer_keys": keys,
        "analyses_active": analyses,
        "analyses_trashed": trashed,
        "users": users_count,
        "admins": admins_count,
        "feed_items": feed_items,
        "feed_items_published": feed_published,
        "annotations": annotations,
        "feed_interactions": interactions,
    }


@router.get("/users")
async def list_users(admin: User = Depends(require_admin)):
    docs = await _db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(1000)
    return docs


class UpdateUserRequest(BaseModel):
    is_admin: bool


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UpdateUserRequest, admin: User = Depends(require_admin)):
    if admin.user_id == user_id and payload.is_admin is False:
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio acesso admin.")
    res = await _db.users.update_one({"user_id": user_id}, {"$set": {"is_admin": payload.is_admin}})


# ---------- Firestore sync (admin only) ----------

def _build_public_doc(master: dict) -> dict:
    """Gera a versao FILTRADA (aluno) a partir do doc completo (master).
    Mantem SOMENTE questao (enunciado, alternativas, recursos) e dados
    basicos da fonte. Nenhum processo cognitivo / dominio / competencia /
    metadado interno. item_id aleatorio e unico por questao.
    """
    q = (master.get("pipeline") or {}).get("questao") or master.get("questao") or {}
    f = (master.get("pipeline") or {}).get("fonte") or master.get("fonte") or {}
    alternativas = [
        {"letra": a.get("letra"), "texto": a.get("texto"), "correta": a.get("correta")}
        for a in (q.get("alternativas") or [])
    ]
    return {
        "item_id": uuid.uuid4().hex,
        "master_id": master.get("id"),
        "questao": {
            "enunciado": q.get("enunciado"),
            "alternativas": alternativas,
            "recursos": q.get("recursos") or {},
        },
        "fonte": {
            "disciplina": f.get("disciplina"),
            "ano": f.get("ano"),
            "prova": f.get("prova"),
            "banca": f.get("banca"),
            "tema": f.get("tema"),
            "conteudo": f.get("conteudo"),
        },
    }


@router.post("/firestore/sync")
async def firestore_sync(admin: User = Depends(require_admin)):
    """Le TODAS as questoes (colecao 'itens') e schema completo do Firestore,
    salva o schema COMPLETO em 'questoes_master' (visivel/editavel so no admin)
    e (re)gera a versao FILTRADA em 'questoes_public' (consumida pelo aluno).
    """
    try:
        items = await asyncio.to_thread(_read_all_firestore, "itens")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Firestore error: {exc}")

    # 1) master = schema completo (upsert por id original)
    for it in items:
        await _db.questoes_master.update_one(
            {"id": it.get("id")}, {"$set": it}, upsert=True
        )

    # 2) public = versao filtrada regenerada a partir do master
    await _db.questoes_public.delete_many({})
    publics = [_build_public_doc(it) for it in items]
    if publics:
        await _db.questoes_public.insert_many(publics)

    return {
        "ok": True,
        "master_count": len(items),
        "public_count": len(publics),
    }


def _read_all_firestore(collection: str) -> list[dict]:
    """Le TODOS os documentos de uma colecao do Firestore (sem limite de 500)."""
    docs = fs.get_firestore().collection(collection).stream()
    return [{"id": snap.id, **(snap.to_dict() or {})} for snap in docs]


@router.get("/questoes-master")
async def list_questoes_master(limit: int = 500, admin: User = Depends(require_admin)):
    limit = max(1, min(int(limit), 2000))
    docs = await _db.questoes_master.find({}, {"_id": 0}).limit(limit).to_list(limit)
    return {"items": docs, "count": len(docs)}


class UpdateMasterRequest(BaseModel):
    data: dict


@router.patch("/questoes-master/{item_id}")
async def update_questao_master(item_id: str, payload: UpdateMasterRequest, admin: User = Depends(require_admin)):
    """Edita um doc master e regenera a versao publica correspondente."""
    res = await _db.questoes_master.update_one({"id": item_id}, {"$set": payload.data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Questão não encontrada")
    master = await _db.questoes_master.find_one({"id": item_id}, {"_id": 0})
    # regenera a versao publica desta questao, preservando o item_id existente
    existing = await _db.questoes_public.find_one({"master_id": item_id}, {"_id": 0, "item_id": 1})
    pub = _build_public_doc(master)
    if existing and existing.get("item_id"):
        pub["item_id"] = existing["item_id"]
    await _db.questoes_public.update_one(
        {"master_id": item_id}, {"$set": pub}, upsert=True
    )
    return {"ok": True}

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"ok": True, "is_admin": payload.is_admin}
