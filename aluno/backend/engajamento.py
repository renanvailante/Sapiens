"""Motor de engajamento — ofensiva, XP, níveis, missões e ligas.

Só REGRAS, sem I/O: tudo aqui é função pura sobre dados que o chamador já leu.
É o que torna a mecânica testável sem Firestore e sem Mongo, e o que impede que
uma regra de produto (quanto vale um acerto, quando a ofensiva quebra) fique
escondida dentro de uma rota.

--------------------------------------------------------------------------
A LINHA ÉTICA — o que este motor faz e o que ele se recusa a fazer
--------------------------------------------------------------------------
O público é vestibulando, boa parte menor de idade, e o produto cobra em
Sparks. Isso põe um limite no que a gamificação pode fazer, e o limite precisa
morar no código, não numa intenção:

O que ele FAZ (pressão real, honesta):
  * Ofensiva que quebra de verdade quando o aluno não estuda. A perda é real
    porque a conquista é real — o dado vem de `agregado.dias_ativos`, escrito
    por resposta de questão de verdade.
  * Avisar, com números verdadeiros, o que está em risco ("você perde 12 dias
    se não estudar hoje"). Enquadrar perda é legítimo quando a perda existe.
  * Congelador de ofensiva comprável: um bem real, preço à vista, teto de 2.
  * Missões diárias que PAGAM Sparks — ganhar, não gastar.
  * Sapiens Plus pela primeira ofensiva de 5 dias: prêmio fixo (2 dias),
    anunciado desde o primeiro acesso, pago uma vez, por estudo de verdade.
  * Liga semanal com subida e queda entre gente de verdade.

O que ele NÃO FAZ, e por quê (cada item é uma tentação que foi recusada):
  * **Nada de urgência falsa.** Nenhum contador que reinicia, nenhuma oferta
    "que acaba em 10 minutos" e volta amanhã. Um prazo só é exibido se ele
    existir no relógio (a virada do dia em São Paulo, e só).
  * **Nada de escassez falsa.** Nenhuma "última vaga", nenhum estoque
    inventado.
  * **Nada de prova social falsa.** Nenhum "37 alunos estudando agora" que não
    seja contado de gente real; na dúvida, o número não aparece.
  * **Nenhum bot na liga.** Liga vazia é exibida como vazia. Encher o ranking
    com adversários fictícios é mentir sobre com quem a pessoa compete.
  * **XP não se compra.** Sparks compram conveniência (congelador, destaque),
    nunca progresso. No dia em que nível vira mercadoria, o nível para de
    dizer o que o aluno aprendeu — e essa é a única métrica que o produto
    inteiro existe para tornar verdadeira.
  * **Nada de recompensa aleatória.** Toda missão anuncia o prêmio exato antes
    de começar. Razão variável é a mecânica de caça-níquel; ela funciona, e é
    exatamente por isso que está fora.
  * **Nada de preço que sobe com o desespero.** O congelador custa o mesmo para
    quem tem 3 dias e para quem tem 300.
  * **Nada de culpa.** As mensagens de retorno falam do que o aluno construiu,
    nunca do que ele "deve" a ninguém.

Quem for mexer aqui: a pergunta é "isto seria verdade se o aluno visse o
código?". Se a mecânica só funciona enquanto ele não entende o que está
acontecendo, ela não entra.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable
import rotas_do_app as rotas

# ---------------------------------------------------------------------------
# XP — o que cada ação vale
# ---------------------------------------------------------------------------
# Proporção deliberada: a redação (a tarefa mais cara em esforço e a mais
# decisiva no ENEM) vale ~8 questões; responder dúvida de colega vale mais que
# responder questão sozinho, porque explicar é o estudo mais caro que existe e
# é o comportamento que sustenta a comunidade. Nada disto é comprável.
XP_POR_ACAO: dict[str, int] = {
    "questao_respondida": 10,
    "questao_correta": 5,       # somado ao de cima quando acerta
    "revisao_concluida": 15,
    "bloco_cronograma": 25,
    # Estação de curso concluída: 10-20 minutos de estudo guiado que terminam
    # com o aluno acertando os exercícios que contam. Vale mais que um bloco
    # de cronograma (que é uma promessa cumprida) e menos que uma redação (que
    # é a tarefa mais cara do ENEM). Pago UMA vez por estação — refazer não
    # fabrica XP (ver `cursos_progresso.talvez_concluir`).
    "estacao_concluida": 50,
    # Estação vencida por SONDAGEM DE DOMÍNIO — o aluno provou que já sabia e
    # pulou. Vale menos que concluir (foram três exercícios, não a estação
    # inteira) e mais que zero, porque provar domínio também é trabalho. As
    # duas ações dividem a mesma `chave_unica` (`estacao:{curso}:{estacao}`),
    # então uma estação paga XP UMA vez, tenha sido estudada ou provada.
    "estacao_dominada": 30,
    # Exercício de curso. Pago UMA vez por exercício, com duas guardas de
    # `chave_unica` diferentes: a de baixo na primeira tentativa (persistir
    # vale alguma coisa) e a de cima no primeiro acerto. Sem as guardas,
    # responder errado em laço seria uma máquina de fabricar XP — o exercício
    # de curso, ao contrário do da prova, pode ser repetido à vontade.
    "exercicio_curso": 6,
    "exercicio_curso_correto": 4,        # somado ao de cima quando acerta
    # Degrau por dificuldade, somado ao acerto. É o que torna o XP do curso
    # configurável por questão sem espalhar número por tela nenhuma: quem
    # decide quanto vale um exercício de nível 4 é esta tabela, e só ela.
    "exercicio_curso_nivel_2": 2,
    "exercicio_curso_nivel_3": 4,
    "exercicio_curso_nivel_4": 6,
    "exercicio_curso_nivel_5": 9,
    "redacao_corrigida": 120,
    "duvida_publicada": 10,
    "resposta_publicada": 15,
    "resposta_util": 60,        # resposta marcada como a que resolveu
    "missao_concluida": 40,
}

# Curva de nível: T(n) = 50·(n-1)·n é o XP acumulado para ESTAR no nível n.
# Nível 2 a 100 XP (chega no fim da primeira sessão de verdade, ~7 questões),
# nível 5 a 1.000, nível 10 a 4.500. Quadrática porque linear faz o nível 40
# chegar tão rápido quanto o 4 e o número parar de significar alguma coisa.
def xp_acumulado_do_nivel(nivel: int) -> int:
    n = max(1, int(nivel))
    return 50 * (n - 1) * n


def nivel_de_xp(xp_total: int) -> dict[str, int]:
    """Nível, progresso dentro dele e quanto falta para o próximo."""
    xp = max(0, int(xp_total or 0))
    nivel = 1
    while xp_acumulado_do_nivel(nivel + 1) <= xp:
        nivel += 1
    base = xp_acumulado_do_nivel(nivel)
    topo = xp_acumulado_do_nivel(nivel + 1)
    return {
        "nivel": nivel,
        "xp_total": xp,
        "xp_no_nivel": xp - base,
        "xp_do_nivel": topo - base,
        "xp_para_o_proximo": topo - xp,
        "percentual": round(100 * (xp - base) / (topo - base)) if topo > base else 0,
    }


# ---------------------------------------------------------------------------
# Ofensiva (sequência de dias estudando)
# ---------------------------------------------------------------------------

# Teto de congeladores guardados. Dois cobrem o fim de semana viajando ou uma
# semana de prova na escola; a partir daí a ofensiva deixaria de medir hábito e
# passaria a medir saldo de Sparks, que é o oposto do que ela existe para dizer.
MAX_CONGELADORES = 2
CUSTO_CONGELADOR = 50


@dataclass(frozen=True)
class Ofensiva:
    dias: int
    recorde: int
    estudou_hoje: bool
    em_risco: bool
    # Dias que o congelador precisa cobrir para a sequência sobreviver — o
    # serviço persiste e debita. Vazio quando não há nada a salvar.
    congelar: tuple[str, ...]
    congeladores_restantes: int


def _dia(d: date) -> str:
    return d.isoformat()


def calcular_ofensiva(
    dias_ativos: Iterable[str],
    *,
    hoje: str,
    dias_congelados: Iterable[str] = (),
    congeladores: int = 0,
) -> Ofensiva:
    """Sequência de dias consecutivos estudando, olhando para trás a partir de hoje.

    `dias_ativos` vem de `agregado.dias_ativos` (Firestore): um dia só entra ali
    quando existe um evento de resposta real. Não há como somar ofensiva sem
    estudar — é o que faz a perda doer de verdade e, por isso mesmo, o que
    torna legítimo avisar sobre ela.

    **O congelador nunca é gasto à toa.** Ele só é consumido se, com ele, a
    sequência sobrevive: um buraco maior que os congeladores disponíveis quebra
    a ofensiva e devolve os congeladores intactos. Gastar dois congeladores numa
    sequência que ia quebrar de qualquer jeito é o tipo de cobrança silenciosa
    que este arquivo se recusa a fazer.

    Ainda não ter estudado HOJE não quebra nada: o dia não acabou. A contagem
    começa em ontem nesse caso, e `em_risco` marca a diferença para a interface.
    """
    ativos = {d for d in dias_ativos if d}
    congelados = {d for d in dias_congelados if d}
    vivos = ativos | congelados
    hoje_d = date.fromisoformat(hoje)

    estudou_hoje = hoje in ativos
    # Sem atividade hoje, a sequência ainda vale — conta a partir de ontem.
    cursor = hoje_d if estudou_hoje else hoje_d - timedelta(days=1)

    # Buraco entre a sequência e hoje: quantos dias seguidos faltam antes de
    # encontrar atividade. É o que o congelador cobriria.
    a_congelar: list[str] = []
    if not estudou_hoje:
        sonda = cursor
        while _dia(sonda) not in vivos and len(a_congelar) <= MAX_CONGELADORES:
            a_congelar.append(_dia(sonda))
            sonda -= timedelta(days=1)
        if a_congelar:
            if len(a_congelar) <= congeladores and _dia(sonda) in vivos:
                # Dá para salvar: o buraco cabe nos congeladores E existe
                # sequência do outro lado para ser salva.
                vivos = vivos | set(a_congelar)
                cursor = sonda
            else:
                a_congelar = []  # não salva nada; não gasta nada.

    # O dia congelado LIGA a corrente, mas não conta como dia estudado: a
    # ofensiva diz "dias em que você estudou", e um congelador que somasse +1
    # transformaria 50 Sparks num dia de estudo comprado — exatamente o que a
    # linha ética no topo proíbe. Ele protege o que existe; não fabrica.
    dias = 0
    while _dia(cursor) in vivos:
        if _dia(cursor) in ativos:
            dias += 1
        cursor -= timedelta(days=1)

    # Recorde histórico: a maior sequência já feita. Mesma regra do bloco acima
    # — congelado atravessa o buraco, só dia estudado soma.
    recorde = _maior_sequencia(ativos | congelados, ativos)

    return Ofensiva(
        dias=dias,
        recorde=max(recorde, dias),
        estudou_hoje=estudou_hoje,
        em_risco=dias > 0 and not estudou_hoje,
        congelar=tuple(a_congelar),
        congeladores_restantes=max(0, congeladores - len(a_congelar)),
    )


def _maior_sequencia(vivos: set[str], ativos: set[str]) -> int:
    """Maior corrente de dias consecutivos em `vivos`, contando só os que estão
    em `ativos` (dia congelado atravessa o buraco sem virar dia estudado)."""
    if not ativos:
        return 0
    ordenados = sorted(date.fromisoformat(d) for d in vivos)
    maior = atual = 0
    anterior: date | None = None
    for d in ordenados:
        if anterior is not None and (d - anterior).days > 1:
            atual = 0
        if _dia(d) in ativos:
            atual += 1
            maior = max(maior, atual)
        anterior = d
    return maior


# ---------------------------------------------------------------------------
# Sapiens Plus pela ofensiva
# ---------------------------------------------------------------------------
# Pedido do dono em 2026-10-08: o aluno sabe DESDE O INÍCIO que, se mantiver a
# ofensiva por 5 dias, ganha 2 dias "como se fosse pago" — o Sapiens Plus
# (os direitos de `sparks_store.DIREITOS_DO_PLUS`).
#
# Três escolhas, cada uma com o porquê:
#
# * **Uma vez por aluno, não a cada 5 dias.** Um prêmio recorrente de 2 em
#   cada 5 dias daria Plus a quem estuda todo dia durante 40% do tempo — a
#   Mentis ilimitada é a coisa mais cara do catálogo de rodar (cada mensagem
#   é uma chamada de modelo), e o pacote que vende os mesmos direitos deixaria
#   de ter motivo para existir. É o "primeiro presente": o aluno prova o
#   produto inteiro depois de provar a si mesmo que volta. `MARCOS_PLUS` é uma
#   tabela para que um marco novo (30 dias, 100 dias) seja uma linha, não uma
#   refatoração.
# * **A régua é a ofensiva, e a ofensiva é estudo.** `dias` sai de
#   `calcular_ofensiva`, que só conta dia com resposta real; congelador liga a
#   corrente sem somar dia, então não se compra o Plus com Sparks.
# * **48 horas a partir da concessão**, não "até o fim de amanhã": o número
#   que a tela promete ("2 dias") é o número que o relógio entrega, ganhe o
#   aluno o prêmio às 8h ou às 23h59.
PLUS_META_DIAS = 5
PLUS_PRESENTE_DIAS = 2
# marco (dias de ofensiva) -> (chave única do prêmio, dias de Plus)
MARCOS_PLUS: dict[int, tuple[str, int]] = {
    PLUS_META_DIAS: ("plus:ofensiva:5", PLUS_PRESENTE_DIAS),
}


def marco_plus_devido(dias_ofensiva: int, ja_premiado: Iterable[str]) -> tuple[str, int] | None:
    """O marco de Plus que esta ofensiva acabou de alcançar e ainda não foi
    pago — ou `None`. O menor primeiro: quem chega com 12 dias numa conta
    antiga recebe o de 5, e o próximo marco (se um dia existir) no seu dia."""
    pagos = set(ja_premiado or ())
    for meta in sorted(MARCOS_PLUS):
        chave, dias_de_plus = MARCOS_PLUS[meta]
        if dias_ofensiva >= meta and chave not in pagos:
            return chave, dias_de_plus
    return None


def estado_do_plus(
    dias_ofensiva: int,
    *,
    ja_premiado: Iterable[str] = (),
    plus_ate: str | None = None,
    concedido_em: str | None = None,
    agora: str,
) -> dict[str, Any]:
    """O que a interface precisa para contar a promessa e o prêmio.

    Tudo derivado de dado gravado: a ofensiva medida, a chave de prêmio no
    perfil e o prazo que o servidor escreveu. `agora` entra como parâmetro
    para a função continuar pura (e testável sem relógio)."""
    chave, _ = MARCOS_PLUS[PLUS_META_DIAS]
    ganhou = chave in set(ja_premiado or ())
    ativo = False
    if plus_ate:
        try:
            ativo = datetime.fromisoformat(plus_ate) > datetime.fromisoformat(agora)
        except (TypeError, ValueError):
            ativo = False  # prazo ilegível é Plus vencido, nunca eterno
    rumo = PLUS_META_DIAS if ganhou else max(0, min(int(dias_ofensiva or 0), PLUS_META_DIAS))
    return {
        "meta_dias": PLUS_META_DIAS,
        "presente_dias": PLUS_PRESENTE_DIAS,
        "progresso": rumo,
        "faltam": 0 if ganhou else PLUS_META_DIAS - rumo,
        "conquistado": ganhou,
        "ativo": ativo,
        "ate": plus_ate if ativo else None,
        "concedido_em": concedido_em if ganhou else None,
    }


# ---------------------------------------------------------------------------
# Missões diárias
# ---------------------------------------------------------------------------
# Três por dia, sorteadas de forma DETERMINÍSTICA por (aluno, dia): o mesmo
# aluno vê as mesmas três o dia inteiro, em qualquer aparelho, e elas trocam na
# virada do dia em São Paulo. Determinismo aqui não é elegância — é o que
# impede que recarregar a página vire uma máquina de sortear missão fácil.
#
# Toda missão é medida por um contador que o próprio aluno produziu no dia
# (`engajamento_dia` no Mongo). Nenhuma delas pode ser cumprida gastando Sparks:
# missão é trabalho, não compra.

@dataclass(frozen=True)
class Missao:
    id: str
    titulo: str
    contador: str       # campo de `engajamento_dia` que a mede
    alvo: int
    sparks: int
    rota: str           # para onde o card leva
    cta: str


CATALOGO_MISSOES: tuple[Missao, ...] = (
    Missao("responder5", "Responda 5 questões", "questoes", 5, 5, rotas.PROVAS, "Praticar"),
    Missao("responder15", "Responda 15 questões", "questoes", 15, 12, rotas.PROVAS, "Praticar"),
    Missao("acertar8", "Acerte 8 questões", "acertos", 8, 10, rotas.PROVAS, "Praticar"),
    Missao("revisao", "Faça 1 revisão da fila", "revisoes", 1, 8, rotas.AGENDA_REVISOES, "Revisar"),
    Missao("cronograma", "Conclua 1 bloco do cronograma", "blocos", 1, 8, rotas.AGENDA, "Ver a semana"),
    Missao("treino", "Faça 10 questões do banco de treino", "treino", 10, 10, rotas.TREINO, "Treinar"),
    Missao("comunidade", "Responda a dúvida de um colega", "respostas_comunidade", 1, 10, rotas.COMUNIDADE, "Ajudar"),
)

# Uma missão de cada "peso" por dia, para o conjunto nunca ser três tarefas
# longas nem três triviais. A primeira é sempre de prática (o comportamento que
# o produto existe para causar); a segunda varia; a terceira puxa para uma tela
# que o aluno talvez não conheça.
_TRILHOS: tuple[tuple[str, ...], ...] = (
    ("responder5", "responder15", "acertar8"),
    ("acertar8", "treino", "responder15"),
    ("revisao", "cronograma", "comunidade"),
)


def missoes_do_dia(
    uid: str,
    dia: str,
    contadores: dict[str, int] | None = None,
    resgatadas: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """As três missões de hoje, já com progresso.

    **`hashlib`, não o `hash()` embutido.** O `hash()` de str é aleatorizado por
    processo (PYTHONHASHSEED): as missões trocariam a cada restart do servidor e
    seriam diferentes entre duas instâncias — o aluno veria uma missão sumir com
    progresso pela metade, sem nada no produto explicando por quê. O sorteio
    precisa ser estável no tempo e entre máquinas, e só `hashlib` garante isso.
    """
    contadores = contadores or {}
    ja_resgatadas = set(resgatadas)
    semente = int(hashlib.sha256(f"{uid}:{dia}".encode("utf-8")).hexdigest()[:8], 16)
    por_id = {m.id: m for m in CATALOGO_MISSOES}

    # Os trilhos compartilham missões de propósito (o mesmo "acertar8" cabe no
    # trilho de prática e no de precisão), então o sorteio precisa DESCARTAR
    # repetição: ver "Acerte 8 questões" duas vezes na mesma lista faz o dia
    # parecer quebrado e some com um terço das missões.
    escolhidas: list[Missao] = []
    for i, trilho in enumerate(_TRILHOS):
        inicio = (semente >> (i * 5)) % len(trilho)
        for passo in range(len(trilho)):
            candidata = por_id[trilho[(inicio + passo) % len(trilho)]]
            if candidata not in escolhidas:
                escolhidas.append(candidata)
                break
        else:
            # Trilho inteiro já usado: pega a primeira do catálogo que sobrou,
            # para o aluno nunca ver menos de três missões.
            escolhidas.append(next(m for m in CATALOGO_MISSOES if m not in escolhidas))

    saida = []
    for m in escolhidas:
        feito = int(contadores.get(m.contador) or 0)
        saida.append({
            "id": m.id,
            "titulo": m.titulo,
            "alvo": m.alvo,
            "progresso": min(feito, m.alvo),
            "concluida": feito >= m.alvo,
            "sparks": m.sparks,
            "xp": XP_POR_ACAO["missao_concluida"],
            "rota": m.rota,
            "cta": m.cta,
            # O prêmio é anunciado antes, sempre. Ver a linha ética no topo.
            "resgatada": m.id in ja_resgatadas,
        })
    return saida


# ---------------------------------------------------------------------------
# Ligas semanais
# ---------------------------------------------------------------------------
# Seis divisões. O aluno compete por XP DA SEMANA (não acumulado), o que
# significa que quem começou ontem disputa em pé de igualdade com quem está há
# seis meses — a liga mede esforço da semana, não antiguidade.

LIGAS: tuple[dict[str, str], ...] = (
    {"id": "bronze", "nome": "Bronze", "cor": "#B87333"},
    {"id": "prata", "nome": "Prata", "cor": "#C0C6CE"},
    {"id": "ouro", "nome": "Ouro", "cor": "#E8B923"},
    {"id": "safira", "nome": "Safira", "cor": "#4FD9FF"},
    {"id": "rubi", "nome": "Rubi", "cor": "#FF5B7F"},
    {"id": "diamante", "nome": "Diamante", "cor": "#B794F6"},
)
_IDS_LIGA = [l["id"] for l in LIGAS]

TAMANHO_GRUPO = 30
SOBEM = 7     # os 7 primeiros sobem de divisão
CAEM = 5      # os 5 últimos descem


def liga_por_id(liga_id: str) -> dict[str, str]:
    for l in LIGAS:
        if l["id"] == liga_id:
            return l
    return LIGAS[0]


def promover(liga_id: str, posicao: int, total_no_grupo: int) -> str:
    """Divisão da próxima semana. Grupo pequeno demais não rebaixa ninguém:
    ficar em último entre três pessoas não é o mesmo que ficar em último entre
    trinta, e punir por isso é punir o aluno pelo tamanho da base — um fato
    sobre o produto, não sobre ele."""
    i = _IDS_LIGA.index(liga_id) if liga_id in _IDS_LIGA else 0
    if posicao <= SOBEM and total_no_grupo >= 10:
        return _IDS_LIGA[min(i + 1, len(_IDS_LIGA) - 1)]
    if total_no_grupo >= TAMANHO_GRUPO and posicao > total_no_grupo - CAEM:
        return _IDS_LIGA[max(i - 1, 0)]
    return liga_id


def semana_de(dia: str) -> str:
    """Chave da semana ISO (`2026-W38`) a que o dia pertence. Segunda a domingo,
    a mesma semana do Cronograma — duas noções de semana no mesmo produto seria
    o tipo de detalhe que ninguém percebe até a segunda-feira em que os números
    não batem."""
    d = date.fromisoformat(dia)
    ano, num, _ = d.isocalendar()
    return f"{ano}-W{num:02d}"


def fim_da_semana(semana: str) -> str:
    """Domingo (inclusive) da semana — o instante em que a liga fecha."""
    ano, num = semana.split("-W")
    segunda = date.fromisocalendar(int(ano), int(num), 1)
    return _dia(segunda + timedelta(days=6))


# ---------------------------------------------------------------------------
# ENEM
# ---------------------------------------------------------------------------
# As datas oficiais dos dois domingos de prova. Ficam em código (e não em env)
# porque são fato público, mudam uma vez por ano e precisam ser revisadas junto
# com o resto do catálogo de produto.
DATAS_ENEM: tuple[str, ...] = ("2026-11-08", "2026-11-22")


def dias_para_o_enem(hoje: str) -> dict[str, Any] | None:
    """Dias até o primeiro domingo de prova ainda não realizado.

    Sem urgência inventada: quando as duas datas passam, devolve `None` e a
    contagem some da tela até o calendário do ano seguinte entrar aqui.
    """
    h = date.fromisoformat(hoje)
    for data_prova in DATAS_ENEM:
        d = date.fromisoformat(data_prova)
        if d >= h:
            return {"data": data_prova, "dias": (d - h).days, "fase": DATAS_ENEM.index(data_prova) + 1}
    return None
