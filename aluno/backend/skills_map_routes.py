"""Mapa de Habilidades — endpoint cosmético de gamificação (aba Cognitivo).

Gera um resumo visual GENÉRICO de progresso (hexágono de 6 eixos + árvore de
itens, sem nomes reais da ontologia) a partir do mesmo agregado de processos
respondidos que `/cognitive-profile` já calcula — ver `cosmetic_skills_map`.
Cada geração custa Sparks (mecânica de jogo, não medida pedagógica) e também
recalcula o resumo de feedback (pontos fortes / pontos de atenção), baseado
no histórico de resumos de rodada (`students/{uid}/sparks_rounds`).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

import rate_limit
from auth import require_user
from models import User
import annotation_service
import firestore_service as fs
from cosmetic_skills_map import HUBS, build_hub_tree, compute_feedback, compute_hexagon

logger = logging.getLogger("sapiens.skills_map")


def _safe_reembolso(uid: str, cost: int):
    """Devolver os Sparks não pode virar um segundo erro em cima do
    primeiro: se até a compensação falhar, o log do `except` externo é o
    que resta para a conciliação manual."""
    try:
        return fs.refund_sparks(uid, cost)
    except Exception:  # noqa: BLE001
        logger.exception("REEMBOLSO FALHOU: %d Sparks devidos a %s.", cost, uid)
        return None

router = APIRouter(prefix="", tags=["skills-map"])

# Economia de Sparks 2026-09: "Feedback geral da trilha/habilidade" custa 20
# Sparks, flat, 1ª geração e as seguintes — substitui o esquema temporário
# anterior (achatado em 10 enquanto o mapa estava em validação).
SKILLS_MAP_FIRST_COST = 20
SKILLS_MAP_COST = 20

_ZERO_HEXAGON = [{"hub": h["hub"], "label": h["label"], "mastery": 0.0} for h in HUBS]


def _next_cost(existing: dict | None) -> int:
    return SKILLS_MAP_COST if existing and existing.get("hexagon") else SKILLS_MAP_FIRST_COST


@router.get("/skills-map")
async def get_skills_map(user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    saldo = fs.ensure_sparks_balance(user.user_id)
    snap = fs.read_skills_map(user.user_id) or {}
    hexagon = snap.get("hexagon") or _ZERO_HEXAGON
    return {
        "hubs": build_hub_tree(user.user_id, hexagon),
        "hexagon": snap.get("hexagon"),
        "feedback": snap.get("feedback"),
        "updated_at": snap.get("updated_at"),
        "sparks_balance": saldo,
        "cost": _next_cost(snap),
    }


@router.post("/skills-map/generate")
async def generate_skills_map(
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    fs.ensure_sparks_balance(user.user_id)
    existing = fs.read_skills_map(user.user_id)
    cost = _next_cost(existing)
    try:
        saldo = fs.deduct_sparks(user.user_id, cost)
    except fs.InsufficientSparksError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        )

    # O débito acontece ANTES do trabalho (é ele que autoriza gastar o
    # recurso). Se o trabalho falhar depois — Firestore instável, timeout —, o
    # aluno ficava sem os Sparks E sem o mapa, e Sparks são comprados com
    # dinheiro real. A compensação devolve exatamente o que foi cobrado.
    try:
        profile = await annotation_service.compute_cognitive_profile(user.user_id)
        hexagon = compute_hexagon(profile["ontology_tree"])
        rounds_history = fs.list_sparks_rounds(user.user_id, limit=200)
        feedback = compute_feedback(rounds_history, profile["domain_stats"])
        updated_at = fs.write_skills_map(user.user_id, hexagon, feedback)
    except Exception as exc:  # noqa: BLE001
        saldo_restituido = _safe_reembolso(user.user_id, cost)
        logger.exception(
            "Geração do mapa falhou para %s — %d Sparks devolvidos (saldo: %s).",
            user.user_id, cost, saldo_restituido,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível gerar o mapa agora. Seus Sparks foram devolvidos.",
        ) from exc

    return {
        "hubs": build_hub_tree(user.user_id, hexagon),
        "hexagon": hexagon,
        "feedback": feedback,
        "updated_at": updated_at,
        "sparks_balance": saldo,
        "cost": _next_cost(fs.read_skills_map(user.user_id)),
    }
