"""Authentication routes for Sapiens: JWT email/password + Emergent Google Auth.

Admin role is bootstrapped via env var `ADMIN_EMAILS` (comma-separated) — every
signup/login/Emergent-session flow reconciles the `is_admin` flag against that
list, so promoting a user is as simple as adding their email and having them
sign in again. Admins can also toggle other users' admin flag via /admin/users.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi import Header

from models import LoginRequest, SignupRequest, User, UserSession

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_TTL_DAYS = 7
EMERGENT_SESSION_ENDPOINT = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


_db = None
def set_db(db):
    global _db
    _db = db


def _admin_emails() -> set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _is_admin_email(email: str) -> bool:
    return email.lower() in _admin_emails()


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def _new_session_token() -> str:
    return f"tok_{uuid.uuid4().hex}{uuid.uuid4().hex}"


async def _create_session(user_id: str) -> str:
    token = _new_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    session = UserSession(user_id=user_id, session_token=token, expires_at=expires_at.isoformat())
    await _db.user_sessions.insert_one(session.model_dump())
    return token


def _set_cookie(response: Response, token: str):
    response.set_cookie(
        key="session_token", value=token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True, secure=True, samesite="none", path="/",
    )


async def _reconcile_admin(email: str, user_id: str) -> bool:
    """If the ADMIN_EMAILS env changed, keep the DB in sync on next login."""
    want = _is_admin_email(email)
    await _db.users.update_one({"user_id": user_id}, {"$set": {"is_admin": want}})
    return want


async def _resolve_user(request: Request) -> User | None:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    session = await _db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        return None
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    user_doc = await _db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user_doc:
        return None
    return User(**user_doc)


async def require_user(request: Request) -> User:
    user = await _resolve_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_admin(request: Request) -> User:
    user = await require_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/signup")
async def signup(payload: SignupRequest, response: Response):
    existing = await _db.users.find_one({"email": payload.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email, name=payload.name, provider="email",
        password_hash=_hash_password(payload.password),
        is_admin=_is_admin_email(payload.email),
    )
    await _db.users.insert_one(user.model_dump())
    token = await _create_session(user.user_id)
    _set_cookie(response, token)
    return {
        "user": {"user_id": user.user_id, "email": user.email, "name": user.name,
                 "picture": user.picture, "is_admin": user.is_admin},
        "token": token,
    }


@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    doc = await _db.users.find_one({"email": payload.email}, {"_id": 0})
    if not doc or not doc.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not _check_password(payload.password, doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    is_admin = await _reconcile_admin(doc["email"], doc["user_id"])
    token = await _create_session(doc["user_id"])
    _set_cookie(response, token)
    return {
        "user": {"user_id": doc["user_id"], "email": doc["email"], "name": doc["name"],
                 "picture": doc.get("picture"), "is_admin": is_admin},
        "token": token,
    }


@router.post("/emergent/session")
async def emergent_session(response: Response, x_session_id: str = Header(..., alias="X-Session-ID")):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(EMERGENT_SESSION_ENDPOINT, headers={"X-Session-ID": x_session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Emergent session")
    data = r.json()
    email = data["email"]
    existing = await _db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await _db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data.get("name") or existing["name"],
                      "picture": data.get("picture"),
                      "provider": "google",
                      "is_admin": _is_admin_email(email)}},
        )
    else:
        user = User(email=email, name=data.get("name") or email.split("@")[0],
                    picture=data.get("picture"), provider="google",
                    is_admin=_is_admin_email(email))
        await _db.users.insert_one(user.model_dump())
        user_id = user.user_id

    session_token = data.get("session_token") or _new_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    await _db.user_sessions.insert_one(
        UserSession(user_id=user_id, session_token=session_token, expires_at=expires_at.isoformat()).model_dump()
    )
    _set_cookie(response, session_token)
    user_doc = await _db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return {"user": user_doc, "token": session_token}


@router.get("/me")
async def me(request: Request):
    user = await _resolve_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user.model_dump(exclude={"password_hash"})


@router.post("/logout")
async def logout(response: Response, session_token: str | None = Cookie(default=None)):
    if session_token:
        await _db.user_sessions.delete_many({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}



def _admin_emails():
    raw = os.environ.get("ADMIN_EMAILS", "")
    print("ADMIN_EMAILS =", raw)
    return {e.strip().lower() for e in raw.split(",") if e.strip()}