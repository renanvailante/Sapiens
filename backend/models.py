"""Sapiens data models."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, Field, EmailStr


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class User(BaseModel):
    user_id: str = Field(default_factory=lambda: f"user_{uuid.uuid4().hex[:12]}")
    email: EmailStr
    name: str
    picture: str | None = None
    provider: str = "email"  # email | google
    password_hash: str | None = None
    created_at: str = Field(default_factory=_now_iso)


class UserSession(BaseModel):
    session_id: str = Field(default_factory=_uuid)
    user_id: str
    session_token: str
    expires_at: str
    created_at: str = Field(default_factory=_now_iso)


# ---------- ENEM domain ----------

AREAS = {
    "MT": "Matemática",
    "CN": "Ciências da Natureza",
    "CH": "Ciências Humanas",
    "LC": "Linguagens e Códigos",
}


class Alternative(BaseModel):
    letter: str  # A, B, C, D, E
    text: str


class Question(BaseModel):
    question_id: str = Field(default_factory=_uuid)
    exam_id: str
    number: int
    area: str  # MT, CN, CH, LC
    subject: str  # e.g., "Álgebra"
    topic: str
    statement: str
    alternatives: list[Alternative]
    correct_answer: str
    image_url: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)  # AI-generated tags
    difficulty: str = "medio"  # facil, medio, dificil
    competency: int | None = None  # ENEM competency
    ability: int | None = None  # ENEM ability
    expected_time_seconds: int = 180


class Exam(BaseModel):
    exam_id: str = Field(default_factory=_uuid)
    provider: str = "ENEM"  # ENEM, FUVEST, etc.
    year: int
    color: str  # Azul, Amarela, Branca, Cinza
    area: str  # Whole day: LC+CH or MT+CN
    title: str
    total_questions: int
    created_at: str = Field(default_factory=_now_iso)


class UserAnswer(BaseModel):
    question_id: str
    letter: str  # A-E or "" if blank


class Analysis(BaseModel):
    analysis_id: str = Field(default_factory=_uuid)
    user_id: str
    exam_id: str
    exam_label: str
    answers: list[UserAnswer]
    score: int = 0
    total: int = 0
    percent: float = 0.0
    by_area: dict[str, dict[str, int]] = Field(default_factory=dict)  # area -> {correct, total}
    by_tag: dict[str, dict[str, int]] = Field(default_factory=dict)   # tag_group -> {correct, total, ...}
    error_patterns: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    diagnostic_headline: str = ""
    diagnostic_body: str = ""
    cognitive_profile: dict[str, float] = Field(default_factory=dict)  # trait -> 0-100
    study_plan: list[dict[str, Any]] = Field(default_factory=list)  # ordered items
    learning_map: dict[str, Any] = Field(default_factory=dict)  # nodes/edges
    created_at: str = Field(default_factory=_now_iso)


# ---------- Request / Response schemas ----------

class SignupRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SubmitExamRequest(BaseModel):
    exam_id: str
    answers: list[UserAnswer]


class VisionOCRRequest(BaseModel):
    exam_id: str
    image_base64: str  # data URL or bare base64


class ImportExamRequest(BaseModel):
    provider: str = "ENEM"
    year: int
    color: str
    area: str
    title: str
    questions: list[dict[str, Any]]
