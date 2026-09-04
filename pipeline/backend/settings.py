"""Configuração e validação de ambiente — app `pipeline`.

Um único ponto onde o processo decide se pode subir. A regra é **falhar no
boot, com mensagem que diz o que fazer**, em vez de falhar na primeira
requisição com `KeyError` ou, pior, subir com um default inseguro.

Três defaults deste projeto eram inseguros e foram removidos:

* ``CORS_ORIGINS`` caía em ``"*"``. Combinado com ``allow_credentials=True``
  isso é rejeitado pelo próprio navegador e, onde não é, permite que qualquer
  site leia respostas autenticadas.
* ``STORAGE_MODE`` caía em ``local``. Em PaaS de container o disco é efêmero:
  o PDF original desaparece no primeiro redeploy e `regenerate` passa a falhar
  para todo item já criado.
* Seeds de demonstração rodavam a cada boot, sem condição.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


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
PIPELINE_API_KEY = _env("PIPELINE_API_KEY")
GEMINI_API_KEY = _env("GEMINI_API_KEY")
CORS_ORIGINS = _lista("CORS_ORIGINS")

STORAGE_MODE = (_env("STORAGE_MODE", "local") or "local").lower()
FIREBASE_STORAGE_BUCKET = _env("FIREBASE_STORAGE_BUCKET")
FIRESTORE_MODE = (_env("FIRESTORE_MODE", "mock") or "mock").lower()
GOOGLE_CREDENTIALS = _env("GOOGLE_APPLICATION_CREDENTIALS") or _env("FIREBASE_SERVICE_ACCOUNT_PATH")
FIREBASE_SERVICE_ACCOUNT_JSON = _env("FIREBASE_SERVICE_ACCOUNT_JSON")

SEED_DEMO_DATA = _flag("SEED_DEMO_DATA", default=not IS_PRODUCTION)
LOG_LEVEL = (_env("LOG_LEVEL", "INFO") or "INFO").upper()

# Limites de upload. FastAPI/Starlette não impõem teto por padrão: sem isto,
# um POST de 2 GB é lido inteiro para a memória do processo.
MAX_UPLOAD_MB = int(_env("MAX_UPLOAD_MB", "25") or 25)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_FILES_POR_REQUISICAO = int(_env("MAX_FILES_POR_REQUISICAO", "20") or 20)


class ConfigError(RuntimeError):
    """Configuração ausente ou inválida — o processo não deve subir."""


def validar() -> list[str]:
    """Devolve a lista de problemas. Vazia = pode subir."""
    problemas: list[str] = []

    if not MONGO_URL:
        problemas.append("MONGO_URL ausente — banco operacional do pipeline.")
    if not DB_NAME:
        problemas.append("DB_NAME ausente.")

    if not PIPELINE_API_KEY:
        problemas.append(
            "PIPELINE_API_KEY ausente — é o segredo que protege TODAS as rotas "
            "do pipeline. Sem ele o serviço responde 503 a tudo."
        )
    elif IS_PRODUCTION and len(PIPELINE_API_KEY) < 32:
        problemas.append(
            f"PIPELINE_API_KEY tem {len(PIPELINE_API_KEY)} caracteres; em produção "
            "use ao menos 32 (ex.: `python3 -c \"import secrets;print(secrets.token_hex(32))\"`)."
        )

    if not GEMINI_API_KEY:
        problemas.append(
            "GEMINI_API_KEY ausente — sem ela a anotação cognitiva, o manifesto "
            "de caderno e a importação de ontologia por PDF não funcionam."
        )

    if IS_PRODUCTION:
        if not CORS_ORIGINS:
            problemas.append(
                "CORS_ORIGINS ausente em produção. Liste as origens exatas do "
                "frontend, separadas por vírgula (ex.: https://pipeline.exemplo.app)."
            )
        if "*" in CORS_ORIGINS:
            problemas.append(
                "CORS_ORIGINS contém '*'. Curinga é incompatível com credenciais "
                "e permitiria que qualquer site lesse respostas autenticadas."
            )
        for origem in CORS_ORIGINS:
            if origem.startswith("http://") and "localhost" not in origem and "127.0.0.1" not in origem:
                problemas.append(f"CORS_ORIGINS contém origem sem TLS em produção: {origem}")

        if STORAGE_MODE == "local":
            problemas.append(
                "STORAGE_MODE=local em produção. O disco de um container é "
                "efêmero: os PDFs originais somem no primeiro redeploy e a "
                "regeneração de qualquer item passa a falhar. Use "
                "STORAGE_MODE=firebase e defina FIREBASE_STORAGE_BUCKET."
            )
        if STORAGE_MODE == "firebase" and not FIREBASE_STORAGE_BUCKET:
            problemas.append("STORAGE_MODE=firebase exige FIREBASE_STORAGE_BUCKET.")
        if STORAGE_MODE == "firebase" and not (GOOGLE_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_JSON):
            problemas.append(
                "STORAGE_MODE=firebase exige GOOGLE_APPLICATION_CREDENTIALS "
                "(caminho) ou FIREBASE_SERVICE_ACCOUNT_JSON (conteúdo)."
            )
        if FIRESTORE_MODE != "admin":
            problemas.append(
                f"FIRESTORE_MODE={FIRESTORE_MODE!r} em produção. O modo 'mock' guarda "
                "o espelho em memória: o app do aluno nunca veria os itens."
            )
        if SEED_DEMO_DATA:
            problemas.append(
                "SEED_DEMO_DATA está ligado em produção — inseriria dados de "
                "demonstração no banco real."
            )

    if STORAGE_MODE not in {"local", "firebase"}:
        problemas.append(f"STORAGE_MODE={STORAGE_MODE!r} inválido. Use 'local' ou 'firebase'.")

    return problemas


def exigir_config_valida() -> None:
    """Aborta o processo se a configuração não permitir operação correta."""
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
        "storage_mode": STORAGE_MODE,
        "firestore_mode": FIRESTORE_MODE,
        "seed_demo_data": SEED_DEMO_DATA,
        "max_upload_mb": MAX_UPLOAD_MB,
        "gemini_configurado": bool(GEMINI_API_KEY),
        "api_key_configurada": bool(PIPELINE_API_KEY),
    }
