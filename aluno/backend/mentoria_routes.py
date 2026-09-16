"""Lista de espera da MENTORIA com o 1º colocado de Medicina da USP.

**O que mudou em 2026-09-15.** Isto era "aulas particulares": um formulário
de pedido de aula avulsa, com várias pessoas dando aula. O produto deixou de
existir nessa forma. O que existe agora é **uma lista de espera para a
mentoria**, e a mentoria é com UMA pessoa específica — quem passou em
primeiro lugar em Medicina na USP. A diferença não é de rótulo:

* **Não se pede uma aula, entra-se numa fila.** Não há agendamento aqui, e a
  tela não promete horário nenhum: promete posição numa lista e um contato.
* **A vaga é escassa por natureza** (uma pessoa, não um time), e é por isso
  que a fila existe — não é um funil de marketing inventado.

**A coleção do Mongo continua sendo `aulas_particulares`**, de propósito: ela
guarda os pedidos reais de alunos que já se inscreveram, e renomeá-la
trocaria um nome interno por perder o histórico de gente esperando contato.
O inventário da LGPD (`dados_pessoais.COLECOES_POR_USUARIO`) aponta para esse
mesmo nome — ver o comentário lá.

O mesmo vale para os valores de `status`: `pendente`/`em_andamento`/
`concluida`/`cancelada` estão gravados nos registros existentes. O que mudou
foi o RÓTULO que o admin lê ("na fila", "conversando", "virou mentoria",
"saiu da fila"), que vive no frontend.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin, require_user
from models import (
    MENTORIA_AREAS,
    MENTORIA_STATUS,
    CreateMentoriaEsperaRequest,
    MentoriaEspera,
    UpdateMentoriaStatusRequest,
    User,
    _now_iso,
)

router = APIRouter(prefix="/mentoria", tags=["mentoria"])

# Ver o docstring: nome interno preservado para não perder o histórico.
COLECAO = "aulas_particulares"

_db = None
def set_db(db):
    global _db
    _db = db


@router.post("")
async def entrar_na_fila(payload: CreateMentoriaEsperaRequest, user: User = Depends(require_user)):
    if not payload.areas:
        raise HTTPException(status_code=422, detail="Selecione ao menos uma área.")
    invalidas = [a for a in payload.areas if a not in MENTORIA_AREAS]
    if invalidas:
        raise HTTPException(status_code=422, detail=f"Área(s) inválida(s): {', '.join(invalidas)}")
    if not payload.nome_completo.strip() or not payload.whatsapp.strip():
        raise HTTPException(status_code=422, detail="Nome completo e WhatsApp são obrigatórios.")

    # Um aluno, um lugar na fila. Entrar duas vezes não avança ninguém e
    # ainda faria a lista do admin mostrar a mesma pessoa duas vezes — o
    # segundo envio ATUALIZA o pedido em vez de criar outro.
    existente = await _db[COLECAO].find_one({"user_id": user.user_id}, {"_id": 0})
    if existente:
        await _db[COLECAO].update_one(
            {"request_id": existente["request_id"]},
            {"$set": {
                "nome_completo": payload.nome_completo.strip(),
                "whatsapp": payload.whatsapp.strip(),
                "areas": payload.areas,
                "descricao": payload.descricao.strip(),
                "updated_at": _now_iso(),
            }},
        )
        atualizado = await _db[COLECAO].find_one({"request_id": existente["request_id"]}, {"_id": 0})
        return {**atualizado, "ja_estava_na_fila": True, "posicao": await _posicao(existente["request_id"])}

    req = MentoriaEspera(
        user_id=user.user_id,
        nome_completo=payload.nome_completo.strip(),
        whatsapp=payload.whatsapp.strip(),
        areas=payload.areas,
        descricao=payload.descricao.strip(),
    )
    await _db[COLECAO].insert_one(req.model_dump())
    return {**req.model_dump(), "ja_estava_na_fila": False, "posicao": await _posicao(req.request_id)}


async def _posicao(request_id: str) -> int | None:
    """Em que lugar da fila o aluno está, contando por ordem de chegada.

    A posição é informação honesta e é o que uma lista de espera deve
    devolver — "recebemos seu pedido" não diz nada. Quem já saiu da fila
    (`concluida`/`cancelada`) não conta, senão a posição só cresceria.
    """
    docs = await _db[COLECAO].find(
        {"status": {"$in": ["pendente", "em_andamento"]}}, {"_id": 0, "request_id": 1, "created_at": 1},
    ).sort("created_at", 1).to_list(5000)
    for i, d in enumerate(docs, start=1):
        if d["request_id"] == request_id:
            return i
    return None


@router.get("/me")
async def meu_lugar_na_fila(user: User = Depends(require_user)):
    """O pedido deste aluno, se existir, com a posição atual."""
    doc = await _db[COLECAO].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"na_fila": False}
    return {"na_fila": True, **doc, "posicao": await _posicao(doc["request_id"])}


@router.get("")
async def listar_a_fila(admin: User = Depends(require_admin)):
    docs = await _db[COLECAO].find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return docs


@router.patch("/{request_id}")
async def atualizar_status(
    request_id: str,
    payload: UpdateMentoriaStatusRequest,
    admin: User = Depends(require_admin),
):
    if payload.status not in MENTORIA_STATUS:
        raise HTTPException(status_code=422, detail=f"Status inválido: {payload.status}")
    res = await _db[COLECAO].update_one(
        {"request_id": request_id},
        {"$set": {"status": payload.status, "updated_at": _now_iso()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    doc = await _db[COLECAO].find_one({"request_id": request_id}, {"_id": 0})
    return doc
