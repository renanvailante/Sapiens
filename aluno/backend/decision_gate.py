"""Decision Gate — classifica evidências em um estado operacional.

Não sabe nada sobre Enem, redação, Gemini ou qualquer LLM (nenhum import
deste tipo aparece neste arquivo, de propósito — é o que garante que a
confiabilidade de uma classificação nunca depende de como a evidência foi
produzida). Consome apenas `Evidencia`: sinais observáveis (candidatos,
suporte, evidências presentes/ausentes, método de origem). A classificação
vem da FORMA da evidência — concordância entre métodos independentes,
suporte de cada candidato, evidência crítica ausente — nunca de um valor de
confidence relatado por quem produziu a evidência. Um LLM pode relatar
confidence mal calibrada (já ocorreu no Sapiens: Gemini atribuindo ~0.7 a
quase toda questão); por isso nenhum campo desse tipo é lido aqui nem em
`redacao/escalonamento_redacao.py`.

Estados possíveis — nunca um score numérico:
- DETERMINADO: um candidato claro, suporte suficiente, sem conflito.
- AMBIGUO: candidato único mas com suporte fraco, ou evidência ausente crítica.
- CONFLITANTE: dois métodos independentes apontam candidatos diferentes.
- INSUFICIENTE: não há evidência (ou entrada) suficiente para propor um candidato.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EstadoOperacional(str, Enum):
    DETERMINADO = "DETERMINADO"
    AMBIGUO = "AMBIGUO"
    CONFLITANTE = "CONFLITANTE"
    INSUFICIENTE = "INSUFICIENTE"


@dataclass
class Evidencia:
    """Um sinal observável sobre um critério (`criterio_id`), de um método.

    `candidatos`: lista de `(valor, suporte)` — `valor` é o que este método
    propõe (ex.: `True`/`False` para um gatilho, ou um nível 0-200 para uma
    competência); `suporte` é uma força local a ESTE método (ex.: "3 dos 4
    elementos temáticos encontrados, 2x cada"), nunca uma probabilidade
    normalizada entre métodos diferentes — o gate só compara *concordância*
    de valor entre métodos, nunca soma ou pondera suporte entre eles.

    `suporte_minimo_forte`: a partir de qual suporte (na escala desta própria
    evidência) o candidato é considerado bem sustentado quando é o único
    método disponível. Cada heurística define o seu.
    """

    criterio_id: str
    metodo: str  # "mecanico" | "heuristica_local" | "llm"
    candidatos: list[tuple[Any, float]] = field(default_factory=list)
    evidencias_presentes: list[str] = field(default_factory=list)
    evidencias_ausentes: list[str] = field(default_factory=list)
    qualidade_entrada: str | None = None  # motivo declarado quando não há candidato
    suporte_minimo_forte: float = 1.0


@dataclass
class Classificacao:
    criterio_id: str
    estado: EstadoOperacional
    candidato_final: Any | None
    evidencias: list[Evidencia]
    motivo: str


def classificar(criterio_id: str, evidencias: list[Evidencia]) -> Classificacao:
    """Combina 1+ `Evidencia` do mesmo critério num único `EstadoOperacional`.

    Uso típico: chamado 1x só com a evidência de `heuristica_local`/`mecanico`.
    Se o resultado não for `DETERMINADO`, o item entra na lista de
    escalonamento; depois de resolvido, esta função é chamada de novo com a
    evidência local + a evidência `llm` para decidir se concordam
    (`DETERMINADO`) ou não (`CONFLITANTE` — nunca decidido a favor do lado
    mais severo por padrão).
    """
    if not evidencias:
        return Classificacao(criterio_id, EstadoOperacional.INSUFICIENTE, None, [], "sem evidência")

    dominantes: dict[str, tuple[Any, float, Evidencia]] = {}
    motivos_insuficiencia: list[str] = []
    for ev in evidencias:
        if ev.candidatos:
            valor, suporte = max(ev.candidatos, key=lambda c: c[1])
            dominantes[ev.metodo] = (valor, suporte, ev)
        elif ev.qualidade_entrada:
            motivos_insuficiencia.append(ev.qualidade_entrada)

    if not dominantes:
        motivo = "; ".join(motivos_insuficiencia) or "nenhum método propôs candidato"
        return Classificacao(criterio_id, EstadoOperacional.INSUFICIENTE, None, evidencias, motivo)

    valores_distintos = {v for v, _, _ in dominantes.values()}

    if len(dominantes) >= 2 and len(valores_distintos) > 1:
        detalhe = [(m, v) for m, (v, _, _) in dominantes.items()]
        return Classificacao(
            criterio_id, EstadoOperacional.CONFLITANTE, None, evidencias,
            f"métodos discordam: {detalhe}",
        )

    if len(dominantes) >= 2 and len(valores_distintos) == 1:
        valor = next(iter(valores_distintos))
        return Classificacao(
            criterio_id, EstadoOperacional.DETERMINADO, valor, evidencias,
            f"{len(dominantes)} métodos independentes concordam em {valor!r}",
        )

    metodo, (valor, suporte, ev) = next(iter(dominantes.items()))
    if suporte >= ev.suporte_minimo_forte:
        # `evidencias_ausentes` continua registrada em `evidencias` para o rastro
        # auditável (ex.: "registro e estrutura sintática não avaliados
        # localmente") — é informação sobre o MÉTODO, não necessariamente um
        # motivo para desconfiar do candidato. Quem gera a `Evidencia` decide se
        # uma ausência é bloqueante através do `suporte` que atribui: uma
        # heurística que considera uma ausência crítica deve refletir isso
        # propondo suporte abaixo de `suporte_minimo_forte`, não só listando a
        # ausência — senão o gate nunca chegaria a `DETERMINADO` para nenhuma
        # competência, já que toda heurística de nível/pontuação aqui declara
        # pelo menos um aspecto que não avalia.
        return Classificacao(
            criterio_id, EstadoOperacional.DETERMINADO, valor, evidencias,
            f"{metodo}: suporte {suporte} >= mínimo {ev.suporte_minimo_forte}",
        )
    return Classificacao(
        criterio_id, EstadoOperacional.AMBIGUO, valor, evidencias,
        f"{metodo}: suporte {suporte} abaixo do mínimo {ev.suporte_minimo_forte}",
    )
