"""Configuração e validação de ambiente — app `professor`.

Falha no boot com mensagem acionável. Além dos defaults inseguros comuns aos
três apps, este tinha dois problemas próprios:

* ``allowed_origins`` incluía ``http://localhost:3000`` **fixo no código**, sem
  condição de ambiente: a origem de desenvolvimento ia junto para produção.
* ``ADMIN_PASSWORD`` semeava um administrador a cada boot sem exigir nada da
  senha — e o valor usado em desenvolvimento era ``admin123``.
"""
from __future__ import annotations

import os
import sys


def _env(nome: str, default: str | None = None) -> str | None:
    v = os.environ.get(nome)
    if v is None:
        return default
    v = v.strip()
    return v or default


def _flag(nome: str, default: bool = False) -> bool:
    v = _env(nome)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}


def _lista(nome: str) -> list[str]:
    v = _env(nome)
    return [x.strip() for x in v.split(",") if x.strip()] if v else []


APP_ENV = (_env("APP_ENV", "development") or "development").lower()
IS_PRODUCTION = APP_ENV == "production"

MONGO_URL = _env("MONGO_URL")
DB_NAME = _env("DB_NAME")
JWT_SECRET = _env("JWT_SECRET")
FRONTEND_URL = _env("FRONTEND_URL")
CORS_ORIGINS = _lista("CORS_ORIGINS") or ([FRONTEND_URL] if FRONTEND_URL else [])

ADMIN_EMAIL = _env("ADMIN_EMAIL")
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")

SEED_DEMO_DATA = _flag("SEED_DEMO_DATA", default=not IS_PRODUCTION)
LOG_LEVEL = (_env("LOG_LEVEL", "INFO") or "INFO").upper()

COOKIE_SECURE = _flag("COOKIE_SECURE", default=IS_PRODUCTION)
COOKIE_SAMESITE = (_env("COOKIE_SAMESITE", "none" if IS_PRODUCTION else "lax") or "lax").lower()
COOKIE_DOMAIN = _env("COOKIE_DOMAIN")

_SENHAS_DE_EXEMPLO = {"admin123", "admin", "senha", "password", "123456", "changeme"}


class ConfigError(RuntimeError):
    """Configuração ausente ou inválida — o processo não deve subir."""


def validar() -> list[str]:
    problemas: list[str] = []

    if not MONGO_URL:
        problemas.append("MONGO_URL ausente.")
    if not DB_NAME:
        problemas.append("DB_NAME ausente.")
    if not JWT_SECRET:
        problemas.append(
            "JWT_SECRET ausente — é o segredo que assina os tokens de acesso "
            "do professor."
        )

    if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
        problemas.append(f"COOKIE_SAMESITE={COOKIE_SAMESITE!r} inválido. Use lax, strict ou none.")
    if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
        problemas.append("COOKIE_SAMESITE=none exige COOKIE_SECURE=true.")

    if IS_PRODUCTION:
        if JWT_SECRET and len(JWT_SECRET) < 32:
            problemas.append(
                f"JWT_SECRET tem {len(JWT_SECRET)} caracteres; em produção use ao "
                "menos 32 (ex.: `python3 -c \"import secrets;print(secrets.token_hex(32))\"`). "
                "Um segredo curto é adivinhável e permite forjar token de admin."
            )
        if not CORS_ORIGINS:
            problemas.append("CORS_ORIGINS (ou FRONTEND_URL) ausente em produção.")
        if "*" in CORS_ORIGINS:
            problemas.append("CORS_ORIGINS contém '*', incompatível com credenciais.")
        for origem in CORS_ORIGINS:
            if origem.startswith("http://") and "localhost" not in origem and "127.0.0.1" not in origem:
                problemas.append(f"CORS_ORIGINS contém origem sem TLS em produção: {origem}")
        if not COOKIE_SECURE:
            problemas.append("COOKIE_SECURE=false em produção — os tokens trafegariam em claro.")
        if ADMIN_PASSWORD and ADMIN_PASSWORD.lower() in _SENHAS_DE_EXEMPLO:
            problemas.append(
                "ADMIN_PASSWORD é uma senha de exemplo. Ela semearia um "
                "administrador com credencial pública no banco de produção."
            )
        if ADMIN_PASSWORD and len(ADMIN_PASSWORD) < 12:
            problemas.append(
                f"ADMIN_PASSWORD tem {len(ADMIN_PASSWORD)} caracteres; use ao menos 12 em produção."
            )
        if SEED_DEMO_DATA:
            problemas.append(
                "SEED_DEMO_DATA está ligado em produção — inseriria as turmas e "
                "os alunos fictícios de demonstração no banco real."
            )

    return problemas


def exigir_config_valida() -> None:
    problemas = validar()
    if not problemas:
        return
    cabecalho = f"Configuração inválida para APP_ENV={APP_ENV!r}:"
    corpo = "\n".join(f"  - {p}" for p in problemas)
    print(f"\n{cabecalho}\n{corpo}\n", file=sys.stderr)
    raise ConfigError(f"{cabecalho}\n{corpo}")


def resumo() -> dict:
    """Estado da configuração, sem revelar segredo algum."""
    return {
        "app_env": APP_ENV,
        "db_name": DB_NAME,
        "cors_origins": CORS_ORIGINS or ["<não definido>"],
        "cookie": {"secure": COOKIE_SECURE, "samesite": COOKIE_SAMESITE, "domain": COOKIE_DOMAIN},
        "seed_demo_data": SEED_DEMO_DATA,
        "admin_seed_configurado": bool(ADMIN_EMAIL and ADMIN_PASSWORD),
    }
