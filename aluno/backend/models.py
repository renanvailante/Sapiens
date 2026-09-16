"""Sapiens data models — Answer-Key-only schema (v2).

Exams no longer store questions or alternatives. Each exam holds official
answer keys in English and/or Spanish, keyed by question number.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import re
import unicodedata
import uuid

from pydantic import BaseModel, Field, EmailStr


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug_nome(nome: str) -> str:
    """Nome -> ascii minúsculo, só [a-z0-9_], sem acento. Vazio vira 'aluno'."""
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", sem_acento).strip("_").lower()
    return slug[:24] or "aluno"


def generate_user_id(nome: str) -> str:
    """`user_id` legível: nome do aluno na frente, poucos dígitos atrás.

    Admin/professor identificam o aluno lendo o próprio id (`renan_vailante_a1b2`),
    sem precisar de um segundo campo — o sufixo hex existe só para nunca colidir
    entre dois alunos de mesmo nome; `auth.py` ainda checa unicidade antes de
    gravar, porque hex[:4] tem espaço de colisão pequeno o bastante para não
    confiar só nele.
    """
    return f"{_slug_nome(nome)}_{uuid.uuid4().hex[:4]}"


# ---------- Users ----------

class User(BaseModel):
    # Fallback só para construções que não passam `name` explicitamente (ex.:
    # deserializar um doc já existente do Mongo, que já tem user_id salvo).
    # Criação de conta nova SEMPRE passa `user_id=generate_user_id(nome)`
    # explícito em `auth.py` — nunca cai neste default.
    user_id: str = Field(default_factory=lambda: f"user_{uuid.uuid4().hex[:12]}")
    email: EmailStr
    name: str
    picture: str | None = None
    provider: str = "email"
    password_hash: str | None = None
    is_admin: bool = False
    # Prova de posse do e-mail: só o login com Google ou a redefinição de senha
    # por link a concedem. Sem ela, uma senha criada por terceiro é invalidada
    # no primeiro login Google da dona real (ver `auth.google_sign_in`).
    email_verificado: bool = False
    # Código de promoção efetivamente APLICADO no cadastro (já normalizado em
    # maiúsculas), e quantos Sparks ele deu. `None` significa duas coisas
    # diferentes que a tela distingue pela data da conta: cadastro sem código,
    # ou conta anterior a 2026-09-15, quando o vínculo aluno↔código passou a
    # ser gravado. Antes disso só existia o contador global `promo_codes.usos`,
    # que diz QUANTOS usaram e nunca QUEM.
    promo_code: str | None = None
    promo_sparks: int | None = None
    # WhatsApp do aluno — pedido no cadastro (2026-09-15) porque é o único
    # canal em que a equipe realmente alcança um estudante: e-mail de menor de
    # idade não é lido, e o link da aula ao vivo de quinta precisa chegar a
    # quem pagou por ele. Dois campos de propósito: `whatsapp` é o que a
    # pessoa digitou (ela reconhece) e `whatsapp_e164` é o número discável,
    # que é o que o painel do admin usa para abrir a conversa. Ver
    # `whatsapp.py`. `None` nas contas anteriores a esta data e em quem entrou
    # pelo Google sem informar — a tela pede depois, não inventa número.
    whatsapp: str | None = None
    whatsapp_e164: str | None = None
    created_at: str = Field(default_factory=_now_iso)


class UserSession(BaseModel):
    session_id: str = Field(default_factory=_uuid)
    user_id: str
    session_token: str
    expires_at: str
    created_at: str = Field(default_factory=_now_iso)


# ---------- ENEM Answer-Key model ----------

AREA_LABELS = {
    "LC-Idioma": "Língua estrangeira",
    "LC": "Linguagens e Códigos",
    "CH": "Ciências Humanas",
    "CN": "Ciências da Natureza",
    "MT": "Matemática",
}


def area_for(day: int, number: int) -> str:
    """Map (day, question number) → area code using the standard ENEM layout.

    Day 1: 1-5 language, 6-45 Portuguese/Arts/PE, 46-90 CH.
    Day 2: 91-135 CN, 136-180 MT (or 1-45/46-90 if paste re-numbered from 1).
    """
    n = int(number)
    if day == 1:
        if 1 <= n <= 5:
            return "LC-Idioma"
        if 6 <= n <= 45:
            return "LC"
        return "CH"
    # day 2
    if 91 <= n <= 135:
        return "CN"
    if 136 <= n <= 180:
        return "MT"
    # re-numbered from 1
    if 1 <= n <= 45:
        return "CN"
    return "MT"


class AnswerKeyItem(BaseModel):
    number: int
    letter: str  # A-E, "*" means annulled / no valid answer


class Exam(BaseModel):
    exam_id: str = Field(default_factory=_uuid)
    provider: str = "ENEM"
    year: int
    day: int  # 1 or 2
    color: str  # Azul, Amarela, Branca, Cinza, Rosa, ...
    title: str
    total_questions: int
    has_english: bool = False
    has_spanish: bool = False
    created_at: str = Field(default_factory=_now_iso)


class AnswerKey(BaseModel):
    key_id: str = Field(default_factory=_uuid)
    exam_id: str
    language: str  # "english" | "spanish"
    answers: list[AnswerKeyItem]
    created_at: str = Field(default_factory=_now_iso)


# ---------- User answers & analysis ----------

class UserAnswer(BaseModel):
    number: int
    letter: str  # A-E or "" if blank


class Analysis(BaseModel):
    analysis_id: str = Field(default_factory=_uuid)
    user_id: str
    exam_id: str
    exam_label: str
    label: str | None = None  # user-customisable name
    language: str
    answers: list[UserAnswer]
    score: int = 0
    total: int = 0
    percent: float = 0.0
    by_area: dict[str, dict[str, int]] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)  # [{number, area, chosen, correct}]
    diagnostic_headline: str = ""
    diagnostic_body: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    cognitive_profile: dict[str, float] = Field(default_factory=dict)
    study_plan: list[dict[str, Any]] = Field(default_factory=list)
    learning_map: dict[str, Any] = Field(default_factory=dict)
    deleted: bool = False
    deleted_at: str | None = None
    created_at: str = Field(default_factory=_now_iso)


# ---------- Request / Response schemas ----------

# Limites de tamanho: sem eles o mínimo de 6 caracteres da senha existia só
# como atributo HTML do input — uma requisição direta criava conta com senha
# vazia — e os campos de texto livre aceitavam qualquer volume.
class SignupRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=8, max_length=200)
    # WhatsApp: OBRIGATÓRIO no cadastro por e-mail. É o canal de contato do
    # produto (link da aula ao vivo, aviso de turma, suporte) e pedi-lo depois
    # significa não ter o número de quem mais precisa dele. O formato é
    # validado em `whatsapp.normalizar`, não aqui — o `min_length` abaixo só
    # impede o campo vazio; a mensagem que o aluno lê vem de lá.
    whatsapp: str = Field(..., min_length=8, max_length=30)
    # Opcional: código de promoção que troca o bônus padrão de Sparks do
    # cadastro pelo valor programado no código (ver `promo_codes_routes.py`).
    # Um código inválido/expirado nunca barra a criação da conta — só cai
    # no bônus padrão, como se não tivesse sido informado.
    promo_code: str | None = Field(default=None, max_length=40)


class LoginRequest(BaseModel):
    email: EmailStr
    # Sem `min_length` aqui de propósito: no login, uma senha curta é
    # credencial errada (401), não erro de validação (422) — 422 revelaria a
    # regra de senha para quem só está sondando.
    password: str = Field(..., max_length=200)


class SubmitExamRequest(BaseModel):
    exam_id: str
    language: str  # "english" | "spanish"
    answers: list[UserAnswer]


class VisionOCRRequest(BaseModel):
    exam_id: str
    image_base64: str


class PasteAnswerKeyRequest(BaseModel):
    provider: str = "ENEM"
    year: int
    day: int  # 1 or 2
    color: str
    raw_text: str  # pasted content from INEP


# ---------- Lista de espera da mentoria ----------
#
# Era "aulas particulares" até 2026-09-15. Ver o docstring de
# `mentoria_routes.py`: o produto deixou de ser aula avulsa com vários
# professores e virou a fila de espera de UMA mentoria — a do 1º colocado de
# Medicina da USP.
#
# Os VALORES de `status` e o prefixo `aula_` de `request_id` continuam os
# mesmos porque estão gravados nos registros existentes. O rótulo que o admin
# lê ("na fila", "conversando", "virou mentoria") mora no frontend.

MENTORIA_AREAS = [
    "Matemática",
    "Ciências da Natureza",
    "Linguagens",
    "Ciências Humanas",
    "Redação",
]

MENTORIA_STATUS = ["pendente", "em_andamento", "concluida", "cancelada"]


class MentoriaEspera(BaseModel):
    request_id: str = Field(default_factory=lambda: f"aula_{uuid.uuid4().hex[:12]}")
    user_id: str
    nome_completo: str
    whatsapp: str
    areas: list[str]
    descricao: str = ""
    status: str = "pendente"
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


class CreateMentoriaEsperaRequest(BaseModel):
    nome_completo: str = Field(..., min_length=1, max_length=200)
    whatsapp: str = Field(..., min_length=8, max_length=30)
    # Sem `min_length`: a rota já recusa lista vazia com uma mensagem que o
    # aluno entende ("Selecione ao menos uma área"); o 422 do Pydantic
    # chegaria antes e seria pior de ler.
    areas: list[str] = Field(..., max_length=10)
    descricao: str = Field(default="", max_length=2_000)


class UpdateMentoriaStatusRequest(BaseModel):
    status: str


# ---------- Códigos promocionais ----------
#
# Um código é opcional no cadastro (e-mail/senha ou Google) e troca o bônus
# padrão de Sparks (`firestore_service.SPARKS_INITIAL_BALANCE`) pela
# quantidade programada aqui pelo admin. O catálogo vive no Mongo — é
# configuração de produto, não estado do aluno (que vive só no Firestore).

class PromoCode(BaseModel):
    code: str
    sparks_amount: int = Field(..., ge=1, le=100_000)
    active: bool = True
    usos: int = 0
    created_at: str = Field(default_factory=_now_iso)


class CreatePromoCodeRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=40)
    sparks_amount: int = Field(..., ge=1, le=100_000)


class UpdatePromoCodeRequest(BaseModel):
    sparks_amount: int | None = Field(default=None, ge=1, le=100_000)
    active: bool | None = None


# ---------- Redação (corretor ENEM) ----------
#
# `Redacao` é o que o aluno enviou; `AvaliacaoRedacao` é o resultado da
# correção — separados de propósito: reprocessar uma redação com um canon mais
# novo gera uma avaliação nova sem tocar no texto original, e o histórico
# mostra a evolução sem reescrever o passado.

REDACAO_TEXTO_MAX = 20_000  # ~4x uma redação Enem de 30 linhas; corta abuso sem cortar aluno.


class RedacaoSubmitRequest(BaseModel):
    texto: str = Field(..., max_length=REDACAO_TEXTO_MAX)
    titulo: str | None = Field(default=None, max_length=300)
    tema_frase: str | None = Field(default=None, max_length=1_000)
    tema_elementos_obrigatorios: list[str] = Field(default_factory=list, max_length=20)
    linhas_manuscritas: int | None = Field(default=None, ge=0, le=100)
    textos_motivadores: list[str] = Field(default_factory=list, max_length=10)


class Redacao(BaseModel):
    redacao_id: str = Field(default_factory=lambda: f"red_{uuid.uuid4().hex[:12]}")
    user_id: str
    texto: str
    titulo: str | None = None
    tema_frase: str | None = None
    tema_elementos_obrigatorios: list[str] = Field(default_factory=list)
    linhas_manuscritas: int | None = None
    textos_motivadores: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now_iso)


class AvaliacaoRedacao(BaseModel):
    """Espelha exatamente o dicionário de `redacao.pontuacao.montar_resultado`
    (mais os campos de vínculo). Campos extras do corretor são preservados —
    o canon evolui e não vale a pena perder informação numa validação
    estrita enquanto o formato ainda está se firmando."""

    model_config = {"extra": "allow"}

    avaliacao_id: str = Field(default_factory=lambda: f"aval_{uuid.uuid4().hex[:12]}")
    redacao_id: str
    user_id: str
    estado_geral: str
    nota_total: int
    competencias: list[dict[str, Any]] = Field(default_factory=list)
    gatilhos_disparados: list[dict[str, Any]] = Field(default_factory=list)
    tangenciamento_detectado: bool | None = None
    necessita_revisao_humana: bool = False
    itens_para_revisao: list[str] = Field(default_factory=list)
    itens_escalonados_llm: list[str] = Field(default_factory=list)
    canon_versao: str | None = None
    created_at: str = Field(default_factory=_now_iso)
