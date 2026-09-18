"""O painel do perfil cognitivo — tudo o que o aluno já produziu, em gráfico.

A tela "Seu perfil cognitivo" mostrava dois montes de cartões: no que você é
bom, no que você não é. Um ESTADO, sem escala, sem passado e sem número — o
aluno lia, concordava e não tinha nada para fazer com aquilo. O que falta a
uma tela dessas não é enfeite: é a **mudança**. Ninguém paga para ver um
retrato; paga para ver que o retrato de hoje é melhor que o de abril.

Este módulo é a montagem dessa tela, e é uma função PURA de propósito
(`montar`): quem lê o Firestore/Mongo é a rota (`perfil_publico_routes`), o
que permite testar cada gráfico sobre um agregado de mentira, offline.

## A fronteira de sempre, e onde ela passa aqui

`perfil_pedagogico` continua sendo a única forma de expor o que a ONTOLOGIA
sabe (domínio, competência, processo, habilidade, tipo de erro, intervenção):
rótulo escrito à mão e explicação, sem nome, sem id, sem percentual. Nada
neste módulo afrouxa isso — as forças e os pontos a desenvolver entram aqui
como as mesmas palavras, sem número nenhum ao lado.

Todo o resto que vira número e gráfico **não é ontologia**:

  * a **frente** (Matemática, Biologia, Redação…) é a divisão da prova, vinda
    de `fonte.disciplina` do acervo via `prioridade_enem` — é o vocabulário do
    aluno, não o catálogo interno;
  * **dia, hora, volume, tempo, constância** são o que o aluno fez, e ele tem
    todo o direito de ver o que fez.

## Custo

Zero leitura nova: o insumo é o agregado que o diagnóstico já lia (uma
varredura de eventos, em cache no Mongo por `total_respostas`) mais o ranking
de rendimento, que sai do mesmo agregado. Ver
`project_aluno_disciplina_leitura_firestore` — um painel de gráficos é
exatamente o tipo de tela que derruba a cota se for escrita sem essa conta.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import annotation_service
import prioridade_enem

# ---------------------------------------------------------------------------
# Amostras mínimas. Um gráfico bonito sobre 4 respostas é uma mentira bonita:
# abaixo destes números o painel prefere não afirmar nada.
# ---------------------------------------------------------------------------

# Abaixo disto não há painel: só o convite a responder questões.
MIN_PARA_PAINEL = 5
# Comparar "como você começou" com "como você está" exige metade de cada lado.
MIN_COMPARATIVO = 20
# Um bloco do dia (manhã, tarde, noite, madrugada) só entra na comparação de
# horários com isto.
MIN_BLOCO_HORARIO = 10
# Faixa de tempo e decisão de mudar a resposta: comparações de duas gavetas,
# então a exigência é por gaveta.
MIN_FAIXA_TEMPO = 8
MIN_DECISAO = 8

# Janelas dos gráficos. Não são limites de dados — são limites de LEITURA: uma
# linha com 400 pontos num celular é uma mancha.
JANELA_DIARIA = 90
JANELA_SEMANAL = 26
JANELA_CALENDARIO = 119  # 17 semanas cheias + a corrente
JANELA_FRENTE_SEMANAS = 12
# Regularidade: oito semanas é o horizonte em que um vestibulando ainda
# reconhece a própria rotina. Um ano inteiro dilui a semana que ele perdeu.
JANELA_CONSISTENCIA = 8

# Média móvel da taxa de acerto. 7 dias porque a semana é a unidade em que o
# aluno organiza a vida — e porque menos que isso vira serrilha.
JANELA_MOVEL = 7

BLOCOS_DO_DIA = [
    ("madrugada", "Madrugada", "0h às 5h", range(0, 6)),
    ("manha", "Manhã", "6h às 11h", range(6, 12)),
    ("tarde", "Tarde", "12h às 17h", range(12, 18)),
    ("noite", "Noite", "18h às 23h", range(18, 24)),
]

DIAS_DA_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

def _minutos(segundos: int) -> str:
    """`150` -> `"2min30"`. Só para rótulo — o corte real mora em
    `annotation_service`, e escrevê-lo à mão aqui daria duas verdades."""
    if segundos < 60:
        return f"{segundos}s"
    minutos, resto = divmod(segundos, 60)
    return f"{minutos}min" + (f"{resto:02d}" if resto else "")


_RAPIDO = annotation_service.FAIXA_RAPIDA_SEGUNDOS
_LONGO = annotation_service.FAIXA_LONGA_SEGUNDOS

FAIXAS_DE_TEMPO = [
    ("rapido", "No impulso", f"menos de {_minutos(_RAPIDO)} na questão"),
    ("medio", "No ritmo", f"entre {_minutos(_RAPIDO)} e {_minutos(_LONGO)}"),
    ("longo", "Com calma", f"mais de {_minutos(_LONGO)} na questão"),
]

# Chave da frente -> nome que o aluno lê. Sai de `prioridade_enem`, que é onde
# a divisão da prova mora.
_NOME_DA_FRENTE = {d["chave"]: d["nome"] for d in prioridade_enem.DISCIPLINAS}

# `contexto.tipo` do evento -> como o aluno chama aquilo. Chave desconhecida
# nunca vira rótulo cru na tela: cai em "Outras respostas".
ORIGENS = {
    "pratica_questoes": "Prática de questões",
    "treino_habilidade": "Treino de habilidades",
    "treino_questao_ia": "Questões feitas pela Mentis",
    "curso": "Aulas dos cursos",
    "curso_dominio": "Sondagem das aulas",
    "revisao": "Revisões",
    "prova": "Provas corrigidas",
    "outro": "Outras respostas",
}


# ---------------------------------------------------------------------------
# Utilidades de contagem
# ---------------------------------------------------------------------------


def _taxa(acertos: int, respondidas: int) -> Optional[float]:
    """Percentual de acerto, ou None quando não houve resposta. None não é
    zero: "não medido" e "errou tudo" são coisas diferentes, e um gráfico que
    as confunde desenha um buraco como se fosse um fracasso."""
    if not respondidas:
        return None
    return round(100 * acertos / respondidas, 1)


def _contagem(balde: dict[str, Any] | None, chave: str) -> tuple[int, int]:
    item = (balde or {}).get(chave) or {}
    return int(item.get("respondidas") or 0), int(item.get("acertos") or 0)


def _somar(baldes: list[dict[str, int]]) -> tuple[int, int]:
    respondidas = sum(int(b.get("respondidas") or 0) for b in baldes)
    acertos = sum(int(b.get("acertos") or 0) for b in baldes)
    return respondidas, acertos


def _dia(iso: str) -> date:
    return date.fromisoformat(iso)


def _rotulo_curto(dia_iso: str) -> str:
    d = _dia(dia_iso)
    return f"{d.day:02d}/{d.month:02d}"


# ---------------------------------------------------------------------------
# Séries temporais — a parte da tela que o produto inteiro existia sem ter
# ---------------------------------------------------------------------------


def _serie_diaria(por_dia: dict[str, Any], hoje: date) -> list[dict[str, Any]]:
    """Um ponto por dia da janela, inclusive os dias parados.

    Dia sem resposta entra com `respondidas: 0` e `taxa: None`. É a diferença
    entre a linha do acerto (que não deve cair num dia de folga) e a barra do
    volume (que deve mostrar o buraco).
    """
    if not por_dia:
        return []
    primeiro = min(_dia(d) for d in por_dia)
    inicio = max(primeiro, hoje - timedelta(days=JANELA_DIARIA - 1))

    linhas: list[dict[str, Any]] = []
    acumulado_r = acumulado_a = 0
    # O acumulado começa contando o que veio ANTES da janela: a linha de
    # "acerto acumulado" é a vida inteira do aluno, não só os 90 dias à vista.
    for chave, valor in sorted(por_dia.items()):
        if _dia(chave) < inicio:
            acumulado_r += int(valor.get("respondidas") or 0)
            acumulado_a += int(valor.get("acertos") or 0)

    janela: list[tuple[int, int]] = []
    passo = inicio
    while passo <= hoje:
        chave = passo.isoformat()
        respondidas, acertos = _contagem(por_dia, chave)
        acumulado_r += respondidas
        acumulado_a += acertos
        janela.append((respondidas, acertos))
        janela_recente = janela[-JANELA_MOVEL:]
        movel_r, movel_a = _somar(
            [{"respondidas": r, "acertos": a} for r, a in janela_recente]
        )
        linhas.append({
            "dia": chave,
            "rotulo": _rotulo_curto(chave),
            "respondidas": respondidas,
            "acertos": acertos,
            "taxa": _taxa(acertos, respondidas),
            "movel": _taxa(movel_a, movel_r),
            "acumulada": _taxa(acumulado_a, acumulado_r),
        })
        passo += timedelta(days=1)
    return linhas


def _segunda(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _serie_semanal(por_dia: dict[str, Any], hoje: date) -> list[dict[str, Any]]:
    """Uma barra por semana (segunda a domingo), como o resto do produto conta
    semana. Semana vazia no meio do histórico continua aparecendo — sumir com
    ela esconderia justamente a parada."""
    if not por_dia:
        return []
    semanas: dict[str, dict[str, int]] = {}
    for chave, valor in por_dia.items():
        inicio = _segunda(_dia(chave)).isoformat()
        alvo = semanas.setdefault(inicio, {"respondidas": 0, "acertos": 0})
        alvo["respondidas"] += int(valor.get("respondidas") or 0)
        alvo["acertos"] += int(valor.get("acertos") or 0)

    primeira = min(_dia(s) for s in semanas)
    corrente = _segunda(hoje)
    inicio = max(primeira, corrente - timedelta(weeks=JANELA_SEMANAL - 1))

    linhas = []
    passo = inicio
    while passo <= corrente:
        chave = passo.isoformat()
        dados = semanas.get(chave) or {"respondidas": 0, "acertos": 0}
        linhas.append({
            "semana": chave,
            "rotulo": _rotulo_curto(chave),
            "respondidas": dados["respondidas"],
            "acertos": dados["acertos"],
            "taxa": _taxa(dados["acertos"], dados["respondidas"]),
            "corrente": chave == corrente.isoformat(),
        })
        passo += timedelta(weeks=1)
    return linhas


def _comparativo(por_dia: dict[str, Any]) -> dict[str, Any]:
    """"Como você começou" × "como você está agora".

    O corte é pela METADE DAS RESPOSTAS, não pela metade do tempo: um aluno
    que respondeu 200 questões em março e 20 em setembro teria, no corte por
    tempo, um "agora" de 20 respostas comparado a um "antes" de 200 — e a
    diferença entre os dois lados seria só a amostra.
    """
    total_r, total_a = _somar(list(por_dia.values())) if por_dia else (0, 0)
    if total_r < MIN_COMPARATIVO:
        return {"suficiente": False, "minimo": MIN_COMPARATIVO, "respondidas": total_r}

    metade = total_r // 2
    inicio = {"respondidas": 0, "acertos": 0, "primeiro_dia": None, "ultimo_dia": None}
    agora = {"respondidas": 0, "acertos": 0, "primeiro_dia": None, "ultimo_dia": None}
    caminhado = 0
    for chave, valor in sorted(por_dia.items()):
        respondidas = int(valor.get("respondidas") or 0)
        acertos = int(valor.get("acertos") or 0)
        if not respondidas:
            continue
        alvo = inicio if caminhado < metade else agora
        alvo["respondidas"] += respondidas
        alvo["acertos"] += acertos
        alvo["primeiro_dia"] = alvo["primeiro_dia"] or chave
        alvo["ultimo_dia"] = chave
        caminhado += respondidas

    taxa_inicio = _taxa(inicio["acertos"], inicio["respondidas"])
    taxa_agora = _taxa(agora["acertos"], agora["respondidas"])
    if taxa_inicio is None or taxa_agora is None:
        return {"suficiente": False, "minimo": MIN_COMPARATIVO, "respondidas": total_r}
    return {
        "suficiente": True,
        "inicio": {**inicio, "taxa": taxa_inicio},
        "agora": {**agora, "taxa": taxa_agora},
        "delta": round(taxa_agora - taxa_inicio, 1),
    }


def _evolucao_por_frente(
    frente_por_semana: dict[str, Any], hoje: date
) -> dict[str, Any]:
    """Uma linha por matéria ao longo das semanas.

    As chaves do agregado são `frente|segunda-da-semana` — string plana porque
    o agregado é gravado no Mongo. Frente com amostra pequena fica de fora: o
    gráfico tem oito linhas possíveis e todas as oito desenhadas com três
    respostas cada não informam nada.
    """
    if not frente_por_semana:
        return {"semanas": [], "series": [], "linhas": []}

    por_frente: dict[str, dict[str, dict[str, int]]] = {}
    for chave, valor in frente_por_semana.items():
        if "|" not in chave:
            continue
        frente, semana = chave.split("|", 1)
        por_frente.setdefault(frente, {})[semana] = {
            "respondidas": int(valor.get("respondidas") or 0),
            "acertos": int(valor.get("acertos") or 0),
        }

    corrente = _segunda(hoje)
    limite = corrente - timedelta(weeks=JANELA_FRENTE_SEMANAS - 1)
    semanas = sorted({
        semana
        for mapa in por_frente.values()
        for semana in mapa
        if _dia(semana) >= limite
    })
    if not semanas:
        return {"semanas": [], "series": [], "linhas": []}

    series = []
    for frente, mapa in por_frente.items():
        total_r, total_a = _somar([mapa[s] for s in mapa if s in semanas])
        if total_r < prioridade_enem.AMOSTRA_MINIMA:
            continue
        series.append({
            "chave": frente,
            "nome": _NOME_DA_FRENTE.get(frente, frente),
            "respondidas": total_r,
            "taxa": _taxa(total_a, total_r),
        })
    series.sort(key=lambda s: -s["respondidas"])

    linhas = []
    for semana in semanas:
        linha: dict[str, Any] = {"semana": semana, "rotulo": _rotulo_curto(semana)}
        for serie in series:
            dados = por_frente[serie["chave"]].get(semana)
            linha[serie["chave"]] = (
                _taxa(dados["acertos"], dados["respondidas"]) if dados else None
            )
            linha[f"{serie['chave']}__n"] = dados["respondidas"] if dados else 0
        linhas.append(linha)
    return {"semanas": semanas, "series": series, "linhas": linhas}


# ---------------------------------------------------------------------------
# Ritmo e hábitos — o que o aluno faz, nunca o que ele é
# ---------------------------------------------------------------------------


def _por_hora(telemetria: dict[str, Any]) -> list[dict[str, Any]]:
    balde = telemetria.get("por_hora") or {}
    linhas = []
    for hora in range(24):
        respondidas, acertos = _contagem(balde, str(hora))
        linhas.append({
            "hora": hora,
            "rotulo": f"{hora:02d}h",
            "respondidas": respondidas,
            "acertos": acertos,
            "taxa": _taxa(acertos, respondidas),
        })
    return linhas


def _blocos_do_dia(telemetria: dict[str, Any]) -> list[dict[str, Any]]:
    balde = telemetria.get("por_hora") or {}
    linhas = []
    for chave, nome, faixa, horas in BLOCOS_DO_DIA:
        respondidas, acertos = _somar([(balde.get(str(h)) or {}) for h in horas])
        linhas.append({
            "chave": chave,
            "rotulo": nome,
            "faixa": faixa,
            "respondidas": respondidas,
            "acertos": acertos,
            "taxa": _taxa(acertos, respondidas),
            "confiavel": respondidas >= MIN_BLOCO_HORARIO,
        })
    return linhas


def _por_dia_semana(telemetria: dict[str, Any]) -> list[dict[str, Any]]:
    balde = telemetria.get("por_dia_semana") or {}
    linhas = []
    for indice, nome in enumerate(DIAS_DA_SEMANA):
        respondidas, acertos = _contagem(balde, str(indice))
        linhas.append({
            "indice": indice,
            "rotulo": nome,
            "respondidas": respondidas,
            "acertos": acertos,
            "taxa": _taxa(acertos, respondidas),
        })
    return linhas


def _por_faixa_de_tempo(telemetria: dict[str, Any]) -> list[dict[str, Any]]:
    balde = telemetria.get("por_faixa_de_tempo") or {}
    linhas = []
    for chave, rotulo, descricao in FAIXAS_DE_TEMPO:
        respondidas, acertos = _contagem(balde, chave)
        linhas.append({
            "chave": chave,
            "rotulo": rotulo,
            "descricao": descricao,
            "respondidas": respondidas,
            "acertos": acertos,
            "taxa": _taxa(acertos, respondidas),
            "confiavel": respondidas >= MIN_FAIXA_TEMPO,
        })
    return linhas


def _decisao(telemetria: dict[str, Any]) -> list[dict[str, Any]]:
    balde = telemetria.get("por_decisao") or {}
    rotulos = [
        ("manteve", "Mantive a primeira resposta"),
        ("mudou", "Mudei de ideia antes de enviar"),
    ]
    linhas = []
    for chave, rotulo in rotulos:
        respondidas, acertos = _contagem(balde, chave)
        linhas.append({
            "chave": chave,
            "rotulo": rotulo,
            "respondidas": respondidas,
            "acertos": acertos,
            "taxa": _taxa(acertos, respondidas),
            "confiavel": respondidas >= MIN_DECISAO,
        })
    return linhas


def _por_origem(telemetria: dict[str, Any]) -> list[dict[str, Any]]:
    balde = telemetria.get("por_origem") or {}
    linhas = []
    for chave, valor in balde.items():
        respondidas = int(valor.get("respondidas") or 0)
        if not respondidas:
            continue
        linhas.append({
            "chave": chave,
            "rotulo": ORIGENS.get(chave, ORIGENS["outro"]),
            "respondidas": respondidas,
            "acertos": int(valor.get("acertos") or 0),
            "taxa": _taxa(int(valor.get("acertos") or 0), respondidas),
        })
    linhas.sort(key=lambda l: -l["respondidas"])
    return linhas


# ---------------------------------------------------------------------------
# Tendência: o que subiu e o que caiu
#
# A curva geral responde "eu melhorei?". Ela não responde "melhorei EM QUÊ" —
# e é essa a pergunta que muda o que o aluno faz na segunda-feira. Aqui a
# comparação é entre dois blocos de quatro semanas, por matéria, com amostra
# mínima dos DOIS lados: sem isso, uma matéria com três questões no mês
# passado e vinte neste apareceria como "queda de 30 pontos" que é só ruído.
# ---------------------------------------------------------------------------

JANELA_TENDENCIA_SEMANAS = 4
MIN_TENDENCIA_LADO = 5


def _tendencia_por_frente(
    frente_por_semana: dict[str, Any], hoje: date
) -> list[dict[str, Any]]:
    corrente = _segunda(hoje)
    # A semana corrente entra no bloco recente: ela é o "agora" do aluno,
    # mesmo pela metade — o que a amostra mínima já protege.
    inicio_agora = corrente - timedelta(weeks=JANELA_TENDENCIA_SEMANAS - 1)
    inicio_antes = inicio_agora - timedelta(weeks=JANELA_TENDENCIA_SEMANAS)

    blocos: dict[str, dict[str, dict[str, int]]] = {}
    for chave, valor in (frente_por_semana or {}).items():
        if "|" not in chave:
            continue
        frente, semana = chave.split("|", 1)
        dia = _dia(semana)
        if dia >= inicio_agora:
            lado = "agora"
        elif dia >= inicio_antes:
            lado = "antes"
        else:
            continue
        alvo = blocos.setdefault(frente, {
            "antes": {"respondidas": 0, "acertos": 0},
            "agora": {"respondidas": 0, "acertos": 0},
        })[lado]
        alvo["respondidas"] += int(valor.get("respondidas") or 0)
        alvo["acertos"] += int(valor.get("acertos") or 0)

    linhas = []
    for frente, lados in blocos.items():
        antes, agora = lados["antes"], lados["agora"]
        if antes["respondidas"] < MIN_TENDENCIA_LADO or agora["respondidas"] < MIN_TENDENCIA_LADO:
            continue
        taxa_antes = _taxa(antes["acertos"], antes["respondidas"])
        taxa_agora = _taxa(agora["acertos"], agora["respondidas"])
        linhas.append({
            "chave": frente,
            "nome": _NOME_DA_FRENTE.get(frente, frente),
            "antes": {**antes, "taxa": taxa_antes},
            "agora": {**agora, "taxa": taxa_agora},
            "delta": round(taxa_agora - taxa_antes, 1),
        })
    # Do que mais subiu para o que mais caiu: a ordem já conta a história.
    linhas.sort(key=lambda l: -l["delta"])
    return linhas


# ---------------------------------------------------------------------------
# Pulso — o que cabe dentro de um azulejo de medida
# ---------------------------------------------------------------------------

JANELA_PULSO = 14
MIN_PULSO_LADO = 5


def _pulso(por_dia: dict[str, Any], hoje: date) -> dict[str, Any]:
    """Os últimos 14 dias de volume (a minilinha do azulejo) e a variação da
    taxa entre a última semana e a anterior.

    A variação só existe com amostra dos dois lados. Um "+18 pontos" feito de
    duas questões contra três é o tipo de número que anima o aluno hoje e o
    desmente na semana que vem."""
    dias = []
    for i in range(JANELA_PULSO - 1, -1, -1):
        chave = (hoje - timedelta(days=i)).isoformat()
        respondidas, acertos = _contagem(por_dia, chave)
        dias.append({"dia": chave, "respondidas": respondidas, "acertos": acertos})

    recente = dias[-7:]
    anterior = dias[-14:-7]
    r_r, r_a = _somar(recente)
    a_r, a_a = _somar(anterior)
    comparavel = r_r >= MIN_PULSO_LADO and a_r >= MIN_PULSO_LADO
    return {
        "dias": dias,
        "respondidas_7": r_r,
        "respondidas_7_anterior": a_r,
        "taxa_7": _taxa(r_a, r_r),
        "taxa_7_anterior": _taxa(a_a, a_r),
        "delta_taxa": round(_taxa(r_a, r_r) - _taxa(a_a, a_r), 1) if comparavel else None,
    }


# ---------------------------------------------------------------------------
# Redação — a única frente que não tem taxa de acerto, e a que mais vale
#
# 1000 pontos num componente só, e o produto já guarda cada correção com nota
# total e nota por competência (`redacao_avaliacoes`, escrito por
# `redacao_routes.submeter_redacao`). O painel ignorava esse dado inteiro.
#
# Nada aqui é inferido: a série é a nota que o corretor deu, na ordem em que
# saiu, e a leitura por competência é a média das correções do aluno com a
# amostra ao lado. `estimada` carrega a honestidade do próprio corretor —
# quando parte da nota veio de competência não confirmada, a tela diz.
# ---------------------------------------------------------------------------

REDACAO_NOTA_MAXIMA = prioridade_enem.REDACAO_NOTA_MAXIMA
COMPETENCIA_MAXIMA = 200

COMPETENCIAS_REDACAO = [
    ("COMP-I", "Norma culta", "Domínio da escrita formal"),
    ("COMP-II", "Compreensão do tema", "Entender a proposta e não fugir dela"),
    ("COMP-III", "Argumentação", "Selecionar e organizar argumentos"),
    ("COMP-IV", "Coesão", "Amarrar as partes do texto"),
    ("COMP-V", "Proposta de intervenção", "Propor solução detalhada"),
]


def _redacao(avaliacoes: list[dict[str, Any]] | None) -> dict[str, Any]:
    """`avaliacoes` são os documentos de `redacao_avaliacoes` do aluno, da
    mais antiga para a mais recente."""
    corrigidas = list(avaliacoes or [])
    validas = [a for a in corrigidas if a.get("nota_total") is not None]
    if not validas:
        # MESMAS chaves do caso com dado, com o valor ausente explícito. Um
        # bloco que muda de formato conforme o aluno tem ou não histórico faz
        # a tela ler `undefined` só para quem ainda não escreveu nada — que é
        # exatamente quem mais precisa da tela funcionando.
        return {
            "corrigidas": 0, "serie": [], "competencias": [],
            "maxima": REDACAO_NOTA_MAXIMA, "melhor": None, "ultima": None, "media": None,
        }

    serie = []
    for i, a in enumerate(validas, start=1):
        criada = str(a.get("created_at") or "")[:10]
        serie.append({
            "indice": i,
            "data": criada or None,
            "rotulo": f"{criada[8:10]}/{criada[5:7]}" if len(criada) == 10 else f"#{i}",
            "nota": int(a.get("nota_total") or 0),
            "estimados": int(a.get("nota_pontos_estimados") or 0),
            "anulada": a.get("estado_geral") == "ANULADA",
        })

    competencias = []
    for comp_id, rotulo, descricao in COMPETENCIAS_REDACAO:
        pontos = [
            int(c.get("nivel_pontos") or 0)
            for a in validas
            for c in (a.get("competencias") or [])
            if c.get("id") == comp_id
        ]
        if not pontos:
            continue
        competencias.append({
            "id": comp_id,
            "rotulo": rotulo,
            "descricao": descricao,
            "media": round(sum(pontos) / len(pontos)),
            "ultima": pontos[-1],
            "melhor": max(pontos),
            "amostra": len(pontos),
            "maxima": COMPETENCIA_MAXIMA,
        })

    notas = [s["nota"] for s in serie]
    return {
        "corrigidas": len(validas),
        "serie": serie[-12:],
        "competencias": competencias,
        "maxima": REDACAO_NOTA_MAXIMA,
        "melhor": max(notas),
        "ultima": notas[-1],
        "media": round(sum(notas) / len(notas)),
    }


# ---------------------------------------------------------------------------
# Constância
# ---------------------------------------------------------------------------


def _nivel_do_dia(respondidas: int) -> int:
    """Quatro degraus de intensidade para o calendário. Fixos, não relativos
    ao próprio aluno: uma escala que se reajusta sozinha faz o quadrado de 3
    questões acender igual ao de 30 numa semana fraca."""
    if respondidas <= 0:
        return 0
    if respondidas < 5:
        return 1
    if respondidas < 10:
        return 2
    if respondidas < 20:
        return 3
    return 4


def _constancia(por_dia: dict[str, Any], hoje: date) -> dict[str, Any]:
    ativos = {d for d, v in (por_dia or {}).items() if int(v.get("respondidas") or 0) > 0}

    # A sequência corrente ainda está viva se o aluno não estudou HOJE mas
    # estudou ontem — o dia só termina à meia-noite (mesma regra de
    # `lib/atividade.js`, para os dois números nunca discordarem).
    passo = hoje if hoje.isoformat() in ativos else hoje - timedelta(days=1)
    sequencia = 0
    while passo.isoformat() in ativos:
        sequencia += 1
        passo -= timedelta(days=1)

    melhor = atual = 0
    anterior: Optional[date] = None
    for chave in sorted(ativos):
        d = _dia(chave)
        atual = atual + 1 if anterior and (d - anterior).days == 1 else 1
        melhor = max(melhor, atual)
        anterior = d

    calendario = []
    inicio = _segunda(hoje - timedelta(days=JANELA_CALENDARIO))
    passo = inicio
    while passo <= hoje:
        chave = passo.isoformat()
        respondidas, acertos = _contagem(por_dia, chave)
        calendario.append({
            "dia": chave,
            "respondidas": respondidas,
            "acertos": acertos,
            "taxa": _taxa(acertos, respondidas),
            "nivel": _nivel_do_dia(respondidas),
            "semana": (passo - inicio).days // 7,
            "dia_semana": passo.weekday(),
        })
        passo += timedelta(days=1)

    ultimos_30 = sum(
        1 for i in range(30) if (hoje - timedelta(days=i)).isoformat() in ativos
    )
    # Consistência = em quantas das últimas 8 semanas o aluno apareceu pelo
    # menos uma vez. Não é "quantas questões": é presença. Quem estuda 20
    # questões toda semana aprende mais que quem faz 160 num domingo e some
    # por dois meses, e essa é a única medida de regularidade que dá para
    # afirmar sem inventar fórmula.
    semanas_ativas = {_segunda(_dia(d)).isoformat() for d in ativos}
    corrente = _segunda(hoje)
    janela = [(corrente - timedelta(weeks=i)).isoformat() for i in range(JANELA_CONSISTENCIA)]
    semanas_com_estudo = sum(1 for s in janela if s in semanas_ativas)

    return {
        "sequencia": sequencia,
        "melhor_sequencia": melhor,
        "dias_ativos": len(ativos),
        "dias_ativos_30": ultimos_30,
        "semanas_com_estudo": semanas_com_estudo,
        "semanas_na_janela": JANELA_CONSISTENCIA,
        "primeiro_dia": min(ativos) if ativos else None,
        "calendario": calendario,
    }


# ---------------------------------------------------------------------------
# A Mentis lendo o painel em voz alta
#
# Determinístico, grátis e sem modelo nenhum: são frases montadas a partir dos
# mesmos números que estão no gráfico ao lado. A régua é a da casa (ver
# `lib/venda.js` e `engajamento.py`):
#
#   1. nenhum número inventado — toda leitura cita a medida e a amostra;
#   2. nenhuma causa afirmada — "você acerta mais à noite" é descrição;
#      "porque você rende mais à noite" seria invenção;
#   3. nada de alarme: uma queda é dita como fato, com a saída ao lado;
#   4. toda leitura termina em algo que o aluno pode FAZER.
# ---------------------------------------------------------------------------


def _leitura(id_: str, ancora: str, tom: str, titulo: str, texto: str, acao=None) -> dict[str, Any]:
    return {"id": id_, "ancora": ancora, "tom": tom, "titulo": titulo, "texto": texto, "acao": acao}


def _acao_ir(rotulo: str, href: str) -> dict[str, Any]:
    return {"tipo": "ir", "rotulo": rotulo, "href": href}


def _acao_mentis(rotulo: str, assunto: str, evidencia: str = "") -> dict[str, Any]:
    return {"tipo": "mentis", "rotulo": rotulo, "assunto": assunto, "evidencia": evidencia}


def _leituras(
    *,
    resumo: dict[str, Any],
    comparativo: dict[str, Any],
    semanal: list[dict[str, Any]],
    frentes: list[dict[str, Any]],
    blocos: list[dict[str, Any]],
    faixas: list[dict[str, Any]],
    decisao: list[dict[str, Any]],
    constancia: dict[str, Any],
    forcas: dict[str, Any],
    tendencia: Optional[list[dict[str, Any]]] = None,
    redacao: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    leituras: list[dict[str, Any]] = []

    # 1. A mudança. É a primeira porque é a única coisa que a tela antiga não
    #    conseguia dizer de jeito nenhum.
    if comparativo.get("suficiente"):
        delta = comparativo["delta"]
        inicio = comparativo["inicio"]
        agora = comparativo["agora"]
        if delta >= 3:
            leituras.append(_leitura(
                "evolucao", "evolucao", "bom",
                f"Você subiu {abs(delta):.1f} pontos de acerto",
                f"Nas suas primeiras {inicio['respondidas']} respostas você acertava "
                f"{inicio['taxa']:.0f}%. Nas {agora['respondidas']} mais recentes, "
                f"{agora['taxa']:.0f}%. Isso é a sua curva, medida — não é estimativa minha.",
                _acao_ir("Continuar praticando", "/exams"),
            ))
        elif delta <= -3:
            leituras.append(_leitura(
                "evolucao", "evolucao", "atencao",
                f"Sua taxa caiu {abs(delta):.1f} pontos",
                f"Você acertava {inicio['taxa']:.0f}% nas primeiras {inicio['respondidas']} "
                f"respostas e está em {agora['taxa']:.0f}% nas {agora['respondidas']} últimas. "
                "Cair depois de avançar de assunto é comum — o que muda o número de volta é "
                "revisar o que ficou para trás.",
                _acao_ir("Ver minhas revisões", "/revisoes"),
            ))
        else:
            leituras.append(_leitura(
                "evolucao", "evolucao", "neutro",
                "Sua taxa está estável",
                f"{inicio['taxa']:.0f}% no começo, {agora['taxa']:.0f}% agora, em "
                f"{resumo['respondidas']} respostas. Estável com volume subindo é bom sinal: "
                "você está acertando o mesmo em questão mais difícil.",
                _acao_ir("Praticar agora", "/exams"),
            ))

    # 1b. Em QUÊ mudou. A curva geral diz que subiu; esta diz onde, e é essa
    #     que muda o que o aluno faz na segunda-feira.
    subiu = [t for t in (tendencia or []) if t["delta"] >= 5]
    caiu = [t for t in (tendencia or []) if t["delta"] <= -5]
    if subiu:
        alvo = subiu[0]
        leituras.append(_leitura(
            "tendencia", "tendencia", "bom",
            f"{alvo['nome']} subiu {abs(alvo['delta']):.0f} pontos",
            f"Nas quatro semanas anteriores você acertava {alvo['antes']['taxa']:.0f}% em "
            f"{alvo['antes']['respondidas']} questões dessa matéria; nas quatro últimas, "
            f"{alvo['agora']['taxa']:.0f}% em {alvo['agora']['respondidas']}. "
            "O que você fez ali funcionou — vale repetir o método na próxima.",
            None,
        ))
    elif caiu:
        alvo = caiu[-1]
        leituras.append(_leitura(
            "tendencia", "tendencia", "atencao",
            f"{alvo['nome']} recuou {abs(alvo['delta']):.0f} pontos",
            f"De {alvo['antes']['taxa']:.0f}% ({alvo['antes']['respondidas']} questões) para "
            f"{alvo['agora']['taxa']:.0f}% ({alvo['agora']['respondidas']}) nas últimas quatro "
            "semanas. Costuma ser assunto novo dentro da mesma matéria, não conteúdo perdido.",
            _acao_ir(f"Praticar {alvo['nome']}", "/exams"),
        ))

    # 2. Onde a próxima hora rende mais. Mesma fonte que o cronograma e o
    #    Painel usam — a tela não pode responder isto com critério próprio.
    topo = frentes[0] if frentes else None
    if topo:
        leituras.append(_leitura(
            "prioridade", "prioridade", "atencao",
            f"{topo['nome']} é onde a sua próxima hora rende mais",
            topo.get("porque") or "",
            _acao_ir(f"Praticar {topo['nome']}", topo.get("rota") or "/exams"),
        ))

    # 2b. Redação. Mil pontos num componente só: o painel não pode passar por
    #     ela em silêncio, tenha o aluno corrigido alguma ou nenhuma.
    if redacao and redacao.get("corrigidas"):
        fracas = sorted(
            (c for c in redacao.get("competencias") or []),
            key=lambda c: c["media"],
        )
        pior = fracas[0] if fracas else None
        leituras.append(_leitura(
            "redacao", "redacao", "neutro",
            f"Sua melhor redação deu {redacao['melhor']} de 1000",
            f"Em {redacao['corrigidas']} correção(ões), a sua média está em {redacao['media']}."
            + (
                f" A competência que mais segura a sua nota é {pior['rotulo'].lower()}: "
                f"{pior['media']} de {pior['maxima']} em média."
                if pior else ""
            ),
            _acao_ir("Escrever outra redação", "/redacao"),
        ))
    elif redacao is not None and not redacao.get("corrigidas"):
        leituras.append(_leitura(
            "redacao", "redacao", "atencao",
            "Você ainda não corrigiu nenhuma redação aqui",
            "A redação vale 1000 pontos sozinha e é a nota que mais sobe com treino. É também a "
            "única parte da prova em que eu não tenho nada medido sobre você.",
            _acao_ir("Corrigir uma redação", "/redacao"),
        ))

    # 3. Horário. Só fala quando os dois blocos comparados têm amostra.
    confiaveis = [b for b in blocos if b["confiavel"] and b["taxa"] is not None]
    if len(confiaveis) >= 2:
        melhor = max(confiaveis, key=lambda b: b["taxa"])
        pior = min(confiaveis, key=lambda b: b["taxa"])
        diferenca = round(melhor["taxa"] - pior["taxa"], 1)
        if diferenca >= 8:
            leituras.append(_leitura(
                "horario", "ritmo", "neutro",
                f"Você acerta mais de {melhor['rotulo'].lower()}",
                f"{melhor['rotulo']} ({melhor['faixa']}): {melhor['taxa']:.0f}% em "
                f"{melhor['respondidas']} questões. {pior['rotulo']} ({pior['faixa']}): "
                f"{pior['taxa']:.0f}% em {pior['respondidas']}. São {diferenca:.0f} pontos de "
                "diferença — vale marcar o estudo pesado no horário em que você já vai melhor.",
                _acao_ir("Montar minha semana", "/cronograma"),
            ))

    # 4. Pressa. A leitura mais acionável que existe numa prova cronometrada.
    rapido = next((f for f in faixas if f["chave"] == "rapido"), None)
    longo = next((f for f in faixas if f["chave"] == "longo"), None)
    if rapido and longo and rapido["confiavel"] and longo["confiavel"]:
        diferenca = round((longo["taxa"] or 0) - (rapido["taxa"] or 0), 1)
        if diferenca >= 10:
            leituras.append(_leitura(
                "pressa", "tempo", "atencao",
                "A pressa está te custando questão",
                f"Quando você responde em menos de {_minutos(_RAPIDO)}, acerta "
                f"{rapido['taxa']:.0f}% ({rapido['respondidas']} questões). Quando passa de "
                f"{_minutos(_LONGO)}, "
                f"{longo['taxa']:.0f}% ({longo['respondidas']}). A questão que você lê duas "
                "vezes é a que você leva.",
                _acao_mentis(
                    "Como não cair na pressa",
                    "responder rápido demais",
                    f"acerto {rapido['taxa']:.0f}% quando respondo em menos de {_minutos(_RAPIDO)}",
                ),
            ))
        elif diferenca <= -10:
            leituras.append(_leitura(
                "pressa", "tempo", "neutro",
                "Você vai bem no automático",
                f"Menos de {_minutos(_RAPIDO)}: {rapido['taxa']:.0f}% de acerto em "
                f"{rapido['respondidas']} questões. Mais de {_minutos(_LONGO)}: "
                f"{longo['taxa']:.0f}% em "
                f"{longo['respondidas']}. Travar muito tempo numa questão costuma ser sinal de "
                "conteúdo faltando, não de falta de atenção.",
                _acao_ir("Ver onde focar", "/treino"),
            ))

    # 5. Mudar de resposta.
    manteve = next((d for d in decisao if d["chave"] == "manteve"), None)
    mudou = next((d for d in decisao if d["chave"] == "mudou"), None)
    if manteve and mudou and manteve["confiavel"] and mudou["confiavel"]:
        diferenca = round((manteve["taxa"] or 0) - (mudou["taxa"] or 0), 1)
        if abs(diferenca) >= 8:
            melhor_manter = diferenca > 0
            leituras.append(_leitura(
                "decisao", "habitos", "neutro",
                "Mudar de resposta: o seu número" if melhor_manter else "Você faz bem em repensar",
                (
                    f"Quando você mantém a primeira resposta, acerta {manteve['taxa']:.0f}% "
                    f"({manteve['respondidas']} questões). Quando muda, {mudou['taxa']:.0f}% "
                    f"({mudou['respondidas']}). "
                    + (
                        "Não é regra universal — é o seu histórico. Na dúvida sem motivo novo, "
                        "a sua primeira leitura tem ido melhor."
                        if melhor_manter else
                        "Ou seja: quando você volta numa questão e muda, costuma ser por um bom "
                        "motivo. Confie na revisão."
                    )
                ),
                None,
            ))

    # 6. Constância — sem contador regressivo e sem culpa.
    if constancia["dias_ativos_30"] > 0:
        leituras.append(_leitura(
            "constancia", "constancia",
            "bom" if constancia["dias_ativos_30"] >= 12 else "neutro",
            f"{constancia['dias_ativos_30']} dias de estudo nos últimos 30",
            (
                f"Sua maior sequência foi de {constancia['melhor_sequencia']} dias seguidos"
                + (
                    f", e a atual está em {constancia['sequencia']}."
                    if constancia["sequencia"] else "."
                )
                + f" Você apareceu em {constancia['semanas_com_estudo']} das últimas "
                f"{constancia['semanas_na_janela']} semanas."
                + " Frequência move mais nota do que maratona: dez minutos hoje contam mais "
                "que três horas no domingo."
            ),
            _acao_ir("Ver meu cronograma", "/cronograma"),
        ))

    # 7. A frente nunca medida. É o buraco que o aluno não vê sozinho.
    nunca = [f for f in frentes if f.get("estado") == "sem_medida" and f["chave"] != "redacao"]
    if nunca:
        alvo = nunca[0]
        leituras.append(_leitura(
            "lacuna", "frentes", "atencao",
            f"Eu ainda não sei como você vai em {alvo['nome']}",
            f"Você respondeu {alvo['respondidas']} questões de {alvo['nome']} por aqui — abaixo "
            f"de {prioridade_enem.AMOSTRA_MINIMA} eu não afirmo nada. Umas poucas questões e eu "
            "troco o palpite por medida.",
            _acao_ir(f"Responder {alvo['nome']}", alvo.get("rota") or "/exams"),
        ))

    # 8. Força e ponto a desenvolver, nas palavras que o aluno pode ler — sem
    #    número ao lado, porque aqui a fonte é a ontologia (ver o cabeçalho).
    forte = (forcas.get("pontos_fortes") or [None])[0]
    if forte:
        leituras.append(_leitura(
            "forca", "forcas", "bom",
            f"O seu ponto mais firme: {forte['rotulo'].lower()}",
            forte["explicacao"],
            None,
        ))
    fraco = (forcas.get("pontos_a_desenvolver") or [None])[0]
    if fraco:
        leituras.append(_leitura(
            "desenvolver", "forcas", "atencao",
            f"O que mais vale destravar: {fraco['rotulo'].lower()}",
            fraco["explicacao"],
            _acao_mentis("Me explica isso", fraco["rotulo"]),
        ))

    # 9. Volume da semana — a leitura que faz a tela valer a visita de segunda.
    if len(semanal) >= 2:
        atual, passada = semanal[-1], semanal[-2]
        if atual["respondidas"] or passada["respondidas"]:
            leituras.append(_leitura(
                "semana", "volume", "neutro",
                f"{atual['respondidas']} questões esta semana",
                f"Na semana passada foram {passada['respondidas']}. "
                + (
                    "Você está com mais volume que na semana anterior."
                    if atual["respondidas"] > passada["respondidas"]
                    else "A semana ainda não fechou — dá tempo de virar o número."
                ),
                _acao_ir("Praticar agora", "/exams"),
            ))
    return leituras


# ---------------------------------------------------------------------------
# Montagem
# ---------------------------------------------------------------------------


def montar(
    *,
    telemetria: dict[str, Any],
    prioridades: list[dict[str, Any]],
    forcas: dict[str, Any],
    diagnostico: Optional[dict[str, Any]] = None,
    avaliacoes_redacao: Optional[list[dict[str, Any]]] = None,
    hoje: Optional[date] = None,
) -> dict[str, Any]:
    """O painel inteiro, pronto para desenhar. Função pura: nada aqui lê banco.

    `telemetria` vem de `annotation_service.telemetria_de`, `prioridades` de
    `prioridade_enem.ranking`, `avaliacoes_redacao` de `redacao_avaliacoes` no
    Mongo (da mais antiga para a mais nova) e `forcas` de `perfil_pedagogico`
    — que é a única peça cujos textos nascem da ontologia, e por isso a única
    que entra sem número nenhum.
    """
    hoje = hoje or date.today()
    telemetria = telemetria or {}
    por_dia = telemetria.get("por_dia") or {}

    origens = _por_origem(telemetria)
    respondidas, acertos = _somar(
        [{"respondidas": o["respondidas"], "acertos": o["acertos"]} for o in origens]
    )

    tempo_total = float(telemetria.get("tempo_total_segundos") or 0)
    com_tempo = int(telemetria.get("respostas_com_tempo") or 0)

    constancia = _constancia(por_dia, hoje)
    semanal = _serie_semanal(por_dia, hoje)
    comparativo = _comparativo(por_dia)
    blocos = _blocos_do_dia(telemetria)
    faixas = _por_faixa_de_tempo(telemetria)
    decisao = _decisao(telemetria)
    pulso = _pulso(por_dia, hoje)
    tendencia = _tendencia_por_frente(telemetria.get("frente_por_semana") or {}, hoje)
    redacao = _redacao(avaliacoes_redacao)

    # A lista de frentes que a tela desenha: a de rendimento, na ordem dela.
    # A Redação entra junto de propósito — ela não tem taxa de acerto, e um
    # painel de desempenho que a omite ensina o aluno a esquecer 1000 pontos.
    frentes = list(prioridades or [])
    medidas = [f for f in frentes if f.get("respondidas")]

    resumo = {
        "respondidas": respondidas,
        "acertos": acertos,
        "taxa": _taxa(acertos, respondidas),
        "tempo_total_minutos": int(round(tempo_total / 60)) if com_tempo else 0,
        "tempo_medio_segundos": int(round(tempo_total / com_tempo)) if com_tempo else None,
        "respostas_com_tempo": com_tempo,
        "dias_ativos": constancia["dias_ativos"],
        "sequencia": constancia["sequencia"],
        "melhor_sequencia": constancia["melhor_sequencia"],
        "primeiro_dia": constancia["primeiro_dia"],
        "frentes_medidas": len(medidas),
        "frentes_totais": len(frentes),
        "pulso": pulso,
    }

    leituras = _leituras(
        resumo=resumo,
        comparativo=comparativo,
        semanal=semanal,
        frentes=frentes,
        blocos=blocos,
        faixas=faixas,
        decisao=decisao,
        constancia=constancia,
        forcas=forcas or {},
        tendencia=tendencia,
        redacao=redacao,
    )

    return {
        "amostra_insuficiente": respondidas < MIN_PARA_PAINEL,
        "minimo_para_painel": MIN_PARA_PAINEL,
        "resumo": resumo,
        "evolucao": {
            "diaria": _serie_diaria(por_dia, hoje),
            "semanal": semanal,
            "comparativo": comparativo,
            "por_frente": _evolucao_por_frente(
                telemetria.get("frente_por_semana") or {}, hoje
            ),
        },
        "frentes": {
            "linhas": frentes,
            "tendencia": tendencia,
            "amostra_minima": prioridade_enem.AMOSTRA_MINIMA,
            "amostra_plena": prioridade_enem.AMOSTRA_PLENA,
            "janela_tendencia_semanas": JANELA_TENDENCIA_SEMANAS,
        },
        "redacao": redacao,
        "ritmo": {
            "por_hora": _por_hora(telemetria),
            "blocos": blocos,
            "por_dia_semana": _por_dia_semana(telemetria),
            "por_faixa_de_tempo": faixas,
        },
        "habitos": {"decisao": decisao, "origem": origens},
        "constancia": constancia,
        "forcas": forcas or {"pontos_fortes": [], "pontos_a_desenvolver": []},
        "mentis": {"leituras": leituras},
        "cobertura": {
            # Quantas das respostas do aluno o catálogo anotado alcança. É
            # honestidade de amostra, não métrica de produto: sem isso o aluno
            # não tem como saber que o gráfico de matérias descreve parte do
            # que ele respondeu.
            "eventos": int((diagnostico or {}).get("total_events") or 0),
            "com_anotacao": int((diagnostico or {}).get("matched_events") or 0),
        },
    }
