"""Ingestão manual de item anotado — contrato **Schema Sapiens 2.2**.

Antes de 2026-08-21 este módulo definia um contrato próprio ("Formato C"),
independente do pipeline e de `pipeline/docs/`. Ele foi substituído pelo
contrato canônico. Três divergências não eram cosméticas:

* ``DistratorAnalise.error_type_id: int`` — inteiro. Os tipos de erro do White
  Paper 1.0 são numerados de 1 a 13 e formam conjunto **disjunto** dos
  ``ERR-01``–``ERR-13`` do catálogo vigente, com a mesma cardinalidade e o mesmo
  intervalo. É a colisão **NS-1** do Mapa de Rastreabilidade de IDs,
  classificada **BLOQUEANTE**, com falha silenciosa comprovada: um `3` ingerido
  aqui e lido como `ERR-03` produz um diagnóstico plausível e errado, sem
  nenhum sinal de erro.
* ``item.alternativas[].id`` e ``item.gabarito`` separado — a 2.2 usa
  ``letra`` e ``correta`` **dentro** da alternativa.
* ausência de ``ontology_version`` — sem ele a anotação é indatável e não pode
  ser remapeada (GOV-1.0 §6.1).

O payload continua sendo armazenado **verbatim**: este módulo valida a forma
mínima e nunca recalcula, altera ou infere campo cognitivo algum. A validação
completa contra o catálogo é feita por `canonical_ontology.validate_item`, cujo
resultado é gravado junto do registro — registrado, nunca bloqueante, para que
uma anotação problemática fique visível para revisão em vez de desaparecer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Alternativa(BaseModel):
    model_config = ConfigDict(extra="allow")
    letra: str
    texto: str | None = None
    correta: bool | None = None


class Fonte(BaseModel):
    model_config = ConfigDict(extra="allow")
    banca: str | None = None
    ano: int | None = None
    prova: str | None = None
    numero: int | None = None
    disciplina: str | None = None
    tema: str | None = None
    conteudo: str | None = None
    arquivo_origem: str | None = None
    pagina: int | None = None


class Questao(BaseModel):
    model_config = ConfigDict(extra="allow")
    enunciado: str | None = None
    alternativas: list[Alternativa] = Field(default_factory=list)
    recursos: dict[str, Any] = Field(default_factory=dict)


class Habilidade(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    peso_no_processo: float | None = None
    confianca: float | str | None = None
    aproximado: bool | None = None


class Processo(BaseModel):
    """Um processo cognitivo do item.

    `papel` é vocabulário FECHADO — `nuclear` | `secundario` (Error Trace §7).
    O valor `facilitador`, aceito pelo formato anterior, não existe na 2.2: um
    processo que apenas facilita falha o teste de necessidade do Manual §4 e não
    deve ser registrado. Aqui ele é aceito como string e reprovado pela
    validação canônica, com mensagem explícita — em vez de rejeitado por
    tipagem, que produziria um 400 sem explicação útil.
    """
    model_config = ConfigDict(extra="allow")
    id: str
    papel: str | None = None
    peso_no_item: float | None = None
    confianca: float | str | None = None
    dificuldade_local: dict[str, Any] | float | None = None
    habilidades: list[Habilidade] = Field(default_factory=list)
    evidencias: dict[str, Any] = Field(default_factory=dict)
    justificativa: str | None = None


class EstruturaCognitiva(BaseModel):
    """Domínios e competências são DERIVADOS dos processos (Constituição §4.4).

    Se vierem preenchidos no payload, a validação canônica compara com a união
    derivada dos processos e reprova qualquer divergência — ela é erro de
    integridade, não alternativa de anotação.
    """
    model_config = ConfigDict(extra="allow")
    dominios: list[dict[str, Any]] = Field(default_factory=list)
    competencias: list[dict[str, Any]] = Field(default_factory=list)
    processos: list[Processo] = Field(default_factory=list)


class EloDeErro(BaseModel):
    """Um elo da cadeia ordenada de erro esperado.

    Substitui o campo único `erro` da 2.1. `confianca` é obrigatória em todo elo
    (Error Trace R-3): confiança implícita, ausente ou igual a 1 por convenção
    de preenchimento viola o Axioma da Crença Calibrada.
    """
    model_config = ConfigDict(extra="allow")
    ordem: int
    erro: str
    processo_afetado: str
    confianca: float | str
    mecanismo: str | None = None


class Distrator(BaseModel):
    model_config = ConfigDict(extra="allow")
    alternativa: str
    erros_esperados: list[EloDeErro] = Field(default_factory=list)
    plausibilidade: dict[str, Any] | str | None = None
    probabilidade_estimada: float | None = None
    explicacao: str | None = None


class Intervencao(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    gatilho: dict[str, Any] = Field(default_factory=dict)
    acao: str | None = None
    prioridade: Any = None


class Incerteza(BaseModel):
    model_config = ConfigDict(extra="allow")
    marcadores: list[str] = Field(default_factory=list)
    detalhe: str | None = None
    requer_arbitragem: bool | None = None


class Qualidade(BaseModel):
    model_config = ConfigDict(extra="allow")
    confianca_global: float | str | None = None
    revisado: bool | None = None
    revisor: str | None = None
    data_anotacao: str | None = None
    apto_para_camada_de_crenca: dict[str, Any] | bool | None = None
    observacoes: str | None = None


class AnnotationPayload(BaseModel):
    """Item anotado no Schema Sapiens 2.2.

    `extra='allow'` em todos os níveis para que acréscimos futuros do contrato
    não quebrem a ingestão; os campos declarados obrigatórios aqui são os que o
    contrato exige em todo objeto persistido.
    """
    model_config = ConfigDict(extra="allow")
    schema_version: str
    ontology_version: str
    item_id: str
    item_hash: str | None = None
    fonte: Fonte | None = None
    questao: Questao | None = None
    estrutura_cognitiva: EstruturaCognitiva | None = None
    incerteza: Incerteza | None = None
    distratores: list[Distrator] = Field(default_factory=list)
    intervencoes: list[Intervencao] = Field(default_factory=list)
    pedagogia: dict[str, Any] | None = None
    psicometria: dict[str, Any] | None = None
    pipeline: dict[str, Any] | None = None
    qualidade: Qualidade | None = None


class AnnotationRecord(BaseModel):
    """Wrapper armazenado no Mongo. `payload` é o JSON recebido, verbatim."""
    model_config = ConfigDict(extra="allow")
    item_id: str
    schema_version: str
    ontology_version: str
    item_hash: str | None = None
    banca: str | None = None
    ano: int | None = None
    prova: str | None = None
    numero: int | None = None
    disciplina: str | None = None
    payload: dict[str, Any]
    validacao: dict[str, Any] | None = None
    received_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)
