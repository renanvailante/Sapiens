"""Diagnóstico real do aluno — desempenho medido por domínio/competência/
processo, com nomes reais da ontologia e amostra mínima declarada.

Diferente de `/skills-map` (cosmético, custa Sparks, esconde nomes reais por
decisão de produto): esta rota é gratuita, porque é leitura/agregação
determinística sobre dados que o aluno já gerou respondendo questões — não é
geração de conteúdo nem mecânica de jogo.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth import require_user
from models import User
import annotation_service
import firestore_service as fs

router = APIRouter(prefix="", tags=["diagnostico"])


@router.get("/diagnostico")
async def get_diagnostico(user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    return await annotation_service.compute_diagnostico_real(user.user_id)
