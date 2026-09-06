"""`GET /perfil` — a única visão de desempenho cognitivo que o app do aluno
serve ao cliente. Ver `perfil_pedagogico.py`: nenhum campo da resposta
carrega nome ou ID interno da ontologia, nem percentual."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth import require_user
from models import User
import firestore_service as fs
import perfil_pedagogico

router = APIRouter(prefix="", tags=["perfil-publico"])


@router.get("/perfil")
async def get_perfil(user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    return await perfil_pedagogico.perfil_publico(user.user_id)
