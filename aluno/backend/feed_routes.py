"""Learning feed routes: infinite cursor-based feed + interaction/progress capture.

Zero cognitive interpretation happens here — interactions are stored raw for
the future cognitive engine to analyze.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import require_admin, require_user
from feed_models import FeedInteractionIn, FeedProgressIn, FeedItem, FeedItemIn
from models import User

router = APIRouter(prefix="", tags=["feed"])

_db = None
def set_db(db):
    global _db
    _db = db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Public feed browsing (auth optional but recommended) ----------

@router.get("/feed")
async def get_feed(
    cursor: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=30),
):
    """Cursor-based infinite feed.

    `cursor` is the last sequence_order the client has already consumed.
    Returns items strictly after it, up to `limit`. Client should preload
    a few items ahead of the visible one to make swipe transitions instant.
    """
    q = {"sequence_order": {"$gt": cursor}, "published": True}
    items = await _db.feed_items.find(q, {"_id": 0}).sort("sequence_order", 1).limit(limit).to_list(limit)
    next_cursor = items[-1]["sequence_order"] if items else cursor
    has_more = False
    if items:
        remaining = await _db.feed_items.count_documents(
            {"sequence_order": {"$gt": next_cursor}, "published": True}
        )
        has_more = remaining > 0
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}


# ---------- Interactions (require auth) ----------

@router.post("/feed/interactions")
async def log_interaction(payload: FeedInteractionIn, user: User = Depends(require_user)):
    """Append a raw interaction event. Multiple calls per card are allowed
    (e.g., separate events for open, answer, complete). Events are appended
    to `interaction_history` on the same interaction doc keyed by (user, content).
    """
    item = await _db.feed_items.find_one({"content_id": payload.content_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    now = _now()
    doc = await _db.feed_interactions.find_one(
        {"user_id": user.user_id, "content_id": payload.content_id}, {"_id": 0}
    )

    event = payload.event or {}
    if event and "at" not in event:
        event["at"] = now

    if doc:
        update = {
            "$inc": {"time_spent_ms": max(0, payload.time_spent_ms)},
            "$set": {},
        }
        if payload.completed:
            update["$set"]["completed"] = True
        if payload.user_response:
            update["$set"]["user_response"] = payload.user_response
        if payload.is_correct is not None:
            update["$set"]["is_correct"] = payload.is_correct
        if event:
            update["$push"] = {"interaction_history": event}
        if not update["$set"]:
            update.pop("$set")
        await _db.feed_interactions.update_one(
            {"user_id": user.user_id, "content_id": payload.content_id}, update
        )
    else:
        new_doc = {
            "interaction_id": _now(),  # ISO ts is fine as id here; unique
            "user_id": user.user_id,
            "content_id": payload.content_id,
            "time_spent_ms": max(0, payload.time_spent_ms),
            "completed": bool(payload.completed),
            "user_response": payload.user_response or {},
            "is_correct": payload.is_correct,
            "interaction_history": [event] if event else [],
            "created_at": now,
        }
        await _db.feed_interactions.insert_one(new_doc)

    # If item was completed, add to progress
    if payload.completed:
        await _db.feed_progress.update_one(
            {"user_id": user.user_id},
            {"$addToSet": {"completed_content_ids": payload.content_id},
             "$set": {"updated_at": now}},
            upsert=True,
        )

    return {"ok": True}


# ---------- Progress ----------

@router.get("/feed/progress")
async def get_progress(user: User = Depends(require_user)):
    doc = await _db.feed_progress.find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"user_id": user.user_id, "last_position": 0, "last_content_id": None,
                "completed_content_ids": []}
    return doc


@router.post("/feed/progress")
async def set_progress(payload: FeedProgressIn, user: User = Depends(require_user)):
    await _db.feed_progress.update_one(
        {"user_id": user.user_id},
        {"$set": {"last_position": payload.last_position,
                  "last_content_id": payload.last_content_id,
                  "updated_at": _now()}},
        upsert=True,
    )
    return {"ok": True}


# ---------- Admin CRUD ----------

@router.get("/admin/feed-items")
async def admin_list_items(admin: User = Depends(require_admin)):
    items = await _db.feed_items.find({}, {"_id": 0}).sort("sequence_order", 1).to_list(1000)
    return items


@router.post("/admin/feed-items")
async def admin_create_item(payload: FeedItemIn, admin: User = Depends(require_admin)):
    if payload.sequence_order == 0:
        # Auto-assign next order
        last = await _db.feed_items.find_one({}, sort=[("sequence_order", -1)])
        seq = ((last or {}).get("sequence_order", 0) or 0) + 1
    else:
        seq = payload.sequence_order
    item = FeedItem(**{**payload.model_dump(), "sequence_order": seq})
    await _db.feed_items.insert_one(item.model_dump())
    return item.model_dump()


class FeedItemPatch(BaseModel):
    content_type: str | None = None
    sequence_order: int | None = None
    question_data: dict | None = None
    answer_options: list[dict] | None = None
    explanation_data: dict | None = None
    multimedia_assets: list[dict] | None = None
    metadata: dict | None = None
    cognitive_mapping_reference: str | None = None
    difficulty_reference: str | None = None
    learning_objectives: list[str] | None = None
    background_theme: str | None = None
    published: bool | None = None


@router.patch("/admin/feed-items/{content_id}")
async def admin_update_item(content_id: str, payload: FeedItemPatch, admin: User = Depends(require_admin)):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        return {"ok": True, "changes": 0}
    changes["updated_at"] = _now()
    res = await _db.feed_items.update_one({"content_id": content_id}, {"$set": changes})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.delete("/admin/feed-items/{content_id}")
async def admin_delete_item(content_id: str, admin: User = Depends(require_admin)):
    res = await _db.feed_items.delete_one({"content_id": content_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}
