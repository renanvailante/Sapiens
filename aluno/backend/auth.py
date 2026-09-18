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

from typing import Any

import bcrypt
import httpx
from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Request, Response

import rate_limit
import settings
import whatsapp as wa
from models import LoginRequest, SignupRequest, User, UserSession, generate_user_id

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


async def _is_promoter(email: str) -> bool:
    """Um promoter não tem flag própria: é ter o e-mail gravado em algum
    `promo_codes.promoter_email` (gerido pelo admin em `/admin/promo-codes`).
    Calculado a cada resposta de auth em vez de guardado no `User` porque o
    admin pode atribuir/remover um cupom a qualquer momento, e uma flag
    persistida ficaria desatualizada até o próximo re-cálculo manual."""
    return bool(await _db.promo_codes.find_one({"promoter_email": email.lower()}, {"_id": 1}))


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def _new_session_token() -> str:
    return f"tok_{uuid.uuid4().hex}{uuid.uuid4().hex}"


async def _gerar_user_id_unico(nome: str) -> str:
    """`user_id` legível (nome + poucos dígitos), com checagem de colisão.

    `generate_user_id` já reduz o espaço de colisão ao mínimo (hex[:4] após
    o nome), mas não é infinito — diferente do e-mail, `user_id` não tem
    índice único no banco vindo de fora, então a checagem é aqui.
    """
    for _ in range(5):
        candidato = generate_user_id(nome)
        if not await _db.users.find_one({"user_id": candidato}, {"_id": 1}):
            return candidato
    # Praticamente inatingível (colidir 5x seguidas em hex[:4]) — mas um
    # fallback determinístico é melhor que um 500 numa conta nova.
    return f"user_{uuid.uuid4().hex[:12]}"


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


async def _bonus_de_cadastro(promo_code: str | None) -> tuple[int, str | None, int | None]:
    """Sparks iniciais da conta nova: valor do código de promoção se um
    código ativo foi informado, senão o bônus padrão. Importado aqui dentro
    (não no topo do módulo) porque `promo_codes_routes` importa `require_admin`
    deste próprio arquivo — import no topo criaria um ciclo.

    Devolve `(sparks, codigo_aplicado, sparks_do_codigo)`. O código volta
    NORMALIZADO (maiúsculas) e só quando de fato valeu — código inexistente ou
    desativado devolve `None`, que é o que faz o cadastro registrar "sem
    cupom" em vez do texto que a pessoa digitou. Sem esses dois campos extras,
    a única memória de promoção era o contador `promo_codes.usos`: sabia-se
    quantas contas usaram um código e nunca QUAIS.
    """
    import firestore_service as fs
    import promo_codes_routes as promo_module

    aplicado = await promo_module.validar_e_registrar_uso(promo_code)
    if aplicado is None:
        return fs.SPARKS_INITIAL_BALANCE, None, None
    return aplicado["sparks_amount"], aplicado["code"], aplicado["sparks_amount"]


async def _registrar_cupom(user_id: str, code: str | None, sparks: int | None) -> None:
    """Carimba na conta o cupom que valeu no cadastro.

    Uma escrita separada, logo depois do `insert_one`, e não um campo no
    `User` construído antes: a ORDEM importa. `validar_e_registrar_uso`
    incrementa o contador de usos do código, e incrementá-lo antes de a conta
    existir faria um cadastro que falhasse (e-mail duplicado numa corrida)
    consumir um uso de cupom que ninguém recebeu.
    """
    if not code:
        return
    await _db.users.update_one(
        {"user_id": user_id}, {"$set": {"promo_code": code, "promo_sparks": sparks}}
    )


async def _registrar_indicacao(user_id: str, code: str | None) -> None:
    """Segunda leitura do MESMO campo do cadastro: se o texto digitado não era
    um cupom do catálogo, ainda pode ser o código pessoal de um aluno.

    Um campo só na tela, e não dois, porque quem recebe um código de um amigo
    não tem como saber de que tipo ele é — e um formulário que exige essa
    distinção transforma o erro de classificação da pessoa em "não funcionou".

    A ordem de resolução (cupom primeiro, indicação depois) está em
    `_bonus_de_cadastro`, que é quem já consumiu o catálogo: chegar aqui
    significa que nenhum cupom ativo casou. O vínculo não dá Spark nenhum
    agora — ele só passa a valer na primeira compra do indicado, e quem paga
    é o webhook (ver `indicacoes.creditar_primeira_compra`).

    Erro aqui nunca derruba o cadastro: a conta existe, e uma indicação
    perdida é infinitamente menos grave que um cadastro que falha.
    """
    if not code:
        return
    import indicacoes

    try:
        indicador = await indicacoes.resolver_indicador(_db, code)
        if not indicador:
            return
        await indicacoes.registrar_indicacao(
            _db,
            indicado_id=user_id,
            indicador_id=indicador["user_id"],
            codigo=indicador["referral_code"],
        )
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar indicação de %s (código %r).", user_id, code)


@router.post("/signup")
async def signup(
    payload: SignupRequest,
    response: Response,
    _: None = Depends(rate_limit.por_ip("signup")),
):
    import firestore_service as fs

    existing = await _db.users.find_one({"email": payload.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    # O número é validado ANTES de a conta existir: um cadastro que cria a
    # conta e só depois recusa o telefone deixaria o aluno com uma conta que
    # ele acha que não criou e um erro na tela.
    try:
        whatsapp_digitado, whatsapp_e164 = wa.normalizar(payload.whatsapp)
    except wa.WhatsAppInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    responsavel = _campos_do_responsavel(
        payload.menor_de_idade,
        payload.responsavel_nome,
        payload.responsavel_whatsapp,
        exigir=True,
    )
    user = User(
        user_id=await _gerar_user_id_unico(payload.name),
        email=payload.email, name=payload.name, provider="email",
        password_hash=_hash_password(payload.password),
        is_admin=_is_admin_email(payload.email),
        whatsapp=whatsapp_digitado, whatsapp_e164=whatsapp_e164,
        **responsavel,
    )
    await _db.users.insert_one(user.model_dump())
    sparks_iniciais, cupom, cupom_sparks = await _bonus_de_cadastro(payload.promo_code)
    await _registrar_cupom(user.user_id, cupom, cupom_sparks)
    if not cupom:
        await _registrar_indicacao(user.user_id, payload.promo_code)
    fs.ensure_student_profile(user.user_id, user.name, user.email, initial_sparks=sparks_iniciais)
    token = await _create_session(user.user_id)
    _set_cookie(response, token)
    return {
        "user": {"user_id": user.user_id, "email": user.email, "name": user.name,
                 "picture": user.picture, "is_admin": user.is_admin,
                 "is_promoter": await _is_promoter(user.email)},
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
                 "picture": doc.get("picture"), "is_admin": is_admin,
                 "is_promoter": await _is_promoter(doc["email"])},
        "token": token,
    }


@router.post("/google")
async def google_sign_in(
    response: Response,
    id_token: str = Body(..., embed=True),
    promo_code: str | None = Body(default=None, embed=True),
    whatsapp: str | None = Body(default=None, embed=True),
    menor_de_idade: bool = Body(default=False, embed=True),
    responsavel_nome: str | None = Body(default=None, embed=True),
    responsavel_whatsapp: str | None = Body(default=None, embed=True),
):
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
        # O WhatsApp aqui é OPCIONAL, ao contrário do cadastro por e-mail: o
        # botão do Google também cria conta a partir da tela de LOGIN, onde
        # não há formulário nenhum para preencher. Quem entrar assim é
        # convidado a informar o número depois (`POST /auth/whatsapp`) — e
        # recusar a conta neste ponto seria barrar quem já provou o e-mail.
        novo = User(
            user_id=await _gerar_user_id_unico(nome),
            email=email, name=nome, picture=foto, provider="google",
            is_admin=admin, email_verificado=True,
            **_campos_de_whatsapp(whatsapp),
            **_campos_do_responsavel(
                menor_de_idade, responsavel_nome, responsavel_whatsapp, exigir=False
            ),
        )
        await _db.users.insert_one(novo.model_dump())
        user_id = novo.user_id
        sparks_iniciais, cupom, cupom_sparks = await _bonus_de_cadastro(promo_code)
        await _registrar_cupom(user_id, cupom, cupom_sparks)
        if not cupom:
            await _registrar_indicacao(user_id, promo_code)
        fs.ensure_student_profile(user_id, nome, email, initial_sparks=sparks_iniciais)

    token = await _create_session(user_id)
    _set_cookie(response, token)
    doc = await _db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    doc["is_promoter"] = await _is_promoter(doc["email"])
    return {"user": doc, "token": token}


def _campos_do_responsavel(
    menor: bool, nome: str | None, whatsapp: str | None, *, exigir: bool
) -> dict[str, Any]:
    """Os campos do responsável legal de um aluno menor de idade.

    `exigir=True` (cadastro por e-mail) recusa o cadastro com 422 quando falta
    nome ou telefone: a declaração de ser menor SEM um responsável alcançável
    é exatamente o registro que a LGPD (art. 14) não aceita, e gravá-la assim
    seria pior do que não perguntar nada.

    `exigir=False` (login com Google, onde não há formulário) grava o que
    veio e não barra ninguém — a entrada da pessoa não pode depender de um
    campo que a tela daquele caminho nem sempre mostra.

    Quem declara ser maior nunca recebe campo de responsável, mesmo que a
    requisição traga um: seria guardar dado de terceiro sem finalidade.
    """
    if not menor:
        return {"menor_de_idade": False}
    nome = (nome or "").strip()
    bruto = (whatsapp or "").strip()
    if exigir and (not nome or not bruto):
        raise HTTPException(
            status_code=422,
            detail="Quem tem menos de 18 anos precisa informar o nome e o WhatsApp do responsável.",
        )
    campos: dict[str, Any] = {"menor_de_idade": True}
    if nome:
        campos["responsavel_nome"] = nome
    if bruto:
        try:
            digitado, e164 = wa.normalizar(bruto)
        except wa.WhatsAppInvalido as exc:
            if exigir:
                raise HTTPException(
                    status_code=422, detail=f"WhatsApp do responsável: {exc}"
                ) from exc
            logger.info("WhatsApp do responsável inválido ignorado no login com Google.")
            return campos
        campos["responsavel_whatsapp"] = digitado
        campos["responsavel_whatsapp_e164"] = e164
    return campos


def _campos_de_whatsapp(bruto: str | None) -> dict[str, str]:
    """`{}` quando não veio número; os dois campos quando veio um válido.

    Um número inválido no login com Google é IGNORADO em vez de derrubar a
    entrada: o campo é opcional nesse caminho, e recusar a autenticação por
    causa de um telefone mal digitado trocaria um dado que falta por uma
    pessoa que não consegue entrar.
    """
    if not bruto:
        return {}
    try:
        digitado, e164 = wa.normalizar(bruto)
    except wa.WhatsAppInvalido:
        logger.info("WhatsApp inválido ignorado no login com Google.")
        return {}
    return {"whatsapp": digitado, "whatsapp_e164": e164}


@router.post("/whatsapp")
async def definir_whatsapp(
    request: Request,
    whatsapp: str = Body(..., embed=True),
    menor_de_idade: bool | None = Body(default=None, embed=True),
    responsavel_nome: str | None = Body(default=None, embed=True),
    responsavel_whatsapp: str | None = Body(default=None, embed=True),
):
    """Completa o cadastro de quem entrou sem preencher formulário.

    **Quem cai aqui:** quem criou a conta pelo botão do Google a partir da aba
    de LOGIN (onde não existe formulário nenhum) e as contas anteriores a
    2026-09-15, quando o campo não existia. Para essas duas, esta é a ÚNICA
    porta pela qual o telefone entra — e sem telefone a equipe não alcança o
    aluno por canal nenhum.

    Aceita os mesmos campos do cadastro por e-mail (2026-09-17): o WhatsApp e,
    para quem se declara menor de idade, o responsável. Uma chamada só, porque
    é uma tela só — ver `pages/CompletarCadastro.jsx`.

    `menor_de_idade=None` significa "não perguntei nesta chamada" e deixa os
    campos como estão; `False` limpa o responsável, porque quem se declarou
    maior não pode continuar com o telefone de um terceiro guardado.
    """
    user = await require_user(request)
    try:
        digitado, e164 = wa.normalizar(whatsapp)
    except wa.WhatsAppInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    campos: dict[str, Any] = {"whatsapp": digitado, "whatsapp_e164": e164}
    if menor_de_idade is not None:
        campos.update(
            _campos_do_responsavel(
                menor_de_idade, responsavel_nome, responsavel_whatsapp, exigir=True,
            )
        )
        if not menor_de_idade:
            campos.update({
                "responsavel_nome": None,
                "responsavel_whatsapp": None,
                "responsavel_whatsapp_e164": None,
            })
    await _db.users.update_one({"user_id": user.user_id}, {"$set": campos})
    return {"ok": True, "whatsapp": digitado}


@router.get("/me")
async def me(request: Request):
    user = await _resolve_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    doc = user.model_dump(exclude={"password_hash"})
    doc["is_promoter"] = await _is_promoter(user.email)
    return doc


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
# ENTREGA DO E-MAIL: `_entregar_link_de_reset` é o ponto único de integração.
# Com `RESEND_API_KEY` + `RESEND_FROM` configurados, envia de verdade; sem
# eles, registra o link no log (o admin ainda consegue destravar um aluno à
# mão). Ver RESET_DE_SENHA.md.
# ---------------------------------------------------------------------------

PASSWORD_RESET_TTL_MINUTOS = 30


def _hash_token(token: str) -> str:
    """SHA-256 — o token tem 256 bits de entropia vinda de `secrets`, então
    não há o que uma tabela pré-computada acelere; bcrypt aqui só adicionaria
    custo por requisição sem ganho."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


_RESEND_URL = "https://api.resend.com/emails"
_TIMEOUT_EMAIL_SEGUNDOS = 10.0


def _corpo_do_email(link: str) -> str:
    """HTML do e-mail. Nada aqui vem do usuário: o único valor interpolado é um
    link que nós mesmos montamos, com um token hexadecimal."""
    return (
        f'<p>Recebemos um pedido para criar uma senha nova no Sapiens.</p>'
        f'<p><a href="{link}">Clique aqui para redefinir sua senha</a>. '
        f'O link vale por {PASSWORD_RESET_TTL_MINUTOS} minutos e só pode ser usado uma vez.</p>'
        f'<p>Se não foi você que pediu, ignore este e-mail — sua senha atual continua valendo.</p>'
    )


async def _entregar_link_de_reset(email: str, token: str) -> None:
    """Ponto ÚNICO de entrega do link de redefinição.

    **Nunca propaga erro.** Quem chama é `/password/forgot`, cuja resposta tem
    de ser idêntica exista ou não a conta — senão a rota vira um verificador de
    quem estuda aqui, isto é, uma lista de menores de idade para quem quisesse
    coletá-la. Uma exceção escapando daqui viraria um 500 só para e-mails
    cadastrados, que é exatamente o oráculo que o resto do fluxo evita. Por
    isso o `except` largo: o aluno vê a mesma resposta, e a falha fica no log.

    Sem provedor configurado, o link vai para o log em nível WARNING (visível
    em `fly logs`), o que mantém o fluxo completo e auditável sem fingir um
    envio que não acontece.
    """
    link = f"{settings.frontend_base()}/redefinir-senha?token={token}"

    if not settings.EMAIL_HABILITADO:
        logger.warning(
            "[RESET DE SENHA] Nenhum provedor de e-mail configurado "
            "(RESEND_API_KEY + RESEND_FROM). Link para %s (válido por %d min): %s",
            email, PASSWORD_RESET_TTL_MINUTOS, link,
        )
        return

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_EMAIL_SEGUNDOS) as cliente:
            resposta = await cliente.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={
                    "from": settings.RESEND_FROM,
                    "to": [email],
                    "subject": "Redefinir sua senha do Sapiens",
                    "html": _corpo_do_email(link),
                },
            )
        resposta.raise_for_status()
        logger.info("[RESET DE SENHA] Link enviado para %s.", email)
    except Exception:  # noqa: BLE001
        # O link vai para o log para que o aluno ainda possa ser destravado à
        # mão — o mesmo caminho de quando não há provedor nenhum.
        logger.exception(
            "[RESET DE SENHA] ENVIO FALHOU para %s. Link (válido por %d min): %s",
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
