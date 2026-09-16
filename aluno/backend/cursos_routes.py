"""Aba de Cursos: o catálogo (todo "em breve") e a aula ao vivo de quinta.

Três superfícies, um módulo:

**1. O catálogo.** Quatro cursos, todos `em_breve` (ver `cursos.CURSOS`),
vendidos em pré-venda por `cursos.CURSO_CUSTO_SPARKS` Sparks com **acesso
vitalício**: cobra-se uma vez, e quando o curso abrir o aluno entra sem pagar
de novo (`POST /cursos/{id}/acesso`). Quem prefere esperar tem o caminho de
graça ao lado — a lista de avisados (`POST /cursos/{id}/interesse`), que
também diz à equipe qual dos quatro construir primeiro e a quem chamar no
WhatsApp quando abrir.

Vender antes de entregar só é honesto com o combinado à vista: a tela diz que
as aulas ainda não existem, a resposta da compra devolve `disponivel: false`,
e o painel do admin mostra quantas pessoas já pagaram por cada curso — que é
a dívida assumida com elas.

**2. A aula ao vivo, toda quinta, com o 1º colocado de Medicina da USP.**
Custa `cursos.LIVE_CUSTO_SPARKS` Sparks e dá o link da sala DAQUELA edição.

Idempotência, mesma regra da redação e do mapa de habilidades: a compra é
reivindicada ANTES do débito, num documento cujo `_id` é `"{uid}:{edicao}"`.
O Mongo garante um por aluno por semana; duplo clique, retry do axios e uma
segunda aba caem na mesma reivindicação e a segunda chamada devolve o mesmo
acesso sem cobrar nada. Se o débito falhar (saldo insuficiente), a
reivindicação é desfeita — senão o aluno ficaria com um acesso que ele não
pagou e sem poder tentar de novo depois de comprar Sparks.

**Comprar antes de o link existir é permitido, de propósito.** O que o aluno
paga é a VAGA na edição de quinta; o link do Meet costuma ser gerado na
véspera. A tela diz isso com todas as letras, e o painel do admin avisa em
vermelho quando existe gente paga numa edição sem link publicado — é a única
forma de o combinado não virar uma promessa esquecida.

**3. O painel do admin** (`/admin/cursos`): publicar o link e o tema da
edição, ver quem já pagou — com o WhatsApp de cada um, que é como a equipe
efetivamente fala com o aluno — e ver o interesse acumulado por curso.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

import cursos
import firestore_service as fs
import rate_limit
import whatsapp as wa
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.cursos")

router = APIRouter(prefix="/cursos", tags=["cursos"])
router_admin = APIRouter(prefix="/admin/cursos", tags=["cursos-admin"])

_db = None


def set_db(db):
    global _db
    _db = db


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id_acesso(uid: str, edicao: str) -> str:
    return f"{uid}:{edicao}"


# ---------------------------------------------------------------------------
# Configuração da edição (link do Meet + tema), publicada pelo admin
# ---------------------------------------------------------------------------
#
# Um documento por EDIÇÃO, e não um único "link atual": o link da semana
# passada não pode continuar valendo para quem pagou a desta semana, e um
# campo único sobrescrito toda quinta apagaria o histórico de quem entregou o
# quê. `_id` é a data da edição, então publicar duas vezes é um upsert.


async def _config_da_edicao(edicao: str) -> dict:
    doc = await _db.cursos_config.find_one({"_id": edicao}, {"_id": 0})
    return doc or {}


class PublicarLiveRequest(BaseModel):
    # O link é opcional para o admin poder publicar só o tema (e vice-versa)
    # sem apagar o outro campo — ver `publicar_live`.
    link: str | None = Field(default=None, max_length=500)
    tema: str | None = Field(default=None, max_length=200)
    edicao: str | None = Field(default=None, max_length=10)


def _validar_link(link: str) -> str:
    limpo = link.strip()
    if not limpo:
        return ""
    if not limpo.startswith(("https://meet.google.com/", "https://meet.google.com")):
        # Só o Google Meet: é o que foi prometido ao aluno, e aceitar qualquer
        # URL transformaria um campo de admin num redirecionador aberto dentro
        # do produto.
        raise HTTPException(
            status_code=422,
            detail="O link precisa ser uma sala do Google Meet (https://meet.google.com/...).",
        )
    return limpo


# ---------------------------------------------------------------------------
# Aluno
# ---------------------------------------------------------------------------


async def _acesso_do_aluno(uid: str, edicao: str) -> dict | None:
    return await _db.cursos_live_acessos.find_one({"_id": _id_acesso(uid, edicao)}, {"_id": 0})


async def _montar_live(user: User, saldo: int | None) -> dict:
    live = cursos.proxima_live()
    config = await _config_da_edicao(live["edicao"])
    acesso = await _acesso_do_aluno(user.user_id, live["edicao"])
    tem_acesso = acesso is not None

    return {
        **live,
        "tema": config.get("tema"),
        # O link só sai para quem pagou. Devolvê-lo sempre e esconder na tela
        # seria publicar a sala para qualquer um que abrisse o DevTools.
        "link": config.get("link") if tem_acesso else None,
        "link_publicado": bool(config.get("link")),
        "tenho_acesso": tem_acesso,
        "acesso_em": (acesso or {}).get("criado_em"),
        "sparks_balance": saldo,
    }


@router.get("")
async def listar(user: User = Depends(require_user)):
    """Tudo o que a aba Cursos precisa, numa requisição.

    O saldo vem junto porque a tela decide com ele (botão de comprar x botão
    de "comprar Sparks"), e uma segunda chamada só para o saldo faria a página
    piscar entre os dois estados.
    """
    try:
        saldo = fs.read_sparks_balance(user.user_id)
    except Exception:  # noqa: BLE001
        # Firestore fora do ar não pode derrubar a página inteira: a lista de
        # cursos e o horário da live não dependem dele (ver o incidente de
        # cota de 2026-09-04). A tela mostra o preço e pede para tentar de novo
        # no clique.
        logger.warning("Saldo indisponível na aba Cursos para %s.", user.user_id)
        saldo = None

    interesses = await _db.cursos_interesse.find(
        {"user_id": user.user_id}, {"_id": 0, "curso_id": 1}
    ).to_list(50)
    marcados = {i["curso_id"] for i in interesses}

    comprados = await _db.cursos_acessos.find(
        {"user_id": user.user_id}, {"_id": 0, "curso_id": 1}
    ).to_list(50)
    meus = {c["curso_id"] for c in comprados}

    return {
        "cursos": [
            {
                **c,
                "tenho_interesse": c["curso_id"] in marcados,
                "tenho_acesso": c["curso_id"] in meus,
            }
            for c in cursos.listar_cursos()
        ],
        "live": await _montar_live(user, saldo),
        "whatsapp": user.whatsapp,
    }


class _JaTinha(Exception):
    """O aluno já era dono disto. Não é erro: é a segunda chamada da mesma
    compra (duplo clique, retry, outra aba) e ela não pode cobrar de novo."""


async def _reivindicar_e_cobrar(
    user: User, colecao: str, doc_id: str, doc: dict, custo: int, oque: str,
) -> int:
    """Reivindica a compra no Mongo e SÓ ENTÃO debita os Sparks.

    A ordem é a garantia inteira, e é a mesma da redação e do treino: um
    documento de `_id` determinístico (`"{uid}:{coisa}"`) é criado primeiro;
    o Mongo recusa o segundo com `DuplicateKeyError`, então duas requisições
    simultâneas do mesmo aluno produzem uma cobrança, não duas.

    Se o débito falhar — saldo insuficiente ou Firestore instável — a
    reivindicação é DESFEITA. Sem isso o aluno ficaria com a chave queimada:
    dono de um acesso que não pagou e sem conseguir comprar depois de
    recarregar. Devolve o saldo restante.
    """
    try:
        await _db[colecao].insert_one({
            "_id": doc_id, "user_id": user.user_id, "custo_sparks": custo,
            "criado_em": _agora_iso(), **doc,
        })
    except DuplicateKeyError as exc:
        raise _JaTinha() from exc

    try:
        fs.ensure_student_profile(user.user_id, user.name, user.email)
        fs.ensure_sparks_balance(user.user_id)
        saldo = fs.deduct_sparks(user.user_id, custo)
    except fs.InsufficientSparksError as exc:
        await _db[colecao].delete_one({"_id": doc_id})
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        await _db[colecao].delete_one({"_id": doc_id})
        logger.exception("Falha ao cobrar %s de %s.", oque, user.user_id)
        raise HTTPException(
            status_code=503,
            detail="Não foi possível concluir agora. Nenhum Spark foi debitado — tente de novo.",
        ) from exc

    await _db[colecao].update_one({"_id": doc_id}, {"$set": {"cobrado": True, "saldo_apos": saldo}})
    logger.info("%s liberado para %s (-%d Sparks).", oque, user.user_id, custo)
    return saldo


@router.post("/live/acesso")
async def comprar_acesso_live(
    user: User = Depends(require_user),
    whatsapp: str | None = Body(default=None, embed=True),
    _: None = Depends(rate_limit.por_usuario("cursos")),
):
    """Debita os Sparks e garante a vaga do aluno na edição desta quinta."""
    live = cursos.proxima_live()
    edicao = live["edicao"]
    custo = cursos.LIVE_CUSTO_SPARKS

    # Quem chegou sem número (conta antiga, ou entrou pelo Google) pode
    # informá-lo aqui: é por ele que o lembrete da aula chega, e é o pedido
    # mais natural do produto inteiro — o aluno está comprando justamente a
    # aula sobre a qual quer ser lembrado.
    if whatsapp:
        await _gravar_whatsapp(user.user_id, whatsapp)

    if await _acesso_do_aluno(user.user_id, edicao):
        return await _resposta_de_acesso(user, edicao, cobrado=False)

    try:
        saldo = await _reivindicar_e_cobrar(
            user,
            "cursos_live_acessos",
            _id_acesso(user.user_id, edicao),
            {"edicao": edicao},
            custo,
            f"acesso à live {edicao}",
        )
    except _JaTinha:
        # Outra requisição do mesmo aluno ganhou a corrida: ela cobra, esta
        # devolve o acesso sem cobrar.
        return await _resposta_de_acesso(user, edicao, cobrado=False)
    return await _resposta_de_acesso(user, edicao, cobrado=True, saldo=saldo)


async def _resposta_de_acesso(user: User, edicao: str, *, cobrado: bool, saldo: int | None = None):
    if saldo is None:
        try:
            saldo = fs.read_sparks_balance(user.user_id)
        except Exception:  # noqa: BLE001
            saldo = None
    config = await _config_da_edicao(edicao)
    return {
        "ok": True,
        "edicao": edicao,
        "cobrado": cobrado,
        "custo_sparks": cursos.LIVE_CUSTO_SPARKS if cobrado else 0,
        "sparks_balance": saldo,
        "link": config.get("link"),
        "tema": config.get("tema"),
        # Sem link ainda: a vaga está garantida e a tela precisa dizer isso
        # sem parecer que a compra falhou.
        "link_publicado": bool(config.get("link")),
    }


@router.post("/{curso_id}/acesso")
async def comprar_curso(
    curso_id: str,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cursos")),
):
    """Compra o acesso VITALÍCIO a um curso — uma cobrança, para sempre.

    Diferente da live, aqui não existe edição: o `_id` é `"{uid}:{curso_id}"`,
    então o aluno é dono daquele curso e ponto. Uma segunda chamada devolve o
    mesmo acesso sem cobrar — e isso vale para sempre, não só para o duplo
    clique: se daqui a um ano ele clicar em "comprar" de novo, a resposta é
    "você já tem", nunca uma segunda cobrança.
    """
    curso = cursos.get_curso(curso_id)
    if curso is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    custo = cursos.CURSO_CUSTO_SPARKS
    doc_id = f"{user.user_id}:{curso_id}"

    if await _db.cursos_acessos.find_one({"_id": doc_id}, {"_id": 1}):
        return await _resposta_do_curso(user, curso, cobrado=False)

    try:
        saldo = await _reivindicar_e_cobrar(
            user, "cursos_acessos", doc_id,
            {"curso_id": curso_id, "vitalicio": True},
            custo, f"acesso vitalício a {curso_id}",
        )
    except _JaTinha:
        return await _resposta_do_curso(user, curso, cobrado=False)
    return await _resposta_do_curso(user, curso, cobrado=True, saldo=saldo)


async def _resposta_do_curso(user: User, curso, *, cobrado: bool, saldo: int | None = None):
    if saldo is None:
        try:
            saldo = fs.read_sparks_balance(user.user_id)
        except Exception:  # noqa: BLE001
            saldo = None
    return {
        "ok": True,
        "curso_id": curso.curso_id,
        "titulo": curso.titulo,
        "cobrado": cobrado,
        "custo_sparks": cursos.CURSO_CUSTO_SPARKS if cobrado else 0,
        "sparks_balance": saldo,
        "tenho_acesso": True,
        "vitalicio": True,
        # O que separa "comprei" de "posso assistir". A tela precisa dos dois
        # para não prometer uma aula que ainda não existe.
        "disponivel": curso.status == cursos.DISPONIVEL,
        "status": curso.status,
    }


@router.post("/{curso_id}/interesse")
async def marcar_interesse(curso_id: str, user: User = Depends(require_user)):
    """Entra na lista de avisados de um curso. Não custa Spark nenhum.

    De propósito: cobrar para avisar sobre um produto que ainda não existe
    seria cobrar por uma promessa. O valor aqui é para a equipe — saber qual
    dos quatro cursos construir primeiro, e ter a quem avisar quando abrir.
    """
    curso = cursos.get_curso(curso_id)
    if curso is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    await _db.cursos_interesse.update_one(
        {"_id": f"{user.user_id}:{curso_id}"},
        {"$set": {"user_id": user.user_id, "curso_id": curso_id, "criado_em": _agora_iso()}},
        upsert=True,
    )
    return {"ok": True, "curso_id": curso_id, "tenho_interesse": True}


@router.delete("/{curso_id}/interesse")
async def desmarcar_interesse(curso_id: str, user: User = Depends(require_user)):
    if cursos.get_curso(curso_id) is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")
    await _db.cursos_interesse.delete_one({"_id": f"{user.user_id}:{curso_id}"})
    return {"ok": True, "curso_id": curso_id, "tenho_interesse": False}


async def _gravar_whatsapp(uid: str, bruto: str) -> None:
    """Grava o número do aluno nos dois formatos (ver `whatsapp.py`)."""
    try:
        digitado, e164 = wa.normalizar(bruto)
    except wa.WhatsAppInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await _db.users.update_one(
        {"user_id": uid}, {"$set": {"whatsapp": digitado, "whatsapp_e164": e164}}
    )


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


@router_admin.get("")
async def painel(admin: User = Depends(require_admin)):
    """Edição corrente + quem pagou + interesse por curso.

    Os inscritos vêm com nome, e-mail e WhatsApp já formatado e com o link de
    conversa pronto: a tarefa real do admin aqui não é "consultar", é "mandar
    o link para essas pessoas".
    """
    live = cursos.proxima_live()
    config = await _config_da_edicao(live["edicao"])

    acessos = await _db.cursos_live_acessos.find(
        {"edicao": live["edicao"]}, {"_id": 0}
    ).sort("criado_em", 1).to_list(1000)

    interesses = await _db.cursos_interesse.find({}, {"_id": 0}).to_list(5000)
    compras = await _db.cursos_acessos.find({}, {"_id": 0}).to_list(5000)

    # UMA leitura de `users` para a tela inteira — inscritos da live,
    # compradores e interessados dos quatro cursos juntos. Um `find` por
    # curso seriam nove viagens ao banco para responder a mesma pergunta.
    contatos = await _contatos({r.get("user_id") for r in acessos + interesses + compras})

    por_curso: dict[str, list[dict]] = {c.curso_id: [] for c in cursos.CURSOS}
    for i in interesses:
        if i["curso_id"] in por_curso:
            por_curso[i["curso_id"]].append(_com_contato(i, contatos))

    compradores: dict[str, list[dict]] = {c.curso_id: [] for c in cursos.CURSOS}
    for c in compras:
        if c["curso_id"] in compradores:
            compradores[c["curso_id"]].append(_com_contato(c, contatos))

    # Histórico curto: quantos pagaram em cada quinta anterior.
    todos = await _db.cursos_live_acessos.find({}, {"_id": 0, "edicao": 1}).to_list(5000)
    por_edicao: dict[str, int] = {}
    for a in todos:
        por_edicao[a["edicao"]] = por_edicao.get(a["edicao"], 0) + 1

    return {
        "live": {
            **live,
            "tema": config.get("tema"),
            "link": config.get("link"),
            "link_publicado": bool(config.get("link")),
            "publicado_em": config.get("atualizado_em"),
            "publicado_por": config.get("atualizado_por"),
        },
        "inscritos": [_com_contato(a, contatos) for a in acessos],
        "inscritos_count": len(acessos),
        "receita_sparks": sum(int(a.get("custo_sparks") or 0) for a in acessos),
        "historico": sorted(
            ({"edicao": e, "inscritos": n} for e, n in por_edicao.items()),
            key=lambda x: x["edicao"], reverse=True,
        )[:12],
        "cursos": [
            {
                "curso_id": c["curso_id"],
                "titulo": c["titulo"],
                "status": c["status"],
                "custo_sparks": c["custo_sparks"],
                "interessados": len(por_curso.get(c["curso_id"], [])),
                # Quantas pessoas JÁ PAGARAM por um curso que ainda não
                # existe. É o número mais importante desta tela: é a dívida
                # assumida com aluno, não uma métrica de vaidade.
                "compradores": len(compradores.get(c["curso_id"], [])),
                "sparks_arrecadados": sum(
                    int(x.get("custo_sparks") or 0) for x in compradores.get(c["curso_id"], [])
                ),
            }
            for c in cursos.listar_cursos()
        ],
        "interessados_por_curso": por_curso,
        "compradores_por_curso": compradores,
    }


async def _contatos(ids: set) -> dict[str, dict]:
    """`user_id -> {nome, e-mail, WhatsApp}`, numa leitura só."""
    limpos = sorted(i for i in ids if i)
    if not limpos:
        return {}
    contas = await _db.users.find(
        {"user_id": {"$in": limpos}},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1, "whatsapp": 1, "whatsapp_e164": 1},
    ).to_list(len(limpos))
    return {c["user_id"]: c for c in contas}


def _com_contato(registro: dict, contatos: dict[str, dict]) -> dict:
    """Um registro por aluno + como falar com ele.

    O WhatsApp sai formatado (`(11) 98765-4321`) E como link de conversa: o
    admin abre o chat de um clique, sem copiar número à mão — que é o ponto
    inteiro de ter guardado o campo.
    """
    conta = contatos.get(registro.get("user_id")) or {}
    e164 = conta.get("whatsapp_e164")
    return {
        **registro,
        "nome": conta.get("name"),
        "email": conta.get("email"),
        "whatsapp": wa.formatar_br(e164) or conta.get("whatsapp"),
        "whatsapp_e164": e164,
        "whatsapp_link": wa.link_conversa(e164),
    }


@router_admin.put("/live")
async def publicar_live(payload: PublicarLiveRequest, admin: User = Depends(require_admin)):
    """Publica (ou corrige) o link do Meet e o tema de uma edição.

    `edicao` em branco significa "a próxima" — que é o caso de 99% dos
    cliques. Poder nomear a edição existe para consertar a semana errada sem
    esperar o relógio.
    """
    edicao = (payload.edicao or cursos.proxima_live()["edicao"]).strip()

    campos: dict = {"atualizado_em": _agora_iso(), "atualizado_por": admin.email}
    if payload.link is not None:
        campos["link"] = _validar_link(payload.link)
    if payload.tema is not None:
        campos["tema"] = payload.tema.strip()

    await _db.cursos_config.update_one({"_id": edicao}, {"$set": campos}, upsert=True)
    doc = await _db.cursos_config.find_one({"_id": edicao}, {"_id": 0})
    logger.info("Live %s publicada por %s (link=%s).", edicao, admin.email, bool(campos.get("link")))
    return {"ok": True, "edicao": edicao, **(doc or {})}
