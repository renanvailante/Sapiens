"""Escalonamento adaptativo genérico entre um nível barato e um nível caro de
LLM — sem saber nada de Gemini, Enem ou qualquer domínio específico.

Port do padrão provado em `pipeline/backend/cognitive_engine.py::
run_cognitive_pipeline_adaptive` (auditoria de custo 2026-08-22: escalonar só
quando necessário chegou a ~20% do custo de rodar sempre no nível caro, sem
perda de validade estrutural na amostra testada). Generalizado aqui como
callables async, para que qualquer chamador — o corretor de redação, e no
futuro outras áreas do Sapiens — reuse o mesmo mecanismo sem reimplementar o
cap de 2 chamadas nem a regra de "judge que falha nunca escala por engano".
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger("sapiens.llm_escalation")

T = TypeVar("T")
JudgeFn = Callable[[T], bool]


async def run_adaptive(
    call_low: Callable[[], Awaitable[T]],
    judge: JudgeFn,
    call_high: Callable[[], Awaitable[T]],
) -> tuple[T, dict[str, Any]]:
    """1 chamada barata → `judge()` local e síncrono decide se está aprovada.
    Se não, 1 (e só 1) chamada cara. Nunca mais que 2 chamadas totais — não
    existe uma 3ª tentativa nesta função, de propósito, para que um item
    difícil nunca vire um laço caro.

    `judge` deve ser síncrono, local e barato (nunca deve chamar outro LLM —
    duplicaria custo por engano). `judge` que lança exceção é tratado como
    aprovado: uma falha no validador não pode silenciosamente dobrar o custo
    da chamada seguinte.

    Retorna `(resultado, meta)`, onde `meta = {"attempts": int, "escalated":
    bool}` — só para telemetria/log, nunca deve ser persistido dentro do
    próprio resultado.
    """
    resultado = await call_low()
    try:
        aprovado = bool(judge(resultado))
    except Exception:  # noqa: BLE001
        logger.exception(
            "run_adaptive: judge() levantou exceção — mantendo o resultado da chamada barata sem escalonar"
        )
        aprovado = True
    if aprovado:
        return resultado, {"attempts": 1, "escalated": False}
    logger.info("run_adaptive: judge() reprovou a chamada barata — escalonando 1x")
    resultado = await call_high()
    return resultado, {"attempts": 2, "escalated": True}
