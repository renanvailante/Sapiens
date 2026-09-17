"""Banco de treino (`HAB-01`..`HAB-56`) — balões de pontos fortes/fracos,
questões-base e o pedido (ainda em beta) de questões novas.

Três operações:

1. `GET /treino/habilidades` — lista as 56 habilidades com o desempenho do
   aluno (agregado O(1), ver `firestore_service.ler_treino_stats`), para
   colorir os balões.
2. `GET /treino/habilidade/{hab_id}/base` + `POST .../responder` — as
   questões-base já existentes (`treino_habilidades.py`), corrigidas no
   servidor. Cada resposta também escreve um evento de `student_behavior`
   (mesmo contrato do Enem, `contexto_tipo="treino_habilidade"`, namespace de
   `item_id` próprio — nunca colide com item real, então Motor Cognitivo e
   Diagnóstico real (que resolvem eventos contra a coleção `itens`) ignoram
   estes eventos automaticamente, sem precisar de nenhum filtro extra).
3. `POST /treino/habilidade/{hab_id}/gerar` — 3 Sparks por questão nova.
   Gera de verdade via Gemini, mas primeiro tenta servir do pool
   compartilhado (`treino_questoes_ia`): a primeira pessoa a pedir prática
   numa habilidade paga a geração, os próximos reaproveitam sem gastar Gemini
   de novo — cobrados do mesmo jeito, porque o valor entregue é o mesmo
   (mesmo princípio de `mentis_routes._CACHE_PREFIXO`). Mesma reivindicação
   idempotente por `idempotency_key` do corretor de redação
   (`redacao_routes.py`) — duplo clique ou retry não cobram duas vezes, e uma
   queda do processo entre cobrança e reembolso é recuperável (TTL de
   retomada). As questões entregues ficam em "Minhas questões"
   (`GET /treino/questoes-geradas`) — nunca são refeitas ao reabrir a tela.
4. `GET /treino/questoes-geradas` + `POST .../responder` — lista e corrige as
   questões de IA já entregues a este aluno. Mesmo contrato de behavior e de
   Sparks por resposta do item 2, só que sobre `treino_questoes_ia` em vez do
   banco estático.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

import ai_service
import engajamento_service
import firestore_service as fs
import llm_cache
import llm_telemetry
import rate_limit
import treino_habilidades as th
import treino_grafo_v0_2 as tg
from auth import require_user
from models import User

logger = logging.getLogger("sapiens.treino")

router = APIRouter(prefix="/treino", tags=["treino"])

_db = None


def set_db(db):
    global _db
    _db = db


CUSTO_POR_QUESTAO = th.CUSTO_POR_QUESTAO_NOVA
# Orçamento TOTAL (primário + reserva) desde 17/09 — ver
# `ai_service.generate_json_resiliente`. Gerar questão é o único chamador
# interativo que legitimamente escreve muito (enunciado + 5 alternativas +
# justificativa, vezes a quantidade pedida), então o teto de saída escala com
# o pedido em vez de ser fixo, e o de tempo é maior que os 10 s dos demais.
_TIMEOUT_QUESTOES_IA = 20.0
_MAX_TOKENS_POR_QUESTAO_IA = 700
_ONTOLOGY_VERSION_QUESTOES_IA = "treino-questoes-ia-1.0"

# Igual a `redacao_routes._RECLAMACAO_TTL_SEGUNDOS`: o pedido termina em
# milissegundos (não há geração de verdade), este teto só existe para o caso
# de a instância morrer no meio e não deixar a chave do aluno queimada.
_RECLAMACAO_TTL_SEGUNDOS = 120

_FORTE_MIN_RESPOSTAS = 3
_FORTE_LIMIAR = 0.70
_FRACO_LIMIAR = 0.40


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _classificacao(respondidas: int, acertos: int) -> str:
    if respondidas < _FORTE_MIN_RESPOSTAS:
        return "sem_dados"
    taxa = acertos / respondidas
    if taxa >= _FORTE_LIMIAR:
        return "forte"
    if taxa <= _FRACO_LIMIAR:
        return "fraco"
    return "neutro"


@router.get("/habilidades")
async def listar_habilidades(user: User = Depends(require_user)):
    stats = fs.ler_treino_stats(user.user_id)
    habilidades = []
    for h in th.listar_habilidades():
        s = stats.get(h["hab_id"], {"respondidas": 0, "acertos": 0})
        respondidas, acertos = s["respondidas"], s["acertos"]
        percentual = round(100 * acertos / respondidas, 1) if respondidas else None
        habilidades.append({
            **h,
            "respondidas": respondidas,
            "acertos": acertos,
            "percentual": percentual,
            "classificacao": _classificacao(respondidas, acertos),
        })
    return {"habilidades": habilidades}


@router.get("/precos")
async def precos(_: User = Depends(require_user)):
    return {"custo_por_questao": CUSTO_POR_QUESTAO}


_NOMES_POR_HAB: dict[str, str] | None = None


def _nomes_por_hab() -> dict[str, str]:
    global _NOMES_POR_HAB
    if _NOMES_POR_HAB is None:
        _NOMES_POR_HAB = {h["hab_id"]: h["nome"] for h in th.listar_habilidades()}
    return _NOMES_POR_HAB


def _bfs_distancias(seeds: set[str]) -> dict[str, int]:
    """Distância (em arestas do grafo `treino_grafo_v0_2`) de cada
    habilidade ao conjunto `seeds`. Só decide o quanto do mapa já foi
    EXPOSTO ao aluno (`estado`); o que está de fato dominado vem sempre de
    `treino_agregado`, nunca desta distância."""
    dist = {s: 0 for s in seeds}
    fila = deque(seeds)
    while fila:
        atual = fila.popleft()
        for vizinho in tg.vizinhos(atual):
            if vizinho not in dist:
                dist[vizinho] = dist[atual] + 1
                fila.append(vizinho)
    return dist


def _estado_no(stats_hab: dict[str, int], distancia: int | None) -> str:
    if stats_hab.get("respondidas", 0) > 0:
        classificacao = _classificacao(stats_hab["respondidas"], stats_hab["acertos"])
        return "mastered" if classificacao == "forte" else "in_progress"
    if distancia is None:
        return "unknown"
    if distancia <= 1:
        return "available"
    if distancia <= 3:
        return "discovered"
    return "unknown"


@router.get("/mapa")
async def obter_mapa(user: User = Depends(require_user)):
    """Mapa de exploração: as mesmas 56 habilidades de sempre, num único
    grafo contínuo (`treino_grafo_v0_2`) agrupado em 6 biomas de experiência
    — nunca nos domínios/processos/competências da ontologia oficial, que
    o aluno nunca vê. Não existe território "bloqueado": cada habilidade
    tem um `estado` (unknown/discovered/available/in_progress/mastered)
    calculado pela distância, no grafo, até o que o aluno já respondeu (mais
    um ponto de entrada por bioma, sempre disponível) — dominar uma
    habilidade estende essa distância e revela o entorno dela no próximo
    carregamento do mapa, sem nenhum cadeado explícito."""
    stats = fs.ler_treino_stats(user.user_id)
    nomes = _nomes_por_hab()
    respondidas_ids = {h for h, s in stats.items() if s.get("respondidas", 0) > 0}
    entradas = {bioma["habilidades"][0] for bioma in tg.BIOMAS}
    distancias = _bfs_distancias(respondidas_ids | entradas)
    posicoes = tg.layout()

    biomas_saida = []
    for bioma in tg.BIOMAS:
        nodes = []
        dominadas = 0
        visiveis = 0
        for hab_id in bioma["habilidades"]:
            s = stats.get(hab_id, {"respondidas": 0, "acertos": 0})
            estado = _estado_no(s, distancias.get(hab_id))
            if estado == "mastered":
                dominadas += 1
            if estado != "unknown":
                visiveis += 1
            x, y = posicoes[hab_id]
            nodes.append({
                "hab_id": hab_id,
                "nome": nomes[hab_id],
                "x": x, "y": y,
                "estado": estado,
                "respondidas": s.get("respondidas", 0),
                "acertos": s.get("acertos", 0),
            })
        biomas_saida.append({
            "bioma_id": bioma["bioma_id"],
            "nome": bioma["nome"],
            "ideia": bioma["ideia"],
            "resumo": bioma["resumo"],
            "nodes": nodes,
            "total": len(nodes),
            "visiveis": visiveis,
            "dominadas": dominadas,
        })

    arestas_saida = [
        {"source": a["source"], "target": a["target"], "relation": a["relation"]}
        for a in tg.ARESTAS
    ]

    return {
        "biomas": biomas_saida,
        "arestas": arestas_saida,
        "sparks_balance": fs.read_sparks_balance(user.user_id),
        "custo_conceito": CONCEITO_EXPLICACAO_COST,
    }


# ---------- "Aprofundar com a Mentis" — explicação de conceito sob demanda ----------

CONCEITO_EXPLICACAO_COST = 10
_CONCEITO_CACHE_PREFIXO = "treino_conceito"
_TIMEOUT_CONCEITO = 10.0
_MAX_TOKENS_CONCEITO = 900

_CONCEITO_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens, uma plataforma de preparação
para o ENEM. Um aluno concluiu uma missão de treino e pediu para aprofundar um conceito
específico que apareceu nela.

Escreva uma explicação em 2 a 4 parágrafos curtos, em português do Brasil, clara e concreta,
com ao menos um exemplo do mundo real (fora da prova) de onde esse conceito aparece. Tom
direto e adulto — nunca infantilizado, nunca em formato de lista.

Responda em JSON: {"paragrafos": ["...", "...", ...]}
Sem markdown, sem prefixos, apenas o JSON."""


class ConceitoPayload(BaseModel):
    hab_id: str
    conceito: str = Field(..., min_length=2, max_length=140)


def _montar_prompt_conceito(hab_nome: str, bioma_nome: str, bioma_ideia: str, conceito: str) -> str:
    return (
        f"Habilidade em treino: {hab_nome}\n"
        f"Bioma de exploração: {bioma_nome} — {bioma_ideia}\n"
        f"Conceito que o aluno quer aprofundar: {conceito}\n"
    )


def _validar_paragrafos_conceito(resultado: Any) -> list[str]:
    if not isinstance(resultado, dict):
        raise ValueError("Resposta do Gemini não é um objeto JSON.")
    paragrafos = resultado.get("paragrafos")
    if not isinstance(paragrafos, list):
        raise ValueError("Campo 'paragrafos' ausente ou inválido.")
    paragrafos = [p.strip() for p in paragrafos if isinstance(p, str) and p.strip()]
    if len(paragrafos) < 2:
        raise ValueError(f"Só {len(paragrafos)} parágrafo(s) válido(s) — mínimo 2.")
    return paragrafos


@router.post("/conceito/explicar")
async def explicar_conceito(
    payload: ConceitoPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    """Aprofundamento opcional de um conceito — sempre depois de a missão já
    ter sido cumprida, nunca no caminho do aprendizado básico. Mesmo padrão
    de `mentis_routes.gerar_explicacao`: cache por chave estável, cobra só
    quando gera de verdade, e devolve os Sparks se o modelo falhar."""
    nomes = _nomes_por_hab()
    hab_nome = nomes.get(payload.hab_id)
    if hab_nome is None:
        raise HTTPException(status_code=404, detail=f"Habilidade {payload.hab_id} não encontrada.")
    bioma_id = tg.BIOMA_POR_HAB.get(payload.hab_id)
    bioma = tg.BIOMA_POR_ID.get(bioma_id, {})

    chave = llm_cache.cache_key(_CONCEITO_CACHE_PREFIXO, payload.hab_id, payload.conceito.strip().lower())
    cache_hit = await llm_cache.get(_db.treino_conceitos, chave)
    if cache_hit is not None:
        return {"paragrafos": cache_hit, "sparks_balance": fs.read_sparks_balance(user.user_id), "cobrado": False}

    saldo = _cobrar(user.user_id, CONCEITO_EXPLICACAO_COST)
    prompt = _montar_prompt_conceito(hab_nome, bioma.get("nome", ""), bioma.get("ideia", ""), payload.conceito)
    inicio = time.monotonic()
    try:
        resultado = await ai_service.generate_json_resiliente(
            _CONCEITO_SYSTEM, prompt, thinking_level="MINIMAL", timeout=_TIMEOUT_CONCEITO,
            max_output_tokens=_MAX_TOKENS_CONCEITO,
        )
        paragrafos = _validar_paragrafos_conceito(resultado)
        await llm_telemetry.persist(
            _db.mentis_llm_chamadas,
            contexto=f"hab_id={payload.hab_id}",
            motivo="aprofundamento de conceito pedido pelo aluno (Treino)",
            modelo="gemini (thinking=MINIMAL)",
            thinking_level="MINIMAL",
            resultado_estado="ok",
            duration_ms=(time.monotonic() - inicio) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        saldo = _safe_reembolso(user.user_id, CONCEITO_EXPLICACAO_COST)
        logger.exception(
            "Treino: aprofundamento de conceito falhou para hab_id=%s — %d Sparks devolvidos (saldo: %s).",
            payload.hab_id, CONCEITO_EXPLICACAO_COST, saldo,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível aprofundar esse conceito agora. Seus Sparks foram devolvidos.",
        ) from exc

    await llm_cache.set(_db.treino_conceitos, chave, paragrafos)
    return {"paragrafos": paragrafos, "sparks_balance": saldo, "cobrado": True}


@router.get("/habilidade/{hab_id}/base")
async def obter_base(hab_id: str, user: User = Depends(require_user)):
    try:
        base = th.obter_base(hab_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Habilidade {hab_id} não encontrada.")
    stats = fs.ler_treino_stats(user.user_id).get(hab_id, {"respondidas": 0, "acertos": 0})
    return {**base, **stats}


class ResponderRequest(BaseModel):
    indice: int = Field(..., ge=1)
    alternativa: str = Field(..., min_length=1, max_length=1)


@router.post("/habilidade/{hab_id}/responder")
async def responder(hab_id: str, payload: ResponderRequest, user: User = Depends(require_user)):
    try:
        base = th.obter_base(hab_id)
        resultado = th.checar_resposta(hab_id, payload.indice, payload.alternativa.upper())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    item_id = f"TREINO:{hab_id}:{payload.indice}"
    questao_publica = next(q for q in base["questoes"] if q["indice"] == payload.indice)
    fs.write_behavior_event(
        user.user_id,
        item_id=item_id,
        ontology_version=th.ONTOLOGY_VERSION_TREINO,
        alternativa_escolhida=payload.alternativa.upper(),
        acertou=resultado["acertou"],
        item_content=questao_publica,
        contexto_tipo="treino_habilidade",
        origem="treino_local",
    )
    fs.increment_treino_stats(user.user_id, hab_id, resultado["acertou"])

    # Economia de Sparks 2026-09: +1 Spark por questão de treino de
    # habilidade CONCLUÍDA (certo ou errado — o que conta é ter praticado),
    # uma vez só por `item_id`. Responder a mesma questão de novo (revisão,
    # refresh) nunca credita de novo — garantia atômica de
    # `grant_question_sparks` (mesmo `DocumentReference.create()` que
    # `grant_round_sparks`/`grant_purchase_sparks` já usam).
    ganho = fs.grant_question_sparks(user.user_id, item_id)

    # Mesmo XP da questão do ENEM: praticar é praticar. O contador `treino` é
    # o que a missão "10 questões do banco de treino" lê.
    await engajamento_service.registrar_acao(
        user.user_id,
        ["questao_respondida"] + (["questao_correta"] if resultado["acertou"] else []),
        contadores={"treino": 1, "questoes": 1, "acertos": 1 if resultado["acertou"] else 0},
        nome=user.name,
    )

    stats = fs.ler_treino_stats(user.user_id).get(hab_id, {"respondidas": 0, "acertos": 0})
    return {
        **resultado,
        "hab_id": hab_id,
        "indice": payload.indice,
        "respondidas": stats["respondidas"],
        "acertos": stats["acertos"],
        "classificacao": _classificacao(stats["respondidas"], stats["acertos"]),
        "sparks_ganhos": 0 if ganho["ja_concedido"] else ganho["sparks_ganhos"],
        "sparks_balance": fs.read_sparks_balance(user.user_id),
    }


# ---------- Geração de questões novas (beta indisponível) ----------


class GerarRequest(BaseModel):
    quantidade: int = Field(..., ge=1, le=10)
    dificuldade: str
    idempotency_key: str = Field(..., min_length=8, max_length=100)


def _safe_reembolso(uid: str, custo: int) -> int | None:
    """Mesmo contrato de `redacao_routes._safe_reembolso`: devolver os
    Sparks não pode virar um segundo erro em cima do primeiro."""
    try:
        return fs.refund_sparks(uid, custo)
    except Exception:  # noqa: BLE001
        logger.exception("REEMBOLSO FALHOU (treino): %d Sparks devidos a %s.", custo, uid)
        return None


def _cobrar(uid: str, custo: int) -> int:
    fs.ensure_sparks_balance(uid)
    try:
        return fs.deduct_sparks(uid, custo)
    except fs.InsufficientSparksError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        ) from exc


async def _reivindicar(claim_id: str, base: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Mesmo contrato de `redacao_routes._reivindicar` — ver lá a explicação
    completa de por que existe uma reivindicação em vez de só um índice
    único no Mongo."""
    colecao = _db.treino_geracoes
    agora = _iso(_agora())
    try:
        doc = {**base, "_id": claim_id, "status": "processando",
               "cobrado": False, "criado_em": agora, "atualizado_em": agora}
        await colecao.insert_one(doc)
        return doc, True
    except DuplicateKeyError:
        pass

    limite = _iso(_agora() - timedelta(seconds=_RECLAMACAO_TTL_SEGUNDOS))
    retomado = await colecao.find_one_and_update(
        {"_id": claim_id, "status": "processando", "atualizado_em": {"$lt": limite}},
        {"$set": {"atualizado_em": agora}},
        return_document=True,
    )
    if retomado is not None:
        logger.warning("treino: reivindicação %s retomada após %ss parada.", claim_id, _RECLAMACAO_TTL_SEGUNDOS)
        return retomado, True

    doc = await colecao.find_one({"_id": claim_id})
    return doc or {}, False


async def _marcar_concluida(claim_id: str, resposta: dict[str, Any]) -> None:
    await _db.treino_geracoes.update_one(
        {"_id": claim_id},
        {"$set": {"status": "concluida", "resposta": resposta, "atualizado_em": _iso(_agora())}},
    )


async def _marcar_cobrado(claim_id: str, saldo: int | None) -> None:
    await _db.treino_geracoes.update_one(
        {"_id": claim_id},
        {"$set": {"cobrado": True, "saldo_apos_cobranca": saldo, "atualizado_em": _iso(_agora())}},
    )


async def _liberar(claim_id: str) -> None:
    try:
        await _db.treino_geracoes.delete_one({"_id": claim_id})
    except Exception:  # noqa: BLE001
        logger.exception("treino: não foi possível liberar a reivindicação %s", claim_id)


_QUESTAO_IA_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens. Gere questões de
múltipla escolha, estilo ENEM, para PRÁTICA de uma habilidade específica.

Estas questões são REUTILIZÁVEIS: ficam salvas e serão mostradas a qualquer aluno que praticar
esta habilidade depois — nunca mencione um aluno específico nem um erro que alguém tenha
cometido.

Cada questão: enunciado claro e autocontido (sem depender de imagem ou tabela), exatamente 5
alternativas (A a E), com UMA única correta e 4 distratores plausíveis — erros de raciocínio
reais, nunca alternativas absurdas descartáveis à primeira vista. Escreva também uma elucidação
(2 a 4 frases) explicando a resolução e por que os distratores enganam.

Responda EXCLUSIVAMENTE com JSON no formato:
{"questoes": [{"enunciado": "...", "alternativas": [{"letra":"A","texto":"..."}, {"letra":"B","texto":"..."}, {"letra":"C","texto":"..."}, {"letra":"D","texto":"..."}, {"letra":"E","texto":"..."}], "correta": "A", "elucidacao": "..."}]}
Sem markdown, sem texto fora do JSON."""


def _montar_prompt_questao_ia(hab_nome: str, dificuldade: str, quantidade: int) -> str:
    return (
        f"Habilidade: {hab_nome}\n"
        f"Dificuldade: {dificuldade}\n"
        f"Gere exatamente {quantidade} questão(ões) inédita(s) sobre esta habilidade, nesta dificuldade."
    )


def _validar_questoes_ia(resultado: Any, dificuldade: str) -> list[dict[str, Any]]:
    """Aceita só questões com as 5 letras completas e gabarito consistente —
    uma questão malformada é descartada, não derruba o lote inteiro."""
    if not isinstance(resultado, dict):
        raise ValueError("Resposta do Gemini não é um objeto JSON.")
    brutas = resultado.get("questoes")
    if not isinstance(brutas, list):
        raise ValueError("Campo 'questoes' ausente ou inválido.")

    validas: list[dict[str, Any]] = []
    for q in brutas:
        if not isinstance(q, dict):
            continue
        enunciado = q.get("enunciado")
        alternativas = q.get("alternativas")
        correta = q.get("correta")
        elucidacao = q.get("elucidacao")
        if not isinstance(enunciado, str) or not enunciado.strip():
            continue
        if not isinstance(alternativas, list) or len(alternativas) != 5:
            continue
        if not all(isinstance(a, dict) and isinstance(a.get("letra"), str) and isinstance(a.get("texto"), str) for a in alternativas):
            continue
        letras = {a["letra"].strip().upper() for a in alternativas}
        if letras != {"A", "B", "C", "D", "E"}:
            continue
        if not isinstance(correta, str) or correta.strip().upper() not in letras:
            continue
        if not isinstance(elucidacao, str) or not elucidacao.strip():
            continue
        validas.append({
            "enunciado_antes": enunciado.strip(),
            "tabela": None,
            "enunciado_depois": "",
            "alternativas": [
                {"letra": a["letra"].strip().upper(), "texto": a["texto"].strip()} for a in alternativas
            ],
            "gabarito": [correta.strip().upper()],
            "elucidacao": elucidacao.strip(),
            "dificuldade": dificuldade,
        })
    return validas


@router.post("/habilidade/{hab_id}/gerar")
async def gerar_questoes(hab_id: str, payload: GerarRequest, user: User = Depends(require_user)):
    try:
        th.obter_base(hab_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Habilidade {hab_id} não encontrada.")
    if payload.dificuldade not in th.DIFICULDADES_VALIDAS:
        raise HTTPException(
            status_code=422,
            detail=f"Dificuldade inválida: {payload.dificuldade!r}. Use uma de {th.DIFICULDADES_VALIDAS}.",
        )

    custo_total = CUSTO_POR_QUESTAO * payload.quantidade
    claim_id = f"{user.user_id}:{payload.idempotency_key}"
    claim, sou_o_dono = await _reivindicar(
        claim_id, {"user_id": user.user_id, "tipo": "geracao_treino", "hab_id": hab_id},
    )

    if not sou_o_dono:
        if claim.get("status") == "concluida" and claim.get("resposta"):
            return claim["resposta"]
        raise HTTPException(
            status_code=409,
            detail="Este pedido já está sendo processado. Aguarde alguns segundos.",
        )

    if claim.get("cobrado"):
        saldo_apos_cobranca = claim.get("saldo_apos_cobranca")
    else:
        try:
            saldo_apos_cobranca = _cobrar(user.user_id, custo_total)
        except HTTPException:
            await _liberar(claim_id)
            raise
        await _marcar_cobrado(claim_id, saldo_apos_cobranca)

    # Reaproveitamento primeiro: questões desta habilidade que este aluno
    # ainda não recebeu. Só chama o Gemini pelo que falta — a mesma questão
    # nunca é gerada duas vezes, e o segundo aluno a pedir prática nesta
    # habilidade paga os mesmos Sparks pelo trabalho que o primeiro já pagou.
    pool = [doc async for doc in _db.treino_questoes_ia.find(
        {"hab_id": hab_id, "mostrada_para": {"$ne": user.user_id}}
    ).limit(payload.quantidade)]

    faltam = payload.quantidade - len(pool)
    novas: list[dict[str, Any]] = []
    if faltam > 0:
        hab_nome = _nomes_por_hab().get(hab_id, hab_id)
        prompt = _montar_prompt_questao_ia(hab_nome, payload.dificuldade, faltam)
        inicio = time.monotonic()
        try:
            resultado = await ai_service.generate_json_resiliente(
                _QUESTAO_IA_SYSTEM, prompt, thinking_level="MINIMAL", timeout=_TIMEOUT_QUESTOES_IA,
                max_output_tokens=_MAX_TOKENS_POR_QUESTAO_IA * max(1, faltam),
            )
            # Trunca em `faltam`: o Gemini pode devolver mais questões válidas
            # do que o pedido (o prompt pede uma quantidade, não é um teto
            # rígido) — sem isto, `quantidade_entregue` passaria do pedido e
            # o cálculo de devolução abaixo viraria negativo.
            validas = _validar_questoes_ia(resultado, payload.dificuldade)[:faltam]
            await llm_telemetry.persist(
                _db.mentis_llm_chamadas,
                contexto=f"hab_id={hab_id}",
                motivo="geração de questões novas de treino (Mentis)",
                modelo="gemini (thinking=MINIMAL)",
                thinking_level="MINIMAL",
                resultado_estado="ok",
                duration_ms=(time.monotonic() - inicio) * 1000,
            )
            agora_iso = _iso(_agora())
            novas = [
                {
                    "_id": uuid.uuid4().hex,
                    "hab_id": hab_id,
                    "origem": "mentis_ia",
                    "gerada_em": agora_iso,
                    "gerada_por_uid": user.user_id,
                    "questao": q,
                    "mostrada_para": [],
                    "respostas": {},
                }
                for q in validas
            ]
            if novas:
                await _db.treino_questoes_ia.insert_many(novas)
        except Exception:  # noqa: BLE001
            # Não interrompe a resposta: o aluno ainda recebe o que já havia
            # no pool, e o que faltar é devolvido em Sparks abaixo.
            logger.exception("treino: geração de questões IA falhou para hab_id=%s", hab_id)

    entregues = pool + novas
    if entregues:
        await _db.treino_questoes_ia.update_many(
            {"_id": {"$in": [d["_id"] for d in entregues]}},
            {"$addToSet": {"mostrada_para": user.user_id}},
        )

    quantidade_entregue = len(entregues)
    quantidade_faltante = payload.quantidade - quantidade_entregue
    if quantidade_faltante > 0:
        _safe_reembolso(user.user_id, quantidade_faltante * CUSTO_POR_QUESTAO)

    if quantidade_entregue == 0:
        resposta = {
            "status": "falhou",
            "hab_id": hab_id,
            "quantidade": 0,
            "dificuldade": payload.dificuldade,
            "sparks_cobrados": 0,
            "sparks_devolvidos": custo_total,
            "sparks_balance": fs.read_sparks_balance(user.user_id),
            "mensagem": "Não foi possível gerar questões agora. Seus Sparks foram devolvidos.",
        }
    else:
        resposta = {
            "status": "ok",
            "hab_id": hab_id,
            "quantidade": quantidade_entregue,
            "dificuldade": payload.dificuldade,
            "sparks_cobrados": quantidade_entregue * CUSTO_POR_QUESTAO,
            "sparks_devolvidos": quantidade_faltante * CUSTO_POR_QUESTAO,
            "sparks_balance": fs.read_sparks_balance(user.user_id),
            "mensagem": (
                f"{quantidade_entregue} questão(ões) nova(s) pronta(s) em Minhas questões."
                + (
                    f" {quantidade_faltante} não puderam ser geradas agora e foram devolvidas."
                    if quantidade_faltante > 0 else ""
                )
            ),
        }
    await _marcar_concluida(claim_id, resposta)
    return resposta


# ---------- Minhas questões: listar e responder o que a Mentis já gerou ----------


def _questao_ia_sem_gabarito(doc: dict[str, Any]) -> dict[str, Any]:
    q = doc["questao"]
    return {
        "questao_id": doc["_id"],
        "hab_id": doc["hab_id"],
        "dificuldade": q["dificuldade"],
        "enunciado_antes": q["enunciado_antes"],
        "tabela": q["tabela"],
        "enunciado_depois": q["enunciado_depois"],
        "alternativas": q["alternativas"],
        "gerada_em": doc["gerada_em"],
    }


@router.get("/questoes-geradas")
async def listar_questoes_geradas(hab_id: str | None = None, user: User = Depends(require_user)):
    """As questões que a Mentis já gerou (ou reaproveitou) para este aluno —
    nunca refeitas ao reabrir a tela, só lidas daqui."""
    filtro: dict[str, Any] = {"mostrada_para": user.user_id}
    if hab_id:
        filtro["hab_id"] = hab_id
    nomes = _nomes_por_hab()
    docs = [
        doc async for doc in
        _db.treino_questoes_ia.find(filtro).sort("gerada_em", -1).limit(200)
    ]
    itens = []
    for doc in docs:
        resposta_aluno = (doc.get("respostas") or {}).get(user.user_id)
        item = _questao_ia_sem_gabarito(doc)
        item["habilidade_nome"] = nomes.get(doc["hab_id"], doc["hab_id"])
        item["respondida"] = resposta_aluno is not None
        if resposta_aluno:
            item["minha_resposta"] = resposta_aluno.get("alternativa")
            item["acertou"] = resposta_aluno.get("acertou")
        itens.append(item)
    return {"itens": itens}


class ResponderQuestaoIARequest(BaseModel):
    alternativa: str = Field(..., min_length=1, max_length=1)


@router.post("/questoes-geradas/{questao_id}/responder")
async def responder_questao_ia(questao_id: str, payload: ResponderQuestaoIARequest, user: User = Depends(require_user)):
    doc = await _db.treino_questoes_ia.find_one({"_id": questao_id})
    if doc is None or user.user_id not in (doc.get("mostrada_para") or []):
        raise HTTPException(status_code=404, detail="Questão não encontrada.")

    alternativa = payload.alternativa.upper()
    letras_validas = {a["letra"] for a in doc["questao"]["alternativas"]}
    if alternativa not in letras_validas:
        raise HTTPException(status_code=422, detail=f"Alternativa {alternativa!r} não existe nesta questão.")

    ja_respondida = (doc.get("respostas") or {}).get(user.user_id)
    if ja_respondida is not None:
        # Idempotente: reabrir e responder de novo não reescreve behavior nem
        # concede Sparks duas vezes — devolve o mesmo resultado de antes.
        acertou = ja_respondida["acertou"]
    else:
        acertou = alternativa in doc["questao"]["gabarito"]
        agora_iso = _iso(_agora())
        item_id = f"TREINO-IA:{questao_id}"
        fs.write_behavior_event(
            user.user_id,
            item_id=item_id,
            ontology_version=_ONTOLOGY_VERSION_QUESTOES_IA,
            alternativa_escolhida=alternativa,
            acertou=acertou,
            item_content=_questao_ia_sem_gabarito(doc),
            contexto_tipo="treino_questao_ia",
            origem="mentis_ia",
        )
        fs.grant_question_sparks(user.user_id, item_id)
        await _db.treino_questoes_ia.update_one(
            {"_id": questao_id},
            {"$set": {f"respostas.{user.user_id}": {"alternativa": alternativa, "acertou": acertou, "em": agora_iso}}},
        )

    return {
        "questao_id": questao_id,
        "acertou": acertou,
        "gabarito": doc["questao"]["gabarito"],
        "elucidacao": doc["questao"]["elucidacao"],
        "sparks_balance": fs.read_sparks_balance(user.user_id),
    }
