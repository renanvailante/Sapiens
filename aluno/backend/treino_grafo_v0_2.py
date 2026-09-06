"""Grafo pedagógico de exploração da aba Treino — `training_graph_v0_2`.

Camada de PRODUTO, derivada da ontologia oficial
(`pipeline/docs/ontology/ontology_v1.4.json`) mas separada e versionada à
parte dela: agrupa as 56 habilidades observáveis em 6 "biomas" de
exploração e define ~90 relações pedagógicas entre elas (pré-requisito,
continuidade, transferência, contraste...).

Nem os biomas nem as relações são ontologia: não redefinem `hab_id`, nome ou
processo algum, só decoram o que já existe com uma camada de navegação e
narrativa. Podem mudar (rebalancear bioma, adicionar aresta) num deploy
qualquer sem nenhuma migração de dado do aluno — o estado persistido
(`treino_agregado`, ver `firestore_service.py`) é só `{hab_id: {respondidas,
acertos}}`, que continua fazendo sentido em qualquer versão do grafo.

O aluno nunca recebe `HAB-*`, `DOM-*`, `PROC-*`, `COMP-*` nem qualquer nome
interno da ontologia — só o nome da própria habilidade (já é uma frase em
português, não um código) e o nome do bioma. `treino_routes.py` é quem monta
a resposta HTTP; este módulo só descreve o grafo e calcula posições.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

RELACOES_PERMITIDAS = {
    "prerequisito", "continuidade", "transferencia", "integracao",
    "contraste", "aplicacao", "contextualizacao", "especializacao",
    "representacao", "reversibilidade",
}

# ---------------------------------------------------------------------------
# 6 biomas — camada de experiência, EXATAMENTE estes seis, não a ontologia.
# ---------------------------------------------------------------------------

BIOMAS = [
    {
        "bioma_id": "perceber",
        "nome": "Perceber",
        "ideia": "Observar antes de interpretar.",
        "resumo": (
            "É o que você usa toda vez que compara dois preços de cabeça, lê um gráfico "
            "rápido numa notícia ou percebe um padrão numa tabela antes de qualquer cálculo "
            "— a primeira leitura, antes de interpretar."
        ),
        "habilidades": [
            "HAB-01", "HAB-02", "HAB-06", "HAB-07", "HAB-08", "HAB-09", "HAB-10", "HAB-11",
            "HAB-25", "HAB-26", "HAB-27", "HAB-28", "HAB-29", "HAB-42", "HAB-43", "HAB-44",
        ],
    },
    {
        "bioma_id": "relacionar",
        "nome": "Relacionar",
        "ideia": "Entender como uma coisa muda quando outra muda.",
        "resumo": (
            "Está presente sempre que uma coisa muda em função de outra: juros, inflação, a "
            "chance real de um evento, uma pesquisa com margem de erro — entender a relação "
            "entre as partes antes de tirar conclusão."
        ),
        "habilidades": [
            "HAB-03", "HAB-04", "HAB-05", "HAB-17", "HAB-18", "HAB-20", "HAB-21", "HAB-22",
            "HAB-23", "HAB-24", "HAB-30", "HAB-31", "HAB-32", "HAB-33", "HAB-34", "HAB-35",
        ],
    },
    {
        "bioma_id": "representar",
        "nome": "Representar",
        "ideia": "Transformar uma ideia em uma estrutura que pode ser manipulada.",
        "resumo": (
            "Aparece quando você traduz uma ideia para uma forma manipulável — uma planta "
            "baixa, uma fórmula, um símbolo técnico — e consegue ir e voltar entre a "
            "representação e o que ela significa."
        ),
        "habilidades": ["HAB-12", "HAB-13", "HAB-14", "HAB-15", "HAB-16", "HAB-19", "HAB-38", "HAB-39", "HAB-40", "HAB-41", "HAB-45", "HAB-46"],
    },
    {
        "bioma_id": "investigar",
        "nome": "Investigar",
        "ideia": "Não basta ter uma explicação. É preciso testá-la.",
        "resumo": (
            "É o raciocínio por trás de perguntar 'como eu saberia se isso é verdade': o que "
            "foi de fato testado, o que foi só observado, e o que a conclusão pode ou não "
            "sustentar."
        ),
        "habilidades": ["HAB-49", "HAB-50", "HAB-51"],
    },
    {
        "bioma_id": "integrar",
        "nome": "Integrar",
        "ideia": "Entender o sistema inteiro.",
        "resumo": (
            "Entra em cena quando uma parte de um sistema afeta as outras — uma cadeia "
            "produtiva, um ecossistema, uma rede de causas — e a resposta certa depende de "
            "enxergar o todo, não só a peça em foco."
        ),
        "habilidades": ["HAB-47", "HAB-48", "HAB-52", "HAB-53", "HAB-54"],
    },
    {
        "bioma_id": "decidir",
        "nome": "Decidir",
        "ideia": "Usar o que foi compreendido para julgar, classificar e escolher.",
        "resumo": (
            "É o passo final: usar tudo o que foi compreendido para julgar um argumento, "
            "escolher o critério certo de classificação ou decidir entre alternativas."
        ),
        "habilidades": ["HAB-36", "HAB-37", "HAB-55", "HAB-56"],
    },
]

BIOMA_POR_HAB: dict[str, str] = {h: b["bioma_id"] for b in BIOMAS for h in b["habilidades"]}
BIOMA_POR_ID: dict[str, dict] = {b["bioma_id"]: b for b in BIOMAS}

# ---------------------------------------------------------------------------
# ~90 arestas do grafo pedagógico v0.2 — deduplicadas (pares equivalentes e
# duplicatas exatas do material original já removidos). `direction` é sempre
# "bidirecional": nenhuma aresta do material de origem tinha seta única.
# ---------------------------------------------------------------------------

_RATIONALE_POR_RELACAO = {
    "prerequisito": "Uma habilidade só se sustenta se a outra já estiver formada.",
    "continuidade": "Uma é o passo seguinte natural da outra, no mesmo raciocínio.",
    "transferencia": "O mesmo raciocínio reaparece aplicado a um material diferente.",
    "integracao": "Nenhuma das duas sozinha resolve — a resposta exige juntar as duas.",
    "contraste": "Aparecem juntas porque a diferença entre elas é o que precisa ser notado.",
    "aplicacao": "Uma é onde a outra aparece aplicada a um contexto concreto.",
    "contextualizacao": "Uma dá o cenário onde a outra faz sentido.",
    "especializacao": "Uma é um caso mais específico da outra.",
    "representacao": "Uma é a forma representada da ideia que a outra descreve.",
    "reversibilidade": "O caminho entre as duas pode ser percorrido nos dois sentidos.",
}

_ARESTAS_BRUTAS: list[tuple[str, str, str]] = [
    ("HAB-01", "HAB-02", "continuidade"), ("HAB-01", "HAB-06", "aplicacao"),
    ("HAB-02", "HAB-03", "prerequisito"), ("HAB-02", "HAB-04", "prerequisito"),
    ("HAB-03", "HAB-04", "contraste"), ("HAB-03", "HAB-05", "continuidade"),
    ("HAB-04", "HAB-05", "continuidade"), ("HAB-06", "HAB-07", "continuidade"),
    ("HAB-06", "HAB-11", "transferencia"), ("HAB-07", "HAB-08", "aplicacao"),
    ("HAB-07", "HAB-09", "aplicacao"), ("HAB-08", "HAB-09", "continuidade"),
    ("HAB-10", "HAB-11", "continuidade"), ("HAB-10", "HAB-12", "prerequisito"),
    ("HAB-10", "HAB-13", "prerequisito"), ("HAB-11", "HAB-12", "aplicacao"),
    ("HAB-11", "HAB-13", "aplicacao"), ("HAB-14", "HAB-15", "continuidade"),
    ("HAB-14", "HAB-16", "continuidade"), ("HAB-15", "HAB-16", "integracao"),
    ("HAB-14", "HAB-53", "aplicacao"), ("HAB-16", "HAB-53", "aplicacao"),
    ("HAB-17", "HAB-18", "continuidade"), ("HAB-17", "HAB-19", "representacao"),
    ("HAB-18", "HAB-19", "representacao"), ("HAB-17", "HAB-20", "transferencia"),
    ("HAB-18", "HAB-20", "aplicacao"), ("HAB-20", "HAB-21", "continuidade"),
    ("HAB-21", "HAB-22", "continuidade"), ("HAB-20", "HAB-52", "transferencia"),
    ("HAB-21", "HAB-52", "transferencia"), ("HAB-22", "HAB-52", "transferencia"),
    ("HAB-23", "HAB-24", "continuidade"), ("HAB-23", "HAB-25", "aplicacao"),
    ("HAB-23", "HAB-30", "transferencia"), ("HAB-24", "HAB-30", "continuidade"),
    ("HAB-30", "HAB-31", "continuidade"), ("HAB-25", "HAB-26", "contraste"),
    ("HAB-25", "HAB-27", "contraste"), ("HAB-26", "HAB-27", "contraste"),
    ("HAB-28", "HAB-29", "continuidade"), ("HAB-28", "HAB-07", "aplicacao"),
    ("HAB-29", "HAB-07", "aplicacao"), ("HAB-32", "HAB-33", "contraste"),
    ("HAB-32", "HAB-34", "aplicacao"), ("HAB-32", "HAB-35", "aplicacao"),
    ("HAB-33", "HAB-07", "aplicacao"), ("HAB-34", "HAB-18", "transferencia"),
    ("HAB-35", "HAB-14", "aplicacao"), ("HAB-35", "HAB-16", "aplicacao"),
    ("HAB-32", "HAB-52", "transferencia"), ("HAB-36", "HAB-37", "continuidade"),
    ("HAB-36", "HAB-32", "aplicacao"), ("HAB-37", "HAB-33", "aplicacao"),
    ("HAB-36", "HAB-45", "aplicacao"), ("HAB-37", "HAB-45", "aplicacao"),
    ("HAB-38", "HAB-39", "continuidade"), ("HAB-38", "HAB-40", "transferencia"),
    ("HAB-39", "HAB-19", "representacao"), ("HAB-40", "HAB-41", "continuidade"),
    ("HAB-41", "HAB-09", "aplicacao"), ("HAB-38", "HAB-45", "transferencia"),
    ("HAB-42", "HAB-43", "continuidade"), ("HAB-42", "HAB-44", "continuidade"),
    ("HAB-43", "HAB-48", "integracao"), ("HAB-44", "HAB-46", "continuidade"),
    ("HAB-45", "HAB-46", "continuidade"), ("HAB-45", "HAB-47", "integracao"),
    ("HAB-46", "HAB-47", "integracao"), ("HAB-47", "HAB-48", "integracao"),
    ("HAB-49", "HAB-50", "prerequisito"), ("HAB-50", "HAB-51", "continuidade"),
    ("HAB-49", "HAB-32", "transferencia"), ("HAB-49", "HAB-33", "aplicacao"),
    ("HAB-50", "HAB-18", "aplicacao"), ("HAB-51", "HAB-20", "aplicacao"),
    ("HAB-52", "HAB-53", "continuidade"), ("HAB-53", "HAB-54", "continuidade"),
    ("HAB-54", "HAB-35", "aplicacao"), ("HAB-55", "HAB-56", "especializacao"),
    ("HAB-55", "HAB-07", "aplicacao"), ("HAB-56", "HAB-35", "aplicacao"),
    ("HAB-55", "HAB-14", "aplicacao"), ("HAB-23", "HAB-43", "transferencia"),
    ("HAB-25", "HAB-42", "aplicacao"), ("HAB-29", "HAB-46", "aplicacao"),
    ("HAB-36", "HAB-38", "transferencia"), ("HAB-38", "HAB-47", "integracao"),
    ("HAB-47", "HAB-53", "integracao"), ("HAB-52", "HAB-18", "transferencia"),
]


def _validar_e_montar_arestas() -> list[dict[str, Any]]:
    vistas: dict[frozenset, dict] = {}
    for source, target, relation in _ARESTAS_BRUTAS:
        if relation not in RELACOES_PERMITIDAS:
            raise ValueError(f"Relação não permitida no grafo v0.2: {relation!r}")
        chave = frozenset((source, target))
        if chave in vistas:
            continue  # pares equivalentes/duplicatas já saem deduplicados aqui
        vistas[chave] = {
            "source": source,
            "target": target,
            "relation": relation,
            "weight": 1,
            "direction": "bidirecional",
            "rationale": _RATIONALE_POR_RELACAO[relation],
        }
    return list(vistas.values())


ARESTAS: list[dict[str, Any]] = _validar_e_montar_arestas()

_ADJACENCIA: dict[str, set[str]] = {}
for _a in ARESTAS:
    _ADJACENCIA.setdefault(_a["source"], set()).add(_a["target"])
    _ADJACENCIA.setdefault(_a["target"], set()).add(_a["source"])


def vizinhos(hab_id: str) -> set[str]:
    return _ADJACENCIA.get(hab_id, set())


# ---------------------------------------------------------------------------
# Layout espacial — um grafo de fato (spring layout determinístico), não uma
# roda de raios por bioma: âncoras fracas por bioma mantêm cada um coeso,
# mas as arestas entre biomas puxam os nós-ponte para fora do próprio
# aglomerado, criando as interseções e atalhos exigidos pelo produto.
# ---------------------------------------------------------------------------

_ANCORA_BIOMA: dict[str, tuple[float, float]] = {
    "perceber": (170, 480),
    "relacionar": (430, 560),
    "representar": (700, 470),
    "investigar": (880, 300),
    "integrar": (700, 130),
    "decidir": (380, 110),
}

_CANVAS_W, _CANVAS_H = 1000, 640
_MARGEM = 60


def _seed(hab_id: str) -> int:
    return int(hashlib.sha1(hab_id.encode()).hexdigest()[:8], 16)


def _posicoes_iniciais() -> dict[str, list[float]]:
    pos: dict[str, list[float]] = {}
    for bioma in BIOMAS:
        cx, cy = _ANCORA_BIOMA[bioma["bioma_id"]]
        habs = bioma["habilidades"]
        n = max(len(habs), 1)
        for i, hab_id in enumerate(habs):
            seed = _seed(hab_id)
            angulo = (2 * math.pi * i) / n + (seed % 1000) / 1000 * 0.6
            raio = 34 + (seed // 1000 % 100) / 100 * 32
            pos[hab_id] = [cx + raio * math.cos(angulo), cy + raio * math.sin(angulo) * 0.72]
    return pos


def _relaxar(pos: dict[str, list[float]], iteracoes: int = 200) -> None:
    ids = list(pos.keys())
    for _ in range(iteracoes):
        disp = {k: [0.0, 0.0] for k in ids}
        for i in range(len(ids)):
            a = ids[i]
            for j in range(i + 1, len(ids)):
                b = ids[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                dist2 = max(dx * dx + dy * dy, 4.0)
                forca = 1400 / dist2
                dist = math.sqrt(dist2)
                fx, fy = dx / dist * forca, dy / dist * forca
                disp[a][0] += fx; disp[a][1] += fy
                disp[b][0] -= fx; disp[b][1] -= fy
        for aresta in ARESTAS:
            s, t = aresta["source"], aresta["target"]
            if s not in pos or t not in pos:
                continue
            dx, dy = pos[s][0] - pos[t][0], pos[s][1] - pos[t][1]
            dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
            forca = (dist - 65) * 0.018
            fx, fy = dx / dist * forca, dy / dist * forca
            disp[s][0] -= fx; disp[s][1] -= fy
            disp[t][0] += fx; disp[t][1] += fy
        for hab_id in ids:
            cx, cy = _ANCORA_BIOMA[BIOMA_POR_HAB[hab_id]]
            disp[hab_id][0] += (cx - pos[hab_id][0]) * 0.005
            disp[hab_id][1] += (cy - pos[hab_id][1]) * 0.005
        for k in ids:
            pos[k][0] += max(-9.0, min(9.0, disp[k][0]))
            pos[k][1] += max(-9.0, min(9.0, disp[k][1]))
            pos[k][0] = max(_MARGEM, min(_CANVAS_W - _MARGEM, pos[k][0]))
            pos[k][1] = max(_MARGEM, min(_CANVAS_H - _MARGEM, pos[k][1]))


_LAYOUT: dict[str, list[float]] | None = None


def layout() -> dict[str, list[float]]:
    """Posições x/y (canvas virtual 1000x640) — determinístico e em cache de
    processo: a mesma entrada (biomas + arestas) sempre produz a mesma
    saída, então todo aluno vê o mesmo mapa."""
    global _LAYOUT
    if _LAYOUT is None:
        pos = _posicoes_iniciais()
        _relaxar(pos)
        _LAYOUT = {k: [round(v[0], 1), round(v[1], 1)] for k, v in pos.items()}
    return _LAYOUT
