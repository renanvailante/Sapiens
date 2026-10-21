"""Notificação no celular — o que lê o banco, assina e envia.

As regras (quando, o quê, para onde) estão em `push.py`, sem I/O. Aqui fica o
resto: a inscrição do aparelho, a medição dos sinais do aluno, o envio pelo
serviço de push do navegador e o laço agendado.

Duas coleções no Mongo, as duas por aluno e as duas em
`dados_pessoais.COLECOES_POR_USUARIO` (saem com a conta):

* `push_inscricoes` — um documento por APARELHO (`_id` = sha256 do endpoint):
  o endereço que o serviço de push do navegador deu e as duas chaves públicas
  para cifrar a mensagem. Nada sobre o aluno além de `user_id`.
* `push_envios` — a reivindicação diária (`_id` = `"{uid}:{dia}"`), com o tipo
  do que saiu. É o teto de uma notificação por dia, garantido pelo `_id`; um
  TTL de 40 dias apaga o histórico, que não é fonte de verdade de nada.

**A chave privada VAPID mora só no secret `VAPID_PRIVATE_KEY` do Fly.** A
pública é derivada dela aqui, em memória — um par só, sem a chance de as duas
metades divergirem entre `fly.toml` e secret (a armadilha que já custou um
incidente com `FIRESTORE_AUTO_SYNC_SECONDS`).

Custo do laço (a conta inteira está no `fly.toml`, ao lado das variáveis):
fora do horário da avaliação, zero I/O; dentro dela, O(inscritos) no Mongo e
**no máximo UMA leitura do Firestore por aluno inscrito por dia** — a do
documento `students/{uid}`, que traz o agregado e o estado de revisão juntos.
Nada aqui varre `behavior`.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from pymongo.errors import DuplicateKeyError

import engajamento as eng
import firestore_service as fs
import intervencoes
import push
import revisao_espacada as rev
import settings

logger = logging.getLogger("sapiens.push")

_db = None


def set_db(db):
    global _db
    _db = db


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

def _int_env(nome: str, padrao: int) -> int:
    try:
        return int(os.environ.get(nome, padrao) or padrao)
    except (TypeError, ValueError):
        return padrao


# De quanto em quanto tempo o laço acorda. 900s = 15 min: dentro da janela da
# avaliação (19h–21h) isso são 8 ciclos — sobra para quem não coube num ciclo
# (ver `PUSH_MAX_POR_CICLO`) e para uma máquina que reiniciou no meio.
PUSH_LACO_SEGUNDOS = _int_env("PUSH_LACO_SEGUNDOS", 900)
PUSH_HORA_AVALIACAO = push.hora_da_avaliacao(os.environ.get("PUSH_HORA_AVALIACAO"))
# Teto de alunos avaliados por ciclo. Não é o teto do dia: quem não coube volta
# no ciclo seguinte. Existe para um ciclo nunca virar uma rajada de milhares de
# leituras do Firestore de uma vez só.
PUSH_MAX_POR_CICLO = _int_env("PUSH_MAX_POR_CICLO", 400)
# A mensagem fala de HOJE. Se o aparelho estiver desligado até amanhã, ela não
# deve chegar amanhã dizendo que a sequência "acaba à meia-noite".
PUSH_TTL_SEGUNDOS = 4 * 3600
MAX_INSCRICOES_POR_ALUNO = 5
EXPURGO_ENVIOS_DIAS = 40

_VAPID: Any = None
_VAPID_ORIGEM: str | None = None


def _vapid():
    """O par VAPID, montado uma vez a partir do secret. `None` sem secret —
    e aí o push simplesmente não existe neste ambiente (o app sobe igual)."""
    global _VAPID, _VAPID_ORIGEM
    bruto = (os.environ.get("VAPID_PRIVATE_KEY") or "").strip()
    if not bruto:
        return None
    if _VAPID is not None and _VAPID_ORIGEM == bruto:
        return _VAPID
    try:
        from py_vapid import Vapid01

        _VAPID = Vapid01.from_string(private_key=bruto)
        _VAPID_ORIGEM = bruto
    except Exception as exc:  # noqa: BLE001
        logger.error("VAPID_PRIVATE_KEY inválida — push desligado: %s", type(exc).__name__)
        _VAPID, _VAPID_ORIGEM = None, None
    return _VAPID


def chave_publica() -> str | None:
    """A `applicationServerKey` que o navegador pede: o ponto público P-256
    não comprimido (65 bytes), em base64url sem `=`."""
    v = _vapid()
    if v is None:
        return None
    from cryptography.hazmat.primitives import serialization

    bruto = v.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return base64.urlsafe_b64encode(bruto).decode("ascii").rstrip("=")


def _assunto_vapid() -> str:
    """Contato do remetente, exigido pelos serviços de push (a Apple recusa
    sem ele). O endereço público do produto — nunca um e-mail pessoal."""
    explicito = (os.environ.get("VAPID_SUBJECT") or "").strip()
    if explicito.startswith(("mailto:", "https://")):
        return explicito
    base = settings.frontend_base()
    return base if base.startswith("https://") else "https://sapiens-aluno.pages.dev"


def _agora_local() -> datetime:
    return datetime.now(fs.ZONA_BRASIL)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id_da_inscricao(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Inscrição
# ---------------------------------------------------------------------------

async def inscrever(uid: str, endpoint: str, p256dh: str, auth: str, *, aparelho: str | None = None) -> dict:
    """Grava (ou reatribui) a inscrição deste aparelho.

    O `_id` é o endpoint: o mesmo aparelho inscrito de novo é a MESMA linha,
    e um aparelho que trocou de conta passa a notificar só a conta nova —
    quem entra no celular de outra pessoa não herda as notificações dela.
    """
    if _db is None:
        raise RuntimeError("push_service.set_db não foi chamado")
    agora = _now_iso()
    _id = _id_da_inscricao(endpoint)
    await _db.push_inscricoes.update_one(
        {"_id": _id},
        {
            "$set": {
                "user_id": uid,
                "endpoint": endpoint,
                "chaves_push": {"p256dh": p256dh, "auth": auth},
                "aparelho": (aparelho or "")[:120] or None,
                "atualizado_em": agora,
            },
            "$setOnInsert": {"criado_em": agora},
        },
        upsert=True,
    )
    # Teto de aparelhos: o mais antigo sai. Quem troca de celular todo ano não
    # acumula cinco inscrições mortas recebendo cada envio.
    docs = await _db.push_inscricoes.find({"user_id": uid}, {"_id": 1, "criado_em": 1}).to_list(50)
    if len(docs) > MAX_INSCRICOES_POR_ALUNO:
        docs.sort(key=lambda d: d.get("criado_em") or "")
        for velho in docs[: len(docs) - MAX_INSCRICOES_POR_ALUNO]:
            await _db.push_inscricoes.delete_one({"_id": velho["_id"], "user_id": uid})
    return {"inscrito": True}


async def desinscrever(uid: str, endpoint: str) -> dict:
    if _db is None:
        raise RuntimeError("push_service.set_db não foi chamado")
    r = await _db.push_inscricoes.delete_one({"_id": _id_da_inscricao(endpoint), "user_id": uid})
    return {"inscrito": False, "removida": bool(getattr(r, "deleted_count", 0))}


# ---------------------------------------------------------------------------
# Os sinais do aluno — tudo medido, nada inventado
# ---------------------------------------------------------------------------

# Quantas linhas da fila de revisão olhar procurando questão nova. A fila já
# vem ordenada por urgência; olhar além das primeiras é pagar CPU para escolher
# um ponto que o próprio Próximo Passo não escolheria.
_LINHAS_DE_PADRAO = 3


def _trecho_volta_ate(doc: dict, hoje: str) -> bool:
    """Mesma regra de `lembretes_routes._revisar_em`: a data agendada, ou o
    dia seguinte ao que o trecho foi guardado (lembrete anterior à revisão
    programada). Importada de lá para não existir uma segunda definição."""
    import lembretes_routes

    quando = lembretes_routes._revisar_em(doc)
    return bool(quando and quando <= hoje)


async def sinais_do_aluno(uid: str, hoje: str) -> dict[str, Any] | None:
    """Os números de que `push.escolher_mensagem` precisa. `None` quando a
    leitura do Firestore falhou — e aí NÃO se manda nada: avisar que a
    sequência acaba sem ter conseguido ler a sequência seria inventar."""
    try:
        estado = await asyncio.to_thread(fs.ler_estado_do_aluno, uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("push: estado de %s indisponível: %s", uid, type(exc).__name__)
        return None

    agregado = estado.get("agregado") or {}
    bloco_revisao = estado.get("revisao") or {}

    perfil = (await _db.engajamento_perfil.find_one({"_id": uid})) or {}
    # `calcular_ofensiva` é pura: aqui ela NÃO gasta congelador (quem gasta é
    # `engajamento_service.estado`, quando o aluno abre o app). Ela só diz se,
    # com os congeladores que ele tem, a sequência ainda está viva.
    ofensiva = eng.calcular_ofensiva(
        agregado.get("dias_ativos") or [],
        hoje=hoje,
        dias_congelados=perfil.get("dias_congelados") or [],
        congeladores=int(perfil.get("congeladores") or 0),
    )

    linhas = rev.fila(bloco_revisao, hoje, limite=rev.FILA_TAMANHO)
    revisoes_hoje = sum(1 for l in linhas if l.get("vencido"))

    lembretes = await _db.lembretes_revisao.find(
        {"user_id": uid, "status": "aberto"},
        {"_id": 0, "agendamento": 1, "criado_em": 1, "status": 1},
    ).to_list(200)
    trechos_hoje = sum(1 for d in lembretes if _trecho_volta_ate(d, hoje))

    padrao = None
    respondidos = agregado.get("item_ids_respondidos") or []
    for linha in linhas[:_LINHAS_DE_PADRAO]:
        if not linha.get("erro_dominante") or linha.get("sem_intervencao_catalogada"):
            continue
        try:
            novas = intervencoes.sugerir_pratica(linha["processo_id"], respondidos, limite=50)
        except Exception:  # noqa: BLE001
            logger.exception("push: sugestão de prática falhou para %s", uid)
            break
        if novas.get("itens"):
            padrao = {"questoes_novas": len(novas["itens"])}
            break

    doc_dia = (await _db.engajamento_dia.find_one({"_id": f"{uid}:{hoje}"})) or {}
    # A lista que o dia já fixou (`engajamento_service._missoes_de_hoje`); sem
    # ela, o sorteio de sempre — o aviso só cita a primeira pendente, que é de
    # prática e não depende de sinal nenhum.
    missoes = eng.missoes_do_dia(
        uid, hoje, doc_dia.get("contadores") or {}, doc_dia.get("resgatadas") or [],
        fixadas=doc_dia.get("missoes_ids"),
    )
    missao = next((m for m in missoes if not m["concluida"]), None)

    return {
        "ofensiva": {
            "dias": ofensiva.dias,
            "estudou_hoje": ofensiva.estudou_hoje,
            "em_risco": ofensiva.em_risco,
        },
        "trechos_hoje": trechos_hoje,
        "revisoes_hoje": revisoes_hoje,
        "padrao": padrao,
        "missao": missao,
    }


# ---------------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------------

def _webpush(inscricao: dict, corpo: str) -> None:
    from pywebpush import webpush

    chaves = inscricao.get("chaves_push") or {}
    webpush(
        subscription_info={
            "endpoint": inscricao["endpoint"],
            "keys": {"p256dh": chaves.get("p256dh"), "auth": chaves.get("auth")},
        },
        data=corpo,
        vapid_private_key=_vapid(),
        # Dicionário NOVO a cada envio: o `webpush` grava `aud` nele a partir
        # do endpoint. Reaproveitado, a segunda inscrição (Firefox depois de
        # Chrome) sairia assinada para o serviço da primeira e seria recusada.
        vapid_claims={"sub": _assunto_vapid()},
        ttl=PUSH_TTL_SEGUNDOS,
        timeout=10,
    )


def _status_da_falha(exc: Exception) -> int | None:
    resposta = getattr(exc, "response", None)
    return getattr(resposta, "status_code", None)


async def enviar(uid: str, mensagem: dict[str, str], *, transporte: Callable[[dict, str], None] | None = None) -> dict:
    """Manda a mensagem para todos os aparelhos do aluno.

    404/410 do serviço de push quer dizer "esta inscrição não existe mais" (o
    aluno desinstalou, limpou o navegador, revogou a permissão): a linha é
    apagada, e não tentada de novo amanhã.
    """
    enviar_um = transporte or _webpush
    corpo = json.dumps(
        {k: mensagem[k] for k in ("titulo", "corpo", "rota", "tag", "tipo")},
        ensure_ascii=False,
    )
    inscricoes = await _db.push_inscricoes.find({"user_id": uid}).to_list(MAX_INSCRICOES_POR_ALUNO * 2)
    enviados = removidas = falhas = 0
    for inscricao in inscricoes:
        try:
            await asyncio.to_thread(enviar_um, inscricao, corpo)
            enviados += 1
        except Exception as exc:  # noqa: BLE001
            status = _status_da_falha(exc)
            if status in (404, 410):
                await _db.push_inscricoes.delete_one({"_id": inscricao["_id"]})
                removidas += 1
            else:
                falhas += 1
                logger.warning("push: envio para %s falhou (%s, status %s)", uid, type(exc).__name__, status)
    return {"enviados": enviados, "removidas": removidas, "falhas": falhas}


# ---------------------------------------------------------------------------
# O laço
# ---------------------------------------------------------------------------

async def ciclo(
    agora_local: datetime | None = None,
    *,
    transporte: Callable[[dict, str], None] | None = None,
) -> dict[str, Any]:
    """Uma passada. Devolve o que fez, para o log e para os testes.

    Ordem das guardas, da mais barata para a mais cara: relógio (nenhum I/O),
    lista de inscritos e reivindicações do dia (Mongo, O(inscritos)), e só
    então, por aluno ainda não avaliado hoje, a leitura do Firestore.
    """
    relogio = (lambda: agora_local) if agora_local is not None else _agora_local
    agora = relogio()
    saida: dict[str, Any] = {"avaliados": 0, "enviados": 0, "sem_mensagem": 0, "indisponiveis": 0}
    if _db is None:
        return {**saida, "motivo": "sem_banco"}
    if transporte is None and _vapid() is None:
        return {**saida, "motivo": "sem_vapid"}
    if not push.hora_de_avaliar(agora, PUSH_HORA_AVALIACAO):
        return {**saida, "motivo": "fora_do_horario"}

    hoje = agora.date().isoformat()
    inscritos = {
        d["user_id"]
        for d in await _db.push_inscricoes.find({}, {"_id": 0, "user_id": 1}).to_list(None)
        if d.get("user_id")
    }
    ja_avaliados = {
        d["user_id"]
        for d in await _db.push_envios.find({"dia": hoje}, {"_id": 0, "user_id": 1}).to_list(None)
    }
    pendentes = sorted(inscritos - ja_avaliados)
    saida["pendentes"] = len(pendentes)

    for uid in pendentes[:PUSH_MAX_POR_CICLO]:
        # O ciclo pode atravessar as 21h: a janela vale para cada envio, não
        # só para o começo da passada.
        if not push.dentro_da_janela(relogio()):
            saida["motivo"] = "janela_fechou"
            break
        try:
            await _db.push_envios.insert_one({
                "_id": push.chave_do_dia(uid, hoje),
                "user_id": uid,
                "dia": hoje,
                "criado_em": _now_iso(),
                "expurgo_em_dt": datetime.now(timezone.utc) + timedelta(days=EXPURGO_ENVIOS_DIAS),
            })
        except DuplicateKeyError:
            continue  # outra máquina (ou um ciclo anterior) já pegou este aluno hoje
        saida["avaliados"] += 1

        sinais = await sinais_do_aluno(uid, hoje)
        if sinais is None:
            saida["indisponiveis"] += 1
            await _db.push_envios.update_one({"_id": push.chave_do_dia(uid, hoje)}, {"$set": {"tipo": None, "motivo": "leitura_indisponivel"}})
            continue
        mensagem = push.escolher_mensagem(sinais)
        if mensagem is None:
            saida["sem_mensagem"] += 1
            await _db.push_envios.update_one({"_id": push.chave_do_dia(uid, hoje)}, {"$set": {"tipo": None, "motivo": "sem_sinal"}})
            continue
        resultado = await enviar(uid, mensagem, transporte=transporte)
        saida["enviados"] += resultado["enviados"]
        await _db.push_envios.update_one(
            {"_id": push.chave_do_dia(uid, hoje)},
            {"$set": {"tipo": mensagem["tipo"], **resultado, "enviado_em": _now_iso()}},
        )
    return saida


async def laco() -> None:
    """Roda para sempre, com o mesmo contrato dos outros laços do `server.py`:
    uma falha é logada e o ciclo seguinte tenta de novo; nada derruba o
    processo. `PUSH_LACO_SEGUNDOS <= 0` desliga."""
    if PUSH_LACO_SEGUNDOS <= 0:
        logger.warning("Push DESLIGADO (PUSH_LACO_SEGUNDOS=%d).", PUSH_LACO_SEGUNDOS)
        return
    if _vapid() is None:
        logger.warning("Push sem VAPID_PRIVATE_KEY — nenhuma notificação sai deste processo.")
    while True:
        await asyncio.sleep(PUSH_LACO_SEGUNDOS)
        try:
            resultado = await ciclo()
            if resultado.get("avaliados"):
                logger.info("Push: %s", resultado)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Push: ciclo falhou (tentando de novo em %ds): %s", PUSH_LACO_SEGUNDOS, exc)
