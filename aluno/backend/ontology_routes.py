"""Ontology routes: expose the 5-level cognitive framework."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/ontology", tags=["ontology"])

_db = None
def set_db(db):
    global _db
    _db = db


@router.get("")
async def get_ontology():
    """Return the full 5-level ontology tree.

    Levels 1-3 are curated from literature.
    Level 4 are operational hypotheses.
    Level 5 (indicators) is empirical — its stats grow with each attempt.
    """
    domains = await _db.ontology_domains.find({}, {"_id": 0}).to_list(200)
    competences = await _db.ontology_competences.find({}, {"_id": 0}).to_list(500)
    processes = await _db.ontology_processes.find({}, {"_id": 0}).to_list(500)
    skills = await _db.ontology_skills.find({}, {"_id": 0}).to_list(500)
    indicators = await _db.ontology_indicators.find({}, {"_id": 0}).to_list(500)

    return {
        "levels": {
            "1": {"name": "Domínio Cognitivo",
                  "origin": "Derivado diretamente da literatura consolidada",
                  "evidence": "very_high",
                  "items": domains},
            "2": {"name": "Competência",
                  "origin": "Síntese ontológica baseada em múltiplos modelos teóricos",
                  "evidence": "high",
                  "items": competences},
            "3": {"name": "Processo Cognitivo",
                  "origin": "Decomposição operacional apoiada pela literatura",
                  "evidence": "medium_high",
                  "items": processes},
            "4": {"name": "Habilidade Observável",
                  "origin": "Derivação operacional voltada à mensuração",
                  "evidence": "medium",
                  "items": skills},
            "5": {"name": "Indicador Comportamental",
                  "origin": "Definição empírica baseada em dados do sistema",
                  "evidence": "empirical",
                  "items": indicators},
        }
    }


@router.get("/indicators")
async def get_indicators():
    """Level-5 empirical indicators, ordered by evidence strength."""
    items = await _db.ontology_indicators.find({}, {"_id": 0}).sort("confidence", -1).to_list(500)
    return items
