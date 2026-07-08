"""Sapiens AI service: Claude for cognitive analysis + Vision for answer-sheet OCR."""
from __future__ import annotations

import base64
import json
import os
import re
import uuid
from typing import Any

from dotenv import load_dotenv
from emergentintegrations.llm.chat import (
    FileContentWithMimeType,
    ImageContent,
    LlmChat,
    UserMessage,
)

load_dotenv()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
VISION_MODEL = ("gemini", "gemini-2.5-flash")


def _new_chat(system: str, provider: str = "anthropic", model: str = CLAUDE_MODEL) -> LlmChat:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"sapiens-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model(provider, model)
    return chat


def _extract_json(text: str) -> Any:
    """Extract JSON from an LLM reply."""
    text = text.strip()
    # try direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # try code fence
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # last resort: first {..} block
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
    from emergentintegrations.llm.chat import TextDelta, StreamDone
    async for ev in chat.stream_message(msg):
        if isinstance(ev, TextDelta):
            out += ev.content
        elif isinstance(ev, StreamDone):
            break
    return out


# ---------- Cognitive Diagnostic ----------

DIAGNOSTIC_SYSTEM = """Você é o Sapiens, um analista de aprendizagem que descobre PADRÕES cognitivos.
NUNCA comece falando da nota. Comece revelando um insight surpreendente sobre COMO o aluno pensa.
Escreva em português claro, humano, com empatia. Nada de bullets de "Pontos fortes/fracos".
Você recebe:
- desempenho por área e por etiqueta cognitiva
- as questões que ele errou (com etiquetas cognitivas ricas)
Sua tarefa é responder SÓ com um JSON, com as chaves:
  "headline": frase curta e provocativa (máx 90 caracteres)
  "body": 2-3 parágrafos curtos que expliquem PADRÕES (ex: "você acerta o difícil e erra o fácil", "leitura apressada", "duas variáveis simultâneas"), sem listar números
  "strengths": lista de 3-5 traços cognitivos dominados (frases curtas)
  "weaknesses": lista de 3-5 padrões de erro concretos (frases curtas)
  "cognitive_profile": objeto com traços 0-100 (chaves em pt: "Pensamento visual","Pensamento algébrico","Interpretação","Memorização","Abstração","Velocidade","Precisão","Consistência","Tomada de decisão","Tolerância à complexidade","Leitura","Inferência")
  "study_plan": lista de itens ORDENADOS por retorno esperado (não por matéria). Cada item: {topic, why, impact_points, hours}
  "learning_map": {"nodes": [{id, label, mastery(0-100), area}], "edges": [{source, target, reason}]}
    - inclua causas-raiz (ex: proporcionalidade → fração → razão → grandezas)
Responda EXCLUSIVAMENTE com o JSON. Sem markdown, sem prefixos.
"""


async def diagnose(payload: dict[str, Any]) -> dict[str, Any]:
    """payload contains aggregated performance + list of errors with tags."""
    chat = _new_chat(DIAGNOSTIC_SYSTEM)
    prompt = "Dados da prova:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    reply = await _send(chat, prompt)
    try:
        return _extract_json(reply)
    except Exception:
        # Graceful fallback
        return {
            "headline": "Seu desempenho revela padrões maiores do que a nota mostra.",
            "body": "Analisamos suas respostas em busca de padrões cognitivos. Explore o painel para ver o mapa de competências e o plano de estudos personalizado.",
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
- Não adicione explicações.
"""


async def ocr_answer_sheet(image_base64: str, expected_count: int) -> list[dict[str, Any]]:
    # Strip data URL prefix if present
    if "," in image_base64 and image_base64.strip().startswith("data:"):
        image_base64 = image_base64.split(",", 1)[1]
    chat = _new_chat(VISION_SYSTEM, provider=VISION_MODEL[0], model=VISION_MODEL[1])
    img = ImageContent(image_base64=image_base64)
    prompt = f"Extraia as respostas marcadas. A prova tem {expected_count} questões numeradas de 1 a {expected_count}."
    reply = await _send(chat, prompt, images=[img])
    data = _extract_json(reply)
    return data.get("answers", [])


# ---------- Question tagging (admin panel) ----------

TAG_SYSTEM = """Você é um especialista pedagógico que gera etiquetas cognitivas para questões de vestibular.
Retorne SOMENTE um JSON com dezenas de etiquetas úteis, com chaves:
disciplina, area, tema, subtema, microtema, competencia_enem, habilidade_enem, conteudo,
pre_requisitos (lista), tipo_raciocinio, interpretacao_textual (bool), interpretacao_grafico (bool),
interpretacao_tabela (bool), visualizacao_espacial (bool), algebra (bool), geometria (bool),
funcoes (bool), estatistica (bool), probabilidade (bool), proporcionalidade (bool), modelagem (bool),
conversao_unidades (bool), grandezas (bool), raciocinio_logico (bool), memorizacao (bool),
conhecimento_factual (bool), conhecimento_conceitual (bool), numero_etapas (int),
complexidade_textual (0-10), complexidade_matematica (0-10), complexidade_visual (0-10),
carga_cognitiva (0-10), tipo_distracao, tipo_erro_comum, pegadinha (bool),
tempo_medio_segundos (int), dificuldade (facil/medio/dificil), nivel_bloom, probabilidade_acerto (0-1),
competencias_secundarias (lista), habilidades_secundarias (lista).
"""


async def tag_question(statement: str, alternatives: list[dict], correct: str) -> dict[str, Any]:
    chat = _new_chat(TAG_SYSTEM)
    prompt = json.dumps(
        {"enunciado": statement, "alternativas": alternatives, "gabarito": correct},
        ensure_ascii=False,
    )
    reply = await _send(chat, prompt)
    try:
        return _extract_json(reply)
    except Exception:
        return {}
