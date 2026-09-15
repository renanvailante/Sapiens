"""FastAPI routes for Firestore-backed pipeline & student behavior.

Todas as rotas sao protegidas pela sessao do proprio backend
(`auth.require_user`). Nao se usa Firebase Authentication.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

import rate_limit
from firestore_http import safe_call as _safe_call
from auth import require_user, require_admin
from models import User
import ai_service
import annotation_service
import engajamento_service
import firestore_service as fs
import microdiagnostico
import revisao_service
from feedback_templates import build_feedback, causa_raiz

logger = logging.getLogger("sapiens.firestore.routes")

router = APIRouter(prefix="/firestore", tags=["firestore"])

_db = None


def set_db(db):
    global _db
    _db = db


class AnswerPayload(BaseModel):
    item_id: str
    alternativa_escolhida: str
    tempo_resposta_segundos: float = 0
    numero_tentativas: int = 1
    mudou_resposta: bool = False
    contexto_tipo: str = "pratica_questoes"
    prova_id: Optional[str] = None
    dispositivo: Optional[str] = None
    versao_aplicacao: Optional[str] = None


class BehaviorProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reading_speed: Optional[str] = None
    confidence_level: Optional[str] = None
    attention_span: Optional[str] = None
    error_pattern: Optional[str] = None


class BehaviorFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")
    onboarded: Optional[bool] = None
    first_exam_done: Optional[bool] = None


class BehaviorPayload(BaseModel):
    """Only self-declared fields are writable by the student. Server-derived
    blocks (stats, events, identity) are never accepted from the client."""
    model_config = ConfigDict(extra="forbid")
    profile: Optional[BehaviorProfile] = None
    flags: Optional[BehaviorFlags] = None

    def to_update(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.profile:
            p = self.profile.model_dump(exclude_none=True)
            if p:
                out["profile"] = p
        if self.flags:
            f = self.flags.model_dump(exclude_none=True)
            if f:
                out["flags"] = f
        return out


# ---------- Reads: pipeline ----------

@router.get("/pipeline/questao")
async def list_questoes(limit: int = Query(100, ge=1, le=500), _: User = Depends(require_user)):
    return {"items": _safe_call(fs.read_collection, "pipeline/questao", limit)}


@router.get("/pipeline/questao/{doc_id}")
async def get_questao(doc_id: str, _: User = Depends(require_user)):
    doc = _safe_call(fs.read_document, "pipeline/questao", doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Questao not found")
    return doc


@router.get("/pipeline/fonte")
async def list_fontes(limit: int = Query(100, ge=1, le=500), _: User = Depends(require_user)):
    return {"items": _safe_call(fs.read_collection, "pipeline/fonte", limit)}


@router.get("/pipeline/fonte/{doc_id}")
async def get_fonte(doc_id: str, _: User = Depends(require_user)):
    doc = _safe_call(fs.read_document, "pipeline/fonte", doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Fonte not found")
    return doc


# ---------- Config: behavior_schema ----------

@router.get("/pipeline/config/behavior-schema")
async def get_behavior_schema(limit: int = Query(100, ge=1, le=500), _: User = Depends(require_user)):
    return {"items": _safe_call(fs.read_collection, "pipeline/config/behavior_schema", limit)}


# ---------- Student behavior ----------

@router.get("/students/me/respondidas")
async def minhas_respondidas(user: User = Depends(require_user)):
    """`item_id`s que este aluno já respondeu, do histórico de behavior real
    (Firestore, `students/{uid}/behavior`) — nunca inferido de outro lugar.

    Usado para retomar uma prova exatamente de onde o aluno parou: o
    frontend cruza esta lista com os itens do bloco que está exibindo e pula
    para o primeiro ainda não respondido. Não existe um "ponto de parada"
    gravado à parte — cada resposta já é um evento de behavior persistido no
    instante em que é enviada (`POST /students/me/answer`), então abandonar
    no meio nunca perde progresso: só não respondeu o que não respondeu.
    """
    agregado = _safe_call(fs.ler_agregado, user.user_id) or {}
    return {"item_ids": sorted(agregado.get("item_ids_respondidos") or [])}


@router.get("/students/me/behavior")
async def get_my_behavior(user: User = Depends(require_user)):
    # Auto-provision on first access — no Firebase Auth involved.
    _safe_call(fs.ensure_student_behavior, user.user_id, user.email, user.name)
    doc = _safe_call(fs.read_student_behavior, user.user_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Behavior document not found")
    return doc


@router.post("/students/me/ensure")
async def ensure_my_behavior(user: User = Depends(require_user)):
    """Idempotently create the student's behavior_student document.
    Called by the frontend on every successful login/session load. No Firebase Auth used —
    o chamador e autenticado pela sessao do proprio backend (require_user).
    """
    # Nova estrutura (Fase 1): cria students/{uid} (profile) no login se não existir.
    _safe_call(fs.ensure_student_profile, user.user_id, user.name, user.email)
    created = _safe_call(fs.ensure_student_behavior, user.user_id, user.email, user.name)
    doc = _safe_call(fs.read_student_behavior, user.user_id)
    return {"created": created, "user_id": user.user_id, "path": f"students_behavior/students_id/{user.user_id}/behavior_student", "doc": doc}


@router.put("/students/me/behavior")
async def upsert_my_behavior(payload: BehaviorPayload, user: User = Depends(require_user)):
    return _safe_call(fs.write_student_behavior, user.user_id, payload.to_update())


@router.post("/students/me/answer")
async def register_answer(payload: AnswerPayload, user: User = Depends(require_user)):
    """Registra a resposta do aluno a uma questão.

    Determina certo/errado **no servidor** a partir de `questoes_public` e grava
    o evento de behavior (contrato **1.1**) em `students/{uid}/behavior`.

    `ontology_version` e `item_hash` vêm do ITEM respondido, não da ontologia
    ativa nem de um recálculo: o contrato 1.1 pede a versão contra a qual o item
    **estava anotado no momento da resposta**, e o hash do conteúdo **daquele**
    momento. Recalcular o hash aqui produziria um valor que só por acaso
    coincidiria com o do item, e o casamento item↔evento falharia em silêncio.
    """
    doc = await _db.questoes_public.find_one({"item_id": payload.item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    questao = doc.get("questao") or {}
    alternativas = questao.get("alternativas") or []
    correta_letra = next((a.get("letra") for a in alternativas if a.get("correta") is True), None)
    acertou = (payload.alternativa_escolhida == correta_letra) if correta_letra is not None else None

    ontology_version = doc.get("ontology_version")
    if not ontology_version:
        # Item sincronizado antes da migração 2.2: não sabemos contra qual
        # catálogo ele foi anotado. Recusar é a única resposta correta —
        # gravar um evento sem versão o tornaria indatável para sempre.
        raise HTTPException(
            status_code=409,
            detail=(
                "Este item não declara 'ontology_version' e foi anotado antes do "
                "Schema 2.2. Rode a sincronização do pipeline (POST /admin/firestore/sync) "
                "para reingeri-lo sob o contrato vigente antes de aceitar respostas."
            ),
        )

    # Feedback qualitativo por TEMPLATES (sem IA): lookup no master.
    master = await _db.questoes_master.find_one({"id": doc.get("master_id")}, {"_id": 0})
    feedback = build_feedback(master, payload.alternativa_escolhida, acertou)

    _safe_call(fs.ensure_student_profile, user.user_id, user.name, user.email)
    evento = _safe_call(
        fs.write_behavior_event,
        user.user_id,
        item_id=payload.item_id,
        ontology_version=ontology_version,
        alternativa_escolhida=payload.alternativa_escolhida,
        acertou=acertou,
        item_schema_version=doc.get("item_schema_version"),
        item_hash=doc.get("item_hash"),
        item_content=questao,
        contexto_tipo=payload.contexto_tipo,
        prova_id=payload.prova_id,
        tempo_resposta_segundos=payload.tempo_resposta_segundos,
        numero_tentativas=payload.numero_tentativas,
        mudou_resposta=payload.mudou_resposta,
        dispositivo=payload.dispositivo,
        versao_aplicacao=payload.versao_aplicacao,
    )

    # Estado de revisão espaçada (Fase 1) + gatilho do Professor Invisível
    # (Fase 2), no MESMO ciclo da resposta.
    #
    # O item anotado sai de `master`, que já está carregado para o feedback —
    # nenhuma ida ao banco a mais. O custo somado das duas fases aqui é 1
    # leitura (memorizada por sessão) e 1 escrita, ambas no documento
    # `students/{uid}` que o agregado já usa; o gatilho é avaliado sobre o
    # bloco que a atualização acabou de produzir e por isso não custa leitura
    # nenhuma. Nada disto pode derrubar o registro da resposta: o evento já
    # está gravado quando chegamos aqui.
    revisao = {"gatilho": None}
    item_anotado = (master or {}).get("item") or (master or {}).get("pipeline") or master
    if evento:
        try:
            revisao = await asyncio.to_thread(
                revisao_service.registrar_resposta,
                user.user_id,
                item=item_anotado,
                evento=evento,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("revisão espaçada não atualizada para %s: %s", user.user_id, exc)

    # A causa raiz sai de graça: `master` já está carregado para o feedback, e
    # `causa_raiz` é a mesma leitura de cadeia, sem nenhuma ida ao banco. É ela
    # que habilita a Intervenção da Mentis logo depois do erro — sem isso, a
    # tela teria de perguntar ao servidor "esta resposta tem causa?" numa
    # segunda chamada, pagando de novo o que já estava na mão.
    raiz = None if acertou else causa_raiz(master, payload.alternativa_escolhida)

    # XP e contadores de missão. É a ÚNICA porta por onde XP entra pela
    # prática, e ela fica aqui, depois do evento de behavior já gravado, de
    # propósito: assim é impossível somar XP sem que exista uma resposta real
    # por trás. `registrar_acao` engole as próprias falhas (ver o docstring
    # dele) — perder XP é aborrecimento, perder a resposta é perder o estudo.
    await engajamento_service.registrar_acao(
        user.user_id,
        ["questao_respondida"] + (["questao_correta"] if acertou else []),
        contadores={"questoes": 1, "acertos": 1 if acertou else 0},
        nome=user.name,
    )

    return {
        "acertou": acertou,
        "correta": correta_letra,
        "feedback": feedback,
        "causa_raiz": raiz,
        "event_id": (evento or {}).get("event_id"),
        # O Professor Invisível: `None` quase sempre, de propósito. Uma
        # intervenção ativa por vez, cooldown por par, e só com evidência que
        # atinge o MESMO limiar que o motor já usa (`MIN_TRACOS_RAIZ`).
        "professor_invisivel": revisao.get("gatilho"),
        # Fase 3: a micropergunta, quando o distrator marcado tem cadeia
        # anotada e o par ainda tem poucas confirmações. Pular é indistinguível
        # de não ter recebido.
        "microdiagnostico": await microdiagnostico.perguntar_por(
            causa_raiz=raiz, acertou=acertou, event_id=(evento or {}).get("event_id") or ""
        ),
    }


class RespostaSessao(BaseModel):
    item_id: str
    alternativa_escolhida: str
    acertou: Optional[bool] = None


class SessaoDiagnosticoPayload(BaseModel):
    # Mínimo de 10: é o "pelo menos 10 questões" pedido — abaixo disso a
    # amostra é pequena demais para um padrão dizer algo real.
    respostas: list[RespostaSessao] = Field(..., min_length=10)


@router.post("/students/me/sessao/diagnostico")
async def diagnostico_sessao(
    payload: SessaoDiagnosticoPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    """Resumo em linguagem natural de uma sessão de prática (mín. 10 respostas).

    Não grava nada — o aluno já respondeu tudo isso via `/students/me/answer`
    (que já persistiu o evento de behavior de cada uma). Este endpoint só lê
    o item de cada resposta para montar o contexto e chama o Gemini UMA vez
    por sessão, com `thinking_level=LOW` (ver `ai_service.diagnose_sessao`).
    """
    respostas = [r.model_dump() for r in payload.respostas]
    contexto = await asyncio.to_thread(annotation_service.montar_contexto_sessao, respostas)
    return await ai_service.diagnose_sessao(contexto)


# ---------- Rodadas (progresso/devolutiva/Sparks) ----------
#
# Prova de 45 questões dividida em rodadas de 10 (a última fecha com o
# restante: 5, para um bloco de 45). Ao fim de cada rodada: devolutiva
# determinística (sem IA, ver `annotation_service.resumo_rodada`) + Sparks
# (+1 por acerto da rodada), concedidos no máximo uma vez por rodada.

RODADA_TAMANHO = 10


class BlocoRef(BaseModel):
    """Identifica um bloco/prova de até 45 questões — os mesmos 5 campos que
    `/api/provas` devolve e o frontend já guarda como `filtro`."""
    banca: Optional[str] = None
    ano: Optional[int] = None
    prova: Optional[str] = None
    numero_min: Optional[int] = None
    numero_max: Optional[int] = None


class RodadaConcluirPayload(BaseModel):
    bloco: BlocoRef
    rodada: int = Field(..., ge=1, le=5)


def _round_key(bloco: dict[str, Any], rodada: int) -> str:
    """Chave determinística e estável de `students/{uid}/sparks_rounds/{key}`.

    Determinística em (aluno, bloco, rodada): a mesma prova+rodada produz
    sempre a mesma chave, é isso que faz `DocumentReference.create()` (em
    `firestore_service.grant_round_sparks`) funcionar como trava de
    idempotência — chamar de novo bate no mesmo documento.
    """
    partes = [
        str(bloco.get("banca") or ""), str(bloco.get("ano") or ""), str(bloco.get("prova") or ""),
        str(bloco.get("numero_min") or ""), str(bloco.get("numero_max") or ""), f"r{rodada}",
    ]
    bruto = "-".join(partes)
    return re.sub(r"[^A-Za-z0-9_.-]", "_", bruto)[:400] or f"rodada-{rodada}"


def _rodada_range(numero_min: int, numero_max: int, rodada: int) -> tuple[int, int]:
    """`(numero_inicio, numero_fim)` da rodada dentro do bloco. Rodadas 1-4 têm
    10 questões; a última fecha com o que sobrar (5, para um bloco de 45) —
    nunca ultrapassa `numero_max`."""
    inicio = numero_min + (rodada - 1) * RODADA_TAMANHO
    fim = min(inicio + RODADA_TAMANHO - 1, numero_max)
    return inicio, fim


@router.post("/students/me/rodada/concluir")
async def concluir_rodada(payload: RodadaConcluirPayload, user: User = Depends(require_user)):
    """Devolutiva determinística da rodada (sem IA) + concessão idempotente de Sparks.

    Não recebe respostas do cliente: os `item_id`s da rodada são recalculados
    aqui a partir de `bloco`+`rodada` (mesma faixa `fonte.numero` que
    `/api/questoes` usa), e o acerto de cada um vem do que já está gravado em
    `students/{uid}/behavior` — o mesmo evento que `/students/me/answer` já
    persistiu. Isso evita que o cliente possa inflar Sparks só enviando uma
    lista de `item_id`s arbitrária.

    Repetir a chamada (retomada, refresh, corrida de rede) nunca credita Sparks
    duas vezes — ver a garantia atômica em `firestore_service.grant_round_sparks`.
    """
    bloco = payload.bloco.model_dump()
    numero_min, numero_max = bloco.get("numero_min"), bloco.get("numero_max")
    if numero_min is None or numero_max is None:
        raise HTTPException(status_code=422, detail="bloco.numero_min e bloco.numero_max são obrigatórios")

    inicio, fim = _rodada_range(numero_min, numero_max, payload.rodada)

    item_ids: list[str] = []
    if inicio <= fim:
        filtro: dict[str, Any] = {"fonte.numero": {"$gte": inicio, "$lte": fim}}
        if bloco.get("banca"):
            filtro["fonte.banca"] = bloco["banca"]
        if bloco.get("ano") is not None:
            filtro["fonte.ano"] = bloco["ano"]
        if bloco.get("prova"):
            filtro["fonte.prova"] = bloco["prova"]
        cursor = _db.questoes_public.find(filtro, {"_id": 0, "item_id": 1}).sort("fonte.numero", 1)
        item_ids = [doc["item_id"] async for doc in cursor if doc.get("item_id")]

    _safe_call(fs.ensure_student_profile, user.user_id, user.name, user.email)
    _safe_call(fs.ensure_sparks_balance, user.user_id)

    # Só os ~10 itens desta rodada, não o histórico inteiro: era uma leitura de
    # até 5.000 documentos do Firestore a cada rodada concluída — o custo
    # crescia com o engajamento do aluno, justamente quem mais fecha rodadas.
    por_item = _safe_call(fs.get_behavior_events_for_items, user.user_id, item_ids) or {}

    respostas = [
        {
            "item_id": item_id,
            "alternativa_escolhida": (por_item.get(item_id) or {}).get("resposta", {}).get("alternativa_escolhida"),
            "acertou": (por_item.get(item_id) or {}).get("resposta", {}).get("acertou"),
        }
        for item_id in item_ids
    ]

    resumo = await asyncio.to_thread(annotation_service.resumo_rodada, respostas)

    round_key = _round_key(bloco, payload.rodada)
    evolucao = None
    if payload.rodada > 1:
        anterior = _safe_call(fs.read_round, user.user_id, _round_key(bloco, payload.rodada - 1))
        if anterior and anterior.get("percentual_acerto") is not None:
            evolucao = round(resumo["percentual_acerto"] - anterior["percentual_acerto"], 1)

    resultado = _safe_call(
        fs.grant_round_sparks,
        user.user_id,
        round_key=round_key,
        bloco=bloco,
        rodada=payload.rodada,
        item_ids=item_ids,
        acertos=resumo["acertos"],
        erros=resumo["erros"],
        total=resumo["total"],
        percentual_acerto=resumo["percentual_acerto"],
        padroes_de_erro=resumo["padroes_de_erro"],
    )
    saldo_atual = _safe_call(fs.read_sparks_balance, user.user_id)

    return {
        "rodada": payload.rodada,
        "acertos": resultado.get("acertos", resumo["acertos"]),
        "erros": resultado.get("erros", resumo["erros"]),
        "total": resultado.get("total", resumo["total"]),
        "percentual_acerto": resultado.get("percentual_acerto", resumo["percentual_acerto"]),
        "evolucao": evolucao,
        "padroes_de_erro": resultado.get("padroes_de_erro", resumo["padroes_de_erro"]),
        "sparks_ganhos": resultado.get("sparks_ganhos", 0),
        "sparks_balance": saldo_atual,
        "ja_concedido": resultado.get("ja_concedido", False),
    }


@router.get("/students/me/sparks")
async def meus_sparks(user: User = Depends(require_user)):
    _safe_call(fs.ensure_student_profile, user.user_id, user.name, user.email)
    saldo = _safe_call(fs.ensure_sparks_balance, user.user_id)
    return {"sparks_balance": saldo}


@router.get("/students/me/activity")
async def minha_atividade(user: User = Depends(require_user)):
    """Datas com atividade registrada (behavior real) — usado pelo painel
    para sequência de estudos (streak) e progresso semanal."""
    dates = _safe_call(fs.get_activity_dates, user.user_id, 3000)
    return {"dates": dates}


@router.get("/students/me/rounds")
async def minhas_rodadas(user: User = Depends(require_user)):
    """Histórico de rodadas concluídas (10 questões, 5 na última do bloco) —
    já usado internamente pelo mapa de habilidades; exposto aqui pra
    `ExamSelect` mostrar tentativas anteriores por caderno (simulados como
    experiência contínua: progresso, desempenho anterior, comparação)."""
    rounds = _safe_call(fs.list_sparks_rounds, user.user_id, 300)
    return {"rounds": rounds}


# Admin-only: access by arbitrary uid (e.g. teacher/admin viewing a student)
@router.get("/students/{uid}/behavior")
async def get_behavior_by_uid(uid: str, _: User = Depends(require_admin)):
    doc = _safe_call(fs.read_student_behavior, uid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Behavior document not found")
    return doc
