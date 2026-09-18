"""Estado de revisão do aluno — o eixo do TEMPO sobre a fila que o motor já produz.

**Zero IA e zero I/O.** Este módulo é uma função pura sobre um dicionário: recebe
o bloco `students/{uid}.revisao`, devolve o bloco novo. Quem lê e escreve é
`revisao_service`; quem interpreta o erro continua sendo `motor_cognitivo`.

Por que este módulo existe
--------------------------
`motor_cognitivo._priorizar()` já responde "o que este aluno deve melhorar", com
a raiz separada da manifestação e o peso de confiança calibrado. O que faltava
não era a fila — era saber QUANDO voltar a cada item dela, e se a volta
funcionou. O produto observava e não retestava: o traço era produzido, agregado,
exibido, e nada no sistema perguntava depois se a intervenção pegou.

Três estados que antes não existiam, e a definição operacional de cada um:

    em consolidação   raiz recente, reteste agendado e ainda não vencido.
    erro recorrente   >= MIN_TRACOS_RAIZ raízes do mesmo par (erro, processo)
                      em DIAS distintos (ver `_recorrente`).
    em deterioração   acerto da janela recente abaixo do da janela anterior,
                      com as duas janelas grandes o bastante para comparar.

O que este módulo NÃO faz (e por quê)
-------------------------------------
* **Não agenda por manifestação.** Só o elo `ordem: 1` colapsa o intervalo.
  Tratar manifestação de superfície como causa é o defeito que o Error Trace
  §1.1 existe para impedir, e agendar reteste por ela seria fazer exatamente
  isso com um calendário em cima.
* **Não inventa vínculo Erro→Processo** (R-1). O par já chega validado contra o
  catálogo por `motor_cognitivo._validar_cadeia`; aqui ele é só uma chave.
* **Não determiniza causa** (R-3). `provisorio` acompanha cada raiz e sobe para
  a fila inteira: enquanto o portão de crença estiver desligado, o que sai
  daqui é hipótese, e a tela é obrigada a dizer isso.
* **Não usa mecanismo (`MEC-*`)** para escolher nem exibir nada (§4.2).

Custo
-----
Todo o estado cabe num bloco de tamanho LIMITADO dentro do documento que o app
já lê e escreve (`students/{uid}`): listas com teto declarado (`_MAX_*`), nada
de histórico. A conta de leitura fica em O(1) por requisição — a regra escrita
em sangue depois de 2026-09-04, quando um laço O(eventos) esgotou a cota diária
do Firestore e derrubou toda rota autenticada.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable, Optional

VERSAO_BLOCO = 1

# ---------------------------------------------------------------------------
# Grandezas declaradas
# ---------------------------------------------------------------------------

# A escada do espaçamento. Cresce a cada reteste ACERTADO e colapsa para o
# primeiro degrau a cada raiz nova do mesmo par — que é a única forma honesta
# de espaçar: o intervalo é uma aposta sobre retenção, e errar de novo é a
# evidência de que a aposta estava errada.
INTERVALOS_DIAS = (1, 3, 7, 16, 35)

# Janela = bloco de respostas ao MESMO processo. Contada em respostas, não em
# dias, porque a comparação entre janelas só significa alguma coisa com
# denominadores parecidos — um aluno que responde 30 questões numa terça e 2
# na quarta não "deteriorou" na quarta.
JANELA_TAMANHO = 8
JANELA_MINIMA = 4

# Uma queda pequena entre janelas é ruído amostral, não deterioração. 15 pontos
# percentuais sobre janelas de 4 a 8 respostas é a menor diferença que não se
# explica por uma questão a mais ou a menos.
QUEDA_MINIMA = 0.15

# "Antes estável": só cai quem estava de pé. Sem este piso, todo processo ruim
# ficaria permanentemente "em deterioração", que é o mesmo que não ter estado.
ESTAVEL_MINIMO = 0.70

# A escada acima é igual pra todo aluno — o que é individual é o ESTADO por
# processo, não o RITMO dela. Este fator corrige isso: um aluno cujos
# retestes falham muito tem a escada comprimida (volta mais cedo); um cujos
# retestes raramente falham tem a escada esticada (não desperdiça revisão em
# quem já consolidou). Amostra mínima evita ajustar o ritmo de um aluno novo
# com 1 ou 2 retestes — puro ruído.
FATOR_MIN_AMOSTRA = 6
FATOR_MIN = 0.6
FATOR_MAX = 1.4
# 50% de acerto nos retestes -> 0.7x (mais curto); 90%+ -> 1.3x (mais longo).
_FATOR_BASE = 0.7
_FATOR_INCLINACAO = 1.5
_FATOR_TAXA_REFERENCIA = 0.5

# Teto de intervenções concorrentes (não mais 1): represar um processo B com
# evidência nova só porque A ainda não fechou também deixa de individualizar
# — B fica sem reteste agendado até A ser resolvido, às vezes nunca. O piso
# continua o mesmo: nunca duas vezes o MESMO par, e cooldown por par intacto.
_MAX_INTERVENCOES_ATIVAS = 2

# Mesmo limiar de evidência do motor. Um limiar novo aqui criaria duas noções
# divergentes de "evidência suficiente" dentro do mesmo produto.
from motor_cognitivo import MIN_TRACOS_RAIZ, SENTINELAS  # noqa: E402

# Tetos de tamanho. O documento `students/{uid}` já carrega
# `agregado.item_ids_respondidos` como ArrayUnion sem teto; acrescentar blocos
# que crescem sem limite aproxima o limite de 1 MB do Firestore, e um documento
# estourado não degrada — para de aceitar escrita.
_MAX_RAIZES = 8
_MAX_MARCOS = 12
_MAX_CONTEXTOS = 6
_MAX_PROCESSOS = 40

# Quantas linhas a fila diária entrega. Fechada e curta de propósito: uma lista
# de 40 habilidades não é uma fila, é o mesmo painel com outro nome.
FILA_TAMANHO = 8

ESTADO_CONSOLIDACAO = "em_consolidacao"
ESTADO_RECORRENTE = "erro_recorrente"
ESTADO_DETERIORACAO = "em_deterioracao"
ESTADO_ESTAVEL = "estavel"
ESTADO_SEM_SINAL = "sem_sinal"

GATILHO_RECORRENCIA = "recorrencia"
GATILHO_DETERIORACAO = "deterioracao"
GATILHO_RETESTE_FALHO = "reteste_falho"

MARCO_RAIZ = "raiz"
MARCO_INTERVENCAO = "intervencao"
MARCO_RETESTE_OK = "reteste_ok"
MARCO_RETESTE_FALHO = "reteste_falho"
MARCO_TRANSFERENCIA = "transferencia"


# ---------------------------------------------------------------------------
# Estruturas
# ---------------------------------------------------------------------------


def bloco_vazio() -> dict[str, Any]:
    return {
        "versao": VERSAO_BLOCO,
        "processos": {},
        # `processo_id -> intervenção ativa`. Teto em `_MAX_INTERVENCOES_ATIVAS`
        # — sem teto nenhum, o "Professor Invisível" vira pop-up.
        "intervencoes_ativas": {},
        # `par -> dia` até o qual aquele par não volta a disparar.
        "cooldowns": {},
        "atualizado_em": None,
    }


def _entrada_vazia() -> dict[str, Any]:
    return {
        "janela_atual": {"respondidas": 0, "acertos": 0, "inicio": None},
        "janela_anterior": {"respondidas": 0, "acertos": 0, "inicio": None},
        "raizes_recentes": [],
        "pesos_raiz": {},
        "proximo_reteste": None,
        "degrau": 0,
        "ultimo_reteste": None,
        "retestes": {"total": 0, "acertos": 0},
        "transferencias": {"total": 0, "acertos": 0},
        "contextos_da_raiz": [],
        "marcos": [],
        "dispensas": 0,
        "ultima_atividade": None,
        "provisorio": False,
    }


def par(erro_id: str, processo_id: str) -> str:
    return f"{erro_id}|{processo_id}"


def _entrada(bloco: dict, processo_id: str) -> dict[str, Any]:
    return (bloco.get("processos") or {}).get(processo_id) or _entrada_vazia()


def _somar_dias(dia: str, dias: int) -> str:
    return (date.fromisoformat(dia) + timedelta(days=dias)).isoformat()


def _limitar(lista: list, teto: int) -> list:
    """Descarta o mais antigo. A ordem de chegada é a ordem da lista."""
    return lista[-teto:] if len(lista) > teto else lista


def _fator_individual(bloco: dict[str, Any]) -> float:
    """O ritmo da escada PARA ESTE ALUNO — 1.0 até haver amostra.

    Soma os retestes de TODOS os processos porque a pergunta não é "este
    processo específico" (isso já é o que `degrau` resolve) — é "de modo
    geral, quando marco um reteste para este aluno, ele volta a acertar?".
    Recalculado a cada resposta, sem custo de leitura: já está no bloco.
    """
    tot = ok = 0
    for e in (bloco.get("processos") or {}).values():
        r = e.get("retestes") or {}
        tot += r.get("total") or 0
        ok += r.get("acertos") or 0
    if tot < FATOR_MIN_AMOSTRA:
        return 1.0
    taxa = ok / tot
    fator = _FATOR_BASE + (taxa - _FATOR_TAXA_REFERENCIA) * _FATOR_INCLINACAO
    return max(FATOR_MIN, min(FATOR_MAX, fator))


# ---------------------------------------------------------------------------
# Escrita — o que uma resposta faz com o estado
# ---------------------------------------------------------------------------


def registrar(
    bloco: dict[str, Any] | None,
    *,
    processos: Iterable[str],
    acertou: bool,
    dia: str,
    quando: str,
    raiz: Optional[dict[str, Any]] = None,
    contexto: Optional[str] = None,
) -> dict[str, Any]:
    """O efeito de UMA resposta sobre o estado de revisão. Devolve o bloco novo.

    `processos`   — os processos que o ITEM exercita (`estrutura_cognitiva`).
                    Alimentam as janelas de desempenho, que existem
                    independentemente de haver cadeia anotada.
    `raiz`        — `{erro, processo, confianca, provisorio}` do elo `ordem: 1`,
                    ou `None`. **Só a raiz agenda**: o chamador é responsável
                    por nunca passar aqui um elo de ordem >= 2 (§1.1).
    `contexto`    — chave curta do contexto do item (domínio/tema). É o que
                    permite distinguir "acertou de novo" de "acertou noutro
                    lugar", que é a única evidência de transferência que o
                    acervo sustenta hoje.

    Idempotência: NÃO é idempotente por design, e não deve ser — cada resposta
    é uma tentativa real, igual ao que `increment_treino_stats` já assume.
    """
    novo = _clonar(bloco)
    entradas = novo["processos"]
    # Calculado UMA vez por resposta, sobre o estado anterior — a mesma
    # leitura que `registrar` já pagou, sem I/O adicional.
    fator = _fator_individual(novo)

    for pid in dict.fromkeys(p for p in processos if p):
        e = dict(entradas.get(pid) or _entrada_vazia())
        e["ultima_atividade"] = quando

        # 1) Reteste vencido? Isto tem de acontecer ANTES de a raiz nova
        #    colapsar o intervalo: a resposta que falha o reteste é a mesma
        #    que produz a raiz nova, e contar só o colapso apagaria a
        #    evidência de que o reteste foi cobrado e não passou.
        e = _consumir_reteste(e, acertou=acertou, dia=dia, quando=quando, contexto=contexto, fator=fator)

        # 2) Janelas de desempenho.
        e = _acumular_janela(e, acertou=acertou, dia=dia)

        # 3) Transferência: acerto do MESMO processo num contexto que não é o
        #    da raiz. Instrumentação do §12 — é o número que diz se o ciclo
        #    ensinou a habilidade ou apenas o item.
        if contexto and e["contextos_da_raiz"] and contexto not in e["contextos_da_raiz"]:
            e["transferencias"] = {
                "total": e["transferencias"]["total"] + 1,
                "acertos": e["transferencias"]["acertos"] + (1 if acertou else 0),
            }
            if acertou:
                e = _marco(e, MARCO_TRANSFERENCIA, quando)

        entradas[pid] = e

    if raiz:
        pid = raiz.get("processo")
        if pid:
            entradas[pid] = _registrar_raiz(
                dict(entradas.get(pid) or _entrada_vazia()),
                raiz=raiz,
                dia=dia,
                quando=quando,
                contexto=contexto,
            )

    novo["processos"] = _podar_processos(entradas)
    novo["atualizado_em"] = quando
    return novo


def _clonar(bloco: dict[str, Any] | None) -> dict[str, Any]:
    base = bloco_vazio()
    if not isinstance(bloco, dict):
        return base
    return {
        **base,
        **{k: v for k, v in bloco.items() if k not in ("processos", "intervencao_ativa")},
        "versao": VERSAO_BLOCO,
        "processos": {
            pid: {**_entrada_vazia(), **e}
            for pid, e in (bloco.get("processos") or {}).items()
            if isinstance(e, dict)
        },
        "cooldowns": dict(bloco.get("cooldowns") or {}),
        # `intervencao_ativa` (singular) é o nome do campo em documentos
        # gravados antes desta mudança — ignorado de propósito (ver acima):
        # a pior consequência de não migrá-lo é uma vaga que já estava presa
        # se libertar mais cedo, nunca duas intervenções fantasmas.
        "intervencoes_ativas": dict(bloco.get("intervencoes_ativas") or {}),
    }


def _acumular_janela(e: dict, *, acertou: bool, dia: str) -> dict:
    atual = dict(e["janela_atual"])
    if not atual.get("inicio"):
        atual["inicio"] = dia
    atual["respondidas"] += 1
    atual["acertos"] += 1 if acertou else 0
    if atual["respondidas"] >= JANELA_TAMANHO:
        # Rotaciona: a cheia vira "anterior", e a próxima resposta abre a nova.
        return {**e, "janela_anterior": atual, "janela_atual": {"respondidas": 0, "acertos": 0, "inicio": None}}
    return {**e, "janela_atual": atual}


def _consumir_reteste(
    e: dict, *, acertou: bool, dia: str, quando: str, contexto: str | None, fator: float = 1.0
) -> dict:
    """Esta resposta É o reteste agendado? Só quando há agendamento vencido.

    `degrau` sobe com acerto e **fica parado** com erro. Não recua de propósito:
    recuar puniria duas vezes o mesmo erro (colapso do intervalo pela raiz nova
    + perda do degrau) e transformaria um tropeço numa regressão ao início.

    `fator` só se aplica ao caminho de ACERTO — o colapso de erro (abaixo,
    quando `acertou` é falso) é uma medida de segurança, não uma aposta sobre
    retenção, e não faz sentido esticá-la para o aluno "fácil".
    """
    marcado = e.get("proximo_reteste")
    if not marcado or dia < marcado:
        return e

    retestes = {
        "total": e["retestes"]["total"] + 1,
        "acertos": e["retestes"]["acertos"] + (1 if acertou else 0),
    }
    degrau = min(e.get("degrau", 0) + 1, len(INTERVALOS_DIAS) - 1) if acertou else e.get("degrau", 0)
    e = {
        **e,
        "retestes": retestes,
        "degrau": degrau,
        "ultimo_reteste": {
            "ts": quando,
            "acertou": bool(acertou),
            # Reteste noutro contexto é o teste que interessa: mede a
            # habilidade, não a memória daquele item.
            "transferencia": bool(contexto and e["contextos_da_raiz"] and contexto not in e["contextos_da_raiz"]),
        },
        # Acertou: reagenda mais longe, escalado pelo ritmo deste aluno. Errou:
        # o próximo reteste é o primeiro degrau de novo (sem fator), e a raiz
        # nova (se houver) o confirma logo abaixo.
        "proximo_reteste": _somar_dias(
            dia, max(1, round(INTERVALOS_DIAS[degrau] * fator)) if acertou else INTERVALOS_DIAS[0]
        ),
    }
    return _marco(e, MARCO_RETESTE_OK if acertou else MARCO_RETESTE_FALHO, quando)


def _registrar_raiz(e: dict, *, raiz: dict, dia: str, quando: str, contexto: str | None) -> dict:
    """Uma raiz nova: registra a ocorrência e COLAPSA o intervalo para o mínimo.

    O colapso é a regra central do espaçamento adaptativo — e é o que separa
    isto de Anki: o intervalo não cai porque o aluno apertou "difícil", cai
    porque o sistema sabe qual raiz voltou a aparecer.
    """
    erro_id = raiz.get("erro")
    confianca = float(raiz.get("confianca") or 0.0)
    pesos = dict(e.get("pesos_raiz") or {})
    pesos[erro_id] = round(pesos.get(erro_id, 0.0) + confianca, 3)

    raizes = list(e.get("raizes_recentes") or [])
    raizes.append({"erro": erro_id, "dia": dia, "ts": quando, "provisorio": bool(raiz.get("provisorio"))})

    contextos = list(e.get("contextos_da_raiz") or [])
    if contexto and contexto not in contextos:
        contextos.append(contexto)

    e = {
        **e,
        "pesos_raiz": pesos,
        "raizes_recentes": _limitar(raizes, _MAX_RAIZES),
        "contextos_da_raiz": _limitar(contextos, _MAX_CONTEXTOS),
        "degrau": 0,
        "proximo_reteste": _somar_dias(dia, INTERVALOS_DIAS[0]),
        "ultima_atividade": quando,
        "provisorio": bool(e.get("provisorio")) or bool(raiz.get("provisorio")),
    }
    return _marco(e, MARCO_RAIZ, quando, erro=erro_id)


def _marco(e: dict, tipo: str, quando: str, **extra) -> dict:
    """Log de MARCOS, não de respostas.

    A trajetória (Fase 4) é derivada daqui. Um registro por marco — e marcos
    são raros por definição —, o que mantém o documento pequeno sem precisar de
    uma segunda coleção nem de uma varredura.
    """
    marcos = list(e.get("marcos") or [])
    marcos.append({"tipo": tipo, "ts": quando, **{k: v for k, v in extra.items() if v}})
    return {**e, "marcos": _limitar(marcos, _MAX_MARCOS)}


def _podar_processos(entradas: dict[str, dict]) -> dict[str, dict]:
    """Teto de processos acompanhados. A ontologia vigente tem 25 processos, o
    que já cabe — o teto existe para o dia em que ela crescer, não para hoje.
    Sai primeiro quem não tem reteste pendente e está parado há mais tempo."""
    if len(entradas) <= _MAX_PROCESSOS:
        return entradas
    ordenadas = sorted(
        entradas.items(),
        key=lambda kv: (bool(kv[1].get("proximo_reteste")), kv[1].get("ultima_atividade") or ""),
        reverse=True,
    )
    return dict(ordenadas[:_MAX_PROCESSOS])


# ---------------------------------------------------------------------------
# Leitura — estados, fila, trajetória
# ---------------------------------------------------------------------------


def _taxa(janela: dict) -> float | None:
    n = janela.get("respondidas") or 0
    return (janela.get("acertos") or 0) / n if n else None


def _recorrente(e: dict) -> dict | None:
    """O par (erro, processo) que reincidiu. `None` quando nenhum reincidiu.

    "Janelas distintas" da proposta é lido aqui como **dias distintos**: duas
    marcações do mesmo distrator na mesma sessão, cinco minutos uma da outra,
    são um lapso — não um padrão. Exigir o retorno noutro dia é o que separa
    as duas coisas com o dado que existe.
    """
    por_erro: dict[str, list[str]] = {}
    for r in e.get("raizes_recentes") or []:
        por_erro.setdefault(r.get("erro"), []).append(r.get("dia"))
    melhor = None
    for erro_id, dias in por_erro.items():
        if len(dias) < MIN_TRACOS_RAIZ or len({d for d in dias if d}) < 2:
            continue
        peso = (e.get("pesos_raiz") or {}).get(erro_id, 0.0)
        if melhor is None or peso > melhor["peso"]:
            melhor = {"erro": erro_id, "ocorrencias": len(dias), "dias": len(set(dias)), "peso": peso}
    return melhor


def _deteriorou(e: dict) -> dict | None:
    """Queda de janela para janela, sobre amostras comparáveis."""
    ant, atu = e.get("janela_anterior") or {}, e.get("janela_atual") or {}
    if (ant.get("respondidas") or 0) < JANELA_MINIMA or (atu.get("respondidas") or 0) < JANELA_MINIMA:
        return None
    t_ant, t_atu = _taxa(ant), _taxa(atu)
    if t_ant is None or t_atu is None or t_ant < ESTAVEL_MINIMO:
        return None
    if (t_ant - t_atu) < QUEDA_MINIMA:
        return None
    return {"antes": round(100 * t_ant, 1), "agora": round(100 * t_atu, 1)}


def estado(e: dict, hoje: str) -> str:
    """O estado de UM processo. A ordem das perguntas é a ordem de urgência."""
    if _recorrente(e):
        return ESTADO_RECORRENTE
    if _deteriorou(e):
        return ESTADO_DETERIORACAO
    marcado = e.get("proximo_reteste")
    if marcado and hoje < marcado:
        return ESTADO_CONSOLIDACAO
    if marcado and hoje >= marcado:
        # Reteste vencido é trabalho de hoje, não estabilidade.
        return ESTADO_CONSOLIDACAO
    if (e.get("janela_atual", {}).get("respondidas") or 0) or (e.get("janela_anterior", {}).get("respondidas") or 0):
        return ESTADO_ESTAVEL
    return ESTADO_SEM_SINAL


# A fila entrega os estados nesta ordem. Recorrência primeiro porque é a
# evidência mais forte que o produto tem; sentinela por último porque não há o
# que prescrever — mesma disciplina de `motor_cognitivo._priorizar`.
_ORDEM_ESTADO = {
    ESTADO_RECORRENTE: 0,
    ESTADO_DETERIORACAO: 1,
    ESTADO_CONSOLIDACAO: 2,
    ESTADO_ESTAVEL: 3,
    ESTADO_SEM_SINAL: 4,
}


def fila(bloco: dict[str, Any] | None, hoje: str, *, limite: int = FILA_TAMANHO) -> list[dict[str, Any]]:
    """A fila do dia: processos com trabalho pendente, do mais urgente ao menos.

    Função pura sobre o bloco — sem nomes, sem catálogo, sem I/O. Quem traduz
    `PROC-xx` em nome legível é `revisao_service`, que já tem o catálogo em
    memória; misturar as duas coisas aqui obrigaria este módulo a carregar a
    ontologia só para montar uma lista.
    """
    b = _clonar(bloco)
    linhas: list[dict[str, Any]] = []
    for pid, e in (b.get("processos") or {}).items():
        est = estado(e, hoje)
        if est in (ESTADO_ESTAVEL, ESTADO_SEM_SINAL):
            continue
        rec = _recorrente(e)
        det = _deteriorou(e)
        marcado = e.get("proximo_reteste")
        erro_dominante = None
        pesos = e.get("pesos_raiz") or {}
        if pesos:
            erro_dominante = max(pesos.items(), key=lambda kv: kv[1])[0]
        linhas.append(
            {
                "processo_id": pid,
                "estado": est,
                "erro_dominante": erro_dominante,
                "sem_intervencao_catalogada": erro_dominante in SENTINELAS if erro_dominante else True,
                "peso_raiz": round(sum(pesos.values()), 3),
                "ocorrencias_raiz": len(e.get("raizes_recentes") or []),
                "recorrencia": rec,
                "deterioracao": det,
                "proximo_reteste": marcado,
                "vencido": bool(marcado and hoje >= marcado),
                "degrau": e.get("degrau", 0),
                "ultimo_reteste": e.get("ultimo_reteste"),
                "retestes": e.get("retestes"),
                "transferencias": e.get("transferencias"),
                "contextos_da_raiz": list(e.get("contextos_da_raiz") or []),
                # Hipótese continua sendo hipótese: enquanto o portão de crença
                # estiver desligado, tudo que sai daqui carrega o rótulo, e a
                # tela é obrigada a mostrá-lo (§1.1).
                "provisorio": bool(e.get("provisorio")),
            }
        )
    linhas.sort(
        key=lambda l: (
            _ORDEM_ESTADO.get(l["estado"], 9),
            l["sem_intervencao_catalogada"],
            not l["vencido"],
            -l["peso_raiz"],
        )
    )
    return linhas[:limite]


def trajetoria(bloco: dict[str, Any] | None, processo_id: str) -> list[dict[str, Any]]:
    """Os marcos de um processo, do mais antigo para o mais novo."""
    e = _entrada(_clonar(bloco), processo_id)
    return sorted(e.get("marcos") or [], key=lambda m: m.get("ts") or "")


def instrumentacao(bloco: dict[str, Any] | None) -> dict[str, Any]:
    """A hipótese do §12, em números — instrumentada JUNTO com a Fase 1.

    A pergunta não é se a fila existe. É se o reteste agendado acerta mais que
    a resposta original, e se a diferença SOBREVIVE à troca de contexto. Se não
    sobreviver, o ciclo está ensinando o item e não a habilidade, e a Fase 1
    precisa ser reprojetada antes de qualquer outra.
    """
    b = _clonar(bloco)
    tot = ok = t_tot = t_ok = raizes = 0
    for e in (b.get("processos") or {}).values():
        tot += e["retestes"]["total"]
        ok += e["retestes"]["acertos"]
        t_tot += e["transferencias"]["total"]
        t_ok += e["transferencias"]["acertos"]
        raizes += len(e.get("raizes_recentes") or [])
    return {
        "raizes_registradas": raizes,
        "retestes": {"total": tot, "acertos": ok, "taxa": round(100 * ok / tot, 1) if tot else None},
        "transferencia": {
            "total": t_tot,
            "acertos": t_ok,
            "taxa": round(100 * t_ok / t_tot, 1) if t_tot else None,
        },
        # Transparência: o ritmo que ESTE aluno recebeu, não o ritmo médio.
        "fator_individual": round(_fator_individual(b), 2),
    }


# ---------------------------------------------------------------------------
# Fase 2 — o gatilho do Professor Invisível
# ---------------------------------------------------------------------------


def avaliar_gatilho(
    bloco: dict[str, Any] | None, *, processo_id: str, hoje: str
) -> Optional[dict[str, Any]]:
    """Há evidência suficiente para INTERROMPER o aluno agora?

    Roda sobre o bloco que a escrita da resposta acabou de produzir — custo de
    leitura adicional: nenhum. Devolve o gatilho ou `None`.

    Disciplina de interrupção, que é o que separa um professor invisível de um
    pop-up (e sem a qual a feature é ignorada em uma semana):

      * no máximo `_MAX_INTERVENCOES_ATIVAS` intervenções ativas por vez, no
        aluno inteiro, e nunca duas para o MESMO processo;
      * cooldown por par: disparado, não redispara antes do reteste;
      * dispensar conta como sinal (`dispensas`), e também aciona o cooldown.
    """
    b = _clonar(bloco)
    ativas = b.get("intervencoes_ativas") or {}
    if processo_id in ativas or len(ativas) >= _MAX_INTERVENCOES_ATIVAS:
        return None
    e = _entrada(b, processo_id)

    rec = _recorrente(e)
    det = _deteriorou(e)
    ultimo = e.get("ultimo_reteste") or {}
    falhou_reteste = ultimo.get("acertou") is False

    # Ordem de confiança, não de recência: a recorrência é a evidência mais
    # forte que o produto tem, e o reteste falho só significa alguma coisa
    # depois de ter havido um agendamento.
    if rec:
        motivo, erro_id, detalhe = GATILHO_RECORRENCIA, rec["erro"], rec
    elif det:
        motivo, erro_id, detalhe = GATILHO_DETERIORACAO, _erro_dominante(e), det
    elif falhou_reteste:
        motivo, erro_id, detalhe = GATILHO_RETESTE_FALHO, _erro_dominante(e), ultimo
    else:
        return None

    if not erro_id:
        return None
    chave = par(erro_id, processo_id)
    ate = (b.get("cooldowns") or {}).get(chave)
    if ate and hoje < ate:
        return None

    return {
        "processo_id": processo_id,
        "erro_id": erro_id,
        "par": chave,
        "motivo": motivo,
        "detalhe": detalhe,
        "sem_intervencao_catalogada": erro_id in SENTINELAS,
        "provisorio": bool(e.get("provisorio")),
    }


def _erro_dominante(e: dict) -> str | None:
    pesos = e.get("pesos_raiz") or {}
    return max(pesos.items(), key=lambda kv: kv[1])[0] if pesos else None


def marcar_disparo(bloco: dict[str, Any] | None, gatilho: dict, *, quando: str, hoje: str) -> dict[str, Any]:
    """Registra que a intervenção foi mostrada: ocupa uma vaga (das
    `_MAX_INTERVENCOES_ATIVAS`) e liga o cooldown do par até o reteste. Sem
    isto, a mesma evidência dispararia a cada resposta seguinte."""
    b = _clonar(bloco)
    pid = gatilho["processo_id"]
    e = dict(b["processos"].get(pid) or _entrada_vazia())
    b["processos"][pid] = _marco(e, MARCO_INTERVENCAO, quando, erro=gatilho.get("erro_id"))
    ativas = dict(b.get("intervencoes_ativas") or {})
    ativas[pid] = {
        "processo_id": pid,
        "erro_id": gatilho["erro_id"],
        "par": gatilho["par"],
        "motivo": gatilho["motivo"],
        "em": quando,
    }
    b["intervencoes_ativas"] = ativas
    b["cooldowns"][gatilho["par"]] = e.get("proximo_reteste") or _somar_dias(hoje, INTERVALOS_DIAS[0])
    b["atualizado_em"] = quando
    return b


def encerrar_intervencao(
    bloco: dict[str, Any] | None, *, processo_id: str, quando: str, dispensada: bool = False
) -> dict[str, Any]:
    """Libera a vaga daquele processo. `dispensada=True` conta a dispensa como
    sinal — o aluno dizendo "não é isto" é informação sobre a anotação, não
    silêncio. Encerrar um processo sem vaga ativa é no-op, não erro: a vaga
    pode já ter expirado por outro caminho."""
    b = _clonar(bloco)
    ativas = dict(b.get("intervencoes_ativas") or {})
    if processo_id not in ativas:
        return b
    del ativas[processo_id]
    b["intervencoes_ativas"] = ativas
    if dispensada and processo_id in b["processos"]:
        e = dict(b["processos"][processo_id])
        e["dispensas"] = int(e.get("dispensas") or 0) + 1
        b["processos"][processo_id] = e
    b["atualizado_em"] = quando
    return b
