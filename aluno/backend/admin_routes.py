"""Admin-only routes: dashboard summary + user management."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth import require_admin
from models import User
import firestore_service as fs
import firestore_http
import mercadopago_client as mp
import perfil_cognitivo_service
import sparks_payments_service as sparks_svc
import sparks_store

logger = logging.getLogger("sapiens.admin")

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
    """Contas do Mongo + saldo de Sparks e volume de respostas do Firestore.

    O join acontece aqui, e não na tela, porque as duas metades moram em
    bancos diferentes: identidade/permissão no Mongo, estado do aluno no
    Firestore. Custo: 1 leitura do Firestore por aluno, UMA vez por
    carregamento da tela (`resumo_dos_alunos` faz uma varredura só) — não 1
    por linha renderizada.

    Se o Firestore falhar (cota estourada é o caso real — ver o incidente de
    2026-09-04), a tela NÃO cai: os campos vêm `None` e `sparks_indisponivel`
    explica por quê. Esta é a tela de permissões, e revogar um admin não pode
    depender de o Firestore estar de pé.
    """
    docs = await _db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(1000)

    resumo: dict[str, dict] = {}
    indisponivel = False
    try:
        resumo = await asyncio.to_thread(fs.resumo_dos_alunos)
    except Exception as exc:  # noqa: BLE001
        indisponivel = True
        logger.warning("Resumo de Sparks/respostas indisponível na lista de usuários: %s", exc)

    for d in docs:
        r = resumo.get(d["user_id"]) or {}
        d["sparks_balance"] = r.get("sparks_balance")
        d["questoes_respondidas"] = r.get("questoes_respondidas")
        d["dias_ativos"] = r.get("dias_ativos")
        d["ultima_atividade"] = r.get("ultima_atividade")
        d["sparks_indisponivel"] = indisponivel
    return docs


@router.get("/users/{user_id}/detalhe")
async def detalhe_usuario(user_id: str, admin: User = Depends(require_admin)):
    """Ficha completa de um aluno — o que abre ao clicar no cartão dele.

    Junta as três fontes que hoje sabem algo sobre um aluno: a conta (Mongo
    `users`), o estado de estudo e o saldo (Firestore `students/{uid}`, UMA
    leitura) e a atividade dele nas demais coleções do Mongo, aqui só como
    CONTAGEM. Contagem e não conteúdo de propósito: cada uma dessas coisas já
    tem tela própria, e trazer o corpo de tudo faria desta rota a mais cara do
    painel sem responder melhor a pergunta "quem é este aluno".
    """
    conta = await _db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if conta is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    try:
        perfil = await asyncio.to_thread(fs.resumo_de_um_aluno, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Perfil Firestore indisponível para %s: %s", user_id, exc)
        perfil = {"indisponivel": True}

    async def _contar(colecao: str, filtro: dict) -> int:
        return await _db[colecao].count_documents(filtro)

    (
        analises, redacoes, reportes, sugestoes, aulas, pagamentos, pagos, sessoes_mentis,
    ) = await asyncio.gather(
        _contar("analyses", {"user_id": user_id, "deleted": False}),
        _contar("redacoes", {"user_id": user_id}),
        _contar("question_reports", {"user_id": user_id}),
        _contar("sugestoes", {"user_id": user_id}),
        _contar("aulas_particulares", {"user_id": user_id}),
        _contar("sparks_payments", {"user_id": user_id}),
        _contar("sparks_payments", {"user_id": user_id, "credited": True}),
        _contar("mentis_sessoes", {"user_id": user_id}),
    )

    transacoes = await _db.sparks_payments.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    # Mesmo rótulo de pacote que `/admin/transacoes` monta, para a ficha não
    # mostrar `spark_1500` cru onde a outra tela mostra "1.500 Sparks".
    for t in transacoes:
        pkg = sparks_store.get_package(t.get("package_id") or "")
        t["pacote_label"] = pkg.label if pkg else (t.get("package_id") or "—")
    gasto_centavos = sum(int(t.get("price_cents") or 0) for t in transacoes if t.get("credited"))
    sparks_comprados = sum(int(t.get("sparks_amount") or 0) for t in transacoes if t.get("credited"))

    recarga = await _db.sparks_auto_recharge.find_one({"user_id": user_id}, {"_id": 0})

    return {
        "conta": conta,
        "perfil": perfil,
        "atividade": {
            "analises": analises,
            "redacoes": redacoes,
            "reportes_de_questao": reportes,
            "sugestoes": sugestoes,
            "aulas_particulares": aulas,
            "sessoes_mentis": sessoes_mentis,
        },
        "financeiro": {
            "transacoes": pagamentos,
            "transacoes_pagas": pagos,
            "sparks_comprados": sparks_comprados,
            "gasto_centavos": gasto_centavos,
            "recarga_automatica": recarga,
        },
        "transacoes": transacoes,
    }


@router.get("/transacoes")
async def listar_transacoes(limit: int = 500, admin: User = Depends(require_admin)):
    """Toda cobrança de Sparks já registrada, mais recente primeiro.

    Fonte: `sparks_payments` no Mongo — a auditoria de COBRANÇA, que existe
    desde a tentativa de pagamento, aprovada ou não. Não é o Firestore, que só
    guarda o que virou saldo: uma tela de transações que só mostrasse compras
    creditadas esconderia exatamente o caso que interessa investigar (o Pix
    abandonado, o cartão recusado, o pagamento preso sem crédito).

    O nome do aluno vem de um join em memória sobre `users`, e o pacote de
    `sparks_store` — nem um nem outro está gravado na transação, e reconstruir
    o rótulo aqui é o que impede a tela de mostrar `spark_1500` cru.

    `saldo_antes`/`saldo_apos` são carimbados no crédito (ver
    `sparks_payments_service.process_payment_webhook`) e só existem em
    pagamentos creditados a partir de 2026-09-15 — antes disso ninguém
    registrava o saldo do aluno no instante da compra, e a tela mostra "—"
    em vez de inventar um número.
    """
    limit = max(1, min(int(limit), 2000))
    docs = await _db.sparks_payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)

    ids = {d.get("user_id") for d in docs if d.get("user_id")}
    contas = await _db.users.find(
        {"user_id": {"$in": list(ids)}}, {"_id": 0, "user_id": 1, "name": 1, "email": 1},
    ).to_list(len(ids) or 1)
    por_id = {c["user_id"]: c for c in contas}

    linhas = []
    for d in docs:
        conta = por_id.get(d.get("user_id")) or {}
        pkg = sparks_store.get_package(d.get("package_id") or "")
        linhas.append({
            **d,
            "aluno_nome": conta.get("name"),
            "aluno_email": conta.get("email"),
            "pacote_label": pkg.label if pkg else (d.get("package_id") or "—"),
        })

    creditadas = [l for l in linhas if l.get("credited")]
    return {
        "items": linhas,
        "count": len(linhas),
        "resumo": {
            "total": len(linhas),
            "creditadas": len(creditadas),
            "receita_centavos": sum(int(l.get("price_cents") or 0) for l in creditadas),
            "sparks_vendidos": sum(int(l.get("sparks_amount") or 0) for l in creditadas),
        },
    }


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


# ---------- Reconciliação de pagamentos (Sparks) ----------
#
# O crédito de Sparks depende inteiramente do webhook do Mercado Pago
# chegar (`POST /api/sparks/webhook`). Se ele se perder, atrasar, ou a
# notificação nunca for entregue por qualquer motivo do lado do Mercado
# Pago, o pagamento fica preso em `credited: false` para sempre, sem
# nenhum jeito de destravar — o admin não tinha como ver isso, nem re-
# disparar o crédito manualmente. Os dois endpoints abaixo cobrem exatamente
# esse buraco, sem inventar lógica nova: `reprocessar` chama a MESMA função
# que o webhook chama (`process_payment_webhook`), com a mesma garantia
# atômica de "credita uma vez só" — rodar isto em um pagamento já creditado
# é inofensivo (não credita de novo).

@router.get("/sparks/pendentes")
async def listar_sparks_pendentes(admin: User = Depends(require_admin)):
    """O que está "preso" agora, mais a prova de o Mercado Pago estar (ou não)
    notificando.

    As duas metades respondem perguntas diferentes e só juntas dizem onde está
    o defeito: `items` vazio e `webhooks_recebidos` cheio é operação saudável;
    `items` cheio e `webhooks_recebidos` vazio significa que a notificação
    nunca chegou; `webhooks_recebidos` com `assinatura_valida: false` significa
    que chegou e foi recusada — o segredo do painel não bate com o nosso.
    """
    cursor = _db.sparks_payments.find(
        {"credited": False, "status": {"$nin": ["rejected", "cancelled"]}},
        {"_id": 0},
    ).sort("created_at", -1)
    itens = await cursor.to_list(length=200)

    recebidos = await _db.webhook_recebimentos.find({}, {"_id": 0}).sort(
        "received_at", -1
    ).to_list(length=50)

    return {
        "items": itens,
        "count": len(itens),
        "webhooks_recebidos": recebidos,
        "webhooks_recebidos_count": len(recebidos),
    }


@router.post("/sparks/reprocessar/{mp_payment_id}")
async def reprocessar_pagamento(mp_payment_id: str, admin: User = Depends(require_admin)):
    """Rebusca o pagamento no Mercado Pago pelo id e credita se `approved` —
    a mesma função que `/api/sparks/webhook` chama, chamada manualmente."""
    try:
        resultado = await sparks_svc.process_payment_webhook(_db, mp_payment_id)
    except mp.MercadoPagoError as exc:
        raise HTTPException(status_code=502, detail=f"Mercado Pago: {exc.message or exc.error}")
    return resultado
