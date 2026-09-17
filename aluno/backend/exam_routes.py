"""Exam & analysis routes — answer-key based, with recycle bin."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import logging

import rate_limit
import settings
from auth import require_admin, require_user
from ai_service import GeminiIndisponivelError, diagnose, ocr_answer_sheet
import firestore_service as fs
from enem_seed import import_pasted_key
from models import (
    Analysis,
    PasteAnswerKeyRequest,
    SubmitExamRequest,
    User,
    UserAnswer,
    VisionOCRRequest,
    area_for,
)

logger = logging.getLogger("sapiens.exams")

router = APIRouter(prefix="", tags=["exams"])

_db = None
def set_db(db):
    global _db
    _db = db


class RenameRequest(BaseModel):
    label: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Exams ----------

@router.get("/exams")
async def list_exams():
    docs = await _db.exams.find({}, {"_id": 0}).sort([("year", -1), ("day", 1), ("color", 1)]).to_list(500)
    return docs


@router.get("/exams/{exam_id}")
async def get_exam(exam_id: str, language: str = Query("english")):
    exam = await _db.exams.find_one({"exam_id": exam_id}, {"_id": 0})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    key = await _db.answer_keys.find_one({"exam_id": exam_id, "language": language}, {"_id": 0})
    if not key:
        key = await _db.answer_keys.find_one({"exam_id": exam_id, "language": "english"}, {"_id": 0})
        if not key:
            raise HTTPException(status_code=404, detail="Answer key not found")
    numbers = [a["number"] for a in key["answers"]]
    return {"exam": exam, "language": key["language"], "numbers": numbers}


# ---------- Custo das duas chamadas de IA desta rota ----------
#
# As duas eram gratuitas até 17/09. A do cartão-resposta é a mesma classe de
# trabalho que o OCR da redação manuscrita, que já custa
# `redacao_routes.DIGITALIZACAO_COST` (25) — cobrar uma e não a outra era só
# inconsistência. A do diagnóstico do simulado é uma chamada longa de texto,
# na faixa das outras devolutivas da Mentis.
OCR_CARTAO_COST = 25
DIAGNOSTICO_SIMULADO_COST = 40


def _safe_reembolso(uid: str, custo: int) -> int | None:
    try:
        return fs.refund_sparks(uid, custo)
    except Exception:  # noqa: BLE001
        logger.exception("REEMBOLSO FALHOU (exams): %d Sparks devidos a %s.", custo, uid)
        return None


def _cobrar(uid: str, custo: int) -> int:
    fs.ensure_sparks_balance(uid)
    try:
        return fs.deduct_sparks(uid, custo)
    except fs.InsufficientSparksError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        ) from exc


# ---------- Vision ----------

@router.post("/vision/answer-sheet")
async def vision_ocr(
    payload: VisionOCRRequest,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    """OCR do cartão-resposta.

    `MAX_UPLOAD_BYTES` existia em `settings.py` e não era usado em lugar
    nenhum: a rota aceitava base64 de qualquer tamanho dentro de um JSON. Uma
    foto de 12 MP vira ~11 MB de base64 na memória de uma VM de 512 MB que
    aceita 80 requisições simultâneas — alguns envios juntos derrubavam a
    instância. O frontend agora redimensiona antes de enviar; esta checagem é
    a rede de segurança do servidor, que não depende do cliente colaborar.
    """
    tamanho = len(payload.image_base64 or "")
    if tamanho > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Imagem grande demais ({tamanho // (1024 * 1024)} MB). "
                f"O limite é {settings.MAX_UPLOAD_MB} MB — tire a foto mais de perto "
                "ou use uma resolução menor."
            ),
        )

    exam = await _db.exams.find_one({"exam_id": payload.exam_id}, {"_id": 0})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    key = await _db.answer_keys.find_one({"exam_id": payload.exam_id, "language": "english"}, {"_id": 0})
    if not key:
        raise HTTPException(status_code=404, detail="Answer key not found")
    numbers = [a["number"] for a in key["answers"]]
    if not numbers:
        raise HTTPException(status_code=400, detail="Prova sem gabarito.")
    # Cobrado só aqui: depois de 413/404/400, para nunca debitar por um pedido
    # que ia falhar de graça, e antes da chamada, como nas demais ferramentas.
    saldo = _cobrar(user.user_id, OCR_CARTAO_COST)
    try:
        answers = await ocr_answer_sheet(payload.image_base64, len(numbers), start_number=numbers[0])
    except GeminiIndisponivelError as exc:
        saldo = _safe_reembolso(user.user_id, OCR_CARTAO_COST)
        # Timeout do modelo: o aluno pode tentar de novo ou digitar. Dizer isso
        # é melhor que um 500 genérico depois de uma espera longa.
        raise HTTPException(
            status_code=504,
            detail="A leitura do cartão demorou demais. Tente de novo ou digite as respostas.",
        ) from exc
    except Exception as e:
        saldo = _safe_reembolso(user.user_id, OCR_CARTAO_COST)
        logger.exception("OCR do cartão-resposta falhou para %s", user.user_id)
        raise HTTPException(
            status_code=502,
            detail="Não conseguimos ler o cartão. Tente outra foto ou digite as respostas.",
        ) from e
    got = {a.get("number"): (a.get("letter") or "").upper() for a in answers}
    normalized = [{"number": n, "letter": got.get(n, "")} for n in numbers]
    return {"answers": normalized, "cobrado": OCR_CARTAO_COST, "sparks_balance": saldo}


# ---------- Analyses (attempts) ----------

@router.post("/analyses")
async def submit_analysis(payload: SubmitExamRequest, user: User = Depends(require_user)):
    """Create a new independent attempt. Never overwrites previous attempts."""
    exam = await _db.exams.find_one({"exam_id": payload.exam_id}, {"_id": 0})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    key = await _db.answer_keys.find_one({"exam_id": payload.exam_id, "language": payload.language}, {"_id": 0})
    if not key:
        raise HTTPException(status_code=404, detail="Answer key not found for language")

    correct_map = {a["number"]: a["letter"].upper() for a in key["answers"]}
    user_map = {a.number: (a.letter or "").upper() for a in payload.answers}

    correct_count = 0
    total = len(correct_map)
    by_area: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    errors: list[dict[str, Any]] = []
    day = exam["day"]

    for number, correct_letter in correct_map.items():
        area = area_for(day, number)
        by_area[area]["total"] += 1
        chosen = user_map.get(number, "")
        if correct_letter == "*" or chosen == correct_letter:
            correct_count += 1
            by_area[area]["correct"] += 1
        else:
            errors.append({"number": number, "area": area, "chosen": chosen, "correct": correct_letter})

    percent = round(100 * correct_count / total, 1) if total else 0.0

    ai_payload = {
        "prova": exam["title"], "ano": exam["year"], "dia": day, "cor": exam["color"],
        "idioma": payload.language, "total": total, "acertos": correct_count,
        "percentual": percent, "por_area": dict(by_area), "erros": errors,
    }
    # O diagnóstico por IA do simulado também saía de graça. Cobrado aqui, com
    # a mesma regra das outras ferramentas: se o modelo não entrega e a rota
    # cai no texto de indisponibilidade abaixo, o aluno não paga por ele.
    saldo = _cobrar(user.user_id, DIAGNOSTICO_SIMULADO_COST)
    try:
        ai_out = await diagnose(ai_payload)
    except Exception:
        saldo = _safe_reembolso(user.user_id, DIAGNOSTICO_SIMULADO_COST)
        ai_out = {
            "headline": "Análise recebida. Diagnóstico cognitivo indisponível no momento — tente reprocessar em instantes.",
            "body": "Sua pontuação e desempenho por área foram calculados normalmente. A camada de IA responsável pela leitura de padrões cognitivos não respondeu a tempo.",
            "strengths": [], "weaknesses": [],
            "cognitive_profile": {}, "study_plan": [],
            "learning_map": {"nodes": [], "edges": []},
        }

    exam_label = exam["title"] + (" · English" if payload.language == "english" else " · Español")
    analysis = Analysis(
        user_id=user.user_id,
        exam_id=payload.exam_id,
        exam_label=exam_label,
        language=payload.language,
        answers=[UserAnswer(**a.model_dump()) for a in payload.answers],
        score=correct_count, total=total, percent=percent,
        by_area=dict(by_area), errors=errors,
        diagnostic_headline=ai_out.get("headline", ""),
        diagnostic_body=ai_out.get("body", ""),
        strengths=ai_out.get("strengths", []),
        weaknesses=ai_out.get("weaknesses", []),
        cognitive_profile=ai_out.get("cognitive_profile", {}),
        study_plan=ai_out.get("study_plan", []),
        learning_map=ai_out.get("learning_map", {"nodes": [], "edges": []}),
    )
    await _db.analyses.insert_one(analysis.model_dump())
    return analysis.model_dump()


@router.get("/analyses")
async def list_analyses(user: User = Depends(require_user), trash: bool = Query(False)):
    q = {"user_id": user.user_id, "deleted": trash}
    docs = await _db.analyses.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, user: User = Depends(require_user)):
    doc = await _db.analyses.find_one({"analysis_id": analysis_id, "user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return doc


@router.patch("/analyses/{analysis_id}/rename")
async def rename_analysis(analysis_id: str, payload: RenameRequest, user: User = Depends(require_user)):
    label = (payload.label or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="Nome vazio")
    res = await _db.analyses.update_one(
        {"analysis_id": analysis_id, "user_id": user.user_id},
        {"$set": {"label": label}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"ok": True, "label": label}


@router.post("/analyses/{analysis_id}/trash")
async def trash_analysis(analysis_id: str, user: User = Depends(require_user)):
    res = await _db.analyses.update_one(
        {"analysis_id": analysis_id, "user_id": user.user_id},
        {"$set": {"deleted": True, "deleted_at": _now_iso()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"ok": True}


@router.post("/analyses/{analysis_id}/restore")
async def restore_analysis(analysis_id: str, user: User = Depends(require_user)):
    res = await _db.analyses.update_one(
        {"analysis_id": analysis_id, "user_id": user.user_id},
        {"$set": {"deleted": False, "deleted_at": None}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"ok": True}


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str, user: User = Depends(require_user)):
    res = await _db.analyses.delete_one({"analysis_id": analysis_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"ok": True}


# ---------- Admin: paste answer key ----------

@router.post("/admin/paste-answer-key")
async def paste_answer_key(payload: PasteAnswerKeyRequest, admin: User = Depends(require_admin)):
    try:
        result = await import_pasted_key(
            _db, payload.provider, payload.year, payload.day, payload.color, payload.raw_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result
