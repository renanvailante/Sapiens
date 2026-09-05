"""Tradução de falha do Firestore para resposta HTTP — um lugar só.

`firestore_routes`, `events_routes` e `admin_routes` tinham cada um a sua
cópia de `_safe_call`, e as três copiavam o mesmo par de defeitos:

* **Cota esgotada virava 502.** No incidente de 2026-09-04 (o laço de auto-sync
  consumindo 154% da cota diária do Firestore) toda rota autenticada respondia
  502 com uma mensagem que não dizia nada acionável. Cota esgotada é condição
  operacional temporária, que se resolve sozinha na virada do dia: isso é 503
  com `Retry-After`, que é o que um cliente — e um monitor — sabem interpretar.

* **A exceção crua ia para o cliente.** `detail=f"Firestore error: {exc}"`
  devolvia a mensagem interna do SDK do Google (caminho da coleção, id do
  projeto, forma da consulta) para qualquer pessoa autenticada. Detalhe de
  falha pertence ao log; o cliente recebe o que precisa para decidir o que fazer.

Não há política por módulo: se um dia a tradução mudar, muda aqui.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger("sapiens.firestore.http")

COTA_ESGOTADA_DETALHE = (
    "O banco de dados atingiu o limite de leituras do dia. O serviço volta "
    "sozinho na virada do dia; se for urgente, avise a equipe."
)


def safe_call(fn, *args, **kwargs):
    """Executa `fn`, traduzindo qualquer falha do Firestore em HTTPException."""
    try:
        return fn(*args, **kwargs)
    except google_exceptions.ResourceExhausted as exc:
        # `logger.error` e não `exception`: o traceback do gRPC não acrescenta
        # nada aqui e, num dia de cota estourada, ele repete a cada requisição.
        logger.error("Firestore com cota esgotada: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=COTA_ESGOTADA_DETALHE,
            headers={"Retry-After": "3600"},
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha no Firestore: %s", exc)
        raise HTTPException(status_code=502, detail="Falha ao consultar o banco de dados.") from exc


async def executar_async(fn, *args, **kwargs):
    """Mesma tradução, para as rotas cujo trabalho já é `async` (o sync do
    acervo e o recálculo de perfis, ambos de admin). Sem isto, elas ficariam
    com uma política de erro própria — que foi exatamente como os três
    `_safe_call` divergiram."""
    try:
        return await fn(*args, **kwargs)
    except google_exceptions.ResourceExhausted as exc:
        logger.error("Firestore com cota esgotada: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=COTA_ESGOTADA_DETALHE,
            headers={"Retry-After": "3600"},
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha no Firestore: %s", exc)
        raise HTTPException(status_code=502, detail="Falha ao consultar o banco de dados.") from exc
