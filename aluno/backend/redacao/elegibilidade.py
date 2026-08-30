"""Etapa 0 — só os gatilhos que o canon marca `decidivel_mecanicamente: true`
(`ZERO-03`, `ZERO-04`, `ZERO-08`). Puro Python, zero rede, zero LLM.

Cada função devolve uma `decision_gate.Evidencia` de `metodo="mecanico"` —
nunca decide sozinha fora do Decision Gate, para que o mesmo mecanismo de
classificação (inclusive o registro de evidências ausentes) valha aqui e nas
heurísticas locais.
"""
from __future__ import annotations

import re
import unicodedata

from decision_gate import Evidencia
from redacao.tipos import RedacaoEntrada

# Núcleo de palavras function-word do português — suficiente para distinguir
# "texto majoritariamente em português" de "texto majoritariamente em outro
# idioma" sem precisar de um detector de idioma como dependência nova (essas
# palavras aparecem em altíssima frequência em QUALQUER texto em português
# corrido, dissertativo ou não; a ausência quase total delas é o sinal).
_STOPWORDS_PT = frozenset(
    "de a o que e do da em um para com não uma os no se na por mais as dos "
    "como mas ao ele das seu sua ou ser quando muito nos já eu também só "
    "pelo pela até isso ela entre depois sem mesmo aos seus quem nas me "
    "esse eles você essa num nem suas meu às minha numa pelos elas qual "
    "nós lhe deles essas esses pelas este dele tu te vocês vos lhes meus "
    "minhas teu tua teus tuas nosso nossa nossos nossas dessa desse dessas "
    "desses aquele aquela aqueles aquelas isto aquilo estou está estamos "
    "estão".split()
)

_LIMIAR_COBERTURA_PT = 0.15  # fração mínima de palavras-função em PT esperada num texto real em português


def _tokens(texto: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", texto.lower(), flags=re.UNICODE)


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def checar_texto_em_branco(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-03 — ausência de texto escrito."""
    vazio = not (entrada.texto or "").strip()
    return Evidencia(
        criterio_id="ZERO-03",
        metodo="mecanico",
        candidatos=[(vazio, 1.0)],
        evidencias_presentes=["texto vazio"] if vazio else ["texto presente"],
    )


def checar_texto_insuficiente(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-04 — até 7 linhas manuscritas configura texto insuficiente
    (convenção de engenharia AMB-01: ≤7 dispara, ≥8 não dispara este gatilho
    especificamente).

    Só decidível mecanicamente quando `linhas_manuscritas` é informado
    (submissão veio de um fluxo que contou linhas — ex.: transcrição
    manual/OCR futuro). Para texto digitado direto, não existe "linha
    manuscrita" — a checagem por proxy de tamanho fica em
    `heuristicas.checar_texto_curto_digital`, que nunca decide sozinha um
    disparo, só descarta com segurança textos claramente longos.
    """
    if entrada.linhas_manuscritas is None:
        return Evidencia(
            criterio_id="ZERO-04",
            metodo="mecanico",
            qualidade_entrada="linhas_manuscritas não informado — ZERO-04 não decidível por esta via",
        )
    dispara = entrada.linhas_manuscritas <= 7
    return Evidencia(
        criterio_id="ZERO-04",
        metodo="mecanico",
        candidatos=[(dispara, 1.0)],
        evidencias_presentes=[f"{entrada.linhas_manuscritas} linhas manuscritas"],
    )


def checar_lingua_estrangeira(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-08 — predominância de língua estrangeira.

    Sinal: fração de tokens que são palavras-função comuns do português.
    Um texto real em português corrido sempre passa muito acima do limiar;
    um texto majoritariamente em outro idioma fica muito abaixo. A zona
    intermediária (texto muito curto, ou de fato misto) não é decidida aqui
    — vira `AMBIGUO` no Decision Gate por suporte insuficiente.
    """
    tokens = _tokens(entrada.texto or "")
    if len(tokens) < 20:
        return Evidencia(
            criterio_id="ZERO-08",
            metodo="mecanico",
            qualidade_entrada="texto curto demais para estimar idioma com confiança",
        )
    normalizados = {_sem_acento(t) for t in tokens}
    stop_norm = {_sem_acento(s) for s in _STOPWORDS_PT}
    cobertura = sum(1 for t in tokens if _sem_acento(t) in stop_norm) / len(tokens)
    dispara = cobertura < _LIMIAR_COBERTURA_PT
    # suporte proporcional à distância do limiar — quanto mais longe, mais forte o sinal.
    suporte = min(3.0, abs(cobertura - _LIMIAR_COBERTURA_PT) / _LIMIAR_COBERTURA_PT * 2)
    return Evidencia(
        criterio_id="ZERO-08",
        metodo="mecanico",
        candidatos=[(dispara, suporte)],
        evidencias_presentes=[f"cobertura de palavras-função PT: {cobertura:.2f}"],
        suporte_minimo_forte=1.0,
    )


def checar_identificacao_fora_local(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-07 — identificação fora do espaço destinado na Folha de Redação.

    Convenção de engenharia (não uma das ambiguidades do canon, é uma
    constatação estrutural): esse gatilho pressupõe um "local" físico na
    folha de resposta. Submissão de texto digital nesta v1 não tem esse
    conceito — não há onde "vazar" uma identificação para fora do espaço
    destinado. Estruturalmente inaplicável a esta modalidade, não inferido
    em silêncio: nunca dispara aqui, documentado explicitamente.
    """
    return Evidencia(
        "ZERO-07", "mecanico", candidatos=[(False, 10.0)],
        evidencias_presentes=["não aplicável a submissão de texto digital nesta v1"],
    )


def checar_texto_ilegivel(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-09 — texto ilegível. O próprio canon nota que só se aplica a
    redação manuscrita ("sem sentido para texto já transcrito
    digitalmente") — texto digitado é sempre legível por definição."""
    return Evidencia(
        "ZERO-09", "mecanico", candidatos=[(False, 10.0)],
        evidencias_presentes=["não aplicável a submissão de texto digital (só manuscrita, conforme o canon)"],
    )


def avaliar_mecanico(entrada: RedacaoEntrada) -> dict[str, Evidencia]:
    return {
        "ZERO-03": checar_texto_em_branco(entrada),
        "ZERO-04": checar_texto_insuficiente(entrada),
        "ZERO-07": checar_identificacao_fora_local(entrada),
        "ZERO-08": checar_lingua_estrangeira(entrada),
        "ZERO-09": checar_texto_ilegivel(entrada),
    }
