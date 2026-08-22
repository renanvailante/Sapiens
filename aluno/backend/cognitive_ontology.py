"""Ontologia Cognitiva Sapiens — arquitetura em rede.

FONTE ÚNICA: `pipeline/docs/ontology/ontology_v1.4.json` (hoje na versão
**1.4.1**), resolvido por `canonical_ontology`. As relações são LIDAS
explicitamente do JSON, sem inventar categorias:

    domínio → competência → processo → habilidade

Relações no JSON:
- competencia.processos          → processos da competência
- processo.competencia           → competência do processo
- processo.dominios              → domínios do processo
- habilidade.processos_cognitivos→ processos que a habilidade observa

A competência é ancorada ao domínio do(s) seu(s) processo(s) — derivação, nunca
atribuição direta, conforme a proibição da Constituição §4.4.
Sem IA/LLM — puro agregado determinístico.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from canonical_ontology import load_ontology, ontology_version  # noqa: F401  (reexport)


def build_ontology_tree(answered_process_ids: set[str] | None = None) -> list[dict[str, Any]]:
    """Monta a árvore completa do catálogo canônico vigente.

    answered_process_ids: conjunto de IDs de processo (PROC-*) que o usuário
    efetivamente ativou (respondeu ao menos uma questão que os aciona).

    Propagação de `answered`:
    - processo   : respondido se estiver em answered_process_ids
    - habilidade : respondida se o processo pai foi respondido (granularidade
                   das anotações é por processo)
    - competência: respondida se algum processo filho foi respondido
    - domínio    : respondido se alguma competência filha foi respondida
    """
    answered = set(answered_process_ids or [])
    onto = load_ontology()
    domains = onto.get("dominios", [])
    comps = onto.get("competencias", [])
    procs = onto.get("processos_cognitivos", [])
    habs = onto.get("habilidades_observaveis", [])

    proc_by_id = {p["id"]: p for p in procs}

    habs_by_proc: dict[str, list] = defaultdict(list)
    for h in habs:
        for pid in h.get("processos_cognitivos", []) or []:
            habs_by_proc[pid].append(h)

    # Ancora cada competência ao domínio do primeiro processo que tem domínio.
    comp_domain: dict[str, str | None] = {}
    for c in comps:
        dom = None
        for pid in c.get("processos", []) or []:
            p = proc_by_id.get(pid)
            if p and p.get("dominios"):
                dom = p["dominios"][0]
                break
        comp_domain[c["id"]] = dom

    comps_by_domain: dict[str | None, list] = defaultdict(list)
    for c in comps:
        comps_by_domain[comp_domain[c["id"]]].append(c)

    tree: list[dict[str, Any]] = []
    for d in domains:
        dnode: dict[str, Any] = {
            "code": d["id"],
            "nome": d.get("nome", d["id"]),
            "descricao": d.get("descricao", ""),
            "level": "dominio",
            "children": [],
        }
        dom_answered = False
        for c in comps_by_domain.get(d["id"], []):
            cnode: dict[str, Any] = {
                "code": c["id"],
                "nome": c.get("nome", c["id"]),
                "level": "competencia",
                "children": [],
            }
            comp_answered = False
            for pid in c.get("processos", []) or []:
                p = proc_by_id.get(pid)
                if not p:
                    continue
                p_answered = pid in answered
                if p_answered:
                    comp_answered = True
                pnode = {
                    "code": pid,
                    "nome": p.get("nome", pid),
                    "definicao": p.get("definicao_operacional", ""),
                    "level": "processo",
                    "answered": p_answered,
                    "children": [
                        {
                            "code": h["id"],
                            "nome": h.get("nome", h["id"]),
                            "level": "habilidade",
                            "answered": p_answered,
                        }
                        for h in habs_by_proc.get(pid, [])
                    ],
                }
                cnode["children"].append(pnode)
            cnode["answered"] = comp_answered
            dom_answered = dom_answered or comp_answered
            dnode["children"].append(cnode)
        dnode["answered"] = dom_answered
        tree.append(dnode)
    return tree
