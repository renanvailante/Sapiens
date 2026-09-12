"""A semana do aluno — domínio puro, sem I/O e sem IA.

O cronograma é uma agenda de segunda a domingo com **tudo** que o aluno vai
fazer: os compromissos que ele já tem (aula, trabalho, treino, a prova do
colégio) e os blocos de estudo que o Sapiens monta em volta deles.

A divisão de trabalho deste módulo com o resto da feature é a decisão mais
importante da funcionalidade, e existe por um motivo específico:

    **A aritmética do tempo e a ordem de prioridade são determinísticas
    aqui. O modelo de linguagem nunca decide horário nem o que vem antes.**

Um LLM pedindo para montar uma semana inteira erra de três jeitos que o aluno
percebe na hora: marca estudo em cima da aula dele, inventa um dia 32, e muda
a ordem das prioridades a cada geração. Aqui os horários livres são
calculados subtraindo os compromissos da janela do dia (`slots_livres`), a
prioridade sai de `prioridade_enem.ranking` (peso na prova × lacuna medida), e
o que sobra para o modelo — quando o aluno paga por isso — é **escrever** o
conteúdo de cada bloco já alocado, nunca escolher onde ele cai.

Consequência direta: o cronograma funciona inteiro com o modelo fora do ar, e
o aluno que nunca gastou um Spark tem a mesma semana montada com o mesmo
critério. O que a Mentis acrescenta é texto, não estrutura.

Semana começa na SEGUNDA (`dia` 0) e termina no domingo (`dia` 6) — é o
"de segunda a segunda" que o aluno enxerga no calendário dele, não a semana
ISO do servidor nem a semana domingo-a-sábado do Google.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

import prioridade_enem

# ---------------------------------------------------------------------------
# Vocabulário
# ---------------------------------------------------------------------------

DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")

# Tipos de bloco. Os quatro primeiros são COMPROMISSO do aluno (imóveis: o
# Sapiens trabalha em volta deles). Os cinco últimos são ESTUDO — o que o
# cronograma aloca no que sobrou.
TIPOS_COMPROMISSO = ("aula", "trabalho", "prova", "pessoal")
TIPOS_ESTUDO = ("questoes", "treino", "redacao", "revisao", "estudo")
TIPOS = TIPOS_COMPROMISSO + TIPOS_ESTUDO

ORIGENS = ("manual", "voz", "chat", "google", "ics", "mentis", "sapiens")

MINUTOS_NO_DIA = 24 * 60

# Padrões da janela de estudo. Todos ajustáveis pelo aluno em
# `/cronograma/preferencias` — estes são só o ponto de partida de quem nunca
# mexeu em nada.
PREFERENCIAS_PADRAO: dict[str, Any] = {
    "inicio_dia": "07:00",
    "fim_dia": "22:00",
    "bloco_minutos": 50,      # um bloco de estudo com intervalo curto depois
    "intervalo_minutos": 10,
    "blocos_por_dia": 3,
    "dias_de_folga": [6],     # domingo: descanso previsto, não esquecimento
}

_BLOCO_MIN = 20
_BLOCO_MAX = 180
_BLOCOS_POR_DIA_MAX = 8
_TETO_SLOTS_SEMANA = 40        # teto de segurança do prompt e da tela
_TETO_COMPROMISSOS = 60        # por aluno; acima disso a agenda vira lixo
_TITULO_MAX = 90
_DETALHE_MAX = 220


# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------


def hhmm_para_minutos(valor: str) -> int:
    """"08:30" -> 510. Levanta ValueError em qualquer coisa que não seja um
    horário do dia — inclusive "24:00", que parece inofensivo e quebra toda a
    aritmética de fim de intervalo mais adiante."""
    if not isinstance(valor, str):
        raise ValueError("Horário precisa ser texto no formato HH:MM.")
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", valor)
    if not m:
        raise ValueError(f"Horário inválido: {valor!r}. Use HH:MM.")
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        raise ValueError(f"Horário fora do dia: {valor!r}.")
    return h * 60 + mi


def minutos_para_hhmm(minutos: int) -> str:
    minutos = max(0, min(MINUTOS_NO_DIA - 1, int(minutos)))
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def segunda_da_semana(quando: date) -> str:
    """A segunda-feira da semana que contém `quando`, em ISO (YYYY-MM-DD).

    É a CHAVE da semana em todo o resto do sistema: o plano é gravado sob ela,
    a tela pede por ela e a comparação "o plano é da semana passada?" é uma
    comparação de strings.
    """
    return (quando - timedelta(days=quando.weekday())).isoformat()


def dias_da_semana(segunda_iso: str) -> list[str]:
    base = date.fromisoformat(segunda_iso)
    return [(base + timedelta(days=i)).isoformat() for i in range(7)]


def indice_do_dia(data_iso: str, segunda_iso: str) -> Optional[int]:
    """0..6 se `data_iso` cai nesta semana; None se não cai."""
    try:
        delta = (date.fromisoformat(data_iso) - date.fromisoformat(segunda_iso)).days
    except (TypeError, ValueError):
        return None
    return delta if 0 <= delta <= 6 else None


# ---------------------------------------------------------------------------
# Compromissos
# ---------------------------------------------------------------------------


def novo_id() -> str:
    return uuid.uuid4().hex[:12]


def normalizar_compromisso(bruto: dict[str, Any], *, origem: str = "manual") -> dict[str, Any]:
    """Valida e completa um compromisso vindo de qualquer porta de entrada
    (formulário, chat, voz, Google Agenda, arquivo .ics).

    Uma porta de entrada só: por mais diferentes que sejam as origens, um
    compromisso mal formado nunca chega ao banco, e a tela nunca precisa
    saber de onde ele veio para desenhá-lo.
    """
    titulo = str(bruto.get("titulo") or "").strip()[:_TITULO_MAX]
    if not titulo:
        raise ValueError("Todo compromisso precisa de um título.")

    inicio = hhmm_para_minutos(str(bruto.get("inicio") or "00:00"))
    fim = hhmm_para_minutos(str(bruto.get("fim") or "00:00"))
    dia_inteiro = bool(bruto.get("dia_inteiro"))
    if dia_inteiro:
        inicio, fim = 0, MINUTOS_NO_DIA - 1
    elif fim <= inicio:
        raise ValueError(f"'{titulo}': o fim ({minutos_para_hhmm(fim)}) não vem depois do início.")

    data_iso = bruto.get("data")
    if data_iso:
        try:
            dia = date.fromisoformat(str(data_iso)).weekday()
        except ValueError as exc:
            raise ValueError(f"'{titulo}': data inválida ({data_iso!r}).") from exc
        data_iso = str(data_iso)
    else:
        dia = bruto.get("dia")
        if not isinstance(dia, int) or not 0 <= dia <= 6:
            raise ValueError(f"'{titulo}': informe o dia da semana (0=segunda) ou uma data.")
        data_iso = None

    tipo = bruto.get("tipo") if bruto.get("tipo") in TIPOS_COMPROMISSO else "pessoal"
    return {
        "id": str(bruto.get("id") or novo_id()),
        "titulo": titulo,
        "dia": dia,
        "inicio": minutos_para_hhmm(inicio),
        "fim": minutos_para_hhmm(fim),
        "tipo": tipo,
        # Sem data = rotina que se repete toda semana ("aula de inglês, terça,
        # 19h"). Com data = evento de um dia só ("prova de biologia, dia 24").
        # É a única diferença entre as duas, e ela decide se o bloco reaparece
        # na semana seguinte.
        "data": data_iso,
        "dia_inteiro": dia_inteiro,
        "origem": origem if origem in ORIGENS else "manual",
        "fixo": True,
        "observacao": (str(bruto.get("observacao") or "").strip() or None),
        "externo_id": (str(bruto.get("externo_id")).strip() if bruto.get("externo_id") else None),
    }


def compromissos_da_semana(compromissos: Iterable[dict], segunda_iso: str) -> list[dict]:
    """Os compromissos que valem NESTA semana: os recorrentes, sempre, e os
    datados, só se a data cair dentro dela."""
    fora: list[dict] = []
    for c in compromissos or []:
        if c.get("data"):
            if indice_do_dia(c["data"], segunda_iso) is None:
                continue
            fora.append({**c, "dia": indice_do_dia(c["data"], segunda_iso)})
        else:
            fora.append(dict(c))
    fora.sort(key=lambda c: (c["dia"], c["inicio"]))
    return fora


def conflitos(compromissos: list[dict]) -> list[tuple[str, str]]:
    """Pares de compromissos que se sobrepõem no mesmo dia.

    Não impede de salvar — a vida do aluno sobrepõe mesmo, e um formulário que
    recusa "aula das 8 às 12" porque existe "monitoria das 11 às 12" só ensina
    a pessoa a mentir para o app. Serve para a tela AVISAR.
    """
    achados: list[tuple[str, str]] = []
    por_dia: dict[int, list[dict]] = {}
    for c in compromissos:
        por_dia.setdefault(c["dia"], []).append(c)
    for lista in por_dia.values():
        ordenada = sorted(lista, key=lambda c: hhmm_para_minutos(c["inicio"]))
        for i in range(len(ordenada) - 1):
            a, b = ordenada[i], ordenada[i + 1]
            if hhmm_para_minutos(b["inicio"]) < hhmm_para_minutos(a["fim"]):
                achados.append((a["id"], b["id"]))
    return achados


# ---------------------------------------------------------------------------
# Janelas livres e slots de estudo
# ---------------------------------------------------------------------------


def normalizar_preferencias(bruto: Optional[dict]) -> dict[str, Any]:
    p = {**PREFERENCIAS_PADRAO, **(bruto or {})}
    inicio = hhmm_para_minutos(str(p["inicio_dia"]))
    fim = hhmm_para_minutos(str(p["fim_dia"]))
    if fim - inicio < _BLOCO_MIN:
        raise ValueError("A janela de estudo do dia precisa ter pelo menos 20 minutos.")
    bloco = max(_BLOCO_MIN, min(_BLOCO_MAX, int(p["bloco_minutos"])))
    folgas = sorted({d for d in (p.get("dias_de_folga") or []) if isinstance(d, int) and 0 <= d <= 6})
    if len(folgas) == 7:
        # Sete dias de folga é uma semana sem cronograma. Aceitar isso em
        # silêncio devolveria uma tela vazia sem nenhuma explicação.
        raise ValueError("Deixe pelo menos um dia da semana livre para estudar.")
    return {
        "inicio_dia": minutos_para_hhmm(inicio),
        "fim_dia": minutos_para_hhmm(fim),
        "bloco_minutos": bloco,
        "intervalo_minutos": max(0, min(60, int(p["intervalo_minutos"]))),
        "blocos_por_dia": max(1, min(_BLOCOS_POR_DIA_MAX, int(p["blocos_por_dia"]))),
        "dias_de_folga": folgas,
    }


def janelas_livres_do_dia(ocupados: list[dict], inicio: int, fim: int) -> list[tuple[int, int]]:
    """O que sobra da janela [inicio, fim] depois de tirar os compromissos.

    Compromissos sobrepostos são fundidos antes da subtração — sem isso, "aula
    8-12" e "monitoria 11-12" produziriam uma janela livre fantasma das 12 às
    11, e o cronograma marcaria estudo dentro da aula.
    """
    intervalos = sorted(
        ((hhmm_para_minutos(c["inicio"]), hhmm_para_minutos(c["fim"])) for c in ocupados),
        key=lambda t: t[0],
    )
    fundidos: list[list[int]] = []
    for a, b in intervalos:
        if fundidos and a <= fundidos[-1][1]:
            fundidos[-1][1] = max(fundidos[-1][1], b)
        else:
            fundidos.append([a, b])

    livres: list[tuple[int, int]] = []
    cursor = inicio
    for a, b in fundidos:
        if b <= inicio or a >= fim:
            continue
        if a > cursor:
            livres.append((cursor, min(a, fim)))
        cursor = max(cursor, b)
        if cursor >= fim:
            break
    if cursor < fim:
        livres.append((cursor, fim))
    return [(a, b) for a, b in livres if b - a >= _BLOCO_MIN]


def slots_livres(compromissos: list[dict], preferencias: dict, segunda_iso: str) -> list[dict]:
    """Os horários candidatos da semana, em ordem, já sem conflito nenhum.

    Cada slot é uma vaga vazia: dia, início, fim e nada mais. Quem decide o
    que entra em cada uma é `alocar`, e quem eventualmente ESCREVE o conteúdo é
    a Mentis — nenhum dos dois volta a mexer no horário.
    """
    prefs = normalizar_preferencias(preferencias)
    inicio_dia = hhmm_para_minutos(prefs["inicio_dia"])
    fim_dia = hhmm_para_minutos(prefs["fim_dia"])
    passo = prefs["bloco_minutos"] + prefs["intervalo_minutos"]
    da_semana = compromissos_da_semana(compromissos, segunda_iso)

    slots: list[dict] = []
    for dia in range(7):
        if dia in prefs["dias_de_folga"]:
            continue
        ocupados = [c for c in da_semana if c["dia"] == dia]
        do_dia = 0
        for a, b in janelas_livres_do_dia(ocupados, inicio_dia, fim_dia):
            cursor = a
            while cursor + prefs["bloco_minutos"] <= b and do_dia < prefs["blocos_por_dia"]:
                slots.append({
                    "dia": dia,
                    "inicio": minutos_para_hhmm(cursor),
                    "fim": minutos_para_hhmm(cursor + prefs["bloco_minutos"]),
                    "ordem_no_dia": do_dia,
                })
                cursor += passo
                do_dia += 1
            if do_dia >= prefs["blocos_por_dia"]:
                break
    for i, s in enumerate(slots):
        s["indice"] = i
    return slots[:_TETO_SLOTS_SEMANA]


def _contiguos(a: dict, b: dict, prefs: dict) -> bool:
    return (
        a["dia"] == b["dia"]
        and hhmm_para_minutos(b["inicio"]) - hhmm_para_minutos(a["fim"]) <= prefs["intervalo_minutos"]
    )
