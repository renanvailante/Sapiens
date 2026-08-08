"""Response Event Store — the single, permanent, append-only source of truth
for student answer history.

Two separate event types (never mixed):
- StudentResponseEvent: observed behavior only. No cognitive fields duplicated.
- StudentInterventionEvent: pedagogical action, keyed to the student, decoupled
  in time from the response.

Observability layer JOINs these with the immutable ITEM annotations. Neither
this module nor consumers rewrite events — status transitions produce NEW
events with the same attempt_id.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Response Event ----------

class ResponseContext(BaseModel):
    model_config = ConfigDict(extra="allow")
    avaliacao_id: str | None = None
    sessao_id: str | None = None
    origem: str | None = None  # simulado | revisao | prova | diagnostico | tarefa
    versao_prova: str | None = None


class ResponseTech(BaseModel):
    model_config = ConfigDict(extra="allow")
    device: str | None = None
    platform: str | None = None
    latencia_ms: int | None = None
    versao_app: str | None = None


class StudentResponseEvent(BaseModel):
    """Immutable. Append-only. Never edited after write."""
    model_config = ConfigDict(extra="allow")

    evento_id: str = Field(default_factory=_uuid)
    attempt_id: str  # groups response + correction + retry for the same question
    aluno_id: str
    turma: str | None = None

    item_id: str  # ITEM-ENEM-YYYY-...
    item_schema_version: str
    item_hash: str  # sha256 hash of item content at response time (client-provided)

    contexto: ResponseContext = Field(default_factory=ResponseContext)

    data_hora_resposta: str  # ISO 8601 timestamp
    alternativa_escolhida: str  # A|B|C|D|E
    acertou: bool  # strict comparison to item.gabarito (computed by client from item)
    tempo_resposta_seg: float

    status: str = "respondida"  # respondida | anulada | corrigida | cancelada
    metadata_tecnica: ResponseTech = Field(default_factory=ResponseTech)

    # Server-side write timestamp — separate from data_hora_resposta which is
    # when the student actually answered.
    written_at: str = Field(default_factory=_now_iso)


# ---------- Intervention Event ----------

class StudentInterventionEvent(BaseModel):
    """Immutable. Separate collection. May occur days/months after the response."""
    model_config = ConfigDict(extra="allow")

    evento_id: str = Field(default_factory=_uuid)
    aluno_id: str
    cognitive_process_id: str  # references item.pedagogia.principal_intervencao
    tipo_intervencao: str
    data_hora_aplicacao: str  # ISO 8601
    aplicada_por: str  # e.g. "professor:jane@school.com" or "sistema:auto"

    # Optional back-reference — never used to mutate a response event
    linked_evento_id: str | None = None

    written_at: str = Field(default_factory=_now_iso)


# ---------- Request schemas ----------

class ResponseEventIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    attempt_id: str | None = None
    aluno_id: str
    turma: str | None = None
    item_id: str
    item_schema_version: str
    item_hash: str
    contexto: dict[str, Any] = Field(default_factory=dict)
    data_hora_resposta: str
    alternativa_escolhida: str
    acertou: bool
    tempo_resposta_seg: float
    status: str = "respondida"
    metadata_tecnica: dict[str, Any] = Field(default_factory=dict)


class InterventionEventIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    aluno_id: str
    cognitive_process_id: str
    tipo_intervencao: str
    data_hora_aplicacao: str
    aplicada_por: str
    linked_evento_id: str | None = None


class BulkResponsesIn(BaseModel):
    events: list[ResponseEventIn]
