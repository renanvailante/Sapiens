"""Constrói a árvore da Ontologia Cognitiva Sapiens v1.4 a partir do corpus
de questões auditadas (questoes_master). NÃO inventa categorias: cada nó
(domínio/competência/processo/habilidade) é um código v1.4 que existe nos dados.

Relações de parentesco (domínio→competência→processo→habilidade):
- habilidade → processo: link EXPLÍCITO no dado (processo.habilidades).
- processo → competência e competência → domínio: derivadas por co-ocorrência
  dominante dentro do mesmo item anotado (o corpus v1.4 é a fonte).

Sem IA/LLM — puro agregado determinístico.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _ec(m: dict) -> dict:
    return (m.get("pipeline") or {}).get("estrutura_cognitiva") or {}


def build_ontology_tree(masters: list[dict], answered_master_ids: set[str]) -> list[dict[str, Any]]:
    comp_dom: dict[str, Counter] = defaultdict(Counter)
    proc_comp: dict[str, Counter] = defaultdict(Counter)
    proc_habs: dict[str, set] = defaultdict(set)

    all_doms: set[str] = set()
    dom_ok: set[str] = set()
    comp_ok: set[str] = set()
    proc_ok: set[str] = set()
    hab_ok: set[str] = set()

    for m in masters:
        ec = _ec(m)
        doms = [d.get("id") for d in (ec.get("dominios") or []) if d.get("id")]
        comps = [c.get("id") for c in (ec.get("competencias") or []) if c.get("id")]
        procs = ec.get("processos") or []
        answered = m.get("id") in answered_master_ids

        for d in doms:
            all_doms.add(d)
            if answered:
                dom_ok.add(d)
        for c in comps:
            if answered:
                comp_ok.add(c)
            for d in doms:
                comp_dom[c][d] += 1
        for p in procs:
            pid = p.get("id")
            if not pid:
                continue
            if answered:
                proc_ok.add(pid)
            for h in (p.get("habilidades") or []):
                hid = h.get("id")
                if not hid:
                    continue
                proc_habs[pid].add(hid)
                if answered:
                    hab_ok.add(hid)
            for c in comps:
                proc_comp[pid][c] += 1

    comp_parent = {c: (cnt.most_common(1)[0][0] if cnt else None) for c, cnt in comp_dom.items()}
    proc_parent = {p: (cnt.most_common(1)[0][0] if cnt else None) for p, cnt in proc_comp.items()}

    comps_by_dom: dict[str, list] = defaultdict(list)
    for c, d in comp_parent.items():
        comps_by_dom[d].append(c)
    procs_by_comp: dict[str, list] = defaultdict(list)
    for p, c in proc_parent.items():
        procs_by_comp[c].append(p)

    tree: list[dict[str, Any]] = []
    for d in sorted(all_doms):
        dnode = {"code": d, "level": "dominio", "answered": d in dom_ok, "children": []}
        for c in sorted(comps_by_dom.get(d, [])):
            cnode = {"code": c, "level": "competencia", "answered": c in comp_ok, "children": []}
            for p in sorted(procs_by_comp.get(c, [])):
                pnode = {
                    "code": p,
                    "level": "processo",
                    "answered": p in proc_ok,
                    "children": [
                        {"code": h, "level": "habilidade", "answered": h in hab_ok}
                        for h in sorted(proc_habs.get(p, []))
                    ],
                }
                cnode["children"].append(pnode)
            dnode["children"].append(cnode)
        tree.append(dnode)
    return tree
