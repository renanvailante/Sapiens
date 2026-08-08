"""Feedback qualitativo baseado em TEMPLATES (Fase 3) — 100% regras, sem IA/LLM.

Mapeia processo cognitivo / competência / distrator (erro) -> frases simples,
em linguagem cotidiana e sem jargão técnico. É um lookup direto no dicionário.

Códigos baseados na Ontologia v1.4 (famílias de processo e tipos de erro
presentes nas questões auditadas da coleção 'itens').
"""
from __future__ import annotations

import random
from typing import Any, Optional

# ---- Frases para quando o aluno ACERTA ----
POSITIVOS = [
    "Boa! Você aplicou o raciocínio certo do começo ao fim.",
    "Acertou! Seu caminho para resolver essa questão foi consistente.",
    "Certa resposta! Você conectou bem as informações da questão.",
]

# ---- Por FAMÍLIA de processo (PROC-QUANT-01 -> "PROC-QUANT") ----
# Diz, em linguagem simples, o que a questão realmente exercita e uma dica.
PROCESSOS = {
    "PROC-QUANT": [
        "Essa questão pede organização com números e contas passo a passo. Vale conferir cada etapa antes de escolher.",
        "O foco aqui é transformar os dados em contas certas. Reler o que cada número representa ajuda a não se perder.",
    ],
    "PROC-ESPACO": [
        "Aqui você precisa enxergar as formas e as medidas. Fazer um desenho rápido costuma clarear a relação entre elas.",
        "A questão trabalha com figuras e espaço. Marcar no desenho o que já sabe ajuda a achar o que falta.",
    ],
    "PROC-SIMB": [
        "Essa questão pede traduzir o enunciado para uma expressão ou fórmula. Escrever o que cada letra significa evita trocas.",
        "O ponto central é montar a expressão certa a partir do texto. Vá com calma nessa 'tradução'.",
    ],
    "PROC-TEXT": [
        "Aqui o segredo é ler com atenção e separar a informação principal. Sublinhar os dados importantes ajuda muito.",
        "A questão exige interpretar bem o texto antes de calcular. Reler devagar costuma revelar o que passou batido.",
    ],
    "PROC-INC": [
        "Essa questão lida com chances e dados. Vale identificar o total e a parte que interessa antes de comparar.",
        "O foco é interpretar dados e possibilidades. Organizar as informações em partes facilita a conta.",
    ],
    "PROC-MUD": [
        "Aqui você acompanha como uma grandeza muda em relação à outra. Ver o que aumenta e o que diminui orienta a resposta.",
        "A questão trata de variação e proporção. Comparar os cenários lado a lado ajuda a enxergar o padrão.",
    ],
}

# ---- Por TIPO DE ERRO do distrator escolhido (ERR-*) ----
ERROS = {
    "ERR-01": [
        "Parece que você parou em uma etapa intermediária. Muitas vezes falta o último passo para chegar ao que a questão pede.",
    ],
    "ERR-02": [
        "Pode ter havido uma troca de dados ou de sinal no meio do caminho. Reler os números com calma ajuda a evitar isso.",
    ],
    "ERR-03": [
        "Um passo do cálculo pode ter ficado de fora. Refazer a conta em etapas separadas costuma resolver.",
    ],
    "ERR-04": [
        "Talvez uma multiplicação ou divisão tenha se perdido no caminho. Conferir a ordem das operações ajuda.",
    ],
    "ERR-05": [
        "Pode ter faltado aplicar uma condição do enunciado. Vale checar se você usou todas as informações dadas.",
    ],
    "ERR-06": [
        "Uma fórmula pode ter sido trocada por outra parecida. Anotar a fórmula certa antes de calcular evita o engano.",
    ],
    "ERR-10": [
        "A interpretação do que a questão pede pode ter escapado. Reler a pergunta final ajuda a mirar na resposta certa.",
    ],
    "ERR-11": [
        "Alguns dados podem ter sido lidos de forma trocada. Voltar ao texto e conferir cada valor ajuda bastante.",
    ],
    "ERR-13": [
        "Pode ter havido uma confusão entre grandezas parecidas. Identificar bem o que é cada coisa evita a troca.",
    ],
}

ERRO_GENERICO = (
    "Não foi dessa vez. Reveja com calma o que a questão pede e tente identificar "
    "em que passo a sua resposta mudou de direção."
)


def _proc_family(pid: Optional[str]) -> Optional[str]:
    if not pid:
        return None
    parts = pid.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else pid


def _pick(options: list[str]) -> Optional[str]:
    return random.choice(options) if options else None


def _nuclear_process(master: dict) -> Optional[str]:
    ec = (master.get("pipeline") or {}).get("estrutura_cognitiva") or {}
    procs = ec.get("processos") or []
    nuclear = next((p for p in procs if p.get("papel") == "nuclear"), None)
    alvo = nuclear or (procs[0] if procs else None)
    return alvo.get("id") if alvo else None


def _distrator_para_alternativa(master: dict, letra: Optional[str]) -> Optional[dict]:
    for d in (master.get("pipeline") or {}).get("distratores") or []:
        if d.get("alternativa") == letra:
            return d
    return None


def build_feedback(master: Optional[dict], alternativa_escolhida: Optional[str], acertou: Optional[bool]) -> dict[str, Any]:
    """Retorna feedback qualitativo por templates (sem IA).

    Formato: { "acertou": bool|None, "titulo": str, "mensagens": [str, ...] }
    """
    mensagens: list[str] = []

    if acertou:
        msg = _pick(POSITIVOS)
        if msg:
            mensagens.append(msg)
        if master:
            fam = _proc_family(_nuclear_process(master))
            reforco = _pick(PROCESSOS.get(fam or "", []))
            if reforco:
                mensagens.append("Para fixar: " + reforco)
        return {"acertou": True, "titulo": "Mandou bem!", "mensagens": mensagens or [POSITIVOS[0]]}

    # Errou (ou correta desconhecida): tenta usar o distrator escolhido.
    if master:
        dist = _distrator_para_alternativa(master, alternativa_escolhida)
        if dist:
            erro_msg = _pick(ERROS.get(dist.get("erro") or "", []))
            if erro_msg:
                mensagens.append(erro_msg)
            fam = _proc_family((dist.get("processos_afetados") or [None])[0])
            proc_msg = _pick(PROCESSOS.get(fam or "", []))
            if proc_msg:
                mensagens.append(proc_msg)
        if not mensagens:
            fam = _proc_family(_nuclear_process(master))
            proc_msg = _pick(PROCESSOS.get(fam or "", []))
            if proc_msg:
                mensagens.append(proc_msg)

    if not mensagens:
        mensagens.append(ERRO_GENERICO)

    return {"acertou": bool(acertou), "titulo": "Vamos revisar juntos", "mensagens": mensagens}
