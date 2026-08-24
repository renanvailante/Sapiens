"""Serve a figura de uma questão ao aluno, sem o app tocar o storage binário.

O app do aluno nunca acessa o bucket de artefatos do pipeline diretamente —
decisão documentada em `requirements.txt` ("os artefatos binários são do
pipeline, que permanece privado"). Este módulo busca os bytes já otimizados
(WebP) servidor-a-servidor em `pipeline/backend` (`GET /api/blobs/{...}`,
autenticado por `PIPELINE_API_KEY`) e os repassa ao aluno autenticado, com
cache HTTP de longo prazo — o blob é endereçado por SHA-256, então o mesmo
`item_id` sempre aponta para os mesmos bytes.

O caminho do blob (`{sha256}.{ext}`) chega até aqui em
`questao.recursos.imagens[].arquivo`, preenchido por
`pipeline/backend/figure_extractor.py` (extração determinística via PyMuPDF,
sem Gemini) e propagado pelo espelho Firestore -> `questoes_public` como
qualquer outro campo de `recursos`.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response

import settings
from auth import require_user
from models import User

logger = logging.getLogger("sapiens.exam_images")

router = APIRouter(prefix="", tags=["exam-images"])

_db = None


def set_db(db) -> None:
    global _db
    _db = db


_CACHE_CONTROL = "public, max-age=31536000, immutable"


def _first_figure_path(doc: dict | None) -> str | None:
    if not doc:
        return None
    imagens = ((doc.get("questao") or {}).get("recursos") or {}).get("imagens") or []
    for img in imagens:
        if isinstance(img, dict) and img.get("arquivo"):
            return img["arquivo"]
    return None


@router.get("/exam-images/{item_id}")
async def get_exam_image(item_id: str, user: User = Depends(require_user)) -> Response:
    doc = await _db.questoes_public.find_one(
        {"item_id": item_id}, {"_id": 0, "questao.recursos.imagens": 1}
    )
    arquivo = _first_figure_path(doc)
    if not arquivo:
        raise HTTPException(status_code=404, detail="Questão sem figura.")

    if not settings.PIPELINE_URL or not settings.PIPELINE_API_KEY:
        raise HTTPException(status_code=503, detail="Entrega de imagens não configurada.")

    url = f"{settings.PIPELINE_URL.rstrip('/')}/api/blobs/{arquivo}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"X-API-Key": settings.PIPELINE_API_KEY})
    except httpx.HTTPError as exc:
        logger.warning("Falha ao buscar figura do pipeline (item %s): %s", item_id, exc)
        raise HTTPException(status_code=502, detail="Falha ao buscar imagem.") from exc

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Figura não encontrada no storage.")
    if resp.status_code != 200:
        logger.warning(
            "Pipeline devolveu %s ao buscar figura do item %s", resp.status_code, item_id
        )
        raise HTTPException(status_code=502, detail="Falha ao buscar imagem.")

    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "image/webp"),
        headers={"Cache-Control": _CACHE_CONTROL},
    )
