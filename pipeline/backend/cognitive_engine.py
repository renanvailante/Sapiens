"""Cognitive pipeline engine — usa a API direta do Google Gemini (google-genai).

Dada a ontologia atualmente ativa e um ou mais arquivos (PDF / imagens),
produz um pipeline cognitivo JSON estrito usando somente IDs da ontologia.

Motor único: Google Gemini via `google-genai` (chave em GEMINI_API_KEY).
Modelo configurável em GEMINI_MODEL (default: gemini-3.1-pro-preview).
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3-flash-preview"


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não configurada.")
    return genai.Client(api_key=api_key)


def _get_model() -> str:
    return os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL


_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _mime_for(filename: str, default: str = "application/octet-stream") -> str:
    return _MIME_BY_EXT.get(os.path.splitext(filename)[1].lower(), default)


def _ontology_prompt_slice(ontology: dict[str, Any]) -> str:
    def compact(items: list[dict], keys: list[str]) -> list[dict]:
        return [{k: it.get(k) for k in keys} for it in items]

    payload = {
        "versao": ontology.get("version"),
        "dominios": compact(ontology.get("dominios", []), ["id", "nome", "descricao"]),
        "competencias": compact(ontology.get("competencias", []),
                                ["id", "nome", "dominio", "descricao"]),
        "processos_cognitivos": compact(ontology.get("processos_cognitivos", []),
                                        ["id", "nome", "categoria", "descricao"]),
        "habilidades_observaveis": compact(ontology.get("habilidades_observaveis", []),
                                           ["id", "nome", "processos_cognitivos", "descricao"]),
        "tipos_erro": compact(ontology.get("tipos_erro", []),
                              ["id", "nome", "descricao"]),
        "intervencoes_pedagogicas": compact(ontology.get("intervencoes_pedagogicas", []),
                                            ["id", "nome", "descricao"]),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# Default pipeline schema — the canonical output structure expected from Gemini.
# Kept as a Python dict so it can be JSON-dumped into the prompt and also
# exposed via /api/schema. Overridable at runtime by importing a custom schema
# (armazenado em Mongo via /api/schema/import); veja server.py.
DEFAULT_PIPELINE_SCHEMA: dict[str, Any] = {
    "questao": {
        "disciplina": "string",
        "banca": "string|null",
        "ano": "string|null",
        "tema": "string",
        "enunciado": "string com todo o texto extraído",
        "alternativas": [
            {"letra": "A", "texto": "..."},
            {"letra": "B", "texto": "..."},
        ],
        "resposta_correta": "A|B|C|D|E|null",
        "figuras_detectadas": [
            {"descricao": "descrição breve do que a figura contém"}
        ],
    },
    "classificacao": {
        "dominios": ["DOM-..."],
        "competencias": ["COMP-..."],
        "processos_cognitivos": [
            {
                "id": "PROC-...",
                "papel": "nuclear|secundario|facilitador",
                "justificativa": {
                    "trechos_enunciado": ["citação 1", "citação 2"],
                    "elementos_figura": ["descrição do que na figura foi usado"],
                    "regras_ontologia": ["por que a definição de PROC-XX se aplica"],
                    "por_que_este_papel": "explicação curta do papel escolhido",
                },
            }
        ],
        "habilidades_observaveis": ["HAB-..."],
        "distratores": [
            {
                "alternativa": "B",
                "tipo_erro_id": "ERR-...",
                "explicacao": "por que essa alternativa é atrativa e qual raciocínio errado ela captura",
            }
        ],
        "tipos_erro_previstos": ["ERR-..."],
        "intervencoes_sugeridas": ["INT-..."],
    },
    "meta": {
        "confianca": 0.0,
        "observacoes": "notas do motor sobre limites de leitura",
    },
}


_SYSTEM_PROMPT_TEMPLATE = """Você é o motor de anotação cognitiva do sistema Sapiens.

REGRA ABSOLUTA: sua saída DEVE ser um único objeto JSON válido, sem texto
antes ou depois, sem markdown, sem comentários.

Você recebe:
1. Uma ONTOLOGIA COGNITIVA (única fonte autorizada).
2. Um ou mais arquivos (PDF, PNG ou JPG) contendo UMA questão de vestibular
   (texto, alternativas, figuras, gráficos, fórmulas).

Você DEVE:
- Ler multimodalmente todo o conteúdo (texto + figuras + tabelas + fórmulas).
- Extrair estruturadamente a questão.
- Classificar exclusivamente usando os IDs da ontologia. NUNCA invente
  IDs, competências, processos, domínios, habilidades ou tipos de erro. Se
  algo não couber, deixe a lista vazia — nunca crie IDs novos.
- Para cada processo cognitivo indicar se é "nuclear", "secundario" ou
  "facilitador", com justificativa detalhada (trechos do enunciado,
  elementos da figura e regra da ontologia que sustentam a escolha).
- Listar as HABILIDADES OBSERVÁVEIS (HAB-...) evidenciadas pela questão,
  usando apenas IDs presentes na ontologia.

Formato de saída OBRIGATÓRIO (JSON estrito, siga EXATAMENTE este schema):

{schema_json}

Se um campo não puder ser preenchido com certeza, use null (para escalares)
ou lista vazia. Nunca invente. Nunca use IDs fora da ontologia."""


def build_system_prompt(schema: dict[str, Any] | None = None) -> str:
    schema = schema or DEFAULT_PIPELINE_SCHEMA
    schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
    return _SYSTEM_PROMPT_TEMPLATE.replace("{schema_json}", schema_json)


# Backward compatibility — legacy consumers that still import SYSTEM_PROMPT.
SYSTEM_PROMPT = build_system_prompt()


def _extract_json_object(text: str) -> dict:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    if start == -1:
        raise ValueError("Nenhum JSON encontrado na resposta do modelo.")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("JSON incompleto na resposta do modelo.")


def _build_parts(files: list[tuple[str, bytes]], user_text: str) -> list:
    parts = []
    for filename, data in files:
        mime = _mime_for(filename)
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    parts.append(types.Part.from_text(text=user_text))
    return parts


async def _generate_json(
    system_instruction: str,
    user_text: str,
    files: list[tuple[str, bytes]],
) -> dict:
    import asyncio as _asyncio
    from google.genai import errors as _genai_errors

    client = _get_client()
    model = _get_model()
    parts = _build_parts(files, user_text)
    logger.info("Gemini call · model=%s · files=%d", model, len(files))
    # Retry para 503 UNAVAILABLE (picos temporários de demanda)
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            resp = await client.aio.models.generate_content(
                model=model,
                contents=parts,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            raw = resp.text or ""
            logger.info("Gemini raw length: %d (attempt %d)", len(raw), attempt + 1)
            return _extract_json_object(raw)
        except _genai_errors.ServerError as exc:
            last_exc = exc
            if getattr(exc, "code", None) == 503 and attempt < 3:
                wait = 2 * (attempt + 1)
                logger.warning("Gemini 503 — retry em %ds (tentativa %d)", wait, attempt + 1)
                await _asyncio.sleep(wait)
                continue
            raise
    raise last_exc  # pragma: no cover


# ---------------------------------------------------------------------------
# Pipeline cognitivo (uma questão)
# ---------------------------------------------------------------------------
async def run_cognitive_pipeline(
    ontology: dict[str, Any],
    files: list[tuple[str, bytes]],
    session_id: str | None = None,  # kept for backward compatibility
    focus_hint: str | None = None,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ontology_text = _ontology_prompt_slice(ontology)
    user_text = (
        "ONTOLOGIA COGNITIVA (única fonte autorizada, use apenas estes IDs):\n\n"
        f"{ontology_text}\n\n"
    )
    if focus_hint:
        user_text += (
            "FOCO OBRIGATÓRIO: os arquivos anexados podem conter várias questões. "
            f"Extraia e classifique APENAS a seguinte questão: {focus_hint}. "
            "Ignore todas as demais questões do documento. Se figuras, tabelas ou "
            "gráficos pertencerem a esta questão específica, inclua-os na análise "
            "multimodal.\n\n"
        )
    user_text += (
        "Analise os arquivos anexados (podem conter uma ou mais questões, suas "
        "figuras, gráficos, infográficos e alternativas). Produza o JSON conforme "
        "especificado no system message."
    )
    system_instruction = build_system_prompt(schema)
    return await _generate_json(system_instruction, user_text, files)


# ---------------------------------------------------------------------------
# Manifesto do caderno
# ---------------------------------------------------------------------------
MANIFEST_PROMPT = """Você é um enumerador de cadernos de vestibular.

O usuário anexa um PDF (e opcionalmente imagens) contendo múltiplas questões
de uma prova. Sua tarefa é IDENTIFICAR cada questão distinta no documento
e devolver um manifesto JSON, sem processá-las cognitivamente.

FORMATO OBRIGATÓRIO:

{
  "questoes": [
    {
      "numero": "1",
      "titulo": "resumo do enunciado, ≤ 90 chars",
      "paginas": [3, 4],
      "disciplina": "estimativa da disciplina ou null",
      "tem_figura": true
    }
  ]
}

REGRAS:
- Saída DEVE ser um único JSON válido, sem markdown, sem texto ao redor.
- Preserve a numeração original da prova. Se não houver, use 1, 2, 3...
- Se o PDF não contém questões, devolva {"questoes": []}.
- NÃO extraia enunciado completo aqui — apenas o índice."""


async def run_book_manifest(files: list[tuple[str, bytes]]) -> list[dict]:
    user_text = "Enumere todas as questões distintas do caderno anexado."
    parsed = await _generate_json(MANIFEST_PROMPT, user_text, files)
    questoes = parsed.get("questoes", []) or []
    clean: list[dict] = []
    for q in questoes:
        if not isinstance(q, dict):
            continue
        clean.append(
            {
                "numero": str(q.get("numero") or q.get("number") or ""),
                "titulo": q.get("titulo") or q.get("title") or "",
                "paginas": q.get("paginas") or q.get("pages") or [],
                "disciplina": q.get("disciplina") or q.get("discipline"),
                "tem_figura": bool(q.get("tem_figura") or q.get("has_figure")),
            }
        )
    return clean


# ---------------------------------------------------------------------------
# Parser de ontologia (PDF/DOCX/MD/TXT)
# ---------------------------------------------------------------------------
ONTOLOGY_PARSE_PROMPT = """Você é um extrator de ontologias cognitivas.

O usuário anexa um documento (PDF/DOCX/MD/TXT) contendo a descrição de uma
ontologia cognitiva para anotação de questões de vestibular. Sua tarefa é
converter o conteúdo em UM ÚNICO JSON no schema abaixo.

REGRAS:
- Saída DEVE ser um único objeto JSON válido, sem texto antes ou depois,
  sem markdown, sem comentários.
- NUNCA invente elementos. Se algo não estiver no documento, deixe a lista vazia.
- Preserve os IDs exatamente como aparecem no documento (ex: DOM-QUANT, COMP-01,
  PROC-05, ERR-03, INT-02). Se o documento não fornecer IDs explícitos, gere IDs
  sequenciais no padrão: DOM-01, COMP-01, PROC-01, ERR-01, INT-01.
- Se o documento contiver descrição de "pipeline padrão" ou instruções que não
  sejam elementos ontológicos, ignore-as (esta rotina extrai apenas a ontologia).

SCHEMA (obrigatório):
{
  "version": "string extraído do documento ou 'imported-<timestamp>'",
  "name": "nome da ontologia (ou vazio)",
  "description": "descrição curta (ou vazio)",
  "dominios": [
    {"id":"DOM-...", "nome":"...", "descricao":"..."}
  ],
  "competencias": [
    {"id":"COMP-...", "nome":"...", "dominio":"DOM-... ou vazio",
     "descricao":"..."}
  ],
  "processos_cognitivos": [
    {"id":"PROC-...", "nome":"...", "categoria":"opcional",
     "descricao":"..."}
  ],
  "habilidades_observaveis": [
    {"id":"HAB-...", "nome":"...", "processos_cognitivos":["PROC-..."],
     "descricao":"opcional"}
  ],
  "tipos_erro": [
    {"id":"ERR-...", "nome":"...", "descricao":"..."}
  ],
  "intervencoes_pedagogicas": [
    {"id":"INT-...", "nome":"...", "descricao":"..."}
  ]
}
"""


async def parse_ontology_with_gemini(
    filename: str, data: bytes, mime_type: str
) -> dict[str, Any]:
    user_text = (
        "Extraia a ontologia do arquivo anexado e devolva o JSON no schema "
        "especificado no system message."
    )
    parsed = await _generate_json(ONTOLOGY_PARSE_PROMPT, user_text, [(filename, data)])
    for key in (
        "dominios",
        "competencias",
        "processos_cognitivos",
        "habilidades_observaveis",
        "tipos_erro",
        "intervencoes_pedagogicas",
    ):
        parsed.setdefault(key, [])
    return parsed
