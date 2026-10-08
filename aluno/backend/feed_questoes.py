"""O Folhear sobre questões REAIS do acervo — o lote seguinte do feed infinito.

`/estudar/folhear` nasceu como feed de cards autorais (`feed_items`), e a
coleção de produção está vazia: o aluno abria e lia "Você chegou ao fim." no
primeiro card. Encher com card de exemplo seria conteúdo fictício. O que o
produto TEM, em quantidade, são questões reais do ENEM — e é delas que o feed
infinito é feito, um item por tela.

A ordem do lote, do mais útil ao menos:

1. **padrão de erro** — questões inéditas que exercitam os processos em que o
   aluno mais erra (os ids vêm de `/motor/perfil`, que a tela já carregou; a
   mesma fila que o Próximo Passo usa);
2. **acervo** — as outras inéditas, primeiro as frentes que mais pesam na nota
   (`prioridade_enem`, a escala do dono: Matemática > Natureza > Humanas e
   Linguagens), embaralhadas de forma estável por aluno e por dia;
3. **rever** — quando não sobra inédita, as já respondidas voltam (primeiro as
   do padrão de erro). É isso que faz o feed não ter fim.

Custo: UMA leitura do Firestore por lote (`ler_agregado`, para saber o que já
foi respondido) e duas consultas ao Mongo (`questoes_public`, só `item_id` e
`fonte`; depois o corpo das escolhidas). O índice de itens anotados é o cache
de processo que o motor já mantém. Nada aqui é O(eventos).

O gabarito nunca sai: a projeção é a mesma de `server.PROJECAO_SEM_GABARITO`.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

import prioridade_enem as pe

PROJECAO_SEM_GABARITO = {"_id": 0, "master_id": 0, "questao.alternativas.correta": 0}

LOTE_MAX = 8
MAX_EXCLUIR = 600
MAX_PROCESSOS = 5
_PROC = re.compile(r"^PROC-[A-Z]+-\d{2}$")
_ITEM = re.compile(r"^[A-Za-z0-9_.:\-]{1,120}$")


def processos_validos(bruto: str | None) -> list[str]:
    saida: list[str] = []
    for p in (bruto or "").split(","):
        p = p.strip()
        if _PROC.match(p) and p not in saida:
            saida.append(p)
        if len(saida) >= MAX_PROCESSOS:
            break
    return saida


def ids_validos(bruto: str | None) -> set[str]:
    ids = [i.strip() for i in (bruto or "").split(",") if i.strip()]
    return {i for i in ids[:MAX_EXCLUIR] if _ITEM.match(i)}


def _processos_do_item(item: dict) -> set[str]:
    nos = (item.get("estrutura_cognitiva") or {}).get("processos") or []
    return {n.get("id") if isinstance(n, dict) else n for n in nos} - {None}


def _peso(fonte: dict | None) -> float:
    chave = pe.classificar_disciplina((fonte or {}).get("disciplina"))
    return float((pe._POR_CHAVE.get(chave) or {}).get("peso", 0.5))


def _mistura(semente: str, item_id: str) -> str:
    return hashlib.sha256(f"{semente}:{item_id}".encode("utf-8")).hexdigest()


def escolher(
    *,
    index: dict[str, dict],
    acervo: Iterable[dict],
    respondidos: set[str],
    excluir: set[str],
    processos: list[str],
    limite: int,
    semente: str,
) -> list[dict[str, Any]]:
    """O lote: `[{item_id, motivo, processo_id?}]`, sem repetir nada de
    `excluir` (o que a tela já mostrou nesta sessão)."""
    limite = max(1, min(int(limite), LOTE_MAX))
    acervo = [a for a in acervo if a.get("item_id")]
    existentes = {a["item_id"] for a in acervo}
    escolhidos: list[dict[str, Any]] = []
    usados = set(excluir)

    def _por(item_id: str, motivo: str, pid: str | None = None) -> bool:
        if item_id in usados or item_id not in existentes:
            return False
        usados.add(item_id)
        escolhidos.append({"item_id": item_id, "motivo": motivo, **({"processo_id": pid} if pid else {})})
        return len(escolhidos) >= limite

    # Itens anotados por processo, uma passada só pelo índice.
    por_processo: dict[str, list[str]] = {p: [] for p in processos}
    if processos:
        vistos: set[str] = set()
        for item in index.values():
            iid = item.get("item_id")
            if not iid or iid in vistos:
                continue
            vistos.add(iid)
            for p in _processos_do_item(item) & set(processos):
                por_processo[p].append(iid)
        for p in processos:
            por_processo[p].sort(key=lambda i: _mistura(semente, i))

    # 1. padrão de erro — inéditas, intercalando os processos (um de cada vez)
    # para o feed não virar dez questões do mesmo ponto em seguida.
    filas = [[i for i in por_processo[p] if i not in respondidos] for p in processos]
    while any(filas):
        for p, fila in zip(processos, filas):
            if fila and _por(fila.pop(0), "padrao", p):
                return escolhidos

    # 2. acervo — inéditas, peso da frente primeiro.
    ineditas = [a for a in acervo if a["item_id"] not in respondidos]
    ineditas.sort(key=lambda a: (-_peso(a.get("fonte")), _mistura(semente, a["item_id"])))
    for a in ineditas:
        if _por(a["item_id"], "acervo"):
            return escolhidos

    # 3. rever — o que já foi respondido volta, padrão de erro primeiro.
    for p in processos:
        for iid in por_processo[p]:
            if iid in respondidos and _por(iid, "rever", p):
                return escolhidos
    ja = [a for a in acervo if a["item_id"] in respondidos]
    ja.sort(key=lambda a: _mistura(semente, a["item_id"]))
    for a in ja:
        if _por(a["item_id"], "rever"):
            return escolhidos
    return escolhidos
