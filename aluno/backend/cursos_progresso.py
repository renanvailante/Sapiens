"""Progresso do aluno dentro de um curso: o que ele viu, o que acertou, o que
já liberou.

Duas coleções, com papéis que não se misturam:

**`cursos_progresso` — o ESTADO.** Um documento por aluno por estação, de
`_id` determinístico (`"{uid}:{curso_id}:{estacao_id}"`). É o que a tela lê, e
é pequeno e limitado: uma estação tem dezenas de blocos, não milhares. Abrir a
trilha custa UMA consulta ao Mongo, e nenhuma ao Firestore.

**`cursos_eventos` — o HISTÓRICO.** Uma linha por interação (estação aberta,
bloco visto, exercício respondido, estação concluída), só escrita. **Nada no
caminho do aluno lê esta coleção** — é a regra que vale para todo o app desde
o incidente de cota de 2026-09-04 e que `test_custo_firestore.py` tranca: uma
tela cujo custo cresce com o histórico do aluno fica mais lenta e mais cara
exatamente para quem mais usa o produto. Quem lê daqui é o painel do admin,
com agregação e recorte, e é daqui que sai a análise de comportamento (onde a
turma trava, qual exercício leva mais tempo, qual alternativa errada atrai
mais gente).

Por que os agregados ficam no documento de estado e não são recalculados dos
eventos: recalcular é a versão bonita e é a que custa O(eventos) por abertura
de tela. O contador do documento é a versão que escala.

**Liberação de estação** é função pura (`mapa_de_estados`): o servidor decide,
a tela só desenha. Duas fontes, nesta ordem:

1. a ORDEM da trilha — a estação N abre quando a N-1 está concluída;
2. `pre_requisitos` declarados no conteúdo — que podem cruzar trilhas.

A primeira trilha e a primeira estação de cada trilha começam abertas. Trilhas
são paralelas de propósito: quem quer começar por Frações e quem quer começar
por Porcentagem estão os dois estudando.

**Nada aqui cobra Sparks.** Quem pode entrar no curso é decidido antes, pelo
direito de acesso (`cursos_estudo_routes._exigir_acesso`); daqui para dentro o
conteúdo é livre. Preço não aparece neste módulo por decisão de arquitetura, e
sim em `cursos.py`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import cursos
import cursos_conteudo as cc
import firestore_service as fs

logger = logging.getLogger("sapiens.cursos.progresso")

_db = None

BLOQUEADA = "bloqueada"
DISPONIVEL = "disponivel"
EM_ANDAMENTO = "em_andamento"
CONCLUIDA = "concluida"
# Concluída ACERTANDO TUDO DE PRIMEIRA. Não é um selo a mais: é a diferença
# entre "chegou ao fim" e "já sabia", e ela sai de dado que o documento já
# guarda (`acertou_de_primeira`), sem nenhuma pergunta nova ao aluno.
DOMINADA = "dominada"
# Vencida pela SONDAGEM DE DOMÍNIO, sem estudar o conteúdo. Estado próprio, e
# nunca `concluida`: marcar as duas coisas como a mesma faria o produto (e a
# Mentis) afirmarem que o aluno estudou uma estação que ele pulou. O que ele
# provou foi que sabia — e é isso que fica escrito.
PULADA = "pulada"

# Quantos exercícios a sondagem de domínio faz, e quantos deles têm de sair
# certos DE PRIMEIRA para a estação ser pulada. Três dos mais difíceis, todos
# certos: com dois, o acerto por acaso em múltipla escolha de quatro
# alternativas é 1 em 16; com três, 1 em 64 — e o aluno ainda perde a chance
# se errar um. Uma sondagem por estação, sem segunda chance: repetir até
# passar não seria evidência de domínio, seria força bruta.
SONDAGEM_QUESTOES = 3
SONDAGEM_TENTATIVAS = 1

# O SALTO: "pular até aqui". Vinte questões sorteadas de TODAS as estações
# anteriores ao destino, e 80% delas certas de primeira.
#
# Os três números são a mesma decisão vista de ângulos diferentes. Vinte
# porque a prova cobre um pedaço inteiro do curso e uma amostra pequena não
# distingue quem sabe de quem teve sorte. 80% e não 100% porque quem pula dez
# estações vai encontrar um assunto de canto que não domina, e travar por um
# item seria punir justamente quem sabe quase tudo. De primeira porque com
# quatro alternativas e tentativa livre todo mundo acerta no fim.
#
# UMA tentativa por destino — e essa é a parte que faz a prova valer alguma
# coisa. Com repetição, vinte questões de múltipla escolha caem por força
# bruta. Quem não passa não fica sem saída: pode provar um salto mais curto,
# que é exatamente o que o produto quer que ele faça.
SALTO_QUESTOES = 20
SALTO_APROVACAO = 0.8
SALTO_TENTATIVAS = 1

# Os estados que tiram a estação do caminho — e que a barra de progresso conta.
VENCIDOS = (CONCLUIDA, DOMINADA, PULADA)

# Teto do tempo que o cliente pode reportar por exercício. Não é segurança —
# é higiene de dado: a aba que ficou aberta a noite toda mandaria "28.000
# segundos" e envenenaria a média de tempo por exercício do curso inteiro.
TEMPO_MAXIMO_SEGUNDOS = 3600


def set_db(db):
    global _db
    _db = db


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(uid: str, curso_id: str, estacao_id: str) -> str:
    return f"{uid}:{curso_id}:{estacao_id}"


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


async def progresso_do_curso(uid: str, curso_id: str) -> dict[str, dict]:
    """Todo o progresso do aluno naquele curso — `estacao_id -> documento`.

    UMA consulta para a trilha inteira. Um `find_one` por estação seria uma
    ida ao banco por card da tela.
    """
    if _db is None:
        return {}
    docs = await _db.cursos_progresso.find(
        {"uid": uid, "curso_id": curso_id}, {"_id": 0}
    ).to_list(500)
    return {d["estacao_id"]: d for d in docs}


async def progresso_de_todos_os_cursos(uid: str) -> dict[str, dict[str, dict]]:
    """Todo o progresso do aluno, agrupado por curso. UMA consulta.

    É o que a HOME de Cursos precisa para dizer "continue de onde parou" em
    cada curso sem fazer uma consulta por card. O teto existe e é generoso
    (duas mil estações tocadas por aluno); o custo continua sendo O(estações
    que ele tocou), nunca O(histórico) — que é a classe que derrubou o app em
    2026-09-04.
    """
    if _db is None:
        return {}
    docs = await _db.cursos_progresso.find({"uid": uid}, {"_id": 0}).to_list(2000)
    por_curso: dict[str, dict[str, dict]] = {}
    for d in docs:
        por_curso.setdefault(d.get("curso_id", ""), {})[d["estacao_id"]] = d
    return por_curso


async def resumo_para_mentis(uid: str) -> dict:
    """O que a Mentis precisa saber sobre os cursos deste aluno, compactado.

    UMA consulta — a mesma de `progresso_de_todos_os_cursos` — nunca
    `cursos_eventos`: é a mesma disciplina de leitura do resto do módulo,
    aplicada ao dossiê do chat (`mentis_routes._montar_dossie`). Sem isto a
    Mentis sabia tudo sobre treino e nada sobre curso — um aluno que passa a
    tarde numa estação e abre o chat depois encontrava uma tutora que não
    tinha lido o que ele acabou de fazer.

    Devolve `{}` para quem nunca tocou um curso — dossiê vazio não vira linha
    nenhuma no texto (ver o chamador).
    """
    por_curso = await progresso_de_todos_os_cursos(uid)
    if not por_curso:
        return {}

    cursos_tocados: list[dict] = []
    total_exercicios = 0
    total_acertos = 0
    for curso_id, estacoes in por_curso.items():
        curso = cursos.get_curso(curso_id)
        concluidas = sum(1 for d in estacoes.values() if esta_vencida(d))
        for d in estacoes.values():
            respostas = d.get("respostas") or {}
            total_exercicios += len(respostas)
            total_acertos += sum(1 for r in respostas.values() if r.get("acertou"))
        cursos_tocados.append({
            "curso_id": curso_id,
            "titulo": curso.titulo if curso else curso_id,
            "estacoes_tocadas": len(estacoes),
            "estacoes_concluidas": concluidas,
        })

    return {
        "cursos": cursos_tocados,
        "exercicios_respondidos": total_exercicios,
        "exercicios_acertados": total_acertos,
    }


def resumo_do_curso(curso: cc.CursoConteudo, progresso: dict[str, dict]) -> dict:
    """O cartão de um curso na home: quanto andou e qual é o próximo passo.

    Deriva de `mapa_de_estados` em vez de contar documentos: é a MESMA regra
    de liberação da tela do curso, então a home nunca aponta para uma estação
    que o mapa mostra trancada.
    """
    mapa = mapa_de_estados(curso, progresso)
    total = sum(t["total"] for t in mapa)
    vencidas = sum(t["concluidas"] for t in mapa)
    return {
        "estacoes": total,
        "concluidas": vencidas,
        "estudadas": sum(t["estudadas"] for t in mapa),
        "puladas": sum(t["puladas"] for t in mapa),
        "percentual": round(100 * vencidas / total) if total else 0,
        "comecou": bool(progresso),
        "proxima": proxima_estacao(curso, progresso),
    }


async def progresso_da_estacao(uid: str, curso_id: str, estacao_id: str) -> dict:
    if _db is None:
        return {}
    doc = await _db.cursos_progresso.find_one({"_id": _id(uid, curso_id, estacao_id)}, {"_id": 0})
    return doc or {}


def acertos(progresso: dict, estacao: cc.Estacao) -> int:
    """Quantos exercícios QUE CONTAM o aluno já acertou ao menos uma vez.

    Contado a partir do mapa de respostas, e não de um contador incrementado
    no acerto: contador incrementado diverge no dia em que um exercício sai do
    conteúdo ou deixa de contar, e ninguém percebe porque o número continua
    parecendo razoável.
    """
    respostas = progresso.get("respostas") or {}
    return sum(
        1 for b in estacao.exercicios
        if (respostas.get(b["bloco_id"]) or {}).get("acertou")
    )


def acertos_de_primeira(progresso: dict, estacao: cc.Estacao) -> int:
    """Quantos dos exercícios que contam saíram certos na PRIMEIRA tentativa.

    É a medida de domínio que não custa nada: já está no documento desde que
    a primeira resposta foi gravada. Acerto na terceira tentativa mede
    persistência — que é bom, e é outra coisa.
    """
    respostas = progresso.get("respostas") or {}
    return sum(
        1 for b in estacao.exercicios
        if (respostas.get(b["bloco_id"]) or {}).get("acertou_de_primeira")
    )


def esta_concluida(progresso: dict) -> bool:
    return bool(progresso.get("concluida_em"))


def foi_pulada(progresso: dict) -> bool:
    return bool(progresso.get("pulada_em"))


def esta_vencida(progresso: dict) -> bool:
    """A estação saiu do caminho do aluno — por estudo ou por prova de domínio.

    É ESTA a pergunta que libera a estação seguinte, e não `esta_concluida`:
    quem provou que já sabia não pode ficar preso atrás do próprio domínio.
    As duas continuam distintas em tudo o mais, que é o ponto.
    """
    return esta_concluida(progresso) or foi_pulada(progresso)


def estado_da_estacao(estacao: cc.Estacao, progresso: dict, *, liberada: bool) -> str:
    """Os seis estados, decididos num lugar só.

    A ordem das perguntas é a precedência: pulada e concluída são finais;
    bloqueada só vale para quem não venceu; e "em andamento" é ter começado.
    """
    if foi_pulada(progresso):
        return PULADA
    if esta_concluida(progresso):
        if acertos_de_primeira(progresso, estacao) >= estacao.acertos_para_concluir:
            return DOMINADA
        return CONCLUIDA
    if not liberada:
        return BLOQUEADA
    if progresso.get("iniciada_em"):
        return EM_ANDAMENTO
    return DISPONIVEL


def resumo_da_estacao(estacao: cc.Estacao, progresso: dict) -> dict:
    """O que a tela mostra no card de uma estação, sem o conteúdo dela."""
    import cursos_recompensa as cr

    feitos = acertos(progresso, estacao)
    alvo = estacao.acertos_para_concluir
    dominio = progresso.get("dominio") or {}
    return {
        "estacao_id": estacao.estacao_id,
        "trilha_id": estacao.trilha_id,
        "numero": estacao.numero,
        "titulo": estacao.titulo,
        "objetivo": estacao.objetivo,
        "duracao_minutos": estacao.duracao_minutos,
        # `habilidades` e `conceitos` são vocabulário INTERNO e não vão para a
        # tela do aluno (ver a regra de privacidade da ontologia): saem daqui
        # porque a mesma função serve o painel do admin e a Mentis.
        "habilidades": list(estacao.habilidades),
        "conceitos": list(estacao.conceitos),
        "exercicios": len(estacao.exercicios),
        "acertos": feitos,
        "acertos_de_primeira": acertos_de_primeira(progresso, estacao),
        "acertos_para_concluir": alvo,
        "blocos": len(estacao.blocos),
        "blocos_vistos": len(progresso.get("blocos_vistos") or []),
        "concluida_em": progresso.get("concluida_em"),
        "pulada_em": progresso.get("pulada_em"),
        "iniciada_em": progresso.get("iniciada_em"),
        # Quanto a estação ainda rende. Vem da MESMA tabela que paga
        # (`cursos_recompensa`), para a tela nunca anunciar um número que o
        # servidor não vai creditar.
        "xp_possivel": cr.xp_possivel(estacao),
        "sparks_possiveis": cr.sparks_possiveis(estacao),
        # A sondagem já foi usada? A tela precisa saber para não oferecer um
        # botão que o servidor vai recusar.
        "sondagem_usada": bool(dominio.get("tentativas")),
        "salto_usado": bool((progresso.get("salto") or {}).get("tentativas")),
    }


def mapa_de_estados(curso: cc.CursoConteudo, progresso: dict[str, dict]) -> list[dict]:
    """As trilhas do curso com o estado de cada estação para ESTE aluno.

    Função pura — recebe conteúdo e progresso, devolve desenho. É o único
    lugar que decide o que está liberado, e por isso a tela nunca precisa
    repetir a regra (nem pode contradizê-la).
    """
    # "Vencida" e não "concluída": quem provou domínio na sondagem também
    # abre a estação seguinte. São estados diferentes em tudo o mais.
    vencidas = {eid for eid, p in progresso.items() if esta_vencida(p)}

    # Quantas estações AINDA NÃO VENCIDAS existem antes de cada uma, na ordem
    # do curso inteiro (que atravessa trilhas). É o número que decide se o
    # "pular até aqui" tem o que provar.
    pendentes_antes: dict[str, int] = {}
    acumulado = 0
    for eid in curso.ordem_das_estacoes:
        pendentes_antes[eid] = acumulado
        if eid not in vencidas:
            acumulado += 1

    trilhas: list[dict] = []

    for trilha in curso.trilhas:
        estacoes: list[dict] = []
        anterior_ok = True  # a primeira estação de cada trilha começa aberta
        for eid in trilha.estacoes:
            estacao = curso.estacoes[eid]
            p = progresso.get(eid) or {}
            faltando = [r for r in estacao.pre_requisitos if r not in vencidas]
            liberada = anterior_ok and not faltando

            estacoes.append({
                **resumo_da_estacao(estacao, p),
                "estado": estado_da_estacao(estacao, p, liberada=liberada),
                # "Pular até aqui" só existe quando há o que pular: alguma
                # estação anterior ainda não vencida, e esta ainda por vencer.
                # Quem responde isso é o servidor — a tela não conhece a ordem
                # do curso inteiro, só a da trilha que está desenhando.
                "pode_saltar": bool(
                    pendentes_antes.get(eid) and not esta_vencida(p)
                ),
                "estacoes_a_pular": pendentes_antes.get(eid, 0),
                # O que falta para abrir, com NOME e não com id: é o que a
                # tela precisa escrever para o cadeado fazer sentido.
                "pre_requisitos_faltando": [
                    {"estacao_id": r, "titulo": curso.estacoes[r].titulo}
                    for r in faltando if r in curso.estacoes
                ],
            })
            anterior_ok = eid in vencidas

        trilhas.append({
            "trilha_id": trilha.trilha_id,
            "titulo": trilha.titulo,
            "resumo": trilha.resumo,
            "estacoes": estacoes,
            # O que a barra de progresso conta: tudo que saiu do caminho.
            # Um curso em que o aluno pulou seis estações provando domínio não
            # pode mostrar 0% — ele andou seis estações.
            "concluidas": sum(1 for e in estacoes if e["estado"] in VENCIDOS),
            "estudadas": sum(1 for e in estacoes if e["estado"] in (CONCLUIDA, DOMINADA)),
            "puladas": sum(1 for e in estacoes if e["estado"] == PULADA),
            "total": len(estacoes),
        })
    return trilhas


def estacao_liberada(curso: cc.CursoConteudo, estacao_id: str, progresso: dict[str, dict]) -> bool:
    """A mesma decisão de `mapa_de_estados`, para UMA estação.

    Deriva do mapa em vez de repetir a regra: duas implementações da mesma
    liberação divergem, e a que erra é sempre a que o aluno encontra.
    """
    for trilha in mapa_de_estados(curso, progresso):
        for e in trilha["estacoes"]:
            if e["estacao_id"] == estacao_id:
                return e["estado"] != BLOQUEADA
    return False


def proxima_estacao(curso: cc.CursoConteudo, progresso: dict[str, dict]) -> dict | None:
    """Por onde continuar: a primeira em andamento, senão a primeira liberada.

    Em andamento vem antes de nova porque retomar o que foi começado é quase
    sempre o passo certo — e porque é o que o aluno esperava encontrar ao
    voltar.
    """
    mapa = mapa_de_estados(curso, progresso)
    todas = [e for t in mapa for e in t["estacoes"]]
    return (
        next((e for e in todas if e["estado"] == EM_ANDAMENTO), None)
        or next((e for e in todas if e["estado"] == DISPONIVEL), None)
    )


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------


async def _escrever(uid: str, estacao: cc.Estacao, update: dict, *, abre_estacao: bool = True):
    """Toda escrita de progresso passa por aqui, e toda escrita é um upsert.

    O documento de progresso **nasce com identidade completa**, seja qual for
    a interação que o criou. A alternativa — deixar `iniciar()` ser o único a
    gravar `uid`/`curso_id` — funciona enquanto o cliente sempre abre a
    estação antes de responder, e produz um documento fantasma no dia em que
    não abre: a resposta é gravada, mas a consulta do mapa da trilha (que
    filtra por `uid` e `curso_id`) não o encontra, e o aluno vê a estação que
    acabou de concluir como se nunca tivesse sido tocada.

    `$setOnInsert` é o que separa o que é do NASCIMENTO do que é de agora:
    `iniciada_em` é a primeira vez e não pode ser reescrita a cada visita,
    senão a métrica de quanto tempo a estação leva passa a medir a última.
    `versao_conteudo` idem — é a versão que este aluno de fato estudou, e é o
    que mantém os dados interpretáveis depois de o conteúdo ser reescrito.
    """
    nascimento = {
        "uid": uid,
        "curso_id": estacao.curso_id,
        "estacao_id": estacao.estacao_id,
        "trilha_id": estacao.trilha_id,
        "versao_conteudo": estacao.versao,
    }
    # `abre_estacao=False` é para a escrita que TOCA o documento sem que o
    # aluno tenha entrado na estação: a prova de salto mora no documento do
    # destino, e sem esta ressalva abrir a prova marcaria como "em andamento"
    # uma estação que ele nunca abriu — e dispararia o evento de início, que
    # inflaria a taxa de início de toda a análise.
    if abre_estacao:
        nascimento["iniciada_em"] = _agora_iso()
    # `blocos_vistos` e `respostas` NÃO nascem vazios aqui de propósito: o
    # Mongo real recusa o update inteiro quando `$setOnInsert` e `$addToSet`
    # (ou um `$set` com caminho pontilhado) tocam o mesmo campo — "would
    # create a conflict at 'blocos_vistos'". Ausente é o mesmo que vazio para
    # todo mundo que lê (`.get(...) or []`), e `$addToSet` cria o array.
    pedido = dict(update)
    pedido["$setOnInsert"] = {**nascimento, **(pedido.get("$setOnInsert") or {})}
    r = await _db.cursos_progresso.update_one(
        {"_id": _id(uid, estacao.curso_id, estacao.estacao_id)}, pedido, upsert=True,
    )
    # `upserted_id` é a única forma de distinguir "criei agora" de "já
    # existia" num upsert — e é o que impede um evento de início por abertura
    # de página, que inflaria a taxa de início de toda a análise.
    if r.upserted_id is not None and abre_estacao:
        await _evento(uid, estacao, evento="estacao_iniciada")
    return r


async def iniciar(uid: str, estacao: cc.Estacao) -> dict:
    """Marca a entrada do aluno na estação. Idempotente."""
    if _db is None:
        return {}
    await _escrever(uid, estacao, {
        "$set": {"vista_em": _agora_iso()}, "$inc": {"aberturas": 1},
    })
    return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)


async def marcar_bloco_visto(uid: str, estacao: cc.Estacao, bloco_id: str) -> dict:
    """Texto lido, exemplo percorrido, vídeo assistido.

    `$addToSet`: ver duas vezes é ver uma vez. O sinal que interessa é
    "chegou até aqui", não quantas vezes rolou a tela.
    """
    if _db is None:
        return {}
    # Só o `$addToSet`, sem carimbo de "atualizado agora" junto: com um campo
    # de data no mesmo update, `modified_count` seria 1 em TODA chamada (a
    # data sempre muda) e o evento de "bloco visto" seria gravado a cada
    # rolagem da tela. Aqui `modified_count` significa exatamente uma coisa —
    # este bloco entrou agora na lista.
    r = await _escrever(uid, estacao, {"$addToSet": {"blocos_vistos": bloco_id}})
    if r.modified_count or r.upserted_id is not None:
        await _evento(uid, estacao, evento="bloco_visto", bloco_id=bloco_id)
    return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)


async def registrar_resposta(
    uid: str,
    estacao: cc.Estacao,
    bloco: dict,
    *,
    acertou: bool,
    chave: str,
    tempo_segundos: float | None = None,
    resposta_bruta: Any = None,
    sondagem: bool = False,
) -> dict:
    """Guarda a tentativa e devolve o progresso atualizado.

    Um exercício acertado **não volta a ser errado**: `acertou` no documento é
    "já acertou alguma vez". Quem quiser rever o exercício depois pode errar à
    vontade sem perder o que conquistou — e a conclusão da estação não fica
    oscilando entre concluída e não concluída.

    `acertou_de_primeira` é gravado uma vez e é o número que vale para
    medir a dificuldade real de um exercício: o acerto na terceira tentativa
    mede persistência, não entendimento.
    """
    if _db is None:
        return {}

    bloco_id = bloco["bloco_id"]
    campo = f"respostas.{bloco_id}"
    anterior = (await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)).get(
        "respostas", {}
    ).get(bloco_id) or {}

    mudancas: dict[str, Any] = {
        f"{campo}.ultima_em": _agora_iso(),
        f"{campo}.ultima_chave": chave,
        "atualizada_em": _agora_iso(),
    }
    if acertou and not anterior.get("acertou"):
        mudancas[f"{campo}.acertou"] = True
        mudancas[f"{campo}.acertou_em"] = _agora_iso()
        # Primeira tentativa é o que mede dificuldade de verdade: acerto na
        # terceira mede persistência, não entendimento.
        mudancas[f"{campo}.acertou_de_primeira"] = not anterior.get("tentativas")

    # `$inc` e não `$set` do valor calculado: o contador de tentativas é a
    # única coisa aqui que duas requisições simultâneas do mesmo aluno (duplo
    # clique, retry do axios) incrementariam para o MESMO número, perdendo uma.
    # O `$inc` é atômico no servidor do Mongo; a leitura logo abaixo devolve o
    # valor real, que é o que vira o degrau da devolutiva.
    await _escrever(uid, estacao, {
        "$set": mudancas, "$inc": {f"{campo}.tentativas": 1},
    })
    tentativa = int(anterior.get("tentativas", 0)) + 1

    await _evento(
        uid, estacao,
        evento="desafio_respondido" if bloco["tipo"] == "desafio" else "exercicio_respondido",
        bloco_id=bloco_id,
        nivel=bloco.get("nivel"),
        formato=bloco.get("formato"),
        acertou=acertou,
        chave=chave,
        tentativa=tentativa,
        de_primeira=acertou and tentativa == 1,
        tempo_segundos=tempo_segundos,
        # O que o aluno DIGITOU, nos formatos em que `chave` não guarda isso
        # (numérico e texto curto viram só "correto"/"incorreto"). É a
        # matéria-prima de "que erro específico a turma comete" — e é o campo
        # que o contrato canônico de behavior não tem onde guardar. Cortado
        # porque um campo livre de cliente não pode ser ilimitado.
        resposta=(str(resposta_bruta)[:120] if resposta_bruta is not None
                  and bloco.get("formato") != "multipla_escolha" else None),
        conceitos=list(bloco.get("conceitos") or []) or None,
        sondagem=True if sondagem else None,
    )
    return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)


async def talvez_concluir(uid: str, estacao: cc.Estacao, progresso: dict, *, nome: str | None = None) -> dict:
    """Conclui a estação se o critério do conteúdo foi cumprido. Idempotente.

    Conclusão é automática, na resposta que completa o critério, e não um
    botão: um botão que o aluno não vê deixa a estação seguinte trancada para
    sempre — trava silenciosa, do tipo que ninguém reporta e todo mundo
    abandona.

    O XP entra pelo motor de engajamento com `chave_unica`, que é a garantia
    de pagamento único: refazer a estação depois não fabrica XP.
    """
    if _db is None or esta_concluida(progresso):
        return progresso

    if acertos(progresso, estacao) < estacao.acertos_para_concluir:
        return progresso

    agora = _agora_iso()
    r = await _db.cursos_progresso.update_one(
        {
            "_id": _id(uid, estacao.curso_id, estacao.estacao_id),
            # A condição no filtro é o que torna a conclusão atômica: duas
            # respostas simultâneas não concluem duas vezes.
            "concluida_em": {"$exists": False},
        },
        {"$set": {"concluida_em": agora}},
    )
    if not r.modified_count:
        return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)

    await _evento(uid, estacao, evento="estacao_concluida")
    await _dar_xp(uid, estacao, nome=nome)
    return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)


async def _dar_xp(uid: str, estacao: cc.Estacao, *, nome: str | None, acao: str = "estacao_concluida") -> None:
    """XP pela estação concluída — e nunca duas vezes pela mesma.

    Importado aqui dentro para o módulo de progresso não depender do motor de
    engajamento na importação (e para o teste poder rodar sem ele). Falha
    aqui é engolida com log: perder o XP é aborrecimento, perder a conclusão
    do estudo é perder o estudo.
    """
    try:
        import engajamento_service

        await engajamento_service.registrar_acao(
            uid,
            [acao],
            contadores={"estacoes": 1},
            nome=nome,
            chave_unica=f"estacao:{estacao.curso_id}:{estacao.estacao_id}",
        )
    except Exception:  # noqa: BLE001
        logger.exception("XP da estação %s não registrado para %s.", estacao.estacao_id, uid)


# ---------------------------------------------------------------------------
# Sondagem de domínio — "eu já sei isto"
# ---------------------------------------------------------------------------
#
# A pergunta que esta parte responde é a mais antiga do ensino: *e quem já
# sabe?* Obrigar quem domina frações a atravessar a estação de frações não
# ensina ninguém e é o motivo mais comum de alguém fechar a aba.
#
# A resposta do produto não é um botão de "pular". É uma PROVA: três dos
# exercícios mais difíceis da estação, todos certos de primeira. Quem passa,
# passa; quem não passa, estuda — e as respostas que deu na sondagem contam
# para a estação do mesmo jeito, porque eram exercícios de verdade.
#
# O que fica gravado é a EVIDÊNCIA, não só o resultado: quais blocos foram
# perguntados, o que o aluno acertou e quando. É o que separa "o sistema
# decidiu que ele sabia" de "ele provou, e está aqui como".


def blocos_da_sondagem(estacao: cc.Estacao) -> list[dict]:
    """Os exercícios que a sondagem pergunta — os mais difíceis da estação.

    Determinístico e calculado no SERVIDOR a cada chamada: o cliente não
    escolhe, e não precisa guardar nada entre a abertura e a resposta. Ordem
    por nível decrescente, desempate pela ordem do conteúdo (que é a
    progressão escrita pelo autor), e o desafio fica de fora — ele é o teto da
    estação, não a medida de quem já sabe o conteúdo dela.
    """
    candidatos = sorted(
        enumerate(estacao.exercicios),
        key=lambda par: (-int(par[1].get("nivel") or 1), par[0]),
    )
    return [bloco for _, bloco in candidatos[:SONDAGEM_QUESTOES]]


def resultado_da_sondagem(estacao: cc.Estacao, progresso: dict) -> dict:
    """Como vai a sondagem: o que já foi respondido e se passou.

    O critério é acertar TODOS os blocos perguntados **de primeira**. A
    tentativa é contada por bloco (`respostas.<id>.tentativas`), então errar e
    tentar de novo não vira domínio — vira estudo, que é o caminho certo.
    """
    respostas = progresso.get("respostas") or {}
    blocos = blocos_da_sondagem(estacao)
    respondidos, certos = 0, 0
    for bloco in blocos:
        r = respostas.get(bloco["bloco_id"]) or {}
        if r.get("tentativas"):
            respondidos += 1
        if r.get("acertou_de_primeira"):
            certos += 1
    return {
        "blocos": [b["bloco_id"] for b in blocos],
        "total": len(blocos),
        "respondidos": respondidos,
        "acertos_de_primeira": certos,
        "completa": respondidos >= len(blocos),
        "aprovado": bool(blocos) and certos >= len(blocos),
    }


async def abrir_sondagem(uid: str, estacao: cc.Estacao) -> dict:
    """Registra que o aluno pediu para provar domínio, e devolve o estado.

    `$inc` em `dominio.tentativas` e uma tentativa só por estação: repetir a
    sondagem até passar seria força bruta com quatro alternativas, não
    evidência. Quem não passou tem o caminho de sempre — estudar a estação.
    """
    if _db is None:
        return {}
    progresso = await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)
    ja = (progresso.get("dominio") or {}).get("tentativas") or 0
    if ja >= SONDAGEM_TENTATIVAS:
        return progresso

    await _escrever(uid, estacao, {
        "$inc": {"dominio.tentativas": 1},
        "$set": {"dominio.aberta_em": _agora_iso()},
    })
    await _evento(uid, estacao, evento="dominio_sondagem_aberta")
    return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)


async def talvez_pular(
    uid: str, estacao: cc.Estacao, progresso: dict, *, nome: str | None = None,
) -> dict:
    """Marca a estação como PULADA se a sondagem foi aprovada. Idempotente.

    Nunca escreve `concluida_em`. A estação seguinte abre por `esta_vencida`, e
    a diferença entre ter estudado e ter provado continua legível para sempre
    — para o aluno, para o painel e para a Mentis. O XP entra pela ação
    `estacao_dominada`, que divide a `chave_unica` com a conclusão: uma
    estação paga XP uma vez.
    """
    if _db is None or esta_vencida(progresso):
        return progresso

    resultado = resultado_da_sondagem(estacao, progresso)
    if not resultado["aprovado"]:
        return progresso

    agora = _agora_iso()
    r = await _db.cursos_progresso.update_one(
        {
            "_id": _id(uid, estacao.curso_id, estacao.estacao_id),
            "pulada_em": {"$exists": False},
            "concluida_em": {"$exists": False},
        },
        {"$set": {
            "pulada_em": agora,
            # A evidência, e não só o veredito: quais exercícios foram
            # perguntados e como ele foi. Sem isto, "pulou" é uma afirmação
            # sem lastro no dia em que alguém perguntar por quê.
            "dominio.aprovado_em": agora,
            "dominio.blocos": resultado["blocos"],
            "dominio.acertos_de_primeira": resultado["acertos_de_primeira"],
        }},
    )
    if not r.modified_count:
        return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)

    await _evento(
        uid, estacao,
        evento="estacao_pulada",
        blocos=resultado["blocos"],
        acertos_de_primeira=resultado["acertos_de_primeira"],
    )
    await _dar_xp(uid, estacao, nome=nome, acao="estacao_dominada")
    return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)


# ---------------------------------------------------------------------------
# O salto — "pular até aqui"
# ---------------------------------------------------------------------------
#
# A sondagem de domínio pergunta "você já sabe ESTA estação?". O salto
# pergunta outra coisa: *"você já sabe tudo daqui para trás?"* — e é a
# pergunta que interessa a quem chega no produto sabendo metade da matéria.
# Sem ela, esse aluno precisa atravessar quinze estações que não lhe ensinam
# nada para chegar onde ele trava, e é nesse trajeto que ele desiste.
#
# O sorteio é do SERVIDOR e fica GRAVADO: o cliente não escolhe o que vai ser
# perguntado e não pode trocar a prova recarregando a página. É o mesmo
# princípio da correção — quem decide é quem tem o gabarito.
#
# Nenhum Spark é creditado aqui (`cursos_recompensa.pagar_exercicio(...,
# sem_sparks=True)`): o salto não é estudo, é prova. O XP da estação pulada
# entra normalmente, pela mesma `chave_unica` da conclusão.


def estacoes_antes(curso: cc.CursoConteudo, estacao_id: str) -> list[str]:
    """As estações que vêm antes do destino, na ordem do curso.

    A ordem é a do manifesto (`ordem_das_estacoes`), que é a ordem em que o
    aluno as encontraria — e não a ordem alfabética do id nem a das trilhas
    lado a lado.
    """
    ordem = list(curso.ordem_das_estacoes)
    if estacao_id not in ordem:
        return []
    return ordem[: ordem.index(estacao_id)]


def sortear_salto(
    curso: cc.CursoConteudo, estacao_id: str, *, semente: str,
) -> list[dict]:
    """As questões do salto: uma amostra de tudo que vem antes do destino.

    Duas regras dão à amostra a forma de uma prova em vez de a de um sorteio:

    * **espalhada pelas estações** — percorre as estações em rodadas, pegando
      uma questão de cada, e só volta para a primeira quando já passou por
      todas. Um sorteio uniforme sobre o conjunto todo concentraria metade da
      prova nas estações com mais exercícios;
    * **espalhada pelos níveis** — dentro de cada estação a ordem sorteada
      alterna do fácil ao difícil, então a prova tem fácil, médio e difícil
      mesmo quando é curta.

    Determinística por `semente`: recarregar a página devolve a MESMA prova.
    Sem isso, F5 seria um sorteio novo até sair uma prova fácil.
    """
    import random

    aleatorio = random.Random(semente)
    por_estacao: list[list[dict]] = []
    for eid in estacoes_antes(curso, estacao_id):
        estacao = curso.estacoes[eid]
        # Só exercícios: o desafio é o teto da estação, não a régua de quem
        # já sabe o assunto dela.
        itens = [dict(b, _estacao=eid) for b in estacao.exercicios]
        if not itens:
            continue
        aleatorio.shuffle(itens)
        itens.sort(key=lambda b: int(b.get("nivel") or 1))
        por_estacao.append(itens)

    escolhidas: list[dict] = []
    rodada = 0
    while len(escolhidas) < SALTO_QUESTOES and por_estacao:
        restantes = [fila for fila in por_estacao if len(fila) > rodada]
        if not restantes:
            break
        aleatorio.shuffle(restantes)
        for fila in restantes:
            if len(escolhidas) >= SALTO_QUESTOES:
                break
            escolhidas.append(fila[rodada])
        rodada += 1

    return escolhidas[:SALTO_QUESTOES]


def _semente_do_salto(uid: str, curso_id: str, estacao_id: str, tentativa: int) -> str:
    return f"{uid}:{curso_id}:{estacao_id}:{tentativa}"


def resultado_do_salto(progresso: dict) -> dict:
    """Como vai a prova: quantas foram, quantas saíram certas, se passou."""
    salto = progresso.get("salto") or {}
    blocos = salto.get("blocos") or []
    respostas = salto.get("respostas") or {}
    certos = sum(1 for r in respostas.values() if r.get("acertou"))
    alvo = _acertos_para_saltar(len(blocos))
    return {
        "total": len(blocos),
        "respondidas": len(respostas),
        "acertos": certos,
        "acertos_necessarios": alvo,
        "completa": bool(blocos) and len(respostas) >= len(blocos),
        "aprovado": bool(blocos) and certos >= alvo,
        # O que ainda dá para errar. É o número que a tela precisa para a
        # prova ter tensão sem precisar explicar a regra em texto.
        "erros_restantes": max(0, (len(blocos) - alvo) - (len(respostas) - certos)),
    }


def _acertos_para_saltar(total: int) -> int:
    import math
    return math.ceil(total * SALTO_APROVACAO) if total else 0


async def abrir_salto(uid: str, curso: cc.CursoConteudo, estacao: cc.Estacao) -> dict:
    """Sorteia a prova e a GRAVA. Idempotente: reabrir devolve a mesma prova.

    O documento é o da estação de DESTINO — é dela que o salto é, e é lá que a
    tela vai procurar.
    """
    if _db is None:
        return {}
    progresso = await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)
    salto = progresso.get("salto") or {}
    if salto.get("blocos"):
        return progresso

    tentativa = int(salto.get("tentativas") or 0) + 1
    semente = _semente_do_salto(uid, estacao.curso_id, estacao.estacao_id, tentativa)
    escolhidas = sortear_salto(curso, estacao.estacao_id, semente=semente)
    if not escolhidas:
        return progresso

    await _escrever(uid, estacao, {
        "$set": {
            "salto.aberto_em": _agora_iso(),
            "salto.tentativas": tentativa,
            "salto.blocos": [
                {"estacao_id": b["_estacao"], "bloco_id": b["bloco_id"]} for b in escolhidas
            ],
        },
    }, abre_estacao=False)
    await _evento(uid, estacao, evento="salto_aberto", questoes=len(escolhidas))
    return await progresso_da_estacao(uid, estacao.curso_id, estacao.estacao_id)


async def registrar_resposta_do_salto(
    uid: str,
    estacao_alvo: cc.Estacao,
    origem: cc.Estacao,
    bloco: dict,
    *,
    acertou: bool,
    chave: str,
    tempo_segundos: float | None = None,
) -> dict:
    """Grava uma resposta da prova NO DOCUMENTO DO SALTO, e não no da estação
    de onde a questão veio.

    É a diferença entre estudar e ser avaliado: marcar a questão como
    respondida na estação de origem faria o aluno que reprovou encontrar
    metade das estações "em andamento" sem nunca tê-las aberto — e daria a
    ela um acerto que ele não conquistou estudando.
    """
    if _db is None:
        return {}
    campo = f"salto.respostas.{bloco['bloco_id']}"
    await _escrever(uid, estacao_alvo, {
        "$set": {
            f"{campo}.acertou": acertou,
            f"{campo}.chave": chave,
            f"{campo}.estacao_id": origem.estacao_id,
            f"{campo}.em": _agora_iso(),
        },
    }, abre_estacao=False)
    await _evento(
        uid, origem,
        evento="salto_respondido",
        bloco_id=bloco["bloco_id"],
        nivel=bloco.get("nivel"),
        acertou=acertou,
        chave=chave,
        alvo=estacao_alvo.estacao_id,
        tempo_segundos=tempo_segundos,
    )
    return await progresso_da_estacao(uid, estacao_alvo.curso_id, estacao_alvo.estacao_id)


async def talvez_saltar(
    uid: str, curso: cc.CursoConteudo, estacao: cc.Estacao, progresso: dict,
    *, nome: str | None = None,
) -> list[str]:
    """Se a prova passou, marca TODAS as estações anteriores como puladas.

    Devolve a lista do que foi pulado agora. Cada estação recebe o mesmo
    tratamento de uma sondagem aprovada — `pulada_em`, nunca `concluida_em` —
    e a evidência aponta para a prova que a liberou, para a decisão continuar
    auditável depois de o aluno ter esquecido que a fez.
    """
    if _db is None:
        return []
    resultado = resultado_do_salto(progresso)
    if not resultado["completa"] or not resultado["aprovado"]:
        return []

    agora = _agora_iso()
    puladas: list[str] = []
    progresso_curso = await progresso_do_curso(uid, estacao.curso_id)

    for eid in estacoes_antes(curso, estacao.estacao_id):
        if esta_vencida(progresso_curso.get(eid) or {}):
            continue
        anterior = curso.estacoes[eid]
        await _escrever(uid, anterior, {"$set": {
            "pulada_em": agora,
            "dominio.aprovado_em": agora,
            "dominio.via": "salto",
            "dominio.alvo": estacao.estacao_id,
            "dominio.acertos": resultado["acertos"],
            "dominio.questoes": resultado["total"],
        }})
        await _evento(uid, anterior, evento="estacao_pulada", via="salto", alvo=estacao.estacao_id)
        await _dar_xp(uid, anterior, nome=nome, acao="estacao_dominada")
        puladas.append(eid)

    await _escrever(uid, estacao, {"$set": {"salto.aprovado_em": agora}}, abre_estacao=False)
    await _evento(
        uid, estacao, evento="salto_aprovado",
        puladas=len(puladas), acertos=resultado["acertos"], questoes=resultado["total"],
    )
    return puladas


# ---------------------------------------------------------------------------
# Eventos — só escrita
# ---------------------------------------------------------------------------


async def _evento(uid: str, estacao: cc.Estacao, *, evento: str, **campos) -> None:
    """Acrescenta uma linha ao histórico de comportamento do curso.

    Append-only e **nunca lido no caminho do aluno**. É o que permite
    responder depois, sem instrumentar nada de novo: em que bloco a turma
    para, qual alternativa errada atrai mais gente, quanto tempo leva cada
    exercício, quantos chegam ao fim da trilha.

    Nunca derruba a ação que o chamou: um evento perdido é um buraco na
    análise; uma exceção aqui seria uma resposta de aluno perdida.
    """
    if _db is None:
        return
    tempo = campos.pop("tempo_segundos", None)
    if isinstance(tempo, (int, float)):
        tempo = max(0.0, min(float(tempo), TEMPO_MAXIMO_SEGUNDOS))
    else:
        tempo = None

    doc = {
        "evento": evento,
        "uid": uid,
        "curso_id": estacao.curso_id,
        "trilha_id": estacao.trilha_id,
        "estacao_id": estacao.estacao_id,
        "versao_conteudo": estacao.versao,
        "criado_em": _agora_iso(),
        "dia": fs.dia_local(),
        **{k: v for k, v in campos.items() if v is not None},
    }
    if tempo is not None:
        doc["tempo_segundos"] = tempo
    try:
        await _db.cursos_eventos.insert_one(doc)
    except Exception:  # noqa: BLE001
        logger.exception("Evento %s do curso %s não gravado.", evento, estacao.curso_id)
