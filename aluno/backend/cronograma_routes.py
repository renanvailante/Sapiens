"""Cronograma — a semana do aluno, de segunda a domingo.

Três portas de entrada para os compromissos e uma só saída:

  * o formulário (`POST /cronograma/compromisso`) — **grátis**;
  * o Google Agenda, por OAuth no navegador (`/cronograma/importar/google`) ou
    pelo endereço .ics do calendário (`/cronograma/importar/ics`) — **grátis**;
  * o que o aluno escreve ou DITA em português corrido
    (`/cronograma/compromissos/texto`) — custa `TEXTO_COST` Sparks, porque é
    a única das três que chama o modelo.

E a semana de estudo em volta deles (`POST /cronograma/gerar`), que é
**grátis por padrão**. Isto não é generosidade: a montagem é determinística
(`cronograma.alocar` sobre `prioridade_enem.ranking`), então cobrar por ela
seria cobrar por uma conta que o servidor faz em milissegundos. A Mentis entra
por cima, opcional, por `MENTIS_COST` Sparks — e o que ela acrescenta é TEXTO:
o horário e a prioridade de cada bloco já estavam decididos antes de ela ser
chamada, e continuam iguais depois.

Por isso a falha da Mentis aqui não devolve erro: devolve os Sparks **e a
semana montada mesmo assim**. Um aluno que pediu o cronograma nunca fica sem
cronograma porque o Gemini caiu.

Custo de leitura: `GET /cronograma` lê 1 documento do Mongo e — só quando
precisa das prioridades — o diagnóstico já memoizado em
`annotation_service._agregado_com_cache`. Nada aqui varre o Firestore por
requisição (ver `project_aluno_disciplina_leitura_firestore`).
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import ai_service
import annotation_service
import cronograma as cg
import firestore_service as fs
import llm_telemetry
import prioridade_enem
import rate_limit
import revisao_service
import treino_habilidades as th
from auth import require_user
from models import User

logger = logging.getLogger("sapiens.cronograma")

router = APIRouter(prefix="", tags=["cronograma"])

_db = None


def set_db(db):
    global _db
    _db = db


# ---------- Preços ----------
#
# Só o que chama o Gemini custa. Ver o cabeçalho: a montagem da semana é
# aritmética, e aritmética não vira produto pago neste app.

TEXTO_COST = 10    # "me diz seus compromissos" — 1 chamada curta de extração
MENTIS_COST = 30   # a Mentis reescrevendo os blocos já alocados

_TIMEOUT_TEXTO = 30.0
_TIMEOUT_PLANO = 45.0
_TEXTO_MAX_CHARS = 800
_ICS_MAX_BYTES = 1_000_000
_FUSO_PADRAO = "America/Sao_Paulo"

# Hosts de onde o servidor aceita buscar um .ics. É uma lista curta de
# propósito: `POST` com uma URL arbitrária é um pedido para o servidor fazer
# requisição em nome de quem mandou, e sem a lista qualquer aluno poderia
# apontar a rota para um endereço interno da infraestrutura. Com ela, o pior
# que se consegue é fazer o Fly buscar um calendário do Google.
_HOSTS_ICS = (
    "calendar.google.com",
    "outlook.office365.com",
    "outlook.live.com",
    "outlook.office.com",
    "p01-calendars.icloud.com",
    "icloud.com",
)


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fuso(doc: Optional[dict]) -> ZoneInfo:
    nome = (doc or {}).get("timezone") or _FUSO_PADRAO
    try:
        return ZoneInfo(nome)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(_FUSO_PADRAO)


def _hoje(doc: Optional[dict]) -> date:
    """O dia de HOJE no fuso do aluno, não no do servidor.

    O backend roda em UTC: entre 21h e 24h em São Paulo o servidor já virou o
    dia, e a semana "atual" calculada por lá seria a semana seguinte. Numa
    agenda isso não é um detalhe — é o aluno abrindo o app à noite de domingo
    e vendo a semana que ele ainda não começou."""
    return datetime.now(_fuso(doc)).date()


def _safe_reembolso(uid: str, custo: int):
    try:
        return fs.refund_sparks(uid, custo)
    except Exception:  # noqa: BLE001
        logger.exception("REEMBOLSO FALHOU (cronograma): %d Sparks devidos a %s.", custo, uid)
        return None


def _cobrar(uid: str, custo: int) -> int:
    fs.ensure_sparks_balance(uid)
    try:
        return fs.deduct_sparks(uid, custo)
    except fs.InsufficientSparksError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        ) from exc


# ---------------------------------------------------------------------------
# Persistência — 1 documento por aluno, no Mongo
# ---------------------------------------------------------------------------
#
# Mongo e não Firestore, pelo mesmo motivo de `mentis_sessoes`: a agenda é
# escrita a cada arrastar de bloco e lida a cada abertura da tela, e o
# Firestore é o banco que tem cota diária para estourar (incidente de
# 2026-09-04). Um documento por aluno, `_id = user_id`: toda leitura da tela
# é um `find_one` por chave primária.


async def _ler_doc(uid: str) -> dict[str, Any]:
    doc = await _db.cronogramas.find_one({"_id": uid})
    return doc or {
        "_id": uid,
        "student_id": uid,
        "timezone": _FUSO_PADRAO,
        "preferencias": dict(cg.PREFERENCIAS_PADRAO),
        "compromissos": [],
        "plano": None,
        "concluidos": {},
    }


async def _gravar(uid: str, campos: dict[str, Any]) -> None:
    await _db.cronogramas.update_one(
        {"_id": uid},
        {"$set": {**campos, "student_id": uid, "atualizado_em": _agora_iso()}},
        upsert=True,
    )


# ---------------------------------------------------------------------------
# Prioridades — o motor que todas as telas compartilham
# ---------------------------------------------------------------------------


async def _resumo_redacao(uid: str) -> dict[str, Any]:
    """A melhor nota de redação do aluno, em 1 consulta com projeção mínima.

    A melhor e não a última: uma redação ruim num dia ruim não apaga o que o
    aluno já provou que consegue escrever, e a prioridade da frente tem que
    refletir o teto dele, não o último tropeço.
    """
    try:
        cursor = _db.redacao_avaliacoes.find(
            {"user_id": uid}, {"_id": 0, "nota_total": 1}
        ).sort("nota_total", -1).limit(1)
        melhores = await cursor.to_list(length=1)
        total = await _db.redacao_avaliacoes.count_documents({"user_id": uid})
    except Exception:  # noqa: BLE001
        logger.exception("cronograma: leitura de redações falhou para %s", uid)
        return {"melhor_nota": None, "corrigidas": 0}
    if not melhores:
        return {"melhor_nota": None, "corrigidas": 0}
    return {"melhor_nota": melhores[0].get("nota_total"), "corrigidas": int(total or 0)}


async def _prioridades(uid: str) -> list[dict[str, Any]]:
    """O ranking de rendimento deste aluno. Nunca levanta: uma falha de
    leitura devolve o ranking do aluno sem histórico — que é uma resposta
    honesta (Matemática e Redação no topo, pelo peso na prova) e não uma tela
    de erro."""
    try:
        diagnostico = await annotation_service.compute_diagnostico_real(uid)
        stats = diagnostico.get("por_disciplina") or {}
    except Exception:  # noqa: BLE001
        logger.exception("cronograma: diagnóstico indisponível para %s", uid)
        stats = {}
    return prioridade_enem.ranking(stats, await _resumo_redacao(uid))


async def _habilidades_fracas(uid: str, limite: int = 2) -> list[dict[str, Any]]:
    """As habilidades de treino com pior taxa, com amostra suficiente.

    1 leitura do Firestore (o mesmo documento `students/{uid}` que o resto do
    app já lê), nunca O(eventos).
    """
    try:
        stats = await asyncio.to_thread(fs.ler_treino_stats, uid)
    except Exception:  # noqa: BLE001
        logger.exception("cronograma: agregado de treino indisponível para %s", uid)
        return []
    nomes = {h["hab_id"]: h["nome"] for h in th.listar_habilidades()}
    linhas = []
    for hab_id, s in (stats or {}).items():
        respondidas = int(s.get("respondidas") or 0)
        if respondidas < prioridade_enem.AMOSTRA_MINIMA or hab_id not in nomes:
            continue
        acertos = int(s.get("acertos") or 0)
        linhas.append({
            "hab_id": hab_id,
            "nome": nomes[hab_id],
            "respondidas": respondidas,
            "percentual_acerto": round(100 * acertos / respondidas, 1),
        })
    linhas.sort(key=lambda l: (l["percentual_acerto"], -l["respondidas"]))
    return linhas[:limite]


async def _fila_de_revisao(uid: str, limite: int = cg.MAX_REVISOES_SEMANA) -> list[dict[str, Any]]:
    try:
        fila = await asyncio.to_thread(revisao_service.fila, uid, limite=limite)
    except Exception:  # noqa: BLE001
        logger.exception("cronograma: fila de revisão indisponível para %s", uid)
        return []
    itens = (fila or {}).get("itens") or []
    fora = []
    for i in itens[:limite]:
        rotulo = i.get("rotulo") or "revisão"
        erro = i.get("erro_nome")
        fora.append({
            "processo_nome": i.get("processo_nome") or "ponto marcado para revisão",
            "motivo": (
                f"Entrou na fila como {rotulo}"
                + (f", com o padrão de erro '{erro}' por trás." if erro else ".")
            ),
        })
    return fora


@router.get("/prioridades")
async def minhas_prioridades(user: User = Depends(require_user)):
    """Onde a próxima hora de estudo rende mais ponto — grátis, sem IA.

    Rota compartilhada de propósito: o Painel, o cronograma e o dossiê da
    Mentis respondem "o que estudar agora" com ESTA lista, e não cada um com
    um critério próprio. Ver o cabeçalho de `prioridade_enem`.
    """
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    linhas = await _prioridades(user.user_id)
    return {
        "prioridades": linhas,
        "pesos": {d["chave"]: d["peso"] for d in prioridade_enem.DISCIPLINAS},
        "amostra_minima": prioridade_enem.AMOSTRA_MINIMA,
        "amostra_plena": prioridade_enem.AMOSTRA_PLENA,
    }


# ---------------------------------------------------------------------------
# A semana
# ---------------------------------------------------------------------------


def _semana_pedida(semana: Optional[str], doc: dict) -> str:
    if semana:
        try:
            return cg.segunda_da_semana(date.fromisoformat(semana))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Semana inválida. Use YYYY-MM-DD.") from exc
    return cg.segunda_da_semana(_hoje(doc))


def _montar_semana(doc: dict, semana_iso: str) -> dict[str, Any]:
    """A tela inteira, a partir do documento já lido. Sem I/O."""
    compromissos = cg.compromissos_da_semana(doc.get("compromissos") or [], semana_iso)
    plano = doc.get("plano") or {}
    blocos_plano = plano.get("blocos") or [] if plano.get("semana") == semana_iso else []
    concluidos = set((doc.get("concluidos") or {}).get(semana_iso) or [])
    blocos = [
        {**b, "concluido": b.get("id") in concluidos}
        for b in blocos_plano
    ]
    datas = cg.dias_da_semana(semana_iso)
    dias = [
        {
            "indice": i,
            "nome": cg.DIAS[i],
            "data": datas[i],
            "compromissos": [c for c in compromissos if c["dia"] == i],
            "blocos": sorted([b for b in blocos if b["dia"] == i], key=lambda b: b["inicio"]),
        }
        for i in range(7)
    ]
    return {
        "semana": semana_iso,
        "dias": dias,
        "preferencias": cg.normalizar_preferencias(doc.get("preferencias")),
        "timezone": doc.get("timezone") or _FUSO_PADRAO,
        "conflitos": cg.conflitos(compromissos),
        "plano": {
            "gerado_em": plano.get("gerado_em"),
            "semana": plano.get("semana"),
            "resumo": plano.get("resumo"),
            "recado": plano.get("recado"),
            "distribuicao": plano.get("distribuicao") or [],
            "com_mentis": bool(plano.get("com_mentis")),
            # O plano da semana passada continua guardado, mas a tela precisa
            # saber que ele venceu — senão o aluno de segunda-feira acha que o
            # cronograma dele sumiu, quando ele só ficou para trás.
            "desta_semana": plano.get("semana") == semana_iso,
        } if plano else None,
        "total_blocos": len(blocos),
        "total_concluidos": sum(1 for b in blocos if b["concluido"]),
        "custo_texto": TEXTO_COST,
        "custo_mentis": MENTIS_COST,
    }


@router.get("/cronograma")
async def ler_cronograma(
    semana: Optional[str] = Query(default=None, description="Qualquer dia da semana desejada (YYYY-MM-DD)"),
    user: User = Depends(require_user),
):
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    doc = await _ler_doc(user.user_id)
    return _montar_semana(doc, _semana_pedida(semana, doc))


# ---------------------------------------------------------------------------
# Compromissos — as três portas
# ---------------------------------------------------------------------------


class CompromissoPayload(BaseModel):
    titulo: str = Field(min_length=1, max_length=90)
    dia: Optional[int] = Field(default=None, ge=0, le=6)
    data: Optional[str] = None
    inicio: str = "08:00"
    fim: str = "09:00"
    tipo: str = "pessoal"
    dia_inteiro: bool = False
    observacao: Optional[str] = Field(default=None, max_length=220)


class PreferenciasPayload(BaseModel):
    inicio_dia: Optional[str] = None
    fim_dia: Optional[str] = None
    bloco_minutos: Optional[int] = Field(default=None, ge=20, le=180)
    intervalo_minutos: Optional[int] = Field(default=None, ge=0, le=60)
    blocos_por_dia: Optional[int] = Field(default=None, ge=1, le=8)
    dias_de_folga: Optional[list[int]] = None
    timezone: Optional[str] = Field(default=None, max_length=64)


@router.post("/cronograma/compromisso")
async def criar_compromisso(payload: CompromissoPayload, user: User = Depends(require_user)):
    """Grátis, sempre. É o caminho que não depende de nada: nem do Google, nem
    do Gemini, nem de saldo de Sparks."""
    doc = await _ler_doc(user.user_id)
    try:
        novo = cg.normalizar_compromisso(payload.model_dump(), origem="manual")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    atuais = list(doc.get("compromissos") or [])
    if len(atuais) >= cg.TETO_COMPROMISSOS:
        raise HTTPException(
            status_code=409,
            detail=f"Sua agenda já tem {cg.TETO_COMPROMISSOS} compromissos. Apague algum antes de criar outro.",
        )
    atuais.append(novo)
    await _gravar(user.user_id, {"compromissos": atuais})
    return {"compromisso": novo, "total": len(atuais)}


@router.patch("/cronograma/compromisso/{compromisso_id}")
async def editar_compromisso(
    compromisso_id: str, payload: CompromissoPayload, user: User = Depends(require_user)
):
    doc = await _ler_doc(user.user_id)
    atuais = list(doc.get("compromissos") or [])
    indice = next((i for i, c in enumerate(atuais) if c.get("id") == compromisso_id), None)
    if indice is None:
        raise HTTPException(status_code=404, detail="Compromisso não encontrado.")
    try:
        atualizado = cg.normalizar_compromisso(
            {**payload.model_dump(), "id": compromisso_id,
             # A origem e o vínculo externo sobrevivem à edição: um evento do
             # Google que o aluno ajustou continua sendo aquele evento, e uma
             # reimportação precisa reconhecê-lo para não criar uma segunda
             # cópia do que ele acabou de corrigir.
             "externo_id": atuais[indice].get("externo_id")},
            origem=atuais[indice].get("origem") or "manual",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    atuais[indice] = atualizado
    await _gravar(user.user_id, {"compromissos": atuais})
    return {"compromisso": atualizado}


@router.delete("/cronograma/compromisso/{compromisso_id}")
async def apagar_compromisso(compromisso_id: str, user: User = Depends(require_user)):
    doc = await _ler_doc(user.user_id)
    atuais = [c for c in (doc.get("compromissos") or []) if c.get("id") != compromisso_id]
    if len(atuais) == len(doc.get("compromissos") or []):
        raise HTTPException(status_code=404, detail="Compromisso não encontrado.")
    await _gravar(user.user_id, {"compromissos": atuais})
    return {"ok": True, "total": len(atuais)}


@router.put("/cronograma/preferencias")
async def salvar_preferencias(payload: PreferenciasPayload, user: User = Depends(require_user)):
    doc = await _ler_doc(user.user_id)
    bruto = {k: v for k, v in payload.model_dump().items() if v is not None and k != "timezone"}
    try:
        prefs = cg.normalizar_preferencias({**(doc.get("preferencias") or {}), **bruto})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    campos: dict[str, Any] = {"preferencias": prefs}
    if payload.timezone:
        try:
            ZoneInfo(payload.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Fuso horário desconhecido.") from exc
        campos["timezone"] = payload.timezone
    await _gravar(user.user_id, campos)
    return {"preferencias": prefs, "timezone": campos.get("timezone", doc.get("timezone") or _FUSO_PADRAO)}


# ---------------------------------------------------------------------------
# Porta 3: o aluno escreve ou fala os compromissos
# ---------------------------------------------------------------------------
#
# A fala não chega aqui como áudio. O reconhecimento acontece no navegador
# (Web Speech API) e o que sobe é o TEXTO já transcrito — de graça, sem
# trafegar gravação de voz do aluno para servidor nenhum e sem uma API de
# transcrição a mais na conta. Para esta rota, ditar e digitar são a mesma
# coisa; só o campo `origem` distingue os dois no registro.

TEXTO_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens. O aluno vai descrever,
em português corrido, os compromissos fixos da semana dele — aula, trabalho,
estágio, treino, terapia, prova marcada. Sua tarefa é transformar isso em
agenda estruturada.

Regras:
- Semana começa na SEGUNDA. dia: 0=segunda, 1=terça, 2=quarta, 3=quinta,
  4=sexta, 5=sábado, 6=domingo.
- Compromisso que se repete toda semana ("tenho aula de inglês às terças"):
  use "dia" e deixe "data" como null.
- Compromisso de um dia só ("prova de química dia 24"): use "data" no formato
  YYYY-MM-DD e deixe "dia" como null. Resolva expressões relativas ("amanhã",
  "sexta que vem") usando a data de hoje que vem no contexto.
- Um compromisso em vários dias vira VÁRIAS entradas, uma por dia.
- "manhã" sem hora = 08:00 às 12:00; "tarde" = 13:00 às 18:00;
  "noite" = 19:00 às 22:00. Se o aluno deu hora, use a hora dele.
- tipo: "aula" (escola, cursinho, faculdade, monitoria), "trabalho" (emprego,
  estágio, plantão), "prova" (prova, simulado, vestibular), "pessoal"
  (qualquer outra coisa: academia, terapia, igreja, família).
- NUNCA invente compromisso que o aluno não disse. Se a frase não tiver
  nenhum compromisso reconhecível, devolva a lista vazia.
- NUNCA crie blocos de estudo aqui. Estudo é montado pelo sistema em cima do
  que sobra; sua tarefa é só registrar o que já ocupa o tempo dele.

Responda EXCLUSIVAMENTE com JSON:
{"compromissos": [{"titulo": "até 6 palavras", "dia": 0, "data": null, "inicio": "HH:MM", "fim": "HH:MM", "tipo": "aula"}],
 "resposta": "uma frase confirmando o que você entendeu, na voz da Mentis: adulta, direta, sem emoji"}
Sem markdown, sem texto fora do JSON."""


class TextoPayload(BaseModel):
    texto: str = Field(min_length=3, max_length=_TEXTO_MAX_CHARS)
    # "voz" quando veio do microfone, "chat" quando foi digitado. Não muda
    # cobrança nem prompt — serve para saber, depois, se ditar pegou.
    origem: str = "chat"
    semana: Optional[str] = None


@router.post("/cronograma/compromissos/texto")
async def compromissos_por_texto(
    payload: TextoPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cronograma")),
):
    """`TEXTO_COST` Sparks: uma chamada ao modelo para virar português solto em
    agenda. Falhou, devolve os Sparks — aqui não há plano B determinístico,
    porque interpretar "trabalho dia sim dia não" é exatamente o que só o
    modelo faz."""
    doc = await _ler_doc(user.user_id)
    semana_iso = _semana_pedida(payload.semana, doc)
    origem = "voz" if payload.origem == "voz" else "chat"

    saldo = _cobrar(user.user_id, TEXTO_COST)
    hoje = _hoje(doc)
    contexto = (
        f"Hoje é {cg.DIAS[hoje.weekday()]}, {hoje.isoformat()}. "
        f"A semana mostrada começa na segunda {semana_iso}.\n\n"
        f"O ALUNO DISSE:\n{payload.texto.strip()}"
    )
    inicio = time.monotonic()
    try:
        resultado = await ai_service.generate_json_resiliente(
            TEXTO_SYSTEM, contexto, thinking_level="MINIMAL", timeout=_TIMEOUT_TEXTO
        )
        novos = cg.validar_compromissos_do_modelo(resultado, semana_iso=semana_iso, origem=origem)
        await llm_telemetry.persist(
            _db.cronograma_llm_chamadas,
            contexto=f"origem={origem} chars={len(payload.texto)}",
            motivo="extração de compromissos a partir de texto/voz do aluno",
            modelo="gemini (thinking=MINIMAL)",
            thinking_level="MINIMAL",
            resultado_estado="ok",
            duration_ms=(time.monotonic() - inicio) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        restituido = _safe_reembolso(user.user_id, TEXTO_COST)
        logger.exception(
            "cronograma: extração falhou para %s — %d Sparks devolvidos (saldo: %s).",
            user.user_id, TEXTO_COST, restituido,
        )
        raise HTTPException(
            status_code=503,
            detail="Não consegui ler seus compromissos agora. Seus Sparks foram devolvidos.",
        ) from exc

    if not novos:
        # Entendeu a frase e não achou compromisso nenhum: é resposta válida do
        # modelo, não falha de infraestrutura — mas o aluno pagou por uma
        # agenda e não recebeu nenhuma, então o Spark volta.
        restituido = _safe_reembolso(user.user_id, TEXTO_COST)
        return {
            "compromissos": [],
            "criados": 0,
            "resposta": (
                "Não reconheci nenhum compromisso nessa frase. Tente algo como "
                "\"aula de segunda a sexta das 7h às 12h30 e inglês terça às 19h\"."
            ),
            "sparks_balance": restituido if restituido is not None else saldo,
            "cobrado": 0,
        }

    atuais, criados, atualizados = cg.mesclar_compromissos(list(doc.get("compromissos") or []), novos)
    await _gravar(user.user_id, {"compromissos": atuais})
    resposta = (resultado or {}).get("resposta") if isinstance(resultado, dict) else None
    return {
        "compromissos": novos,
        "criados": criados,
        "atualizados": atualizados,
        "resposta": (resposta or "").strip()[:400] or f"Anotei {len(novos)} compromisso(s) na sua semana.",
        "sparks_balance": saldo,
        "cobrado": TEXTO_COST,
        "semana": _montar_semana({**doc, "compromissos": atuais}, semana_iso),
    }


# ---------------------------------------------------------------------------
# Importação: Google Agenda (OAuth) e endereço .ics
# ---------------------------------------------------------------------------


class EventosGooglePayload(BaseModel):
    # Os itens crus de `calendar/v3/events`, como o navegador recebeu. O
    # backend não fala com o Google: quem tem o token do aluno é a aba dele, e
    # é lá que o token deve morrer.
    eventos: list[dict[str, Any]] = Field(default_factory=list, max_length=400)
    semana: Optional[str] = None


class IcsPayload(BaseModel):
    url: str = Field(min_length=12, max_length=600)
    semana: Optional[str] = None


async def _aplicar_importacao(
    user: User, doc: dict, semana_iso: str, eventos: list[dict], origem: str
) -> dict[str, Any]:
    novos = cg.compromissos_de_eventos(eventos, semana_iso, origem=origem)
    if not novos:
        return {
            "criados": 0, "atualizados": 0, "compromissos": [],
            "aviso": "Nenhum evento desta semana veio na agenda importada.",
            "semana": _montar_semana(doc, semana_iso),
        }
    atuais, criados, atualizados = cg.mesclar_compromissos(list(doc.get("compromissos") or []), novos)
    await _gravar(user.user_id, {"compromissos": atuais})
    return {
        "criados": criados,
        "atualizados": atualizados,
        "compromissos": novos,
        "aviso": None,
        "semana": _montar_semana({**doc, "compromissos": atuais}, semana_iso),
    }


@router.post("/cronograma/importar/google")
async def importar_google(
    payload: EventosGooglePayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cronograma")),
):
    """Grátis. Recebe os eventos que o NAVEGADOR leu com o token do aluno.

    O backend nunca guarda nem vê credencial do Google: o popup de consentimento
    acontece na aba, o `access_token` fica na memória daquela página e o que
    chega aqui é o mesmo JSON público de qualquer evento de calendário.
    """
    doc = await _ler_doc(user.user_id)
    semana_iso = _semana_pedida(payload.semana, doc)
    crus = [e for e in (cg.normalizar_evento_google(ev) for ev in payload.eventos) if e]
    return await _aplicar_importacao(user, doc, semana_iso, crus, "google")


def _host_permitido(url: str) -> bool:
    try:
        partes = urlparse(url)
    except ValueError:
        return False
    if partes.scheme not in ("https", "webcal"):
        return False
    host = (partes.hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in _HOSTS_ICS)


@router.post("/cronograma/importar/ics")
async def importar_ics(
    payload: IcsPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cronograma")),
):
    """Grátis. Busca o "endereço secreto em formato iCal" do calendário.

    A lista de hosts (`_HOSTS_ICS`) não é conveniência, é a trava: esta rota
    faz o servidor buscar uma URL escolhida por quem chamou, e sem ela o
    endereço poderia apontar para dentro da própria infraestrutura. Com ela, o
    alcance da rota é exatamente "calendários dos três provedores".
    """
    url = payload.url.strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    if not _host_permitido(url):
        raise HTTPException(
            status_code=422,
            detail=(
                "Endereço não aceito. Use o link em formato iCal do Google Agenda, "
                "Outlook ou iCloud (ele termina em .ics)."
            ),
        )

    doc = await _ler_doc(user.user_id)
    semana_iso = _semana_pedida(payload.semana, doc)
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as cliente:
            resposta = await cliente.get(url)
        if (resposta.url.host or "").lower() not in [h for h in _HOSTS_ICS] and not any(
            (resposta.url.host or "").lower().endswith("." + h) for h in _HOSTS_ICS
        ):
            # Um redirecionamento para fora da lista anula a trava — então o
            # destino final é conferido de novo, depois de seguir os saltos.
            raise HTTPException(status_code=422, detail="O endereço redirecionou para fora dos provedores aceitos.")
        resposta.raise_for_status()
        corpo = resposta.text[:_ICS_MAX_BYTES]
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("cronograma: .ics não pôde ser lido para %s: %s", user.user_id, exc)
        raise HTTPException(
            status_code=502,
            detail="Não consegui abrir esse calendário. Confira se o endereço é o link privado em formato iCal.",
        ) from exc

    if "BEGIN:VCALENDAR" not in corpo:
        raise HTTPException(status_code=422, detail="Esse endereço não devolveu um calendário iCal.")
    crus = cg.eventos_do_ics(corpo, _fuso(doc))
    return await _aplicar_importacao(user, doc, semana_iso, crus, "ics")


# ---------------------------------------------------------------------------
# Gerar a semana
# ---------------------------------------------------------------------------

PLANO_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens. A semana de estudo
deste aluno JÁ ESTÁ MONTADA: os horários foram calculados em cima dos
compromissos reais dele, e a prioridade de cada área saiu do peso dela na nota
do ENEM cruzado com a lacuna medida no histórico do próprio aluno.

Você NÃO decide horário, NÃO move bloco, NÃO troca a área de um bloco e NÃO
cria bloco novo. Sua tarefa é escrever o conteúdo de cada bloco já alocado:
dizer, em uma frase, o que exatamente fazer naqueles minutos.

Escala de peso na prova, que você trata como fato dado: Matemática e Redação
são as frentes que mais movem a nota; depois vêm Biologia, Química e Física;
por último Ciências Humanas e Linguagens. Uma frente marcada como "ainda sem
medida" entrou pelo peso, não por diagnóstico — diga isso com franqueza em vez
de fingir que mediu.

Voz: adulta, direta, profissional. Sem emoji, sem euforia, sem "bons estudos".
Uma frase de menos é melhor que uma a mais.

Regras que você não quebra:
- Use SOMENTE os números que aparecem no contexto. Nunca invente porcentagem,
  nota ou quantidade de questões.
- Nunca use identificadores de catálogo (PROC-, ERR-, HAB-, DOM-, COMP-, INT-).
- Blocos de revisão e de treino tratam de um ponto específico já identificado:
  para eles, escreva o que praticar nesse ponto, não "revise a matéria".
- Nunca prometa material que o aluno não tem, nem mande procurar fora do app.

Responda EXCLUSIVAMENTE com JSON:
{"resumo": "2 a 3 frases abrindo a semana: o que ela prioriza e por quê, com o número que sustenta isso",
 "blocos": [{"indice": 0, "titulo": "até 7 palavras, concreto", "detalhe": "1 frase dizendo o que fazer nesses minutos"}],
 "recado": "1 frase: o risco mais provável de esta semana não acontecer, e como evitá-lo"}
Inclua um item em "blocos" para CADA índice que aparece no contexto, com o
mesmo índice. Sem markdown, sem texto fora do JSON."""


class GerarPayload(BaseModel):
    semana: Optional[str] = None
    # False (padrão) monta a semana sem tocar no modelo e sem custar nada.
    com_mentis: bool = False


@router.post("/cronograma/gerar")
async def gerar_cronograma(
    payload: GerarPayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("cronograma")),
):
    """Monta a semana de estudo em volta dos compromissos.

    **Grátis por padrão.** `com_mentis=true` cobra `MENTIS_COST` Sparks para a
    Mentis escrever o conteúdo de cada bloco — e se ela falhar, os Sparks
    voltam e a semana determinística é entregue do mesmo jeito. Pedir
    cronograma nunca termina em mão vazia.
    """
    fs.ensure_student_profile(user.user_id, user.name, user.email)
    doc = await _ler_doc(user.user_id)
    semana_iso = _semana_pedida(payload.semana, doc)

    prioridades = await _prioridades(user.user_id)
    revisoes, fracas = await asyncio.gather(
        _fila_de_revisao(user.user_id), _habilidades_fracas(user.user_id)
    )
    compromissos = cg.compromissos_da_semana(doc.get("compromissos") or [], semana_iso)
    slots = cg.slots_livres(doc.get("compromissos") or [], doc.get("preferencias"), semana_iso)
    montado = cg.alocar(
        slots, prioridades, revisoes=revisoes, habilidades_fracas=fracas,
        preferencias=doc.get("preferencias"),
    )
    blocos = montado["blocos"]
    resumo = cg.resumo_deterministico(blocos, montado["distribuicao"], prioridades)
    recado = None
    com_mentis = False
    saldo = None
    cobrado = 0
    aviso = None

    if payload.com_mentis and blocos:
        saldo = _cobrar(user.user_id, MENTIS_COST)
        cobrado = MENTIS_COST
        inicio = time.monotonic()
        try:
            resultado = await ai_service.generate_json_resiliente(
                PLANO_SYSTEM,
                cg.resumo_para_modelo(blocos, prioridades, compromissos),
                thinking_level="MINIMAL",
                timeout=_TIMEOUT_PLANO,
            )
            blocos, reescritos = cg.aplicar_enriquecimento(blocos, resultado)
            if not reescritos:
                raise ValueError("A resposta não reescreveu nenhum bloco.")
            texto = (resultado or {}).get("resumo") if isinstance(resultado, dict) else None
            if isinstance(texto, str) and texto.strip():
                resumo = texto.strip()[:600]
            fala = (resultado or {}).get("recado") if isinstance(resultado, dict) else None
            if isinstance(fala, str) and fala.strip():
                recado = fala.strip()[:300]
            com_mentis = True
            await llm_telemetry.persist(
                _db.cronograma_llm_chamadas,
                contexto=f"semana={semana_iso} blocos={len(blocos)}",
                motivo="Mentis escrevendo o conteúdo dos blocos já alocados",
                modelo="gemini (thinking=MINIMAL)",
                thinking_level="MINIMAL",
                resultado_estado="ok",
                duration_ms=(time.monotonic() - inicio) * 1000,
            )
        except Exception:  # noqa: BLE001
            saldo = _safe_reembolso(user.user_id, MENTIS_COST)
            cobrado = 0
            aviso = (
                "A Mentis não conseguiu comentar sua semana agora e seus Sparks foram devolvidos — "
                "mas o cronograma abaixo está montado com o mesmo critério de sempre."
            )
            logger.exception(
                "cronograma: enriquecimento falhou para %s — %d Sparks devolvidos.",
                user.user_id, MENTIS_COST,
            )

    plano = {
        "semana": semana_iso,
        "gerado_em": _agora_iso(),
        "blocos": blocos,
        "distribuicao": montado["distribuicao"],
        "resumo": resumo,
        "recado": recado,
        "com_mentis": com_mentis,
    }
    # Gerar de novo zera os "feitos" DAQUELA semana: os ids dos blocos são
    # novos, e manter a marcação antiga daria check em bloco que não existe
    # mais. Semanas anteriores continuam intactas.
    concluidos = {k: v for k, v in (doc.get("concluidos") or {}).items() if k != semana_iso}
    await _gravar(user.user_id, {"plano": plano, "concluidos": concluidos})

    return {
        "semana": _montar_semana({**doc, "plano": plano, "concluidos": concluidos}, semana_iso),
        "prioridades": prioridades,
        "sparks_balance": saldo,
        "cobrado": cobrado,
        "aviso": aviso,
        "sem_horario_livre": not blocos,
    }


class ConcluirPayload(BaseModel):
    concluido: bool = True
    semana: Optional[str] = None


@router.post("/cronograma/bloco/{bloco_id}/concluir")
async def concluir_bloco(bloco_id: str, payload: ConcluirPayload, user: User = Depends(require_user)):
    """Marca (ou desmarca) um bloco como feito. Grátis, e de propósito sem
    nenhum efeito sobre o diagnóstico: dizer "fiz" não é evidência de nada —
    quem mede aprendizagem aqui é a resposta a questão, não o autorrelato."""
    doc = await _ler_doc(user.user_id)
    semana_iso = _semana_pedida(payload.semana, doc)
    plano = doc.get("plano") or {}
    if plano.get("semana") != semana_iso:
        raise HTTPException(status_code=409, detail="Esta semana ainda não tem cronograma montado.")
    if not any(b.get("id") == bloco_id for b in (plano.get("blocos") or [])):
        raise HTTPException(status_code=404, detail="Bloco não encontrado nesta semana.")

    concluidos = dict(doc.get("concluidos") or {})
    da_semana = set(concluidos.get(semana_iso) or [])
    if payload.concluido:
        da_semana.add(bloco_id)
    else:
        da_semana.discard(bloco_id)
    concluidos[semana_iso] = sorted(da_semana)
    # Guarda só as 6 semanas mais recentes: o histórico de check não alimenta
    # nenhuma decisão do produto, e um documento que só cresce acaba virando o
    # problema dele mesmo.
    concluidos = dict(sorted(concluidos.items(), reverse=True)[:6])
    await _gravar(user.user_id, {"concluidos": concluidos})
    total = len(plano.get("blocos") or [])
    return {
        "bloco_id": bloco_id,
        "concluido": payload.concluido,
        "total_concluidos": len(da_semana),
        "total_blocos": total,
    }
