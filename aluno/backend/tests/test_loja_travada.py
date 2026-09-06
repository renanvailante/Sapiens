"""Com a configuração do Mercado Pago incompleta, nenhuma compra acontece.

Esta é a garantia que substitui a recusa de boot: o site sobe normalmente e a
loja fica fechada. O que não pode existir, em hipótese nenhuma, é o meio-termo
— cobrar o cartão e não conseguir creditar os Sparks, porque o webhook sem
segredo rejeita a confirmação.

Os testes chamam as funções de rota direto (mesmo estilo offline do resto do
repo). Nada aqui toca rede, Mongo real ou Firestore.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import mercadopago_client as mp  # noqa: E402
import settings  # noqa: E402
import sparks_routes as rotas  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user() -> User:
    return User(user_id="user-1", email="aluno@exemplo.com", name="Aluno")


@pytest.fixture
def loja_desligada(monkeypatch):
    monkeypatch.setattr(settings, "MERCADOPAGO_HABILITADO", False)
    monkeypatch.setattr(
        settings, "MERCADOPAGO_MOTIVO_DESLIGADA",
        "configuração ausente: MERCADOPAGO_WEBHOOK_SECRET",
    )


@pytest.fixture
def mp_explode(monkeypatch):
    """Qualquer chamada ao Mercado Pago falha o teste.

    É o coração desta suíte: não basta a rota devolver 503 — ela tem que
    devolver 503 ANTES de tocar o Mercado Pago. Um pagamento criado e depois
    recusado internamente já teria movimentado dinheiro.
    """
    def _proibido(*a, **k):
        raise AssertionError("A rota chamou o Mercado Pago com a loja desligada.")

    for fn in ("create_payment", "get_payment", "create_preapproval",
               "update_preapproval", "get_preapproval"):
        monkeypatch.setattr(mp, fn, _proibido)


# ==================================================== rotas que movem dinheiro

def test_criar_compra_e_recusada_sem_tocar_o_mercado_pago(loja_desligada, mp_explode):
    payload = rotas.PurchaseRequest(
        package_id="spark_200", token="tok", payment_method_id="visa",
    )
    with pytest.raises(HTTPException) as exc:
        _run(rotas.create_purchase(payload, user=_user()))
    assert exc.value.status_code == 503


def test_ativar_recarga_automatica_e_recusada(loja_desligada, mp_explode):
    payload = rotas.AutoRechargeCreateRequest(
        package_id="spark_200", frequency_days=30, baseline=50, card_token_id="tok",
    )
    with pytest.raises(HTTPException) as exc:
        _run(rotas.activate_auto_recharge(payload, user=_user()))
    assert exc.value.status_code == 503


def test_alterar_recarga_automatica_e_recusada(loja_desligada, mp_explode):
    """PATCH troca o pacote, o que muda o valor cobrado no Mercado Pago."""
    payload = rotas.AutoRechargeUpdateRequest(package_id="spark_1200")
    with pytest.raises(HTTPException) as exc:
        _run(rotas.patch_auto_recharge(payload, user=_user()))
    assert exc.value.status_code == 503


def test_config_nao_entrega_public_key_com_loja_desligada(loja_desligada, mp_explode):
    """Sem public key o Checkout Brick não monta no navegador — é o que impede
    o formulário de pagamento de aparecer sequer."""
    with pytest.raises(HTTPException) as exc:
        _run(rotas.get_config(_=_user()))
    assert exc.value.status_code == 503


# ============================================================ vazamento

def test_a_recusa_nao_revela_qual_credencial_falta(loja_desligada, mp_explode):
    """O motivo real fica no log e em /ready, que exigem acesso ao servidor.
    Dizer na resposta HTTP contaria a um atacante qual metade está aberta."""
    with pytest.raises(HTTPException) as exc:
        _run(rotas.get_config(_=_user()))
    detalhe = str(exc.value.detail)
    assert "MERCADOPAGO" not in detalhe
    assert "WEBHOOK" not in detalhe.upper()
    assert "temporariamente indisponível" in detalhe


# ============================================ o que CONTINUA funcionando

def test_catalogo_continua_visivel(loja_desligada, mp_explode):
    """O catálogo é estático e não move dinheiro. Mantê-lo visível é o que
    permite ao aluno saber o que existe — e o botão fica desabilitado, porque
    a public key nunca chega."""
    resposta = _run(rotas.list_packages(_=_user()))
    assert len(resposta["packages"]) == 4


def test_webhook_continua_rejeitando_assinatura_invalida():
    """A segurança do webhook NÃO é relaxada em nenhum estado: sem segredo
    configurado, `verify_webhook_signature` devolve False para tudo — inclusive
    para uma notificação bem formada."""
    assert mp.verify_webhook_signature(
        x_signature="ts=123,v1=abc", x_request_id="req-1", data_id="999", secret=None,
    ) is False
    assert mp.verify_webhook_signature(
        x_signature="ts=123,v1=assinatura-errada", x_request_id="req-1",
        data_id="999", secret="segredo-real",
    ) is False


def test_webhook_aceita_assinatura_valida():
    """O outro lado da trava: com o segredo certo e o manifest correto, passa.
    Sem este caso, o teste acima passaria mesmo com a validação quebrada."""
    import hashlib
    import hmac

    segredo, ts, data_id, request_id = "segredo-real", "1700000000", "12345", "req-1"
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(segredo.encode(), manifest.encode(), hashlib.sha256).hexdigest()

    assert mp.verify_webhook_signature(
        x_signature=f"ts={ts},v1={v1}", x_request_id=request_id,
        data_id=data_id, secret=segredo,
    ) is True
