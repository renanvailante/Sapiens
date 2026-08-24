"""Mapa de Habilidades — camada cosmética de gamificação para o aluno.

Nomes e agrupamentos aqui são GENÉRICOS e arbitrários, sem correspondência
1:1 declarada com a ontologia real (`pipeline/docs/ontology/ontology_v1.4.json`).
Existem só para dar ao aluno uma metáfora visual de progresso sem expor os
nomes reais de domínio/competência/processo/habilidade, que são propriedade
intelectual do produto. Nunca usar esta estrutura em qualquer inferência,
relatório ou decisão pedagógica real — é decoração, sem rigor metodológico.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

# hub cosmético -> IDs de domínio REAL (DOM-*) que alimentam o mastery daquele
# vértice do hexágono. Agrupamento livre, só para o número parecer "vivo".
HUB_DOMAIN_MAP: dict[int, list[str]] = {
    1: ["DOM-QUANT"],
    2: ["DOM-ESPACO"],
    3: ["DOM-MUDANCA", "DOM-SISTEMICO"],
    4: ["DOM-INCERTEZA", "DOM-CAUSAL"],
    5: ["DOM-SIMBOLICO", "DOM-TEXTUAL", "DOM-LOGICO"],
    6: ["DOM-EXPERIMENTAL", "DOM-CLASSIF"],
}

HUBS: list[dict[str, Any]] = [
    {
        "hub": 1,
        "label": "Raciocínio Numérico",
        "eyebrow": "eixo 01",
        "branches": [
            {"name": "Cálculo e proporção", "leaves": ["resolver proporção direta", "resolver proporção inversa"]},
            {"name": "Estimativa e escala", "leaves": ["estimar valores aproximados"]},
            {"name": "Lógica e argumentação", "leaves": ["identificar premissas e conclusões", "detectar falácias em argumentos"]},
        ],
    },
    {
        "hub": 2,
        "label": "Raciocínio Espacial",
        "eyebrow": "eixo 02",
        "branches": [
            {"name": "Leitura de formas", "leaves": ["interpretar figuras geométricas", "reconhecer semelhança entre figuras"]},
            {"name": "Medidas e volumes", "leaves": ["calcular áreas e volumes"]},
            {"name": "Estrutura e função", "leaves": ["associar estrutura biológica à função", "associar organização espacial à função"]},
        ],
    },
    {
        "hub": 3,
        "label": "Mudança & Sistemas",
        "eyebrow": "eixo 03",
        "branches": [
            {"name": "Variação e taxas", "leaves": ["calcular taxas de variação", "associar gráfico a padrão de variação"]},
            {"name": "Conservação e equilíbrio", "leaves": ["verificar conservação em transformações"]},
            {"name": "Interdependência de sistemas", "leaves": ["mapear fluxos entre componentes"]},
        ],
    },
    {
        "hub": 4,
        "label": "Dados & Causas",
        "eyebrow": "eixo 04",
        "branches": [
            {"name": "Estatística básica", "leaves": ["calcular média, mediana e moda", "analisar dispersão de dados"]},
            {"name": "Probabilidade", "leaves": ["calcular probabilidade condicional"]},
            {"name": "Causa e efeito", "leaves": ["distinguir causa de correlação", "explicar cadeias causais complexas"]},
        ],
    },
    {
        "hub": 5,
        "label": "Linguagem & Símbolos",
        "eyebrow": "eixo 05",
        "branches": [
            {"name": "Leitura e interpretação", "leaves": ["localizar informação explícita", "inferir informação implícita"]},
            {"name": "Integração de informações", "leaves": ["combinar múltiplas fontes de dados"]},
            {"name": "Tradução simbólica", "leaves": ["traduzir texto em expressão formal"]},
        ],
    },
    {
        "hub": 6,
        "label": "Investigação & Classificação",
        "eyebrow": "eixo 06",
        "branches": [
            {"name": "Método científico", "leaves": ["formular hipóteses testáveis"]},
            {"name": "Controle de variáveis", "leaves": ["isolar variáveis em experimentos"]},
            {"name": "Classificação de elementos", "leaves": ["classificar por critério compartilhado"]},
        ],
    },
]


MASTERY_CEILING = 0.92  # teto de exibição: nunca mostrar >92%, por design do produto.
_MASTERY_CURVE_K = 3.0  # controla o quão rápido o ganho marginal cai perto do teto.


def _diminishing_mastery(raw: float) -> float:
    """Converte progresso bruto (0..1, resposta/total) num valor de exibição
    com retornos decrescentes: sobe rápido no início e fica cada vez mais
    difícil subir perto do teto — nunca alcança `MASTERY_CEILING`, só se
    aproxima assintoticamente dele. É deliberadamente mais difícil "chegar
    perto de 100%" do que sair de 0% — reflete que dominar totalmente uma
    frente ampla é raro por design, não um limite técnico.
    """
    raw = max(0.0, min(1.0, raw))
    return round(MASTERY_CEILING * (1 - math.exp(-_MASTERY_CURVE_K * raw)), 4)


def compute_hexagon(ontology_tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deriva mastery 0..1 por vértice cosmético a partir da árvore real da
    ontologia (só contagem de processos respondidos/total por domínio), já
    passado pela curva de retornos decrescentes (`_diminishing_mastery`).

    Não devolve nenhum nome real — só `hub` (1-6), `label` (genérico) e
    `mastery`. É a única ponte entre o dado real e este mapa decorativo.
    """
    dom_counts: dict[str, dict[str, int]] = {}
    for dnode in ontology_tree:
        total = 0
        answered = 0
        for cnode in dnode.get("children", []) or []:
            for pnode in cnode.get("children", []) or []:
                total += 1
                if pnode.get("answered"):
                    answered += 1
        dom_counts[dnode.get("code")] = {"total": total, "answered": answered}

    hexagon = []
    for hub in HUBS:
        dom_ids = HUB_DOMAIN_MAP.get(hub["hub"], [])
        total = sum(dom_counts.get(d, {}).get("total", 0) for d in dom_ids)
        answered = sum(dom_counts.get(d, {}).get("answered", 0) for d in dom_ids)
        raw = answered / total if total else 0.0
        mastery = _diminishing_mastery(raw) if total else 0.0
        hexagon.append({"hub": hub["hub"], "label": hub["label"], "mastery": mastery})
    return hexagon


def _stable_unit(*parts: str) -> float:
    """Pseudo-aleatório determinístico em [0, 1) a partir de `parts` — mesma
    entrada sempre produz o mesmo número, sem precisar guardar estado. Só para
    dar variação visual "orgânica" aos itens do mapa, nunca para decisão real.
    """
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def build_hub_tree(uid: str, hexagon: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enriquece `HUBS` (estático) com um percentual por hub e por item
    (`leaf`), estável por aluno — mesmo hub/mesma folha sempre rendem o mesmo
    número para o mesmo `uid`, então a árvore não "pisca" a cada re-render.

    O percentual do hub vem do mastery real (`hexagon`, já derivado de
    processos respondidos); o percentual de cada folha é uma variação
    decorativa em torno desse número — não existe granularidade real por
    folha (elas são só rótulos ilustrativos), então isso NUNCA deve ser lido
    como uma medida por si.
    """
    mastery_by_hub = {h["hub"]: h["mastery"] for h in hexagon}
    tree: list[dict[str, Any]] = []
    for hub in HUBS:
        hub_pct = round(mastery_by_hub.get(hub["hub"], 0.0) * 100, 1)
        branches = []
        for branch in hub["branches"]:
            leaves = []
            for leaf in branch["leaves"]:
                jitter = _stable_unit(uid, str(hub["hub"]), branch["name"], leaf)
                base = hub_pct if hub_pct > 0 else jitter * 30
                pct = base * (0.55 + jitter * 0.9)
                pct = max(4.0, min(MASTERY_CEILING * 100, round(pct, 1)))
                leaves.append({"name": leaf, "percent": pct})
            branches.append({"name": branch["name"], "leaves": leaves})
        tree.append({
            "hub": hub["hub"],
            "label": hub["label"],
            "eyebrow": hub["eyebrow"],
            "mastery": hub_pct,
            "branches": branches,
        })
    return tree


_FEEDBACK_MIN_RESPOSTAS = 3  # amostra mínima por domínio p/ entrar no resumo de acerto


def compute_feedback(rounds_history: list[dict[str, Any]], domain_stats: dict[str, dict[str, int]]) -> dict[str, Any]:
    """Resumo gamificado de "onde você mais acerta" / "no que focar", montado
    a partir do HISTÓRICO de resumos de rodada já gravado (`rounds_history`,
    de `students/{uid}/sparks_rounds`) e da contagem bruta de acertos por
    domínio (`domain_stats`, de `annotation_service`). Nunca expõe nome real
    de domínio/processo/competência — só o rótulo cosmético do hub.

    Determinístico, sem IA: soma frequência de padrão de erro por domínio
    (já filtrada por `_PADRAO_FREQUENCIA_MINIMA` em `resumo_rodada`) e taxa de
    acerto por domínio, cada uma agregada para o hub cosmético via
    `HUB_DOMAIN_MAP`.
    """
    error_freq_by_dom: dict[str, int] = {}
    for rodada in rounds_history:
        for p in rodada.get("padroes_de_erro") or []:
            if p.get("tipo") != "dominio" or not p.get("id"):
                continue
            error_freq_by_dom[p["id"]] = error_freq_by_dom.get(p["id"], 0) + int(p.get("frequencia") or 0)

    hub_difficulty: dict[int, int] = {}
    hub_respondidas: dict[int, int] = {}
    hub_acertos: dict[int, int] = {}
    for hub in HUBS:
        dom_ids = HUB_DOMAIN_MAP.get(hub["hub"], [])
        hub_difficulty[hub["hub"]] = sum(error_freq_by_dom.get(d, 0) for d in dom_ids)
        hub_respondidas[hub["hub"]] = sum(domain_stats.get(d, {}).get("respondidas", 0) for d in dom_ids)
        hub_acertos[hub["hub"]] = sum(domain_stats.get(d, {}).get("acertos", 0) for d in dom_ids)

    label_by_hub = {h["hub"]: h["label"] for h in HUBS}

    pontos_fortes = []
    for hub_id, respondidas in hub_respondidas.items():
        if respondidas < _FEEDBACK_MIN_RESPOSTAS:
            continue
        accuracy = round(100 * hub_acertos[hub_id] / respondidas, 1)
        pontos_fortes.append({"hub": hub_id, "label": label_by_hub[hub_id], "accuracy": accuracy, "respondidas": respondidas})
    pontos_fortes.sort(key=lambda x: -x["accuracy"])

    pontos_fracos = []
    for hub_id, freq in hub_difficulty.items():
        if freq <= 0:
            continue
        pontos_fracos.append({"hub": hub_id, "label": label_by_hub[hub_id], "ocorrencias": freq})
    pontos_fracos.sort(key=lambda x: -x["ocorrencias"])

    if not rounds_history:
        headline = "Responda suas primeiras 10 questões para desbloquear seu resumo de desempenho."
    elif pontos_fortes and pontos_fracos:
        headline = f"Você está mandando bem em {pontos_fortes[0]['label']} — o próximo desafio é {pontos_fracos[0]['label']}."
    elif pontos_fortes:
        headline = f"Você está mandando bem em {pontos_fortes[0]['label']}. Continue respondendo para desbloquear mais frentes."
    elif pontos_fracos:
        headline = f"Seu maior desafio agora é {pontos_fracos[0]['label']}."
    else:
        headline = "Continue respondendo questões para desbloquear seu resumo de desempenho."

    return {
        "headline": headline,
        "rounds_analisadas": len(rounds_history),
        "pontos_fortes": pontos_fortes[:3],
        "pontos_fracos": pontos_fracos[:3],
        "narrativa": compute_narrative(rounds_history),
    }


def _hub_label_for_domain(dom_id: str) -> str | None:
    for hub_id, dom_ids in HUB_DOMAIN_MAP.items():
        if dom_id in dom_ids:
            for hub in HUBS:
                if hub["hub"] == hub_id:
                    return hub["label"]
    return None


def _bloco_desc(rodada: dict[str, Any]) -> str:
    b = rodada.get("bloco") or {}
    partes = [str(b.get("banca") or ""), str(b.get("ano") or "")]
    desc = " ".join(p for p in partes if p)
    return desc or "uma prova"


def compute_narrative(rounds_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resumo interativo, determinístico (SEM chamada a Gemini/LLM), montado
    só a partir do histórico de resumos de rodada já gravado. Cada entrada
    tem um `type` (pro front escolher ícone/cor) e um `text` pronto — nunca
    nome real de domínio/processo/competência, só rótulo cosmético de hub.
    """
    if not rounds_history:
        return [{
            "type": "vazio",
            "text": "Você ainda não tem rodadas de 10 questões no histórico. Responda algumas questões para desbloquear seu resumo interativo!",
        }]

    rounds_asc = list(reversed(rounds_history))  # mais antiga primeiro
    total_rounds = len(rounds_asc)
    total_questoes = sum(r.get("total", 0) for r in rounds_asc)
    total_acertos = sum(r.get("acertos", 0) for r in rounds_asc)
    total_sparks = sum(r.get("sparks_ganhos", 0) for r in rounds_asc)
    media_geral = round(100 * total_acertos / total_questoes, 1) if total_questoes else 0.0

    insights: list[dict[str, Any]] = []
    insights.append({"type": "resumo", "text": f"Você já completou {total_rounds} rodada(s) de questões, somando {total_questoes} questões respondidas."})
    insights.append({"type": "acerto", "text": f"Sua taxa de acerto geral, somando todas as rodadas, é de {media_geral}%."})
    insights.append({"type": "sparks", "text": f"Você já ganhou {total_sparks} Sparks só nessas rodadas."})

    melhor = max(rounds_asc, key=lambda r: r.get("percentual_acerto", 0))
    pior = min(rounds_asc, key=lambda r: r.get("percentual_acerto", 100))
    insights.append({
        "type": "melhor",
        "text": f"Sua melhor rodada foi a rodada {melhor.get('rodada')} de {_bloco_desc(melhor)}, com {melhor.get('percentual_acerto')}% de acerto.",
    })
    if pior is not melhor:
        insights.append({
            "type": "pior",
            "text": f"Sua rodada mais desafiadora foi a rodada {pior.get('rodada')} de {_bloco_desc(pior)}, com {pior.get('percentual_acerto')}% de acerto — ótima candidata pra revisar.",
        })

    if total_rounds >= 2:
        meio = max(total_rounds // 2, 1)
        primeira, segunda = rounds_asc[:meio], rounds_asc[meio:]

        def _media(rs: list[dict[str, Any]]) -> float:
            t = sum(r.get("total", 0) for r in rs)
            a = sum(r.get("acertos", 0) for r in rs)
            return round(100 * a / t, 1) if t else 0.0

        delta = round(_media(segunda) - _media(primeira), 1)
        if delta > 2:
            insights.append({"type": "evolucao_up", "text": f"Você está evoluindo: sua taxa de acerto subiu {delta} pontos percentuais entre o início e o momento mais recente do seu histórico."})
        elif delta < -2:
            insights.append({"type": "evolucao_down", "text": f"Sua taxa de acerto caiu {abs(delta)} pontos percentuais nas rodadas mais recentes — bom momento pra revisar o que já foi respondido."})
        else:
            insights.append({"type": "evolucao_estavel", "text": "Sua taxa de acerto está estável ao longo do histórico — consistência é um ótimo sinal!"})

    streak = melhor_streak = 0
    for r in rounds_asc:
        if (r.get("percentual_acerto") or 0) >= 70:
            streak += 1
            melhor_streak = max(melhor_streak, streak)
        else:
            streak = 0
    if melhor_streak >= 2:
        insights.append({"type": "streak", "text": f"Você já emplacou uma sequência de {melhor_streak} rodadas seguidas com 70% de acerto ou mais."})

    rodadas_por_hub: dict[str, set[int]] = {}
    for i, r in enumerate(rounds_asc):
        vistos_nesta_rodada = set()
        for p in r.get("padroes_de_erro") or []:
            if p.get("tipo") != "dominio" or not p.get("id"):
                continue
            label = _hub_label_for_domain(p["id"])
            if label:
                vistos_nesta_rodada.add(label)
        for label in vistos_nesta_rodada:
            rodadas_por_hub.setdefault(label, set()).add(i)

    recorrentes = sorted(((label, len(idxs)) for label, idxs in rodadas_por_hub.items()), key=lambda x: -x[1])
    for label, n_rodadas in recorrentes[:3]:
        if n_rodadas >= 2:
            insights.append({"type": "recorrente", "text": f"\"{label}\" apareceu como ponto de atenção em {n_rodadas} rodadas diferentes — vale um foco extra por aqui."})

    for i, r in enumerate(rounds_asc, start=1):
        data = (r.get("created_at") or "")[:10]
        padroes_hub = sorted({
            _hub_label_for_domain(p["id"])
            for p in (r.get("padroes_de_erro") or [])
            if p.get("tipo") == "dominio" and p.get("id") and _hub_label_for_domain(p["id"])
        })
        insights.append({
            "type": "rodada",
            "text": f"Rodada {i}: {r.get('acertos', 0)}/{r.get('total', 0)} acertos ({r.get('percentual_acerto', 0)}%) em {_bloco_desc(r)}" + (f" — {data}" if data else "") + ".",
            "rodada": r.get("rodada"),
            "sparks_ganhos": r.get("sparks_ganhos", 0),
            "padroes": padroes_hub,
        })

    return insights
