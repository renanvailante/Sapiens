"""Analytics de PRODUTO — activation, time-to-first-value, primeira
microvitória, primeira compra/recompra, retenção/cohort.

**Por que isto não é `growth_events.py` nem `students/{uid}/behavior`.**
`growth_events` é escopado, por decisão já registrada, a aquisição — clique,
cadastro por indicação, comissão (ver o cabeçalho de `growth_events.py`,
"funil de marketing, NÃO o registro cognitivo"). `students/{uid}/behavior`
é o contrato canônico pedagógico do pipeline — resposta a questão, o que o
motor cognitivo interpreta. Nenhum dos dois é "o aluno usou o produto de um
jeito que indica valor percebido", que é uma pergunta de PRODUTO, não de
aquisição nem de pedagogia. Reabrir qualquer um dos dois pra caber isso
repetiria o erro que `growth_events.py` já recusou uma vez — por isso esta é
uma terceira coleção, pequena, com o mesmo espírito das outras duas.

**O que entra aqui.** Só os tipos em `TIPOS`, cada um um marco de FUNIL de
produto (não um log de toda ação). Nenhum dado de desempenho pedagógico.

**Idempotência por `_id` determinístico, não por checagem antes de gravar.**
Eventos "primeira vez" (`primeira_compra`, `primeira_microvitoria`,
`primeiro_proximo_passo`) usam `_id = f"{uid}:{tipo}"` — inserir de novo
esbarra em `DuplicateKeyError` e é ignorado, mesma disciplina de
`influencer_comissoes` (`_id = mp_payment_id`). `recompra` e
`descoberta_prioridade` podem acontecer mais de uma vez por aluno, então o
`_id` inclui o que torna aquela ocorrência única (o pagamento, a chave da
frente descoberta).

**Custo.** Nenhuma função aqui lê `students/{uid}/behavior` nem itera
eventos por aluno — o preço de qualquer leitura O(eventos) já custou um
apagão (ver `Cerebro/arquitetura/custo-de-leitura.md`). `resumo_cohort`
varre `product_events` (coleção NOVA, pequena, um documento por MARCO, não
por ação) e `users` (já é o padrão de `resumo_dos_alunos`), nunca Firestore.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

logger = logging.getLogger("sapiens.product_analytics")

TIPOS = (
    "primeiro_proximo_passo",   # primeira vez que o aluno age sobre a recomendação de Hoje
    "descoberta_prioridade",    # a frente #1 do ranking mudou pra uma nova, com medida real
    "primeira_microvitoria",    # primeira missão diária resgatada
    "primeira_compra",          # primeiro pagamento de Sparks aprovado
    "recompra",                 # segundo pagamento aprovado em diante
)

# Tipos "uma vez na vida" — `_id` é só `{uid}:{tipo}`, sem sufixo extra.
_UNICOS = {"primeiro_proximo_passo", "primeira_microvitoria", "primeira_compra"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def registrar(db, uid: str, tipo: str, *, chave: str | None = None, meta: dict[str, Any] | None = None) -> bool:
    """Grava um marco. Devolve `True` só se este era genuinamente o
    primeiro registro daquele marco (para quem chama decidir se comemora ou
    fica em silêncio) — `False` em duplicata ou tipo desconhecido."""
    if tipo not in TIPOS:
        logger.warning("product_analytics: tipo desconhecido '%s' — não registrado.", tipo)
        return False
    doc_id = f"{uid}:{tipo}" if tipo in _UNICOS else f"{uid}:{tipo}:{chave or _now_iso()}"
    try:
        await db.product_events.insert_one({
            "_id": doc_id,
            "uid": uid,
            "tipo": tipo,
            "chave": chave,
            "meta": meta or {},
            "created_at": _now_iso(),
        })
        return True
    except DuplicateKeyError:
        return False


async def primeiro_evento(db, uid: str) -> dict[str, Any] | None:
    """O marco mais antigo do aluno — o numerador de time-to-first-value."""
    docs = await db.product_events.find({"uid": uid}, {"_id": 0}).sort("created_at", 1).limit(1).to_list(1)
    return docs[0] if docs else None


async def tempo_para_primeiro_valor(db, uid: str, criado_em: str | None) -> float | None:
    """Horas entre o cadastro (`users.created_at`) e o primeiro marco de
    produto. `None` quando falta uma das duas datas — "não sei" nunca vira
    zero."""
    if not criado_em:
        return None
    evento = await primeiro_evento(db, uid)
    if evento is None:
        return None
    try:
        inicio = datetime.fromisoformat(criado_em)
        fim = datetime.fromisoformat(evento["created_at"])
    except (TypeError, ValueError):
        return None
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    return round((fim - inicio).total_seconds() / 3600, 2)


async def resumo_ativacao(db, *, dias: int = 30) -> dict[str, Any]:
    """Quantos alunos cadastrados nos últimos `dias` têm PELO MENOS um marco
    de produto (ativação, no sentido do funil, não do influencer) — e a
    contagem por tipo de marco, pra distinguir ONDE a ativação está
    acontecendo (primeira compra é ativação cara; primeira microvitória é
    barata)."""
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    cadastrados = await db.users.count_documents({"created_at": {"$gte": desde}})
    uids_cadastrados = {
        d["user_id"] async for d in db.users.find({"created_at": {"$gte": desde}}, {"_id": 0, "user_id": 1})
    }
    eventos = await db.product_events.find(
        {"created_at": {"$gte": desde}}, {"_id": 0, "uid": 1, "tipo": 1},
    ).to_list(200_000)
    ativados = {e["uid"] for e in eventos if e["uid"] in uids_cadastrados}
    por_tipo: dict[str, int] = {t: 0 for t in TIPOS}
    for e in eventos:
        if e["uid"] in uids_cadastrados:
            por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
    return {
        "janela_dias": dias,
        "cadastrados": cadastrados,
        "ativados": len(ativados),
        "taxa_ativacao": round(len(ativados) / cadastrados, 4) if cadastrados else None,
        "marcos_por_tipo": por_tipo,
    }


async def resumo_cohort(db, *, semanas: int = 8) -> list[dict[str, Any]]:
    """Uma linha por semana de cadastro: quantos entraram, quantos ativaram
    (>=1 marco), quantos compraram. Cohort clássico, sem inventar retenção
    D1/D7 por evento de sessão (que exigiria instrumentar login, fora de
    escopo aqui) — usa o que já é barato: cadastro (`users`) e marco
    (`product_events`)."""
    agora = datetime.now(timezone.utc)
    linhas: list[dict[str, Any]] = []
    for i in range(semanas):
        fim = agora - timedelta(weeks=i)
        inicio = fim - timedelta(weeks=1)
        inicio_iso, fim_iso = inicio.isoformat(), fim.isoformat()
        uids_semana = {
            d["user_id"] async for d in db.users.find(
                {"created_at": {"$gte": inicio_iso, "$lt": fim_iso}}, {"_id": 0, "user_id": 1},
            )
        }
        if not uids_semana:
            linhas.append({
                "semana_inicio": inicio.date().isoformat(), "cadastrados": 0,
                "ativados": 0, "compraram": 0,
            })
            continue
        eventos = await db.product_events.find(
            {"uid": {"$in": list(uids_semana)}}, {"_id": 0, "uid": 1, "tipo": 1},
        ).to_list(200_000)
        ativados = {e["uid"] for e in eventos}
        compraram = {e["uid"] for e in eventos if e["tipo"] in ("primeira_compra", "recompra")}
        linhas.append({
            "semana_inicio": inicio.date().isoformat(),
            "cadastrados": len(uids_semana),
            "ativados": len(ativados),
            "compraram": len(compraram),
        })
    linhas.reverse()  # mais antiga primeiro — leitura cronológica no admin
    return linhas
