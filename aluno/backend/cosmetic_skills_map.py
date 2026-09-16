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

# Índice inverso do mapa acima. Existe para que a contagem por eixo possa ser
# feita evento a evento (em `annotation_service`), onde é preciso saber a que
# eixo um domínio pertence ANTES de somar — só assim uma questão conta uma
# vez por eixo, e não uma vez por domínio.
DOMAIN_TO_HUB: dict[str, int] = {
    dom_id: hub_id for hub_id, dom_ids in HUB_DOMAIN_MAP.items() for dom_id in dom_ids
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


# ----------------------------------------------------------------------
# Escala do mapa (recalibrada em 2026-09-15)
#
# Antes, o número de um vértice era COBERTURA: processos tocados / processos
# do domínio. Um domínio com três processos ficava "coberto" na primeira
# rodada, e o mapa anunciava "Dominado" para quem tinha respondido três
# questões — a barra subia por o assunto ter APARECIDO, não por ter sido
# acertado. É o pior tipo de número num produto de estudo: parabeniza cedo e
# some com a razão de voltar.
#
# Agora o número é VOLUME DE ACERTOS no eixo, com retornos decrescentes, e a
# âncora é explícita (e travada em teste):
#
#     ACERTOS_ANCORA acertos naquele eixo  ->  MASTERY_ANCORA de exibição.
#
# Ou seja: "Dominado" (80%, ver `frontend/src/lib/dominio.js`) exige 40
# acertos naquele eixo. Errar não desconta — só não soma: a régua é "quanto
# você já acertou aqui", não "qual é a sua taxa de acerto".
# ----------------------------------------------------------------------

MASTERY_CEILING = 0.92  # teto de exibição: nunca mostrar >92%, por design do produto.
ACERTOS_ANCORA = 40     # acertos necessários num eixo para...
MASTERY_ANCORA = 0.80   # ...este valor de exibição ("Dominado").

# Constante de tempo da curva — DERIVADA da âncora, não escolhida a olho:
# é a solução de MASTERY_CEILING * (1 - e^(-n/TAU)) = MASTERY_ANCORA em
# n = ACERTOS_ANCORA. Mexer na âncora reescala tudo sozinho.
_TAU_ACERTOS = -ACERTOS_ANCORA / math.log(1 - MASTERY_ANCORA / MASTERY_CEILING)


def mastery_por_acertos(acertos: float) -> float:
    """Mastery de exibição (0..1) a partir do número de acertos no eixo.

    Retornos decrescentes: passa exatamente pela âncora e se aproxima de
    `MASTERY_CEILING` sem nunca passar dele (só o encosta, por arredondamento,
    lá pelas duas centenas de acertos). Ordens de grandeza, para conferir a
    sensação: 5 acertos ~21%, 10 ~37%, 20 ~59%, 40 = 80%, 60 ~88%, 80 ~90%.
    """
    n = max(0.0, float(acertos or 0))
    return round(MASTERY_CEILING * (1 - math.exp(-n / _TAU_ACERTOS)), 4)


def compute_hexagon(hub_stats: dict[Any, dict[str, int]] | None) -> list[dict[str, Any]]:
    """Deriva o vértice cosmético de cada eixo a partir da contagem por hub já
    agregada em `annotation_service._read_firestore_answered`, onde cada
    questão respondida conta UMA vez por hub — um item que aciona dois
    domínios do mesmo hub (hub 5 tem três) não vale dobrado, senão "40
    acertos" chegaria com 14 questões.

    Devolve `acertos`/`respondidas` junto do `mastery` de propósito: é isso
    que fica gravado no snapshot e o que permite reexibir o mapa numa escala
    nova sem reler nada do Firestore (ver `rescale_hexagon`).
    """
    stats = hub_stats or {}
    hexagon = []
    for hub in HUBS:
        entry = stats.get(hub["hub"]) or stats.get(str(hub["hub"])) or {}
        acertos = int(entry.get("acertos") or 0)
        hexagon.append({
            "hub": hub["hub"],
            "label": hub["label"],
            "mastery": mastery_por_acertos(acertos),
            "acertos": acertos,
            "respondidas": int(entry.get("respondidas") or 0),
        })
    return hexagon


def rescale_hexagon(hexagon: list[dict[str, Any]] | None) -> tuple[list[dict[str, Any]], bool]:
    """Recalcula `mastery` a partir dos `acertos` gravados no snapshot.

    O mapa é servido do snapshot em toda abertura do Painel; reler o
    histórico de respostas por requisição é exatamente a forma do incidente de
    cota do Firestore. Guardar a contagem ao lado do número é o que permite
    trocar a escala e o efeito valer para todo mundo sem pagar leitura nenhuma.

    Snapshot da escala antiga (cobertura, sem `acertos`) não tem conversão
    possível: aquele número não guardava quantas questões havia por trás.
    Esses voltam zerados e com `escala_antiga`: "ainda não medido" fica falso
    até a próxima geração, enquanto "Dominado" ficaria falso e convincente.
    """
    if not hexagon:
        return [], False
    rescaled: list[dict[str, Any]] = []
    escala_antiga = False
    for item in hexagon:
        if "acertos" in item:
            rescaled.append({**item, "mastery": mastery_por_acertos(item.get("acertos"))})
        else:
            escala_antiga = True
            rescaled.append({**item, "mastery": 0.0, "acertos": 0, "respondidas": 0})
    return rescaled, escala_antiga


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

    O percentual do hub vem do mastery real (`hexagon`, derivado dos acertos);
    o percentual de cada folha é uma variação decorativa DENTRO desse número —
    não existe granularidade real por folha (elas são só rótulos
    ilustrativos), então isso NUNCA deve ser lido como uma medida por si.

    Duas regras impedem a decoração de mentir: folha nenhuma passa do
    percentual do próprio hub, e hub sem acerto nenhum tem folha zerada. Antes
    havia um piso de 4% e uma base fictícia de até 30% para hub zerado — um
    eixo "Não explorado" exibia folhas perto de 40%, que é justamente o número
    inflado que esta escala veio remover.
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
                pct = round(hub_pct * (0.6 + jitter * 0.4), 1) if hub_pct > 0 else 0.0
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


_FEEDBACK_MIN_RESPOSTAS = 10  # amostra mínima por eixo p/ entrar no resumo de acerto


def compute_feedback(rounds_history: list[dict[str, Any]], hub_stats: dict[Any, dict[str, int]] | None) -> dict[str, Any]:
    """Resumo gamificado de "onde você mais acerta" / "no que focar", montado
    a partir do HISTÓRICO de resumos de rodada já gravado (`rounds_history`,
    de `students/{uid}/sparks_rounds`) e da contagem por eixo (`hub_stats`, de
    `annotation_service`). Nunca expõe nome real de domínio/processo/
    competência — só o rótulo cosmético do hub.

    Determinístico, sem IA: soma frequência de padrão de erro por domínio (já
    filtrada por `_PADRAO_FREQUENCIA_MINIMA` em `resumo_rodada`), agregada
    para o hub via `HUB_DOMAIN_MAP`, e taxa de acerto por eixo lida direto de
    `hub_stats` — que já conta cada questão UMA vez por eixo. Somar os
    domínios aqui contava em dobro o item que aciona dois domínios do mesmo
    eixo, e a "taxa de acerto" saía de uma base inflada.
    """
    error_freq_by_dom: dict[str, int] = {}
    for rodada in rounds_history:
        for p in rodada.get("padroes_de_erro") or []:
            if p.get("tipo") != "dominio" or not p.get("id"):
                continue
            error_freq_by_dom[p["id"]] = error_freq_by_dom.get(p["id"], 0) + int(p.get("frequencia") or 0)

    stats = hub_stats or {}
    hub_difficulty: dict[int, int] = {}
    hub_respondidas: dict[int, int] = {}
    hub_acertos: dict[int, int] = {}
    for hub in HUBS:
        dom_ids = HUB_DOMAIN_MAP.get(hub["hub"], [])
        entry = stats.get(hub["hub"]) or stats.get(str(hub["hub"])) or {}
        hub_difficulty[hub["hub"]] = sum(error_freq_by_dom.get(d, 0) for d in dom_ids)
        hub_respondidas[hub["hub"]] = int(entry.get("respondidas") or 0)
        hub_acertos[hub["hub"]] = int(entry.get("acertos") or 0)

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
