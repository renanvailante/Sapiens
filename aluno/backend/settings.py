"""Configuração e validação de ambiente — app `aluno`.

Falha no boot com mensagem acionável em vez de falhar na primeira requisição.
Ver `pipeline/backend/settings.py` para a motivação; os defaults inseguros
corrigidos aqui são os mesmos, mais um específico deste app:

* ``CORS_ORIGINS`` caía em ``"*"`` junto com ``allow_credentials=True``.
* Cookie de sessão era emitido com ``secure=True; samesite=none`` fixo. Isso é
  o correto em produção cross-site sobre HTTPS, mas o navegador **descarta**
  esse cookie em ``http://localhost``, o que quebrava o login em
  desenvolvimento e levava a "consertos" que enfraqueceriam a produção.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent

# `server.py` também chama isto — repetido aqui para que `settings` fique
# correto por si só, não importa quem o importe primeiro. Sem isto, um
# módulo que importa `settings` (via `firestore_service`, `admin_routes` etc.)
# antes de `server.py` ter rodado lê `os.environ` cru, sem o `.env`, e
# `MONGO_URL`/`DB_NAME` ficam ausentes — silenciosamente, porque
# `load_dotenv()` não sobrescreve o que já está em `os.environ`, então uma
# chamada posterior de `server.py` não conserta o que já foi lido. Isso
# derrubava `test_provas_agrupamento.py` (que importa `server` normalmente)
# sempre que `pytest-xdist --dist loadscope` o agrupava, no mesmo worker, com
# `test_contratos_aluno.py` (que importa `firestore_service` direto, sem
# passar por `server.py`) — falha de ordem de import, não do teste em si.
load_dotenv(ROOT_DIR / ".env")


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
CORS_ORIGINS = _lista("CORS_ORIGINS")
GEMINI_API_KEY = _env("GEMINI_API_KEY")
ADMIN_EMAILS = _lista("ADMIN_EMAILS")

GOOGLE_CREDENTIALS = _env("FIREBASE_SERVICE_ACCOUNT_PATH") or _env("GOOGLE_APPLICATION_CREDENTIALS")
FIREBASE_SERVICE_ACCOUNT_JSON = _env("FIREBASE_SERVICE_ACCOUNT_JSON")
FIREBASE_PROJECT_ID = _env("FIREBASE_PROJECT_ID")

SEED_DEMO_DATA = _flag("SEED_DEMO_DATA", default=not IS_PRODUCTION)
LOG_LEVEL = (_env("LOG_LEVEL", "INFO") or "INFO").upper()

# Cookie de sessão. Em produção cross-site (frontend e backend em domínios
# diferentes) o par obrigatório é Secure + SameSite=None. Em desenvolvimento
# sobre http://localhost, SameSite=Lax sem Secure é o que o navegador aceita.
COOKIE_SECURE = _flag("COOKIE_SECURE", default=IS_PRODUCTION)
COOKIE_SAMESITE = (_env("COOKIE_SAMESITE", "none" if IS_PRODUCTION else "lax") or "lax").lower()
COOKIE_DOMAIN = _env("COOKIE_DOMAIN")  # opcional: compartilhar cookie entre subdomínios
SESSION_TTL_DAYS = int(_env("SESSION_TTL_DAYS", "7") or 7)

MAX_UPLOAD_MB = int(_env("MAX_UPLOAD_MB", "10") or 10)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Figuras de questão: o aluno nunca acessa o storage binário do pipeline
# diretamente (decisão documentada em requirements.txt — "os artefatos
# binários são do pipeline, que permanece privado"). `/api/exam-images/{id}`
# busca os bytes servidor-a-servidor via `PIPELINE_URL` + `PIPELINE_API_KEY`
# (mesmo par que já protege `pipeline/backend`'s `/api/*`). Opcional: sem
# isso configurado, o endpoint responde 503 em vez de derrubar o boot — a
# entrega de imagens é um extra sobre o fluxo de prova, não um requisito dele.
PIPELINE_URL = _env("PIPELINE_URL")
PIPELINE_API_KEY = _env("PIPELINE_API_KEY")

# Mercado Pago — loja de Sparks (compra avulsa + recarga automática por
# assinatura/calendário). Sem isto configurado, /api/sparks/* responde 503 em
# vez de derrubar o boot, mesmo padrão de PIPELINE_URL logo acima.
MERCADOPAGO_ACCESS_TOKEN = _env("MERCADOPAGO_ACCESS_TOKEN")
MERCADOPAGO_PUBLIC_KEY = _env("MERCADOPAGO_PUBLIC_KEY")
# Gerado pelo painel do Mercado Pago ao cadastrar a URL de notificação
# (Webhooks > Configurar notificações) — não é o mesmo par de ACCESS_TOKEN/
# PUBLIC_KEY, só existe depois de a URL do webhook estar cadastrada lá.
MERCADOPAGO_WEBHOOK_SECRET = _env("MERCADOPAGO_WEBHOOK_SECRET")


class ConfigError(RuntimeError):
    """Configuração ausente ou inválida — o processo não deve subir."""


def validar() -> list[str]:
    problemas: list[str] = []

    if not MONGO_URL:
        problemas.append("MONGO_URL ausente.")
    if not DB_NAME:
        problemas.append("DB_NAME ausente.")

    if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
        problemas.append(f"COOKIE_SAMESITE={COOKIE_SAMESITE!r} inválido. Use lax, strict ou none.")
    if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
        problemas.append(
            "COOKIE_SAMESITE=none exige COOKIE_SECURE=true — o navegador "
            "descarta o cookie caso contrário, e o login simplesmente não "
            "persiste, sem erro visível."
        )

    if IS_PRODUCTION:
        if not CORS_ORIGINS:
            problemas.append(
                "CORS_ORIGINS ausente em produção. Liste as origens exatas do "
                "frontend (ex.: https://aluno.exemplo.app)."
            )
        if "*" in CORS_ORIGINS:
            problemas.append(
                "CORS_ORIGINS contém '*'. Curinga é incompatível com credenciais "
                "e permitiria que qualquer site lesse respostas autenticadas."
            )
        for origem in CORS_ORIGINS:
            if origem.startswith("http://") and "localhost" not in origem and "127.0.0.1" not in origem:
                problemas.append(f"CORS_ORIGINS contém origem sem TLS em produção: {origem}")

        if not COOKIE_SECURE:
            problemas.append("COOKIE_SECURE=false em produção — o cookie de sessão trafegaria em claro.")
        if not (GOOGLE_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_JSON):
            problemas.append(
                "Credencial do Firebase ausente. O app do aluno grava os eventos "
                "de behavior no Firestore; sem ela nenhuma resposta é registrada."
            )
        if not GEMINI_API_KEY:
            problemas.append(
                "GEMINI_API_KEY ausente — sem ela o OCR do cartão-resposta e o "
                "diagnóstico do simulado não funcionam."
            )
        if SEED_DEMO_DATA:
            problemas.append(
                "SEED_DEMO_DATA está ligado em produção — inseriria conteúdo de "
                "demonstração no feed e gabaritos de exemplo no banco real."
            )
        if not ADMIN_EMAILS:
            problemas.append(
                "ADMIN_EMAILS ausente em produção — ninguém conseguiria acessar "
                "as telas administrativas."
            )
        if bool(PIPELINE_URL) != bool(PIPELINE_API_KEY):
            problemas.append(
                "PIPELINE_URL e PIPELINE_API_KEY devem ser configurados juntos "
                "ou nenhum dos dois — só um dos dois presente deixa "
                "/api/exam-images sempre respondendo 503."
            )
        if not MERCADOPAGO_ACCESS_TOKEN:
            problemas.append(
                "MERCADOPAGO_ACCESS_TOKEN ausente em produção — a loja de "
                "Sparks não consegue criar pagamento nem assinatura nenhuma."
            )
        if not MERCADOPAGO_WEBHOOK_SECRET:
            problemas.append(
                "MERCADOPAGO_WEBHOOK_SECRET ausente em produção — sem ele "
                "/api/sparks/webhook não tem como validar que a notificação "
                "veio mesmo do Mercado Pago, e Sparks nunca seriam creditados."
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
        "gemini_configurado": bool(GEMINI_API_KEY),
        "firebase_configurado": bool(GOOGLE_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_JSON),
        "admins_declarados": len(ADMIN_EMAILS),
        "pipeline_imagens_configurado": bool(PIPELINE_URL and PIPELINE_API_KEY),
        "mercadopago_configurado": bool(MERCADOPAGO_ACCESS_TOKEN and MERCADOPAGO_WEBHOOK_SECRET),
    }
