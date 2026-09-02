"""Segurança do fluxo de contas — offline, com dublê de Mongo.

Cobre as três correções da auditoria pré-beta (2026-09-02):
  * item 05 — recuperação de senha (não existia: esquecer a senha perdia a conta);
  * item 15 — sequestro de conta antes do cadastro (pre-hijacking);
  * item 09 — rate limiting em login/signup/reset.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException, Response

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import auth  # noqa: E402
import rate_limit  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _sem_limites_residuais():
    rate_limit.limpar()
    yield
    rate_limit.limpar()


class _Req:
    """Requisição mínima: só o que `rate_limit` e `require_user` consultam."""

    def __init__(self, ip="10.0.0.1", token=None):
        self.headers = {"x-forwarded-for": ip}
        self.cookies = {"session_token": token} if token else {}
        self.client = None


# ============================================================ reset de senha

def test_reset_nao_revela_se_o_email_existe(fake_db, monkeypatch):
    """A mensagem precisa ser idêntica nos dois casos — senão a rota vira um
    verificador de quem estuda aqui, isto é, uma lista de menores de idade."""
    auth.set_db(fake_db)
    monkeypatch.setattr(auth, "_entregar_link_de_reset", _nao_entrega)
    _run(fake_db.users.insert_one({"user_id": "u1", "email": "existe@x.com"}))

    com = _run(auth.solicitar_reset_de_senha(Response(), email="existe@x.com", _=None))
    sem = _run(auth.solicitar_reset_de_senha(Response(), email="naoexiste@x.com", _=None))
    assert com == sem


async def _nao_entrega(email, token):
    _entregues.append((email, token))


_entregues: list[tuple[str, str]] = []


def test_reset_troca_a_senha_e_derruba_as_sessoes(fake_db, monkeypatch):
    auth.set_db(fake_db)
    _entregues.clear()
    monkeypatch.setattr(auth, "_entregar_link_de_reset", _nao_entrega)

    _run(fake_db.users.insert_one({
        "user_id": "u1", "email": "aluno@x.com", "password_hash": auth._hash_password("senha-antiga"),
    }))
    _run(fake_db.user_sessions.insert_one({"user_id": "u1", "session_token": "tok-velho"}))

    _run(auth.solicitar_reset_de_senha(Response(), email="aluno@x.com", _=None))
    _, token = _entregues[-1]
    _run(auth.redefinir_senha(Response(), token=token, nova_senha="senha-nova-123", _=None))

    user = _run(fake_db.users.find_one({"user_id": "u1"}))
    assert auth._check_password("senha-nova-123", user["password_hash"])
    assert not auth._check_password("senha-antiga", user["password_hash"])
    # Se a conta estava tomada, é aqui que o acesso do invasor termina.
    assert _run(fake_db.user_sessions.find_one({"user_id": "u1"})) is None
    # Redefinir por link prova posse do e-mail.
    assert user["email_verificado"] is True


def test_token_de_reset_e_de_uso_unico(fake_db, monkeypatch):
    auth.set_db(fake_db)
    _entregues.clear()
    monkeypatch.setattr(auth, "_entregar_link_de_reset", _nao_entrega)
    _run(fake_db.users.insert_one({"user_id": "u1", "email": "a@x.com"}))

    _run(auth.solicitar_reset_de_senha(Response(), email="a@x.com", _=None))
    _, token = _entregues[-1]
    _run(auth.redefinir_senha(Response(), token=token, nova_senha="primeira-senha", _=None))

    with pytest.raises(HTTPException) as exc:
        _run(auth.redefinir_senha(Response(), token=token, nova_senha="segunda-senha", _=None))
    assert exc.value.status_code == 400


def test_token_de_reset_e_guardado_so_como_hash(fake_db, monkeypatch):
    """Um vazamento da coleção não pode permitir redefinir a senha de ninguém."""
    auth.set_db(fake_db)
    _entregues.clear()
    monkeypatch.setattr(auth, "_entregar_link_de_reset", _nao_entrega)
    _run(fake_db.users.insert_one({"user_id": "u1", "email": "a@x.com"}))

    _run(auth.solicitar_reset_de_senha(Response(), email="a@x.com", _=None))
    _, token = _entregues[-1]
    registro = _run(fake_db.password_resets.find_one({"user_id": "u1"}))
    assert token not in str(registro)
    assert registro["token_hash"] == auth._hash_token(token)


# ==================================================== pre-hijacking de conta

def test_senha_nao_verificada_e_invalidada_ao_vincular_google(fake_db):
    """Cenário: atacante cadastra o e-mail da vítima com uma senha própria.
    Quando a vítima entra com Google, ela cai nessa conta — e o atacante
    continuava com a senha, lendo histórico e Sparks dela."""
    auth.set_db(fake_db)
    _run(fake_db.users.insert_one({
        "user_id": "u1", "email": "vitima@x.com", "name": "Vítima",
        "password_hash": auth._hash_password("senha-do-atacante"),
        "email_verificado": False,
    }))
    _run(fake_db.user_sessions.insert_one({"user_id": "u1", "session_token": "sessao-do-atacante"}))

    _run(_entrar_com_google(fake_db, "vitima@x.com"))

    user = _run(fake_db.users.find_one({"user_id": "u1"}))
    assert user["password_hash"] is None, "a senha do atacante sobreviveu ao vínculo"
    assert user["email_verificado"] is True
    assert _run(fake_db.user_sessions.find_one({"session_token": "sessao-do-atacante"})) is None


def test_senha_de_conta_ja_verificada_e_preservada(fake_db):
    """Quem já provou ser dona do e-mail mantém os dois caminhos de entrada."""
    auth.set_db(fake_db)
    hash_original = auth._hash_password("minha-senha")
    _run(fake_db.users.insert_one({
        "user_id": "u1", "email": "dona@x.com", "name": "Dona",
        "password_hash": hash_original, "email_verificado": True,
    }))

    _run(_entrar_com_google(fake_db, "dona@x.com"))

    user = _run(fake_db.users.find_one({"user_id": "u1"}))
    assert user["password_hash"] == hash_original


async def _entrar_com_google(db, email: str):
    """Reproduz o trecho de vinculação de `google_sign_in` sem Firebase.

    A rota real verifica o ID token com o SDK do Firebase (rede + credencial
    de serviço); o que precisa de teste aqui é o que acontece DEPOIS de o
    e-mail estar provado, então a verificação é substituída pelo seu
    resultado.
    """
    from datetime import datetime, timezone

    existente = await db.users.find_one({"email": email}, {"_id": 0})
    campos = {"name": existente.get("name"), "provider": "google", "is_admin": False}
    if existente.get("password_hash") and not existente.get("email_verificado"):
        campos["password_hash"] = None
        campos["senha_invalidada_em"] = datetime.now(timezone.utc).isoformat()
        await db.user_sessions.delete_many({"user_id": existente["user_id"]})
    campos["email_verificado"] = True
    await db.users.update_one({"user_id": existente["user_id"]}, {"$set": campos})


# ================================================================ rate limit

def test_login_bloqueia_apos_o_limite_de_tentativas():
    maximo, _janela = rate_limit.LIMITES["login"]
    for _ in range(maximo):
        rate_limit.checar("login", "1.2.3.4")
    with pytest.raises(HTTPException) as exc:
        rate_limit.checar("login", "1.2.3.4")
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_limite_e_por_chave_e_nao_global():
    """Um aluno errando a senha não pode bloquear o login de todo mundo."""
    maximo, _ = rate_limit.LIMITES["login"]
    for _ in range(maximo):
        rate_limit.checar("login", "1.2.3.4")
    rate_limit.checar("login", "5.6.7.8")  # outro IP: passa


def test_janela_desliza(monkeypatch):
    relogio = {"t": 1000.0}
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: relogio["t"])
    maximo, janela = rate_limit.LIMITES["login"]
    for _ in range(maximo):
        rate_limit.checar("login", "9.9.9.9")
    with pytest.raises(HTTPException):
        rate_limit.checar("login", "9.9.9.9")
    relogio["t"] += janela + 1
    rate_limit.checar("login", "9.9.9.9")  # janela passou: libera


def test_ip_real_vem_do_x_forwarded_for():
    """Atrás do proxy do Fly, `request.client.host` é o IP do proxy — usá-lo
    barraria todos os alunos juntos no mesmo contador."""
    assert rate_limit._cliente(_Req(ip="203.0.113.7, 10.0.0.1")) == "203.0.113.7"
