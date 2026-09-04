"""Perfil cognitivo real do aluno — snapshot semanal, automático, quase sem
custo (zero IA na maior parte das vezes).

Duas camadas, deliberadamente separadas por custo:
- Determinística (`annotation_service.compute_diagnostico_real`): pode ser
  recalculada com a frequência que quiser, é só agregação sobre Firestore.
- Narrativa (`ai_service.gerar_narrativa_perfil`): custa uma chamada Gemini,
  então só é gerada UMA VEZ por período (semana ISO) por aluno — chamadas
  seguintes no mesmo período reaproveitam o texto já salvo.

Este módulo não decide QUEM processar (isso é `atualizar_todos_os_perfis`,
usado pelo laço automático em `server.py`) nem é chamado por aluno nenhum
diretamente — é infraestrutura de admin/observabilidade.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import ai_service
import annotation_service
import firestore_service as fs

logger = logging.getLogger("sapiens.perfil_cognitivo")


def periodo_atual() -> str:
    """Semana ISO corrente, ex. '2026-W36'. Zero-padded: '2026-W05', nunca
    '2026-W5' — precisa ordenar como string igual ordena como data."""
    ano, semana, _ = datetime.now(timezone.utc).isocalendar()
    return f"{ano}-W{semana:02d}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitizar_para_narrativa(perfil: dict[str, Any]) -> dict[str, Any]:
    """Remove todo ID de catálogo (`id`, `processo_id`, `erro_id`,
    `intervencao_id`) antes de mandar pro Gemini — mesma disciplina de
    `annotation_service.montar_contexto_sessao`: os IDs são trocados/removidos
    ANTES, não só por instrução de prompt."""

    def _sem_ids(linha: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in linha.items() if k not in ("id", "processo_id", "erro_id", "intervencao_id")}

    def _nivel(bloco: dict[str, Any] | None) -> dict[str, Any]:
        bloco = bloco or {}
        return {
            "fortes": [_sem_ids(l) for l in bloco.get("fortes") or []],
            "fracos": [_sem_ids(l) for l in bloco.get("fracos") or []],
        }

    return {
        "por_dominio": _nivel(perfil.get("por_dominio")),
        "por_competencia": _nivel(perfil.get("por_competencia")),
        "por_processo": _nivel(perfil.get("por_processo")),
        "padroes_associados": [_sem_ids(p) for p in perfil.get("padroes_associados") or []],
        "cobertura_percentual": perfil.get("coverage"),
        "amostra_minima_por_item": perfil.get("amostra_minima"),
    }


async def gerar_e_salvar_snapshot(uid: str, *, fonte_event_count: int | None = None) -> dict[str, Any] | None:
    """Recalcula o perfil real do aluno (determinístico) e salva um snapshot
    no período corrente. Gera narrativa nova só se ainda não existir uma para
    este período — reaproveita a anterior quando chamado de novo na mesma
    semana. Devolve `None` se o aluno ainda não tem amostra suficiente para
    nenhum ponto (nada de útil pra salvar ainda).

    `fonte_event_count`, quando informado, é só guardado no doc para o
    chamador em lote (`atualizar_todos_os_perfis`) decidir depois se vale a
    pena recomputar este aluno de novo sem precisar reler os eventos.
    """
    perfil = await annotation_service.compute_diagnostico_real(uid)
    sem_ponto = not perfil["por_dominio"]["fortes"] and not perfil["por_dominio"]["fracos"] \
        and not perfil["por_competencia"]["fortes"] and not perfil["por_competencia"]["fracos"] \
        and not perfil["por_processo"]["fortes"] and not perfil["por_processo"]["fracos"]
    if sem_ponto:
        return None

    periodo = periodo_atual()
    anterior = await asyncio.to_thread(fs.read_ultimo_perfil, uid)
    narrativa = ""
    if anterior and anterior.get("periodo") == periodo:
        narrativa = anterior.get("narrativa") or ""
    if not narrativa:
        narrativa = await ai_service.gerar_narrativa_perfil(_sanitizar_para_narrativa(perfil))

    doc = {
        **perfil,
        "periodo": periodo,
        "gerado_em": _now_iso(),
        "narrativa": narrativa,
        "fonte_event_count": fonte_event_count if fonte_event_count is not None else perfil.get("total_events", 0),
    }
    await asyncio.to_thread(fs.write_perfil_cognitivo, uid, periodo, doc)
    return doc


async def atualizar_todos_os_perfis() -> dict[str, int]:
    """Ponto de entrada do laço automático (`server._perfil_cognitivo_loop`) e
    do gatilho manual de admin. Só recomputa (a parte cara: ler todo o
    histórico de behavior do aluno) quem teve evento NOVO desde o último
    snapshot salvo — para quem não respondeu nada novo, nem chega a olhar o
    Firestore de novo. A comparação usa a contagem já trazida por
    `list_students_with_behavior` (uma única query, cobre todo mundo), nunca
    lê o histórico completo só para decidir se vale a pena ler o histórico
    completo.
    """
    resultado = {"processados": 0, "pulados": 0, "sem_amostra": 0, "falhas": 0}
    alunos = await asyncio.to_thread(fs.list_students_with_behavior)
    for aluno in alunos:
        uid = aluno.get("student_id")
        contagem_atual = aluno.get("count") or 0
        if not uid:
            continue
        try:
            anterior = await asyncio.to_thread(fs.read_ultimo_perfil, uid)
            if anterior and anterior.get("fonte_event_count") == contagem_atual:
                resultado["pulados"] += 1
                continue
            doc = await gerar_e_salvar_snapshot(uid, fonte_event_count=contagem_atual)
            if doc is None:
                resultado["sem_amostra"] += 1
            else:
                resultado["processados"] += 1
        except Exception:  # noqa: BLE001
            logger.exception("Perfil cognitivo: falha ao processar %s", uid)
            resultado["falhas"] += 1
    return resultado
