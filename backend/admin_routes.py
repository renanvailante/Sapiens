"""Admin-only routes: dashboard summary + user management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_admin
from models import User

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
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"ok": True, "is_admin": payload.is_admin}
