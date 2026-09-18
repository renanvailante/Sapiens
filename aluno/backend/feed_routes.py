"""Learning feed routes: infinite cursor-based feed + interaction/progress capture.

A correção e o que desce para o navegador são `feed_conteudo` — este arquivo
só persiste e orquestra. `feed_comportamento` espelha cada resposta no
registro comportamental canônico (ver o módulo para o porquê); o resto da
interação (tempo, texto digitado, progresso de rolagem) continua em
`feed_interactions`/`feed_progress`, que é ESTADO DE PRODUTO, não claim
cognitivo, e não tem por que morar no Firestore.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import feed_comportamento as fb
import feed_conteudo as fc
import feed_ingestao as fi
from auth import require_admin, require_user
from feed_models import FeedInteractionIn, FeedProgressIn, FeedItem, FeedItemIn
from models import User

logger = logging.getLogger("sapiens.feed")
router = APIRouter(prefix="", tags=["feed"])

_db = None
def set_db(db):
    global _db
    _db = db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Public feed browsing (auth optional but recommended) ----------

@router.get("/feed")
async def get_feed(
    cursor: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=30),
):
    """Cursor-based infinite feed.

    `cursor` is the last sequence_order the client has already consumed.
    Returns items strictly after it, up to `limit`. Client should preload
    a few items ahead of the visible one to make swipe transitions instant.
    """
    q = {"sequence_order": {"$gt": cursor}, "published": True}
    items = await _db.feed_items.find(q, {"_id": 0}).sort("sequence_order", 1).limit(limit).to_list(limit)
    # `para_a_tela` é o único lugar que decide o que um card revela ANTES de
    # ser respondido — gabarito, feedback por alternativa, ordem certa do
    # `ordene`, pareamento do `relacione`. Ver `feed_conteudo` para a lista
    # completa; aqui não se repete a lógica.
    items = [fc.para_a_tela(it) for it in items]
    next_cursor = items[-1]["sequence_order"] if items else cursor
    has_more = False
    if items:
        remaining = await _db.feed_items.count_documents(
            {"sequence_order": {"$gt": next_cursor}, "published": True}
        )
        has_more = remaining > 0
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}


# ---------- Interactions (require auth) ----------

def _alternativa_para_behavior(tipo: str, resposta: dict) -> str | None:
    """O que vai em `resposta.alternativa_escolhida` do evento canônico.

    Autoavaliação (flashcard/revisão) não escolhe entre opções — é um
    julgamento sobre a própria memória — então não fabrica uma alternativa
    que não existiu. Os demais tipos com gabarito têm uma representação de
    texto natural: a letra escolhida, o texto digitado, ou a lista/pares na
    ordem em que o aluno montou.
    """
    if tipo == "ordene":
        ordem = resposta.get("ordem") or []
        return ",".join(str(i) for i in ordem) if ordem else None
    if tipo == "relacione":
        pares = resposta.get("pares") or {}
        return ";".join(f"{k}:{v}" for k, v in pares.items()) if pares else None
    if tipo == "desafio" and "texto" in resposta:
        return (resposta.get("texto") or "").strip() or None
    return resposta.get("selected")


@router.post("/feed/interactions")
async def log_interaction(payload: FeedInteractionIn, user: User = Depends(require_user)):
    """Append a raw interaction event, corrige a resposta e espelha o
    resultado no registro comportamental canônico.

    Multiple calls per card are allowed (view, answer, leave); events are
    appended to `interaction_history` on the same interaction doc keyed by
    (user, content). A correção nunca confia no que o cliente declarou —
    `feed_conteudo.corrigir` refaz o julgamento a partir do que está gravado.
    """
    item = await _db.feed_items.find_one({"content_id": payload.content_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    resposta_usuario = payload.user_response or {}
    is_correct, revelacao = fc.corrigir(item, resposta_usuario)

    now = _now()
    doc = await _db.feed_interactions.find_one(
        {"user_id": user.user_id, "content_id": payload.content_id}, {"_id": 0}
    )

    event = payload.event or {}
    if event and "at" not in event:
        event["at"] = now

    if doc:
        update = {
            "$inc": {"time_spent_ms": max(0, payload.time_spent_ms)},
            "$set": {},
        }
        if payload.completed:
            update["$set"]["completed"] = True
        if resposta_usuario:
            update["$set"]["user_response"] = resposta_usuario
        if is_correct is not None:
            update["$set"]["is_correct"] = is_correct
        if event:
            update["$push"] = {"interaction_history": event}
        if not update["$set"]:
            update.pop("$set")
        await _db.feed_interactions.update_one(
            {"user_id": user.user_id, "content_id": payload.content_id}, update
        )
    else:
        new_doc = {
            "interaction_id": _now(),  # ISO ts is fine as id here; unique
            "user_id": user.user_id,
            "content_id": payload.content_id,
            "time_spent_ms": max(0, payload.time_spent_ms),
            "completed": bool(payload.completed),
            "user_response": resposta_usuario,
            "is_correct": is_correct,
            "interaction_history": [event] if event else [],
            "created_at": now,
        }
        await _db.feed_interactions.insert_one(new_doc)

    # If item was completed, add to progress
    if payload.completed:
        await _db.feed_progress.update_one(
            {"user_id": user.user_id},
            {"$addToSet": {"completed_content_ids": payload.content_id},
             "$set": {"updated_at": now}},
            upsert=True,
        )

    # O evento canônico só existe quando ESTA chamada trouxe uma resposta de
    # verdade (não uma chamada de tempo-de-tela) e o tipo tem julgamento de
    # certo/errado ou autoavaliação — enquete e leitura pura ficam de fora,
    # mesma convenção de `cursos_comportamento` (ver o módulo).
    if resposta_usuario and is_correct is not None:
        await fb.registrar(
            user.user_id,
            card=item,
            card_na_tela=fc.para_a_tela(item),
            acertou=is_correct,
            alternativa=_alternativa_para_behavior(item.get("content_type"), resposta_usuario),
            tempo_segundos=(payload.time_spent_ms / 1000) if payload.time_spent_ms else None,
        )

    # O gabarito só é revelado depois de uma resposta de verdade.
    if resposta_usuario:
        return {"ok": True, "is_correct": is_correct, **revelacao}
    return {"ok": True}


# ---------- Progress ----------

@router.get("/feed/progress")
async def get_progress(user: User = Depends(require_user)):
    doc = await _db.feed_progress.find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"user_id": user.user_id, "last_position": 0, "last_content_id": None,
                "completed_content_ids": []}
    return doc


@router.post("/feed/progress")
async def set_progress(payload: FeedProgressIn, user: User = Depends(require_user)):
    await _db.feed_progress.update_one(
        {"user_id": user.user_id},
        {"$set": {"last_position": payload.last_position,
                  "last_content_id": payload.last_content_id,
                  "updated_at": _now()}},
        upsert=True,
    )
    return {"ok": True}


# ---------- Admin: publicar em lote a partir de texto ----------
#
# O caminho que o feed tinha era um card por vez: abrir o formulário, digitar
# cada campo, salvar, repetir — inviável para um feed de dezenas de cards.
# Aqui a pessoa cola um texto GRANDE, escrito à mão ou por um modelo de
# linguagem FORA do Sapiens, e o servidor faz o resto sozinho: corta em
# cards pelo cabeçalho de cada um, decide o tipo, embaralha alternativas,
# reparte feedback por distrator e valida contra `feed_conteudo`. O parsing é
# **100% determinístico** (`feed_ingestao`, puro Python, sem chamada a
# nenhuma IA) — o formato é um contrato que o Sapiens define e confere
# sozinho, nunca uma interpretação paga.
#
#     texto  →  COMPILAR (nada é gravado)  →  conferir  →  PUBLICAR
#
# Mesmo desenho do painel de cursos (`cursos_estudo_routes`): publicar sem ver
# o que o texto virou é publicar no escuro, porque o compilador toma decisões
# visíveis (posição das alternativas, feedback fatiado, tipo deduzido).


class TextoDeFeed(BaseModel):
    texto: str = Field(..., min_length=1, max_length=400_000)


@router.post("/admin/feed/compilar")
async def admin_compilar_feed(pedido: TextoDeFeed = Body(...), admin: User = Depends(require_admin)):
    """Mostra o que o texto VIRARIA. Não grava nada, em nenhuma hipótese."""
    compilado = fi.compilar(pedido.texto)
    return {
        "cards": compilado.cards,
        "problemas": compilado.problemas,
        "avisos": compilado.avisos,
        "pode_publicar": compilado.pode_publicar,
    }


@router.post("/admin/feed/publicar")
async def admin_publicar_feed(pedido: TextoDeFeed = Body(...), admin: User = Depends(require_admin)):
    """Compila, valida de novo (a prévia nunca é o que decide) e põe no ar.

    Publicar é ADITIVO, e o id do card é o hash do conteúdo dele
    (`feed_ingestao.id_do_card`): colar o MESMO texto duas vezes (um duplo
    clique, um lote reenviado por engano) não duplica nada — o card já existe
    e só é reafirmado na mesma posição. Um texto DIFERENTE para o "mesmo"
    card (uma frase reescrita, um distrator ajustado) tem um hash diferente e
    vira um card novo, no fim da fila; o antigo continua no ar até alguém
    apagá-lo na lista abaixo — publicar aqui nunca apaga silenciosamente o
    que já estava publicado.
    """
    compilado = fi.compilar(pedido.texto)
    if compilado.problemas or not compilado.cards:
        raise HTTPException(
            status_code=422,
            detail={"mensagem": "O texto não compilou nenhum card.", "problemas": compilado.problemas},
        )

    ordem_existente: dict[str, int] = {}
    async for doc in _db.feed_items.find({}, {"_id": 0, "content_id": 1, "sequence_order": 1}):
        ordem_existente[doc["content_id"]] = doc.get("sequence_order", 0)
    proxima_ordem = (max(ordem_existente.values()) if ordem_existente else 0) + 1

    novos, atualizados = 0, 0
    for card in compilado.cards:
        if card["content_id"] in ordem_existente:
            ordem = ordem_existente[card["content_id"]]
            atualizados += 1
        else:
            ordem = proxima_ordem
            proxima_ordem += 1
            novos += 1
        item = FeedItem(**{**card, "sequence_order": ordem})
        await _db.feed_items.update_one(
            {"content_id": item.content_id}, {"$set": item.model_dump()}, upsert=True,
        )

    logger.info(
        "Feed publicado por texto: %d novo(s), %d atualizado(s), por %s",
        novos, atualizados, admin.email,
    )
    return {
        "novos": novos,
        "atualizados": atualizados,
        "total": len(compilado.cards),
        "avisos": compilado.avisos,
    }


# ---------- Admin CRUD ----------

@router.get("/admin/feed-items")
async def admin_list_items(admin: User = Depends(require_admin)):
    items = await _db.feed_items.find({}, {"_id": 0}).sort("sequence_order", 1).to_list(1000)
    return items


@router.post("/admin/feed-items")
async def admin_create_item(payload: FeedItemIn, admin: User = Depends(require_admin)):
    if payload.sequence_order == 0:
        # Auto-assign next order
        last = await _db.feed_items.find_one({}, sort=[("sequence_order", -1)])
        seq = ((last or {}).get("sequence_order", 0) or 0) + 1
    else:
        seq = payload.sequence_order
    item = FeedItem(**{**payload.model_dump(), "sequence_order": seq})
    await _db.feed_items.insert_one(item.model_dump())
    return item.model_dump()


class FeedItemPatch(BaseModel):
    content_type: str | None = None
    sequence_order: int | None = None
    formato: str | None = None
    question_data: dict | None = None
    answer_options: list[dict] | None = None
    explanation_data: dict | None = None
    multimedia_assets: list[dict] | None = None
    metadata: dict | None = None
    cognitive_mapping_reference: str | None = None
    difficulty_reference: str | None = None
    learning_objectives: list[str] | None = None
    background_theme: str | None = None
    published: bool | None = None


@router.patch("/admin/feed-items/{content_id}")
async def admin_update_item(content_id: str, payload: FeedItemPatch, admin: User = Depends(require_admin)):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        return {"ok": True, "changes": 0}
    changes["updated_at"] = _now()
    res = await _db.feed_items.update_one({"content_id": content_id}, {"$set": changes})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.delete("/admin/feed-items/{content_id}")
async def admin_delete_item(content_id: str, admin: User = Depends(require_admin)):
    res = await _db.feed_items.delete_one({"content_id": content_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}
