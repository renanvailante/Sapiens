"""`GET /perfil` e `GET /perfil/painel` — as duas visões de desempenho que o
app do aluno serve ao cliente.

`/perfil` é a leitura em PALAVRAS do que a ontologia sabe: ver
`perfil_pedagogico.py`, nenhum campo dessa resposta carrega nome ou ID interno
da ontologia, nem percentual.

`/perfil/painel` é a tela em GRÁFICOS, e o que ela mede não é ontologia —
é o que o aluno fez (volume, dia, hora, tempo, constância) e como ele vai por
FRENTE da prova (Matemática, Biologia, Redação…), que é o vocabulário público
da prova e não o catálogo interno. Ver `perfil_painel.py`.

Custo de leitura: as duas rotas são **gratuitas** e não chamam modelo nenhum.
O painel lê o agregado de desempenho UMA vez e passa adiante — para o
diagnóstico, para o ranking de rendimento e para a tradução pedagógica —, em
vez de deixar cada peça pedir a sua (ver
`project_aluno_disciplina_leitura_firestore`).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from auth import require_user
from models import User
import annotation_service
import cronograma_routes
import firestore_service as fs
import perfil_painel
import perfil_pedagogico

logger = logging.getLogger("sapiens.perfil")

router = APIRouter(prefix="", tags=["perfil-publico"])

_db = None


def set_db(db):
    global _db
    _db = db


# Teto de correções lidas para o gráfico da redação. Nenhum aluno real chega
# perto disso; o limite existe para que a consulta tenha custo declarado em
# vez de crescer com o histórico (a mesma disciplina do lado do Firestore).
_TETO_REDACOES = 60


async def _avaliacoes_de_redacao(uid: str) -> list[dict]:
    """As correções do aluno, da mais antiga para a mais nova.

    Uma consulta ao Mongo com projeção mínima — nota, competências e data.
    O TEXTO da redação nunca entra aqui: o painel desenha a nota, não lê o que
    o aluno escreveu.
    """
    if _db is None:
        return []
    try:
        cursor = (
            _db.redacao_avaliacoes.find(
                {"user_id": uid},
                {"_id": 0, "nota_total": 1, "nota_pontos_estimados": 1,
                 "competencias": 1, "created_at": 1, "estado_geral": 1},
            )
            .sort("created_at", 1)
            .limit(_TETO_REDACOES)
        )
        return await cursor.to_list(length=_TETO_REDACOES)
    except Exception:  # noqa: BLE001
        # Um gráfico a menos não pode derrubar os outros dez.
        logger.exception("painel: leitura de redações falhou para %s", uid)
        return []


@router.get("/perfil")
async def get_perfil(user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    return await perfil_pedagogico.perfil_publico(user.user_id)


@router.get("/perfil/painel")
async def get_painel(user: User = Depends(require_user)):
    """O painel inteiro numa chamada.

    Uma tela com dez gráficos que fizesse dez requisições seria dez vezes o
    custo de leitura e uma tela que monta aos pedaços. Aqui é uma resposta só,
    montada por uma função pura sobre dados já em cache.
    """
    fs.ensure_student_profile(user.user_id, user.name, user.email)

    try:
        agregado = await annotation_service.agregado_desempenho(user.user_id)
    except Exception:  # noqa: BLE001
        # Cota estourada ou Firestore fora do ar não podem virar tela de erro:
        # `compute_diagnostico_real` sabe devolver o perfil vazio sozinho, e o
        # painel sabe desenhar "ainda não dá para traçar" (ver
        # `project_aluno_incidente_cota_firestore`).
        logger.warning("painel: agregado indisponível para %s", user.user_id, exc_info=True)
        agregado = None

    diagnostico = await annotation_service.compute_diagnostico_real(
        user.user_id, agregado=agregado
    )
    prioridades = await cronograma_routes._prioridades(
        user.user_id, diagnostico=diagnostico
    )
    return perfil_painel.montar(
        telemetria=annotation_service.telemetria_de(agregado),
        prioridades=prioridades,
        forcas=perfil_pedagogico.perfil_de(diagnostico),
        diagnostico=diagnostico,
        avaliacoes_redacao=await _avaliacoes_de_redacao(user.user_id),
    )
