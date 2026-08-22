"""Rotas de autenticação do Sapiens — e-mail/senha com sessão em cookie.

Papel de admin é semeado por `ADMIN_EMAILS` (separado por vírgula): todo
signup/login reconcilia a flag `is_admin` contra essa lista, então promover
alguém é acrescentar o e-mail e pedir que entre de novo. Admins também podem
alternar a flag de outros via /admin/users.

**Login com Google, 2026-08-22.** O fluxo antigo dependia da infraestrutura da
Emergent (`auth.emergentagent.com` para o redirect, `demobackend...` para trocar
o `session_id`) e foi removido com ela. A reimplementação usa **Firebase
Authentication**, com a mesma credencial de serviço que o projeto já usa para o
Firestore — nenhum fornecedor novo.

A troca é deliberadamente estreita: o Firebase autentica e devolve um ID token;
`/auth/google` verifica esse token e emite **a mesma sessão** do fluxo de
e-mail/senha. Não há segunda noção de sessão, segundo formato de usuário nem
segundo caminho de autorização — `require_user` continua sendo o único portão, e
quem entrou por Google é indistinguível de quem entrou por senha daí em diante.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Body, Cookie, HTTPException, Request, Response

import settings
from models import LoginRequest, SignupRequest, User, UserSession

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_TTL_DAYS = settings.SESSION_TTL_DAYS


_db = None
def set_db(db):
    global _db
    _db = db


def _admin_emails() -> set[str]:
    return {e.lower() for e in settings.ADMIN_EMAILS}


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
    """Emite o cookie de sessao com a politica adequada ao ambiente.

    `Secure` + `SameSite=None` e obrigatorio quando frontend e backend estao em
    dominios diferentes sobre HTTPS. Em desenvolvimento sobre http://localhost o
    navegador DESCARTA esse cookie em silencio — o login parece funcionar e a
    sessao nao persiste. Por isso a politica vem da configuracao.
    """
    response.set_cookie(
        key="session_token", value=token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
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


@router.post("/google")
async def google_sign_in(response: Response, id_token: str = Body(..., embed=True)):
    """Troca um ID token do Firebase pela sessão do Sapiens.

    O token é verificado com a credencial de serviço do projeto: assinatura,
    expiração, emissor e audiência. Um token forjado ou de outro projeto é
    recusado pelo próprio SDK — nunca confiamos no e-mail que o cliente afirma.

    O casamento com uma conta existente é por **e-mail verificado**. Sem essa
    condição, alguém poderia registrar `vitima@exemplo.com` num provedor que não
    verifica e-mail e assumir a conta de senha correspondente.
    """
    from firebase_admin import auth as fb_auth

    import firestore_service as fs

    try:
        fs.get_firestore()  # garante que o app do firebase_admin foi inicializado
        claims = fb_auth.verify_id_token(id_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=f"Token do Firebase inválido: {type(exc).__name__}")

    email = (claims.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Token sem e-mail.")
    if not claims.get("email_verified"):
        raise HTTPException(
            status_code=401,
            detail="E-mail não verificado pelo provedor — não é possível vincular a conta.",
        )

    nome = claims.get("name") or email.split("@")[0]
    foto = claims.get("picture")
    admin = _is_admin_email(email)

    existente = await _db.users.find_one({"email": email}, {"_id": 0})
    if existente:
        user_id = existente["user_id"]
        # `provider` passa a "google" para refletir a última via de entrada; a
        # senha existente é PRESERVADA, para que os dois caminhos continuem
        # abertos para a mesma pessoa.
        await _db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": existente.get("name") or nome, "picture": foto,
                      "provider": "google", "is_admin": admin}},
        )
    else:
        novo = User(email=email, name=nome, picture=foto, provider="google", is_admin=admin)
        await _db.users.insert_one(novo.model_dump())
        user_id = novo.user_id

    token = await _create_session(user_id)
    _set_cookie(response, token)
    doc = await _db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return {"user": doc, "token": token}


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
    # os mesmos atributos do set_cookie, senao o navegador nao casa o cookie
    # a ser removido e a sessao continua valida no cliente
    response.delete_cookie(
        "session_token", path="/", domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
    )
    return {"ok": True}
