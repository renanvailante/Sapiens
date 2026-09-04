"""Prontidão para produção — configuração que não pode ir para o ar errada.

Cada teste corresponde a uma forma concreta de quebrar ou expor a plataforma em
produção. Rodam offline: só exercitam `settings.validar()` e leem arquivos de
configuração.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent.parent
sys.path.insert(0, str(BACKEND))

APPS = ("aluno", "pipeline", "professor")

_BASE_PROD = {
    "APP_ENV": "production",
    "MONGO_URL": "mongodb://db:27017",
    "DB_NAME": "sapiens_pipeline",
    "PIPELINE_API_KEY": "k" * 64,
    "GEMINI_API_KEY": "chave-gemini",
    "CORS_ORIGINS": "https://pipeline.exemplo.app",
    "STORAGE_MODE": "firebase",
    "FIREBASE_STORAGE_BUCKET": "proj.firebasestorage.app",
    "GOOGLE_APPLICATION_CREDENTIALS": "/secrets/sa.json",
    "FIRESTORE_MODE": "admin",
    "SEED_DEMO_DATA": "false",
}


def _settings(monkeypatch, **over):
    """Recarrega `settings` com um ambiente controlado."""
    env = {**_BASE_PROD, **over}
    for k in list(_BASE_PROD) + list(over):
        v = env.get(k)
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    import settings as s

    return importlib.reload(s)


def _problemas(monkeypatch, **over) -> str:
    return " | ".join(_settings(monkeypatch, **over).validar())


# ------------------------------------------------------------------ baseline
def test_configuracao_completa_de_producao_e_aceita(monkeypatch):
    assert _settings(monkeypatch).validar() == []


def test_desenvolvimento_nao_exige_nada_de_producao(monkeypatch):
    s = _settings(
        monkeypatch, APP_ENV="development", CORS_ORIGINS=None,
        STORAGE_MODE="local", FIRESTORE_MODE="mock", GOOGLE_APPLICATION_CREDENTIALS=None,
    )
    assert s.validar() == []
    assert s.IS_PRODUCTION is False


# ----------------------------------------------------------------------- CORS
def test_cors_curinga_e_recusado_em_producao(monkeypatch):
    """`allow_origins=['*']` com `allow_credentials=True` é rejeitado pelo
    navegador e, onde não é, deixa qualquer site ler respostas autenticadas."""
    assert "'*'" in _problemas(monkeypatch, CORS_ORIGINS="*")


def test_cors_ausente_e_recusado_em_producao(monkeypatch):
    assert "CORS_ORIGINS ausente" in _problemas(monkeypatch, CORS_ORIGINS=None)


def test_cors_sem_tls_e_recusado_em_producao(monkeypatch):
    assert "sem TLS" in _problemas(monkeypatch, CORS_ORIGINS="http://pipeline.exemplo.app")


def test_localhost_sem_tls_e_tolerado(monkeypatch):
    """Túnel de desenvolvimento contra um backend de staging é caso legítimo."""
    p = _problemas(monkeypatch, CORS_ORIGINS="https://x.app,http://localhost:3001")
    assert "sem TLS" not in p


# -------------------------------------------------------------------- storage
def test_storage_local_e_recusado_em_producao(monkeypatch):
    """Disco de container é efêmero: o PDF original some no primeiro redeploy
    e `regenerate` passa a falhar para todo item já criado."""
    p = _problemas(monkeypatch, STORAGE_MODE="local")
    assert "efêmero" in p and "STORAGE_MODE=firebase" in p


def test_storage_firebase_sem_bucket_e_recusado(monkeypatch):
    assert "FIREBASE_STORAGE_BUCKET" in _problemas(monkeypatch, FIREBASE_STORAGE_BUCKET=None)


def test_storage_firebase_sem_credencial_e_recusado(monkeypatch):
    p = _problemas(monkeypatch, GOOGLE_APPLICATION_CREDENTIALS=None)
    assert "GOOGLE_APPLICATION_CREDENTIALS" in p


def test_storage_modo_invalido_e_recusado(monkeypatch):
    assert "inválido" in _problemas(monkeypatch, APP_ENV="development", STORAGE_MODE="s3")


# ------------------------------------------------------------------ segredos
def test_api_key_ausente_e_recusada(monkeypatch):
    assert "PIPELINE_API_KEY ausente" in _problemas(monkeypatch, PIPELINE_API_KEY=None)


def test_api_key_curta_e_recusada_em_producao(monkeypatch):
    assert "32" in _problemas(monkeypatch, PIPELINE_API_KEY="curta")


def test_gemini_ausente_e_recusada(monkeypatch):
    assert "GEMINI_API_KEY ausente" in _problemas(monkeypatch, GEMINI_API_KEY=None)


# ------------------------------------------------------------------- firestore
def test_firestore_mock_e_recusado_em_producao(monkeypatch):
    """O modo 'mock' guarda o espelho em memória: o app do aluno nunca veria
    os itens, e a falha seria silenciosa."""
    assert "mock" in _problemas(monkeypatch, FIRESTORE_MODE="mock")


# ------------------------------------------------------------ dados de demo
def test_seed_de_demonstracao_e_recusado_em_producao(monkeypatch):
    assert "demonstração" in _problemas(monkeypatch, SEED_DEMO_DATA="true")


def test_seed_desligado_por_padrao_em_producao(monkeypatch):
    assert _settings(monkeypatch, SEED_DEMO_DATA=None).SEED_DEMO_DATA is False


def test_seed_ligado_por_padrao_em_desenvolvimento(monkeypatch):
    s = _settings(monkeypatch, APP_ENV="development", SEED_DEMO_DATA=None,
                  CORS_ORIGINS=None, STORAGE_MODE="local", FIRESTORE_MODE="mock")
    assert s.SEED_DEMO_DATA is True


# ------------------------------------------------------------------- resumo
def test_resumo_nao_revela_segredo(monkeypatch):
    """O resumo vai para o log de boot; um segredo ali vaza para o coletor."""
    s = _settings(monkeypatch)
    texto = json.dumps(s.resumo())
    assert _BASE_PROD["PIPELINE_API_KEY"] not in texto
    assert _BASE_PROD["GEMINI_API_KEY"] not in texto
    assert s.resumo()["gemini_configurado"] is True


def test_boot_aborta_com_configuracao_invalida(monkeypatch):
    s = _settings(monkeypatch, MONGO_URL=None)
    with pytest.raises(s.ConfigError, match="MONGO_URL"):
        s.exigir_config_valida()


# ------------------------------------------------- artefatos de deploy
@pytest.mark.parametrize("app", APPS)
def test_cada_app_tem_env_example_no_backend_e_no_frontend(app):
    """O `.env.example` é a documentação executável das variáveis."""
    assert (ROOT / app / "backend" / ".env.example").is_file()
    assert (ROOT / app / "frontend" / ".env.example").is_file()


@pytest.mark.parametrize("app", APPS)
def test_env_example_nao_contem_valor_de_segredo(app):
    """Chaves ficam vazias no exemplo — preenchê-las convida a versionar."""
    for sub in ("backend", "frontend"):
        texto = (ROOT / app / sub / ".env.example").read_text(encoding="utf-8")
        for linha in texto.splitlines():
            linha = linha.strip()
            if linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            if any(t in chave for t in ("SECRET", "API_KEY", "PASSWORD", "CREDENTIALS")):
                assert not valor.strip(), f"{app}/{sub}/.env.example: {chave} tem valor"


@pytest.mark.parametrize("app", APPS)
def test_cada_backend_tem_dockerfile(app):
    assert (ROOT / app / "backend" / "Dockerfile").is_file()
    assert (ROOT / app / "backend" / ".dockerignore").is_file()


@pytest.mark.parametrize("app", APPS)
def test_dockerfile_nao_roda_como_root(app):
    conteudo = (ROOT / app / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "USER sapiens" in conteudo


@pytest.mark.parametrize("app", APPS)
def test_dockerfile_respeita_a_porta_da_plataforma(app):
    """PaaS injeta $PORT; ignorá-lo faz o health check da plataforma falhar."""
    assert "${PORT:-8000}" in (ROOT / app / "backend" / "Dockerfile").read_text(encoding="utf-8")


@pytest.mark.parametrize("app", APPS)
def test_build_do_frontend_desativa_sourcemap(app):
    """Source map publica o código-fonte original e os valores substituídos
    das variáveis REACT_APP_*."""
    pkg = json.loads((ROOT / app / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert "GENERATE_SOURCEMAP=false" in pkg["scripts"]["build"]


def test_craco_do_pipeline_recusa_embutir_a_chave_no_bundle():
    """`REACT_APP_*` é substituída no bundle em tempo de build. A chave do
    pipeline protege TODAS as rotas do backend: publicá-la no JS entrega o
    anotador inteiro a qualquer visitante."""
    craco = (ROOT / "pipeline" / "frontend" / "craco.config.js").read_text(encoding="utf-8")
    assert "REACT_APP_PIPELINE_API_KEY" in craco
    assert "build recusada" in craco
    assert "PIPELINE_UI_PUBLICA" in craco


@pytest.mark.parametrize("app", APPS)
def test_gitignore_versiona_o_env_example_mas_nao_o_env(app):
    gi = (ROOT / app / ".gitignore")
    if gi.is_file():
        assert "!*.env.example" in gi.read_text(encoding="utf-8")
