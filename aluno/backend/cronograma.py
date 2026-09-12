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
TETO_COMPROMISSOS = 60        # por aluno; acima disso a agenda vira lixo
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


# ---------------------------------------------------------------------------
# Alocação — quem fica com cada vaga
# ---------------------------------------------------------------------------
#
# A ordem abaixo é a regra do produto, e é deliberadamente rígida:
#
#   1. REVISÃO vem primeiro. Um reteste com data marcada não é uma sugestão —
#      é uma dívida que o próprio aluno contraiu ao errar, e a data saiu da
#      curva de esquecimento, não de uma preferência. Adiar revisão para
#      caber mais matéria nova é exatamente o erro que a revisão espaçada
#      existe para impedir.
#   2. TREINO da habilidade mais fraca. Uma causa raiz identificada é mais
#      específica — e mais barata de corrigir — do que "estudar a matéria".
#   3. REDAÇÃO, quando ela está entre as frentes que mais rendem. Ganha bloco
#      duplo quando há duas vagas seguidas: redação do ENEM leva 90 minutos, e
#      um bloco de 50 ensina o aluno a não terminar.
#   4. O RESTO vai para as áreas, proporcional ao rendimento
#      (`prioridade_enem`), pelo método do maior resto — que é o único jeito
#      de distribuir N vagas inteiras por percentuais sem sumir com a frente
#      que ficou com 0,4 de um bloco.
#
# O teto por frente existe para que a semana continue sendo uma semana: sem
# ele, um aluno com uma lacuna gigante em Matemática recebia sete dias de
# Matemática e parava de abrir o app na quarta-feira.

# O que fazer num bloco de questões depois do primeiro da mesma área. O
# primeiro bloco de cada frente carrega o PORQUÊ (a medida que colocou a área
# ali); do segundo em diante, o mesmo parágrafo repetido em seis cards seguidos
# deixa de ser lido e a semana vira um muro de texto igual. Estas instruções
# não afirmam nada sobre o aluno — são modos de estudar, e por isso podem ser
# fixas sem virar diagnóstico inventado.
INSTRUCOES_QUESTOES = (
    "Faça as questões seguidas, sem consultar nada, e só confira o gabarito no fim.",
    "Comece refazendo o que você errou da última vez nesta área, antes de pegar questão nova.",
    "Cronometre: três minutos por questão, do jeito que vai ser no dia da prova.",
    "Puxe questões de anos diferentes sobre o mesmo tema — é o que separa entender de decorar.",
    "Ao errar, escreva em uma linha por que a alternativa errada pareceu certa. É esse texto que vira revisão.",
)

TETO_POR_FRENTE = 0.40
MAX_REVISOES_SEMANA = 3
MAX_TREINOS_SEMANA = 2
_REDACAO_TOPO = 4   # posição no ranking até a qual a redação ganha bloco fixo


def _bloco(slot: dict, **campos: Any) -> dict[str, Any]:
    return {
        "id": novo_id(),
        "dia": slot["dia"],
        "inicio": slot["inicio"],
        "fim": slot["fim"],
        "fixo": False,
        "origem": campos.pop("origem", "sapiens"),
        "slot": slot["indice"],
        **campos,
    }


def _maior_resto(pesos: list[float], total: int) -> list[int]:
    """Distribui `total` vagas inteiras proporcionalmente a `pesos`.

    Método do maior resto (Hamilton): cada frente leva a parte inteira da sua
    fatia e as vagas que sobram vão para quem tem o maior resto. Arredondar
    cada fatia isoladamente perderia ou inventaria vagas — e a soma precisa
    fechar exatamente com o número de horários livres que o aluno tem.
    """
    soma = sum(pesos)
    if total <= 0 or soma <= 0:
        return [0] * len(pesos)
    exatos = [p / soma * total for p in pesos]
    inteiros = [int(e) for e in exatos]
    sobra = total - sum(inteiros)
    ordem = sorted(range(len(pesos)), key=lambda i: (-(exatos[i] - inteiros[i]), -pesos[i], i))
    for i in ordem[:sobra]:
        inteiros[i] += 1
    return inteiros


def _espalhar(slots: list[dict]) -> list[dict]:
    """Reordena as vagas para que a distribuição caia em dias diferentes.

    Percorrendo os slots na ordem cronológica pura, a primeira frente da fila
    levava as três vagas de segunda-feira e a última nunca aparecia antes de
    quinta. Ordenar por "primeira vaga de cada dia, depois a segunda de cada
    dia" faz a mesma lista produzir uma semana variada, sem nenhuma
    aleatoriedade — a mesma entrada gera sempre a mesma semana.
    """
    return sorted(slots, key=lambda s: (s["ordem_no_dia"], s["dia"], s["inicio"]))


def _tomar_por_dia(disponiveis: list[dict], quantos: int, usados_por_dia: dict[int, int]) -> list[dict]:
    """Pega até `quantos` slots, no máximo um por dia, os mais cedo primeiro."""
    escolhidos: list[dict] = []
    for s in sorted(disponiveis, key=lambda s: (s["dia"], s["inicio"])):
        if len(escolhidos) >= quantos:
            break
        if usados_por_dia.get(s["dia"]):
            continue
        escolhidos.append(s)
        usados_por_dia[s["dia"]] = usados_por_dia.get(s["dia"], 0) + 1
    return escolhidos


def _par_contiguo(disponiveis: list[dict], prefs: dict) -> Optional[tuple[dict, dict]]:
    ordenados = sorted(disponiveis, key=lambda s: (s["dia"], s["inicio"]))
    for a, b in zip(ordenados, ordenados[1:]):
        if _contiguos(a, b, prefs):
            return a, b
    return None


def alocar(
    slots: list[dict],
    prioridades: list[dict],
    *,
    revisoes: Optional[list[dict]] = None,
    habilidades_fracas: Optional[list[dict]] = None,
    preferencias: Optional[dict] = None,
) -> dict[str, Any]:
    """Monta a semana. Determinístico: mesma entrada, mesma semana, sempre.

    `prioridades` vem de `prioridade_enem.ranking`; `revisoes` de
    `revisao_service.fila`; `habilidades_fracas` do agregado de treino.
    Nenhum dos três é opinião de modelo — são contagens sobre o que o aluno
    respondeu.
    """
    prefs = normalizar_preferencias(preferencias)
    disponiveis = list(slots)
    blocos: list[dict] = []
    usados_por_dia: dict[int, int] = {}

    # 1. Revisões marcadas -----------------------------------------------------
    fila = [r for r in (revisoes or []) if r][:MAX_REVISOES_SEMANA]
    for item, slot in zip(fila, _tomar_por_dia(disponiveis, len(fila), usados_por_dia)):
        disponiveis.remove(slot)
        nome = item.get("processo_nome") or item.get("nome") or "ponto marcado para revisão"
        blocos.append(_bloco(
            slot,
            tipo="revisao",
            titulo=f"Revisão: {nome}"[:_TITULO_MAX],
            detalhe=(item.get("motivo") or
                     "Este ponto voltou para a fila porque a data de reteste chegou.")[:_DETALHE_MAX],
            rota="/revisoes",
            frente="revisao",
            frente_nome="Revisão espaçada",
        ))

    # 2. Treino da habilidade mais fraca ---------------------------------------
    fracas = [h for h in (habilidades_fracas or []) if h.get("hab_id")][:MAX_TREINOS_SEMANA]
    for hab, slot in zip(fracas, _tomar_por_dia(disponiveis, len(fracas), usados_por_dia)):
        disponiveis.remove(slot)
        taxa = hab.get("percentual_acerto")
        blocos.append(_bloco(
            slot,
            tipo="treino",
            titulo=f"Treino: {hab.get('nome') or hab['hab_id']}"[:_TITULO_MAX],
            detalhe=(
                f"Você acerta {taxa}% aqui ({hab.get('respondidas')} respostas). "
                "É a habilidade isolada mais fraca do seu histórico."
                if taxa is not None else
                "Habilidade que o seu histórico ainda não sustenta."
            )[:_DETALHE_MAX],
            rota=f"/treino?hab={hab['hab_id']}",
            hab_id=hab["hab_id"],
            frente="treino",
            frente_nome="Treino de habilidade",
        ))

    # 3. Redação ---------------------------------------------------------------
    posicao_redacao = next((i for i, p in enumerate(prioridades) if p["chave"] == "redacao"), 99)
    linha_redacao = next((p for p in prioridades if p["chave"] == "redacao"), None)
    quantas_redacoes = 0
    if linha_redacao is not None and posicao_redacao < _REDACAO_TOPO and disponiveis:
        quantas_redacoes = 2 if (posicao_redacao <= 1 and len(slots) >= 10) else 1
    for _ in range(quantas_redacoes):
        par = _par_contiguo(disponiveis, prefs)
        if par:
            a, b = par
            disponiveis.remove(a)
            disponiveis.remove(b)
            slot = {**a, "fim": b["fim"]}
            duplo = True
        elif disponiveis:
            slot = sorted(disponiveis, key=lambda s: (s["dia"], s["inicio"]))[0]
            disponiveis.remove(slot)
            duplo = False
        else:
            break
        blocos.append(_bloco(
            slot,
            tipo="redacao",
            titulo="Redação do zero, cronometrada" if duplo else "Redação: parágrafo por parágrafo",
            detalhe=(
                (linha_redacao.get("porque") or "")
                + (" Bloco duplo: a redação do ENEM leva 90 minutos, e treinar em 50 ensina a não terminar."
                   if duplo else " Bloco curto: trabalhe uma competência isolada, não o texto inteiro.")
            ).strip()[:_DETALHE_MAX],
            rota="/redacao",
            frente="redacao",
            frente_nome="Redação",
        ))

    # 4. O resto, proporcional ao rendimento -----------------------------------
    frentes = [p for p in prioridades if p["chave"] != "redacao" and p["rendimento"] > 0]
    distribuicao: list[dict] = []
    if frentes and disponiveis:
        teto = max(1, int(len(disponiveis) * TETO_POR_FRENTE))
        cotas = _maior_resto([p["rendimento"] for p in frentes], len(disponiveis))
        # Aplica o teto e devolve o excedente para quem ainda tem espaço, na
        # ordem da prioridade — jogar fora a sobra deixaria vagas vazias na
        # semana de quem tem uma lacuna dominante.
        excedente = 0
        for i, c in enumerate(cotas):
            if c > teto:
                excedente += c - teto
                cotas[i] = teto
        i = 0
        while excedente > 0 and any(c < teto for c in cotas):
            if cotas[i % len(cotas)] < teto:
                cotas[i % len(cotas)] += 1
                excedente -= 1
            i += 1
            if i > len(cotas) * (teto + 1):
                break

        ordem_slots = _espalhar(disponiveis)
        cursor = 0
        ordinal = 0
        for frente, cota in zip(frentes, cotas):
            if cota <= 0:
                continue
            distribuicao.append({
                "chave": frente["chave"], "nome": frente["nome"], "blocos": cota,
                "peso": frente["peso"], "porque": frente["porque"], "estado": frente["estado"],
            })
            for indice_na_frente in range(cota):
                if cursor >= len(ordem_slots):
                    break
                slot = ordem_slots[cursor]
                cursor += 1
                # Gira pelas instruções a partir de um ponto diferente em
                # cada frente: assim Matemática e Biologia não abrem o mesmo
                # dia com exatamente a mesma frase. O PORQUÊ da frente é
                # colocado depois, no bloco que aparece primeiro na semana —
                # ver `_explicar_a_primeira_vez`.
                detalhe = INSTRUCOES_QUESTOES[(ordinal + indice_na_frente) % len(INSTRUCOES_QUESTOES)]
                blocos.append(_bloco(
                    slot,
                    tipo="questoes",
                    titulo=f"Questões de {frente['nome']}"[:_TITULO_MAX],
                    detalhe=detalhe[:_DETALHE_MAX],
                    rota=frente["rota"],
                    frente=frente["chave"],
                    frente_nome=frente["nome"],
                ))
            ordinal += 1

    if quantas_redacoes:
        distribuicao.insert(0, {
            "chave": "redacao", "nome": "Redação", "blocos": quantas_redacoes,
            "peso": (linha_redacao or {}).get("peso", 1.0),
            "porque": (linha_redacao or {}).get("porque", ""),
            "estado": (linha_redacao or {}).get("estado", "sem_medida"),
        })

    blocos.sort(key=lambda b: (b["dia"], b["inicio"]))
    # A distribuição é lida como "por que a semana ficou assim": ordenada por
    # tamanho da fatia, e não pela ordem em que as frentes foram alocadas.
    # A Redação é inserida no topo da lista por ser um caso à parte, e com 1
    # bloco ela abria a explicação de uma semana com 5 de Matemática.
    distribuicao.sort(key=lambda d: (-d["blocos"], -d["peso"], d["nome"]))
    _explicar_a_primeira_vez(blocos, frentes)
    return {"blocos": blocos, "distribuicao": distribuicao}


def _explicar_a_primeira_vez(blocos: list[dict], frentes: list[dict]) -> None:
    """O porquê de cada área vai no bloco em que ela APARECE primeiro na semana.

    Tem de ser depois da ordenação: a alocação distribui as vagas espalhando
    por dia, então o primeiro bloco que uma frente recebe não é o primeiro que
    o aluno vê. Antes deste passo, a explicação de Matemática caía na quarta
    enquanto a terça já tinha um bloco de Matemática sem contexto nenhum.
    """
    por_chave = {f["chave"]: f for f in frentes}
    explicadas: set[str] = set()
    for b in blocos:
        chave = b.get("frente")
        if b["tipo"] != "questoes" or chave in explicadas or chave not in por_chave:
            continue
        b["detalhe"] = por_chave[chave]["porque"][:_DETALHE_MAX]
        explicadas.add(chave)


# ---------------------------------------------------------------------------
# Importação de agenda externa
# ---------------------------------------------------------------------------
#
# Duas portas, porque nem todo aluno consegue passar pela mesma:
#
#  * **Google Agenda por OAuth** — o aluno autoriza no popup do Google, o
#    navegador lê os eventos da semana com o token dele e manda para cá já em
#    JSON. O backend nunca vê credencial nenhuma do Google.
#  * **Endereço .ics** — o "endereço secreto em formato iCal" que o Google (e
#    Outlook, e iCloud) publica nas configurações do calendário. Não depende
#    de console, de consentimento verificado nem de escopo aprovado: é uma URL
#    que o servidor busca. É a porta que funciona quando a primeira não abre.
#
# As duas terminam em `normalizar_compromisso`, então um evento importado é
# indistinguível de um digitado à mão — pode ser editado e apagado igual.

_ICS_MAX_EVENTOS = 300
_ESCAPES_ICS = {"\\n": " ", "\\N": " ", "\\,": ",", "\\;": ";", "\\\\": "\\"}


def _desdobrar_ics(texto: str) -> list[str]:
    """Junta as linhas continuadas do iCalendar (RFC 5545 §3.1): uma linha que
    começa com espaço ou tab é a continuação da anterior, sem separador."""
    linhas: list[str] = []
    for bruta in texto.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if bruta[:1] in (" ", "\t") and linhas:
            linhas[-1] += bruta[1:]
        else:
            linhas.append(bruta)
    return linhas


def _valor_ics(valor: str) -> str:
    for de, para in _ESCAPES_ICS.items():
        valor = valor.replace(de, para)
    return valor.strip()


def _instante_ics(propriedade: str, valor: str, tz) -> tuple[Optional[datetime], bool]:
    """Converte DTSTART/DTEND para datetime no fuso do aluno.

    Três formas na natureza, e as três aparecem em calendários reais:
      `;VALUE=DATE:20260914`            evento de dia inteiro
      `;TZID=America/Sao_Paulo:...`     horário local de um fuso nomeado
      `:20260914T110000Z`               UTC
    """
    from zoneinfo import ZoneInfo  # local: o import custa e só esta função usa

    params = propriedade.split(";")[1:]
    dia_inteiro = any(p.upper() == "VALUE=DATE" for p in params)
    tzid = next((p[5:] for p in params if p.upper().startswith("TZID=")), None)
    valor = valor.strip()
    try:
        if dia_inteiro or (len(valor) == 8 and valor.isdigit()):
            return datetime.strptime(valor, "%Y%m%d").replace(tzinfo=tz), True
        if valor.endswith("Z"):
            bruto = datetime.strptime(valor, "%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC"))
            return bruto.astimezone(tz), False
        origem = tz
        if tzid:
            try:
                origem = ZoneInfo(tzid)
            except Exception:  # noqa: BLE001 - TZID desconhecido: trata como local
                origem = tz
        return datetime.strptime(valor, "%Y%m%dT%H%M%S").replace(tzinfo=origem).astimezone(tz), False
    except ValueError:
        return None, False


def eventos_do_ics(texto: str, tz) -> list[dict[str, Any]]:
    """Eventos crus de um arquivo .ics, já no fuso do aluno.

    Parser mínimo de propósito: SUMMARY, DTSTART, DTEND e RRULE semanal. Um
    .ics de verdade traz dezenas de propriedades (participantes, anexos,
    alarmes, fusos embutidos) que não mudam nada no cronograma e cujo suporte
    completo custaria uma dependência nova no runtime.
    """
    eventos: list[dict[str, Any]] = []
    atual: Optional[dict[str, Any]] = None
    for linha in _desdobrar_ics(texto):
        if linha.startswith("BEGIN:VEVENT"):
            atual = {}
            continue
        if linha.startswith("END:VEVENT"):
            if atual and atual.get("titulo") and atual.get("inicio"):
                eventos.append(atual)
            atual = None
            if len(eventos) >= _ICS_MAX_EVENTOS:
                break
            continue
        if atual is None or ":" not in linha:
            continue
        propriedade, _, valor = linha.partition(":")
        nome = propriedade.split(";")[0].upper()
        if nome == "SUMMARY":
            atual["titulo"] = _valor_ics(valor)[:_TITULO_MAX]
        elif nome == "LOCATION":
            atual["observacao"] = _valor_ics(valor)[:_DETALHE_MAX] or None
        elif nome == "UID":
            atual["externo_id"] = _valor_ics(valor)[:120]
        elif nome == "DTSTART":
            quando, dia_inteiro = _instante_ics(propriedade, valor, tz)
            atual["inicio"] = quando
            atual["dia_inteiro"] = dia_inteiro
        elif nome == "DTEND":
            quando, _ = _instante_ics(propriedade, valor, tz)
            atual["fim"] = quando
        elif nome == "RRULE":
            atual["semanal"] = "FREQ=WEEKLY" in valor.upper()
    return eventos


def _tipo_por_titulo(titulo: str) -> str:
    """Chute honesto do tipo a partir do nome do evento. Erra para "pessoal",
    que é o tipo que não promete nada — e o aluno corrige em um clique."""
    baixo = unicodedata.normalize("NFKD", titulo.lower()).encode("ascii", "ignore").decode()
    if any(p in baixo for p in ("prova", "simulado", "exame", "avaliacao", "vestibular", "enem")):
        return "prova"
    if any(p in baixo for p in ("aula", "curso", "escola", "colegio", "cursinho", "monitoria", "reforco")):
        return "aula"
    if any(p in baixo for p in ("trabalho", "estagio", "expediente", "plantao", "turno", "reuniao")):
        return "trabalho"
    return "pessoal"


def compromissos_de_eventos(
    eventos: list[dict[str, Any]], segunda_iso: str, *, origem: str = "ics"
) -> list[dict[str, Any]]:
    """Eventos crus -> compromissos válidos, só os que caem nesta semana.

    Eventos com repetição semanal viram compromissos RECORRENTES (sem data):
    a aula de terça às 19h é a mesma toda semana, e gravá-la datada faria o
    cronograma da semana que vem nascer achando que a terça está livre.
    """
    fora: list[dict[str, Any]] = []
    for ev in eventos:
        inicio: Optional[datetime] = ev.get("inicio")
        if not inicio:
            continue
        fim: Optional[datetime] = ev.get("fim")
        semanal = bool(ev.get("semanal"))
        data_iso = inicio.date().isoformat()
        if not semanal and indice_do_dia(data_iso, segunda_iso) is None:
            continue
        try:
            fora.append(normalizar_compromisso({
                "titulo": ev.get("titulo") or "Compromisso",
                "dia": inicio.weekday() if semanal else None,
                "data": None if semanal else data_iso,
                "inicio": inicio.strftime("%H:%M"),
                "fim": (fim or (inicio + timedelta(hours=1))).strftime("%H:%M"),
                "dia_inteiro": bool(ev.get("dia_inteiro")),
                "tipo": _tipo_por_titulo(ev.get("titulo") or ""),
                "observacao": ev.get("observacao"),
                "externo_id": ev.get("externo_id"),
            }, origem=origem))
        except ValueError:
            # Um evento malformado no meio do calendário não pode derrubar a
            # importação inteira — o aluno perderia os outros 40 por causa de
            # um só, sem saber qual.
            continue
    return fora[:TETO_COMPROMISSOS]


def normalizar_evento_google(ev: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Um item de `calendar/v3/events` -> evento cru no formato de `eventos_do_ics`.

    O navegador já pediu `singleEvents=true`, então cada ocorrência chega
    datada e expandida: aqui nunca há RRULE para interpretar.
    """
    inicio_raw = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date")
    fim_raw = (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date")
    if not inicio_raw:
        return None
    dia_inteiro = not (ev.get("start") or {}).get("dateTime")
    try:
        inicio = datetime.fromisoformat(str(inicio_raw).replace("Z", "+00:00"))
        fim = datetime.fromisoformat(str(fim_raw).replace("Z", "+00:00")) if fim_raw else None
    except ValueError:
        return None
    return {
        "titulo": (ev.get("summary") or "Compromisso")[:_TITULO_MAX],
        "inicio": inicio,
        "fim": fim,
        "dia_inteiro": dia_inteiro,
        "semanal": False,
        "observacao": (ev.get("location") or None),
        "externo_id": (ev.get("id") or None),
    }


def mesclar_compromissos(atuais: list[dict], novos: list[dict]) -> tuple[list[dict], int, int]:
    """Junta o que veio de fora com o que já existia, sem duplicar.

    A chave é `externo_id` (UID do .ics / id do evento do Google): reimportar
    a mesma agenda ATUALIZA os eventos em vez de empilhar uma segunda cópia de
    cada aula. O que o aluno digitou à mão nunca é tocado — ele não tem
    `externo_id`, então nada de fora casa com ele.
    """
    por_externo = {c["externo_id"]: i for i, c in enumerate(atuais) if c.get("externo_id")}
    resultado = [dict(c) for c in atuais]
    criados = atualizados = 0
    for novo in novos:
        chave = novo.get("externo_id")
        if chave and chave in por_externo:
            indice = por_externo[chave]
            # Preserva o id interno: a tela pode ter esse bloco aberto, e
            # trocar o id por baixo transformaria uma edição em um órfão.
            resultado[indice] = {**novo, "id": resultado[indice]["id"]}
            atualizados += 1
        else:
            resultado.append(novo)
            if chave:
                por_externo[chave] = len(resultado) - 1
            criados += 1
    return resultado[:TETO_COMPROMISSOS], criados, atualizados


# ---------------------------------------------------------------------------
# O que o modelo pode dizer — e o que ele nunca decide
# ---------------------------------------------------------------------------


def validar_compromissos_do_modelo(
    resultado: Any, *, semana_iso: str, origem: str = "chat"
) -> list[dict[str, Any]]:
    """Valida a extração de compromissos a partir do que o aluno escreveu ou
    falou ("tenho aula seg/qua/sex de manhã e trabalho terça à tarde").

    O modelo aqui faz a única coisa que ele faz melhor que código: entender
    português solto. Tudo que ele devolve passa por `normalizar_compromisso`,
    o mesmo portão do formulário — um horário impossível ou um dia 9 é
    descartado em silêncio em vez de virar um bloco quebrado na agenda.
    """
    itens = resultado.get("compromissos") if isinstance(resultado, dict) else None
    if not isinstance(itens, list):
        raise ValueError("Campo 'compromissos' ausente ou inválido.")
    validos: list[dict[str, Any]] = []
    for bruto in itens:
        if not isinstance(bruto, dict):
            continue
        data_iso = bruto.get("data")
        if data_iso and indice_do_dia(str(data_iso), semana_iso) is None:
            # Data fora da semana pedida: mantém como recorrente se o modelo
            # deu o dia, descarta se não deu. Nunca grava um compromisso que a
            # tela não teria como mostrar.
            data_iso = None
            if not isinstance(bruto.get("dia"), int):
                continue
        try:
            validos.append(normalizar_compromisso({**bruto, "data": data_iso}, origem=origem))
        except ValueError:
            continue
    return validos[:TETO_COMPROMISSOS]


def resumo_para_modelo(
    blocos: list[dict], prioridades: list[dict], compromissos: list[dict]
) -> str:
    """A semana JÁ MONTADA, compactada para o prompt.

    O modelo recebe o que foi decidido, não os dados para decidir: uma linha
    por bloco com o índice, o dia, o horário e a frente. É o que permite pedir
    a ele um texto por bloco e casar a resposta pelo índice, sem nunca lhe dar
    a chance de mover nada.
    """
    linhas = [f"PRIORIDADES DO ALUNO (peso na prova x lacuna medida): {prioridade_enem.texto_para_modelo(prioridades)}"]
    if compromissos:
        ocupado = "; ".join(
            f"{DIAS[c['dia']]} {c['inicio']}-{c['fim']} {c['titulo']}" for c in compromissos[:12]
        )
        linhas.append(f"COMPROMISSOS FIXOS (intocáveis): {ocupado}.")
    else:
        linhas.append("COMPROMISSOS FIXOS: nenhum informado.")
    linhas.append("BLOCOS DE ESTUDO JÁ ALOCADOS (o horário é final, não mexa):")
    for i, b in enumerate(blocos):
        linhas.append(
            f"[{i}] {DIAS[b['dia']]} {b['inicio']}-{b['fim']} — {b.get('frente_nome') or b['tipo']}"
            f" ({b['tipo']})"
        )
    return "\n".join(linhas)


def aplicar_enriquecimento(blocos: list[dict], resultado: Any) -> tuple[list[dict], int]:
    """Aplica o texto escrito pela Mentis sobre os blocos já alocados.

    Só `titulo` e `detalhe` mudam. Dia, horário, tipo e rota são ignorados
    mesmo se vierem na resposta — é a garantia estrutural de que a Mentis não
    consegue marcar estudo em cima da aula do aluno nem inventar um link que
    não existe, por mais convincente que o texto dela seja.

    Devolve os blocos e quantos foram efetivamente reescritos: zero significa
    que a chamada não entregou nada, e quem chamou decide o que fazer com
    isso (na prática: devolver os Sparks e servir a semana determinística).
    """
    itens = resultado.get("blocos") if isinstance(resultado, dict) else None
    if not isinstance(itens, list):
        return blocos, 0
    saida = [dict(b) for b in blocos]
    reescritos = 0
    for item in itens:
        if not isinstance(item, dict):
            continue
        indice = item.get("indice")
        if not isinstance(indice, int) or not 0 <= indice < len(saida):
            continue
        titulo = item.get("titulo")
        detalhe = item.get("detalhe")
        mudou = False
        if isinstance(titulo, str) and titulo.strip():
            saida[indice]["titulo"] = titulo.strip()[:_TITULO_MAX]
            mudou = True
        if isinstance(detalhe, str) and detalhe.strip():
            saida[indice]["detalhe"] = detalhe.strip()[:_DETALHE_MAX]
            mudou = True
        if mudou:
            saida[indice]["origem"] = "mentis"
            reescritos += 1
    return saida, reescritos


def resumo_deterministico(blocos: list[dict], distribuicao: list[dict], prioridades: list[dict]) -> str:
    """O parágrafo que abre o cronograma quando a Mentis não foi chamada.

    Existe para que a versão gratuita não pareça uma versão mutilada: ela diz
    exatamente a mesma coisa que a paga diria — quantos blocos, onde eles
    foram parar e por quê —, só que com os números no lugar da prosa.
    """
    if not blocos:
        return (
            "Não sobrou nenhum horário livre nesta semana com os compromissos e a janela de "
            "estudo que você definiu. Ajuste a janela do dia ou remova um compromisso para a "
            "semana voltar a ter espaço."
        )
    horas = sum(
        hhmm_para_minutos(b["fim"]) - hhmm_para_minutos(b["inicio"]) for b in blocos
    ) / 60
    topo = max(distribuicao, key=lambda d: d["blocos"]) if distribuicao else None
    partes = [
        f"{len(blocos)} blocos nesta semana, {horas:.1f} horas de estudo no total."
    ]
    if topo:
        partes.append(
            f"A maior fatia foi para {topo['nome']} ({topo['blocos']} "
            f"{'bloco' if topo['blocos'] == 1 else 'blocos'}): {topo['porque']}"
        )
    sem_medida = [p["nome"] for p in prioridades if p.get("estado") == "sem_medida"][:3]
    if sem_medida:
        partes.append(
            "Entraram pelo peso na prova, sem medida sua ainda: " + ", ".join(sem_medida)
            + ". Responder questões dessas áreas troca esse palpite por diagnóstico."
        )
    return " ".join(partes)
