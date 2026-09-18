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

import logging

from fastapi import APIRouter, Depends, HTTPException

import firestore_service as fs
import whatsapp as wa
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

logger = logging.getLogger("sapiens.mentoria")

router = APIRouter(prefix="/mentoria", tags=["mentoria"])

# Ver o docstring: nome interno preservado para não perder o histórico.
COLECAO = "aulas_particulares"

# ---------------------------------------------------------------------------
# O preço da fila
# ---------------------------------------------------------------------------
#
# Entrar na lista de espera custa Sparks desde 2026-09-17. Não é monetização
# da fila: é o filtro que faz a fila significar alguma coisa.
#
# Uma lista de espera de graça enche de gente que clicou "por via das dúvidas",
# e quem atende — UMA pessoa — passa a gastar o tempo escasso dela ligando para
# quem não queria mentoria nenhuma. Quem está na frente da fila espera mais por
# causa disso. Um preço pequeno faz a fila voltar a ser uma fila de gente que
# quer entrar.
#
# **Cobra-se UMA vez, na ENTRADA.** Corrigir os próprios dados depois é de
# graça, para sempre: cobrar por uma correção seria transformar um erro de
# digitação num segundo débito, e faria o aluno preferir deixar o telefone
# errado — que é exatamente o dado que a fila existe para ter.
ENTRADA_COST = 50

_db = None
def set_db(db):
    global _db
    _db = db


def _cobrar(uid: str, custo: int) -> int:
    fs.ensure_sparks_balance(uid)
    try:
        return fs.deduct_sparks(uid, custo)
    except fs.InsufficientSparksError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        ) from exc


def _safe_reembolso(uid: str, custo: int):
    try:
        return fs.refund_sparks(uid, custo)
    except Exception:  # noqa: BLE001
        logger.exception("REEMBOLSO FALHOU (mentoria): %d Sparks devidos a %s.", custo, uid)
        return None


async def _gravar_whatsapp_na_conta(user: User, bruto: str) -> None:
    """O número informado na fila também vira o WhatsApp da CONTA, quando ela
    ainda não tem um.

    Desde 2026-09-17 o WhatsApp é pedido no cadastro e os cartões que o pediam
    depois foram removidos das telas. Sobram as contas antigas e as criadas
    pelo botão do Google a partir da tela de login, que não passam por
    formulário nenhum — para elas, esta é a única porta. Não sobrescreve um
    número já existente: a fila é um pedido, não uma tela de perfil.
    """
    if user.whatsapp:
        return
    try:
        digitado, e164 = wa.normalizar(bruto)
    except wa.WhatsAppInvalido:
        return
    try:
        await _db.users.update_one(
            {"user_id": user.user_id},
            {"$set": {"whatsapp": digitado, "whatsapp_e164": e164}},
        )
    except Exception:  # noqa: BLE001
        logger.exception("mentoria: não consegui gravar o WhatsApp na conta de %s.", user.user_id)


@router.get("/precos")
async def precos(_: User = Depends(require_user)):
    """O frontend nunca decide preço — só o exibe e desabilita botão."""
    return {"custo_entrada": ENTRADA_COST}


@router.post("")
async def entrar_na_fila(payload: CreateMentoriaEsperaRequest, user: User = Depends(require_user)):
    """Entra na fila (cobra `ENTRADA_COST`) ou CORRIGE o pedido (de graça).

    A diferença entre as duas é o aluno já estar ou não na fila, e ela é
    decidida no servidor — o cliente não manda nada que influencie o preço.

    **Um aluno, um lugar.** O `user_id` é a chave: o segundo envio atualiza o
    pedido existente em vez de criar um segundo, então nem o duplo clique nem
    o aluno que reabre a página entram duas vezes na lista do admin. É também
    o que impede a cobrança dupla, porque quem já está na fila não é cobrado.
    """
    if not payload.areas:
        raise HTTPException(status_code=422, detail="Selecione ao menos uma área.")
    invalidas = [a for a in payload.areas if a not in MENTORIA_AREAS]
    if invalidas:
        raise HTTPException(status_code=422, detail=f"Área(s) inválida(s): {', '.join(invalidas)}")

    nome = payload.nome_completo.strip()
    bruto = payload.whatsapp.strip()
    # Nome, e-mail e WhatsApp são o que o admin recebe — e a fila sem eles é
    # uma linha que ninguém consegue atender. O e-mail vem da CONTA e sempre
    # existe (nenhum caminho de cadastro cria conta sem ele); os outros dois
    # são checados aqui, ANTES de qualquer débito, para o aluno nunca pagar
    # por uma entrada que não vai acontecer.
    if not nome or not bruto:
        raise HTTPException(status_code=422, detail="Nome completo e WhatsApp são obrigatórios.")
    try:
        whatsapp_digitado, _e164 = wa.normalizar(bruto)
    except wa.WhatsAppInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not user.email:
        raise HTTPException(
            status_code=422,
            detail="Sua conta está sem e-mail. Fale com a equipe antes de entrar na fila.",
        )

    existente = await _db[COLECAO].find_one({"user_id": user.user_id}, {"_id": 0})
    if existente:
        # CORREÇÃO DO PEDIDO — de graça, e sem mexer no lugar na fila.
        await _db[COLECAO].update_one(
            {"request_id": existente["request_id"]},
            {"$set": {
                "nome_completo": nome,
                "email": user.email,
                "whatsapp": whatsapp_digitado,
                "areas": payload.areas,
                "descricao": payload.descricao.strip(),
                "updated_at": _now_iso(),
            }},
        )
        atualizado = await _db[COLECAO].find_one({"request_id": existente["request_id"]}, {"_id": 0})
        await _gravar_whatsapp_na_conta(user, whatsapp_digitado)
        return {
            **atualizado,
            "ja_estava_na_fila": True,
            "cobrado": 0,
            "sparks_balance": _saldo(user.user_id),
            "posicao": await _posicao(existente["request_id"]),
        }

    # ENTRADA NOVA — cobra primeiro, grava depois. Se a gravação falhar, os
    # Sparks voltam: um débito sem lugar na fila é o pior resultado possível.
    saldo = _cobrar(user.user_id, ENTRADA_COST)
    req = MentoriaEspera(
        user_id=user.user_id,
        nome_completo=nome,
        email=user.email,
        whatsapp=whatsapp_digitado,
        areas=payload.areas,
        descricao=payload.descricao.strip(),
        sparks_cobrados=ENTRADA_COST,
    )
    try:
        await _db[COLECAO].insert_one(req.model_dump())
    except Exception as exc:  # noqa: BLE001
        saldo = _safe_reembolso(user.user_id, ENTRADA_COST)
        logger.exception(
            "mentoria: entrada na fila falhou para %s — %d Sparks devolvidos.",
            user.user_id, ENTRADA_COST,
        )
        raise HTTPException(
            status_code=503,
            detail="Não consegui te colocar na fila agora. Seus Sparks foram devolvidos.",
        ) from exc

    await _gravar_whatsapp_na_conta(user, whatsapp_digitado)
    return {
        **req.model_dump(),
        "ja_estava_na_fila": False,
        "cobrado": ENTRADA_COST,
        "sparks_balance": saldo,
        "posicao": await _posicao(req.request_id),
    }


def _saldo(uid: str) -> int | None:
    try:
        return fs.read_sparks_balance(uid)
    except Exception:  # noqa: BLE001
        logger.exception("mentoria: leitura de saldo falhou — resposta segue sem saldo")
        return None


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
    """O pedido deste aluno, se existir, com a posição atual.

    Vem junto o que a tela precisa para decidir se pede dados antes de cobrar:
    o preço da entrada e o que a CONTA já tem de nome, e-mail e WhatsApp.
    Numa resposta só — a alternativa seria a tela abrir com três requisições
    para desenhar um formulário.
    """
    conta = {
        "nome": user.name,
        "email": user.email,
        "whatsapp": user.whatsapp,
    }
    doc = await _db[COLECAO].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"na_fila": False, "custo_entrada": ENTRADA_COST, "conta": conta}
    return {
        "na_fila": True,
        **doc,
        "custo_entrada": ENTRADA_COST,
        "conta": conta,
        "posicao": await _posicao(doc["request_id"]),
    }


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
