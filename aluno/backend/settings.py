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

# Mercado Pago. Só estes dois segredos + o webhook secret são usados: Client ID
# e Client Secret pertencem ao fluxo OAuth de marketplace (cobrar em nome de
# terceiros), que não é o caso aqui — a loja cobra na própria conta.
# `MERCADOPAGO_PUBLIC_KEY` é pública por natureza (vai para o navegador montar
# o Brick); o access token e o webhook secret NUNCA saem do backend.
MERCADOPAGO_ACCESS_TOKEN = _env("MERCADOPAGO_ACCESS_TOKEN")
MERCADOPAGO_PUBLIC_KEY = _env("MERCADOPAGO_PUBLIC_KEY")
MERCADOPAGO_WEBHOOK_SECRET = _env("MERCADOPAGO_WEBHOOK_SECRET")

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
        # A loja de Sparks é opcional: sem `MERCADOPAGO_ACCESS_TOKEN` ela
        # simplesmente não abre (`_require_mp_configured` devolve 503 e o
        # frontend mostra "compra indisponível"), e o resto do produto —
        # prática, redação, diagnóstico — funciona igual. Abrir o beta com
        # pagamento desligado é uma escolha legítima, então isso NÃO impede o
        # boot.
        #
        # O que impede o boot é a configuração PELA METADE. Com token e sem
        # webhook secret, o checkout cobra o cartão do aluno e a notificação de
        # confirmação é rejeitada por assinatura inválida: o dinheiro sai e os
        # Sparks nunca entram. É o pior estado possível, e é silencioso — daí
        # ser melhor não subir do que subir assim.
        if MERCADOPAGO_ACCESS_TOKEN:
            if MERCADOPAGO_ACCESS_TOKEN.startswith("TEST-"):
                problemas.append(
                    "MERCADOPAGO_ACCESS_TOKEN é credencial de teste (prefixo "
                    "TEST-) em produção — o checkout abriria, o cartão seria "
                    "'aceito' e nenhum dinheiro entraria."
                )
            if not MERCADOPAGO_WEBHOOK_SECRET:
                problemas.append(
                    "MERCADOPAGO_WEBHOOK_SECRET ausente com a loja de Sparks "
                    "LIGADA. O crédito de Sparks só acontece no webhook, e sem "
                    "o segredo toda notificação é rejeitada por assinatura "
                    "inválida: o aluno paga e nunca recebe. Crie a assinatura "
                    "secreta em Mercado Pago > Suas integrações > Webhooks e "
                    "publique com `fly secrets set MERCADOPAGO_WEBHOOK_SECRET=...`, "
                    "ou remova MERCADOPAGO_ACCESS_TOKEN para abrir o beta com a "
                    "loja desligada."
                )
            if not MERCADOPAGO_PUBLIC_KEY:
                problemas.append(
                    "MERCADOPAGO_PUBLIC_KEY ausente com a loja LIGADA — o "
                    "Checkout Brick não consegue montar no navegador."
                )
            elif MERCADOPAGO_PUBLIC_KEY.startswith("TEST-"):
                problemas.append(
                    "MERCADOPAGO_PUBLIC_KEY é credencial de teste (prefixo "
                    "TEST-) em produção — o Brick abriria em modo sandbox."
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
        # Booleano e nunca o valor: este resumo vai para o log de startup e
        # para /ready, ambos legíveis por quem tiver acesso a eles.
        "mercadopago_configurado": bool(MERCADOPAGO_ACCESS_TOKEN),
        "mercadopago_public_key_configurada": bool(MERCADOPAGO_PUBLIC_KEY),
        "mercadopago_webhook_configurado": bool(MERCADOPAGO_WEBHOOK_SECRET),
        # Qual ambiente do MP as credenciais apontam — sem revelar a credencial.
        "mercadopago_ambiente": (
            "não configurado" if not MERCADOPAGO_ACCESS_TOKEN
            else "teste" if MERCADOPAGO_ACCESS_TOKEN.startswith("TEST-")
            else "produção"
        ),
    }
