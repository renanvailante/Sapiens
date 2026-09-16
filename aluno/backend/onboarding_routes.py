"""O que o aluno declara sobre si no primeiro acesso — e o que o produto faz
com isso.

Três perguntas, feitas uma vez, pela Mentis:

  1. **Dificuldade declarada** por área (0 a 10), nas cinco frentes que o
     aluno reconhece: Matemática, Natureza, Linguagens, Humanas e Redação.
  2. **Objetivo** em uma frase e **quanto tempo por dia** ele quer estudar.
  3. **Meta no ENEM 2026**: básico (120-140 acertos), médio (140-160) ou
     avançado (160-180).

**Por que isto não é mais um formulário morto.** Cada resposta tem um
consumidor real, e nenhuma delas inventa medida:

  * o tempo por dia vira a janela de estudo do Cronograma na hora
    (`cronograma.normalizar_preferencias`), então a primeira semana montada
    já cabe na vida do aluno;
  * a dificuldade declarada entra em `prioridade_enem.ranking` **apenas**
    onde ainda não há medida nenhuma — assim que o aluno responde questões,
    a medida real toma o lugar do que ele achava. Opinião nunca sobrescreve
    contagem;
  * a meta vira o número de acertos que a interface persegue, e o dossiê da
    Mentis passa a saber para onde ele está remando.

**Mongo e não Firestore**, pelo mesmo motivo do Cronograma e das sessões da
Mentis: o Firestore é o banco com cota diária para estourar (incidente de
2026-09-04). Um documento por aluno, `_id = user_id`, toda leitura é um
`find_one` por chave primária.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

import cronograma as cg
import firestore_service as fs
from auth import require_user
from models import User

logger = logging.getLogger("sapiens.onboarding")

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_db = None


def set_db(db):
    global _db
    _db = db


# ---------------------------------------------------------------------------
# Vocabulário
# ---------------------------------------------------------------------------

# As cinco áreas do slider. São as que o ALUNO reconhece — não as oito frentes
# de `prioridade_enem.DISCIPLINAS`. A tradução de uma para a outra está em
# `FRENTES_POR_AREA`, e é de mão única: a área declarada informa as frentes,
# nunca o contrário.
AREAS = ("matematica", "natureza", "linguagens", "humanas", "redacao")

AREA_LABEL = {
    "matematica": "Matemática",
    "natureza": "Natureza",
    "linguagens": "Linguagens",
    "humanas": "Humanas",
    "redacao": "Redação",
}

FRENTES_POR_AREA: dict[str, tuple[str, ...]] = {
    "matematica": ("matematica",),
    "natureza": ("biologia", "quimica", "fisica", "natureza"),
    "linguagens": ("linguagens",),
    "humanas": ("humanas",),
    "redacao": ("redacao",),
}

# Quanto tempo por dia, em minutos — os seis degraus da tela. Cada um vira uma
# janela de estudo concreta no Cronograma: quantos blocos por dia e de que
# tamanho. O de 10 minutos vira um bloco de 20 porque 20 é o mínimo que o
# motor aceita (`cronograma._BLOCO_MIN`) — abaixo disso um bloco de estudo não
# cabe numa questão inteira.
TEMPOS_MINUTOS = (10, 30, 60, 120, 240, 480)

_JANELA_POR_TEMPO: dict[int, dict[str, int]] = {
    10: {"bloco_minutos": 20, "blocos_por_dia": 1, "intervalo_minutos": 10},
    30: {"bloco_minutos": 30, "blocos_por_dia": 1, "intervalo_minutos": 10},
    60: {"bloco_minutos": 30, "blocos_por_dia": 2, "intervalo_minutos": 10},
    120: {"bloco_minutos": 40, "blocos_por_dia": 3, "intervalo_minutos": 10},
    240: {"bloco_minutos": 60, "blocos_por_dia": 4, "intervalo_minutos": 15},
    480: {"bloco_minutos": 60, "blocos_por_dia": 8, "intervalo_minutos": 15},
}

# A meta do aluno no ENEM 2026, em ACERTOS (as 180 questões objetivas). Faixas
# fechadas de propósito: um campo livre aqui produziria "quero 179" e uma
# interface que finge acreditar. Os rótulos são os que a tela mostra.
METAS: dict[str, dict[str, Any]] = {
    "basico": {"nivel": "basico", "rotulo": "Básico", "acertos_min": 120, "acertos_max": 140},
    "medio": {"nivel": "medio", "rotulo": "Médio", "acertos_min": 140, "acertos_max": 160},
    "avancado": {"nivel": "avancado", "rotulo": "Avançado", "acertos_min": 160, "acertos_max": 180},
}

_OBJETIVO_MAX = 180


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def _vazio(uid: str) -> dict[str, Any]:
    return {
        "_id": uid,
        "student_id": uid,
        "concluido": False,
        "video_visto": False,
        "dificuldades": {},
        "objetivo": None,
        "minutos_por_dia": None,
        "meta": None,
    }


async def _ler_doc(uid: str) -> dict[str, Any]:
    if _db is None:
        return _vazio(uid)
    try:
        doc = await _db.onboarding_perfil.find_one({"_id": uid})
    except Exception:  # noqa: BLE001
        logger.exception("onboarding: leitura falhou para %s", uid)
        return _vazio(uid)
    return doc or _vazio(uid)


async def _gravar(uid: str, campos: dict[str, Any]) -> None:
    await _db.onboarding_perfil.update_one(
        {"_id": uid},
        {"$set": {**campos, "student_id": uid, "atualizado_em": _agora_iso()}},
        upsert=True,
    )


def _serializar(doc: dict[str, Any]) -> dict[str, Any]:
    """A resposta da API. Sempre com as cinco áreas presentes (mesmo que nulas)
    e a meta já expandida em acertos — a tela nunca precisa conhecer a tabela
    de faixas para escrever "140 a 160 acertos"."""
    dificuldades = doc.get("dificuldades") or {}
    meta = METAS.get((doc.get("meta") or {}).get("nivel") if isinstance(doc.get("meta"), dict) else doc.get("meta"))
    return {
        "concluido": bool(doc.get("concluido")),
        "video_visto": bool(doc.get("video_visto")),
        "dificuldades": {a: dificuldades.get(a) for a in AREAS},
        "objetivo": doc.get("objetivo"),
        "minutos_por_dia": doc.get("minutos_por_dia"),
        "meta": dict(meta) if meta else None,
        "atualizado_em": doc.get("atualizado_em"),
        # Servido junto para a tela não repetir a tabela de opções em JS — o
        # dia em que um degrau mudar, muda num lugar só.
        "opcoes": {
            "areas": [{"chave": a, "rotulo": AREA_LABEL[a]} for a in AREAS],
            "tempos": list(TEMPOS_MINUTOS),
            "metas": [dict(m) for m in METAS.values()],
        },
    }


# ---------------------------------------------------------------------------
# Leitura para o resto do backend
# ---------------------------------------------------------------------------

async def dificuldade_por_frente(uid: str) -> dict[str, int]:
    """`{chave de frente: 0..10}` — o que o aluno declarou, traduzido para o
    vocabulário de `prioridade_enem`.

    Nunca levanta: sem onboarding (ou com o Mongo fora), devolve `{}` e o
    ranking segue exatamente como era antes desta feature existir.
    """
    doc = await _ler_doc(uid)
    declarado = doc.get("dificuldades") or {}
    saida: dict[str, int] = {}
    for area, valor in declarado.items():
        if not isinstance(valor, int) or area not in FRENTES_POR_AREA:
            continue
        for frente in FRENTES_POR_AREA[area]:
            saida[frente] = valor
    return saida


async def resumo_para_modelo(uid: str) -> Optional[str]:
    """Uma linha para entrar no dossiê da Mentis, ou None quando não há nada
    declarado. Curta de propósito: vai junto de TODA abertura de sessão."""
    doc = await _ler_doc(uid)
    if not doc.get("concluido"):
        return None
    partes: list[str] = []
    if doc.get("objetivo"):
        partes.append(f'objetivo declarado: "{doc["objetivo"]}"')
    if doc.get("minutos_por_dia"):
        partes.append(f"quer estudar cerca de {doc['minutos_por_dia']} min/dia")
    meta = METAS.get((doc.get("meta") or {}).get("nivel")) if isinstance(doc.get("meta"), dict) else None
    if meta:
        partes.append(f"meta no ENEM 2026: {meta['acertos_min']}-{meta['acertos_max']} acertos ({meta['rotulo']})")
    dificuldades = doc.get("dificuldades") or {}
    if dificuldades:
        piores = sorted(
            ((a, v) for a, v in dificuldades.items() if isinstance(v, int)),
            key=lambda t: -t[1],
        )[:2]
        if piores:
            partes.append(
                "onde ele MESMO diz ter mais dificuldade (0-10): "
                + ", ".join(f"{AREA_LABEL.get(a, a)} {v}" for a, v in piores)
            )
    if not partes:
        return None
    return "O QUE O ALUNO DECLAROU NO PRIMEIRO ACESSO (opinião dele, não medida): " + "; ".join(partes) + "."


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

class DificuldadesPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    matematica: Optional[int] = Field(default=None, ge=0, le=10)
    natureza: Optional[int] = Field(default=None, ge=0, le=10)
    linguagens: Optional[int] = Field(default=None, ge=0, le=10)
    humanas: Optional[int] = Field(default=None, ge=0, le=10)
    redacao: Optional[int] = Field(default=None, ge=0, le=10)


class OnboardingPayload(BaseModel):
    """Salvamento parcial: a tela grava a cada etapa, e fechar o navegador no
    meio não apaga o que já foi respondido."""
    model_config = ConfigDict(extra="forbid")
    video_visto: Optional[bool] = None
    dificuldades: Optional[DificuldadesPayload] = None
    objetivo: Optional[str] = Field(default=None, max_length=_OBJETIVO_MAX)
    minutos_por_dia: Optional[int] = None
    meta: Optional[str] = None
    concluido: Optional[bool] = None


@router.get("")
async def ler_onboarding(user: User = Depends(require_user)):
    return _serializar(await _ler_doc(user.user_id))


@router.put("")
async def salvar_onboarding(payload: OnboardingPayload, user: User = Depends(require_user)):
    doc = await _ler_doc(user.user_id)
    campos: dict[str, Any] = {}

    if payload.video_visto is not None:
        campos["video_visto"] = bool(payload.video_visto)

    if payload.dificuldades is not None:
        novas = payload.dificuldades.model_dump(exclude_none=True)
        campos["dificuldades"] = {**(doc.get("dificuldades") or {}), **novas}

    if payload.objetivo is not None:
        texto = payload.objetivo.strip()
        campos["objetivo"] = texto or None

    if payload.minutos_por_dia is not None:
        if payload.minutos_por_dia not in TEMPOS_MINUTOS:
            raise HTTPException(
                status_code=422,
                detail=f"Tempo inválido. Escolha um de: {', '.join(str(t) for t in TEMPOS_MINUTOS)} minutos.",
            )
        campos["minutos_por_dia"] = payload.minutos_por_dia

    if payload.meta is not None:
        if payload.meta not in METAS:
            raise HTTPException(status_code=422, detail="Meta inválida.")
        campos["meta"] = {"nivel": payload.meta}

    if payload.concluido is not None:
        campos["concluido"] = bool(payload.concluido)

    if campos:
        await _gravar(user.user_id, campos)

    # Efeitos colaterais depois da gravação, nunca antes: se um deles falhar,
    # o que o aluno respondeu já está salvo. Nenhum é essencial à resposta.
    if "minutos_por_dia" in campos:
        await _aplicar_tempo_no_cronograma(user.user_id, campos["minutos_por_dia"])
    if campos.get("concluido"):
        _marcar_onboarded(user.user_id)

    return _serializar({**doc, **campos})


async def _aplicar_tempo_no_cronograma(uid: str, minutos: int) -> None:
    """O tempo declarado vira a janela de estudo da semana.

    Escreve no MESMO documento (`cronogramas/{uid}`) que a tela de Cronograma
    já usa — não existe uma segunda noção de "quanto tempo o aluno tem". Se o
    aluno depois ajustar a janela na tela de Cronograma, é aquela que vale:
    isto aqui só dá o ponto de partida.
    """
    janela = _JANELA_POR_TEMPO.get(minutos)
    if janela is None or _db is None:
        return
    try:
        doc = await _db.cronogramas.find_one({"_id": uid}) or {}
        prefs = cg.normalizar_preferencias({**(doc.get("preferencias") or {}), **janela})
        await _db.cronogramas.update_one(
            {"_id": uid},
            {"$set": {"preferencias": prefs, "student_id": uid, "atualizado_em": _agora_iso()}},
            upsert=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("onboarding: não foi possível aplicar o tempo no cronograma de %s", uid)


def _marcar_onboarded(uid: str) -> None:
    """`flags.onboarded` no Firestore continua sendo a chave que decide se o
    guia de boas-vindas aparece — quem terminou o onboarding não é mais
    perguntado. Falha em silêncio: no pior caso o aluno vê o guia de novo."""
    try:
        fs.write_student_behavior(uid, {"flags": {"onboarded": True}})
    except Exception:  # noqa: BLE001
        logger.exception("onboarding: não foi possível marcar onboarded para %s", uid)
