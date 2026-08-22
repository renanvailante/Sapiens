"""Serviços de IA do app do aluno — Google Gemini, chamada direta.

Substitui o proxy `emergentintegrations`, removido da plataforma. Duas
capacidades, ambas cobertas nativamente pela Gemini API:

* `diagnose` — narrativa diagnóstica sobre um cartão-resposta corrigido.
  Antes ia para Claude Sonnet via proxy; é geração de texto com saída JSON, que
  o Gemini faz com `response_mime_type="application/json"`.
* `ocr_answer_sheet` — leitura do cartão-resposta. Já era Gemini Vision, só que
  atravessando o proxy. Agora é a mesma família de modelo, sem intermediário.

Mesmo cliente (`google-genai`) e mesmo padrão de configuração do motor do
pipeline, para que exista **uma** forma de falar com o modelo neste projeto.

**Fronteira de contrato.** Nada aqui produz Error Trace, e nada aqui alimenta a
camada de crença sobre o estado cognitivo de um estudante. O `cognitive_profile`
devolvido por `diagnose` é texto de apresentação para o próprio aluno, derivado
de acerto/erro por área — não é anotação, não usa IDs da ontologia e não é
persistido como estrutura cognitiva. A atribuição de causa de erro tem contrato
próprio (`Especificação do Error Trace v1.0`) e exige confiança ponderada por
elo; derivá-la daqui produziria atribuição determinística, proibida pela
Constituição §4.4.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger("sapiens.ai")

DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_VISION_MODEL = "gemini-3-flash-preview"


def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não configurada. O app do aluno usa a Gemini API "
            "diretamente desde a remoção do proxy Emergent."
        )
    return genai.Client(api_key=api_key)


def _model() -> str:
    return os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL


def _vision_model() -> str:
    return os.environ.get("GEMINI_VISION_MODEL") or DEFAULT_VISION_MODEL


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    raise ValueError("Não foi possível extrair JSON da resposta do modelo.")


async def _generate_json(
    system_instruction: str,
    user_text: str,
    parts: list | None = None,
    model: str | None = None,
) -> Any:
    client = _client()
    chosen = model or _model()
    contents = list(parts or [])
    contents.append(types.Part.from_text(text=user_text))
    resp = await client.aio.models.generate_content(
        model=chosen,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return _extract_json(resp.text or "")


# ---------- Diagnóstico cognitivo ----------

DIAGNOSTIC_SYSTEM = """Você é o Sapiens — um analista de aprendizagem que descobre padrões cognitivos.
NUNCA comece pela nota. Comece revelando um padrão que surpreenda o aluno.
Português claro, humano, com empatia. Sem bullets frios de "Pontos fortes/fracos".

Você não tem o enunciado das questões — apenas:
- ano/cor/dia/idioma da prova
- número de acertos por área (LC-Idioma, LC, CH, CN, MT)
- os NÚMEROS das questões que o aluno errou (com a área de cada)
- a letra que ele marcou e a letra correta
Combine posição da questão, área, e padrão da letra escolhida para inferir padrões cognitivos
(ex: fadiga nas questões finais, viés de alternativa, letra "chutada" repetida, fraqueza em blocos
consecutivos de uma área).

Estas observações são de superfície, feitas sem acesso ao enunciado: descreva
padrões de comportamento de prova, nunca causa cognitiva definitiva. Não use
identificadores de catálogo (PROC-, ERR-, HAB-, DOM-, COMP-, INT-) em nenhum campo.

Responda EXCLUSIVAMENTE com JSON no formato:
{
  "headline": "frase curta e provocativa (máx 90 caracteres)",
  "body": "2-3 parágrafos explicando PADRÕES (não números soltos)",
  "strengths": ["...", "..."],   // 3-5 traços dominados
  "weaknesses": ["...", "..."],  // 3-5 padrões de erro concretos
  "cognitive_profile": {
    "Pensamento visual":  0-100,
    "Pensamento algébrico": 0-100,
    "Interpretação": 0-100,
    "Memorização": 0-100,
    "Abstração": 0-100,
    "Velocidade": 0-100,
    "Precisão": 0-100,
    "Consistência": 0-100,
    "Tomada de decisão": 0-100,
    "Tolerância à complexidade": 0-100,
    "Leitura": 0-100,
    "Inferência": 0-100
  },
  "study_plan": [
    {"topic": "...", "why": "...", "impact_points": 18, "hours": 2}
  ],
  "learning_map": {
    "nodes": [{"id":"prop", "label":"Proporcionalidade", "mastery": 40, "area":"MT"}, ...],
    "edges": [{"source":"frac", "target":"prop", "reason":"proporção depende de fração"}, ...]
  }
}
Sem markdown, sem prefixos, apenas o JSON."""

_DIAGNOSTIC_FALLBACK = {
    "headline": "Seu desempenho revela padrões maiores do que a nota mostra.",
    "body": (
        "Analisamos suas respostas em busca de padrões cognitivos. Explore o "
        "painel para ver o perfil e o plano de estudos."
    ),
    "strengths": [],
    "weaknesses": [],
    "cognitive_profile": {},
    "study_plan": [],
    "learning_map": {"nodes": [], "edges": []},
}


async def diagnose(payload: dict[str, Any]) -> dict[str, Any]:
    """Narrativa diagnóstica do cartão-resposta. Degrada para texto neutro."""
    prompt = "Dados da prova:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        result = await _generate_json(DIAGNOSTIC_SYSTEM, prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Diagnóstico indisponível: %s", exc)
        return dict(_DIAGNOSTIC_FALLBACK)
    if not isinstance(result, dict):
        return dict(_DIAGNOSTIC_FALLBACK)
    return {**_DIAGNOSTIC_FALLBACK, **result}


# ---------- Visão: leitura do cartão-resposta ----------

VISION_SYSTEM = """Você reconhece cartões-resposta de provas objetivas.
Retorne SOMENTE um JSON no formato:
{"answers": [{"number": 1, "letter": "A"}, ...]}
- Se uma questão estiver em branco ou ambígua, use "letter": "".
- Considere marcações preenchidas apenas quando a bolha estiver bem preenchida.
- Não adicione explicações."""

_DATA_URL = re.compile(r"^data:(?P<mime>[^;,]+)?[^,]*,")


def _decode_image(image_base64: str) -> tuple[bytes, str]:
    """Aceita base64 puro ou data URL, preservando o mime declarado."""
    import base64

    raw = (image_base64 or "").strip()
    mime = "image/jpeg"
    m = _DATA_URL.match(raw)
    if m:
        mime = m.group("mime") or mime
        raw = raw[m.end():]
    return base64.b64decode(raw), mime


async def ocr_answer_sheet(
    image_base64: str, expected_count: int, start_number: int = 1
) -> list[dict[str, Any]]:
    data, mime = _decode_image(image_base64)
    end_number = start_number + expected_count - 1
    prompt = (
        f"Extraia as respostas marcadas. A prova tem {expected_count} questões "
        f"numeradas de {start_number} a {end_number}."
    )
    parsed = await _generate_json(
        VISION_SYSTEM,
        prompt,
        parts=[types.Part.from_bytes(data=data, mime_type=mime)],
        model=_vision_model(),
    )
    if isinstance(parsed, list):
        return parsed
    return (parsed or {}).get("answers", [])
