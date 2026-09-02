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

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Request, Response

import rate_limit
import settings
from models import LoginRequest, SignupRequest, User, UserSession

logger = logging.getLogger("sapiens.auth")

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
    doc = session.model_dump()
    # `expires_at` é string ISO (contrato do modelo, lido por `_resolve_user`).
    # O TTL do Mongo só age sobre um campo BSON de data e ignora string em
    # silêncio — daí este campo paralelo, escrito só para o índice
    # `sessao_ttl` (ver `db_indexes.py`). O contrato do modelo fica intacto.
    doc["expires_at_dt"] = expires_at
    await _db.user_sessions.insert_one(doc)
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
async def signup(
    payload: SignupRequest,
    response: Response,
    _: None = Depends(rate_limit.por_ip("signup")),
):
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
async def login(
    payload: LoginRequest,
    response: Response,
    _: None = Depends(rate_limit.por_ip("login")),
):
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
        campos = {"name": existente.get("name") or nome, "picture": foto,
                  "provider": "google", "is_admin": admin}

        # Sequestro de conta ANTES do cadastro (pre-hijacking): como
        # `/auth/signup` não verifica e-mail, alguém podia registrar o
        # endereço de outra pessoa com uma senha própria; quando a dona real
        # entrasse com Google, cairia NESSA conta e o atacante continuaria
        # com a senha, lendo todo o histórico e os Sparks dela.
        #
        # A verificação do Google prova quem é a dona do endereço. Uma senha
        # criada sem essa prova não pode sobreviver ao encontro: ela é
        # invalidada aqui, e voltar a ter senha exige o fluxo de recuperação
        # (`/auth/password/forgot`), que passa pelo e-mail. Uma senha definida
        # DEPOIS de a conta já estar verificada é preservada — quem provou ser
        # dona pode manter os dois caminhos abertos.
        if existente.get("password_hash") and not existente.get("email_verificado"):
            campos["password_hash"] = None
            campos["senha_invalidada_em"] = datetime.now(timezone.utc).isoformat()
            logger.warning(
                "Senha não verificada invalidada ao vincular %s ao Google "
                "(possível conta criada por terceiro antes do cadastro real).",
                user_id,
            )
            # Sessões abertas com aquela senha morrem junto: manter uma delas
            # viva deixaria o acesso do atacante de pé mesmo sem a senha.
            await _db.user_sessions.delete_many({"user_id": user_id})

        campos["email_verificado"] = True
        await _db.users.update_one({"user_id": user_id}, {"$set": campos})
    else:
        novo = User(email=email, name=nome, picture=foto, provider="google",
                    is_admin=admin, email_verificado=True)
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


# ---------------------------------------------------------------------------
# Recuperação de senha
#
# Não existia: quem entrava por e-mail/senha e esquecia a senha perdia a conta,
# com histórico e Sparks comprados dentro, e a única saída era editar o banco
# na mão. Numa base de estudantes isso é a primeira demanda de suporte.
#
# O fluxo é o padrão: token de uso único, com validade curta, guardado apenas
# como hash (um vazamento da coleção não permite redefinir a senha de
# ninguém), e resposta idêntica para e-mail existente ou não — senão a rota
# vira um oráculo que diz quem tem conta aqui.
#
# ENTREGA DO E-MAIL: este backend não tem provedor de e-mail configurado, e
# inventar um seria inventar infraestrutura. `_entregar_link_de_reset` é o
# ponto único de integração: hoje registra o link no log do servidor (o admin
# consegue destravar um aluno), e passa a enviar de verdade assim que houver
# provedor. Ver RESET_DE_SENHA.md.
# ---------------------------------------------------------------------------

PASSWORD_RESET_TTL_MINUTOS = 30


def _hash_token(token: str) -> str:
    """SHA-256 — o token tem 256 bits de entropia vinda de `secrets`, então
    não há o que uma tabela pré-computada acelere; bcrypt aqui só adicionaria
    custo por requisição sem ganho."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


async def _entregar_link_de_reset(email: str, token: str) -> None:
    """Ponto ÚNICO de entrega do link de redefinição.

    Enquanto não há provedor de e-mail, o link vai para o log em nível WARNING
    (visível em `fly logs`), o que mantém o fluxo completo e auditável sem
    fingir um envio que não acontece. Trocar por SendGrid/SES/Resend é
    substituir o corpo desta função — nada mais no fluxo muda.
    """
    base = (settings.CORS_ORIGINS or ["http://localhost:3000"])[0].rstrip("/")
    link = f"{base}/redefinir-senha?token={token}"
    logger.warning(
        "[RESET DE SENHA] Nenhum provedor de e-mail configurado. "
        "Link para %s (válido por %d min): %s",
        email, PASSWORD_RESET_TTL_MINUTOS, link,
    )


@router.post("/password/forgot")
async def solicitar_reset_de_senha(
    response: Response,
    email: str = Body(..., embed=True),
    _: None = Depends(rate_limit.por_ip("password_reset")),
):
    """Sempre devolve a mesma coisa, exista ou não a conta.

    Dizer "e-mail não encontrado" transformaria esta rota num verificador de
    quem estuda aqui — uma lista de menores de idade, para quem quisesse
    coletá-la.
    """
    resposta = {
        "ok": True,
        "mensagem": "Se houver uma conta com esse e-mail, enviamos um link para redefinir a senha.",
    }
    alvo = (email or "").strip().lower()
    if not alvo:
        return resposta

    doc = await _db.users.find_one({"email": alvo}, {"_id": 0, "user_id": 1})
    if not doc:
        return resposta

    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TTL_MINUTOS)
    # Um pedido novo invalida os anteriores: dois links válidos ao mesmo tempo
    # dobram a janela de exposição sem nenhum ganho para o aluno.
    await _db.password_resets.delete_many({"user_id": doc["user_id"]})
    await _db.password_resets.insert_one({
        "user_id": doc["user_id"],
        "token_hash": _hash_token(token),
        "expires_at": expira.isoformat(),
        "expires_at_dt": expira,   # campo BSON para o índice TTL
        "usado": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await _entregar_link_de_reset(alvo, token)
    return resposta


@router.post("/password/reset")
async def redefinir_senha(
    response: Response,
    token: str = Body(...),
    nova_senha: str = Body(..., min_length=8, max_length=200),
    _: None = Depends(rate_limit.por_ip("password_reset")),
):
    """Consome o token e troca a senha. O token morre no uso."""
    registro = await _db.password_resets.find_one({"token_hash": _hash_token(token)}, {"_id": 0})
    if not registro or registro.get("usado"):
        raise HTTPException(status_code=400, detail="Link inválido ou já utilizado.")

    expira = registro["expires_at"]
    if isinstance(expira, str):
        expira = datetime.fromisoformat(expira)
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if expira < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link expirado. Peça um novo.")

    await _db.users.update_one(
        {"user_id": registro["user_id"]},
        # Redefinir por e-mail PROVA a posse do endereço — é o mesmo nível de
        # verificação que o login com Google dá, então a conta passa a contar
        # como verificada (ver o tratamento de pre-hijacking em /auth/google).
        {"$set": {"password_hash": _hash_password(nova_senha), "email_verificado": True}},
    )
    await _db.password_resets.update_one(
        {"token_hash": _hash_token(token)}, {"$set": {"usado": True}},
    )
    # Trocar a senha derruba TODA sessão aberta: se a conta estava tomada, é
    # exatamente aqui que o acesso do invasor precisa terminar.
    await _db.user_sessions.delete_many({"user_id": registro["user_id"]})
    return {"ok": True, "mensagem": "Senha redefinida. Você já pode entrar."}


@router.post("/logout-all")
async def logout_de_todos_os_dispositivos(request: Request, response: Response):
    """Encerra todas as sessões da conta.

    `/auth/logout` apaga só o token atual — quem entrou num computador
    emprestado ou desconfia de acesso indevido não tinha como fechar as
    outras portas.
    """
    user = await require_user(request)
    resultado = await _db.user_sessions.delete_many({"user_id": user.user_id})
    response.delete_cookie(
        "session_token", path="/", domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
    )
    return {"ok": True, "sessoes_encerradas": resultado.deleted_count}


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
