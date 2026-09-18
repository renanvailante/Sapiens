"""O que um exercício de curso vale — em Sparks e em XP — e quem paga.

**Este é o único lugar do produto que sabe quanto vale um exercício de
curso.** Nem a tela, nem a rota, nem o conteúdo: a tela mostra o que recebeu,
a rota chama `pagar_exercicio` e o arquivo de conteúdo tem proibido declarar
preço (`cursos_conteudo.CHAVES_PROIBIDAS`). Um número de recompensa escrito no
React é uma promessa que o servidor não fez.

As duas moedas, e por que são diferentes
----------------------------------------
**Spark é dinheiro, e só o acerto DE PRIMEIRA paga.** +1 por exercício que
sai certo na primeira tentativa, uma única vez por exercício, para sempre —
refazer, rever ou responder de outra aba não credita de novo. A garantia é
atômica e não é deste módulo: `grant_question_sparks` cria
`students/{uid}/sparks_questoes/{item_id}` e só a primeira criação credita
(mesmo padrão de compra e de round).

Por que só a primeira tentativa: com quatro alternativas e tentativas
ilimitadas, todo exercício acaba certo — o Spark por "acerto eventual" seria
um pagamento por persistência de clique, não por saber. Acertar de primeira é
a única evidência que o formato dá de graça.

**A regra não é anunciada na tela, e isso é decisão de produto.** O aluno
descobre respondendo: ganhou no primeiro acerto, não ganhou quando voltou
para refazer. Não há nada escondido que lhe custe algo — Sparks aqui se
GANHAM; o que se paga (curso, live, Mentis) continua com preço na cara.

**XP não se compra e não se perde.** Ele mede esforço, e por isso é pago em
duas guardas: a primeira tentativa (persistir conta) e o primeiro acerto (com
degrau por dificuldade). As duas com `chave_unica`, porque um exercício de
curso pode ser refeito à vontade — sem guarda, um laço de respostas erradas
seria uma máquina de XP, e o ranking da liga deixaria de significar qualquer
coisa. Quanto vale cada degrau está em `engajamento.XP_POR_ACAO`, junto com
todo o resto do XP do produto.

O que este módulo NUNCA faz
---------------------------
* **Não derruba a resposta do aluno.** Toda falha de crédito é logada e
  engolida: perder um Spark é aborrecimento, perder a resposta é perder o
  estudo. É a mesma regra de `cursos_progresso._dar_xp`.
* **Não decide se acertou.** Quem corrige é `cursos_conteudo.corrigir`.
* **Não lê histórico.** Nada aqui cresce com o uso (ver o incidente de cota
  de 2026-09-04): é O(1) por resposta, como toda cobrança do produto.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("sapiens.cursos.recompensa")

SPARKS_POR_ACERTO = 1


def item_id(curso_id: str, estacao_id: str, bloco_id: str) -> str:
    """O endereço de um exercício de curso no ecossistema do aluno.

    Mesmo formato do Treino (`TREINO:{hab}:{indice}`): um prefixo que diz de
    onde o item veio, e depois o caminho. É a chave do crédito de Spark, é o
    `item_id` do evento de behavior e é o que liga uma resposta ao conteúdo
    que a gerou — os três precisam ser a MESMA string, senão o aluno recebe
    Spark duas vezes ou o histórico não casa com o item.
    """
    return f"CURSO:{curso_id}:{estacao_id}:{bloco_id}"


def acoes_de_xp(bloco: dict, *, acertou: bool) -> list[str]:
    """As ações de XP que esta resposta dispara, na tabela do engajamento.

    Desafio entra pelo mesmo caminho dos exercícios: ele é mais difícil (nível
    5, por contrato) e o degrau por nível já o remunera por isso.
    """
    if not acertou:
        return ["exercicio_curso"]
    nivel = int(bloco.get("nivel") or 1)
    acoes = ["exercicio_curso", "exercicio_curso_correto"]
    if nivel > 1:
        acoes.append(f"exercicio_curso_nivel_{min(nivel, 5)}")
    return acoes


async def pagar_exercicio(
    uid: str,
    *,
    curso_id: str,
    estacao_id: str,
    bloco: dict,
    acertou: bool,
    tentativa: int,
    nome: str | None = None,
    sem_sparks: bool = False,
) -> dict[str, Any]:
    """Credita o que esta resposta merece e devolve o que foi creditado AGORA.

    O retorno é o que a tela mostra no instante do feedback — e é só o que
    entrou nesta resposta. Um exercício já pago devolve zero: a devolutiva não
    pode anunciar "+1 Spark" quando nada foi creditado, que é a forma mais
    rápida de fazer o aluno desconfiar do saldo.
    """
    endereco = item_id(curso_id, estacao_id, bloco["bloco_id"])
    ganho = {"sparks": 0, "xp": 0}

    # `sem_sparks` é a prova de salto: lá o aluno não está estudando, está
    # provando que não precisa estudar. Pagar por isso transformaria o atalho
    # numa fonte de renda melhor que a aula.
    if acertou and tentativa <= 1 and not sem_sparks:
        ganho["sparks"] = await _creditar_sparks(uid, endereco)

    ganho["xp"] = await _creditar_xp(
        uid, endereco, bloco=bloco, acertou=acertou, tentativa=tentativa, nome=nome,
    )
    return ganho


async def _creditar_sparks(uid: str, endereco: str) -> int:
    """+1 Spark pelo acerto, uma vez por exercício.

    Importado aqui dentro (e não no topo) pelo mesmo motivo de
    `cursos_progresso._dar_xp`: o módulo de recompensa não pode arrastar o
    Firestore para a importação, e o teste roda sem ele.
    """
    try:
        import firestore_service as fs

        resultado = await asyncio.to_thread(
            fs.grant_question_sparks, uid, endereco, SPARKS_POR_ACERTO,
        )
        return int(resultado.get("sparks_ganhos") or 0)
    except Exception:  # noqa: BLE001
        logger.exception("Spark do exercício %s não creditado para %s.", endereco, uid)
        return 0


async def _creditar_xp(
    uid: str, endereco: str, *, bloco: dict, acertou: bool, tentativa: int, nome: str | None,
) -> int:
    """XP da tentativa e XP do acerto, cada um com sua guarda de unicidade."""
    total = 0
    try:
        import engajamento_service

        if tentativa <= 1:
            r = await engajamento_service.registrar_acao(
                uid, ["exercicio_curso"],
                contadores={"exercicios_curso": 1},
                nome=nome,
                chave_unica=f"tentou:{endereco}",
            )
            total += int(r.get("xp") or 0)

        if acertou:
            acoes = [a for a in acoes_de_xp(bloco, acertou=True) if a != "exercicio_curso"]
            r = await engajamento_service.registrar_acao(
                uid, acoes,
                contadores={"acertos_curso": 1},
                nome=nome,
                chave_unica=f"acertou:{endereco}",
            )
            total += int(r.get("xp") or 0)
    except Exception:  # noqa: BLE001
        logger.exception("XP do exercício %s não registrado para %s.", endereco, uid)
    return total


def xp_possivel(estacao) -> int:
    """Quanto XP a estação ainda pode render, do zero ao fim.

    O que a tela do mapa anuncia antes de o aluno entrar. Soma o máximo de
    cada exercício (tentativa + acerto + degrau) com o XP da conclusão — é o
    teto honesto, e é calculado a partir da MESMA tabela que paga.
    """
    import engajamento as eng

    total = 0
    for bloco in estacao.avaliaveis:
        for acao in acoes_de_xp(bloco, acertou=True):
            total += eng.XP_POR_ACAO.get(acao, 0)
    return total + eng.XP_POR_ACAO.get("estacao_concluida", 0)


def sparks_possiveis(estacao) -> int:
    """O TETO de Sparks da estação: um por exercício acertado de primeira,
    desafio incluído. `avaliaveis` e não `exercicios` porque acertar o desafio
    também credita — ele não conclui a estação, mas vale o Spark."""
    return SPARKS_POR_ACERTO * len(estacao.avaliaveis)
