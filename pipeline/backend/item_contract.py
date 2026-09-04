"""Normalização de um item anotado para o **Schema Sapiens 2.2**.

Este módulo faz o que o contrato exige e o modelo não pode fazer sozinho:

* carimba `schema_version` e `ontology_version` (GOV-1.0 §6.1);
* calcula `item_id` **estável** e `item_hash` **determinístico**;
* **deriva** `estrutura_cognitiva.dominios[]` e `.competencias[]` a partir dos
  processos, em vez de aceitá-los do modelo (Constituição §4.4);
* normaliza `confianca` de rótulo (`alta`/`media`/`baixa`) para o valor de
  registro correspondente (Especificação do Error Trace §5).

Ele **não** inventa conteúdo cognitivo: nenhum ID é criado, corrigido,
substituído ou inferido aqui. O que o modelo não produziu permanece ausente e é
reportado pela validação.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from ontology_validator import (
    CONFIANCA_BINS,
    OntologyRegistry,
    derivar_estrutura,
    validate_item_annotation,
)

SCHEMA_VERSION = "2.2"

# Campos de `fonte` necessários para um item_id determinístico legível.
_FONTE_PARA_ID = ("banca", "ano", "prova", "numero")


def compute_item_hash(questao: Any) -> str:
    """Hash determinístico do conteúdo canônico do item.

    Calculado **somente** sobre o bloco `questao` (enunciado, alternativas,
    recursos) — o conteúdo que o estudante realmente vê. A classificação
    cognitiva fica de fora de propósito: reanotar um item não muda o item, e um
    evento de behavior gravado antes da reanotação continua apontando para o
    mesmo conteúdo respondido.
    """
    canonical = json.dumps(questao, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _slug(value: Any) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "", str(value or "")).upper()
    return s


def build_item_id(fonte: dict | None, fallback: str | None = None) -> str:
    """`item_id` estável, invariável entre pipeline, Firestore, aluno e professor.

    O Schema 2.2 separa duas exigências de força diferente, e o código as trata
    separadamente porque elas não são a mesma coisa:

    * **Obrigação:** "Identificador único e estável da questão. Deve permanecer
      invariável entre pipeline, Firestore, aluno e professor."
    * **Recomendação:** "Recomenda-se um formato determinístico baseado em
      fonte, ano, prova e número, por exemplo 'ITEM-ENEM-2024-CAD01-Q023'."

    Daí a bifurcação:

    * Fonte completa → identificador determinístico e legível
      (`ITEM-INEP-2024-ENEMCAD01-Q023`). Reingerir a mesma questão produz o
      mesmo id, o que torna a deduplicação possível.
    * Fonte incompleta → identificador opaco sorteado **uma única vez**
      (`ITEM-<uuid4hex>`) e daí em diante preservado.

    O identificador **não** é derivado do conteúdo. Isso não é preferência: um
    id derivado do conteúdo mudaria a cada correção de vírgula no enunciado, o
    que contradiz diretamente a obrigação de invariância acima e romperia todo
    evento de behavior já gravado contra o item. A divisão de trabalho está no
    próprio contrato — `item_hash` "deve mudar quando o conteúdo estrutural
    relevante da questão mudar"; `item_id` deve permanecer invariável.
    """
    fonte = fonte or {}
    if all(fonte.get(k) not in (None, "", []) for k in _FONTE_PARA_ID):
        banca = _slug(fonte["banca"])
        ano = _slug(fonte["ano"])
        prova = _slug(fonte["prova"])
        try:
            numero = f"Q{int(fonte['numero']):03d}"
        except (TypeError, ValueError):
            numero = f"Q{_slug(fonte['numero'])}"
        return f"ITEM-{banca}-{ano}-{prova}-{numero}"
    return fallback or f"ITEM-{uuid.uuid4().hex}"


def _normalize_confianca(value: Any) -> Any:
    """Converte o rótulo do bin no valor de registro (Error Trace §5).

    Os três valores são [DE, provisório] e calibráveis pelo piloto; a forma
    — bins declarados, obrigatórios, não determinísticos — não é. Valores
    numéricos já fornecidos passam intactos.
    """
    if isinstance(value, str) and value in CONFIANCA_BINS:
        return CONFIANCA_BINS[value]
    return value


def _normalize_confiancas_em_profundidade(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: (_normalize_confianca(v) if k in ("confianca", "confianca_global")
                else _normalize_confiancas_em_profundidade(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_normalize_confiancas_em_profundidade(x) for x in obj]
    return obj


_MEC_VALIDO = {f"MEC-{i:02d}" for i in range(1, 14)}


def _normalizar_letras(item: dict) -> None:
    """Padroniza em MAIÚSCULA **toda** referência a letra de alternativa.

    O modelo devolve ora 'A', ora 'a'. A letra é comparada com o gabarito
    oficial e com a resposta do aluno — divergir por caixa faz a correção falhar
    em silêncio, marcando errado quem acertou.

    Os dois lados do par precisam ser normalizados juntos: `questao.alternativas[].letra`
    e `distratores[].alternativa` referenciam a mesma coisa, e normalizar só um
    faz o distrator deixar de casar com a alternativa que ele descreve.
    """
    for alt in ((item.get("questao") or {}).get("alternativas") or []):
        if isinstance(alt, dict) and isinstance(alt.get("letra"), str):
            alt["letra"] = alt["letra"].strip().upper()
    for d in (item.get("distratores") or []):
        if isinstance(d, dict) and isinstance(d.get("alternativa"), str):
            d["alternativa"] = d["alternativa"].strip().upper()


def _limpar_mecanismo(item: dict) -> None:
    """Descarta `mecanismo` fora do vocabulário MEC-01..MEC-13.

    O campo é OPCIONAL e PROVISÓRIO (Error Trace §4.2): "nenhuma anotação é
    inválida por omiti-lo". Quando o modelo escreve prosa ali em vez do ID, o
    certo é descartar o valor — invalidar o item inteiro por causa de um campo
    que poderia simplesmente não existir perde a anotação toda por nada.
    """
    for d in (item.get("distratores") or []):
        if not isinstance(d, dict):
            continue
        for elo in (d.get("erros_esperados") or []):
            if isinstance(elo, dict) and elo.get("mecanismo") not in _MEC_VALIDO:
                elo.pop("mecanismo", None)


def normalize_item(
    raw: dict,
    ontology: dict,
    *,
    item_id: str | None = None,
    arquivo_origem: str | None = None,
    fonte_conhecida: dict | None = None,
    registry: OntologyRegistry | None = None,
) -> dict:
    """Aplica ao JSON cru do modelo tudo o que o Schema 2.2 exige.

    `item_id` só é gerado quando não vier; reprocessar um item existente
    preserva o identificador que ele já tinha.
    """
    reg = registry or OntologyRegistry()
    item = _normalize_confiancas_em_profundidade(dict(raw or {}))

    item["schema_version"] = SCHEMA_VERSION
    # Carimbado pelo servidor, nunca aceito do modelo: o modelo poderia copiar
    # errado, e um ontology_version errado é pior que ausente — faz a anotação
    # parecer datável quando não é.
    item["ontology_version"] = ontology.get("version")

    fonte = item.setdefault("fonte", {}) or {}
    if arquivo_origem and not fonte.get("arquivo_origem"):
        fonte["arquivo_origem"] = arquivo_origem
    # `fonte` conhecida pelo chamador SOBRESCREVE a inferida pelo modelo. O
    # modelo lê o cabeçalho da página e erra: numa prova de 2023 chegou a
    # devolver ano 2010 e 2016. Banca, ano e prova são metadado de procedência,
    # não algo a inferir do conteúdo (Manual §8).
    if fonte_conhecida:
        fonte.update({k: v for k, v in fonte_conhecida.items() if v not in (None, "")})
    item["fonte"] = fonte

    _normalizar_letras(item)
    _limpar_mecanismo(item)
    questao = item.get("questao") or {}
    item["item_hash"] = compute_item_hash(questao)
    item["item_id"] = item_id or item.get("item_id") or build_item_id(fonte)

    # Derivação, nunca atribuição (Constituição §4.4).
    ec = item.setdefault("estrutura_cognitiva", {}) or {}
    procs = ec.get("processos") or []
    dominios, competencias = derivar_estrutura(procs, reg)
    ec["dominios"] = dominios
    ec["competencias"] = competencias
    ec["processos"] = procs
    item["estrutura_cognitiva"] = ec

    qual = item.setdefault("qualidade", {}) or {}
    # EXT-WP1-1.0 L13b / Error Trace §6: um item pode ser ARMAZENADO sem revisão
    # humana; não pode influenciar o estado de um estudante real sem ela. O
    # pipeline nunca marca isto como verdadeiro — só a revisão humana marca.
    #
    # Até 2026-08-26 esta linha era `setdefault`, o que PRESERVAVA o valor que o
    # modelo tivesse mandado — e o modelo mandava `true`. 223 dos 268 itens do
    # corpus entraram assim, com o portão aberto pelo próprio anotador. Atribuição
    # incondicional: o único caminho que liga `revisado` a True é
    # `revisao_humana.registrar()`, com revisor identificado e registro auditável.
    qual["revisado"] = False
    qual["apto_para_camada_de_crenca"] = {"valor": False}
    item["qualidade"] = qual

    return item


def validate(item: dict, registry: OntologyRegistry | None = None) -> dict:
    """Atalho para o resultado de validação em forma serializável."""
    return validate_item_annotation(item, registry).to_dict()


def index_fields(item: dict) -> dict:
    """Colunas de índice/filtro derivadas do item 2.2.

    Só extrai o que já existe no objeto — nenhuma inferência.
    """
    fonte = item.get("fonte") or {}
    questao = item.get("questao") or {}
    ec = item.get("estrutura_cognitiva") or {}
    correta = next(
        (a.get("letra") for a in (questao.get("alternativas") or [])
         if isinstance(a, dict) and a.get("correta") is True),
        None,
    )
    return {
        "disciplina": fonte.get("disciplina"),
        "banca": fonte.get("banca"),
        "ano": str(fonte["ano"]) if fonte.get("ano") is not None else None,
        "tema": fonte.get("tema"),
        "resposta_correta": correta,
        "item_id": item.get("item_id"),
        "item_hash": item.get("item_hash"),
        "processos": [p.get("id") for p in (ec.get("processos") or []) if isinstance(p, dict) and p.get("id")],
        "competencias": [c.get("id") for c in (ec.get("competencias") or []) if isinstance(c, dict) and c.get("id")],
        "dominios": [d.get("id") for d in (ec.get("dominios") or []) if isinstance(d, dict) and d.get("id")],
    }
