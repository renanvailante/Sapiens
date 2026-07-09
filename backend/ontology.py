"""Sapiens ontology: 5-level cognitive framework with mixed evidence sources.

Levels 1-3 are curated from literature. Level 4 are operational hypotheses.
Level 5 (behavioral indicators) is empirical — it grows and refines with
every student attempt collected by the system.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Level 1 — Cognitive Domains (from literature) ----------

DOMAINS = [
    {
        "code": "Gf",
        "name": "Raciocínio Fluido",
        "description": "Capacidade de raciocinar diante de situações novas, sem depender de conhecimento prévio (Cattell-Horn-Carroll).",
        "literature": ["McGrew (2009)", "Cattell (1963)"],
        "evidence_level": "very_high",
    },
    {
        "code": "Gc",
        "name": "Compreensão Verbal",
        "description": "Conhecimento cristalizado e uso da linguagem para compreensão e inferência textual.",
        "literature": ["McGrew (2009)", "Horn & Cattell (1966)"],
        "evidence_level": "very_high",
    },
    {
        "code": "Gv",
        "name": "Processamento Visuoespacial",
        "description": "Manipulação mental de imagens, gráficos e relações espaciais.",
        "literature": ["McGrew (2009)", "Shepard & Metzler (1971)"],
        "evidence_level": "very_high",
    },
    {
        "code": "Gq",
        "name": "Raciocínio Quantitativo",
        "description": "Manipulação de conceitos numéricos, algébricos e estatísticos.",
        "literature": ["Geary (2004)", "McGrew (2009)"],
        "evidence_level": "very_high",
    },
    {
        "code": "Glr",
        "name": "Recuperação de Memória de Longo Prazo",
        "description": "Acesso a conhecimento factual e conceitual consolidado.",
        "literature": ["Tulving (1972)", "McGrew (2009)"],
        "evidence_level": "very_high",
    },
    {
        "code": "Gwm",
        "name": "Controle Cognitivo & Memória de Trabalho",
        "description": "Regulação atencional, integração de informação e gerenciamento de carga cognitiva.",
        "literature": ["Baddeley (2000)", "Sweller (1988)"],
        "evidence_level": "very_high",
    },
]


# ---------- Level 2 — Competences (theoretical synthesis) ----------

COMPETENCES = [
    # Gf
    {"code": "prop", "domain": "Gf", "name": "Raciocínio proporcional",
     "definition": "Capacidade de reconhecer e operar relações de covariação entre grandezas.",
     "literature": ["Piaget & Inhelder (1975)", "Karplus (1980)"], "evidence_level": "high"},
    {"code": "ded", "domain": "Gf", "name": "Raciocínio dedutivo",
     "definition": "Aplicação de regras gerais a casos particulares preservando validade lógica.",
     "literature": ["Johnson-Laird (1983)"], "evidence_level": "high"},
    {"code": "ind", "domain": "Gf", "name": "Raciocínio indutivo",
     "definition": "Extração de padrões e generalizações a partir de instâncias específicas.",
     "literature": ["Holland et al. (1986)"], "evidence_level": "high"},
    # Gc
    {"code": "lit", "domain": "Gc", "name": "Interpretação literal",
     "definition": "Localização e reconhecimento de informação explícita em texto.",
     "literature": ["Kintsch (1998)"], "evidence_level": "high"},
    {"code": "inf", "domain": "Gc", "name": "Inferência textual",
     "definition": "Construção de significado além do explícito, integrando pistas linguísticas e conhecimento de mundo.",
     "literature": ["Graesser et al. (1994)"], "evidence_level": "high"},
    # Gv
    {"code": "graph", "domain": "Gv", "name": "Leitura de gráficos e diagramas",
     "definition": "Extração de padrões, tendências e valores de representações visuais quantitativas.",
     "literature": ["Shah & Hoeffner (2002)"], "evidence_level": "high"},
    {"code": "spat", "domain": "Gv", "name": "Visualização espacial",
     "definition": "Manipulação mental de objetos 2D/3D e reconhecimento de relações geométricas.",
     "literature": ["Shepard & Metzler (1971)"], "evidence_level": "high"},
    # Gq
    {"code": "alg", "domain": "Gq", "name": "Manipulação algébrica",
     "definition": "Aplicação de operações simbólicas para resolver equações e expressões.",
     "literature": ["Kieran (1992)"], "evidence_level": "high"},
    {"code": "stat", "domain": "Gq", "name": "Raciocínio estatístico-probabilístico",
     "definition": "Interpretação de médias, dispersões e cálculos de probabilidade em contextos aplicados.",
     "literature": ["Garfield & Ben-Zvi (2007)"], "evidence_level": "high"},
    # Glr
    {"code": "fact", "domain": "Glr", "name": "Recuperação factual",
     "definition": "Acesso preciso a informações declarativas consolidadas em memória de longo prazo.",
     "literature": ["Tulving (1972)"], "evidence_level": "high"},
    {"code": "conc", "domain": "Glr", "name": "Conhecimento conceitual estruturado",
     "definition": "Acesso a redes de significado conectando conceitos, princípios e relações causais.",
     "literature": ["Chi et al. (1981)"], "evidence_level": "high"},
    # Gwm
    {"code": "load", "domain": "Gwm", "name": "Gestão de carga cognitiva",
     "definition": "Regulação da demanda mental durante tarefas complexas evitando sobrecarga.",
     "literature": ["Sweller (1988)"], "evidence_level": "high"},
    {"code": "meta", "domain": "Gwm", "name": "Monitoramento metacognitivo",
     "definition": "Autoavaliação em tempo real do próprio processo de resolução.",
     "literature": ["Flavell (1979)"], "evidence_level": "high"},
]


# ---------- Level 3 — Cognitive Processes (operational decomposition) ----------

PROCESSES = [
    # prop
    {"code": "prop.direct", "competence": "prop", "name": "Inferência proporcional direta",
     "definition": "Aplicar uma razão dada para calcular uma grandeza correspondente.", "evidence_level": "medium_high"},
    {"code": "prop.inverse", "competence": "prop", "name": "Inferência proporcional inversa",
     "definition": "Reconhecer que uma grandeza aumenta quando outra diminui na mesma razão.", "evidence_level": "medium_high"},
    # ded
    {"code": "ded.apply", "competence": "ded", "name": "Aplicação de regra a caso",
     "definition": "Deduzir consequência específica a partir de uma regra geral fornecida.", "evidence_level": "medium_high"},
    # ind
    {"code": "ind.pattern", "competence": "ind", "name": "Detecção de padrão",
     "definition": "Identificar regularidade em sequência ou conjunto de casos.", "evidence_level": "medium_high"},
    # lit / inf
    {"code": "lit.locate", "competence": "lit", "name": "Localização de informação explícita",
     "definition": "Encontrar dado literalmente presente no texto.", "evidence_level": "medium_high"},
    {"code": "inf.bridge", "competence": "inf", "name": "Inferência de ponte",
     "definition": "Conectar duas partes do texto para produzir significado não explícito.", "evidence_level": "medium_high"},
    # graph / spat
    {"code": "graph.trend", "competence": "graph", "name": "Leitura de tendência",
     "definition": "Extrair direção e taxa de variação de um gráfico.", "evidence_level": "medium_high"},
    {"code": "graph.value", "competence": "graph", "name": "Leitura pontual",
     "definition": "Extrair valor específico associado a um ponto do gráfico.", "evidence_level": "medium_high"},
    {"code": "spat.rotate", "competence": "spat", "name": "Rotação mental",
     "definition": "Determinar se dois objetos são o mesmo sob rotação.", "evidence_level": "medium_high"},
    # alg / stat
    {"code": "alg.isolate", "competence": "alg", "name": "Isolamento de variável",
     "definition": "Manipular equação para explicitar variável de interesse.", "evidence_level": "medium_high"},
    {"code": "stat.center", "competence": "stat", "name": "Interpretação de tendência central",
     "definition": "Aplicar corretamente média, mediana e moda em contexto.", "evidence_level": "medium_high"},
    # fact / conc
    {"code": "fact.recall", "competence": "fact", "name": "Evocação declarativa",
     "definition": "Recuperar informação factual da memória sem apoio.", "evidence_level": "medium_high"},
    {"code": "conc.link", "competence": "conc", "name": "Encadeamento conceitual",
     "definition": "Relacionar dois conceitos ligados por princípio ou causalidade.", "evidence_level": "medium_high"},
    # load / meta
    {"code": "load.chunk", "competence": "load", "name": "Chunking em enunciado longo",
     "definition": "Segmentar enunciado extenso em unidades processáveis.", "evidence_level": "medium_high"},
    {"code": "meta.check", "competence": "meta", "name": "Verificação de plausibilidade",
     "definition": "Avaliar se resposta encontrada é coerente com os dados do problema.", "evidence_level": "medium_high"},
]


# ---------- Level 4 — Observable Skills (hypotheses for measurement) ----------

SKILLS = [
    {"code": "skill.prop.explicit", "process": "prop.direct",
     "definition": "Resolve problemas de proporção quando a razão é explicitamente enunciada.",
     "hypothesis": "Aluno com alto Gf apresenta alta taxa de acerto em itens de proporcionalidade com relação explícita.",
     "evidence_level": "medium"},
    {"code": "skill.prop.implicit", "process": "prop.direct",
     "definition": "Resolve problemas de proporção quando a relação NÃO é explicitada.",
     "hypothesis": "A ausência de sinalização explícita da razão aumenta demanda de Gwm e reduz acerto.",
     "evidence_level": "medium"},
    {"code": "skill.ded.apply.enunc", "process": "ded.apply",
     "definition": "Aplica regra geral a caso quando ambos aparecem no mesmo enunciado.",
     "hypothesis": "Alunos falham quando a regra e o caso aparecem separados por parágrafos ou distratores.",
     "evidence_level": "medium"},
    {"code": "skill.lit.short", "process": "lit.locate",
     "definition": "Localiza informação explícita em textos curtos (< 200 palavras).",
     "hypothesis": "Taxa de acerto cai marcadamente após ~200 palavras de enunciado.",
     "evidence_level": "medium"},
    {"code": "skill.graph.linear", "process": "graph.trend",
     "definition": "Extrai tendência em gráfico de linhas.",
     "hypothesis": "Erros aumentam em gráficos com múltiplas séries.", "evidence_level": "medium"},
    {"code": "skill.alg.two.steps", "process": "alg.isolate",
     "definition": "Isola variável em equação com até 2 passos.",
     "hypothesis": "Erros crescem exponencialmente com o número de passos.", "evidence_level": "medium"},
    {"code": "skill.conc.crosslink", "process": "conc.link",
     "definition": "Conecta conceito de uma disciplina a fenômeno de outra (transferência).",
     "hypothesis": "Alunos com bom Glr acertam questões dentro da disciplina mas erram nas de transferência.",
     "evidence_level": "medium"},
    {"code": "skill.load.long.enunc", "process": "load.chunk",
     "definition": "Mantém desempenho em enunciados com mais de 300 palavras.",
     "hypothesis": "Existe queda sistemática de acerto acima de ~300 palavras.", "evidence_level": "medium"},
]


# ---------- Level 5 — Behavioral Indicators (empirical, growing) ----------
# These start as HYPOTHESES with confidence=0. Each attempt updates them.

INDICATOR_HYPOTHESES = [
    {
        "code": "ind.fatigue.late",
        "skill": "skill.load.long.enunc",
        "hypothesis": "Fadiga tardia: taxa de erro nas 30 últimas questões supera a das 30 primeiras em pelo menos 20 %.",
        "detector": "fatigue_late",
    },
    {
        "code": "ind.letter.bias",
        "skill": "skill.prop.explicit",
        "hypothesis": "Viés de letra: mais de 40 % dos erros concentrados numa mesma alternativa (indica chute).",
        "detector": "letter_bias",
    },
    {
        "code": "ind.language.block",
        "skill": "skill.lit.short",
        "hypothesis": "Bloqueio de idioma: 60 % ou mais das questões 1-5 (língua estrangeira) erradas.",
        "detector": "language_block",
    },
    {
        "code": "ind.consecutive.errors",
        "skill": "skill.load.long.enunc",
        "hypothesis": "Sequências de 3 ou mais erros consecutivos indicam desregulação atencional.",
        "detector": "consecutive_errors",
    },
    {
        "code": "ind.scatter.guess",
        "skill": "skill.ded.apply.enunc",
        "hypothesis": "Erros distribuídos entre A-E sem viés (nenhuma letra > 25 %) sugerem chute distribuído deliberado.",
        "detector": "scatter_guess",
    },
]


# ---------- Detectors: applied on every attempt ----------

def detect_fatigue_late(errors: list[dict], total: int) -> bool:
    if total < 60:
        return False
    numbers = sorted([e["number"] for e in errors])
    early = sum(1 for n in numbers if n <= (min(numbers, default=0) + 30))
    late = sum(1 for n in numbers if n >= (max(numbers, default=0) - 30))
    return late >= max(4, int(1.2 * max(early, 1)))


def detect_letter_bias(errors: list[dict], total: int) -> bool:
    if not errors:
        return False
    from collections import Counter
    counts = Counter([e.get("chosen", "") for e in errors if e.get("chosen")])
    if not counts:
        return False
    top = counts.most_common(1)[0][1]
    return top / len(errors) > 0.4


def detect_language_block(errors: list[dict], total: int) -> bool:
    lang_errors = [e for e in errors if 1 <= e["number"] <= 5]
    return len(lang_errors) >= 3


def detect_consecutive_errors(errors: list[dict], total: int) -> bool:
    nums = sorted([e["number"] for e in errors])
    if len(nums) < 3:
        return False
    streak = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            streak += 1
            if streak >= 3:
                return True
        else:
            streak = 1
    return False


def detect_scatter_guess(errors: list[dict], total: int) -> bool:
    if len(errors) < 8:
        return False
    from collections import Counter
    counts = Counter([e.get("chosen", "") for e in errors if e.get("chosen") in "ABCDE"])
    if len(counts) < 4:
        return False
    top = counts.most_common(1)[0][1]
    return (top / len(errors)) <= 0.25


DETECTORS = {
    "fatigue_late": detect_fatigue_late,
    "letter_bias": detect_letter_bias,
    "language_block": detect_language_block,
    "consecutive_errors": detect_consecutive_errors,
    "scatter_guess": detect_scatter_guess,
}


# ---------- Seed & update ----------

async def seed_ontology(db):
    """Idempotent seed of L1-L4 and L5 hypotheses."""
    marker = await db.settings.find_one({"key": "ontology_version"}, {"_id": 0})
    version = marker.get("value", 0) if marker else 0
    if version >= 1:
        return

    await db.ontology_domains.delete_many({})
    await db.ontology_competences.delete_many({})
    await db.ontology_processes.delete_many({})
    await db.ontology_skills.delete_many({})

    for d in DOMAINS:
        await db.ontology_domains.insert_one({**d, "created_at": _now()})
    for c in COMPETENCES:
        await db.ontology_competences.insert_one({**c, "created_at": _now()})
    for p in PROCESSES:
        await db.ontology_processes.insert_one({**p, "created_at": _now()})
    for s in SKILLS:
        await db.ontology_skills.insert_one({**s, "created_at": _now()})

    # Level 5 — hypotheses seeded once, then grow with data
    for i in INDICATOR_HYPOTHESES:
        existing = await db.ontology_indicators.find_one({"code": i["code"]}, {"_id": 0})
        if not existing:
            await db.ontology_indicators.insert_one({
                **i,
                "refined_definition": None,
                "evidence_count": 0,
                "total_observed": 0,
                "confidence": 0.0,
                "created_at": _now(),
                "refined_at": None,
            })

    await db.settings.update_one(
        {"key": "ontology_version"},
        {"$set": {"key": "ontology_version", "value": 1}},
        upsert=True,
    )


async def update_indicators_from_attempt(db, errors: list[dict], total: int) -> list[str]:
    """Called on every attempt. Applies each detector; increments evidence
    and total_observed atomically. Returns list of matched indicator codes.
    """
    matched: list[str] = []
    indicators = await db.ontology_indicators.find({}, {"_id": 0}).to_list(200)
    for ind in indicators:
        detector = DETECTORS.get(ind["detector"])
        if not detector:
            continue
        try:
            fired = detector(errors, total)
        except Exception:
            fired = False
        inc: dict[str, Any] = {"total_observed": 1}
        if fired:
            inc["evidence_count"] = 1
            matched.append(ind["code"])
        await db.ontology_indicators.update_one({"code": ind["code"]}, {"$inc": inc, "$set": {"refined_at": _now()}})
        # Recompute confidence
        fresh = await db.ontology_indicators.find_one({"code": ind["code"]}, {"_id": 0})
        if fresh and fresh.get("total_observed", 0) > 0:
            conf = fresh["evidence_count"] / fresh["total_observed"]
            await db.ontology_indicators.update_one({"code": ind["code"]}, {"$set": {"confidence": round(conf, 4)}})
    return matched
