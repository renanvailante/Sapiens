"""Firestore integration for Sapiens (backend-only).

Read:  pipeline/questao, pipeline/fonte, pipeline/config/behavior_schema
Write: students_behavior/students_id/{uid}/behavior_student

Nao usa Firebase Authentication. A autenticacao e a sessao em cookie do
proprio backend (auth.require_user), unica camada de auth desde a remocao da
Emergent em 2026-08-21.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core import exceptions as gcloud_exceptions

logger = logging.getLogger("sapiens.firestore")

_FS_CLIENT = None


def _load_credentials() -> credentials.Certificate:
    raw_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    if raw_json:
        return credentials.Certificate(json.loads(raw_json))
    if path:
        return credentials.Certificate(path)
    raise RuntimeError(
        "Firebase credentials not configured. Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON."
    )


def get_firestore():
    """Return a cached Firestore client (lazy init)."""
    global _FS_CLIENT
    if _FS_CLIENT is not None:
        return _FS_CLIENT
    try:
        app = firebase_admin.get_app()
    except ValueError:
        options = {}
        if pid := os.environ.get("FIREBASE_PROJECT_ID"):
            options["projectId"] = pid
        app = firebase_admin.initialize_app(_load_credentials(), options=options)
        logger.info("Firebase Admin initialized for project=%s", app.project_id)
    _FS_CLIENT = firestore.client(app)
    return _FS_CLIENT


# ---------- Read helpers ----------

def read_collection(path: str, limit: int = 100) -> list[dict[str, Any]]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    docs = get_firestore().collection(path).limit(limit).stream()
    return [{"id": snap.id, **(snap.to_dict() or {})} for snap in docs]


def read_document(collection_path: str, document_id: str) -> Optional[dict[str, Any]]:
    snap = get_firestore().collection(collection_path).document(document_id).get()
    if not snap.exists:
        return None
    return {"id": snap.id, **(snap.to_dict() or {})}


# ---------- Student behavior (nested path) ----------

def _behavior_ref(uid: str):
    return (
        get_firestore()
        .collection("students_behavior")
        .document("students_id")
        .collection(uid)
        .document("behavior_student")
    )


def write_student_behavior(uid: str, data: dict[str, Any]) -> dict[str, Any]:
    ref = _behavior_ref(uid)
    ref.set(data, merge=True)
    return {"path": ref.path, **data}


def read_student_behavior(uid: str) -> Optional[dict[str, Any]]:
    snap = _behavior_ref(uid).get()
    if not snap.exists:
        return None
    return {"id": snap.id, **(snap.to_dict() or {})}


# ---------- Seed / provisioning ----------

def _initial_behavior_doc(uid: str, email: Optional[str] = None, name: Optional[str] = None) -> dict[str, Any]:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    return {
        "user_id": uid,
        "email": email,
        "name": name,
        "profile": {
            "reading_speed": None,
            "confidence_level": None,
            "attention_span": None,
            "error_pattern": None,
        },
        "stats": {
            "total_answered": 0,
            "total_correct": 0,
            "total_incorrect": 0,
            "avg_time_seconds": 0,
        },
        "flags": {
            "onboarded": False,
            "first_exam_done": False,
        },
        "events": [],
        "created_at": now,
        "updated_at": now,
    }


# Alunos cujo documento já foi confirmado neste processo. `ensure_student_profile`
# e `ensure_student_behavior` são checagens de EXISTÊNCIA, e existência aqui é
# monotônica: uma vez criado, o documento não deixa de existir. Sem esta memória,
# cada uma custava 1 leitura do Firestore por REQUISIÇÃO — e elas estão no
# caminho de quase toda rota autenticada (`/diagnostico`, `/skills-map`,
# `/mentis/*`, `/students/me/*`), então um aluno navegando pagava leitura só
# para perguntar de novo algo cuja resposta nunca muda.
#
# Deliberadamente em memória do processo, como o `rate_limit`: com mais de uma
# máquina cada uma aquece o próprio conjunto, o que custa 1 leitura por aluno
# por máquina e continua correto — `ref.set()` é idempotente. Reiniciar limpa,
# que é o comportamento desejado (nunca serve como fonte de verdade).
_PROVISIONADO_PROFILE: set[str] = set()
_PROVISIONADO_BEHAVIOR: set[str] = set()


def esquecer_provisionamento(uid: str) -> None:
    """Tira o aluno da memória de provisionamento. Para testes e para o caso
    de um documento ser apagado à mão em produção."""
    _PROVISIONADO_PROFILE.discard(uid)
    _PROVISIONADO_BEHAVIOR.discard(uid)


def ensure_student_behavior(uid: str, email: Optional[str] = None, name: Optional[str] = None) -> bool:
    """Create the behavior_student doc if it does not yet exist. Returns True if created."""
    if uid in _PROVISIONADO_BEHAVIOR:
        return False
    ref = _behavior_ref(uid)
    if ref.get().exists:
        _PROVISIONADO_BEHAVIOR.add(uid)
        return False
    ref.set(_initial_behavior_doc(uid, email, name))
    _PROVISIONADO_BEHAVIOR.add(uid)
    return True


async def seed_all_students(mongo_db) -> dict[str, int]:
    """Idempotently create behavior docs for every non-admin user in MongoDB."""
    created = 0
    skipped = 0
    async for u in mongo_db.users.find({}, {"_id": 0, "user_id": 1, "email": 1, "name": 1, "is_admin": 1}):
        if u.get("is_admin"):
            skipped += 1
            continue
        try:
            if await asyncio.to_thread(ensure_student_behavior, u["user_id"], u.get("email"), u.get("name")):
                created += 1
            else:
                skipped += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed_all_students failed for %s: %s", u.get("user_id"), exc)
    logger.info("Firestore student seed: created=%d skipped=%d", created, skipped)
    return {"created": created, "skipped": skipped}



# ======================================================================
# NEW student data structure (Fase 1)
#   students/{uid}                      -> documento "profile" do aluno
#   students/{uid}/behavior/{event_id}  -> um documento por evento de resposta
# NÃO usa Firebase Auth. O uid vem da autenticação já existente.
# ======================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _student_doc_ref(uid: str):
    return get_firestore().collection("students").document(uid)


def _behavior_collection_ref(uid: str):
    return _student_doc_ref(uid).collection("behavior")


SPARKS_INITIAL_BALANCE = 100  # bônus padrão de aluno novo SEM código de promoção válido.


def ensure_student_profile(
    uid: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    initial_sparks: Optional[int] = None,
) -> bool:
    """Cria o documento de profile do aluno em students/{uid} se ainda não existir.
    Deve ser chamado no login (via provisionamento já existente). Retorna True se criou.

    `initial_sparks` é passado só pelo signup (`auth.py`), que já sabe se um
    código de promoção válido trocou o bônus padrão — os demais chamadores
    (rotas protegidas comuns, que só existem para cobrir perfis antigos ou
    uma corrida com o signup) não passam nada e caem no padrão.
    """
    if uid in _PROVISIONADO_PROFILE:
        return False
    ref = _student_doc_ref(uid)
    if ref.get().exists:
        _PROVISIONADO_PROFILE.add(uid)
        return False
    ref.set({
        "nome": name,
        "email": email,
        "created_at": _now_iso(),
        "sparks_balance": initial_sparks if initial_sparks is not None else SPARKS_INITIAL_BALANCE,
    })
    _PROVISIONADO_PROFILE.add(uid)
    return True


def ensure_sparks_balance(uid: str) -> int:
    """Garante que students/{uid} tenha `sparks_balance`, inicializando com
    `SPARKS_INITIAL_BALANCE` se ausente — cobre perfis criados antes desta
    feature existir. Idempotente: não sobrescreve um saldo já existente.
    Retorna o saldo atual (após garantir que existe).
    """
    ref = _student_doc_ref(uid)
    snap = ref.get()
    data = snap.to_dict() or {}
    if "sparks_balance" in data:
        return data["sparks_balance"]
    ref.set({"sparks_balance": SPARKS_INITIAL_BALANCE}, merge=True)
    return SPARKS_INITIAL_BALANCE


def read_sparks_balance(uid: str) -> int:
    snap = _student_doc_ref(uid).get()
    return (snap.to_dict() or {}).get("sparks_balance", SPARKS_INITIAL_BALANCE)


def compute_item_hash(item_content: Any) -> str:
    """Hash determinístico do conteúdo da questão no momento da resposta."""
    canonical = json.dumps(item_content, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


BEHAVIOR_SCHEMA_VERSION = "1.1"


def write_behavior_event(
    uid: str,
    *,
    item_id: str,
    ontology_version: Optional[str] = None,
    alternativa_escolhida: Optional[str] = None,
    acertou: Optional[bool] = None,
    item_schema_version: Optional[str] = None,
    item_content: Any = None,
    item_hash: Optional[str] = None,
    contexto_tipo: Optional[str] = None,
    prova_id: Optional[str] = None,
    origem: str = "firestore",
    tempo_resposta_segundos: float = 0,
    numero_tentativas: int = 1,
    mudou_resposta: bool = False,
    status: str = "respondida",
    dispositivo: Optional[str] = None,
    versao_aplicacao: Optional[str] = None,
    attempt_id: Optional[str] = None,
    event_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Escreve UM evento de behavior em students/{uid}/behavior/{event_id}.

    Contrato: `pipeline/docs/behavior/07 behavior student 1.4.md`, versão
    **1.1** (o "1.4" do nome do arquivo é resíduo de nomeação e nunca foi versão
    deste contrato — GOV-1.0 §6.1).

    `ontology_version` é **obrigatório** desde a 1.1: é a versão da ontologia
    contra a qual o ITEM estava anotado no momento da resposta, não a versão
    ativa hoje. Sem ela, o evento não pode ser reinterpretado depois de a
    ontologia mudar de versão MAIOR, porque não há como saber contra qual
    catálogo o item estava anotado quando o estudante respondeu.

    Nota sobre o bloco `desempenho` (estatuto declarado na 1.1): esses campos são
    o que o White Paper 1.0 chamava de Indicador Comportamental, nível removido
    na arquitetura vigente. Eles são **coletados e registrados**, e **não**
    alimentam atualização de crença sobre o estado cognitivo do estudante — o
    canal de evidência além de acerto/erro segue regido por GL-3, aberto.
    """
    event_id = event_id or uuid.uuid4().hex
    if item_hash is None and item_content is not None:
        item_hash = compute_item_hash(item_content)
    if not ontology_version:
        raise ValueError(
            "ontology_version é obrigatório no contrato de behavior 1.1 "
            "(GOV-1.0 §6.1). Ele vem do item respondido — a versão contra a qual "
            "o item estava anotado —, nunca da ontologia ativa no momento da escrita."
        )

    event = {
        "schema_version": BEHAVIOR_SCHEMA_VERSION,
        "ontology_version": ontology_version,
        "event_id": event_id,
        "attempt_id": attempt_id or uuid.uuid4().hex,
        "student_id": uid,
        "item_id": item_id,
        "item_schema_version": item_schema_version,
        "item_hash": item_hash,
        "timestamp": timestamp or _now_iso(),
        "contexto": {
            "tipo": contexto_tipo,
            "prova_id": prova_id,
            "origem": origem,
        },
        "resposta": {
            "alternativa_escolhida": alternativa_escolhida,
            "acertou": acertou,
        },
        "desempenho": {
            "tempo_resposta_segundos": tempo_resposta_segundos,
            "numero_tentativas": numero_tentativas,
            "mudou_resposta": mudou_resposta,
        },
        "status": status,
        "metadados": {
            "dispositivo": dispositivo,
            "versao_aplicacao": versao_aplicacao,
        },
    }

    _behavior_collection_ref(uid).document(event_id).set(event)
    if status == "respondida":
        _atualizar_agregado(uid, item_id=item_id, timestamp=event["timestamp"])
    return event


# ---------------------------------------------------------------------------
# Agregado do aluno — o que o painel lê em vez de varrer o histórico
#
# `/students/me/respondidas` e `/students/me/activity` liam TODO o histórico de
# eventos (limites de 5.000 e 3.000 documentos) só para derivar uma lista de
# `item_id`s e um conjunto de datas. O painel dispara as duas a cada
# carregamento, então o custo de leitura no Firestore crescia junto com o
# engajamento: um aluno com 500 questões respondidas gerava mais de mil
# leituras por abertura de painel, e cem alunos ativos passavam com folga das
# 50 mil leituras/dia do plano gratuito.
#
# O agregado é mantido no ato da escrita (uma operação a mais por resposta) e
# lido como UM documento. Nunca é fonte de verdade: o histórico de eventos
# continua sendo, e `reconstruir_agregado` o recompõe a partir dele — é o que
# roda para alunos que já respondiam antes deste campo existir.
# ---------------------------------------------------------------------------

# Fuso do aluno. O streak e o calendário da semana eram calculados em UTC, e o
# Brasil está em UTC-3: quem respondia depois das 21h tinha a atividade contada
# no dia seguinte, a bolinha de "hoje" ficava apagada depois de estudar e a
# sequência podia zerar sem motivo — exatamente o horário em que vestibulando
# estuda, e a sequência é a mecânica que o traz de volta.
ZONA_BRASIL = ZoneInfo("America/Sao_Paulo")


def dia_local(timestamp_iso: str | None = None) -> str:
    """`YYYY-MM-DD` no fuso do aluno, a partir de um timestamp ISO em UTC."""
    if timestamp_iso:
        momento = datetime.fromisoformat(timestamp_iso)
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=timezone.utc)
    else:
        momento = datetime.now(timezone.utc)
    return momento.astimezone(ZONA_BRASIL).date().isoformat()


def _atualizar_agregado(uid: str, *, item_id: str, timestamp: str) -> None:
    """Acrescenta ao agregado o efeito de uma resposta. Idempotente por
    natureza: `ArrayUnion` não duplica, então reprocessar não distorce."""
    try:
        _student_doc_ref(uid).set(
            {
                "agregado": {
                    "item_ids_respondidos": firestore.ArrayUnion([item_id]),
                    "dias_ativos": firestore.ArrayUnion([dia_local(timestamp)]),
                    "total_respostas": firestore.Increment(1),
                    "atualizado_em": _now_iso(),
                }
            },
            merge=True,
        )
    except Exception as exc:  # noqa: BLE001
        # O evento já foi gravado — que é o dado que importa. Um agregado
        # desatualizado é recuperável (`reconstruir_agregado`); perder a
        # resposta do aluno não é.
        logger.warning("Agregado de %s não pôde ser atualizado: %s", uid, exc)


def reconstruir_agregado(uid: str, limite: int = 5000) -> dict[str, Any]:
    """Recompõe o agregado lendo o histórico — o caminho caro, de propósito.

    Roda uma vez por aluno: na primeira leitura de quem já respondia antes do
    agregado existir, e em qualquer suspeita de divergência.
    """
    eventos = get_student_behavior_history(uid, limite)
    respondidos = {e["item_id"] for e in eventos if e.get("item_id") and e.get("status") == "respondida"}
    dias = {dia_local(e["timestamp"]) for e in eventos if e.get("timestamp")}
    agregado = {
        "item_ids_respondidos": sorted(respondidos),
        "dias_ativos": sorted(dias, reverse=True),
        "total_respostas": len(eventos),
        "atualizado_em": _now_iso(),
        "reconstruido_em": _now_iso(),
    }
    _student_doc_ref(uid).set({"agregado": agregado}, merge=True)
    return agregado


def ler_agregado(uid: str) -> dict[str, Any]:
    """Agregado do aluno em UMA leitura, reconstruindo na primeira vez."""
    snap = _student_doc_ref(uid).get()
    dados = (snap.to_dict() or {}) if snap.exists else {}
    agregado = dados.get("agregado")
    if agregado is None:
        return reconstruir_agregado(uid)
    return agregado


# ---------------------------------------------------------------------------
# Agregado do banco de treino (HAB-01..HAB-56) — mesma disciplina do agregado
# acima: nada pode custar O(eventos) por requisição (ver
# `project_aluno_disciplina_leitura_firestore`). Um contador por HAB dentro do
# MESMO documento `students/{uid}`, atualizado com `Increment` a cada
# resposta e lido em uma leitura só — é o que alimenta os balões de pontos
# fortes/fracos em `/treino`.
# ---------------------------------------------------------------------------


def increment_treino_stats(uid: str, hab_id: str, acertou: bool) -> None:
    """Idempotente por natureza (Increment nunca duplica um valor já
    somado): reprocessar o mesmo evento duas vezes soma duas respostas de
    verdade, não é um bug — cada resposta de treino é uma tentativa real,
    igual ao agregado de itens do Enem."""
    try:
        _student_doc_ref(uid).set(
            {
                "treino_agregado": {
                    hab_id: {
                        "respondidas": firestore.Increment(1),
                        "acertos": firestore.Increment(1 if acertou else 0),
                        "atualizado_em": _now_iso(),
                    }
                }
            },
            merge=True,
        )
    except Exception as exc:  # noqa: BLE001
        # O evento de behavior já foi gravado — que é o dado que importa. Um
        # agregado de treino desatualizado só atrasa o balão ficar colorido,
        # nunca perde a resposta do aluno.
        logger.warning("Agregado de treino de %s não pôde ser atualizado (%s): %s", uid, hab_id, exc)


def ler_treino_stats(uid: str) -> dict[str, dict[str, int]]:
    """`{hab_id: {respondidas, acertos}}` em uma leitura do mesmo documento
    já lido em outros lugares (`_student_doc_ref`)."""
    snap = _student_doc_ref(uid).get()
    dados = (snap.to_dict() or {}) if snap.exists else {}
    bruto = dados.get("treino_agregado") or {}
    return {
        hab_id: {"respondidas": v.get("respondidas", 0), "acertos": v.get("acertos", 0)}
        for hab_id, v in bruto.items()
        if isinstance(v, dict)
    }


# ---------------------------------------------------------------------------
# Estado de revisão espaçada (Fases 1/2/4) — mesmo documento, mesma disciplina
#
# O bloco `revisao` mora em `students/{uid}` junto de `agregado` e
# `treino_agregado`, pelo motivo de sempre: uma leitura, um documento. O que
# ele guarda é LIMITADO por construção (ver os tetos `_MAX_*` de
# `revisao_espacada`) — o risco declarado desta feature é justamente o
# documento inflar até o limite de 1 MB, e um documento estourado não degrada:
# para de aceitar escrita.
# ---------------------------------------------------------------------------


def ler_revisao(uid: str) -> dict[str, Any]:
    """O bloco de revisão em UMA leitura. `{}` quando o aluno ainda não tem."""
    snap = _student_doc_ref(uid).get()
    dados = (snap.to_dict() or {}) if snap.exists else {}
    return dados.get("revisao") or {}


def ler_estado_do_aluno(uid: str) -> dict[str, Any]:
    """`agregado` + `revisao` do aluno numa leitura SÓ.

    As duas coisas moram no mesmo documento, e a fila diária precisa das duas:
    o estado de revisão para saber o que está pendente, e
    `agregado.item_ids_respondidos` para não sugerir como transferência uma
    questão que o aluno já respondeu. Ler o documento duas vezes seria pagar
    Firestore em dobro pelo mesmo dado — o defeito que `_ler_historico`
    documenta e este módulo inteiro existe para evitar.
    """
    snap = _student_doc_ref(uid).get()
    dados = (snap.to_dict() or {}) if snap.exists else {}
    return {"agregado": dados.get("agregado") or {}, "revisao": dados.get("revisao") or {}}


def escrever_revisao(uid: str, bloco: dict[str, Any]) -> None:
    """Grava o bloco inteiro, já calculado.

    `set(merge=True)` no documento inteiro em vez de `Increment` campo a campo
    porque o bloco é o resultado de uma função pura sobre o bloco anterior:
    rotação de janela, colapso de intervalo e poda de lista não são somas, e
    tentar exprimi-las como operações atômicas espalharia a regra de
    agendamento pelo Firestore em vez de a deixar testável em um módulo só.
    """
    try:
        _student_doc_ref(uid).set({"revisao": bloco}, merge=True)
    except Exception as exc:  # noqa: BLE001
        # O evento de behavior já foi gravado — que é o dado que importa. Um
        # estado de revisão desatualizado atrasa um reteste; perder a resposta
        # do aluno, não.
        logger.warning("Estado de revisão de %s não pôde ser atualizado: %s", uid, exc)


def marcar_autorrelato(uid: str, event_id: str, autorrelato: dict[str, Any]) -> None:
    """Anexa o microdiagnóstico (Fase 3) ao evento de behavior que ele explica.

    Campo PRÓPRIO dentro do evento, nunca dentro de `resposta`: o autorrelato
    tem outro produtor (`proposta: autorrelato`) e outra epistemologia — o
    aluno pós-racionaliza, e frequentemente não sabe por que errou. Fundi-lo
    ao traço seria inventar vínculo Erro→Processo fora do catálogo (R-1) e
    determinizar causa (R-3) de uma vez só.
    """
    _behavior_collection_ref(uid).document(event_id).set({"autorrelato": autorrelato}, merge=True)


def varrer_revisoes(limite: int = 500) -> list[dict[str, Any]]:
    """`revisao` de todos os alunos — 1 leitura por ALUNO, nunca por evento.

    O bloco mora no documento `students/{uid}`, então a mesma varredura que
    `list_students_with_behavior` já faz para listar alunos traz o estado de
    revisão junto. É o que alimenta o Sapiens Lab (instrumento interno): a
    unidade de análise ali é o par (erro, processo) agregado sobre TODOS os
    alunos, e derivar isso por aluno, um `perfil()` de cada vez, custaria a
    cota diária inteira num clique — o incidente de 2026-09-04.
    """
    saida: list[dict[str, Any]] = []
    for snap in get_firestore().collection("students").limit(limite).stream():
        dados = snap.to_dict() or {}
        bloco = dados.get("revisao")
        if bloco:
            saida.append({"uid": snap.id, "revisao": bloco})
    return saida


def get_student_behavior_history(uid: str, limit: int = 1000) -> list[dict[str, Any]]:
    """Lê o histórico de eventos de behavior (schema canônico) de um aluno,
    do mais recente para o mais antigo."""
    docs = (
        _behavior_collection_ref(uid)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]


def get_behavior_events_for_items(uid: str, item_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Último evento de behavior de cada item da lista — `{item_id: evento}`.

    Substitui a varredura do histórico inteiro em `/rodada/concluir`, que lia
    até 5.000 documentos para consultar ~10. O `in` do Firestore aceita no
    máximo 30 valores por consulta, então a lista é fatiada; uma rodada tem 10
    itens, então na prática é sempre uma consulta só.

    "Último" importa porque reiniciar uma prova acrescenta um evento novo sem
    apagar o anterior: a rodada tem que refletir a tentativa mais recente.
    """
    if not item_ids:
        return {}
    encontrados: dict[str, dict[str, Any]] = {}
    for inicio in range(0, len(item_ids), 30):
        fatia = item_ids[inicio:inicio + 30]
        docs = (
            _behavior_collection_ref(uid)
            .where(filter=firestore.FieldFilter("item_id", "in", fatia))
            .stream()
        )
        for doc in docs:
            evento = doc.to_dict() or {}
            item_id = evento.get("item_id")
            if not item_id:
                continue
            anterior = encontrados.get(item_id)
            if anterior is None or (evento.get("timestamp") or "") >= (anterior.get("timestamp") or ""):
                encontrados[item_id] = evento
    return encontrados


def get_activity_dates(uid: str, limit: int = 3000) -> list[str]:
    """Datas (YYYY-MM-DD, **fuso de São Paulo**) em que o aluno respondeu ao
    menos uma questão, mais recente primeiro. Base da sequência de estudos e do
    progresso semanal; nunca inventa atividade sem evento real por trás.

    Lê o agregado (1 documento) em vez de varrer o histórico — ver
    `_atualizar_agregado`. `limit` fica na assinatura porque a reconstrução
    ainda o usa quando o agregado não existe.
    """
    dias = ler_agregado(uid).get("dias_ativos") or []
    return sorted(dias, reverse=True)[:limit]


# Teto de segurança da varredura de alunos: o custo é 1 leitura por aluno, o
# que é barato para dezenas ou centenas e deixa de ser para dezenas de milhares.
_TETO_ALUNOS_VARRIDOS = 5000


def list_students_with_behavior(limit: int = 500) -> list[dict[str, Any]]:
    """Alunos com pelo menos um evento de behavior, com contagem e último evento.

    Lê o AGREGADO de cada aluno (`students/{uid}.agregado`), não a coleção de
    eventos. Custo: 1 leitura por aluno, no lugar de 1 por EVENTO.

    Antes era `collection_group("behavior").limit(5000)`, que tinha dois
    problemas — um de custo e um de correção:

    * **Custo.** 5.000 leituras por chamada, num universo de 50.000/dia. O laço
      diário de perfil cognitivo sozinho gastava 10% da cota do dia só para
      descobrir quem tinha respondido algo novo. Com ~20 alunos, o agregado
      responde a mesma pergunta em ~20 leituras.
    * **Correção — e este era o pior.** O `limit(5000)` truncava em silêncio.
      Passando de 5.000 eventos somados na plataforma, alunos simplesmente
      sumiam desta lista: não apareciam para o admin e paravam de ter perfil
      cognitivo recalculado, sem erro nenhum em lugar algum. Era um defeito
      latente esperando o produto crescer.

    O agregado é mantido por `_atualizar_agregado` a cada resposta e
    reconstruído sob demanda por `ler_agregado`. Aluno que responde antes do
    agregado existir cai no reparo abaixo, que é caro por aluno mas raro e
    definitivo — depois dele, o aluno passa a ter agregado como todo mundo.
    """
    client = get_firestore()
    rows: list[dict[str, Any]] = []
    varridos = 0
    for snap in client.collection("students").stream():
        varridos += 1
        if varridos > _TETO_ALUNOS_VARRIDOS:
            # Truncar em SILÊNCIO foi o defeito da versão anterior (o
            # `limit(5000)` sobre eventos). Aqui o teto existe só para uma base
            # muito maior não virar uma varredura surpresa, e ele GRITA no log
            # quando é atingido — para virar tarefa de paginar de verdade, não
            # um sumiço inexplicável de alunos.
            logger.error(
                "list_students_with_behavior: base passou de %d alunos e a listagem foi "
                "truncada. Está na hora de paginar esta consulta.", _TETO_ALUNOS_VARRIDOS,
            )
            break
        dados = snap.to_dict() or {}
        agregado = dados.get("agregado")
        if agregado is None:
            # Aluno anterior ao agregado (ou com gravação perdida): reconstrói
            # uma vez. `reconstruir_agregado` persiste, então na próxima
            # chamada ele já entra pelo caminho barato.
            try:
                agregado = reconstruir_agregado(snap.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Agregado de %s não pôde ser reconstruído: %s", snap.id, exc)
                continue
        total = int(agregado.get("total_respostas") or 0)
        if total <= 0:
            continue
        rows.append({
            "student_id": snap.id,
            "nome": dados.get("nome"),
            "email": dados.get("email"),
            "count": total,
            "last_at": agregado.get("atualizado_em"),
        })
    rows.sort(key=lambda r: r["last_at"] or "", reverse=True)
    return rows[:limit]


def resumo_dos_alunos() -> dict[str, dict[str, Any]]:
    """Saldo de Sparks e volume de respostas de TODOS os alunos, por uid.

    Uma varredura de `students`, 1 leitura por aluno — a mesma ordem de
    grandeza de `list_students_with_behavior`, e pelo mesmo motivo: o painel
    de admin precisa de um número por aluno, não do histórico de ninguém (ver
    `project_aluno_disciplina_leitura_firestore`).

    **Não reconstrói agregado ausente**, de propósito. Reconstruir custa
    O(eventos) do aluno, e este é o caminho de UMA tela de listagem: um único
    carregamento poderia disparar dezenas de reconstruções em série. Quando o
    agregado não existe, `questoes_respondidas` vem `None` — que a tela mostra
    como "—". Dizer "não sei" é correto; dizer "0" para quem respondeu 300
    questões não é. Quem reconstrói é o laço diário de perfil cognitivo, que
    já chama `list_students_with_behavior`.
    """
    client = get_firestore()
    resumo: dict[str, dict[str, Any]] = {}
    varridos = 0
    for snap in client.collection("students").stream():
        varridos += 1
        if varridos > _TETO_ALUNOS_VARRIDOS:
            logger.error(
                "resumo_dos_alunos: base passou de %d alunos e a varredura foi truncada. "
                "Está na hora de paginar esta consulta.", _TETO_ALUNOS_VARRIDOS,
            )
            break
        dados = snap.to_dict() or {}
        agregado = dados.get("agregado") or None
        resumo[snap.id] = {
            "sparks_balance": dados.get("sparks_balance"),
            "questoes_respondidas": (
                int(agregado.get("total_respostas") or 0) if agregado is not None else None
            ),
            "dias_ativos": len((agregado or {}).get("dias_ativos") or []),
            "ultima_atividade": (agregado or {}).get("atualizado_em"),
            "perfil_criado_em": dados.get("created_at"),
        }
    return resumo


def resumo_de_um_aluno(uid: str) -> dict[str, Any]:
    """Tudo que o documento `students/{uid}` sabe sobre um aluno, em UMA
    leitura — para a ficha que o admin abre ao clicar num aluno.

    As listas grandes que moram no agregado (`item_ids_respondidos`,
    `dias_ativos`) voltam RESUMIDAS: contagem e os dias mais recentes. A ficha
    quer o tamanho do histórico, não o histórico — que já tem tela própria
    (`/admin/history`) e é caro de trafegar.
    """
    snap = _student_doc_ref(uid).get()
    if not snap.exists:
        return {"existe": False}
    dados = snap.to_dict() or {}
    agregado = dados.get("agregado") or {}
    treino = dados.get("treino_agregado") or {}
    respondidas = sum(int((v or {}).get("respondidas") or 0) for v in treino.values() if isinstance(v, dict))
    acertos = sum(int((v or {}).get("acertos") or 0) for v in treino.values() if isinstance(v, dict))
    revisao = dados.get("revisao") or {}
    return {
        "existe": True,
        "nome": dados.get("nome"),
        "email": dados.get("email"),
        "criado_em": dados.get("created_at"),
        "sparks_balance": dados.get("sparks_balance"),
        "questoes_respondidas": int(agregado.get("total_respostas") or 0) if agregado else None,
        "itens_distintos": len(agregado.get("item_ids_respondidos") or []),
        "dias_ativos": len(agregado.get("dias_ativos") or []),
        "ultimos_dias": sorted(agregado.get("dias_ativos") or [], reverse=True)[:14],
        "ultima_atividade": agregado.get("atualizado_em"),
        "agregado_reconstruido_em": agregado.get("reconstruido_em"),
        "treino": {
            "habilidades_tocadas": len(treino),
            "respondidas": respondidas,
            "acertos": acertos,
        },
        "revisao": {
            "processos_acompanhados": len(revisao.get("processos") or {}),
            "intervencao_ativa": bool(revisao.get("intervencao_ativa")),
            "atualizado_em": revisao.get("atualizado_em"),
        },
    }


# ======================================================================
# Sparks — recompensa por rodada do ENEM (10 questões; a última rodada do
# bloco de 45 fecha com 5). Estrutura:
#   students/{uid}.sparks_balance              -> saldo corrente (int)
#   students/{uid}/sparks_rounds/{round_key}   -> UM doc por rodada concluída,
#                                                  auditável (prova/rodada/itens)
#                                                  e a própria prova de que a
#                                                  rodada já foi paga.
#
# Separado do ganho POR QUESTÃO do banco de treino de habilidades
# (`grant_question_sparks`, mais abaixo) — são dois produtos diferentes
# (prova completa vs. treino avulso por habilidade), cada um com sua própria
# regra de recompensa, e por isso duas chaves de idempotência diferentes.
# ======================================================================

def _sparks_round_ref(uid: str, round_key: str):
    return _student_doc_ref(uid).collection("sparks_rounds").document(round_key)


def read_round(uid: str, round_key: str) -> Optional[dict[str, Any]]:
    snap = _sparks_round_ref(uid, round_key).get()
    return snap.to_dict() if snap.exists else None


def list_sparks_rounds(uid: str, limit: int = 200) -> list[dict[str, Any]]:
    """Histórico de resumos de rodada (10 questões, 5 na última do bloco) do
    aluno, mais recente primeiro — cada doc já tem `created_at`, `bloco`
    (banca/ano/prova) e `padroes_de_erro`, gravados por `grant_round_sparks`.
    """
    docs = (
        _student_doc_ref(uid)
        .collection("sparks_rounds")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]


def _conceder_sparks_atomico(
    ref, doc: dict[str, Any], uid: str, amount: int, *, registrar_saldo: bool = False,
) -> bool:
    """Cria `doc` em `ref` E soma `amount` ao saldo — as duas coisas, ou nenhuma.

    Devolve `True` quando foi ESTA chamada que concedeu, `False` quando o
    documento já existia (concessão anterior, retry do Mercado Pago, refresh
    do aluno, corrida de requisições).

    **Por que uma transação e não `create()` seguido de `update()`.** Eram duas
    operações independentes, nesta ordem: cria o documento que prova a
    concessão, depois incrementa o saldo. O processo morrendo entre as duas
    (deploy, OOM na VM de 512 MB, suspensão da máquina) deixava um estado que
    ninguém conseguia mais consertar: o documento existia, o saldo não subira,
    e a retentativa caía em `AlreadyExists` — lida como "já creditado" — sem
    nunca incrementar. Em `grant_purchase_sparks` isso era dinheiro recebido e
    Spark nunca entregue, e o laço de reconciliação marcava o pagamento como
    resolvido logo em seguida, fechando a porta para qualquer reparo.

    A janela era de milissegundos; a consequência, permanente e silenciosa. Com
    a transação, o commit é um só: ou o documento e o saldo entram juntos, ou
    não entra nada e a próxima tentativa refaz tudo do zero.

    A garantia de não duplicar continua vindo do mesmo lugar de antes —
    `create()` só vence uma vez num caminho que ainda não existe —, agora
    dentro do commit transacional. `AlreadyExists` não é erro retentável, então
    o SDK não repete a transação: ela aborta inteira, sem escrever o saldo.

    `registrar_saldo` carimba no comprovante o saldo ANTES e DEPOIS da
    concessão. Custa uma leitura a mais, DENTRO da transação (é a única forma
    de o "antes" ser o mesmo valor que o `Increment` vai somar — lido fora, um
    gasto concorrente do aluno o tornaria mentira). Por isso é opt-in e hoje só
    a compra o liga: uma compra acontece algumas vezes por aluno na vida,
    enquanto `grant_question_sparks` roda a cada questão respondida, e uma
    leitura extra ali multiplicaria a conta do Firestore pelo volume de
    respostas da plataforma inteira (ver
    `project_aluno_disciplina_leitura_firestore`).
    """
    transaction = get_firestore().transaction()

    @firestore.transactional
    def _run(transaction) -> bool:
        if registrar_saldo:
            # Toda leitura tem que vir antes de toda escrita na mesma
            # transação — daí este `get` estar acima do `create`.
            atual = _student_doc_ref(uid).get(transaction=transaction)
            antes = int((atual.to_dict() or {}).get("sparks_balance") or 0)
            doc["saldo_antes"] = antes
            doc["saldo_apos"] = antes + amount
        transaction.create(ref, doc)
        if amount:
            transaction.update(
                _student_doc_ref(uid), {"sparks_balance": firestore.Increment(amount)}
            )
        return True

    try:
        return _run(transaction)
    except gcloud_exceptions.AlreadyExists:
        return False


def grant_round_sparks(
    uid: str,
    *,
    round_key: str,
    bloco: dict[str, Any],
    rodada: int,
    item_ids: list[str],
    acertos: int,
    erros: int,
    total: int,
    percentual_acerto: float,
    padroes_de_erro: list[dict[str, Any]],
) -> dict[str, Any]:
    """Credita +1 Spark por acerto da rodada, UMA única vez, de forma atômica.

    A garantia de "nunca duplicar" não vem de uma checagem prévia no cliente:
    vem do `create()` sobre `sparks_rounds/{round_key}`, que o Firestore só
    deixa UMA chamada concorrente vencer; as demais recebem `AlreadyExists` e
    não escrevem nada. Isso cobre retomada, refresh e corrida de requisições.

    O `create` e o incremento do saldo vão no MESMO commit transacional (ver
    `_conceder_sparks_atomico`), então não existe estado intermediário em que a
    rodada conste como paga e o saldo não tenha subido.
    """
    ref = _sparks_round_ref(uid, round_key)
    round_doc = {
        "round_key": round_key,
        "student_id": uid,
        "bloco": bloco,
        "rodada": rodada,
        "item_ids": item_ids,
        "acertos": acertos,
        "erros": erros,
        "total": total,
        "percentual_acerto": percentual_acerto,
        "padroes_de_erro": padroes_de_erro,
        "sparks_ganhos": acertos,
        "created_at": _now_iso(),
    }
    if not _conceder_sparks_atomico(ref, round_doc, uid, acertos):
        existente = ref.get().to_dict() or {}
        return {"ja_concedido": True, **existente}
    return {"ja_concedido": False, **round_doc}


def _question_spark_ref(uid: str, item_id: str):
    return _student_doc_ref(uid).collection("sparks_questoes").document(item_id)


def grant_question_sparks(uid: str, item_id: str, amount: int = 1) -> dict[str, Any]:
    """Credita Sparks por uma questão CONCLUÍDA (respondida), UMA única vez —
    nunca de novo se o aluno responder a mesma questão outra vez.

    Mesmo padrão atômico de `grant_round_sparks`/`grant_purchase_sparks`:
    `create()` em `students/{uid}/sparks_questoes/{item_id}` só tem sucesso na
    primeira vez; retomada, refresh ou corrida de requisições repetidas caem em
    `AlreadyExists` e não creditam de novo. Documento e saldo entram no mesmo
    commit (ver `_conceder_sparks_atomico`).
    """
    ref = _question_spark_ref(uid, item_id)
    doc = {
        "item_id": item_id,
        "student_id": uid,
        "sparks_ganhos": amount,
        "created_at": _now_iso(),
    }
    if not _conceder_sparks_atomico(ref, doc, uid, amount):
        existente = ref.get().to_dict() or {}
        return {"ja_concedido": True, "sparks_ganhos": 0, **existente}
    return {"ja_concedido": False, **doc}


def _report_spark_ref(uid: str, report_id: str):
    return _student_doc_ref(uid).collection("sparks_reports").document(report_id)


def grant_report_sparks(uid: str, report_id: str, amount: int = 5) -> dict[str, Any]:
    """Credita Sparks por uma sugestão de correção de questão APROVADA por um
    admin, UMA única vez por `report_id` — mesmo padrão atômico de
    `grant_question_sparks`/`grant_round_sparks`/`grant_purchase_sparks`.
    """
    ref = _report_spark_ref(uid, report_id)
    doc = {
        "report_id": report_id,
        "student_id": uid,
        "sparks_ganhos": amount,
        "created_at": _now_iso(),
    }
    if not _conceder_sparks_atomico(ref, doc, uid, amount):
        existente = ref.get().to_dict() or {}
        return {"ja_concedido": True, "sparks_ganhos": 0, **existente}
    return {"ja_concedido": False, **doc}


def grant_sparks_evento(
    uid: str, *, categoria: str, chave: str, amount: int, meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Credita Sparks por um evento de engajamento, UMA única vez por
    `(categoria, chave)`.

    Uma função genérica no lugar de três quase idênticas
    (`grant_missao_sparks`, `grant_comunidade_sparks`, `grant_indicacao_sparks`)
    porque a única coisa que mudaria entre elas é o nome da subcoleção — e o
    que importa, a garantia de não pagar duas vezes, é exatamente igual nas
    três: `create()` sobre um caminho determinístico, no mesmo commit
    transacional do incremento do saldo (ver `_conceder_sparks_atomico`).

    A chave tem que ser determinística e conter tudo que distingue o evento.
    Missão diária: `"2026-09-15:responder5"` — o mesmo aluno pode cumprir a
    mesma missão amanhã, e amanhã é outro pagamento; o mesmo dia não.

    `categoria` vira o nome da subcoleção, então cada tipo de recompensa fica
    auditável em separado, do mesmo jeito que `sparks_rounds` e `sparks_reports`.
    """
    caminho = f"sparks_{categoria}"
    ref = _student_doc_ref(uid).collection(caminho).document(chave)
    doc = {
        "categoria": categoria,
        "chave": chave,
        "student_id": uid,
        "sparks_ganhos": amount,
        "meta": meta or {},
        "created_at": _now_iso(),
    }
    if not _conceder_sparks_atomico(ref, doc, uid, amount):
        existente = ref.get().to_dict() or {}
        return {"ja_concedido": True, **existente, "sparks_ganhos": 0}
    return {"ja_concedido": False, **doc}


def grant_admin_sparks(uid: str, *, amount: int, admin_email: str, motivo: str = "") -> dict[str, Any]:
    """Credita Sparks manualmente por ação de um admin (suporte, ajuste de
    saldo, teste). Ao contrário de `grant_round_sparks`/`grant_question_sparks`/
    `grant_purchase_sparks`, não existe uma chave de negócio natural para
    deduplicar aqui — é uma decisão humana avulsa, não um evento que se repete
    sozinho por retry/refresh, então não há `create()` idempotente: dois
    cliques do admin creditam duas vezes, do mesmo jeito que dois PIX
    creditam duas vezes. Fica registrado em `sparks_admin_grants` para
    auditoria (quem, quanto, por quê, quando).
    """
    doc = {
        "amount": amount,
        "admin_email": admin_email,
        "motivo": motivo,
        "created_at": _now_iso(),
    }
    ref = _student_doc_ref(uid).collection("sparks_admin_grants").document()
    ref.set(doc)
    _student_doc_ref(uid).update({"sparks_balance": firestore.Increment(amount)})
    return {"grant_id": ref.id, **doc}


def count_answers_for_item(uid: str, item_id: str) -> int:
    """Quantas vezes este aluno já respondeu efetivamente este item.

    Base de `numero_tentativas`: reiniciar uma prova nunca apaga nem
    sobrescreve o histórico, só acrescenta eventos — então "esta resposta é a
    enésima tentativa" só pode sair de contar o que já está gravado, nunca de
    um contador à parte no cliente (que zeraria a cada sessão nova).

    Só conta `status == "respondida"`: um evento abandonado não é resposta.
    """
    query = (
        _behavior_collection_ref(uid)
        .where(filter=firestore.FieldFilter("item_id", "==", item_id))
        .where(filter=firestore.FieldFilter("status", "==", "respondida"))
    )
    return sum(1 for _ in query.stream())


def _purchase_ref(uid: str, payment_id: str):
    """`students/{uid}/sparks_purchases/{payment_id}` — o id do pagamento no
    Mercado Pago é a própria chave, que é o que torna o crédito idempotente
    sem nenhuma checagem prévia (ver `grant_purchase_sparks`)."""
    seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", str(payment_id))[:400] or "pagamento"
    return _student_doc_ref(uid).collection("sparks_purchases").document(seguro)


def grant_purchase_sparks(
    uid: str,
    *,
    payment_id: str,
    package_id: str,
    sparks_amount: int,
    price_cents: int,
    currency: str,
    source: str,
) -> dict[str, Any]:
    """Credita os Sparks de um pagamento aprovado, UMA única vez.

    Mesma garantia de `grant_round_sparks`, e pelo mesmo motivo: o Mercado
    Pago reenvia notificações (retry por timeout, entregas duplicadas, e a
    mesma cobrança notificada por eventos diferentes). O documento tem o
    `mp_payment_id` como caminho, então `create()` só pode vencer uma vez —
    quem chegar depois recebe `AlreadyExists` e não incrementa saldo nenhum.

    O crédito é transacional (`_conceder_sparks_atomico`): o comprovante da
    compra e o incremento do saldo entram juntos ou não entram. Isto NÃO é
    detalhe — era aqui que uma morte de processo entre as duas escritas
    deixava o aluno tendo pago sem receber, de forma irreparável.

    Chamado SÓ pelo webhook, nunca na resposta síncrona do checkout: até o
    Mercado Pago confirmar, não existe dinheiro e não deve existir Spark.
    """
    ref = _purchase_ref(uid, payment_id)
    doc = {
        "payment_id": str(payment_id),
        "student_id": uid,
        "package_id": package_id,
        "sparks_amount": sparks_amount,
        "price_cents": price_cents,
        "currency": currency,
        "source": source,
        "created_at": _now_iso(),
    }
    # `registrar_saldo=True` só aqui: o comprovante de COMPRA é o único que
    # precisa responder "quanto o aluno tinha antes de pagar" no painel de
    # transações. Ver o custo dessa leitura extra em `_conceder_sparks_atomico`.
    if not _conceder_sparks_atomico(ref, doc, uid, sparks_amount, registrar_saldo=True):
        existente = ref.get().to_dict() or {}
        return {"ja_creditado": True, **existente}
    return {"ja_creditado": False, **doc}


def list_sparks_purchases(uid: str, limit: int = 100) -> list[dict[str, Any]]:
    """Créditos de compra já aplicados ao saldo do aluno, mais recente
    primeiro — a visão do Firestore (o que de fato virou saldo), separada da
    auditoria de cobrança que vive em `sparks_payments` no Mongo."""
    docs = (
        _student_doc_ref(uid)
        .collection("sparks_purchases")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]


# ---------------------------------------------------------------------------
# Direitos permanentes — o que o pacote de R$119,90 compra além de saldo
# ---------------------------------------------------------------------------
#
# Cada direito é uma flag booleana no documento do aluno
# (`students/{uid}.mentis_ilimitada`, `...comunidade_vip`), e NÃO uma
# assinatura com validade: o que foi vendido é "para sempre", e qualquer data
# de expiração aqui seria uma promessa diferente da que a loja faz. Concedidos
# só pelo webhook de pagamento aprovado, no mesmo lugar em que os Sparks são
# creditados. A lista do que pode existir mora em `sparks_store.DIREITOS`.


def conceder_direitos(uid: str, direitos: tuple[str, ...] | list[str]) -> None:
    """Liga os direitos numa escrita só.

    Idempotente por natureza (escrever `True` duas vezes não muda nada), então
    o reenvio de webhook do Mercado Pago não precisa de guarda extra.
    """
    if not direitos:
        return
    campos: dict[str, Any] = {}
    for d in direitos:
        campos[d] = True
        campos[f"{d}_em"] = _now_iso()
    _student_doc_ref(uid).set(campos, merge=True)


def ler_direitos(uid: str) -> dict[str, bool]:
    """Todos os direitos do aluno em UMA leitura.

    Uma leitura e não uma por direito: eles aparecem juntos na mesma tela, e
    o Firestore deste projeto já estourou cota uma vez por leitura acumulada
    em caminho quente (incidente de 2026-09-04).

    Falha de leitura devolve tudo `False`: na dúvida, cobra-se o Spark e o
    aluno reclama — o inverso (liberar de graça por instabilidade) daria de
    presente o produto mais caro do catálogo para a base inteira durante o
    incidente.
    """
    import sparks_store

    try:
        dados = _student_doc_ref(uid).get().to_dict() or {}
    except Exception:  # noqa: BLE001
        logger.warning("Não foi possível ler os direitos de %s.", uid)
        dados = {}
    return {d: bool(dados.get(d)) for d in sparks_store.DIREITOS}


def tem_mentis_ilimitada(uid: str) -> bool:
    return ler_direitos(uid).get("mentis_ilimitada", False)


def tem_comunidade_vip(uid: str) -> bool:
    return ler_direitos(uid).get("comunidade_vip", False)


class InsufficientSparksError(Exception):
    """Saldo de Sparks do aluno é menor que o custo da ação."""

    def __init__(self, balance: int, needed: int):
        self.balance = balance
        self.needed = needed
        super().__init__(f"saldo insuficiente: {balance} < {needed}")


def deduct_sparks(uid: str, amount: int) -> int:
    """Debita `amount` Sparks do saldo do aluno, atomicamente (transação
    Firestore) para evitar corrida entre requisições concorrentes. Lança
    `InsufficientSparksError` se o saldo não cobrir o custo. Retorna o novo
    saldo.
    """
    ref = _student_doc_ref(uid)
    transaction = get_firestore().transaction()

    @firestore.transactional
    def _run(transaction):
        snap = ref.get(transaction=transaction)
        balance = (snap.to_dict() or {}).get("sparks_balance", SPARKS_INITIAL_BALANCE)
        if balance < amount:
            raise InsufficientSparksError(balance, amount)
        new_balance = balance - amount
        transaction.update(ref, {"sparks_balance": new_balance})
        return new_balance

    return _run(transaction)


def refund_sparks(uid: str, amount: int) -> int:
    """Devolve `amount` Sparks ao saldo — compensação de um débito cujo
    trabalho pago falhou depois de cobrado.

    Existe porque `deduct_sparks` acontece ANTES do trabalho caro (é o débito
    que autoriza gastar o recurso), e uma falha no meio deixaria o aluno sem
    Sparks e sem entrega. Não é uma operação de produto: nenhuma rota expõe
    isso ao cliente, só o tratamento de erro do servidor a chama.
    """
    if amount <= 0:
        return read_sparks_balance(uid)
    _student_doc_ref(uid).update({"sparks_balance": firestore.Increment(amount)})
    return read_sparks_balance(uid)


# ======================================================================
# Mapa de Habilidades — camada cosmética de gamificação (ver
# cosmetic_skills_map.py). Persistido separado de qualquer dado real da
# ontologia: students/{uid}.skills_map = {hexagon, updated_at}.
# ======================================================================

def read_skills_map(uid: str) -> Optional[dict[str, Any]]:
    snap = _student_doc_ref(uid).get()
    return (snap.to_dict() or {}).get("skills_map")


def write_skills_map(uid: str, hexagon: list[dict[str, Any]], feedback: dict[str, Any]) -> str:
    updated_at = _now_iso()
    _student_doc_ref(uid).set(
        {"skills_map": {"hexagon": hexagon, "feedback": feedback, "updated_at": updated_at}},
        merge=True,
    )
    return updated_at


# ======================================================================
# Perfil cognitivo — snapshot real (não cosmético) do desempenho do aluno,
# um documento por período (semana ISO, ex. "2026-W36"), nunca sobrescrevendo
# o passado: students/{uid}/perfil_cognitivo/{periodo}. `periodo` cresce
# lexicograficamente igual a cronologicamente (ano + semana com 2 dígitos),
# então "mais recente" é sempre "maior string" — dá pra ordenar sem parsear.
# Ver `perfil_cognitivo_service.py` para a lógica de quando gerar cada um.
# ======================================================================

def _perfil_collection_ref(uid: str):
    return _student_doc_ref(uid).collection("perfil_cognitivo")


def write_perfil_cognitivo(uid: str, periodo: str, doc: dict[str, Any]) -> None:
    _perfil_collection_ref(uid).document(periodo).set(doc)


def read_ultimo_perfil(uid: str) -> Optional[dict[str, Any]]:
    docs = (
        _perfil_collection_ref(uid)
        .order_by("periodo", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    for snap in docs:
        return snap.to_dict()
    return None


def list_perfil_historico(uid: str, limit: int = 52) -> list[dict[str, Any]]:
    """Até `limit` snapshots (padrão: ~1 ano de semanas), mais recente primeiro."""
    docs = (
        _perfil_collection_ref(uid)
        .order_by("periodo", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [snap.to_dict() for snap in docs]
