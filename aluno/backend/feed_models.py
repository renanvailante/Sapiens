"""Learning feed: flexible content models prepared for future cognitive integration.

Cognitive variables, question taxonomy and difficulty scoring are OWNED by the
AI/research team and will be plugged in later via `cognitive_mapping_reference`
and `difficulty_reference`. This module only builds the software foundation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FeedItem(BaseModel):
    """A single unit of learning content displayed on one full-screen card.

    Every field except `content_id` / `content_type` / `sequence_order` is a
    forward-compatible placeholder. Future ingestion pipelines populate them.
    """
    content_id: str = Field(default_factory=_uuid)
    content_type: str  # "question" | "flashcard" | "video" | "diagram" | "explanation"
    sequence_order: int = 0

    # Flexible payloads — schemas may evolve without breaking the feed
    question_data: dict[str, Any] = Field(default_factory=dict)   # {prompt, image_url, video_url, ...}
    answer_options: list[dict[str, Any]] = Field(default_factory=list)   # [{key, label, is_correct?}]
    explanation_data: dict[str, Any] = Field(default_factory=dict)  # {text, media}
    multimedia_assets: list[dict[str, Any]] = Field(default_factory=list)  # [{type, url, caption}]
    metadata: dict[str, Any] = Field(default_factory=dict)

    # References into the future cognitive engine. Empty strings for now.
    cognitive_mapping_reference: str = ""
    difficulty_reference: str = ""
    learning_objectives: list[str] = Field(default_factory=list)

    # Presentation
    background_theme: str = "slate"  # slate | violet | emerald | amber | rose | ocean
    published: bool = True
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class FeedInteraction(BaseModel):
    """Raw interaction event. No interpretation is performed here."""
    interaction_id: str = Field(default_factory=_uuid)
    user_id: str
    content_id: str
    time_spent_ms: int = 0
    completed: bool = False
    user_response: dict[str, Any] = Field(default_factory=dict)  # e.g. {selected: "B"} or {flipped: true}
    is_correct: bool | None = None
    interaction_history: list[dict[str, Any]] = Field(default_factory=list)  # e.g. [{event, at, ...}]
    created_at: str = Field(default_factory=_now)


class FeedProgress(BaseModel):
    """User's cursor through the feed."""
    user_id: str
    last_position: int = 0
    last_content_id: str | None = None
    completed_content_ids: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=_now)


# ---------- Request schemas ----------

class FeedInteractionIn(BaseModel):
    content_id: str
    time_spent_ms: int = 0
    completed: bool = False
    user_response: dict[str, Any] = Field(default_factory=dict)
    is_correct: bool | None = None
    event: dict[str, Any] | None = None  # optional single event to append


class FeedProgressIn(BaseModel):
    last_position: int
    last_content_id: str | None = None


class FeedItemIn(BaseModel):
    """Admin create/update payload."""
    content_type: str
    sequence_order: int = 0
    question_data: dict[str, Any] = Field(default_factory=dict)
    answer_options: list[dict[str, Any]] = Field(default_factory=list)
    explanation_data: dict[str, Any] = Field(default_factory=dict)
    multimedia_assets: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    cognitive_mapping_reference: str = ""
    difficulty_reference: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    background_theme: str = "slate"
    published: bool = True
