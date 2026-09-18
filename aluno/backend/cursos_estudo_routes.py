"""Estudar um curso: abrir a trilha, abrir uma estação, responder, avançar.

Separado de `cursos_routes` de propósito. Aquele módulo é a **vitrine** (o que
se vende, por quanto, quem já pagou, o link da live de quinta); este é a
**sala de aula** (o que se estuda, em que ordem, o que já foi feito). Os dois
mudam por motivos diferentes e em ritmos diferentes: preço e pré-venda mudam
por decisão comercial, conteúdo e progressão mudam por decisão pedagógica.

O que este módulo NÃO faz
-------------------------
**Não cobra nada.** Nenhum Spark é debitado aqui e nenhum preço é lido. A
única pergunta de dinheiro que ele faz é binária e vem de fora: *este aluno
tem acesso a este curso?* — que já tem uma resposta em `cursos_routes` (comprou
por 500 Sparks) e em `sparks_store.DIREITOS` (o pacote de 4.000 inclui o
catálogo). Um curso liberado é liberado inteiro: cobrar por estação
transformaria uma aula num caixa registradora.

**Não decide o que está liberado.** Quem decide é `cursos_progresso`, e é a
mesma função para a tela do mapa e para a porta da estação.

**Não inventa conteúdo.** Se não existe arquivo em `conteudo/cursos/<id>/`, a
rota devolve `tem_conteudo: false` e a aba continua sendo a pré-venda que já
era. É o estado normal de um curso antes de o conteúdo ser escrito, não um
erro.

Custo de uma abertura de tela
-----------------------------
Mapa da trilha: **1 consulta ao Mongo** (todo o progresso do aluno naquele
curso) e **no máximo 1 leitura do Firestore** (só quando não há documento de
compra, para conferir o direito do pacote). O conteúdo em si é memória — a
biblioteca é carregada uma vez no boot.

Nada aqui lê `cursos_eventos`. Essa coleção cresce com o uso e existe só para
análise; lê-la numa tela de aluno seria repetir o erro que derrubou o app em
2026-09-04.

O admin entra sem comprar
-------------------------
De propósito, e não por conveniência: é assim que se valida uma estação recém
escrita em produção antes de abrir o curso para alguém. O painel
`/admin/cursos/conteudo` mostra o inventário e os problemas de carga, e
recarrega do disco sem reiniciar o processo.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

import cursos
import cursos_comportamento as cb
import cursos_conteudo as cc
import cursos_ingestao as ci
import cursos_progresso as cp
import cursos_publicados as cpub
import cursos_recompensa as cr
import firestore_service as fs
import mentis_routes
import rate_limit
from auth import require_admin, require_user
from models import User

logger = logging.getLogger("sapiens.cursos.estudo")

router = APIRouter(prefix="/cursos", tags=["cursos-estudo"])
router_admin = APIRouter(prefix="/admin/cursos", tags=["cursos-admin"])

_db = None

# Teto de eventos lidos por curso no painel de análise. A agregação é feita em
# Python sobre um `find` limitado, e não com `$group`, porque o volume é de
# milhares e não de milhões enquanto o produto valida as primeiras estações —
# quando passar disso, o lugar de mudar é `_analise`, sozinho.
TETO_DE_EVENTOS = 20000


def set_db(db):
    global _db
    _db = db
    cp.set_db(db)
    cpub.set_db(db)


# ---------------------------------------------------------------------------
# Acesso
# ---------------------------------------------------------------------------


async def _tem_acesso(user: User, curso_id: str) -> bool:
    """Comprou, ganhou no pacote, ou é admin.

    A ordem importa para o custo: o documento de compra é uma consulta ao
    Mongo e resolve o caso de quem pagou avulso; só quem não o tem paga a
    leitura do Firestore que confere o direito do pacote.

    **O custo que sobra, e por que é aceitável.** Para quem entrou pelo pacote
    de 4.000 Sparks não existe documento de compra (é uma decisão de produto,
    ver `cursos_routes.comprar_curso`), então cada ação dentro do curso custa
    UMA leitura do Firestore. É O(1) por ação, como toda cobrança do produto
    (`mentis_routes._cobrar` faz o mesmo por mensagem) — e não O(histórico),
    que é a classe que derrubou o app em 2026-09-04. Se um dia doer, o lugar
    de resolver é aqui, com cache curto de processo; o que NÃO se pode fazer é
    deduzir acesso do progresso já gravado, que seria autorizar pelo próprio
    rastro de quem já entrou.
    """
    if user.is_admin:
        return True
    if _db is not None:
        doc = await _db.cursos_acessos.find_one({"_id": f"{user.user_id}:{curso_id}"}, {"_id": 1})
        if doc:
            return True
    return fs.tem_cursos_inclusos(user.user_id)


async def _exigir(user: User, curso_id: str) -> tuple[cursos.Curso, cc.CursoConteudo]:
    """Curso existe, tem conteúdo publicado e este aluno pode entrar.

    403 e não 404 quando falta acesso: dizer "não existe" a quem pode comprar
    esconde justamente o que está à venda. O 404 fica para curso que não está
    no catálogo, que é erro de endereço.
    """
    # Uma estação publicada pelo painel em OUTRA máquina precisa chegar aqui
    # sozinha. A conferência é limitada no tempo e minúscula (ver
    # `cursos_publicados.garantir_atual`) — nada aqui pode custar uma leitura
    # por requisição.
    await cpub.garantir_atual()

    curso = cursos.get_curso(curso_id)
    if curso is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    conteudo = cc.biblioteca().curso(curso_id)
    if conteudo is None or not conteudo.estacoes:
        raise HTTPException(
            status_code=404,
            detail="Este curso ainda não tem aulas publicadas.",
        )

    if not await _tem_acesso(user, curso_id):
        raise HTTPException(
            status_code=403,
            detail="Você ainda não tem acesso a este curso.",
        )
    return curso, conteudo


# ---------------------------------------------------------------------------
# Aluno
# ---------------------------------------------------------------------------


@router.get("/{curso_id}/trilha")
async def ver_trilha(curso_id: str, user: User = Depends(require_user)):
    """O mapa do curso para este aluno: trilhas, estações e o estado de cada uma.

    Devolve também `proxima` — a estação por onde continuar. A tela não
    recalcula isso: "onde eu parei" é decisão do servidor, senão duas telas do
    produto apontam para estações diferentes na mesma tarde.
    """
    curso, conteudo = await _exigir(user, curso_id)
    progresso = await cp.progresso_do_curso(user.user_id, curso_id)
    trilhas = cp.mapa_de_estados(conteudo, progresso)

    total = sum(t["total"] for t in trilhas)
    concluidas = sum(t["concluidas"] for t in trilhas)
    todas = [e for t in trilhas for e in t["estacoes"]]

    return {
        "curso": {
            "curso_id": curso.curso_id,
            "titulo": curso.titulo,
            "chamada": curso.chamada,
            "descricao": curso.descricao,
            "area": curso.area,
            "categoria": curso.categoria,
            "nivel": curso.nivel,
            "status": curso.status,
            "versao_conteudo": conteudo.versao,
            "duracao_minutos": sum(
                e.duracao_minutos or 0 for e in conteudo.estacoes.values()
            ),
        },
        "trilhas": trilhas,
        "progresso": {
            "estacoes": total,
            "concluidas": concluidas,
            "estudadas": sum(t["estudadas"] for t in trilhas),
            "puladas": sum(t["puladas"] for t in trilhas),
            "percentual": round(100 * concluidas / total) if total else 0,
            # O teto do curso, somado da mesma tabela que paga. A tela anuncia
            # isto antes de o aluno começar, e não pode inventar o número.
            "xp_possivel": sum(e["xp_possivel"] for e in todas),
            "sparks_possiveis": sum(e["sparks_possiveis"] for e in todas),
            "exercicios": sum(e["exercicios"] for e in todas),
        },
        "proxima": cp.proxima_estacao(conteudo, progresso),
    }


def _estacao_ou_404(conteudo: cc.CursoConteudo, estacao_id: str) -> cc.Estacao:
    estacao = conteudo.estacoes.get(estacao_id)
    if estacao is None:
        raise HTTPException(status_code=404, detail="Estação não encontrada neste curso.")
    return estacao


@router.get("/{curso_id}/estacoes/{estacao_id}")
async def abrir_estacao(curso_id: str, estacao_id: str, user: User = Depends(require_user)):
    """A estação inteira, já sem gabarito, mais o que este aluno já fez nela.

    Gabarito, dica, feedback e solução ficam no servidor (`sanitizar_bloco`):
    quem corrige é a rota de resposta, e cada uma dessas coisas chega ao aluno
    no momento em que ela ensina algo. Mandar tudo e esconder na tela seria
    publicar a prova junto com o gabarito.
    """
    _, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)

    progresso_curso = await cp.progresso_do_curso(user.user_id, curso_id)
    if not cp.estacao_liberada(conteudo, estacao_id, progresso_curso):
        raise HTTPException(
            status_code=423,
            detail="Conclua a estação anterior para abrir esta.",
        )

    progresso = await cp.iniciar(user.user_id, estacao)
    respostas = progresso.get("respostas") or {}

    return {
        "curso_id": curso_id,
        "estacao": {
            "estacao_id": estacao.estacao_id,
            "trilha_id": estacao.trilha_id,
            "titulo": estacao.titulo,
            "objetivo": estacao.objetivo,
            "duracao_minutos": estacao.duracao_minutos,
            "habilidades": list(estacao.habilidades),
            "versao": estacao.versao,
            "blocos": [
                _para_a_tela(b)
                for b in estacao.blocos
                # Vídeo sem `ref` é lugar reservado para gravação futura: não
                # vai para a tela, para o aluno não ver um player quebrado.
                if not (b["tipo"] == "video" and not b.get("ref"))
            ],
            "acertos_para_concluir": estacao.acertos_para_concluir,
            "exercicios_que_contam": [b["bloco_id"] for b in estacao.exercicios],
        },
        "progresso": {
            "blocos_vistos": progresso.get("blocos_vistos") or [],
            "concluida_em": progresso.get("concluida_em"),
            # Pulada por domínio é estado da PORTA da estação, não só do mapa:
            # sem ele, a sala de aula ofereceria "já domino isto" a quem
            # acabou de provar que domina.
            "pulada_em": progresso.get("pulada_em"),
            "sondagem_usada": bool((progresso.get("dominio") or {}).get("tentativas")),
            "acertos": cp.acertos(progresso, estacao),
            # Só o que a tela precisa para redesenhar o que já foi respondido:
            # se acertou e quantas vezes tentou. Nunca o que era a resposta.
            "respostas": {
                bid: {
                    "acertou": bool(r.get("acertou")),
                    "tentativas": int(r.get("tentativas", 0)),
                }
                for bid, r in respostas.items()
            },
        },
        "navegacao": _vizinhas(conteudo, estacao),
    }


def _para_a_tela(bloco: dict) -> dict:
    """O bloco sanitizado, mais o preço quando ele existe.

    O preço é acrescentado AQUI e nunca dentro de `sanitizar_bloco`: o hash do
    item em `cursos_comportamento` é calculado sobre o bloco sanitizado, e uma
    mudança de preço passaria a reescrever o histórico de todo mundo como se
    a questão tivesse mudado. Ele também não mora no conteúdo — preço é
    decisão de produto, e o contrato recusa arquivo que declare um.
    """
    limpo = cc.sanitizar_bloco(bloco)
    if bloco.get("formato") == "dissertativo":
        limpo["custo_correcao"] = mentis_routes.DISSERTATIVA_COST
    return limpo


def _vizinhas(conteudo: cc.CursoConteudo, estacao: cc.Estacao) -> dict:
    """Anterior e seguinte DENTRO da trilha — é a leitura que o aluno faz.

    Atravessar para a trilha do lado seria "seguinte" pelo arquivo e surpresa
    pelo produto.
    """
    trilha = next((t for t in conteudo.trilhas if t.trilha_id == estacao.trilha_id), None)
    if trilha is None:
        return {"anterior": None, "seguinte": None}
    ids = list(trilha.estacoes)
    i = ids.index(estacao.estacao_id)

    def _resumo(eid: str | None) -> dict | None:
        if eid is None:
            return None
        e = conteudo.estacoes[eid]
        return {"estacao_id": eid, "titulo": e.titulo}

    return {
        "anterior": _resumo(ids[i - 1] if i > 0 else None),
        "seguinte": _resumo(ids[i + 1] if i + 1 < len(ids) else None),
    }


@router.post("/{curso_id}/estacoes/{estacao_id}/blocos/{bloco_id}/visto")
async def marcar_visto(
    curso_id: str, estacao_id: str, bloco_id: str, user: User = Depends(require_user),
):
    """Texto lido, exemplo percorrido, vídeo assistido.

    Não conclui nada e não vale XP: é sinal de percurso, e é dele que sai a
    resposta para "em que bloco a turma para de ler".
    """
    _, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)
    if estacao.bloco(bloco_id) is None:
        raise HTTPException(status_code=404, detail="Bloco não encontrado nesta estação.")

    progresso = await cp.marcar_bloco_visto(user.user_id, estacao, bloco_id)
    return {"ok": True, "blocos_vistos": progresso.get("blocos_vistos") or []}


class RespostaDeSondagem(BaseModel):
    """Igual à resposta comum, mais o bloco — a sondagem responde fora de
    ordem e o endereço do exercício não está na URL."""
    bloco_id: str = Field(..., min_length=1, max_length=120)
    resposta: object = Field(default=None)
    tempo_segundos: float | None = Field(default=None, ge=0)


class RespostaRequest(BaseModel):
    # `resposta` é livre porque o formato manda: id de alternativa (str),
    # número (int/float) ou texto curto. Quem interpreta é `cc.corrigir`, que
    # conhece o formato do bloco — validar aqui exigiria duplicar essa tabela.
    resposta: object = Field(default=None)
    tempo_segundos: float | None = Field(default=None, ge=0)


@router.post("/{curso_id}/estacoes/{estacao_id}/blocos/{bloco_id}/resposta")
async def responder(
    curso_id: str,
    estacao_id: str,
    bloco_id: str,
    payload: RespostaRequest = Body(default_factory=RespostaRequest),
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cursos_estudo")),
):
    """Corrige, grava a tentativa e devolve o feedback que essa tentativa merece.

    A correção é SEMPRE do servidor, e a escada didática também: dica no
    primeiro erro, comentário do erro específico no segundo, resolução no
    terceiro (ver `cc.feedback_da_tentativa`). O cliente não recebe nada que
    lhe permita antecipar o próximo degrau.

    Se esta resposta cumpriu o critério da estação, ela é concluída AQUI
    mesmo — automaticamente. Um botão de "concluir" que o aluno não visse
    deixaria a estação seguinte trancada para sempre, e esse tipo de trava
    ninguém reporta: abandona.
    """
    _, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)

    progresso_curso = await cp.progresso_do_curso(user.user_id, curso_id)
    if not cp.estacao_liberada(conteudo, estacao_id, progresso_curso):
        raise HTTPException(status_code=423, detail="Esta estação ainda não está liberada.")

    bloco = estacao.bloco(bloco_id)
    if bloco is None or bloco["tipo"] not in ("exercicio", "desafio"):
        raise HTTPException(status_code=404, detail="Este bloco não é um exercício.")
    if bloco.get("formato") == "dissertativo":
        # Não é detalhe de rota: `cc.corrigir` LEVANTA nesse formato, de
        # propósito. Quem corrige texto é a Mentis, por Sparks, e o aluno
        # precisa saber disso antes de escrever — nunca depois de enviar.
        raise HTTPException(
            status_code=409,
            detail="Esta questão é dissertativa: a resposta vai para a correção da Mentis.",
        )

    return await _corrigir_e_pagar(user, estacao, bloco, payload)


async def _corrigir_e_pagar(
    user: User, estacao: cc.Estacao, bloco: dict, payload: "RespostaRequest", *,
    sondagem: bool = False, sem_sparks: bool = False,
    veredito: tuple[bool, str] | None = None,
) -> dict:
    """O caminho ÚNICO de toda resposta de curso — o estudo e a sondagem.

    A ordem aqui é a ordem das garantias, e ela não é estética:

    1. **corrigir** (servidor, sempre);
    2. **gravar o progresso** — é o que o aluno perde se algo abaixo falhar,
       então vem primeiro;
    3. **registrar o comportamento** no contrato canônico, o mesmo do ENEM;
    4. **pagar** Spark e XP, cada um com sua guarda de unicidade;
    5. **concluir** a estação, se esta resposta cumpriu o critério.

    Nada dos passos 3 e 4 pode derrubar os passos 1 e 2: os dois engolem as
    próprias falhas (ver `cursos_comportamento` e `cursos_recompensa`).
    """
    bloco_id = bloco["bloco_id"]
    # `veredito` só chega preenchido no dissertativo, onde quem julgou foi a
    # Mentis (e a régua de acerto, o servidor). Todo o resto do caminho —
    # progresso, comportamento, Spark, conclusão — é exatamente o mesmo.
    acertou, chave = veredito if veredito else cc.corrigir(bloco, payload.resposta)
    progresso = await cp.registrar_resposta(
        user.user_id, estacao, bloco,
        acertou=acertou, chave=chave, tempo_segundos=payload.tempo_segundos,
        resposta_bruta=payload.resposta, sondagem=sondagem,
    )
    tentativa = int(((progresso.get("respostas") or {}).get(bloco_id) or {}).get("tentativas", 1))

    await cb.registrar(
        user.user_id,
        estacao=estacao,
        bloco=bloco,
        acertou=acertou,
        alternativa=cb.alternativa_registravel(bloco, payload.resposta),
        tentativa=tentativa,
        tempo_segundos=payload.tempo_segundos,
        sondagem=sondagem,
    )

    ganho = await cr.pagar_exercicio(
        user.user_id,
        curso_id=estacao.curso_id,
        estacao_id=estacao.estacao_id,
        bloco=bloco,
        acertou=acertou,
        tentativa=tentativa,
        nome=user.name,
        sem_sparks=sem_sparks,
    )

    antes = cp.esta_concluida(progresso)
    progresso = await cp.talvez_concluir(user.user_id, estacao, progresso, nome=user.name)
    concluiu_agora = cp.esta_concluida(progresso) and not antes

    return {
        **cc.feedback_da_tentativa(bloco, chave, acertou, tentativa),
        "bloco_id": bloco_id,
        # `gabarito` só depois de acertar, e como id de alternativa — é o que
        # a tela usa para pintar a certa. Enquanto erra, ele não sai daqui.
        "gabarito": bloco.get("gabarito") if (acertou and bloco.get("formato") == "multipla_escolha") else None,
        "acertos": cp.acertos(progresso, estacao),
        "acertos_para_concluir": estacao.acertos_para_concluir,
        "estacao_concluida": cp.esta_concluida(progresso),
        "concluiu_agora": concluiu_agora,
        # O que ENTROU AGORA no saldo e no XP — nunca o que a questão "vale".
        # Refazer um exercício já pago devolve zero, e a devolutiva precisa
        # dizer zero: anunciar "+1 Spark" sem creditar é o jeito mais rápido
        # de fazer o aluno desconfiar do saldo inteiro.
        "recompensa": ganho,
    }


class DissertativaRequest(BaseModel):
    resposta: str = Field(default="", max_length=4000)
    tempo_segundos: float | None = Field(default=None, ge=0)


def _impressao(texto: str) -> str:
    """A digital do que o aluno escreveu — é ela que impede a cobrança dupla.

    Duplo clique, retry do axios e "voltar e reenviar o mesmo texto" são a
    mesma resposta; cobrar 20 Sparks de novo por ela seria cobrar pelo
    recarregamento da página. Texto DIFERENTE é uma correção nova, e essa
    custa: é um pedido novo à Mentis, com trabalho novo.
    """
    return hashlib.sha256(" ".join((texto or "").split()).lower().encode()).hexdigest()[:24]


@router.post("/{curso_id}/estacoes/{estacao_id}/blocos/{bloco_id}/dissertativa")
async def responder_dissertativa(
    curso_id: str,
    estacao_id: str,
    bloco_id: str,
    payload: DissertativaRequest = Body(default_factory=DissertativaRequest),
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    """A resposta escrita vai para a correção da Mentis, por Sparks.

    A ordem aqui é a das garantias, e ela custa dinheiro se estiver errada:

    1. **acesso e liberação**, antes de qualquer cobrança;
    2. **correção já feita?** — o mesmo texto devolve a mesma correção, de
       graça. Só depois disso alguém é cobrado;
    3. **Mentis corrige e cobra** (e devolve os Sparks se falhar);
    4. **guarda a correção** pela digital do texto;
    5. **o caminho normal de resposta** — progresso, comportamento, Spark de
       exercício e conclusão da estação, idênticos aos da múltipla escolha.
    """
    _, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)

    progresso_curso = await cp.progresso_do_curso(user.user_id, curso_id)
    if not cp.estacao_liberada(conteudo, estacao_id, progresso_curso):
        raise HTTPException(status_code=423, detail="Esta estação ainda não está liberada.")

    bloco = estacao.bloco(bloco_id)
    if bloco is None or bloco.get("formato") != "dissertativo":
        raise HTTPException(status_code=404, detail="Esta questão não é dissertativa.")

    digital = _impressao(payload.resposta)
    chave = {"uid": user.user_id, "estacao_id": estacao_id, "bloco_id": bloco_id, "digital": digital}
    guardada = await _db.cursos_dissertativas.find_one(chave, {"_id": 0, "correcao": 1}) if _db is not None else None
    if guardada and guardada.get("correcao"):
        return {**guardada["correcao"], "cobrado": 0, "repetida": True}

    correcao = await mentis_routes.corrigir_dissertativa(
        user.user_id,
        enunciado=bloco.get("enunciado", ""),
        criterios=list(bloco.get("criterios") or []),
        referencia=bloco.get("referencia", ""),
        resposta=payload.resposta,
    )

    if _db is not None:
        try:
            await _db.cursos_dissertativas.update_one(
                chave,
                {"$set": {**chave, "correcao": correcao, "curso_id": curso_id,
                          "resposta": payload.resposta,
                          "em": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
        except Exception:  # noqa: BLE001
            # Guardar é o que evita a SEGUNDA cobrança, não o que entrega a
            # primeira correção: falhar aqui não pode custar ao aluno a
            # correção que ele acabou de pagar.
            logger.exception("Não deu para guardar a correção dissertativa de %s.", user.user_id)

    resto = await _corrigir_e_pagar(
        user, estacao, bloco,
        RespostaRequest(resposta=payload.resposta, tempo_segundos=payload.tempo_segundos),
        veredito=(correcao["acertou"], "correto" if correcao["acertou"] else "incorreto"),
    )
    return {**resto, **correcao, "cobrado": mentis_routes.DISSERTATIVA_COST, "repetida": False}


@router.post("/{curso_id}/estacoes/{estacao_id}/blocos/{bloco_id}/explicar")
async def explicar_bloco(
    curso_id: str,
    estacao_id: str,
    bloco_id: str,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    """"Explicar melhor" um trecho de leitura (texto, tabela ou exemplo) por
    `mentis_routes.EXPLICACAO_CONTEUDO_COST` Sparks.

    O texto NUNCA vem do cliente — é resolvido aqui, de dentro do conteúdo
    publicado, depois de confirmar que o aluno tem acesso ao curso. Exercício
    e desafio não têm este botão: o que se pede ali é a devolutiva da
    resposta, não uma explicação do enunciado.
    """
    curso, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)
    bloco = estacao.bloco(bloco_id)
    if bloco is None or bloco.get("tipo") not in ("texto", "tabela", "exemplo"):
        raise HTTPException(status_code=404, detail="Este trecho não pode ser explicado.")

    texto_fonte = mentis_routes.texto_do_bloco(bloco)
    if not texto_fonte.strip():
        raise HTTPException(status_code=409, detail="Este trecho não tem conteúdo para explicar.")

    return await mentis_routes.explicar_trecho(
        user.user_id,
        origem="curso",
        ref_id=f"{curso_id}:{estacao_id}:{bloco_id}:{estacao.versao}",
        contexto=f'Curso "{curso.titulo}", estação "{estacao.titulo}" ({estacao.objetivo})',
        texto_fonte=texto_fonte,
    )


# ---------------------------------------------------------------------------
# "Já domino este conteúdo"
# ---------------------------------------------------------------------------


@router.post("/{curso_id}/estacoes/{estacao_id}/dominio")
async def abrir_sondagem(
    curso_id: str, estacao_id: str, user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cursos_estudo")),
):
    """Começa a sondagem de domínio: três exercícios, os mais difíceis da estação.

    Não é um botão de pular. É a chance de PROVAR que já sabe — e o preço de
    usá-la é que ela vale uma vez: quem erra estuda a estação, que é o
    caminho de sempre e continua inteiro (as respostas dadas aqui já contam).

    As questões saem do servidor a cada chamada, sempre as mesmas para a mesma
    estação: o cliente não escolhe o que vai ser perguntado, e não precisa
    guardar estado nenhum entre abrir e responder.
    """
    _, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)

    progresso_curso = await cp.progresso_do_curso(user.user_id, curso_id)
    if not cp.estacao_liberada(conteudo, estacao_id, progresso_curso):
        raise HTTPException(status_code=423, detail="Esta estação ainda não está liberada.")

    atual = progresso_curso.get(estacao_id) or {}
    if cp.esta_vencida(atual):
        raise HTTPException(
            status_code=409,
            detail="Esta estação já está concluída — não há o que pular.",
        )
    if ((atual.get("dominio") or {}).get("tentativas") or 0) >= cp.SONDAGEM_TENTATIVAS:
        raise HTTPException(
            status_code=409,
            detail=(
                "Você já usou a avaliação de domínio desta estação. "
                "Para avançar, estude a estação — o que você já respondeu continua valendo."
            ),
        )

    progresso = await cp.abrir_sondagem(user.user_id, estacao)
    blocos = cp.blocos_da_sondagem(estacao)
    return {
        "curso_id": curso_id,
        "estacao_id": estacao_id,
        "titulo": estacao.titulo,
        "objetivo": estacao.objetivo,
        "regra": {
            "questoes": len(blocos),
            # O critério, por extenso e ANTES de começar. Descobrir depois que
            # um erro custava a chance seria uma armadilha, não uma sondagem.
            "acertos_necessarios": len(blocos),
            "de_primeira": True,
        },
        "blocos": [cc.sanitizar_bloco(b) for b in blocos],
        "resultado": cp.resultado_da_sondagem(estacao, progresso),
    }


@router.post("/{curso_id}/estacoes/{estacao_id}/dominio/resposta")
async def responder_sondagem(
    curso_id: str,
    estacao_id: str,
    payload: RespostaDeSondagem = Body(...),
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cursos_estudo")),
):
    """Responde um exercício da sondagem. Mesmo caminho de uma resposta normal.

    Deliberadamente **a mesma correção, o mesmo registro e o mesmo pagamento**
    de um exercício estudado: eram exercícios de verdade, o acerto vale o
    Spark e o comportamento entra no histórico. O que muda é o `contexto` do
    evento (`curso_dominio`), que é justamente o que permite perguntar depois
    "como vai quem tenta pular".

    Quando a última resposta da sondagem entra, a decisão é tomada aqui: se
    todas saíram certas de primeira, a estação vira PULADA — nunca `concluida`.
    """
    _, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)

    progresso_curso = await cp.progresso_do_curso(user.user_id, curso_id)
    if not cp.estacao_liberada(conteudo, estacao_id, progresso_curso):
        raise HTTPException(status_code=423, detail="Esta estação ainda não está liberada.")

    permitidos = {b["bloco_id"] for b in cp.blocos_da_sondagem(estacao)}
    if payload.bloco_id not in permitidos:
        # O cliente não escolhe o que a sondagem pergunta. Aceitar um bloco
        # qualquer aqui deixaria o aluno "provar domínio" no exercício mais
        # fácil da estação.
        raise HTTPException(status_code=404, detail="Este exercício não faz parte da avaliação.")

    bloco = estacao.bloco(payload.bloco_id)
    resposta = await _corrigir_e_pagar(user, estacao, bloco, payload, sondagem=True)

    progresso = await cp.progresso_da_estacao(user.user_id, curso_id, estacao_id)
    antes = cp.foi_pulada(progresso)
    progresso = await cp.talvez_pular(user.user_id, estacao, progresso, nome=user.name)
    resultado = cp.resultado_da_sondagem(estacao, progresso)

    return {
        **resposta,
        "resultado": resultado,
        "estacao_pulada": cp.foi_pulada(progresso),
        "pulou_agora": cp.foi_pulada(progresso) and not antes,
        # Acabou a sondagem e não passou: a tela precisa dizer isso com todas
        # as letras, e mandar para o conteúdo em vez de deixar a pessoa
        # procurando o botão que sumiu.
        "reprovado": resultado["completa"] and not resultado["aprovado"],
    }


# ---------------------------------------------------------------------------
# "Pular até aqui" — o salto
# ---------------------------------------------------------------------------


class RespostaDoSalto(BaseModel):
    bloco_id: str = Field(..., min_length=1, max_length=120)
    resposta: object = Field(default=None)
    tempo_segundos: float | None = Field(default=None, ge=0)


def _salto_ou_erro(progresso: dict, bloco_id: str) -> dict:
    """O bloco pedido faz parte DESTA prova? O sorteio ficou gravado quando a
    prova abriu, e é ele que manda — senão o cliente escolheria as próprias
    perguntas."""
    for item in (progresso.get("salto") or {}).get("blocos") or []:
        if item.get("bloco_id") == bloco_id:
            return item
    raise HTTPException(status_code=404, detail="Esta questão não faz parte da sua avaliação.")


@router.post("/{curso_id}/saltos/{estacao_id}")
async def abrir_salto(
    curso_id: str, estacao_id: str, user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cursos_estudo")),
):
    """Abre a prova para pular direto até esta estação.

    Vinte questões sorteadas de TUDO que vem antes dela. O sorteio é do
    servidor, fica gravado e não muda se a página recarregar — F5 não é um
    sorteio novo até sair uma prova fácil.

    Não exige que a estação esteja liberada: a prova é justamente o que a
    libera. Exige que exista alguma coisa antes dela para provar.
    """
    _, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)

    progresso_curso = await cp.progresso_do_curso(user.user_id, curso_id)
    if cp.esta_vencida(progresso_curso.get(estacao_id) or {}):
        raise HTTPException(status_code=409, detail="Você já passou por esta estação.")

    anteriores = [
        e for e in cp.estacoes_antes(conteudo, estacao_id)
        if not cp.esta_vencida(progresso_curso.get(e) or {})
    ]
    if not anteriores:
        raise HTTPException(
            status_code=409,
            detail="Não há nada para pular antes desta estação.",
        )

    atual = progresso_curso.get(estacao_id) or {}
    salto = atual.get("salto") or {}
    if salto.get("aprovado_em"):
        raise HTTPException(status_code=409, detail="Você já passou nesta avaliação.")
    # Prova respondida até o fim e reprovada é tentativa GASTA. Sem esta
    # condição, reabrir devolveria a mesma prova já respondida e a única
    # coisa que ela mediria seria a paciência de recarregar a página.
    if cp.resultado_do_salto(atual)["completa"]:
        raise HTTPException(
            status_code=409,
            detail="Você já tentou pular até aqui. Tente um ponto mais próximo.",
        )
    if not salto.get("blocos") and int(salto.get("tentativas") or 0) >= cp.SALTO_TENTATIVAS:
        raise HTTPException(
            status_code=409,
            detail="Você já tentou pular até aqui. Tente um ponto mais próximo.",
        )

    progresso = await cp.abrir_salto(user.user_id, conteudo, estacao)
    return _montar_salto(conteudo, estacao, progresso)


def _montar_salto(conteudo: cc.CursoConteudo, estacao: cc.Estacao, progresso: dict) -> dict:
    """A prova como ela vai para a tela: questões sem gabarito, na ordem
    sorteada, e o que já foi respondido."""
    salto = progresso.get("salto") or {}
    respostas = salto.get("respostas") or {}
    blocos = []
    for item in salto.get("blocos") or []:
        origem = conteudo.estacoes.get(item.get("estacao_id"))
        bloco = origem.bloco(item.get("bloco_id")) if origem else None
        if bloco is None:
            continue
        blocos.append({
            **cc.sanitizar_bloco(bloco),
            # De onde a questão veio. Não é enfeite: é o que permite à tela
            # dizer "isto é da estação 07" quando o aluno erra e quer saber
            # onde estudar.
            "estacao_id": origem.estacao_id,
            "estacao_titulo": origem.titulo,
            "respondida": item.get("bloco_id") in respostas,
        })
    return {
        "curso_id": estacao.curso_id,
        "estacao_id": estacao.estacao_id,
        "titulo": estacao.titulo,
        "blocos": blocos,
        "resultado": cp.resultado_do_salto(progresso),
    }


@router.post("/{curso_id}/saltos/{estacao_id}/resposta")
async def responder_salto(
    curso_id: str,
    estacao_id: str,
    payload: RespostaDoSalto = Body(...),
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cursos_estudo")),
):
    """Responde uma questão da prova de salto.

    Corrigida e registrada como qualquer outra — o comportamento vale para o
    histórico do aluno do mesmo jeito. O que NÃO acontece aqui: Spark (o salto
    não é estudo) e progresso na estação de origem (a questão foi uma prova,
    não uma aula).

    Quando a última resposta entra, a decisão é tomada: passou, todas as
    estações anteriores viram PULADAS de uma vez.
    """
    _, conteudo = await _exigir(user, curso_id)
    estacao = _estacao_ou_404(conteudo, estacao_id)

    progresso = await cp.progresso_da_estacao(user.user_id, curso_id, estacao_id)
    salto = progresso.get("salto") or {}
    if not salto.get("blocos"):
        raise HTTPException(status_code=409, detail="Abra a avaliação antes de responder.")
    if salto.get("aprovado_em"):
        raise HTTPException(status_code=409, detail="Esta avaliação já foi concluída.")

    item = _salto_ou_erro(progresso, payload.bloco_id)
    if payload.bloco_id in (salto.get("respostas") or {}):
        raise HTTPException(status_code=409, detail="Você já respondeu esta questão.")

    origem = conteudo.estacoes.get(item["estacao_id"])
    bloco = origem.bloco(payload.bloco_id) if origem else None
    if bloco is None:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")

    acertou, chave = cc.corrigir(bloco, payload.resposta)
    progresso = await cp.registrar_resposta_do_salto(
        user.user_id, estacao, origem, bloco,
        acertou=acertou, chave=chave, tempo_segundos=payload.tempo_segundos,
    )

    await cb.registrar(
        user.user_id,
        estacao=origem,
        bloco=bloco,
        acertou=acertou,
        alternativa=cb.alternativa_registravel(bloco, payload.resposta),
        tentativa=1,
        tempo_segundos=payload.tempo_segundos,
        sondagem=True,
    )

    puladas = await cp.talvez_saltar(user.user_id, conteudo, estacao, progresso, nome=user.name)
    progresso = await cp.progresso_da_estacao(user.user_id, curso_id, estacao_id)
    resultado = cp.resultado_do_salto(progresso)

    return {
        # Sem escada de devolutiva: numa prova, a explicação depois de cada
        # questão seria aula no meio da avaliação — e entregaria o método das
        # questões seguintes.
        "bloco_id": payload.bloco_id,
        "acertou": acertou,
        "gabarito": bloco.get("gabarito") if bloco.get("formato") == "multipla_escolha" else None,
        "resultado": resultado,
        "puladas": puladas,
        "aprovado": bool(resultado["aprovado"] and resultado["completa"]),
        "reprovado": bool(resultado["completa"] and not resultado["aprovado"]),
    }


# ---------------------------------------------------------------------------
# Admin — a tela de quem produz o conteúdo
# ---------------------------------------------------------------------------


@router_admin.get("/conteudo")
async def inventario(admin: User = Depends(require_admin)):
    """O estado da produção: o que está publicado, o que está quebrado.

    `exercicios_por_nivel` é o número que responde se a progressão existe de
    verdade — um curso inteiro no nível 2 passa em todas as outras validações
    e não ensina ninguém a subir.
    """
    return cc.inventario()


@router_admin.post("/conteudo/recarregar")
async def recarregar(admin: User = Depends(require_admin)):
    """Relê a pasta de conteúdo do disco, sem reiniciar o processo.

    Existe para o ciclo de produção: publicar uma estação, abrir o painel,
    ver o que quebrou. Sem isto, toda correção de vírgula num JSON custaria um
    deploy para ser conferida.
    """
    bib = cc.recarregar()
    logger.info("Conteúdo de cursos recarregado por %s (%d curso(s)).", admin.email, len(bib.cursos))
    return cc.inventario(bib)


@router_admin.get("/conteudo/{curso_id}/analise")
async def analise(curso_id: str, admin: User = Depends(require_admin)):
    """Comportamento agregado por estação e por exercício.

    As perguntas que isto responde, e que são as que decidem o que reescrever:

    * quantos começaram cada estação e quantos chegaram ao fim dela;
    * qual exercício tem a menor taxa de acerto **de primeira** — que é a
      medida de dificuldade real, porque acerto na terceira tentativa mede
      teimosia;
    * qual alternativa errada atrai mais gente, que é o mapa dos equívocos e
      a matéria-prima do feedback da próxima versão;
    * quanto tempo cada exercício leva.

    Agregação em Python sobre um `find` limitado a `TETO_DE_EVENTOS`, e não
    `$group`: é admin, é uma vez por análise, e o volume enquanto se valida as
    primeiras estações é de milhares. Quando deixar de ser, o lugar de mudar é
    esta função.
    """
    conteudo = cc.biblioteca().curso(curso_id)
    if conteudo is None:
        raise HTTPException(status_code=404, detail="Curso sem conteúdo publicado.")

    eventos = await _db.cursos_eventos.find(
        {"curso_id": curso_id}, {"_id": 0}
    ).to_list(TETO_DE_EVENTOS)

    por_estacao: dict[str, dict] = {
        eid: {
            "estacao_id": eid,
            "titulo": est.titulo,
            "trilha_id": est.trilha_id,
            "iniciaram": 0,
            "concluiram": 0,
            "exercicios": {},
        }
        for eid, est in conteudo.estacoes.items()
    }

    for ev in eventos:
        alvo = por_estacao.get(ev.get("estacao_id"))
        if alvo is None:
            continue  # estação que saiu do conteúdo; o evento fica no histórico
        nome = ev.get("evento")
        if nome == "estacao_iniciada":
            alvo["iniciaram"] += 1
        elif nome == "estacao_concluida":
            alvo["concluiram"] += 1
        elif nome in ("exercicio_respondido", "desafio_respondido"):
            bid = ev.get("bloco_id")
            ex = alvo["exercicios"].setdefault(bid, {
                "bloco_id": bid, "nivel": ev.get("nivel"),
                "tentativas": 0, "acertos": 0, "de_primeira": 0, "primeiras": 0,
                "escolhas": {}, "tempo_total": 0.0, "com_tempo": 0,
            })
            ex["tentativas"] += 1
            if ev.get("acertou"):
                ex["acertos"] += 1
            if ev.get("tentativa") == 1:
                ex["primeiras"] += 1
                if ev.get("de_primeira"):
                    ex["de_primeira"] += 1
            chave = ev.get("chave")
            if chave:
                ex["escolhas"][chave] = ex["escolhas"].get(chave, 0) + 1
            if isinstance(ev.get("tempo_segundos"), (int, float)):
                ex["tempo_total"] += float(ev["tempo_segundos"])
                ex["com_tempo"] += 1

    estacoes = []
    for eid in conteudo.ordem_das_estacoes:
        dados = por_estacao[eid]
        exercicios = []
        for ex in dados["exercicios"].values():
            exercicios.append({
                "bloco_id": ex["bloco_id"],
                "nivel": ex["nivel"],
                "tentativas": ex["tentativas"],
                "acerto_de_primeira": (
                    round(100 * ex["de_primeira"] / ex["primeiras"]) if ex["primeiras"] else None
                ),
                "tentativas_por_acerto": (
                    round(ex["tentativas"] / ex["acertos"], 2) if ex["acertos"] else None
                ),
                "tempo_medio_segundos": (
                    round(ex["tempo_total"] / ex["com_tempo"], 1) if ex["com_tempo"] else None
                ),
                # Ordenado do mais escolhido para o menos: o topo da lista,
                # quando não é o gabarito, é o equívoco mais comum da turma.
                "escolhas": sorted(
                    ({"chave": k, "vezes": v} for k, v in ex["escolhas"].items()),
                    key=lambda x: x["vezes"], reverse=True,
                ),
            })
        estacoes.append({
            **{k: v for k, v in dados.items() if k != "exercicios"},
            "conclusao_percentual": (
                round(100 * dados["concluiram"] / dados["iniciaram"]) if dados["iniciaram"] else None
            ),
            "exercicios": exercicios,
        })

    return {
        "curso_id": curso_id,
        "versao_conteudo": conteudo.versao,
        "eventos_lidos": len(eventos),
        "teto_de_eventos": TETO_DE_EVENTOS,
        "estacoes": estacoes,
    }


# ---------------------------------------------------------------------------
# Admin — publicar conteúdo a partir de texto
# ---------------------------------------------------------------------------
#
# A pergunta que estas três rotas respondem é uma só: *como uma pessoa que
# escreveu uma aula põe essa aula no ar hoje?* Antes, a resposta era "escreva
# o JSON do contrato, abra um commit e espere o deploy" — que é a resposta
# certa para um curso inteiro e a resposta errada para uma estação.
#
# O caminho é sempre o mesmo, e a ordem importa:
#
#     texto  →  COMPILAR (nada é gravado)  →  conferir  →  PUBLICAR
#
# `compilar` existe separada de propósito. Publicar sem ver o que o texto virou
# é publicar no escuro: o compilador embaralha alternativas, reparte o feedback
# por distrator e deduz o nível, e quem escreveu precisa poder olhar isso antes
# de um aluno olhar.


class TextoDeCurso(BaseModel):
    """O que o painel manda: o curso de destino e o texto cru.

    `trilha_titulo` é o nome da parte do curso onde as estações novas entram
    ("Números e operações"). Se o curso já tiver uma trilha com aquele nome,
    elas entram no fim dela; senão, ela nasce. É a única decisão de ESTRUTURA
    que o texto não carrega — e é decisão de curso, não de estação.
    """
    curso_id: str = Field(..., min_length=1, max_length=80)
    texto: str = Field(..., min_length=1, max_length=400_000)
    trilha_titulo: str = Field(default="", max_length=120)
    trilha_resumo: str = Field(default="", max_length=240)


def _curso_do_catalogo(curso_id: str):
    curso = cursos.get_curso(curso_id)
    if curso is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"`{curso_id}` não existe no catálogo. Conteúdo só entra em curso "
                "que já está à venda — o produto (título, preço, status) é decisão "
                "de `cursos.py`, e não de um texto colado."
            ),
        )
    return curso


def _trilha_escolhida(curso_id: str, pedido: TextoDeCurso) -> dict:
    """Onde as estações novas vão morar dentro do curso."""
    titulo = (pedido.trilha_titulo or "").strip() or "Novas estações"
    return {
        "trilha_id": ci.slug(titulo)[:60] or "novas-estacoes",
        "titulo": titulo,
        "resumo": (pedido.trilha_resumo or "").strip() or None,
    }


def _previa_do_bloco(bloco: dict) -> dict:
    """Um bloco como o painel do admin o mostra.

    Aqui o gabarito APARECE, ao contrário de tudo que vai para o aluno: quem
    publica precisa conferir se a resposta certa é a certa, e é justamente essa
    conferência que a tela existe para permitir. A rota é `require_admin`.
    """
    resumo = {
        "tipo": bloco["tipo"],
        "bloco_id": bloco["bloco_id"],
        "titulo": bloco.get("titulo"),
    }
    if bloco["tipo"] in ("exercicio", "desafio"):
        resumo.update({
            "nivel": bloco.get("nivel"),
            "formato": bloco.get("formato"),
            "enunciado": bloco.get("enunciado"),
            "alternativas": bloco.get("alternativas"),
            "gabarito": bloco.get("gabarito"),
            "feedback": bloco.get("feedback"),
            "solucao": bloco.get("solucao"),
        })
    elif bloco["tipo"] == "texto":
        resumo["previa"] = (bloco.get("markdown") or "")[:400]
    elif bloco["tipo"] == "exemplo":
        resumo["previa"] = bloco.get("enunciado")
        resumo["passos"] = len(bloco.get("passos") or [])
    elif bloco["tipo"] == "tabela":
        resumo["previa"] = " · ".join(bloco.get("colunas") or [])
    return resumo


def _previa_da_estacao(dados: dict) -> dict:
    blocos = dados.get("blocos") or []
    return {
        "estacao_id": dados["estacao_id"],
        "numero": dados.get("numero"),
        "titulo": dados["titulo"],
        "objetivo": dados["objetivo"],
        "duracao_minutos": dados.get("duracao_minutos"),
        "conclusao": dados.get("conclusao"),
        "contagem": {
            tipo: sum(1 for b in blocos if b["tipo"] == tipo)
            for tipo in cc.TIPOS_DE_BLOCO
        },
        # Os problemas do contrato, estação por estação: é a lista que diz o
        # que consertar no TEXTO, e por isso ela vem antes de qualquer botão.
        "problemas": cc.validar_estacao(dados),
        "blocos": [_previa_do_bloco(b) for b in blocos],
    }


@router_admin.post("/conteudo/compilar")
async def compilar_conteudo(
    pedido: TextoDeCurso = Body(...), admin: User = Depends(require_admin),
):
    """Mostra o que o texto VIRARIA. Não grava nada, em nenhuma hipótese."""
    _curso_do_catalogo(pedido.curso_id)
    compilada = cpub.compilar_texto(pedido.curso_id, pedido.texto)
    estacoes = [_previa_da_estacao(d) for d in compilada.estacoes.values()]
    return {
        "curso_id": pedido.curso_id,
        "trilha": _trilha_escolhida(pedido.curso_id, pedido),
        "estacoes": estacoes,
        "problemas": compilada.problemas,
        "avisos": compilada.avisos,
        # Publicável quando o texto compilou inteiro e nenhuma estação tem
        # problema de contrato. O painel usa isto para ligar o botão; o
        # servidor não confia nele e valida de novo na publicação.
        "pode_publicar": bool(estacoes) and not compilada.problemas
        and not any(e["problemas"] for e in estacoes),
    }


@router_admin.post("/conteudo/publicar")
async def publicar_conteudo(
    pedido: TextoDeCurso = Body(...), admin: User = Depends(require_admin),
):
    """Compila, valida e põe no ar. Tudo ou nada."""
    _curso_do_catalogo(pedido.curso_id)
    compilada = cpub.compilar_texto(pedido.curso_id, pedido.texto)
    if compilada.problemas or not compilada.estacoes:
        raise HTTPException(
            status_code=422,
            detail={"mensagem": "O texto não compilou inteiro.", "problemas": compilada.problemas},
        )

    trilha = _trilha_escolhida(pedido.curso_id, pedido)
    problemas, resumo = await cpub.publicar(
        pedido.curso_id,
        list(compilada.estacoes.values()),
        trilha_id=trilha["trilha_id"],
        trilha_titulo=trilha["titulo"],
        trilha_resumo=trilha["resumo"],
        por=admin.email,
    )
    if problemas:
        raise HTTPException(
            status_code=422,
            detail={"mensagem": "O conteúdo não passou na validação.", "problemas": problemas},
        )

    logger.info(
        "Conteúdo publicado por texto: curso=%s estacoes=%d por=%s",
        pedido.curso_id, len(compilada.estacoes), admin.email,
    )
    return {
        "publicado": resumo,
        "avisos": compilada.avisos,
        "inventario": cc.inventario(),
    }


@router_admin.get("/conteudo/publicados")
async def listar_publicados(admin: User = Depends(require_admin)):
    """O que está no ar por publicação de painel — e não por commit."""
    return {"cursos": await cpub.listar()}


@router_admin.delete("/conteudo/publicados/{curso_id}")
async def remover_publicado(
    curso_id: str, estacao_id: str | None = None, admin: User = Depends(require_admin),
):
    """Desfaz uma publicação: a estação (ou o curso) volta ao que o arquivo diz.

    O conteúdo de arquivo nunca foi apagado — estava coberto. É por isso que
    isto é seguro o bastante para viver ao lado do botão de publicar.
    """
    resultado = await cpub.despublicar(curso_id, estacao_id=estacao_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Este curso não tem conteúdo publicado pelo painel.")
    logger.info("Publicação removida: curso=%s estacao=%s por=%s", curso_id, estacao_id, admin.email)
    return {"resultado": resultado, "inventario": cc.inventario()}
