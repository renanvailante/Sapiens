"""Fase 0 — destravar a evidência. Revisão humana e relatório de oferta.

Não é uma funcionalidade do aluno. É o pré-requisito de todas as outras fases,
e a razão é aritmética: duas escassezes silenciosas bloqueiam o ciclo inteiro.

1. **Revisão humana.** Zero itens revisados ⇒ `PORTAO_CRENCA_MODO=desligado`
   em produção desde 2026-09-04 ⇒ perfil provisório para todo aluno. Construir
   cinco superfícies sobre um corpus não revisado multiplica por cinco os
   lugares em que o produto afirma causalidade sem evidência revisada. Este
   módulo é o ÚNICO caminho legítimo para religar o portão: confirmar o elo de
   ordem 1 grava `qualidade.apto_para_camada_de_crenca` no item.

2. **Oferta de itens.** As Fases 1, 2 e 5 consomem itens de reteste POR
   PROCESSO. Se o acervo tem 3 itens ancorados em `PROC-x`, a fila repete as
   mesmas questões e o reteste mede memória do item, não estabilização da
   habilidade. Ninguém tinha medido essa oferta — `relatorio_de_oferta` mede, e
   o veredito dele é bloqueante: nenhuma fase seguinte entra para um processo
   que ele reprove.

Fronteira (R-7): revisar um item é ato humano registrado, item a item. Nada
aqui altera a ontologia, e nada aqui aprova em lote por heurística.

Custo: uma varredura da coleção `itens`, memorizada no processo — a mesma que
`annotation_service._build_item_index` já faz. Rotas de admin, nunca no caminho
do aluno.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import annotation_service
import firestore_service as fs
import motor_cognitivo
import portao_crenca
from canonical_ontology import load_ontology

logger = logging.getLogger("sapiens.curadoria")

# Um processo entra na Fase 1 com pelo menos isto. Os números são o mínimo
# aritmético para o reteste não ser teste de memória: menos de 4 itens e a
# terceira revisão repete a primeira questão; menos de 2 contextos e não existe
# transferência possível, só o mesmo item com outra roupa.
MIN_ITENS_POR_PROCESSO = 4
MIN_CONTEXTOS_POR_PROCESSO = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Índice com o ID do DOCUMENTO — o que `_build_item_index` não guarda
# ---------------------------------------------------------------------------
#
# `annotation_service._build_item_index` indexa o conteúdo do item por
# `item_id`/`item_hash` e descarta o id do documento do Firestore, que é
# exatamente o que precisamos para ESCREVER a revisão de volta. Em vez de
# alterar aquele índice (usado por motor, intervenções e resumo de sessão),
# este módulo mantém o seu, com a mesma disciplina de cache de processo.

_DOCS: dict[str, str] | None = None


def _indice_de_documentos(force: bool = False) -> dict[str, str]:
    """`{item_id: doc_id}` da coleção `itens`. Uma varredura, memorizada."""
    global _DOCS
    if _DOCS is not None and not force:
        return _DOCS
    mapa: dict[str, str] = {}
    for snap in fs.get_firestore().collection("itens").stream():
        doc = snap.to_dict() or {}
        item = doc.get("item") or doc.get("pipeline") or {}
        item_id = item.get("item_id") or doc.get("item_id")
        if item_id:
            mapa[item_id] = snap.id
    _DOCS = mapa
    return mapa


def esquecer() -> None:
    global _DOCS
    _DOCS = None


# ---------------------------------------------------------------------------
# Relatório de oferta — o veredito bloqueante
# ---------------------------------------------------------------------------


def _processos_do_item(item: dict) -> set[str]:
    nodes = (item.get("estrutura_cognitiva") or {}).get("processos") or []
    return {n.get("id") if isinstance(n, dict) else n for n in nodes if n}


def _contexto(item: dict) -> str | None:
    import revisao_service

    return revisao_service.contexto_do_item(item)


def _raizes_anotadas(item: dict) -> set[tuple[str, str]]:
    """Pares (erro, processo) que aparecem como RAIZ em algum distrator deste
    item, já validados contra o catálogo — par não autorizado não conta como
    oferta, porque o motor vai descartá-lo de qualquer jeito (R-1)."""
    pares: set[tuple[str, str]] = set()
    for d in item.get("distratores") or []:
        if not isinstance(d, dict):
            continue
        elos, _ = motor_cognitivo._validar_cadeia(d.get("erros_esperados") or [])
        if elos:
            pares.add((elos[0]["erro"], elos[0]["processo_afetado"]))
    return pares


def _tem_intervencao(item: dict, processo_id: str) -> bool:
    for b in item.get("intervencoes") or []:
        if isinstance(b, dict) and (b.get("gatilho") or {}).get("processo") == processo_id:
            return True
    return False


def _itens_unicos(index: dict[str, dict]) -> list[dict]:
    """O índice mapeia item_id E item_hash para o mesmo item — deduplicar é
    obrigatório, senão todo item é contado duas vezes."""
    vistos: set[str] = set()
    saida = []
    for item in index.values():
        item_id = item.get("item_id")
        if not item_id or item_id in vistos:
            continue
        vistos.add(item_id)
        saida.append(item)
    return saida


def relatorio_de_oferta() -> dict[str, Any]:
    """Por processo do catálogo: quantos itens existem, quantos têm cadeia
    anotada, quantos têm bloco `intervencoes[]`, em quantos contextos
    distintos, e quantos já passaram por revisão humana.

    O veredito (`apto_para_fase_1`) é o que decide o escopo das Fases 1/2/5.
    Processo reprovado não entra — e a linha de transferência da fila diária
    simplesmente não aparece para ele, em vez de degradar para "mais um item
    igual".
    """
    onto = load_ontology()
    catalogo = {p.get("id"): p for p in onto.get("processos_cognitivos") or [] if p.get("id")}
    itens = _itens_unicos(annotation_service._build_item_index())

    linhas: dict[str, dict[str, Any]] = {
        pid: {
            "processo_id": pid,
            "processo_nome": (proc.get("nome") or pid),
            "itens": 0,
            "com_cadeia_raiz": 0,
            "com_intervencao": 0,
            "revisados": 0,
            "aptos": 0,
            "contextos": set(),
            "pares_raiz": set(),
        }
        for pid, proc in catalogo.items()
    }

    total_revisados = total_aptos = 0
    for item in itens:
        qual = item.get("qualidade") or {}
        revisado = qual.get("revisado") is True
        apto = portao_crenca.apto(item)
        total_revisados += 1 if revisado else 0
        total_aptos += 1 if apto else 0
        ctx = _contexto(item)
        raizes = _raizes_anotadas(item)
        for pid in _processos_do_item(item):
            linha = linhas.get(pid)
            if linha is None:
                continue  # processo fora do catálogo vigente: não é oferta
            linha["itens"] += 1
            linha["revisados"] += 1 if revisado else 0
            linha["aptos"] += 1 if apto else 0
            if ctx:
                linha["contextos"].add(ctx)
            do_processo = {p for p in raizes if p[1] == pid}
            if do_processo:
                linha["com_cadeia_raiz"] += 1
                linha["pares_raiz"] |= do_processo
            if _tem_intervencao(item, pid):
                linha["com_intervencao"] += 1

    saida = []
    for linha in linhas.values():
        contextos = sorted(linha.pop("contextos"))
        pares = sorted(f"{e}|{p}" for e, p in linha.pop("pares_raiz"))
        motivos = []
        if linha["itens"] < MIN_ITENS_POR_PROCESSO:
            motivos.append(f"apenas {linha['itens']} item(ns) no acervo (mínimo {MIN_ITENS_POR_PROCESSO})")
        if len(contextos) < MIN_CONTEXTOS_POR_PROCESSO:
            motivos.append(f"{len(contextos)} contexto(s) distinto(s) — sem transferência possível")
        if not linha["com_cadeia_raiz"]:
            motivos.append("nenhum item com cadeia de erro anotada como raiz")
        saida.append(
            {
                **linha,
                "contextos": contextos,
                "contextos_distintos": len(contextos),
                "pares_raiz": pares,
                "apto_para_fase_1": not motivos,
                "motivos": motivos,
            }
        )
    saida.sort(key=lambda l: (not l["apto_para_fase_1"], -l["itens"]))

    aprovados = [l for l in saida if l["apto_para_fase_1"]]
    return {
        "gerado_em": _now_iso(),
        "ontology_version": onto.get("version"),
        "portao": portao_crenca.modo(),
        "acervo": {
            "itens": len(itens),
            "revisados": total_revisados,
            "aptos_para_crenca": total_aptos,
            "processos_no_catalogo": len(catalogo),
        },
        "criterio": {
            "min_itens": MIN_ITENS_POR_PROCESSO,
            "min_contextos": MIN_CONTEXTOS_POR_PROCESSO,
        },
        "processos": saida,
        "aprovados": [l["processo_id"] for l in aprovados],
        # A frase que o admin precisa ler antes de abrir escopo de fase.
        "veredito": (
            f"{len(aprovados)} de {len(catalogo)} processos têm oferta suficiente para reteste. "
            f"{total_revisados} de {len(itens)} itens passaram por revisão humana."
        ),
    }


def processos_aprovados() -> set[str]:
    """Só os IDs — para quem precisa do veredito e não do relatório."""
    try:
        return set(relatorio_de_oferta()["aprovados"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("curadoria: relatório de oferta indisponível: %s", exc)
        return set()


# ---------------------------------------------------------------------------
# Fila de revisão humana
# ---------------------------------------------------------------------------


def fila_de_revisao(
    *, par: Optional[str] = None, apenas_pendentes: bool = True, limite: int = 50
) -> dict[str, Any]:
    """Itens esperando confirmação do elo de ordem 1, agrupados por par.

    O revisor vê o item, o distrator e a cadeia que o anotador escreveu, e diz
    uma coisa só: **este elo raiz se sustenta?** É a pergunta mínima que o
    portão de crença exige (Error Trace §6 / EXT-WP1-1.0 L13b) — não é revisão
    de gabarito, não é revisão de enunciado.
    """
    itens = _itens_unicos(annotation_service._build_item_index())
    grupos: dict[str, dict[str, Any]] = {}
    pendentes = 0

    for item in itens:
        qual = item.get("qualidade") or {}
        revisado = qual.get("revisado") is True
        if apenas_pendentes and revisado:
            continue
        fonte = item.get("fonte") or {}
        for d in item.get("distratores") or []:
            if not isinstance(d, dict):
                continue
            elos, motivos = motor_cognitivo._validar_cadeia(d.get("erros_esperados") or [])
            if not elos:
                continue
            raiz = elos[0]
            chave = f"{raiz['erro']}|{raiz['processo_afetado']}"
            if par and chave != par:
                continue
            g = grupos.setdefault(
                chave,
                {
                    "par": chave,
                    "erro_id": raiz["erro"],
                    "erro_nome": motor_cognitivo._nome_erro(raiz["erro"]),
                    "processo_id": raiz["processo_afetado"],
                    "processo_nome": motor_cognitivo._nome_processo(raiz["processo_afetado"]),
                    "itens": [],
                    # Quantas linhas o par TEM, não quantas couberam. Uma fila
                    # de revisão que trunca em silêncio é pior que uma fila
                    # vazia: o revisor termina a tela achando que acabou, e os
                    # itens que sobraram nunca mais aparecem para ninguém.
                    "total_no_par": 0,
                },
            )
            g["total_no_par"] += 1
            pendentes += 0 if revisado else 1
            if len(g["itens"]) >= limite:
                continue
            g["itens"].append(
                {
                    "item_id": item.get("item_id"),
                    "alternativa": d.get("alternativa"),
                    "explicacao_do_distrator": d.get("explicacao"),
                    "cadeia": [
                        {
                            "ordem": e["ordem"],
                            "papel": "raiz" if e["ordem"] == 1 else "consequência",
                            "erro_id": e["erro"],
                            "erro_nome": motor_cognitivo._nome_erro(e["erro"]),
                            "processo_id": e["processo_afetado"],
                            "processo_nome": motor_cognitivo._nome_processo(e["processo_afetado"]),
                            "confianca": e["confianca"],
                        }
                        for e in elos
                    ],
                    "elos_invalidos": motivos,
                    "enunciado": (item.get("questao") or {}).get("enunciado"),
                    "fonte": {
                        "banca": fonte.get("banca"),
                        "ano": fonte.get("ano"),
                        "prova": fonte.get("prova"),
                        "numero": fonte.get("numero"),
                        "tema": fonte.get("tema"),
                    },
                    "revisado": revisado,
                    "apto": portao_crenca.apto(item),
                    "revisor": qual.get("revisor"),
                }
            )

    lista = sorted(grupos.values(), key=lambda g: -g["total_no_par"])
    truncados = [g["par"] for g in lista if g["total_no_par"] > len(g["itens"])]
    return {
        "gerado_em": _now_iso(),
        "portao": portao_crenca.modo(),
        "pares": lista,
        "itens_pendentes": pendentes,
        "total_no_acervo": len(itens),
        "limite_por_par": limite,
        # Declarado para a tela poder avisar. `[]` é o estado normal.
        "pares_truncados": truncados,
    }


def revisar_item(
    item_id: str, *, aprovado: bool, revisor: str, observacoes: str = ""
) -> dict[str, Any]:
    """Registra a revisão humana de UM item e liga (ou não) o portão para ele.

    `aprovado=True` significa: o elo de ordem 1 anotado neste item se sustenta,
    e portanto os erros dos alunos neste item PODEM mover o estado cognitivo
    deles. `aprovado=False` registra a revisão sem abrir o portão — o item
    continua circulando na prova (o portão fechado proíbe alimentar crença, não
    ser praticado) e para de aparecer como pendente.
    """
    doc_id = _indice_de_documentos().get(item_id)
    if not doc_id:
        doc_id = _indice_de_documentos(force=True).get(item_id)
    if not doc_id:
        raise KeyError(f"item '{item_id}' não está na coleção 'itens'")

    marca = {
        "revisado": True,
        "revisor": revisor,
        "data_revisao": _now_iso(),
        "apto_para_camada_de_crenca": {"valor": bool(aprovado), "revisor": revisor, "em": _now_iso()},
    }
    if observacoes:
        marca["observacoes"] = observacoes

    fs.get_firestore().collection("itens").document(doc_id).set({"item": {"qualidade": marca}}, merge=True)

    # O índice de itens é cache de processo e alimenta motor, intervenções e
    # este módulo. Sem invalidar, o portão continuaria fechado para todo mundo
    # até o próximo deploy — a revisão teria acontecido e não teria efeito.
    annotation_service._build_item_index(force=True)
    motor_cognitivo.esquecer_historico()
    esquecer()
    return {"ok": True, "item_id": item_id, "aprovado": bool(aprovado), "doc_id": doc_id}


def revisar_em_lote(
    item_ids: Iterable[str], *, aprovado: bool, revisor: str
) -> dict[str, Any]:
    """Vários itens, um ato humano por item — o lote é conveniência de
    interface, não julgamento automático: o revisor viu cada linha na tela
    antes de marcar. Falha de um item não derruba os outros."""
    ok, erros = [], []
    for item_id in item_ids:
        try:
            revisar_item(item_id, aprovado=aprovado, revisor=revisor)
            ok.append(item_id)
        except Exception as exc:  # noqa: BLE001
            erros.append({"item_id": item_id, "erro": str(exc)})
    return {"ok": True, "revisados": ok, "falhas": erros}
