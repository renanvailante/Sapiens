"""Exam & analysis routes."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from auth import require_user
from ai_service import diagnose, ocr_answer_sheet, tag_question
from models import (
    Analysis,
    Exam,
    ImportExamRequest,
    Question,
    SubmitExamRequest,
    User,
    UserAnswer,
    VisionOCRRequest,
)

router = APIRouter(prefix="", tags=["exams"])

_db = None
def set_db(db):
    global _db
    _db = db


@router.get("/exams")
async def list_exams():
    docs = await _db.exams.find({}, {"_id": 0}).sort([("year", -1), ("color", 1)]).to_list(200)
    return docs


@router.get("/exams/{exam_id}")
async def get_exam(exam_id: str):
    exam = await _db.exams.find_one({"exam_id": exam_id}, {"_id": 0})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    questions = await _db.questions.find({"exam_id": exam_id}, {"_id": 0, "correct_answer": 0, "tags": 0}).sort("number", 1).to_list(500)
    return {"exam": exam, "questions": questions}


@router.get("/exams/{exam_id}/full")
async def get_exam_full(exam_id: str, user: User = Depends(require_user)):
    """Full exam with answers/tags — for admin & review after submission."""
    exam = await _db.exams.find_one({"exam_id": exam_id}, {"_id": 0})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    questions = await _db.questions.find({"exam_id": exam_id}, {"_id": 0}).sort("number", 1).to_list(500)
    return {"exam": exam, "questions": questions}


@router.post("/vision/answer-sheet")
async def vision_ocr(payload: VisionOCRRequest, user: User = Depends(require_user)):
    exam = await _db.exams.find_one({"exam_id": payload.exam_id}, {"_id": 0})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    try:
        answers = await ocr_answer_sheet(payload.image_base64, exam["total_questions"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision error: {e}")
    # Ensure all numbers 1..N are present
    got = {a.get("number"): (a.get("letter") or "").upper() for a in answers}
    normalized = [{"number": i, "letter": got.get(i, "")} for i in range(1, exam["total_questions"] + 1)]
    return {"answers": normalized}


@router.post("/analyses")
async def submit_analysis(payload: SubmitExamRequest, user: User = Depends(require_user)):
    exam = await _db.exams.find_one({"exam_id": payload.exam_id}, {"_id": 0})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    questions = await _db.questions.find({"exam_id": payload.exam_id}, {"_id": 0}).sort("number", 1).to_list(500)

    correct_count = 0
    by_area: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    by_tag: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    errors_detail: list[dict[str, Any]] = []
    # Normalize incoming answers
    user_map = {a.question_id: (a.letter or "").upper() for a in payload.answers}
    total = len(questions)
    for q in questions:
        # We stored answers by question_id from frontend when questions returned
        chosen = user_map.get(q["question_id"], "")
        area = q["area"]
        by_area[area]["total"] += 1
        # collect boolean/categorical tags
        tag_keys = ["algebra", "geometria", "funcoes", "estatistica", "probabilidade",
                    "proporcionalidade", "modelagem", "interpretacao_textual",
                    "interpretacao_grafico", "interpretacao_tabela", "visualizacao_espacial",
                    "raciocinio_logico", "memorizacao", "pegadinha"]
        active_tags = [k for k in tag_keys if q.get("tags", {}).get(k)]
        for tk in active_tags:
            by_tag[tk]["total"] += 1
        if chosen == q["correct_answer"]:
            correct_count += 1
            by_area[area]["correct"] += 1
            for tk in active_tags:
                by_tag[tk]["correct"] += 1
        else:
            errors_detail.append({
                "number": q["number"],
                "area": area,
                "topic": q["topic"],
                "subject": q["subject"],
                "chosen": chosen,
                "correct": q["correct_answer"],
                "tags": q.get("tags", {}),
                "difficulty": q.get("difficulty", "medio"),
            })

    percent = round(100 * correct_count / total, 1) if total else 0.0

    # Ask AI to diagnose
    payload_for_ai = {
        "prova": exam["title"],
        "total": total,
        "acertos": correct_count,
        "por_area": dict(by_area),
        "por_etiqueta": dict(by_tag),
        "erros": errors_detail,
    }
    ai_out = await diagnose(payload_for_ai)

    analysis = Analysis(
        user_id=user.user_id,
        exam_id=payload.exam_id,
        exam_label=exam["title"],
        answers=[UserAnswer(**a.model_dump()) for a in payload.answers],
        score=correct_count,
        total=total,
        percent=percent,
        by_area=dict(by_area),
        by_tag=dict(by_tag),
        diagnostic_headline=ai_out.get("headline", ""),
        diagnostic_body=ai_out.get("body", ""),
        strengths=ai_out.get("strengths", []),
        weaknesses=ai_out.get("weaknesses", []),
        cognitive_profile=ai_out.get("cognitive_profile", {}),
        study_plan=ai_out.get("study_plan", []),
        learning_map=ai_out.get("learning_map", {"nodes": [], "edges": []}),
        error_patterns=[e["topic"] for e in errors_detail],
    )
    await _db.analyses.insert_one(analysis.model_dump())
    return analysis.model_dump()


@router.get("/analyses")
async def list_analyses(user: User = Depends(require_user)):
    docs = await _db.analyses.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, user: User = Depends(require_user)):
    doc = await _db.analyses.find_one({"analysis_id": analysis_id, "user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return doc


# ---------- Admin (import new exams) ----------

@router.post("/admin/import-exam")
async def import_exam(payload: ImportExamRequest, user: User = Depends(require_user)):
    exam = Exam(
        provider=payload.provider,
        year=payload.year,
        color=payload.color,
        area=payload.area,
        title=payload.title,
        total_questions=len(payload.questions),
    )
    await _db.exams.insert_one(exam.model_dump())
    for qraw in payload.questions:
        # Auto-tag via AI if tags missing
        tags = qraw.get("tags") or await tag_question(qraw["statement"], qraw["alternatives"], qraw["correct_answer"])
        q = Question(
            exam_id=exam.exam_id,
            number=qraw["number"],
            area=qraw["area"],
            subject=qraw.get("subject", ""),
            topic=qraw.get("topic", ""),
            statement=qraw["statement"],
            alternatives=qraw["alternatives"],
            correct_answer=qraw["correct_answer"],
            tags=tags,
            difficulty=qraw.get("difficulty", "medio"),
            competency=qraw.get("competency"),
        )
        await _db.questions.insert_one(q.model_dump())
    return {"exam_id": exam.exam_id, "total": len(payload.questions)}
