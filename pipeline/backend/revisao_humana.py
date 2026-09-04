"""Registro explícito de revisão humana de itens.

O portão `qualidade.apto_para_camada_de_crenca` só é legítimo se existir, fora
do item, um registro de QUEM revisou, QUANDO e SOBRE QUAL conteúdo. Guardar a
resposta dentro do próprio item — como `qualidade.revisado` fazia — permite que
quem escreve o item escreva também o próprio atestado, que foi exatamente como
223 dos 268 itens do corpus apareceram "revisados" sem nenhum humano envolvido.

O registro amarra a revisão ao CONTEÚDO revisado (`item_hash` no momento da
revisão). Se o conteúdo mudar depois, a revisão deixa de valer sozinha — sem
isso, revisar uma questão uma vez a deixaria aprovada para sempre, inclusive
depois de o enunciado ser reescrito.

Contrato: EXT-WP1-1.0 L13b, Especificação do Error Trace §6, Schema 2.2
`qualidade.apto_para_camada_de_crenca`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

COLECAO = "revisoes_humanas"

DECISOES = ("aprovado", "reprovado")


class RevisaoInvalida(ValueError):
    pass


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def garantir_indices(db) -> None:
    db[COLECAO].create_index([("item_id", 1), ("item_hash", 1)], unique=True)
    db[COLECAO].create_index([("item_id", 1), ("revisado_em", -1)])


def registrar(
    db,
    *,
    item_id: str,
    item_hash: str,
    revisor: str,
    decisao: str = "aprovado",
    processo_nuclear: str | None = None,
    observacoes: str = "",
) -> dict[str, Any]:
    """Grava UM registro de revisão. Idempotente por (item_id, item_hash).

    `processo_nuclear` é o processo cujo papel o revisor confirmou — é essa
    confirmação, e não a leitura geral do item, que EXT-WP1-1.0 L13b exige.
    """
    if decisao not in DECISOES:
        raise RevisaoInvalida(f"decisao deve ser uma de {DECISOES}, recebeu '{decisao}'")
    if not item_id or not item_hash:
        raise RevisaoInvalida("item_id e item_hash são obrigatórios")
    if not revisor:
        raise RevisaoInvalida("revisor é obrigatório — uma revisão sem revisor não é revisão")

    registro = {
        "item_id": item_id,
        "item_hash": item_hash,
        "revisor": revisor,
        "decisao": decisao,
        "processo_nuclear_confirmado": processo_nuclear,
        "observacoes": observacoes,
        "revisado_em": _agora(),
    }
    db[COLECAO].update_one(
        {"item_id": item_id, "item_hash": item_hash},
        {"$set": registro},
        upsert=True,
    )
    return registro


def revisao_vigente(db, item_id: str, item_hash: str) -> dict[str, Any] | None:
    """Registro que aprova ESTE conteúdo, ou None."""
    return db[COLECAO].find_one(
        {"item_id": item_id, "item_hash": item_hash, "decisao": "aprovado"},
        {"_id": 0},
    )


def esta_aprovado(db, item_id: str, item_hash: str) -> bool:
    return revisao_vigente(db, item_id, item_hash) is not None


def aplicar_ao_item(db, item: dict) -> dict:
    """Deriva `qualidade.revisado` e o portão a partir do REGISTRO.

    Derivação, nunca atribuição — mesmo padrão de `estrutura_cognitiva.dominios`.
    O item não é a fonte da própria aprovação.
    """
    qual = item.setdefault("qualidade", {}) or {}
    aprovado = esta_aprovado(db, item.get("item_id") or "", item.get("item_hash") or "")
    qual["revisado"] = aprovado
    qual["apto_para_camada_de_crenca"] = {"valor": aprovado}
    item["qualidade"] = qual
    return item


def itens_com_revisado_sem_registro(db, itens: list[dict]) -> list[str]:
    """`item_id`s que afirmam `revisado: true` sem registro que sustente.

    É a checagem GOV-01 do auditor, na forma reutilizável pelo pipeline.
    """
    fora = []
    for doc in itens:
        item = doc.get("item") or doc
        qual = item.get("qualidade") or {}
        if not qual.get("revisado"):
            continue
        if not esta_aprovado(db, item.get("item_id") or "", item.get("item_hash") or ""):
            fora.append(item.get("item_id"))
    return fora
