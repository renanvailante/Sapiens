"""Motor Cognitivo — rotas.

**Gratuito, como o `/diagnostico`:** isto é leitura e agregação sobre dados
que o próprio aluno gerou respondendo questões, com custo de inferência zero.
Nada aqui chama LLM, então nada aqui cobra Sparks. O que custa Sparks no app
continua sendo geração de conteúdo (Mentis, mapa cosmético), não medida
pedagógica.

Divisão de trabalho com o que já existia:

* `/diagnostico`  — desempenho medido + fato geral do catálogo. Não explica o
  erro de ninguém.
* `/skills-map`   — gamificação cosmética, nomes genéricos, custa Sparks.
* `/motor/*`      — **este**: Error Trace por resposta errada, mapa de causas
  raiz e intervenção catalogada para a habilidade que o aluno clicar.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

import firestore_service as fs
import motor_cognitivo
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.motor")

router = APIRouter(prefix="/motor", tags=["motor-cognitivo"])


@router.get("/perfil")
async def meu_perfil(user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    return await asyncio.to_thread(motor_cognitivo.perfil, user.user_id)


@router.get("/habilidade/{processo_id}")
async def minha_habilidade(processo_id: str, user: User = Depends(require_user)):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    detalhe = await asyncio.to_thread(motor_cognitivo.detalhe, user.user_id, processo_id)
    if detalhe is None:
        raise HTTPException(status_code=404, detail=f"Processo '{processo_id}' não existe no catálogo vigente.")
    return detalhe


# ---------------------------------------------------------------------------
# Visão interna (admin) — o motor olhando a base inteira
# ---------------------------------------------------------------------------


@router.get("/alunos/{uid}/perfil")
async def perfil_de_aluno(uid: str, _: User = Depends(require_admin)):
    return await asyncio.to_thread(motor_cognitivo.perfil, uid)


@router.get("/panorama")
async def panorama(
    limite_alunos: int = Query(50, ge=1, le=200),
    _: User = Depends(require_admin),
):
    """Quais causas RAIZ dominam a base, e em quantos alunos.

    Serve à decisão de conteúdo (que intervenção vale produzir primeiro) e à
    revisão de ontologia — que, sob GOV-1.0 §11.2 Classe B e Error Trace R-7,
    é **humana**: este endpoint informa, nunca altera o catálogo.

    O laço é sequencial de propósito: cada perfil varre o histórico de um
    aluno no Firestore, e disparar 200 varreduras em paralelo transformaria
    um painel de admin em pico de leitura no banco de produção.
    """
    alunos = await asyncio.to_thread(fs.list_students_with_behavior, limite_alunos)
    por_erro: dict[str, dict] = {}
    por_processo: dict[str, dict] = {}
    barrados = analisados = com_traco = 0

    for aluno in alunos:
        uid = aluno.get("student_id")
        if not uid:
            continue
        try:
            p = await asyncio.to_thread(motor_cognitivo.perfil, uid)
        except Exception:  # noqa: BLE001
            logger.exception("panorama: perfil falhou para %s", uid)
            continue
        analisados += 1
        barrados += p["portao"]["tracos_barrados"]
        if p["portao"]["tracos_no_perfil"]:
            com_traco += 1
        for linha in p["mapa_de_erros"]["raizes"]:
            balde = por_erro.setdefault(
                linha["erro_id"],
                {
                    "erro_id": linha["erro_id"],
                    "erro_nome": linha["erro_nome"],
                    "intervencao_id": linha["intervencao_id"],
                    "intervencao_nome": linha["intervencao_nome"],
                    "alunos": 0,
                    "ocorrencias": 0,
                    "peso": 0.0,
                },
            )
            balde["alunos"] += 1
            balde["ocorrencias"] += linha["ocorrencias"]
            balde["peso"] = round(balde["peso"] + linha["peso"], 3)
        for linha in p["habilidades_prioritarias"]:
            if linha["origem"] != "error_trace":
                continue
            balde = por_processo.setdefault(
                linha["processo_id"],
                {
                    "processo_id": linha["processo_id"],
                    "processo_nome": linha["processo_nome"],
                    "dominio_nome": linha["dominio_nome"],
                    "alunos": 0,
                    "peso": 0.0,
                },
            )
            balde["alunos"] += 1
            balde["peso"] = round(balde["peso"] + linha["peso_raiz"], 3)

    return {
        "alunos_analisados": analisados,
        "alunos_com_traco_valido": com_traco,
        "tracos_barrados_pelo_portao": barrados,
        "portao": motor_cognitivo.portao_crenca.modo(),
        "causas_raiz": sorted(por_erro.values(), key=lambda l: (-l["peso"], -l["alunos"])),
        "habilidades": sorted(por_processo.values(), key=lambda l: (-l["peso"], -l["alunos"])),
        "ontology_version": motor_cognitivo.ontology_version(),
    }
