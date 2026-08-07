"""Read helpers that expose the annotation layer to any platform feature.

Rule: NEVER mutate the annotation. Just query and aggregate observed
performance on the client (student) side.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from cognitive_ontology import build_ontology_tree


_db = None
def set_db(db):
    global _db
    _db = db


async def find_annotation_for_question(banca: str, ano: int, caderno: str, numero: int) -> dict | None:
    return await _db.question_annotations.find_one(
        {"banca": banca, "ano": ano, "caderno": caderno, "numero": numero},
        {"_id": 0},
    )


async def find_annotation_by_id(item_id: str) -> dict | None:
    return await _db.question_annotations.find_one({"item_id": item_id}, {"_id": 0})


async def list_annotations(filters: dict | None = None, limit: int = 500) -> list[dict]:
    q = filters or {}
    cursor = _db.question_annotations.find(q, {"_id": 0}).sort("received_at", -1).limit(limit)
    return await cursor.to_list(limit)


async def compute_cognitive_profile(user_id: str) -> dict[str, Any]:
    """Aggregate per-cognitive-process performance for a user across all attempts.

    Reads annotations verbatim. Uses `peso_ativacao` provided by the AI as the
    weight — never overrides it. Only queries and counts.
    """
    analyses = await _db.analyses.find({"user_id": user_id, "deleted": False}, {"_id": 0}).to_list(500)
    if not analyses:
        return {"processes": [], "error_types": [], "misconceptions": [], "coverage": 0,
                "ontology_tree": build_ontology_tree(set())}

    # Preload the exam metadata to know banca/ano/caderno
    exam_ids = list({a["exam_id"] for a in analyses})
    exams = await _db.exams.find({"exam_id": {"$in": exam_ids}}, {"_id": 0}).to_list(500)
    exam_by_id = {e["exam_id"]: e for e in exams}

    process_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "encountered": 0, "correct": 0,
        "weight_sum": 0.0, "weight_correct": 0.0,
        "difficulty_local_sum": 0.0,
        "papel_counts": defaultdict(int),
    })
    error_type_counter: dict[int, int] = defaultdict(int)
    misconception_counter: dict[str, int] = defaultdict(int)
    matched_questions = 0
    total_questions = 0

    for analysis in analyses:
        exam = exam_by_id.get(analysis["exam_id"])
        if not exam:
            continue
        banca = exam.get("provider", "ENEM")
        ano = exam["year"]
        caderno = exam["color"]

        # Build per-answer chosen letter lookup
        chosen_by_num = {a["number"]: (a.get("letter") or "").upper() for a in analysis["answers"]}
        # And correct-map from the answer key (reload; keys are cached by exam)
        key = await _db.answer_keys.find_one({"exam_id": exam["exam_id"], "language": analysis.get("language", "english")}, {"_id": 0})
        correct_map = {a["number"]: a["letter"].upper() for a in (key["answers"] if key else [])}

        for number, chosen in chosen_by_num.items():
            total_questions += 1
            ann = await find_annotation_for_question(banca, ano, caderno, number)
            if not ann:
                continue
            matched_questions += 1
            correct_letter = correct_map.get(number, "")
            hit = (chosen == correct_letter) and bool(chosen)

            payload = ann["payload"]
            for proc in payload.get("processos_ativados", []) or []:
                pid = proc.get("cognitive_process_id")
                if not pid:
                    continue
                st = process_stats[pid]
                weight = float(proc.get("peso_ativacao", 1.0) or 0.0)
                st["encountered"] += 1
                st["weight_sum"] += weight
                st["difficulty_local_sum"] += float(proc.get("dificuldade_local", 0.0) or 0.0)
                if proc.get("papel"):
                    st["papel_counts"][proc["papel"]] += 1
                if hit:
                    st["correct"] += 1
                    st["weight_correct"] += weight

            if not hit and chosen:
                # Find distractor info
                for d in payload.get("analise_distratores", []) or []:
                    if d.get("alternativa") == chosen and d.get("error_type_id") is not None:
                        error_type_counter[int(d["error_type_id"])] += 1
                # Surface misconceptions from pedagogia
                pedagogia = payload.get("pedagogia") or {}
                for m in pedagogia.get("misconceptions", []) or []:
                    misconception_counter[m] += 1

    processes = []
    for pid, st in process_stats.items():
        n = st["encountered"]
        acc = round(100 * st["correct"] / n, 1) if n else 0.0
        weighted_acc = round(100 * st["weight_correct"] / st["weight_sum"], 1) if st["weight_sum"] else 0.0
        processes.append({
            "cognitive_process_id": pid,
            "encountered": n,
            "correct": st["correct"],
            "accuracy": acc,
            "weighted_accuracy": weighted_acc,
            "avg_local_difficulty": round(st["difficulty_local_sum"] / n, 2) if n else 0.0,
            "papel_distribution": dict(st["papel_counts"]),
        })
    processes.sort(key=lambda x: (-x["encountered"], x["cognitive_process_id"]))

    error_types = [{"error_type_id": k, "count": v} for k, v in sorted(error_type_counter.items(), key=lambda kv: -kv[1])]
    misconceptions = [{"label": k, "count": v} for k, v in sorted(misconception_counter.items(), key=lambda kv: -kv[1])]

    return {
        "processes": processes,
        "error_types": error_types,
        "misconceptions": misconceptions,
        "coverage": round(100 * matched_questions / total_questions, 1) if total_questions else 0.0,
        "matched_questions": matched_questions,
        "total_questions": total_questions,
        "ontology_tree": build_ontology_tree(set(process_stats.keys())),
    }
