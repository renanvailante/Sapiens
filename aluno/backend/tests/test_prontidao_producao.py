"""Prontidão para produção — app `aluno`.

Foco no que é específico deste app: política de cookie de sessão e o gate dos
dados de demonstração. Rodam offline.
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
    "DB_NAME": "sapiens_aluno",
    "CORS_ORIGINS": "https://aluno.exemplo.app",
    "GEMINI_API_KEY": "chave-gemini",
    "FIREBASE_SERVICE_ACCOUNT_PATH": "/secrets/sa.json",
    "ADMIN_EMAILS": "admin@exemplo.app",
    "MERCADOPAGO_ACCESS_TOKEN": "APP_USR-token",
    "MERCADOPAGO_PUBLIC_KEY": "APP_USR-public-key",
    "MERCADOPAGO_WEBHOOK_SECRET": "webhook-secret",
    "SEED_DEMO_DATA": "false",
    "COOKIE_SECURE": "true",
    "COOKIE_SAMESITE": "none",
}


def _settings(monkeypatch, **over):
    """Carrega `settings.py` sob um ambiente monkeypatchado, isolado.

    `importlib.reload` de `settings` mutaria o MESMO objeto de módulo que
    `server.py` importa (`sys.modules["settings"]`) — como o valor final fica
    de pé até o próximo reload, um caso aqui testando config INVÁLIDA (ex.:
    `MONGO_URL=None`) deixava `settings.MONGO_URL` quebrado para qualquer
    `import server` posterior no mesmo processo, mesmo depois do
    `monkeypatch` reverter as env vars — o teardown do monkeypatch não
    re-executa o módulo. Isso só aparecia com `pytest-xdist --dist loadscope`
    agrupando este arquivo com outro que faz `import server` no mesmo worker
    (não em execução isolada), tornando o resultado dependente da ordem.
    Carregar um objeto de módulo novo, fora de `sys.modules`, evita o
    problema na raiz: `settings` real nunca é tocado.
    """
    env = {**_BASE_PROD, **over}
    for k in list(_BASE_PROD) + list(over):
        v = env.get(k)
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    # `settings.py` agora chama `load_dotenv()` sozinho, para ficar correto
    # não importa quem o importe primeiro (ver `settings.py`). Sem
    # neutralizar isso aqui, ele preencheria de volta, a partir do `.env`
    # real do dev, exatamente as chaves que este teste removeu de propósito
    # para simular ausência (`over={"CORS_ORIGINS": None}` etc.) — o cenário
    # de "config ausente" deixaria de existir.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    import importlib.util

    spec = importlib.util.spec_from_file_location("settings_sob_teste", BACKEND / "settings.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _problemas(monkeypatch, **over) -> str:
    return " | ".join(_settings(monkeypatch, **over).validar())


def test_configuracao_completa_de_producao_e_aceita(monkeypatch):
    assert _settings(monkeypatch).validar() == []


def test_desenvolvimento_nao_exige_nada_de_producao(monkeypatch):
    s = _settings(
        monkeypatch, APP_ENV="development", CORS_ORIGINS=None, GEMINI_API_KEY=None,
        FIREBASE_SERVICE_ACCOUNT_PATH=None, ADMIN_EMAILS=None,
        MERCADOPAGO_ACCESS_TOKEN=None, MERCADOPAGO_WEBHOOK_SECRET=None,
        COOKIE_SECURE=None, COOKIE_SAMESITE=None, SEED_DEMO_DATA=None,
    )
    assert s.validar() == []


# -------------------------------------------------------------------- cookies
def test_cookie_de_desenvolvimento_e_aceito_pelo_navegador_local(monkeypatch):
    """`SameSite=None; Secure` é DESCARTADO em http://localhost — o login
    parece funcionar e a sessão não persiste, sem erro visível."""
    s = _settings(monkeypatch, APP_ENV="development", COOKIE_SECURE=None,
                  COOKIE_SAMESITE=None, CORS_ORIGINS=None, GEMINI_API_KEY=None,
                  FIREBASE_SERVICE_ACCOUNT_PATH=None, ADMIN_EMAILS=None)
    assert s.COOKIE_SECURE is False
    assert s.COOKIE_SAMESITE == "lax"


def test_cookie_de_producao_e_cross_site_por_padrao(monkeypatch):
    """Frontend e backend em domínios diferentes exigem Secure + SameSite=None."""
    s = _settings(monkeypatch, COOKIE_SECURE=None, COOKIE_SAMESITE=None)
    assert s.COOKIE_SECURE is True
    assert s.COOKIE_SAMESITE == "none"


def test_samesite_none_sem_secure_e_recusado(monkeypatch):
    p = _problemas(monkeypatch, APP_ENV="development", COOKIE_SAMESITE="none",
                   COOKIE_SECURE="false", CORS_ORIGINS=None, GEMINI_API_KEY=None,
                   FIREBASE_SERVICE_ACCOUNT_PATH=None, ADMIN_EMAILS=None)
    assert "COOKIE_SECURE=true" in p


def test_cookie_inseguro_e_recusado_em_producao(monkeypatch):
    p = _problemas(monkeypatch, COOKIE_SECURE="false", COOKIE_SAMESITE="lax")
    assert "em claro" in p


def test_samesite_invalido_e_recusado(monkeypatch):
    assert "inválido" in _problemas(monkeypatch, COOKIE_SAMESITE="talvez")


# ----------------------------------------------------------------------- CORS
def test_cors_curinga_e_recusado_em_producao(monkeypatch):
    assert "'*'" in _problemas(monkeypatch, CORS_ORIGINS="*")


def test_cors_ausente_e_recusado_em_producao(monkeypatch):
    assert "CORS_ORIGINS ausente" in _problemas(monkeypatch, CORS_ORIGINS=None)


# ------------------------------------------------------------ dependências
def test_firebase_ausente_e_recusado_em_producao(monkeypatch):
    """Sem Firestore nenhum evento de resposta é registrado."""
    p = _problemas(monkeypatch, FIREBASE_SERVICE_ACCOUNT_PATH=None)
    assert "Firebase" in p


def test_credencial_do_firebase_aceita_json_inline(monkeypatch):
    """PaaS que só aceita variável de ambiente não consegue montar arquivo."""
    s = _settings(monkeypatch, FIREBASE_SERVICE_ACCOUNT_PATH=None,
                  FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account"}')
    assert s.validar() == []


def test_gemini_ausente_e_recusada_em_producao(monkeypatch):
    assert "GEMINI_API_KEY" in _problemas(monkeypatch, GEMINI_API_KEY=None)


def test_sem_admin_declarado_e_recusado_em_producao(monkeypatch):
    """Ninguém conseguiria acessar as telas administrativas."""
    assert "ADMIN_EMAILS" in _problemas(monkeypatch, ADMIN_EMAILS=None)


def test_loja_desligada_nao_impede_o_boot(monkeypatch):
    """Abrir o beta sem a loja de Sparks é uma escolha legítima: o resto do
    produto (prática, redação, diagnóstico) funciona igual, e a compra aparece
    como indisponível. Não pode derrubar o processo inteiro."""
    assert _settings(
        monkeypatch,
        MERCADOPAGO_ACCESS_TOKEN=None,
        MERCADOPAGO_PUBLIC_KEY=None,
        MERCADOPAGO_WEBHOOK_SECRET=None,
    ).validar() == []


def test_mercadopago_webhook_secret_ausente_e_recusado_em_producao(monkeypatch):
    """Configuração PELA METADE é o estado perigoso: com token e sem segredo de
    webhook, o cartão é cobrado e a confirmação é rejeitada por assinatura
    inválida — o dinheiro sai e os Sparks nunca entram, em silêncio."""
    assert "MERCADOPAGO_WEBHOOK_SECRET" in _problemas(monkeypatch, MERCADOPAGO_WEBHOOK_SECRET=None)


def test_public_key_ausente_com_loja_ligada_e_recusada(monkeypatch):
    """Sem a public key o Brick não monta no navegador — a loja apareceria mas
    o formulário de pagamento ficaria vazio."""
    assert "MERCADOPAGO_PUBLIC_KEY" in _problemas(monkeypatch, MERCADOPAGO_PUBLIC_KEY=None)


def test_credencial_de_teste_do_mercadopago_e_recusada_em_producao(monkeypatch):
    """Deixar a credencial `TEST-` em produção não falha visivelmente: o
    checkout abre, o cartão é "aceito" e nenhum dinheiro entra. O boot precisa
    recusar, senão o erro só aparece na conciliação financeira."""
    p = _problemas(monkeypatch, MERCADOPAGO_ACCESS_TOKEN="TEST-123")
    assert "MERCADOPAGO_ACCESS_TOKEN" in p and "teste" in p


def test_public_key_de_teste_do_mercadopago_e_recusada_em_producao(monkeypatch):
    """O Brick monta com a public key; se ela for de teste, o formulário roda
    em sandbox mesmo com o backend em produção."""
    p = _problemas(monkeypatch, MERCADOPAGO_PUBLIC_KEY="TEST-abc")
    assert "MERCADOPAGO_PUBLIC_KEY" in p and "teste" in p


# ------------------------------------------------------------ dados de demo
def test_seed_de_demonstracao_e_recusado_em_producao(monkeypatch):
    assert "demonstração" in _problemas(monkeypatch, SEED_DEMO_DATA="true")


def test_seed_desligado_por_padrao_em_producao(monkeypatch):
    assert _settings(monkeypatch, SEED_DEMO_DATA=None).SEED_DEMO_DATA is False


# ------------------------------------------------------------------- segredos
def test_resumo_nao_revela_segredo(monkeypatch):
    s = _settings(monkeypatch)
    resumo_json = json.dumps(s.resumo())
    assert _BASE_PROD["GEMINI_API_KEY"] not in resumo_json
    assert _BASE_PROD["MERCADOPAGO_ACCESS_TOKEN"] not in resumo_json
    assert _BASE_PROD["MERCADOPAGO_WEBHOOK_SECRET"] not in resumo_json
    assert s.resumo()["gemini_configurado"] is True
    assert s.resumo()["mercadopago_configurado"] is True


def test_boot_aborta_com_configuracao_invalida(monkeypatch):
    s = _settings(monkeypatch, MONGO_URL=None)
    with pytest.raises(s.ConfigError, match="MONGO_URL"):
        s.exigir_config_valida()


# ------------------------------------------------------------------ Dockerfile
def test_dockerfile_leva_o_corpus_canonico_para_a_imagem():
    """O app lê a ontologia e o validador de `pipeline/`. Buildar só a partir de
    `aluno/backend` produziria imagem que sobe e falha no primeiro acesso."""
    conteudo = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    assert "pipeline/docs/ontology/ontology_v1.4.json" in conteudo
    assert "pipeline/backend/ontology_validator.py" in conteudo
    assert "SAPIENS_ONTOLOGY_PATH" in conteudo
    assert "SAPIENS_CONTRACTS_PATH" in conteudo
    assert "RAIZ DO REPOSITÓRIO" in conteudo


# ------------------------------------------------------ layout de container
def test_resolucao_de_caminho_nao_quebra_em_diretorio_raso(tmp_path, monkeypatch):
    """No container este módulo fica em `/app/`, que não tem dois níveis acima.

    `Path(__file__).resolve().parents[2]` era calculado em tempo de IMPORT e
    levantava `IndexError` ali — o processo morria antes de olhar
    `SAPIENS_ONTOLOGY_PATH`, que tornaria o caminho relativo desnecessário.
    A primeira máquina no Fly.io reiniciou 10 vezes por causa disto.
    """
    import canonical_ontology as co

    monkeypatch.setattr(co, "__file__", "/app/canonical_ontology.py")
    assert co._repo_root() is None  # não levanta

    catalogo = tmp_path / "ontology_v1.4.json"
    catalogo.write_text('{"version": "1.4.1"}', encoding="utf-8")
    monkeypatch.setenv("SAPIENS_ONTOLOGY_PATH", str(catalogo))
    assert co.canonical_path() == catalogo


def test_sem_monorepo_e_sem_env_a_mensagem_diz_o_que_fazer(monkeypatch):
    import canonical_ontology as co

    monkeypatch.delenv("SAPIENS_ONTOLOGY_PATH", raising=False)
    monkeypatch.setattr(co, "_repo_root", lambda: None)
    with pytest.raises(RuntimeError, match="SAPIENS_ONTOLOGY_PATH"):
        co.canonical_path()
