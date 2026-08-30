"""Rotas do corretor de redação Enem — base local-first (ver `redacao/`).

Mesmo padrão de auth/persistência dos demais módulos: `require_user`
(cookie/sessão), `set_db(db)` injetado por `server.py`. A correção roda
síncrona dentro do request — a maioria das redações resolve 100% local
(sem chamada de rede); quando algo escala para o Gemini, é no máximo 1-2
chamadas pequenas e específicas (ver `redacao/service.py`), não uma
chamada longa como a anotação do pipeline.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from auth import require_user
from models import AvaliacaoRedacao, Redacao, RedacaoSubmitRequest, User
from redacao import service
from redacao.canon import CanonIndisponivelError
from redacao.tipos import RedacaoEntrada

logger = logging.getLogger("sapiens.redacao.routes")

router = APIRouter(prefix="/redacao", tags=["redacao"])

_db = None


def set_db(db):
    global _db
    _db = db


@router.post("")
async def submeter_redacao(payload: RedacaoSubmitRequest, user: User = Depends(require_user)):
    if not (payload.texto or "").strip():
        raise HTTPException(status_code=422, detail="Texto da redação vazio.")

    redacao = Redacao(
        user_id=user.user_id, texto=payload.texto, titulo=payload.titulo,
        tema_frase=payload.tema_frase, tema_elementos_obrigatorios=payload.tema_elementos_obrigatorios,
        linhas_manuscritas=payload.linhas_manuscritas, textos_motivadores=payload.textos_motivadores,
    )
    await _db.redacoes.insert_one(redacao.model_dump())

    entrada = RedacaoEntrada(
        texto=payload.texto, titulo=payload.titulo, tema_frase=payload.tema_frase,
        tema_elementos_obrigatorios=payload.tema_elementos_obrigatorios,
        linhas_manuscritas=payload.linhas_manuscritas, textos_motivadores=payload.textos_motivadores,
    )
    try:
        resultado = await service.corrigir_redacao(entrada, db=_db, redacao_id=redacao.redacao_id)
    except CanonIndisponivelError as exc:
        raise HTTPException(status_code=503, detail=f"Corretor indisponível: {exc}") from exc

    avaliacao = AvaliacaoRedacao(redacao_id=redacao.redacao_id, user_id=user.user_id, **resultado)
    await _db.redacao_avaliacoes.insert_one(avaliacao.model_dump())

    return {
        "redacao": redacao.model_dump(),
        "avaliacao": avaliacao.model_dump(),
    }


@router.get("/{redacao_id}")
async def obter_avaliacao(redacao_id: str, user: User = Depends(require_user)):
    redacao = await _db.redacoes.find_one({"redacao_id": redacao_id, "user_id": user.user_id}, {"_id": 0})
    if not redacao:
        raise HTTPException(status_code=404, detail="Redação não encontrada.")
    avaliacao = await _db.redacao_avaliacoes.find_one(
        {"redacao_id": redacao_id, "user_id": user.user_id}, {"_id": 0},
    )
    return {"redacao": redacao, "avaliacao": avaliacao}


@router.get("")
async def historico_redacoes(limit: int = 20, user: User = Depends(require_user)):
    limit = max(1, min(int(limit), 100))
    cursor = _db.redacoes.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).limit(limit)
    redacoes = await cursor.to_list(length=limit)
    ids = [r["redacao_id"] for r in redacoes]
    avaliacoes_cursor = _db.redacao_avaliacoes.find(
        {"redacao_id": {"$in": ids}, "user_id": user.user_id}, {"_id": 0},
    )
    avaliacoes = {a["redacao_id"]: a async for a in avaliacoes_cursor}
    return {
        "items": [
            {"redacao": r, "avaliacao": avaliacoes.get(r["redacao_id"])}
            for r in redacoes
        ],
        "count": len(redacoes),
    }
