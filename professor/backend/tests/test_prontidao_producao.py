"""Prontidão para produção — app `professor`.

Foco no que é específico deste app: força do `JWT_SECRET`, a semente de
administrador e a origem de desenvolvimento que estava fixa no código.
Rodam offline.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

_BASE_PROD = {
    "APP_ENV": "production",
    "MONGO_URL": "mongodb://db:27017",
    "DB_NAME": "sapiens_professor",
    "JWT_SECRET": "s" * 64,
    "FRONTEND_URL": "https://professor.exemplo.app",
    "ADMIN_EMAIL": "admin@exemplo.app",
    "ADMIN_PASSWORD": "senha-longa-o-suficiente",
    "SEED_DEMO_DATA": "false",
    "COOKIE_SECURE": "true",
    "COOKIE_SAMESITE": "none",
}


def _settings(monkeypatch, **over):
    env = {**_BASE_PROD, **over}
    for k in list(_BASE_PROD) + list(over) + ["CORS_ORIGINS"]:
        v = env.get(k)
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    import settings as s

    return importlib.reload(s)


def _problemas(monkeypatch, **over) -> str:
    return " | ".join(_settings(monkeypatch, **over).validar())


def test_configuracao_completa_de_producao_e_aceita(monkeypatch):
    assert _settings(monkeypatch).validar() == []


def test_desenvolvimento_nao_exige_nada_de_producao(monkeypatch):
    s = _settings(monkeypatch, APP_ENV="development", JWT_SECRET="curto",
                  FRONTEND_URL=None, ADMIN_PASSWORD="admin123",
                  COOKIE_SECURE=None, COOKIE_SAMESITE=None, SEED_DEMO_DATA=None)
    assert s.validar() == []


# ------------------------------------------------------------------ JWT
def test_jwt_secret_ausente_e_recusado(monkeypatch):
    assert "JWT_SECRET ausente" in _problemas(monkeypatch, JWT_SECRET=None)


def test_jwt_secret_curto_e_recusado_em_producao(monkeypatch):
    """Segredo curto é adivinhável — e forjar um token de admin dá acesso a
    nome e nota de todos os alunos."""
    p = _problemas(monkeypatch, JWT_SECRET="curto")
    assert "32" in p and "forjar" in p


# ------------------------------------------------ semente de administrador
def test_senha_de_exemplo_e_recusada_em_producao(monkeypatch):
    """`admin123` era a senha usada em desenvolvimento e está em documentação
    versionada — semear com ela cria um admin de credencial pública."""
    assert "senha de exemplo" in _problemas(monkeypatch, ADMIN_PASSWORD="admin123")


@pytest.mark.parametrize("senha", ["admin", "password", "123456", "changeme", "senha"])
def test_outras_senhas_triviais_sao_recusadas(monkeypatch, senha):
    assert "senha de exemplo" in _problemas(monkeypatch, ADMIN_PASSWORD=senha)


def test_senha_curta_e_recusada_em_producao(monkeypatch):
    assert "ao menos 12" in _problemas(monkeypatch, ADMIN_PASSWORD="Xy7!qP2z")


def test_sem_admin_configurado_a_semeadura_e_pulada(monkeypatch):
    """Não é erro: o admin pode ser criado por outro caminho."""
    s = _settings(monkeypatch, ADMIN_EMAIL=None, ADMIN_PASSWORD=None)
    assert s.validar() == []
    assert s.resumo()["admin_seed_configurado"] is False


# ----------------------------------------------------------------------- CORS
def test_origem_de_desenvolvimento_nao_e_mais_fixa_no_codigo():
    """`allowed_origins` incluía `http://localhost:3000` sem condição de
    ambiente: a origem de desenvolvimento ia junto para produção."""
    servidor = (BACKEND / "server.py").read_text(encoding="utf-8")
    assert 'allowed_origins = [FRONTEND_URL, "http://localhost:3000"]' not in servidor
    assert "settings.CORS_ORIGINS" in servidor


def test_cors_derivado_do_frontend_url(monkeypatch):
    s = _settings(monkeypatch)
    assert s.CORS_ORIGINS == ["https://professor.exemplo.app"]


def test_cors_explicito_tem_precedencia(monkeypatch):
    s = _settings(monkeypatch, CORS_ORIGINS="https://a.app,https://b.app")
    assert s.CORS_ORIGINS == ["https://a.app", "https://b.app"]


def test_cors_ausente_e_recusado_em_producao(monkeypatch):
    assert "CORS_ORIGINS" in _problemas(monkeypatch, FRONTEND_URL=None)


def test_cors_sem_tls_e_recusado_em_producao(monkeypatch):
    assert "sem TLS" in _problemas(monkeypatch, FRONTEND_URL="http://professor.exemplo.app")


# -------------------------------------------------------------------- cookies
def test_cookie_de_producao_e_cross_site_por_padrao(monkeypatch):
    s = _settings(monkeypatch, COOKIE_SECURE=None, COOKIE_SAMESITE=None)
    assert s.COOKIE_SECURE is True and s.COOKIE_SAMESITE == "none"


def test_cookie_inseguro_e_recusado_em_producao(monkeypatch):
    assert "em claro" in _problemas(monkeypatch, COOKIE_SECURE="false", COOKIE_SAMESITE="lax")


# ------------------------------------------------------------ dados de demo
def test_seed_de_demonstracao_e_recusado_em_producao(monkeypatch):
    """Turmas e alunos fictícios, indistinguíveis de dado de escola real."""
    assert "demonstração" in _problemas(monkeypatch, SEED_DEMO_DATA="true")


def test_seed_desligado_por_padrao_em_producao(monkeypatch):
    assert _settings(monkeypatch, SEED_DEMO_DATA=None).SEED_DEMO_DATA is False


def test_seed_e_gated_no_startup():
    servidor = (BACKEND / "server.py").read_text(encoding="utf-8")
    assert "if settings.SEED_DEMO_DATA:" in servidor


# ------------------------------------------------------------------- segredos
def test_resumo_nao_revela_segredo(monkeypatch):
    s = _settings(monkeypatch)
    texto = json.dumps(s.resumo())
    assert _BASE_PROD["JWT_SECRET"] not in texto
    assert _BASE_PROD["ADMIN_PASSWORD"] not in texto


def test_boot_aborta_com_configuracao_invalida(monkeypatch):
    s = _settings(monkeypatch, JWT_SECRET=None)
    with pytest.raises(s.ConfigError, match="JWT_SECRET"):
        s.exigir_config_valida()
