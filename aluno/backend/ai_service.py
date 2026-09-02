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
import asyncio
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


_THINKING_VALIDOS = {"MINIMAL", "LOW", "MEDIUM", "HIGH"}

# Teto de espera por chamada ao Gemini. Sem isto uma resposta pendurada segura
# o worker indefinidamente: com `soft_limit = 40` requisições concorrentes numa
# máquina só (fly.toml), poucas chamadas travadas bastam para o site inteiro
# parar de responder — sem erro nenhum, só lentidão inexplicável.
# O OCR do cartão-resposta manda uma imagem e demora mais que uma chamada de
# texto, daí o teto próprio.
GEMINI_TIMEOUT_SEGUNDOS = float(os.environ.get("GEMINI_TIMEOUT_SEGUNDOS", "30") or 30)
GEMINI_TIMEOUT_VISION_SEGUNDOS = float(os.environ.get("GEMINI_TIMEOUT_VISION_SEGUNDOS", "60") or 60)


class GeminiIndisponivelError(RuntimeError):
    """Gemini não respondeu no tempo limite, ou falhou de forma não recuperável.

    Existe para o chamador distinguir "o modelo não respondeu" de "o modelo
    respondeu algo inválido" — o primeiro caso merece uma mensagem de tentar
    de novo, o segundo é um bug de prompt.
    """


async def _generate_json(
    system_instruction: str,
    user_text: str,
    parts: list | None = None,
    model: str | None = None,
    thinking_level: str | None = None,
    timeout: float | None = None,
) -> Any:
    """`thinking_level`, quando presente, limita o raciocínio da chamada.

    A auditoria de custo do pipeline (2026-08-22) mediu `gemini-3-flash-
    preview` sem limite chegando a dezenas de milhares de tokens de
    "thinking" numa única chamada — o app aluno usa o mesmo modelo, então
    chamadas novas e recorrentes aqui (ex.: resumo de sessão, gerado por
    aluno ativo) herdam o mesmo risco se ninguém configurar isto.

    `timeout` (padrão `GEMINI_TIMEOUT_SEGUNDOS`) transforma uma chamada
    pendurada em `GeminiIndisponivelError`, que cada chamador trata com o
    fallback que fizer sentido para ele — nunca deixando o aluno esperando.
    """
    client = _client()
    chosen = model or _model()
    contents = list(parts or [])
    contents.append(types.Part.from_text(text=user_text))
    config_kwargs: dict[str, Any] = {
        "system_instruction": system_instruction,
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }
    nivel = (thinking_level or "").strip().upper()
    if nivel in _THINKING_VALIDOS:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=types.ThinkingLevel(nivel))
    try:
        resp = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=chosen,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
            ),
            timeout=timeout if timeout is not None else GEMINI_TIMEOUT_SEGUNDOS,
        )
    except asyncio.TimeoutError as exc:
        raise GeminiIndisponivelError(
            f"Gemini não respondeu em {timeout or GEMINI_TIMEOUT_SEGUNDOS:.0f}s."
        ) from exc
    return _extract_json(resp.text or "")


async def generate_json(
    system_instruction: str,
    user_text: str,
    model: str | None = None,
    thinking_level: str | None = None,
) -> Any:
    """Fachada pública de `_generate_json` para os módulos que chamam o Gemini
    de fora deste arquivo (hoje o corretor de redação, em `redacao/`).

    Existe como nome público de propósito: é o ponto único que os testes
    offline substituem para rodar o corretor inteiro sem rede.
    """
    return await _generate_json(
        system_instruction, user_text, model=model, thinking_level=thinking_level
    )


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


# ---------- Resumo de sessão de prática (Schema 2.2 / Firestore behavior) ----------
#
# Mesma fronteira de contrato do cabeçalho deste módulo, aplicada à prática
# questão-por-questão: a entrada (`annotation_service.montar_contexto_sessao`)
# já vem sem ID de catálogo, então mesmo que o modelo ignorasse a instrução
# abaixo, não haveria ID para vazar. Narrativa de padrão, não atribuição.

SESSAO_DIAGNOSTIC_SYSTEM = """Você é o Sapiens — um analista de aprendizagem que revela padrões
cognitivos ao final de uma sessão de prática de questões.

Você recebe uma lista de questões respondidas nesta sessão, cada uma com:
- se o aluno acertou ou errou;
- os processos/domínios/competências cognitivos que a questão exercitava (nomes em
  português — não são IDs de catálogo, não use identificadores como "PROC-01");
- quando errou, a explicação (escrita por quem elaborou a questão) de por que a
  alternativa escolhida é um engano plausível — isso descreve um padrão de erro
  POSSÍVEL para a questão, não uma certeza sobre o que este aluno pensou.

Sua tarefa é apontar PADRÕES em linguagem simples e empática, como hipóteses de
estudo — nunca como diagnóstico definitivo. NUNCA comece pela contagem de
acertos. Comece por um padrão que possa surpreender o aluno. Nunca use um ID de
catálogo em texto nenhum.

Responda EXCLUSIVAMENTE com JSON no formato:
{
  "headline": "frase curta e provocativa (máx 90 caracteres)",
  "body": "1-2 parágrafos sobre os padrões observados nesta sessão",
  "pontos_fortes": ["processo/domínio/competência com bom desempenho", "..."],
  "pontos_de_atencao": ["processo/domínio/competência com mais erro", "..."],
  "padroes_de_erro": ["tipo de engano recorrente, em linguagem natural", "..."]
}
Sem markdown, sem prefixos, apenas o JSON."""

_SESSAO_FALLBACK = {
    "headline": "Sessão registrada.",
    "body": "Continue praticando — o resumo de padrões volta a aparecer a cada 10 questões respondidas.",
    "pontos_fortes": [],
    "pontos_de_atencao": [],
    "padroes_de_erro": [],
}


async def diagnose_sessao(contexto: list[dict[str, Any]]) -> dict[str, Any]:
    """Narrativa de padrões de uma sessão de prática. Degrada para texto neutro.

    `thinking_level="LOW"`: a entrada é pequena (10+ questões resumidas, sem
    enunciado nem alternativas) — não é uma tarefa que precise de raciocínio
    "alto" do modelo, e essa chamada roda toda vez que um aluno termina uma
    sessão, não uma vez por lote como a anotação do pipeline.
    """
    prompt = "Questões respondidas nesta sessão:\n" + json.dumps(contexto, ensure_ascii=False, indent=2)
    try:
        result = await _generate_json(SESSAO_DIAGNOSTIC_SYSTEM, prompt, thinking_level="LOW")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Resumo de sessão indisponível: %s", exc)
        return dict(_SESSAO_FALLBACK)
    if not isinstance(result, dict):
        return dict(_SESSAO_FALLBACK)
    return {**_SESSAO_FALLBACK, **result}


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
        timeout=GEMINI_TIMEOUT_VISION_SEGUNDOS,
    )
    if isinstance(parsed, list):
        return parsed
    return (parsed or {}).get("answers", [])
