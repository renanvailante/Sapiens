"""Admin-only routes: dashboard summary + user management."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth import require_admin
from models import User
import firestore_service as fs
import firestore_http
import perfil_cognitivo_service

router = APIRouter(prefix="/admin", tags=["admin"])

_db = None
def set_db(db):
    global _db
    _db = db


@router.get("/summary")
async def summary(admin: User = Depends(require_admin)):
    exams = await _db.exams.count_documents({})
    keys = await _db.answer_keys.count_documents({})
    analyses = await _db.analyses.count_documents({"deleted": False})
    trashed = await _db.analyses.count_documents({"deleted": True})
    users_count = await _db.users.count_documents({})
    admins_count = await _db.users.count_documents({"is_admin": True})
    feed_items = await _db.feed_items.count_documents({})
    feed_published = await _db.feed_items.count_documents({"published": True})
    annotations = await _db.question_annotations.count_documents({})
    interactions = await _db.feed_interactions.count_documents({})
    return {
        "exams": exams,
        "answer_keys": keys,
        "analyses_active": analyses,
        "analyses_trashed": trashed,
        "users": users_count,
        "admins": admins_count,
        "feed_items": feed_items,
        "feed_items_published": feed_published,
        "annotations": annotations,
        "feed_interactions": interactions,
    }


@router.get("/users")
async def list_users(admin: User = Depends(require_admin)):
    docs = await _db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(1000)
    return docs


class UpdateUserRequest(BaseModel):
    is_admin: bool


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UpdateUserRequest, admin: User = Depends(require_admin)):
    if admin.user_id == user_id and payload.is_admin is False:
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio acesso admin.")
    res = await _db.users.update_one({"user_id": user_id}, {"$set": {"is_admin": payload.is_admin}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"ok": True, "is_admin": payload.is_admin}


class GrantSparksRequest(BaseModel):
    email: EmailStr
    amount: int = Field(..., ge=1, le=1_000_000)
    motivo: str = Field(default="", max_length=200)


@router.post("/sparks/grant")
async def grant_sparks(payload: GrantSparksRequest, admin: User = Depends(require_admin)):
    """Credita Sparks manualmente na conta de um aluno, por e-mail — ferramenta
    de suporte/teste do admin (ajuste pontual de saldo, não uma recompensa de
    produto). Ver `firestore_service.grant_admin_sparks` sobre por que não há
    deduplicação aqui: é uma ação humana avulsa, não um evento repetível.
    """
    alvo = await _db.users.find_one({"email": payload.email.strip().lower()}, {"_id": 0, "user_id": 1})
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return fs.grant_admin_sparks(
        alvo["user_id"], amount=payload.amount, admin_email=admin.email, motivo=payload.motivo,
    )


# ---------- Firestore sync (admin only) ----------

def _annotated_item(master: dict) -> dict:
    """Extrai o item anotado (Schema 2.2) de um documento espelhado do pipeline.

    O pipeline grava a anotação sob a chave `item`. A chave `pipeline` é a forma
    anterior (pré-2.2) e é lida apenas para não perder documentos já sincronizados
    antes da migração.
    """
    return master.get("item") or master.get("pipeline") or master


def _build_public_doc(master: dict) -> dict:
    """Gera a versao FILTRADA (aluno) a partir do doc completo (master).

    Mantem SOMENTE `questao` (enunciado, alternativas, recursos) e dados basicos
    da `fonte`. Nenhum processo cognitivo / dominio / competencia / metadado
    interno — o aluno nao ve a classificacao.

    **`item_id` é copiado do item, nunca gerado aqui.** O Schema 2.2 obriga que
    ele "permaneça invariável entre pipeline, Firestore, aluno e professor". Até
    2026-08-21 esta função sorteava um `uuid4().hex` novo **a cada sync**, o que
    tornava impossível ligar um evento de behavior ao item que o originou e
    quebrava o vínculo a cada reconciliação. `master_id` continua guardando o id
    interno do documento do pipeline, que é outra coisa.

    `ontology_version`, `item_schema_version` e `item_hash` são propagados porque
    o contrato de behavior 1.1 os exige em todo evento de resposta, e a única
    fonte correta deles é o item respondido.
    """
    item = _annotated_item(master)
    q = item.get("questao") or {}
    f = item.get("fonte") or {}
    alternativas = [
        {"letra": a.get("letra"), "texto": a.get("texto"), "correta": a.get("correta")}
        for a in (q.get("alternativas") or [])
    ]
    return {
        "item_id": item.get("item_id") or master.get("item_id") or master.get("id"),
        "master_id": master.get("id"),
        "item_schema_version": item.get("schema_version") or master.get("schema_version"),
        "ontology_version": item.get("ontology_version") or master.get("ontology_version"),
        "item_hash": item.get("item_hash") or master.get("item_hash"),
        "questao": {
            "enunciado": q.get("enunciado"),
            "alternativas": alternativas,
            "recursos": q.get("recursos") or {},
            "visual_assets": q.get("visual_assets") or [],
        },
        "fonte": {
            "disciplina": f.get("disciplina"),
            "ano": f.get("ano"),
            "prova": f.get("prova"),
            "banca": f.get("banca"),
            "numero": f.get("numero"),
            "tema": f.get("tema"),
            "conteudo": f.get("conteudo"),
        },
    }


async def run_firestore_sync(db) -> dict:
    """Lê TODAS as questões (coleção 'itens') e schema completo do Firestore,
    salva o schema COMPLETO em 'questoes_master' (visível/editável só no admin)
    e (re)gera a versão FILTRADA em 'questoes_public' (consumida pelo aluno).

    Extraída da rota `POST /admin/firestore/sync` para ser reusada também
    pelo laço automático em `server.py` (`_auto_sync_loop`) — mesma lógica,
    duas formas de disparar: clique manual do admin, ou de tempos em tempos
    sozinho, para uma prova nova aparecer para o aluno sem exigir o clique.
    """
    items = await asyncio.to_thread(_read_all_firestore, "itens")

    # 1) master = schema completo (upsert por id original)
    for it in items:
        await db.questoes_master.update_one(
            {"id": it.get("id")}, {"$set": it}, upsert=True
        )

    # 2) public = versao filtrada regenerada a partir do master
    await db.questoes_public.delete_many({})
    publics = [_build_public_doc(it) for it in items]
    if publics:
        await db.questoes_public.insert_many(publics)

    return {
        "ok": True,
        "master_count": len(items),
        "public_count": len(publics),
    }


@router.post("/firestore/sync")
async def firestore_sync(admin: User = Depends(require_admin)):
    return await firestore_http.executar_async(run_firestore_sync, _db)


@router.post("/perfil-cognitivo/atualizar-todos")
async def perfil_cognitivo_atualizar_todos(admin: User = Depends(require_admin)):
    """Mesmo trabalho do laço automático (`server._perfil_cognitivo_loop`),
    sob demanda — para não esperar o próximo ciclo depois de subir esta
    feature, ou para conferir o resultado logo depois de um aluno responder
    em massa."""
    return await firestore_http.executar_async(perfil_cognitivo_service.atualizar_todos_os_perfis)


def _read_all_firestore(collection: str) -> list[dict]:
    """Le TODOS os documentos de uma colecao do Firestore (sem limite de 500)."""
    docs = fs.get_firestore().collection(collection).stream()
    return [{"id": snap.id, **(snap.to_dict() or {})} for snap in docs]


@router.get("/questoes-master")
async def list_questoes_master(limit: int = 500, admin: User = Depends(require_admin)):
    limit = max(1, min(int(limit), 2000))
    docs = await _db.questoes_master.find({}, {"_id": 0}).limit(limit).to_list(limit)
    return {"items": docs, "count": len(docs)}


class UpdateMasterRequest(BaseModel):
    data: dict


@router.patch("/questoes-master/{item_id}")
async def update_questao_master(item_id: str, payload: UpdateMasterRequest, admin: User = Depends(require_admin)):
    """Edita um doc master e regenera a versao publica correspondente."""
    res = await _db.questoes_master.update_one({"id": item_id}, {"$set": payload.data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Questão não encontrada")
    master = await _db.questoes_master.find_one({"id": item_id}, {"_id": 0})
    pub = _build_public_doc(master)
    await _db.questoes_public.update_one(
        {"master_id": item_id}, {"$set": pub}, upsert=True
    )
    return {"ok": True}
