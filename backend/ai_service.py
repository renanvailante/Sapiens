"""Sapiens AI service: Claude Sonnet 4.5 diagnostic + Gemini Vision OCR."""
from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

from dotenv import load_dotenv
from emergentintegrations.llm.chat import (
    ImageContent,
    LlmChat,
    StreamDone,
    TextDelta,
    UserMessage,
)

load_dotenv()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
VISION_MODEL = ("gemini", "gemini-2.5-flash")


def _new_chat(system: str, provider: str = "anthropic", model: str = CLAUDE_MODEL) -> LlmChat:
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"sapiens-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model(provider, model)


def _extract_json(text: str) -> Any:
    text = text.strip()
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
    raise ValueError("Could not parse JSON from AI response")


async def _send(chat: LlmChat, text: str, images: list[ImageContent] | None = None) -> str:
    msg = UserMessage(text=text, file_contents=images) if images else UserMessage(text=text)
    out = ""
    async for ev in chat.stream_message(msg):
        if isinstance(ev, TextDelta):
            out += ev.content
        elif isinstance(ev, StreamDone):
            break
    return out


# ---------- Cognitive Diagnostic ----------

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


async def diagnose(payload: dict[str, Any]) -> dict[str, Any]:
    chat = _new_chat(DIAGNOSTIC_SYSTEM)
    prompt = "Dados da prova:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    reply = await _send(chat, prompt)
    try:
        return _extract_json(reply)
    except Exception:
        return {
            "headline": "Seu desempenho revela padrões maiores do que a nota mostra.",
            "body": "Analisamos suas respostas em busca de padrões cognitivos. Explore o painel para ver o perfil e o plano de estudos.",
            "strengths": [],
            "weaknesses": [],
            "cognitive_profile": {},
            "study_plan": [],
            "learning_map": {"nodes": [], "edges": []},
        }


# ---------- Vision: Answer-sheet OCR ----------

VISION_SYSTEM = """Você reconhece cartões-resposta de provas objetivas.
Retorne SOMENTE um JSON no formato:
{"answers": [{"number": 1, "letter": "A"}, ...]}
- Se uma questão estiver em branco ou ambígua, use "letter": "".
- Considere marcações preenchidas apenas quando a bolha estiver bem preenchida.
- Não adicione explicações."""


async def ocr_answer_sheet(image_base64: str, expected_count: int, start_number: int = 1) -> list[dict[str, Any]]:
    if "," in image_base64 and image_base64.strip().startswith("data:"):
        image_base64 = image_base64.split(",", 1)[1]
    chat = _new_chat(VISION_SYSTEM, provider=VISION_MODEL[0], model=VISION_MODEL[1])
    img = ImageContent(image_base64=image_base64)
    end_number = start_number + expected_count - 1
    prompt = f"Extraia as respostas marcadas. A prova tem {expected_count} questões numeradas de {start_number} a {end_number}."
    reply = await _send(chat, prompt, images=[img])
    data = _extract_json(reply)
    return data.get("answers", [])
