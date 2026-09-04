"""Adaptador isolado para a Gemini Batch API (`client.batches`).

**Bloqueio confirmado, não hipotético** (`ai.google.dev/gemini-api/docs/pricing`,
consultado em 2026-08-22): para `gemini-3-flash-preview`, a linha "Batch API"
do Free tier lê literalmente "Not available" — só Tier 1 (billing ativo) para
cima tem cota de Batch. Isto não é uma limitação deste código: é a política
do produto. `submit_batch` detecta a recusa e levanta
`GeminiBatchUnavailableError` com essa causa e a ação concreta (ativar billing
em https://aistudio.google.com/), em vez de deixar vazar um erro genérico da
API.

Cobre apenas o modo *inline* (requisições embutidas na própria chamada de
criação, limite documentado de 20MB por lote) — suficiente para lotes de
algumas dezenas de questões. Um lote maior, ou que precise do modo por
arquivo JSONL via Files API, é uma extensão deste módulo, não deste momento:
não há como validar aquele caminho sem uma conta já em Tier 1.

Preserva o mesmo prompt (schema + ontologia) que o caminho interativo produz
— reaproveita `cognitive_engine.build_system_prompt` e `_ontology_prompt_slice`
para que o resultado do Batch API seja estruturalmente idêntico ao de
`run_cognitive_pipeline`, e passível da mesma normalização (`item_contract.py`).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from cognitive_engine import (
    DEFAULT_PIPELINE_SCHEMA,
    _build_parts,
    _extract_json_object,
    _get_client,
    _get_model,
    _ontology_prompt_slice,
    build_system_prompt,
)

logger = logging.getLogger("sapiens.gemini_batch")

# Limite documentado para requisições inline; folga de 20% sobre o teto real
# (20MB) para não depender de contar bytes de serialização com exatidão.
INLINE_SIZE_SOFT_LIMIT_BYTES = 16 * 1024 * 1024


class GeminiBatchUnavailableError(RuntimeError):
    """Batch API recusado pela API — normalmente por tier sem billing ativo."""

    def __init__(self, original: Exception):
        self.original = original
        super().__init__(
            "Gemini Batch API indisponível para este projeto/tier. Causa mais "
            "provável: Free tier não tem cota de Batch API (confirmado em "
            "ai.google.dev/gemini-api/docs/pricing — a linha 'Batch API' do "
            "Free tier é 'Not available' para este modelo). Ação: ativar "
            "billing em https://aistudio.google.com/ (isso move o projeto "
            "para Tier 1, que tem Batch API e caching pago). "
            f"Erro original: {original}"
        )


@dataclass
class BatchItem:
    """Um item de entrada do lote — mesma forma de `run_cognitive_pipeline`."""

    ontology: dict[str, Any]
    files: list[tuple[str, bytes]]
    schema: dict[str, Any] | None = None
    focus_hint: str | None = None
    metadata: dict[str, str] | None = None


def _build_inline_request(item: BatchItem, model: str) -> types.InlinedRequest:
    ontology_text = _ontology_prompt_slice(item.ontology)
    system_instruction = build_system_prompt(item.schema or DEFAULT_PIPELINE_SCHEMA)
    user_text = (
        "ONTOLOGIA COGNITIVA (única fonte autorizada, use apenas estes IDs):\n\n"
        f"{ontology_text}\n\n"
    )
    if item.focus_hint:
        user_text += (
            "FOCO OBRIGATÓRIO: os arquivos anexados podem conter várias questões. "
            f"Extraia e classifique APENAS a seguinte questão: {item.focus_hint}. "
            "Ignore todas as demais questões do documento. Se figuras, tabelas ou "
            "gráficos pertencerem a esta questão específica, inclua-os na análise "
            "multimodal.\n\n"
        )
    user_text += (
        "Analise os arquivos anexados (podem conter uma ou mais questões, suas "
        "figuras, gráficos, infográficos e alternativas). Produza o JSON conforme "
        "especificado no system message."
    )
    parts = _build_parts(item.files, user_text)
    return types.InlinedRequest(
        model=model,
        contents=parts,
        metadata=item.metadata,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )


def submit_batch(
    items: list[BatchItem],
    *,
    model: str | None = None,
    display_name: str | None = None,
    client: genai.Client | None = None,
) -> str:
    """Cria o batch job (modo inline) e devolve seu `name` (`batches/...`).

    Não espera o job terminar — Batch API é assíncrona por natureza (janela
    alvo de 24h). Chame `get_batch_status` para acompanhar e `fetch_results`
    quando `state` indicar término.
    """
    if not items:
        raise ValueError("Lote vazio: nada para enviar.")
    client = client or _get_client()
    model = model or _get_model()
    inlined = [_build_inline_request(item, model) for item in items]

    try:
        job = client.batches.create(
            model=model,
            src=types.BatchJobSource(inlined_requests=inlined),
            config=types.CreateBatchJobConfig(display_name=display_name or "sapiens-lote-cognitivo"),
        )
    except genai_errors.ClientError as exc:
        # PERMISSION_DENIED / FAILED_PRECONDITION são os códigos usuais quando
        # o recurso existe na API mas o tier/projeto não tem acesso a ele.
        if getattr(exc, "code", None) in (403, 400) or (exc.status or "") in (
            "PERMISSION_DENIED", "FAILED_PRECONDITION",
        ):
            raise GeminiBatchUnavailableError(exc) from exc
        raise
    logger.info("Batch job criado: %s (itens=%d, modelo=%s)", job.name, len(items), model)
    return job.name


def get_batch_status(name: str, *, client: genai.Client | None = None) -> types.BatchJob:
    client = client or _get_client()
    return client.batches.get(name=name)


def fetch_results(batch_job: types.BatchJob) -> list[dict[str, Any] | Exception]:
    """Extrai o JSON de cada resposta, na mesma ordem em que foi submetida.

    Um item com erro (falha individual dentro de um lote parcialmente
    bem-sucedido — `JOB_STATE_PARTIALLY_SUCCEEDED`) vira a própria exceção na
    posição correspondente, em vez de interromper a leitura dos demais.
    """
    dest = batch_job.dest
    if not dest or not dest.inlined_responses:
        raise RuntimeError(
            f"Batch job {batch_job.name} não tem `inlined_responses` "
            f"(state={batch_job.state}). Só é legível quando concluído."
        )
    out: list[dict[str, Any] | Exception] = []
    for entry in dest.inlined_responses:
        if entry.error:
            out.append(RuntimeError(f"{entry.error.code}: {entry.error.message}"))
            continue
        try:
            raw = (entry.response.text if entry.response else "") or ""
            out.append(_extract_json_object(raw))
        except Exception as exc:  # noqa: BLE001 — erro de parsing vira resultado, não exceção do lote
            out.append(exc)
    return out
