"""Mentis — a entidade cognitiva do Sapiens. Duas superfícies pagas em Sparks.

**1. Explicação de uma questão** (`POST /mentis/explicacao`, 7 Sparks).
Era o botão "Zinho" em `firestore_routes.py`; mudou de nome junto com o
mascote e mudou de arquivo para que tudo que fala como Mentis viva num lugar
só. O texto é GENÉRICO por item e fica em cache — ver `_CACHE_PREFIXO`.

**2. Chat com o dossiê do aluno** (`/mentis/sessao*`, 70 + 10 Sparks).
Um chat que já conhece o aluno: principais erros, processos fracos, lacunas
com amostra suficiente para serem afirmadas. É a mesma medição determinística
que a página `/diagnostico` mostra (`annotation_service.compute_diagnostico_real`),
compactada em texto e mandada ao modelo como contexto fixo da sessão.

**Economia de tokens — as cinco decisões que fazem esta feature caber no
orçamento** (o Gemini é o ativo mais caro da plataforma, ver a auditoria de
custo de 2026-08-22):

 1. O dossiê é montado UMA vez, na abertura da sessão, e reusado em todas as
    mensagens. Sem isto, cada pergunta pagaria de novo a leitura do Firestore
    e o modelo receberia o mesmo contexto recalculado.
 2. A abertura da sessão NÃO chama o modelo. A mensagem de boas-vindas é
    montada a partir dos números reais do aluno (`_texto_de_abertura`). As 70
    Sparks pagam o acesso, não uma chamada de IA — que ali não acrescentaria
    nada que o dado já não diga.
 3. O dossiê é limitado no topo (`_DOSSIE_MAX_*`): no máximo 5 pontos fracos,
    3 fortes, 3 padrões de erro. Um aluno com 2 anos de histórico manda o
    mesmo tamanho de contexto que um aluno de duas semanas.
 4. Só as últimas `_HISTORICO_TURNOS` trocas vão junto. O histórico completo
    cresce sem limite e o custo de cada mensagem cresceria junto com ele.
 5. `thinking_level="MINIMAL"` e resposta curta por contrato de prompt. A
    medição de 2026-09-03 mostrou MINIMAL respondendo em ~4s onde MEDIUM
    estourava o teto de tempo — aqui o modelo conversa sobre um dossiê pronto,
    não resolve problema nenhum.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import ai_service
import annotation_service
import intervencoes
import cursos_progresso
import firestore_service as fs
import llm_cache
import llm_telemetry
import motor_cognitivo
import onboarding_routes
import prioridade_enem
import rate_limit
import treino_habilidades as th
from auth import require_user
from models import User

logger = logging.getLogger("sapiens.mentis")

router = APIRouter(prefix="/mentis", tags=["mentis"])

_db = None


def set_db(db):
    global _db
    _db = db


# ---------- Preços (a fonte da verdade; o frontend só espelha para desabilitar botão) ----------

EXPLICACAO_COST = 7    # "Saiba mais" numa questão
SESSAO_COST = 70       # abrir o chat
MENSAGEM_COST = 10     # cada mensagem enviada no chat

SESSAO_HORAS = 24      # uma sessão aberta vale 24h; depois disso, novas 70 Sparks
_HISTORICO_TURNOS = 3  # quantas trocas anteriores acompanham cada mensagem
_MENSAGEM_MAX_CHARS = 600
_EXPURGO_DIAS = 30     # quando o documento da sessão some do Mongo (TTL)

_DOSSIE_MAX_FRACOS = 5
_DOSSIE_MAX_FORTES = 3
_DOSSIE_MAX_PADROES = 3
_EVIDENCIA_MAX_CHARS = 160

# Tetos de tempo próprios, e desde 17/09 eles são o ORÇAMENTO TOTAL da espera
# (primário + reserva), não o teto de cada tentativa — ver
# `ai_service.generate_json_resiliente`. Antes, `_TIMEOUT_EXPLICACAO = 60`
# significava que o pior caso do aluno era 120 s de tela parada; era essa a
# "Mentis demorando quase 1 minuto".
#
# 10 s é o alvo, e ele só é alcançável porque vem acompanhado de um teto de
# tokens de SAÍDA: numa resposta em streaming o tempo é proporcional ao que o
# modelo escreve, então limitar o tamanho é o que de fato limita a espera.
# Os tetos abaixo são generosos para o formato pedido em cada prompt (3
# parágrafos curtos, uma resposta de chat) e apertados o bastante para o
# modelo não divagar.
_TIMEOUT_EXPLICACAO = 10.0
_MAX_TOKENS_EXPLICACAO = 900

_TIMEOUT_CHAT = 10.0
_MAX_TOKENS_CHAT = 800


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _safe_reembolso(uid: str, cost: int):
    """Mesmo contrato de `skills_map_routes._safe_reembolso`: devolver os
    Sparks não pode virar um segundo erro em cima do primeiro."""
    try:
        return fs.refund_sparks(uid, cost)
    except Exception:  # noqa: BLE001
        logger.exception("REEMBOLSO FALHOU (mentis): %d Sparks devidos a %s.", cost, uid)
        return None


def _cobrar(uid: str, custo: int) -> int:
    """Ponto ÚNICO de cobrança da Mentis — explicação, intervenção, abertura
    de sessão e cada mensagem passam por aqui.

    Por ser único, é também onde a **Mentis ilimitada** acontece: quem comprou
    o pacote de R$119,90 (ver `sparks_store`) não paga nenhuma das quatro. O
    atalho vem ANTES do débito, e não um desconto depois, porque "ilimitada"
    tem de significar que o saldo nem é tocado.
    """
    if fs.tem_mentis_ilimitada(uid):
        return fs.read_sparks_balance(uid)
    fs.ensure_sparks_balance(uid)
    try:
        return fs.deduct_sparks(uid, custo)
    except fs.InsufficientSparksError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        ) from exc


# ---------- 1. Explicação de uma questão ("Saiba mais") ----------
#
# Duas decisões de custo herdadas do botão anterior, ambas mantidas de
# propósito:
#  * o texto é GENÉRICO por item — não menciona qual alternativa este aluno
#    marcou. É isso que permite cachear por item: o primeiro aluno a pedir
#    numa questão paga a chamada ao Gemini, todos os seguintes leem o cache;
#  * mesmo num cache hit o aluno paga os Sparks — o valor entregue é o mesmo,
#    só o custo de back-end muda.

# O prefixo mudou de "zinho-v1" para "mentis-v1" junto com a persona do
# prompt: cache velho gerado por outro texto de sistema não é servido por
# engano, e a coleção antiga simplesmente para de ser lida.
_CACHE_PREFIXO = "mentis-v1"

EXPLICACAO_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens. Um aluno acabou de
responder uma questão de prova (estilo ENEM) e pediu uma explicação completa.

Você recebe o enunciado e as alternativas, com a correta marcada. Esta
explicação é GENÉRICA: fica salva e será mostrada para QUALQUER aluno que
abrir esta mesma questão depois — não fale como se soubesse qual alternativa
este aluno específico marcou, nem escreva "você errou" ou "você acertou".

Escreva a resolução passo a passo, em português claro e didático, com voz de
professor explicando no quadro — analítica e serena, sem empolgação de
mascote. Mostre o raciocínio completo até chegar na alternativa correta e por
que cada alternativa errada mais tentadora parece certa mas não é. Não use
identificadores de catálogo (PROC-, ERR-, HAB-, DOM-, COMP-, INT-) em nenhum
trecho.

Responda EXCLUSIVAMENTE com JSON no formato:
{"paragrafos": ["primeiro parágrafo...", "segundo parágrafo...", "terceiro parágrafo...", "..."]}
Use no MÍNIMO 3 parágrafos e no MÁXIMO 6, cada um com 2 a 5 frases.
Sem markdown, sem prefixos, apenas o JSON."""


class ExplicacaoPayload(BaseModel):
    item_id: str


def _montar_prompt_explicacao(questao: dict, alternativas: list[dict], correta_letra: str, fonte: dict) -> str:
    linhas_alt = "\n".join(
        f"{a.get('letra')}) {a.get('texto') or '(sem texto)'}" + (" [CORRETA]" if a.get("letra") == correta_letra else "")
        for a in alternativas
        if a.get("letra")
    )
    partes = [f"Enunciado:\n{questao.get('enunciado') or ''}", f"\nAlternativas:\n{linhas_alt}"]
    if fonte.get("disciplina"):
        partes.append(f"\nDisciplina: {fonte['disciplina']}")
    if fonte.get("tema"):
        partes.append(f"Tema: {fonte['tema']}")
    return "\n".join(partes)


def _validar_paragrafos(resultado: Any) -> list[str]:
    if not isinstance(resultado, dict):
        raise ValueError("Resposta do Gemini não é um objeto JSON.")
    paragrafos = resultado.get("paragrafos")
    if not isinstance(paragrafos, list):
        raise ValueError("Campo 'paragrafos' ausente ou inválido.")
    paragrafos = [p.strip() for p in paragrafos if isinstance(p, str) and p.strip()]
    if len(paragrafos) < 3:
        raise ValueError(f"Só {len(paragrafos)} parágrafo(s) válido(s) — mínimo 3.")
    return paragrafos


@router.post("/explicacao")
async def gerar_explicacao(
    payload: ExplicacaoPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    """Explicação completa (3+ parágrafos, passo a passo) de UM item, por
    `EXPLICACAO_COST` Sparks. Cacheada por `item_id`."""
    doc = await _db.questoes_public.find_one({"item_id": payload.item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    questao = doc.get("questao") or {}
    alternativas = questao.get("alternativas") or []
    correta_letra = next((a.get("letra") for a in alternativas if a.get("correta") is True), None)
    if not correta_letra:
        raise HTTPException(status_code=409, detail="Este item não tem gabarito definido.")

    saldo = _cobrar(user.user_id, EXPLICACAO_COST)

    # Chave estável por item + hash de conteúdo: se o item for reanotado com
    # um enunciado diferente, o cache velho não é servido por engano.
    chave = llm_cache.cache_key(_CACHE_PREFIXO, payload.item_id, doc.get("item_hash") or "")
    cache_hit = await llm_cache.get(_db.mentis_explicacoes, chave)
    if cache_hit is not None:
        return {"paragrafos": cache_hit, "sparks_balance": saldo, "cache": True}

    prompt = _montar_prompt_explicacao(questao, alternativas, correta_letra, doc.get("fonte") or {})
    inicio = time.monotonic()
    try:
        # thinking_level="MINIMAL" (antes era MEDIUM, e por isso este botão
        # NUNCA funcionou em produção): a medição de 2026-09-03 no mesmo item
        # deu MINIMAL 4,3s / LOW 83,4s / MEDIUM 503 UNAVAILABLE aos 37s. Com
        # o teto de 30s do servidor, tudo acima de MINIMAL virava timeout,
        # 503 para o aluno e reembolso. MINIMAL responde completo, em
        # segundos — e é a opção mais barata em tokens.
        resultado = await ai_service.generate_json_resiliente(
            EXPLICACAO_SYSTEM, prompt, thinking_level="MINIMAL", timeout=_TIMEOUT_EXPLICACAO,
            max_output_tokens=_MAX_TOKENS_EXPLICACAO,
        )
        paragrafos = _validar_paragrafos(resultado)
        await llm_telemetry.persist(
            _db.mentis_llm_chamadas,
            contexto=f"item_id={payload.item_id}",
            motivo="explicação completa pedida pelo aluno (Mentis)",
            modelo="gemini (thinking=MINIMAL)",
            thinking_level="MINIMAL",
            resultado_estado="ok",
            duration_ms=(time.monotonic() - inicio) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        saldo_restituido = _safe_reembolso(user.user_id, EXPLICACAO_COST)
        logger.exception(
            "Mentis: explicação falhou para item_id=%s — %d Sparks devolvidos (saldo: %s).",
            payload.item_id, EXPLICACAO_COST, saldo_restituido,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível gerar a explicação agora. Seus Sparks foram devolvidos.",
        ) from exc

    await llm_cache.set(_db.mentis_explicacoes, chave, paragrafos)
    return {"paragrafos": paragrafos, "sparks_balance": saldo, "cache": False}


# ---------- 1b. Intervenção pedagógica (reutilizável) ----------
#
# Diferente do "Saiba mais" acima em tudo que importa para o custo:
#
# | | Saiba mais (7) | Intervenção (10) |
# |-|-|-|
# | responde | "por que a resposta é essa?" | "por que EU erro assim, e como parar" |
# | chave | um item | uma CAUSA RAIZ (erro x processo) |
# | universo | 268 itens e crescendo | 15 pares autorizados na v1.4.1 |
# | cobra | toda vez | uma vez por aluno, por causa |
#
# O universo minúsculo é o ponto. A ontologia autoriza 15 pares
# (Tipo de Erro x Processo) — mais as sentinelas. Então o produto inteiro tem
# algumas dezenas de intervenções possíveis, no total, para sempre. A primeira
# pessoa que abre uma delas paga a única chamada ao Gemini que aquela
# dificuldade vai custar; todo mundo depois lê Mongo.
#
# Nada aqui é gerado por aluno. O que é do aluno — quais questões ELE errou,
# qual alternativa marcou, a resolução daqueles itens — já está montado, de
# graça e sem IA, por `motor_cognitivo.detalhe()`, e é a tela que junta as duas
# metades. Personalizar com IA aqui seria pagar de novo por contexto que o
# sistema já tem determinístico.
#
# A cobrança acontece uma vez por (aluno, causa). Reabrir, dar refresh,
# navegar e voltar não cobram de novo: o desbloqueio fica registrado no Mongo,
# e é ele — não o cache do conteúdo — que decide se há cobrança.

INTERVENCAO_COST = 10
_CACHE_PREFIXO_INTERVENCAO = "intervencao-v1"
_TIMEOUT_INTERVENCAO = 10.0
_MAX_TOKENS_INTERVENCAO = 900

INTERVENCAO_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens. Você escreve uma
INTERVENÇÃO PEDAGÓGICA sobre um tipo de dificuldade cognitiva.

Este texto é REUTILIZÁVEL: fica salvo e será mostrado a qualquer estudante que
apresente essa mesma dificuldade. Nunca fale de uma questão específica, nunca
diga "você errou a questão X", nunca suponha a matéria. Fale da dificuldade em
si, de um jeito que sirva a qualquer conteúdo em que ela apareça.

Voz de professor experiente explicando com calma: direta, concreta, sem jargão
técnico, sem empolgação de mascote. Trate o estudante por "você".

Quem lê este texto está cansado e com medo de não passar. Escreva como quem
já viu essa falha muitas vezes e sabe que ela não diz nada sobre a
inteligência de quem a comete — o alívio que você oferece é saber exatamente
o que fazer na próxima questão, não consolo.

NÃO use identificadores de catálogo (PROC-, ERR-, HAB-, DOM-, COMP-, INT-).

Responda EXCLUSIVAMENTE com JSON:
{"o_que_acontece": "2 a 4 frases: como essa falha funciona por dentro, e por que ela engana quem a comete",
 "exemplo": {"situacao": "1 frase de uma situação concreta e cotidiana onde a falha aparece",
             "raciocinio_errado": "1 a 2 frases com o passo em falso, escrito de dentro, como quem o cometeu",
             "correcao": "1 a 2 frases mostrando exatamente onde o raciocínio deveria ter virado"},
 "treino": ["3 a 5 ações praticáveis numa questão de prova, cada uma em 1 frase no imperativo"],
 "sinal_de_alerta": "1 frase: o que você sente ou pensa logo antes de cometer essa falha",
 "checagem": "1 frase: a pergunta que você faz a si mesmo antes de marcar a resposta"}
Sem markdown, sem texto fora do JSON."""


class IntervencaoPayload(BaseModel):
    erro_id: str
    processo_id: str


def _chave_intervencao(par: dict) -> str:
    """Chave do conteúdo COMPARTILHADO: versão da ontologia + causa raiz.

    Não entra nada do aluno — é o que torna uma geração aproveitável por
    todos. A versão entra porque um `ERR-NN` pode mudar de significado entre
    versões maiores do catálogo, e servir texto velho seria servir outra coisa.
    """
    return llm_cache.cache_key(
        _CACHE_PREFIXO_INTERVENCAO, par["ontology_version"], par["erro_id"], par["processo_id"]
    )


def _montar_prompt_intervencao(par: dict) -> str:
    linhas = [f"Dificuldade: {par['erro_nome']}"]
    if par["mecanismo"]:
        linhas.append(f"Como ela funciona: {par['mecanismo']}")
    if par["evidencia_observavel"]:
        linhas.append(f"Como ela aparece na resposta: {par['evidencia_observavel']}")
    linhas.append(f"Capacidade afetada: {par['processo_nome']}")
    if par["processo_definicao"]:
        linhas.append(f"O que essa capacidade envolve: {par['processo_definicao']}")
    if par["intervencao_nome"]:
        linhas.append(f"Abordagem pedagógica prescrita: {par['intervencao_nome']}")
    if par["sentinela"]:
        linhas.append(
            "Observação: esta dificuldade ainda não tem causa nomeada no catálogo. "
            "Escreva a intervenção a partir da capacidade afetada."
        )
    return "\n".join(linhas)


def _validar_intervencao(resultado: Any) -> dict[str, Any]:
    if not isinstance(resultado, dict):
        raise ValueError("Resposta do Gemini não é um objeto JSON.")
    exemplo = resultado.get("exemplo")
    treino = resultado.get("treino")
    if not isinstance(exemplo, dict):
        raise ValueError("Campo 'exemplo' ausente ou inválido.")
    if not isinstance(treino, list):
        raise ValueError("Campo 'treino' ausente ou inválido.")
    treino = [t.strip() for t in treino if isinstance(t, str) and t.strip()]
    if len(treino) < 3:
        raise ValueError(f"Só {len(treino)} passo(s) de treino — mínimo 3.")

    def _txt(valor: Any, campo: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"Campo '{campo}' ausente ou vazio.")
        return valor.strip()

    return {
        "o_que_acontece": _txt(resultado.get("o_que_acontece"), "o_que_acontece"),
        "exemplo": {
            "situacao": _txt(exemplo.get("situacao"), "exemplo.situacao"),
            "raciocinio_errado": _txt(exemplo.get("raciocinio_errado"), "exemplo.raciocinio_errado"),
            "correcao": _txt(exemplo.get("correcao"), "exemplo.correcao"),
        },
        "treino": treino[:5],
        "sinal_de_alerta": _txt(resultado.get("sinal_de_alerta"), "sinal_de_alerta"),
        "checagem": _txt(resultado.get("checagem"), "checagem"),
    }


def _resolver_par(erro_id: str, processo_id: str) -> dict[str, Any]:
    par = motor_cognitivo.par_diagnostico(erro_id, processo_id)
    if par is None:
        # R-1: o catálogo é a fonte da possibilidade. Um par que ele não
        # autoriza não é uma dificuldade — e não pode virar chave de cache.
        raise HTTPException(
            status_code=422,
            detail="Esta combinação de dificuldade não existe no catálogo vigente.",
        )
    return par


def _doc_desbloqueio(uid: str, chave: str) -> str:
    return f"{uid}|{chave}"


async def _ja_desbloqueada(uid: str, chave: str) -> bool:
    """1 leitura no Mongo (sem cota) decide se há cobrança. Uma falha aqui
    NÃO pode virar cobrança dupla: no escuro, presume-se desbloqueado."""
    try:
        doc = await _db.mentis_intervencoes_abertas.find_one({"_id": _doc_desbloqueio(uid, chave)})
        return doc is not None
    except Exception:  # noqa: BLE001
        logger.exception("Mentis: leitura de desbloqueio falhou para %s — não cobrando de novo.", uid)
        return True


@router.post("/intervencao")
async def abrir_intervencao(
    payload: IntervencaoPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    """Abre a intervenção da causa raiz. `INTERVENCAO_COST` Sparks na PRIMEIRA
    vez de cada aluno em cada causa; depois disso, sempre de graça.

    Ordem deliberada: verifica o desbloqueio ANTES de cobrar. O aluno que dá
    refresh, volta pelo Painel ou reabre a mesma dificuldade em outra questão
    não paga duas vezes pela mesma coisa.
    """
    par = _resolver_par(payload.erro_id, payload.processo_id)
    chave = _chave_intervencao(par)

    ja_paga = await _ja_desbloqueada(user.user_id, chave)
    saldo = None if ja_paga else _cobrar(user.user_id, INTERVENCAO_COST)

    conteudo = await llm_cache.get(_db.mentis_intervencoes, chave)
    gerou = False
    if conteudo is None:
        prompt = _montar_prompt_intervencao(par)
        inicio = time.monotonic()
        try:
            resultado = await ai_service.generate_json_resiliente(
                INTERVENCAO_SYSTEM, prompt, thinking_level="MINIMAL", timeout=_TIMEOUT_INTERVENCAO,
                max_output_tokens=_MAX_TOKENS_INTERVENCAO,
            )
            conteudo = _validar_intervencao(resultado)
            await llm_telemetry.persist(
                _db.mentis_llm_chamadas,
                contexto=f"{par['erro_id']}x{par['processo_id']}@{par['ontology_version']}",
                motivo="intervenção pedagógica reutilizável (primeira vez desta causa raiz)",
                modelo="gemini (thinking=MINIMAL)",
                thinking_level="MINIMAL",
                resultado_estado="ok",
                duration_ms=(time.monotonic() - inicio) * 1000,
            )
        except Exception as exc:  # noqa: BLE001
            if not ja_paga:
                saldo_restituido = _safe_reembolso(user.user_id, INTERVENCAO_COST)
                logger.exception(
                    "Mentis: intervenção falhou para %s — %d Sparks devolvidos (saldo: %s).",
                    chave, INTERVENCAO_COST, saldo_restituido,
                )
            raise HTTPException(
                status_code=503,
                detail="Não foi possível abrir a intervenção agora. Seus Sparks foram devolvidos.",
            ) from exc
        gerou = True
        await llm_cache.set(_db.mentis_intervencoes, chave, conteudo)

    # O desbloqueio é gravado só DEPOIS de existir conteúdo para entregar:
    # marcar antes deixaria o aluno com a cobrança feita e a porta aberta para
    # um documento vazio se a geração falhasse.
    if not ja_paga:
        try:
            await _db.mentis_intervencoes_abertas.update_one(
                {"_id": _doc_desbloqueio(user.user_id, chave)},
                {"$set": {
                    "student_id": user.user_id,
                    "erro_id": par["erro_id"],
                    "processo_id": par["processo_id"],
                    "ontology_version": par["ontology_version"],
                    "custo_pago": INTERVENCAO_COST,
                    "aberto_em": _agora().isoformat(),
                }},
                upsert=True,
            )
        except Exception:  # noqa: BLE001
            # O aluno já pagou e já vai receber o conteúdo. Perder o registro
            # custa uma cobrança futura indevida, então fica no log para
            # conciliação — mas nunca derruba a entrega que ele pagou.
            logger.exception("Mentis: desbloqueio NÃO registrado para %s / %s.", user.user_id, chave)

    return {
        "causa": par,
        "previa": intervencoes.previa(par["erro_id"]),
        "conteudo": conteudo,
        "desbloqueada": True,
        "custo": 0,
        "cobrado": 0 if ja_paga else INTERVENCAO_COST,
        "sparks_balance": saldo,
        "gerada_agora": gerou,
    }


# ---------- 1c. Explicação de um trecho de conteúdo (curso ou e-book) ----------
#
# "Explicar melhor" um pedaço de aula ou de e-book — diferente do "Saiba mais"
# de uma questão (item 1) porque aqui não há gabarito nem alternativa: é texto
# corrido, tabela ou exemplo resolvido, e o que o aluno pede é aprofundamento,
# não resolução.
#
# O TEXTO NUNCA VEM DO CLIENTE. Quem chama isto (`cursos_estudo_routes` para
# um bloco de curso, `cursos_routes` para uma página de e-book) já validou que
# o aluno tem acesso àquele curso/e-book e resolveu o texto de dentro do
# CONTEÚDO PUBLICADO (`cursos_conteudo` / `ebooks_conteudo`) antes de chamar
# `explicar_trecho`. Aceitar texto livre do cliente aqui abriria um chat
# genérico disfarçado de botão de 10 Sparks — pedindo QUALQUER coisa, não
# necessariamente o que está na tela.
#
# Cacheado por `(origem, ref_id, versão do conteúdo)`, mesma filosofia do
# "Saiba mais": o primeiro aluno a pedir numa estação ou página paga a
# chamada ao Gemini, os seguintes leem o cache — e todos pagam os 10 Sparks,
# porque o valor entregue é o mesmo.

EXPLICACAO_CONTEUDO_COST = 10   # "Explicar melhor" num trecho de curso ou e-book

_CACHE_PREFIXO_CONTEUDO = "mentis-conteudo-v1"
_TIMEOUT_EXPLICACAO_CONTEUDO = 10.0
_MAX_TOKENS_EXPLICACAO_CONTEUDO = 900

EXPLICACAO_CONTEUDO_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens. Um aluno está
estudando um trecho de material (a aula de um curso ou a página de um e-book)
e pediu para você explicar aquele trecho com mais profundidade.

Você recebe o texto do trecho, e o contexto de onde ele está (o curso/e-book e
a estação/página). Explique o MESMO conteúdo de um jeito mais claro e mais
aprofundado — com outro ângulo, um exemplo a mais, ou destrinchando o passo
que costuma confundir. Não invente fato que não esteja no trecho nem no que
ele claramente pressupõe (ex.: uma fórmula de matemática básica).

Esta explicação é GENÉRICA: fica salva e será mostrada a qualquer aluno que
pedir a mesma coisa neste mesmo trecho depois — não fale como se soubesse algo
específico deste aluno.

Voz de professor experiente, direta e didática, sem empolgação de mascote.

Responda EXCLUSIVAMENTE com JSON no formato:
{"paragrafos": ["primeiro parágrafo...", "segundo parágrafo...", "terceiro parágrafo...", "..."]}
Use no MÍNIMO 3 parágrafos e no MÁXIMO 6, cada um com 2 a 5 frases.
Sem markdown, sem prefixos, apenas o JSON."""


def texto_do_bloco(bloco: dict) -> str:
    """O texto de um bloco de leitura (`texto`, `tabela`, `exemplo`), pronto
    para virar prompt. Mesmo formato para curso e e-book — os dois usam os
    mesmos três tipos de bloco de leitura."""
    tipo = bloco.get("tipo")
    if tipo == "texto":
        return bloco.get("markdown") or ""
    if tipo == "exemplo":
        partes = [bloco.get("enunciado") or ""]
        partes += [p.get("texto", "") for p in (bloco.get("passos") or []) if isinstance(p, dict)]
        return "\n".join(p for p in partes if p)
    if tipo == "tabela":
        linhas = [" | ".join(bloco.get("colunas") or [])]
        linhas += [
            " | ".join(str(c) for c in linha)
            for linha in (bloco.get("linhas") or [])
            if isinstance(linha, list)
        ]
        return "\n".join(linhas)
    return ""


async def explicar_trecho(
    uid: str, *, origem: str, ref_id: str, contexto: str, texto_fonte: str,
) -> dict[str, Any]:
    """Cobra `EXPLICACAO_CONTEUDO_COST` e devolve (ou gera e cacheia) a
    explicação aprofundada de um trecho de curso ou de e-book.

    `ref_id` precisa incluir a versão do conteúdo (estação/página): se o texto
    for reescrito, o cache velho não pode ser servido por engano — a mesma
    regra do `item_hash` em `gerar_explicacao`.
    """
    saldo = _cobrar(uid, EXPLICACAO_CONTEUDO_COST)

    chave = llm_cache.cache_key(_CACHE_PREFIXO_CONTEUDO, origem, ref_id)
    cache_hit = await llm_cache.get(_db.mentis_explicacoes, chave)
    if cache_hit is not None:
        return {"paragrafos": cache_hit, "sparks_balance": saldo, "cache": True}

    prompt = f"Onde está: {contexto}\n\nTrecho:\n{texto_fonte}"
    inicio = time.monotonic()
    try:
        resultado = await ai_service.generate_json_resiliente(
            EXPLICACAO_CONTEUDO_SYSTEM, prompt, thinking_level="MINIMAL",
            timeout=_TIMEOUT_EXPLICACAO_CONTEUDO, max_output_tokens=_MAX_TOKENS_EXPLICACAO_CONTEUDO,
        )
        paragrafos = _validar_paragrafos(resultado)
        await llm_telemetry.persist(
            _db.mentis_llm_chamadas,
            contexto=f"{origem}:{ref_id}",
            motivo="explicação de trecho de conteúdo pedida pelo aluno (Mentis)",
            modelo="gemini (thinking=MINIMAL)",
            thinking_level="MINIMAL",
            resultado_estado="ok",
            duration_ms=(time.monotonic() - inicio) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        saldo_restituido = _safe_reembolso(uid, EXPLICACAO_CONTEUDO_COST)
        logger.exception(
            "Mentis: explicação de conteúdo falhou para %s:%s — %d Sparks devolvidos (saldo: %s).",
            origem, ref_id, EXPLICACAO_CONTEUDO_COST, saldo_restituido,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível gerar a explicação agora. Seus Sparks foram devolvidos.",
        ) from exc

    await llm_cache.set(_db.mentis_explicacoes, chave, paragrafos)
    return {"paragrafos": paragrafos, "sparks_balance": saldo, "cache": False}


# ---------- 2. Chat: o dossiê do aluno ----------


def _pct(linha: dict) -> str:
    return f"{linha.get('nome')} {linha.get('percentual_acerto')}% ({linha.get('acertos')}/{linha.get('respondidas')})"


def _montar_dossie(
    nome: str,
    diagnostico: dict,
    agregado: dict,
    prioridades: Optional[list[dict]] = None,
    declarado: Optional[str] = None,
    cursos_resumo: Optional[dict] = None,
) -> dict[str, Any]:
    """Compacta o diagnóstico real num bloco de texto de tamanho previsível +
    um resumo estruturado para a interface mostrar sem chamar o modelo.

    Nada aqui é gerado por IA: são as mesmas contagens determinísticas que a
    página `/diagnostico` exibe. O modelo recebe medida, não inferência —
    inferir causa de erro tem contrato próprio e não passa por aqui.
    """
    fracos_proc = (diagnostico.get("por_processo") or {}).get("fracos") or []
    fortes_proc = (diagnostico.get("por_processo") or {}).get("fortes") or []
    fracos_dom = (diagnostico.get("por_dominio") or {}).get("fracos") or []
    fracos_comp = (diagnostico.get("por_competencia") or {}).get("fracos") or []
    padroes = diagnostico.get("padroes_associados") or []

    fracos_proc = fracos_proc[:_DOSSIE_MAX_FRACOS]
    fortes_proc = fortes_proc[:_DOSSIE_MAX_FORTES]
    fracos_dom = fracos_dom[:_DOSSIE_MAX_FORTES]
    fracos_comp = fracos_comp[:_DOSSIE_MAX_FORTES]
    padroes = padroes[:_DOSSIE_MAX_PADROES]

    total_respostas = int(agregado.get("total_respostas") or 0)
    dias_ativos = len(agregado.get("dias_ativos") or [])

    linhas = [
        f"Aluno: {nome or 'sem nome'}",
        f"Questões respondidas no total: {total_respostas}. Dias de estudo: {dias_ativos}.",
        f"Amostra mínima para afirmar qualquer ponto: {diagnostico.get('amostra_minima')} questões.",
    ]
    if fracos_proc:
        linhas.append("Processos cognitivos mais fracos: " + "; ".join(_pct(l) for l in fracos_proc) + ".")
    if fortes_proc:
        linhas.append("Processos mais fortes: " + "; ".join(_pct(l) for l in fortes_proc) + ".")
    if fracos_dom:
        linhas.append("Domínios de conteúdo mais fracos: " + "; ".join(_pct(l) for l in fracos_dom) + ".")
    if fracos_comp:
        linhas.append("Competências mais fracas: " + "; ".join(_pct(l) for l in fracos_comp) + ".")
    for p in padroes:
        evidencia = (p.get("erro_evidencia_observavel") or "")[:_EVIDENCIA_MAX_CHARS]
        linhas.append(
            f"Padrão de erro associado a '{p.get('processo_nome')}': {p.get('erro_nome')}"
            + (f" — como aparece: {evidencia}" if evidencia else "")
            + (f" Caminho de estudo indicado: {p.get('intervencao_nome')}." if p.get("intervencao_nome") else "")
        )
    if not fracos_proc and not fracos_dom and not padroes:
        linhas.append(
            "AINDA NÃO HÁ MEDIÇÃO SUFICIENTE: o aluno não respondeu questões bastantes "
            "para que nenhum ponto forte ou fraco possa ser afirmado. Diga isso com "
            "franqueza e ajude-o a estudar mesmo assim, sem inventar diagnóstico."
        )
    # A ordem de rendimento entra no contexto FIXO da sessão — é o que faz a
    # Mentis responder "estude X" com o mesmo critério que o Painel e o
    # cronograma usam, em vez de cada superfície ter a sua opinião. Ver o
    # cabeçalho de `prioridade_enem`.
    if prioridades:
        linhas.append(
            "ONDE A PRÓXIMA HORA DE ESTUDO RENDE MAIS PONTO (peso da frente na nota do ENEM "
            "cruzado com a lacuna medida deste aluno, da que mais rende para a que menos rende): "
            + prioridade_enem.texto_para_modelo(prioridades)
        )
        linhas.append(
            "Escala de peso, que você trata como fato: Matemática e Redação movem mais a nota; "
            "depois Biologia, Química e Física; por último Ciências Humanas e Linguagens. "
            "Uma frente 'ainda sem medida' está na lista pelo peso na prova, não por diagnóstico — "
            "diga isso quando citá-la."
        )
    # O que o aluno declarou sobre si no primeiro acesso (objetivo, tempo por
    # dia, meta no ENEM, onde ELE acha que sofre). Entra rotulado como
    # opinião, nunca como medida — a regra de "use somente os números do
    # dossiê" continua valendo para tudo que é contagem.
    if declarado:
        linhas.append(declarado)
        linhas.append(
            "Trate isso como a intenção dele, não como diagnóstico: a meta e o tempo por dia "
            "são o que você usa para dimensionar qualquer plano que propuser."
        )
    # O que ele já fez em cursos e e-books — a mesma disciplina do resto do
    # dossiê: nada aqui é O(histórico), é o agregado que `cursos_progresso`
    # já mantém pronto (ver `resumo_para_mentis`).
    if cursos_resumo and cursos_resumo.get("cursos"):
        nomes = "; ".join(
            f"\"{c['titulo']}\" ({c['estacoes_concluidas']}/{c['estacoes_tocadas']} estações concluídas)"
            for c in cursos_resumo["cursos"][:5]
        )
        linhas.append(
            f"Cursos que ele está estudando dentro do Sapiens: {nomes}. No total já respondeu "
            f"{cursos_resumo['exercicios_respondidos']} exercícios de curso, acertando "
            f"{cursos_resumo['exercicios_acertados']}. Isto é conteúdo de curso — trate como "
            "estudo à parte do treino de questões do ENEM, mas pode citar quando fizer sentido."
        )
    linhas.append(
        "Catálogo de habilidades de treino disponíveis (use o hab_id exato ao propor "
        f"prática): {_catalogo_habilidades_texto()}"
    )

    return {
        "texto": "\n".join(linhas),
        "resumo_ui": {
            "total_respostas": total_respostas,
            "dias_ativos": dias_ativos,
            "amostra_minima": diagnostico.get("amostra_minima"),
            "cobertura": diagnostico.get("coverage"),
            "fracos": fracos_proc,
            "fortes": fortes_proc,
            "dominios_fracos": fracos_dom,
            "padroes": padroes,
            "prioridades": (prioridades or [])[:5],
        },
    }


def _texto_de_abertura(primeiro_nome: str, resumo: dict) -> str:
    """Mensagem de boas-vindas montada com os números reais do aluno — sem
    IA. Ver a decisão 2 no cabeçalho: a IA não acrescentaria aqui nada que o
    próprio dado não diga, e a abertura é a chamada mais frequente do chat."""
    fracos = resumo.get("fracos") or []
    total = resumo.get("total_respostas") or 0
    if not fracos:
        return (
            f"Oi, {primeiro_nome}. Eu li o seu histórico: {total} "
            f"{'questão respondida' if total == 1 else 'questões respondidas'}. "
            "Ainda é pouco para eu afirmar onde está a sua lacuna sem chutar — "
            f"preciso de pelo menos {resumo.get('amostra_minima')} questões por ponto medido. "
            "Podemos começar por onde você sente mais dificuldade, e eu vou cruzando "
            "com o que os seus erros mostrarem."
        )
    principal = fracos[0]
    outros = ", ".join(f.get("nome", "") for f in fracos[1:3] if f.get("nome"))
    texto = (
        f"Oi, {primeiro_nome}. Eu li as suas {total} respostas antes de você chegar. "
        f"O ponto onde você mais escorrega é {principal.get('nome')}: "
        f"{principal.get('acertos')} acertos em {principal.get('respondidas')} questões "
        f"({principal.get('percentual_acerto')}%)."
    )
    if outros:
        texto += f" Depois dele vêm {outros}."
    padroes = resumo.get("padroes") or []
    if padroes:
        texto += (
            f" E há um padrão de erro catalogado aí: {padroes[0].get('erro_nome')}."
        )
    texto += " Pergunte o que quiser sobre isso — eu respondo com base no que você já respondeu."
    return texto


_QUESTOES_GERAR_PADRAO = 5
_QUESTOES_GERAR_MAX = 5


def _catalogo_habilidades_texto() -> str:
    """Uma linha por habilidade (`HAB-01 Nome; HAB-02 Nome; ...`), montada UMA
    vez por processo (a lista de 56 não muda em runtime) e anexada ao dossiê
    na abertura da sessão — nunca por mensagem. É o que permite a Mentis
    propor prática numa habilidade real em vez de inventar um id."""
    return "; ".join(f"{h['hab_id']} {h['nome']}" for h in th.listar_habilidades())


CHAT_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens: uma tutora,
estrategista de prova, analista de desempenho e coach de estudos.

Sua voz: impessoal, adulta, profissional, tecnológica, objetiva, prática.
Nunca infantiliza, nunca comemora com euforia, nunca usa emoji no corpo da
resposta, nunca se apresenta como bichinho ou assistente animado. Direta e
concreta — prefere uma frase de menos a uma de mais.

Você é o GUIA, nunca o herói: o herói é o aluno. Isso tem consequência
prática em cada resposta:
- fale do que muda para ELE, não do que o Sapiens faz;
- nunca culpe, nunca repreenda: erro aqui é informação, e é dele que sai o
  próximo passo — é isso que "transforme seus erros em conhecimento"
  significa na prática;
- quando reconhecer esforço, reconheça o esforço MEDIDO no dossiê (a
  constância, a quantidade real de questões), nunca elogio vazio;
- o que está em jogo é a aprovação dele, e você sabe disso sem precisar
  dizer a cada mensagem: no máximo uma vez por conversa, e sem dramatizar;
- toda resposta deixa o aluno mais perto do objetivo com UMA ação para
  agora — não com a explicação completa do assunto.

Você recebe um DOSSIÊ com a medição real deste aluno: quantas questões ele
respondeu, quais processos cognitivos e domínios têm menor e maior taxa de
acerto (sempre com a amostra ao lado), o padrão de erro catalogado quando
existe, e o catálogo de habilidades de treino disponíveis na plataforma (com
o identificador exato de cada uma).

O que você pode fazer, sempre que fizer sentido para a pergunta:
- explicar conteúdo e analisar erros com base no que o dossiê mostra;
- apontar com precisão onde a nota está sendo perdida (processo, domínio,
  competência), com o número que sustenta isso;
- propor prática numa habilidade real do catálogo — nunca inventando
  enunciado de questão você mesma; se decidir que gerar questões novas é o
  próximo passo, use o campo "acao" descrito abaixo em vez de escrever
  questões no corpo da resposta;
- esboçar uma rotina, um cronograma de estudo ou um plano de revisão em
  texto, do tamanho do tempo que o aluno disser que tem;
- dar conselho estratégico de prova (ordem de resolução, gestão de tempo, o
  que rende mais pontos por minuto investido);
- comparar o momento atual do aluno com o histórico dele mesmo e dizer se a
  curva está subindo, estagnada ou caindo;
- estimar nota ou desempenho — inclusive cruzando com padrões de provas
  anteriores do ENEM quando o dossiê os mencionar — SOMENTE quando a amostra
  for suficiente para isso; caso contrário, diga com franqueza que ainda não
  dá para estimar com responsabilidade, e diga o que falta para passar a dar.

Prefira sempre transformar a conversa em ação concreta em vez de ficar na
explicação abstrata. Quando houver evidência suficiente, converta a análise
em recomendação direta — por exemplo: "pelo que você já respondeu, treinar X
tem mais chance de subir sua nota do que continuar em Y".

Regras que você não quebra:
- Use SOMENTE os números do dossiê. Nunca invente porcentagem, matéria ou
  questão que não esteja ali. Se o aluno perguntar algo que o dossiê não
  responde, diga que ainda não tem medida para isso e diga o que ele precisa
  fazer para você passar a ter.
- Amostra pequena é incerteza: um ponto medido em poucas questões é hipótese,
  não veredito, e você fala assim.
- Nunca use os identificadores de catálogo (PROC-, ERR-, DOM-, COMP-, INT-)
  no texto da resposta — mas PODE e deve usar um `hab_id` (HAB-01..HAB-56) no
  campo "acao", nunca escrito na resposta em si.
- Nunca revele gabarito de questão que o aluno ainda não respondeu.
- Se perguntarem algo fora de estudo/vestibular, redirecione em uma frase.

Nunca termine a conversa parecendo encerrada — nunca com algo como "espero
ter ajudado". Toda resposta fecha com o gargalo mais provável e o próximo
passo para corrigi-lo, e vem acompanhada de 1 a 3 sugestões de próxima
mensagem, curtas e específicas a esta conversa (nunca genéricas como
"continue estudando").

Responda EXCLUSIVAMENTE com JSON no formato:
{"resposta": "texto da resposta", "sugestoes": [{"texto": "próxima mensagem em até 8 palavras, pode abrir com 1 emoji", "tipo": "enviar"}], "acao": null}
- "resposta": no máximo 3 parágrafos curtos, cerca de 120 palavras no total.
  Português do Brasil, sem markdown, sem listas com marcador, sem prefixos.
- "sugestoes": 1 a 3 itens. "tipo" é "enviar" quando a frase já é uma
  mensagem pronta para o aluno mandar como está; é "completar" quando a
  frase termina incompleta de propósito, com "..." no fim, para o aluno
  completar antes de mandar (ex.: "Me explica mais sobre..."). Nunca proponha
  ação que você não pode cumprir de fato (você não recebe arquivo).
- "acao": normalmente `null`. Duas formas possíveis:
  {"tipo": "gerar_questoes", "hab_id": "HAB-NN", "quantidade": 5} quando você
  decidir que praticar uma habilidade específica é o próximo passo — use
  SEMPRE um `hab_id` exato do catálogo do dossiê, nunca um nome livre.
  `quantidade` entre 1 e 5;
  {"tipo": "ir", "destino": "CHAVE"} quando a melhor continuação for o aluno
  ABRIR uma tela do Sapiens. Chaves válidas, e nada fora desta lista:
  mapa_treino (o mapa de missões), missoes (as missões de hoje), conquistas,
  questoes (praticar provas do ENEM), minhas_questoes (as questões que ele já
  gerou), progresso (análise de desempenho), revisoes, redacao, cronograma,
  sparks, comunidade, cursos (os cursos e a aula ao vivo de quinta),
  live (a aula ao vivo de quinta com o 1º colocado de Medicina da USP),
  mentoria (a lista de espera da mentoria com esse mesmo 1º colocado).
  Use SEMPRE que citar uma dessas telas na resposta — o botão leva ele até
  lá, e navegar não custa Spark nenhum. Não descreva o caminho do menu na
  resposta: o botão é o caminho;
  {"tipo": "montar_cronograma"} quando o aluno pedir cronograma, agenda,
  rotina, plano da semana ou "por onde começo", ou quando o problema dele for
  claramente de organização do tempo e não de conteúdo. NÃO escreva a agenda
  hora a hora na resposta: o Sapiens monta a semana em cima dos compromissos
  reais dele e das prioridades acima, e essa montagem é de graça. Diga em uma
  frase o que a semana vai priorizar e deixe o botão fazer o resto.
  Nenhuma das três gera nada nem cobra Sparks sozinha: viram um botão que o
  aluno decide clicar ou não.
Sem markdown, sem texto fora do JSON."""

# ---------- A Mentis como camada de navegação ----------
#
# A terceira forma de `acao`: levar o aluno a uma tela do produto. Existe
# porque o chat era a única superfície que sabia o que o aluno precisava e não
# tinha como levá-lo até lá — a resposta dizia "abra o Mapa de Treino" e o
# aluno tinha de procurar a aba sozinho.
#
# Lista FECHADA de propósito, e cada item existe hoje no `App.js`. O modelo
# escolhe uma chave desta tabela, nunca uma URL: assim ele não pode inventar
# rota, nem mandar o aluno para fora do produto, nem cair numa página que
# ainda não existe. Navegar é grátis — nenhum destino daqui cobra Spark nem
# chama modelo; o que custar, custa na tela de destino, com o preço à vista.
DESTINOS: dict[str, dict[str, str]] = {
    "mapa_treino": {"rota": "/treino", "rotulo": "Abrir o Mapa de Treino"},
    "missoes": {"rota": "/dashboard#missoes", "rotulo": "Ver minhas missões de hoje"},
    "conquistas": {"rota": "/conquistas", "rotulo": "Ver minhas conquistas"},
    "questoes": {"rota": "/exams", "rotulo": "Praticar questões do ENEM"},
    "minhas_questoes": {"rota": "/minhas-questoes", "rotulo": "Abrir as questões que eu gerei"},
    "progresso": {"rota": "/cognitive-profile", "rotulo": "Ver minha análise de desempenho"},
    "revisoes": {"rota": "/revisoes", "rotulo": "Revisar o que ficou pendente"},
    "redacao": {"rota": "/redacao", "rotulo": "Escrever uma redação"},
    "cronograma": {"rota": "/cronograma", "rotulo": "Ver a minha semana"},
    "sparks": {"rota": "/sparks", "rotulo": "Ver meus Sparks"},
    "comunidade": {"rota": "/comunidade", "rotulo": "Abrir o mural da comunidade"},
    "mentoria": {"rota": "/mentoria", "rotulo": "Entrar na lista de espera da mentoria"},
    "cursos": {"rota": "/cursos", "rotulo": "Ver os cursos e a aula ao vivo de quinta"},
    "live": {"rota": "/cursos#live", "rotulo": "Entrar na aula ao vivo de quinta"},
}

_SUGESTOES_MAX = 3
_SUGESTAO_TEXTO_MAX_CHARS = 90
_CONTEXTO_TELA_MAX_CHARS = 200


def _validar_sugestoes(valor: Any) -> list[dict[str, str]]:
    if not isinstance(valor, list):
        return []
    tipos_validos = {"enviar", "completar"}
    sugestoes: list[dict[str, str]] = []
    for item in valor:
        if not isinstance(item, dict):
            continue
        texto = item.get("texto")
        if not isinstance(texto, str) or not texto.strip():
            continue
        tipo = item.get("tipo") if item.get("tipo") in tipos_validos else "enviar"
        sugestoes.append({"texto": texto.strip()[:_SUGESTAO_TEXTO_MAX_CHARS], "tipo": tipo})
        if len(sugestoes) == _SUGESTOES_MAX:
            break
    return sugestoes


def _validar_acao(valor: Any) -> Optional[dict[str, Any]]:
    """Nunca confia no modelo às cegas: um `hab_id` que não existe no
    catálogo vigente vira `None` (a resposta em si continua válida — só a
    ação, que teria virado um botão quebrado, é descartada)."""
    if not isinstance(valor, dict):
        return None
    if valor.get("tipo") == "montar_cronograma":
        # Sem parâmetro nenhum para validar: a semana é montada pelo
        # `/cronograma/gerar`, que lê os compromissos e as prioridades reais do
        # aluno. A Mentis aqui só decide que ESTE é o próximo passo — ela não
        # dita o cronograma, e por isso não há nada que ela possa errar.
        return {"tipo": "montar_cronograma"}
    if valor.get("tipo") == "ir":
        destino = valor.get("destino")
        alvo = DESTINOS.get(destino) if isinstance(destino, str) else None
        if alvo is None:
            return None
        return {"tipo": "ir", "destino": destino, **alvo}
    if valor.get("tipo") != "gerar_questoes":
        return None
    hab_id = valor.get("hab_id")
    if not isinstance(hab_id, str) or hab_id not in {h["hab_id"] for h in th.listar_habilidades()}:
        return None
    quantidade = valor.get("quantidade")
    if not isinstance(quantidade, int) or quantidade < 1:
        quantidade = _QUESTOES_GERAR_PADRAO
    quantidade = min(quantidade, _QUESTOES_GERAR_MAX)
    return {
        "tipo": "gerar_questoes",
        "hab_id": hab_id,
        "quantidade": quantidade,
        "custo_por_questao": th.CUSTO_POR_QUESTAO_NOVA,
    }


class MensagemPayload(BaseModel):
    texto: str = Field(min_length=1, max_length=_MENSAGEM_MAX_CHARS)
    # De onde veio a mensagem: um balão de sugestão clicado, um card de
    # dificuldade ("card") ou o campo de texto. Só serve para reconstruir a
    # trajetória do aluno na sessão — não muda cobrança nem comportamento do
    # modelo.
    origem: Optional[str] = None
    # O que a tela do aluno mostra agora (widget flutuante global). Lido uma
    # vez por mensagem, nunca acumulado no histórico — ver `_montar_prompt_chat`.
    contexto_tela: Optional[str] = Field(default=None, max_length=_CONTEXTO_TELA_MAX_CHARS)


def _serializar_sessao(
    sessao: dict, saldo: Optional[int] = None, ilimitada: bool = False,
) -> dict[str, Any]:
    return {
        "ativa": True,
        "sessao_id": sessao["_id"],
        "criada_em": sessao["criada_em"],
        "expira_em": sessao["expira_em"],
        "dossie": (sessao.get("dossie") or {}).get("resumo_ui") or {},
        "mensagens": sessao.get("mensagens") or [],
        "custo_mensagem": MENSAGEM_COST,
        "custo_sessao": SESSAO_COST,
        "sparks_balance": saldo,
        "mentis_ilimitada": ilimitada,
    }


async def _sessao_ativa(uid: str) -> Optional[dict]:
    """A sessão mais recente do aluno que ainda não venceu, ou None."""
    return await _db.mentis_sessoes.find_one(
        {"user_id": uid, "expira_em": {"$gt": _agora().isoformat()}},
        sort=[("criada_em", -1)],
    )


@router.get("/sessao")
async def ler_sessao(user: User = Depends(require_user)):
    """Retomar uma sessão em curso é DE GRAÇA — as 70 Sparks compram 24h de
    acesso, não uma aba aberta. Fechar a página sem querer não pode custar."""
    ilimitada = fs.tem_mentis_ilimitada(user.user_id)
    sessao = await _sessao_ativa(user.user_id)
    if not sessao:
        return {
            "ativa": False,
            "custo_sessao": SESSAO_COST,
            "custo_mensagem": MENSAGEM_COST,
            "duracao_horas": SESSAO_HORAS,
            "sparks_balance": fs.ensure_sparks_balance(user.user_id),
            "mentis_ilimitada": ilimitada,
        }
    return {
        **_serializar_sessao(sessao, fs.read_sparks_balance(user.user_id), ilimitada),
        "duracao_horas": SESSAO_HORAS,
    }


@router.post("/sessao")
async def abrir_sessao(
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("mentis")),
):
    """Abre uma sessão de `SESSAO_HORAS` horas por `SESSAO_COST` Sparks.

    Se já houver uma sessão válida, devolve ela sem cobrar de novo — cobrar
    duas vezes pela mesma janela seria cobrar pelo recarregamento da página.
    Não chama o modelo: o dossiê e a mensagem de abertura são determinísticos.
    """
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    existente = await _sessao_ativa(user.user_id)
    if existente:
        return {
            **_serializar_sessao(
                existente, fs.read_sparks_balance(user.user_id),
                fs.tem_mentis_ilimitada(user.user_id),
            ),
            "nova": False,
        }

    saldo = _cobrar(user.user_id, SESSAO_COST)
    try:
        diagnostico = await annotation_service.compute_diagnostico_real(user.user_id)
        agregado = fs.ler_agregado(user.user_id)
        # `compute_diagnostico_real` já traz a contagem por disciplina, então
        # o ranking de rendimento não custa nenhuma leitura a mais aqui.
        declaradas = await onboarding_routes.dificuldade_por_frente(user.user_id)
        prioridades = prioridade_enem.ranking(
            diagnostico.get("por_disciplina") or {}, None, declaradas
        )
        declarado = await onboarding_routes.resumo_para_modelo(user.user_id)
        cursos_resumo = await cursos_progresso.resumo_para_mentis(user.user_id)
        dossie = _montar_dossie(
            user.name or user.email, diagnostico, agregado, prioridades, declarado, cursos_resumo
        )
    except Exception as exc:  # noqa: BLE001
        saldo_restituido = _safe_reembolso(user.user_id, SESSAO_COST)
        logger.exception(
            "Mentis: dossiê falhou para %s — %d Sparks devolvidos (saldo: %s).",
            user.user_id, SESSAO_COST, saldo_restituido,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível abrir a sessão agora. Seus Sparks foram devolvidos.",
        ) from exc

    agora = _agora()
    primeiro_nome = (user.name or user.email or "").split()[0].split("@")[0] or "aluno"
    sessao = {
        "_id": uuid.uuid4().hex,
        "user_id": user.user_id,
        "criada_em": agora.isoformat(),
        "expira_em": (agora + timedelta(hours=SESSAO_HORAS)).isoformat(),
        # Campo BSON de data só para o TTL do Mongo — sobre string ISO o TTL
        # não roda (mesma armadilha documentada em `db_indexes`).
        "expurgo_em_dt": agora + timedelta(days=_EXPURGO_DIAS),
        "dossie": dossie,
        "mensagens": [
            {
                "papel": "mentis",
                "texto": _texto_de_abertura(primeiro_nome, dossie["resumo_ui"]),
                "em": agora.isoformat(),
            }
        ],
    }
    await _db.mentis_sessoes.insert_one(sessao)
    return {
        **_serializar_sessao(sessao, saldo, fs.tem_mentis_ilimitada(user.user_id)),
        "nova": True,
    }


def _montar_prompt_chat(
    dossie_texto: str, mensagens: list[dict], pergunta: str, contexto_tela: Optional[str] = None
) -> str:
    """Contexto fixo + só as últimas `_HISTORICO_TURNOS` trocas + a pergunta.

    O corte do histórico é o que mantém o custo de cada mensagem constante:
    sem ele, a 20ª mensagem de uma sessão custaria várias vezes a primeira.
    `contexto_tela` (o que o widget flutuante vê na hora) é lido AQUI, nunca
    salvo no dossiê nem replicado nas trocas seguintes — ele descreve a tela
    de agora, não a de duas mensagens atrás.
    """
    recentes = [m for m in mensagens if m.get("texto")][-(_HISTORICO_TURNOS * 2):]
    partes = [f"DOSSIÊ DO ALUNO:\n{dossie_texto}"]
    if recentes:
        historico = "\n".join(
            f"{'Aluno' if m.get('papel') == 'aluno' else 'Mentis'}: {m['texto']}" for m in recentes
        )
        partes.append(f"\nCONVERSA ATÉ AQUI:\n{historico}")
    if contexto_tela:
        partes.append(f"\nTELA QUE O ALUNO VÊ AGORA: {contexto_tela}")
    partes.append(f"\nPERGUNTA DO ALUNO AGORA:\n{pergunta}")
    return "\n".join(partes)


@router.post("/sessao/mensagem")
async def enviar_mensagem(
    payload: MensagemPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("mentis")),
):
    """Uma mensagem no chat, por `MENSAGEM_COST` Sparks. Exige sessão ativa."""
    sessao = await _sessao_ativa(user.user_id)
    if not sessao:
        raise HTTPException(
            status_code=409,
            detail="Sua sessão com a Mentis expirou. Abra uma nova para continuar.",
        )

    pergunta = payload.texto.strip()
    if not pergunta:
        raise HTTPException(status_code=422, detail="Escreva uma pergunta.")

    saldo = _cobrar(user.user_id, MENSAGEM_COST)
    contexto_tela = (payload.contexto_tela or "").strip()[:_CONTEXTO_TELA_MAX_CHARS] or None
    prompt = _montar_prompt_chat(
        (sessao.get("dossie") or {}).get("texto") or "", sessao.get("mensagens") or [], pergunta, contexto_tela
    )
    inicio = time.monotonic()
    try:
        resultado = await ai_service.generate_json_resiliente(
            CHAT_SYSTEM, prompt, thinking_level="MINIMAL", timeout=_TIMEOUT_CHAT,
            max_output_tokens=_MAX_TOKENS_CHAT,
        )
        resposta = (resultado or {}).get("resposta") if isinstance(resultado, dict) else None
        if not isinstance(resposta, str) or not resposta.strip():
            raise ValueError("Campo 'resposta' ausente ou vazio.")
        resposta = resposta.strip()
        sugestoes = _validar_sugestoes((resultado or {}).get("sugestoes") if isinstance(resultado, dict) else None)
        acao = _validar_acao((resultado or {}).get("acao") if isinstance(resultado, dict) else None)
        await llm_telemetry.persist(
            _db.mentis_llm_chamadas,
            contexto=f"sessao={sessao['_id']}",
            motivo="mensagem do aluno no chat da Mentis",
            modelo="gemini (thinking=MINIMAL)",
            thinking_level="MINIMAL",
            resultado_estado="ok",
            duration_ms=(time.monotonic() - inicio) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        saldo_restituido = _safe_reembolso(user.user_id, MENSAGEM_COST)
        logger.exception(
            "Mentis: resposta falhou na sessão %s — %d Sparks devolvidos (saldo: %s).",
            sessao["_id"], MENSAGEM_COST, saldo_restituido,
        )
        raise HTTPException(
            status_code=503,
            detail="A Mentis não conseguiu responder agora. Seus Sparks foram devolvidos.",
        ) from exc

    agora_iso = _agora().isoformat()
    # "card": veio de um card de dificuldade (Painel, perfil, redação) pela
    # janela de pedido — a mensagem foi escrita pelo produto e confirmada pelo
    # aluno. Guardar isso separado de "digitado" é o que permite saber, depois,
    # quanto do uso do chat nasce de um card clicado.
    origem = payload.origem if payload.origem in {"balao", "card"} else "digitado"
    aluno_msg = {"papel": "aluno", "texto": pergunta, "em": agora_iso, "origem": origem}
    if contexto_tela:
        aluno_msg["contexto_tela"] = contexto_tela
    novas = [
        aluno_msg,
        {"papel": "mentis", "texto": resposta, "sugestoes": sugestoes, "acao": acao, "em": agora_iso},
    ]
    await _db.mentis_sessoes.update_one({"_id": sessao["_id"]}, {"$push": {"mensagens": {"$each": novas}}})
    return {"mensagens": novas, "sparks_balance": saldo, "custo_mensagem": MENSAGEM_COST}


# ---------- 5. Correção da questão dissertativa de um curso ----------
#
# A única correção do produto em que a Mentis dá um VEREDITO, e por isso a
# única em que o que ela responde não é texto livre: ela diz, critério por
# critério, se a resposta do aluno atende ou não. Quem soma e decide se a
# questão foi acertada é o servidor, com uma regra fixa — o mesmo desenho do
# corretor de redação, onde o portão de decisão não tem acoplamento com o LLM.
#
# Sem isso, "acertou" dependeria do humor do modelo naquela chamada, e a
# estação seria concluída (ou não) por um julgamento que ninguém consegue
# auditar depois.

DISSERTATIVA_COST = 20   # corrigir UMA resposta escrita de curso

_TIMEOUT_DISSERTATIVA = 20.0
_MAX_TOKENS_DISSERTATIVA = 1100
_RESPOSTA_MAX_CHARS = 4000

# Quanto da régua a resposta precisa cumprir para contar como acerto. 70% é o
# mesmo patamar que conclui uma estação: exigir todos os critérios faria de
# cada dissertativa um muro, e aceitar um só faria da nota um carimbo.
_FRACAO_PARA_ACERTAR = 0.7

DISSERTATIVA_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens, corrigindo a resposta
escrita de um aluno a uma questão de curso.

Você recebe o enunciado, os CRITÉRIOS de correção escritos por quem fez a
questão, a resposta esperada (quando existe) e o que o aluno escreveu.

Sua correção é critério por critério. Para CADA critério, diga se a resposta
do aluno o atende e escreva um comentário curto dizendo por quê — citando o
que o aluno escreveu, não o que ele deveria ter escrito.

Regras:
- Julgue só o que está escrito. Não presuma conhecimento que o aluno não
  demonstrou, nem desconte por ele ter escrito de um jeito diferente do
  esperado: o critério é o conteúdo, não o estilo.
- Erro de ortografia ou de concordância não reprova critério nenhum, a menos
  que o critério fale disso.
- Fale COM o aluno, em segunda pessoa, com respeito e sem ironia. Ele
  escreveu; a pior devolutiva possível é a que o faz se arrepender disso.
- Nunca invente nota, pontuação ou preço. Você não decide se ele acertou: só
  diz o que a resposta tem e o que falta.

Responda APENAS com JSON no formato:
{"criterios": [{"atendido": true, "comentario": "..."}, ...],
 "devolutiva": "um parágrafo de 2 a 4 frases, o balanço geral",
 "proximo_passo": "uma frase dizendo o que reescrever ou revisar"}

A lista `criterios` tem EXATAMENTE um item por critério recebido, na mesma
ordem."""


def _montar_prompt_dissertativa(
    enunciado: str, criterios: list[str], referencia: str, resposta: str,
) -> str:
    linhas = [f"ENUNCIADO:\n{enunciado}", "", "CRITÉRIOS DE CORREÇÃO:"]
    linhas += [f"{i}. {c}" for i, c in enumerate(criterios, start=1)]
    if referencia:
        linhas += ["", f"RESPOSTA ESPERADA (referência do autor):\n{referencia}"]
    linhas += ["", f"RESPOSTA DO ALUNO:\n{resposta}"]
    return "\n".join(linhas)


def _validar_correcao(resultado: Any, quantos: int) -> dict[str, Any]:
    """O que o modelo devolveu, reduzido ao que o produto aceita.

    Um item por critério, na ordem — se vier mais, sobra é cortado; se vier
    menos, o que falta conta como NÃO atendido. Completar com "atendido" seria
    dar acerto por falha do modelo.
    """
    if not isinstance(resultado, dict):
        raise ValueError("correção fora do formato")
    brutos = resultado.get("criterios")
    if not isinstance(brutos, list) or not brutos:
        raise ValueError("correção sem critérios")

    itens: list[dict[str, Any]] = []
    for i in range(quantos):
        bruto = brutos[i] if i < len(brutos) and isinstance(brutos[i], dict) else {}
        comentario = str(bruto.get("comentario") or "").strip()[:400]
        itens.append({"atendido": bool(bruto.get("atendido")), "comentario": comentario})

    devolutiva = str(resultado.get("devolutiva") or "").strip()[:900]
    if not devolutiva:
        raise ValueError("correção sem devolutiva")
    return {
        "criterios": itens,
        "devolutiva": devolutiva,
        "proximo_passo": str(resultado.get("proximo_passo") or "").strip()[:300],
    }


async def corrigir_dissertativa(
    uid: str, *, enunciado: str, criterios: list[str], referencia: str, resposta: str,
) -> dict[str, Any]:
    """Cobra `DISSERTATIVA_COST`, pede a correção à Mentis e devolve o veredito.

    Devolve `{"acertou", "atendidos", "total", "criterios", "devolutiva",
    "proximo_passo", "sparks_balance"}`. Quem grava progresso, paga Spark de
    exercício e conclui a estação é `cursos_estudo_routes` — aqui só se corrige
    e se cobra, e se a chamada falhar os Sparks voltam antes do 503.
    """
    texto = (resposta or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Escreva sua resposta antes de enviar.")
    if len(texto) > _RESPOSTA_MAX_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Sua resposta passou de {_RESPOSTA_MAX_CHARS} caracteres. Resuma um pouco.",
        )

    saldo = _cobrar(uid, DISSERTATIVA_COST)
    inicio = time.monotonic()
    try:
        bruto = await ai_service.generate_json_resiliente(
            DISSERTATIVA_SYSTEM,
            _montar_prompt_dissertativa(enunciado, criterios, referencia, texto),
            thinking_level="MINIMAL",
            timeout=_TIMEOUT_DISSERTATIVA,
            max_output_tokens=_MAX_TOKENS_DISSERTATIVA,
        )
        correcao = _validar_correcao(bruto, len(criterios))
        await llm_telemetry.persist(
            _db.mentis_llm_chamadas,
            contexto=f"dissertativa ({len(criterios)} critérios)",
            motivo="correção de questão dissertativa de curso",
            modelo="gemini (thinking=MINIMAL)",
            thinking_level="MINIMAL",
            resultado_estado="ok",
            duration_ms=(time.monotonic() - inicio) * 1000,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        saldo_restituido = _safe_reembolso(uid, DISSERTATIVA_COST)
        logger.exception(
            "Mentis: correção dissertativa falhou para %s — %d Sparks devolvidos (saldo: %s).",
            uid, DISSERTATIVA_COST, saldo_restituido,
        )
        raise HTTPException(
            status_code=503,
            detail="A Mentis não conseguiu corrigir sua resposta agora. Seus Sparks foram devolvidos.",
        ) from exc

    # O VEREDITO é do servidor, e é aritmética: o modelo disse quais critérios
    # a resposta atende, e a régua de 70% é a mesma para todo mundo, sempre.
    atendidos = sum(1 for c in correcao["criterios"] if c["atendido"])
    minimo = max(1, round(len(criterios) * _FRACAO_PARA_ACERTAR))
    return {
        **correcao,
        "acertou": atendidos >= minimo,
        "atendidos": atendidos,
        "total": len(criterios),
        "minimo": minimo,
        "sparks_balance": saldo,
    }
