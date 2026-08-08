"""Sapiens data models — Answer-Key-only schema (v2).

Exams no longer store questions or alternatives. Each exam holds official
answer keys in English and/or Spanish, keyed by question number.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, Field, EmailStr


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Users ----------

class User(BaseModel):
    user_id: str = Field(default_factory=lambda: f"user_{uuid.uuid4().hex[:12]}")
    email: EmailStr
    name: str
    picture: str | None = None
    provider: str = "email"
    password_hash: str | None = None
    is_admin: bool = False
    created_at: str = Field(default_factory=_now_iso)


class UserSession(BaseModel):
    session_id: str = Field(default_factory=_uuid)
    user_id: str
    session_token: str
    expires_at: str
    created_at: str = Field(default_factory=_now_iso)


# ---------- ENEM Answer-Key model ----------

AREA_LABELS = {
    "LC-Idioma": "Língua estrangeira",
    "LC": "Linguagens e Códigos",
    "CH": "Ciências Humanas",
    "CN": "Ciências da Natureza",
    "MT": "Matemática",
}


def area_for(day: int, number: int) -> str:
    """Map (day, question number) → area code using the standard ENEM layout.

    Day 1: 1-5 language, 6-45 Portuguese/Arts/PE, 46-90 CH.
    Day 2: 91-135 CN, 136-180 MT (or 1-45/46-90 if paste re-numbered from 1).
    """
    n = int(number)
    if day == 1:
        if 1 <= n <= 5:
            return "LC-Idioma"
        if 6 <= n <= 45:
            return "LC"
        return "CH"
    # day 2
    if 91 <= n <= 135:
        return "CN"
    if 136 <= n <= 180:
        return "MT"
    # re-numbered from 1
    if 1 <= n <= 45:
        return "CN"
    return "MT"


class AnswerKeyItem(BaseModel):
    number: int
    letter: str  # A-E, "*" means annulled / no valid answer


class Exam(BaseModel):
    exam_id: str = Field(default_factory=_uuid)
    provider: str = "ENEM"
    year: int
    day: int  # 1 or 2
    color: str  # Azul, Amarela, Branca, Cinza, Rosa, ...
    title: str
    total_questions: int
    has_english: bool = False
    has_spanish: bool = False
    created_at: str = Field(default_factory=_now_iso)


class AnswerKey(BaseModel):
    key_id: str = Field(default_factory=_uuid)
    exam_id: str
    language: str  # "english" | "spanish"
    answers: list[AnswerKeyItem]
    created_at: str = Field(default_factory=_now_iso)


# ---------- User answers & analysis ----------

class UserAnswer(BaseModel):
    number: int
    letter: str  # A-E or "" if blank


class Analysis(BaseModel):
    analysis_id: str = Field(default_factory=_uuid)
    user_id: str
    exam_id: str
    exam_label: str
    label: str | None = None  # user-customisable name
    language: str
    answers: list[UserAnswer]
    score: int = 0
    total: int = 0
    percent: float = 0.0
    by_area: dict[str, dict[str, int]] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)  # [{number, area, chosen, correct}]
    diagnostic_headline: str = ""
    diagnostic_body: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    cognitive_profile: dict[str, float] = Field(default_factory=dict)
    study_plan: list[dict[str, Any]] = Field(default_factory=list)
    learning_map: dict[str, Any] = Field(default_factory=dict)
    deleted: bool = False
    deleted_at: str | None = None
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
    language: str  # "english" | "spanish"
    answers: list[UserAnswer]


class VisionOCRRequest(BaseModel):
    exam_id: str
    image_base64: str


class PasteAnswerKeyRequest(BaseModel):
    provider: str = "ENEM"
    year: int
    day: int  # 1 or 2
    color: str
    raw_text: str  # pasted content from INEP
