"""Comunidade — o Mural de Dúvidas do app aluno.

Um aluno publica uma dúvida por área, outros respondem, e quem perguntou marca
a resposta que resolveu. Quem resolveu ganha Sparks e XP.

**Por que no Mongo e não no Firestore.** Um feed é a coisa mais próxima de
"ler muitos documentos por abertura de tela" que existe num produto. No
Firestore isso é a cota do dia (ver `project_aluno_incidente_cota_firestore`);
aqui é uma consulta indexada. O Firestore só é tocado para PAGAR Sparks, que é
dinheiro e mora lá.

**Três decisões de produto que estão no código porque não podem se perder:**

1. **Perguntar é de graça, sempre.** Nenhuma dúvida custa Spark. Cobrar de
   quem está travado num exercício é cobrar exatamente no pior momento, e
   mataria o mural na primeira semana — sem dúvida publicada não há comunidade.
2. **Só o autor marca a melhor resposta**, e ela paga quem respondeu. É o único
   lugar do produto onde um aluno gera Sparks para outro; por isso tem teto
   diário (`MAX_SPARKS_DIA`), não paga a si mesmo, e a dúvida precisa ter
   idade mínima — as três travas juntas tornam a fazenda de contas-fantasma
   mais trabalhosa do que estudar.
3. **Destacar é conveniência, não vantagem.** 30 Sparks põem a dúvida no topo
   da área por 24h. Não compra resposta, não compra Mentis, não muda a ordem
   de quem já respondeu.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

import engajamento_service
import firestore_service as fs

logger = logging.getLogger("sapiens.comunidade")

_db = None


def set_db(db):
    global _db
    _db = db


# Áreas do ENEM + Redação. Lista fechada porque é o filtro do mural: campo
# livre aqui viraria quarenta grafias de "matematica" e um filtro inútil.
AREAS: tuple[str, ...] = (
    "Matemática",
    "Ciências da Natureza",
    "Ciências Humanas",
    "Linguagens e Códigos",
    "Redação",
    "Outro",
)

SPARKS_MELHOR_RESPOSTA = 15
CUSTO_DESTAQUE = 30
HORAS_DESTAQUE = 24

# Teto de Sparks que um aluno pode GANHAR por dia respondendo dúvidas. Cinco
# melhores respostas por dia é mais do que qualquer aluno honesto consegue
# (cada uma exige que outra pessoa marque a dele), e transforma a fazenda de
# contas falsas num trabalho pior remunerado que praticar de verdade.
MAX_SPARKS_DIA = 5

# Reportes DISTINTOS que escondem a publicação até um admin olhar. Três é baixo
# o bastante para tirar do ar rápido o que precisa sair rápido (o público é
# menor de idade) e alto o bastante para uma pessoa sozinha, ou duas combinadas,
# não conseguirem calar um colega. O conteúdo não é apagado: fica `em_revisao`,
# visível para o admin e para o próprio autor.
REPORTES_PARA_OCULTAR = 3

_MAX_TITULO = 160
_MAX_CORPO = 4000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _uid() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Publicar
# ---------------------------------------------------------------------------

async def publicar_duvida(
    *, student_id: str, autor_nome: str, area: str, titulo: str, corpo: str, item_id: str | None = None,
) -> dict[str, Any]:
    """Publica uma dúvida. Grátis, sempre — ver a decisão 1 no topo."""
    if area not in AREAS:
        area = "Outro"
    doc = {
        "duvida_id": _uid(),
        "student_id": student_id,
        "autor_nome": autor_nome or "Aluno",
        "area": area,
        "titulo": titulo.strip()[:_MAX_TITULO],
        "corpo": corpo.strip()[:_MAX_CORPO],
        # Quando a dúvida nasce de uma questão específica, o link permite à
        # tela levar quem for responder direto ao enunciado — responder no
        # escuro é o que faz resposta ruim.
        "item_id": item_id,
        "status": "publicada",
        "respostas": 0,
        "votos": 0,
        "resolvida": False,
        "melhor_resposta_id": None,
        "destacada_ate": None,
        "reportada_por": [],
        "created_at": _now_iso(),
        "atualizado_em": _now_iso(),
    }
    await _db.comunidade_duvidas.insert_one(dict(doc))
    await engajamento_service.registrar_acao(student_id, ["duvida_publicada"], nome=autor_nome)
    doc.pop("_id", None)
    return doc


async def responder(
    *, duvida_id: str, student_id: str, autor_nome: str, corpo: str,
) -> dict[str, Any]:
    duvida = await _db.comunidade_duvidas.find_one({"duvida_id": duvida_id}, {"_id": 0})
    if not duvida or duvida["status"] != "publicada":
        return {"ok": False, "motivo": "Esta dúvida não está disponível."}

    doc = {
        "resposta_id": _uid(),
        "duvida_id": duvida_id,
        "student_id": student_id,
        "autor_nome": autor_nome or "Aluno",
        "corpo": corpo.strip()[:_MAX_CORPO],
        "votos": 0,
        "melhor": False,
        "status": "publicada",
        "reportada_por": [],
        "created_at": _now_iso(),
    }
    await _db.comunidade_respostas.insert_one(dict(doc))
    await _db.comunidade_duvidas.update_one(
        {"duvida_id": duvida_id}, {"$inc": {"respostas": 1}, "$set": {"atualizado_em": _now_iso()}}
    )
    await engajamento_service.registrar_acao(
        student_id, ["resposta_publicada"], contadores={"respostas_comunidade": 1}, nome=autor_nome
    )
    doc.pop("_id", None)
    return {"ok": True, "resposta": doc}


# ---------------------------------------------------------------------------
# Ler
# ---------------------------------------------------------------------------

async def listar(
    *, area: str | None = None, filtro: str = "recentes", uid: str | None = None, limite: int = 30, pular: int = 0,
) -> dict[str, Any]:
    """Mural, paginado.

    `pular`/`limite` existem desde o primeiro dia porque um feed sem paginação é
    a mesma armadilha do `limit(5000)` de `list_students_with_behavior`: funciona
    com vinte dúvidas e vira uma varredura silenciosa com duas mil.
    """
    consulta: dict[str, Any] = {"status": "publicada"}
    if area and area in AREAS:
        consulta["area"] = area
    if filtro == "sem_resposta":
        consulta["respostas"] = 0
    elif filtro == "resolvidas":
        consulta["resolvida"] = True
    elif filtro == "minhas" and uid:
        # O autor enxerga a própria dúvida em revisão — sumir sem explicação é
        # o que faz a pessoa achar que o produto engoliu o texto dela. O que um
        # admin já removeu continua fora.
        consulta["status"] = {"$ne": "removida"}
        consulta["student_id"] = uid

    # Destaque comprado sobe ao topo enquanto vale; depois disso a ordem é a
    # natural. `destacada_ate` no passado ordena junto com `null` porque a
    # comparação é com o instante de agora, feita no `$set` abaixo.
    agora = _now_iso()
    pipeline = [
        {"$match": consulta},
        {"$addFields": {"em_destaque": {"$cond": [{"$gt": ["$destacada_ate", agora]}, 1, 0]}}},
        {"$sort": {"em_destaque": -1, "created_at": -1}},
        {"$skip": max(0, pular)},
        {"$limit": max(1, min(limite, 50))},
        {"$project": {"_id": 0, "reportada_por": 0}},
    ]
    itens = await _db.comunidade_duvidas.aggregate(pipeline).to_list(length=50)
    total = await _db.comunidade_duvidas.count_documents(consulta)
    return {"items": itens, "total": total, "areas": list(AREAS)}


async def ler_duvida(duvida_id: str, *, uid: str | None = None) -> dict[str, Any] | None:
    duvida = await _db.comunidade_duvidas.find_one({"duvida_id": duvida_id}, {"_id": 0, "reportada_por": 0})
    if not duvida:
        return None
    if duvida["status"] != "publicada" and duvida["student_id"] != uid:
        return None
    respostas = await (
        _db.comunidade_respostas.find({"duvida_id": duvida_id, "status": "publicada"}, {"_id": 0, "reportada_por": 0})
        .sort([("melhor", -1), ("votos", -1), ("created_at", 1)])
        .to_list(length=200)
    )
    # Os votos que ESTE aluno já deu, para a interface não deixar votar de novo
    # no que já foi votado — uma consulta, não uma por resposta.
    meus_votos: list[str] = []
    if uid:
        alvos = [duvida_id] + [r["resposta_id"] for r in respostas]
        docs = await _db.comunidade_votos.find({"uid": uid, "alvo": {"$in": alvos}}, {"_id": 0, "alvo": 1}).to_list(length=300)
        meus_votos = [d["alvo"] for d in docs]
    return {"duvida": duvida, "respostas": respostas, "meus_votos": meus_votos}


# ---------------------------------------------------------------------------
# Interagir
# ---------------------------------------------------------------------------

async def votar(*, tipo: str, alvo_id: str, uid: str) -> dict[str, Any]:
    """Um voto por pessoa por alvo, e nunca no próprio conteúdo.

    O `_id` determinístico (`tipo:alvo:uid`) é a trava: o segundo voto levanta
    `DuplicateKeyError` no banco, não numa checagem que duas requisições
    simultâneas passariam juntas.
    """
    colecao = _db.comunidade_duvidas if tipo == "duvida" else _db.comunidade_respostas
    campo = "duvida_id" if tipo == "duvida" else "resposta_id"
    alvo = await colecao.find_one({campo: alvo_id}, {"_id": 0, "student_id": 1})
    if not alvo:
        return {"ok": False, "motivo": "Conteúdo não encontrado."}
    if alvo["student_id"] == uid:
        return {"ok": False, "motivo": "Você não pode votar no próprio conteúdo."}

    try:
        await _db.comunidade_votos.insert_one(
            {"_id": f"{tipo}:{alvo_id}:{uid}", "uid": uid, "alvo": alvo_id, "tipo": tipo, "created_at": _now_iso()}
        )
    except DuplicateKeyError:
        return {"ok": False, "motivo": "Você já votou aqui."}
    await colecao.update_one({campo: alvo_id}, {"$inc": {"votos": 1}})
    return {"ok": True}


async def marcar_melhor(*, duvida_id: str, resposta_id: str, uid: str) -> dict[str, Any]:
    """O autor da dúvida escolhe a resposta que resolveu; ela paga Sparks.

    Ordem das travas, da mais barata para a mais cara: é minha dúvida? já tem
    uma marcada? a resposta existe? não é minha? o dono da resposta já bateu o
    teto do dia? Só depois de tudo isso o Firestore é tocado.
    """
    duvida = await _db.comunidade_duvidas.find_one({"duvida_id": duvida_id}, {"_id": 0})
    if not duvida or duvida["student_id"] != uid:
        return {"ok": False, "motivo": "Só quem publicou a dúvida pode marcar a resposta."}
    if duvida.get("melhor_resposta_id"):
        return {"ok": False, "motivo": "Esta dúvida já tem uma resposta marcada."}

    resposta = await _db.comunidade_respostas.find_one({"resposta_id": resposta_id, "duvida_id": duvida_id}, {"_id": 0})
    if not resposta:
        return {"ok": False, "motivo": "Resposta não encontrada."}
    if resposta["student_id"] == uid:
        return {"ok": False, "motivo": "Você não pode marcar a própria resposta."}

    marcado = await _db.comunidade_duvidas.update_one(
        {"duvida_id": duvida_id, "melhor_resposta_id": None},
        {"$set": {"melhor_resposta_id": resposta_id, "resolvida": True, "atualizado_em": _now_iso()}},
    )
    if marcado.modified_count == 0:
        return {"ok": False, "motivo": "Esta dúvida já tem uma resposta marcada."}
    await _db.comunidade_respostas.update_one({"resposta_id": resposta_id}, {"$set": {"melhor": True}})

    premiado = resposta["student_id"]
    dia = fs.dia_local()
    pagos_hoje = await _db.comunidade_respostas.count_documents(
        {"student_id": premiado, "melhor": True, "pago_em_dia": dia}
    )
    sparks = 0
    if pagos_hoje < MAX_SPARKS_DIA:
        concessao = await asyncio.to_thread(
            fs.grant_sparks_evento,
            premiado,
            categoria="comunidade",
            chave=f"melhor:{resposta_id}",
            amount=SPARKS_MELHOR_RESPOSTA,
            meta={"duvida_id": duvida_id},
        )
        sparks = concessao.get("sparks_ganhos", 0)
        await _db.comunidade_respostas.update_one({"resposta_id": resposta_id}, {"$set": {"pago_em_dia": dia}})

    # O XP vem mesmo quando o teto do dia já foi batido: o teto existe contra
    # fazenda de Sparks, e XP não é comprável nem transferível — segurá-lo só
    # puniria quem ajudou muita gente no mesmo dia.
    await engajamento_service.registrar_acao(premiado, ["resposta_util"], nome=resposta.get("autor_nome"))
    await engajamento_service.somar_ao_perfil(premiado, "respostas_uteis")
    return {"ok": True, "sparks_para_o_autor": sparks, "limite_diario_atingido": sparks == 0}


async def destacar(*, duvida_id: str, uid: str) -> dict[str, Any]:
    """Põe a dúvida no topo da área por 24h, por `CUSTO_DESTAQUE` Sparks."""
    duvida = await _db.comunidade_duvidas.find_one({"duvida_id": duvida_id}, {"_id": 0})
    if not duvida or duvida["student_id"] != uid:
        return {"ok": False, "motivo": "Só quem publicou pode destacar."}
    if duvida["status"] != "publicada":
        return {"ok": False, "motivo": "Esta dúvida não está no mural."}
    if (duvida.get("destacada_ate") or "") > _now_iso():
        return {"ok": False, "motivo": "Esta dúvida já está destacada."}

    try:
        saldo = await asyncio.to_thread(fs.deduct_sparks, uid, CUSTO_DESTAQUE)
    except fs.InsufficientSparksError as exc:
        return {"ok": False, "motivo": f"Faltam {exc.needed - exc.balance} Sparks.", "faltam": exc.needed - exc.balance}

    ate = (_now() + timedelta(hours=HORAS_DESTAQUE)).isoformat()
    try:
        await _db.comunidade_duvidas.update_one({"duvida_id": duvida_id}, {"$set": {"destacada_ate": ate}})
    except Exception:  # noqa: BLE001
        logger.exception("Destaque não aplicado em %s — devolvendo Sparks", duvida_id)
        saldo = await asyncio.to_thread(fs.refund_sparks, uid, CUSTO_DESTAQUE)
        return {"ok": False, "motivo": "Não foi possível destacar agora. Seus Sparks foram devolvidos."}
    return {"ok": True, "destacada_ate": ate, "sparks_balance": saldo}


# ---------------------------------------------------------------------------
# Moderação
# ---------------------------------------------------------------------------

async def reportar(*, tipo: str, alvo_id: str, uid: str, motivo: str) -> dict[str, Any]:
    """Reporte de conteúdo. `$addToSet` porque o que conta é gente DIFERENTE:
    a mesma pessoa clicando cinco vezes não pode tirar nada do ar."""
    colecao = _db.comunidade_duvidas if tipo == "duvida" else _db.comunidade_respostas
    campo = "duvida_id" if tipo == "duvida" else "resposta_id"
    alvo = await colecao.find_one({campo: alvo_id}, {"_id": 0})
    if not alvo:
        return {"ok": False, "motivo": "Conteúdo não encontrado."}

    await colecao.update_one({campo: alvo_id}, {"$addToSet": {"reportada_por": uid}})
    atualizado = await colecao.find_one({campo: alvo_id}, {"_id": 0, "reportada_por": 1})
    quantos = len(atualizado.get("reportada_por") or [])

    await _db.comunidade_reportes.insert_one({
        "reporte_id": _uid(), "tipo": tipo, "alvo_id": alvo_id, "reportado_por": uid,
        "motivo": (motivo or "").strip()[:500], "created_at": _now_iso(), "resolvido": False,
    })
    if quantos >= REPORTES_PARA_OCULTAR and alvo.get("status") == "publicada":
        await colecao.update_one({campo: alvo_id}, {"$set": {"status": "em_revisao"}})
        logger.warning("Conteúdo %s %s ocultado por %d reportes distintos.", tipo, alvo_id, quantos)
    return {"ok": True, "reportes": quantos}


async def moderar(*, tipo: str, alvo_id: str, acao: str) -> dict[str, Any]:
    """Decisão do admin: `restaurar` devolve ao mural e zera os reportes (senão
    o próximo reporte sozinho o derrubaria de novo); `remover` é definitivo para
    o mural, mas guarda o documento — apagar destrói a prova de por que a
    decisão foi tomada."""
    colecao = _db.comunidade_duvidas if tipo == "duvida" else _db.comunidade_respostas
    campo = "duvida_id" if tipo == "duvida" else "resposta_id"
    novo = {"restaurar": "publicada", "remover": "removida"}.get(acao)
    if novo is None:
        return {"ok": False, "motivo": "Ação inválida."}
    mudanca: dict[str, Any] = {"$set": {"status": novo, "moderado_em": _now_iso()}}
    if acao == "restaurar":
        mudanca["$set"]["reportada_por"] = []
    resultado = await colecao.update_one({campo: alvo_id}, mudanca)
    if resultado.matched_count == 0:
        return {"ok": False, "motivo": "Conteúdo não encontrado."}
    await _db.comunidade_reportes.update_many({"alvo_id": alvo_id}, {"$set": {"resolvido": True}})
    return {"ok": True, "status": novo}


async def fila_de_moderacao() -> dict[str, Any]:
    duvidas = await _db.comunidade_duvidas.find(
        {"$or": [{"status": "em_revisao"}, {"reportada_por.0": {"$exists": True}}]}, {"_id": 0}
    ).sort("atualizado_em", -1).to_list(length=200)
    respostas = await _db.comunidade_respostas.find(
        {"$or": [{"status": "em_revisao"}, {"reportada_por.0": {"$exists": True}}]}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=200)
    return {"duvidas": duvidas, "respostas": respostas}
