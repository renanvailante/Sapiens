"""Rotas dos direitos do titular (LGPD art. 18).

Duas para o próprio aluno (exportar e excluir a própria conta) e duas para o
admin, porque boa parte de quem usa o Sapiens é menor de idade e o pedido
costuma chegar pelo responsável, por e-mail, não pela tela.

Ver `dados_pessoais.py` para o inventário do que é exportado e apagado.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel

import dados_pessoais as dp
import rate_limit
import settings
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.dados_pessoais")

router = APIRouter(prefix="", tags=["dados-pessoais"])

_db = None


def set_db(db):
    global _db
    _db = db
    dp.set_db(db)


# Palavra que o aluno precisa digitar. Existe para que a exclusão não possa
# acontecer por um clique errado, por um link malicioso ou por um cliente que
# repita a requisição: é uma ação sem volta e o corpo tem de dizer isso.
CONFIRMACAO = "EXCLUIR"


class ExclusaoRequest(BaseModel):
    confirmacao: str
    senha: str | None = None


@router.get("/me/dados")
async def exportar_meus_dados(
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("dados_pessoais")),
):
    """Cópia dos dados do titular (art. 18, II e V)."""
    return await dp.exportar(user.user_id)


@router.post("/me/conta/excluir")
async def excluir_minha_conta(
    response: Response,
    payload: ExclusaoRequest,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("dados_pessoais")),
):
    """Exclusão da própria conta (art. 18, VI). **Não tem volta.**

    Quem entrou por e-mail confirma com a senha. Quem entrou pelo Google não
    tem senha para confirmar — ali a garantia é a sessão válida mais a palavra
    de confirmação, que é o mesmo padrão que o resto do produto usa para ação
    sem volta. Pedir "digite seu e-mail" não acrescentaria nada: quem está com
    a sessão aberta já vê o e-mail na tela.
    """
    if payload.confirmacao != CONFIRMACAO:
        raise HTTPException(
            status_code=400,
            detail=f"Para confirmar, envie confirmacao='{CONFIRMACAO}'.",
        )

    if user.provider == "email":
        from auth import _check_password

        doc = await _db.users.find_one({"user_id": user.user_id}, {"password_hash": 1})
        if not payload.senha or not _check_password(payload.senha, (doc or {}).get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Senha incorreta.")

    logger.warning("Pedido de EXCLUSÃO DE CONTA por %s (%s).", user.user_id, user.provider)
    relatorio = await dp.excluir(user.user_id)

    # Mesmos atributos do `set_cookie`, senão o navegador não casa o cookie e a
    # sessão some do servidor mas continua no cliente.
    response.delete_cookie(
        "session_token", path="/", domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
    )
    return {"ok": True, "relatorio": relatorio}


# ------------------------------------------------------------------ admin
#
# O pedido de um responsável chega por e-mail, não pela tela — e ele não tem
# (nem deve ter) a senha do filho para entrar na conta e clicar.

@router.get("/admin/users/{user_id}/dados")
async def exportar_dados_de(user_id: str, admin: User = Depends(require_admin)):
    logger.warning("Admin %s exportou os dados de %s.", admin.email, user_id)
    return await dp.exportar(user_id)


@router.post("/admin/users/{user_id}/excluir")
async def excluir_conta_de(
    user_id: str,
    admin: User = Depends(require_admin),
    confirmacao: str = Body(..., embed=True),
):
    if confirmacao != CONFIRMACAO:
        raise HTTPException(
            status_code=400, detail=f"Para confirmar, envie confirmacao='{CONFIRMACAO}'."
        )
    alvo = await _db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1})
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    logger.warning("Admin %s EXCLUIU a conta de %s a pedido do titular.", admin.email, user_id)
    return {"ok": True, "relatorio": await dp.excluir(user_id)}
