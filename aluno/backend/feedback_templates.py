"""Feedback qualitativo por TEMPLATES — 100% regras, sem IA/LLM.

Traduz a anotação cognitiva do item (Schema 2.2) em frases de linguagem
cotidiana, sem jargão técnico e sem entregar a resposta.

**Duas correções estruturais em 2026-08-21, ambas determinadas pelos contratos:**

1. *Leitura da cadeia de erro.* O módulo lia `distratores[].erro` e
   `distratores[].processos_afetados` — campos da 2.1, removidos na 2.2. Agora
   lê `erros_esperados[]` e usa o elo de **`ordem: 1`**, a RAIZ da cadeia. A
   regra é explícita: "um traço cuja raiz é leitura deficiente e cuja
   manifestação é erro proporcional pede a intervenção da raiz" (Error Trace
   §1.1). Falar da manifestação de superfície é pedagogicamente ineficaz, que é
   exatamente o motivo de a cadeia ser ordenada.

2. *Origem do significado de cada `ERR-NN`.* Havia aqui um dicionário
   hard-coded que atribuía a cada ID um significado **divergente do catálogo**:
   `ERR-01` recebia "parou numa etapa intermediária" quando o catálogo o define
   como "Leitura literal deficiente"; `ERR-13` recebia "confusão entre grandezas
   parecidas" quando o catálogo o define como "Classificação por critério
   superficial". Esse mapa era um contrato paralelo não declarado (GOV-1.0 §12)
   e reproduzia, dentro do código, a colisão NS-2 do Mapa de Rastreabilidade —
   mesmo identificador, significado diferente. A explicação de cada erro passa a
   ser **derivada do catálogo canônico** (`mecanismo` e `evidencia_observavel`),
   e o texto autoral fica restrito ao enquadramento e à dica de estudo, que não
   são normativos.
"""
from __future__ import annotations

import random
from typing import Any, Optional

from canonical_ontology import load_ontology

# ---- Frases para quando o aluno ACERTA ----
POSITIVOS = [
    "Boa! Você aplicou o raciocínio certo do começo ao fim.",
    "Acertou! Seu caminho para resolver essa questão foi consistente.",
    "Certa resposta! Você conectou bem as informações da questão.",
]

# ---- Dica de estudo por FAMÍLIA de processo (PROC-QUANT-01 -> "PROC-QUANT") ----
# Texto autoral, não normativo: diz em linguagem simples o que a questão
# exercita. As famílias abaixo são as 11 do catálogo v1.4.1 — se um domínio novo
# entrar na ontologia, a ausência aqui degrada para silêncio, nunca para uma
# dica errada.
PROCESSOS = {
    "PROC-QUANT": "Essa questão pede organização com números e relações entre quantidades. "
                  "Vale conferir cada etapa antes de escolher.",
    "PROC-ESPACO": "Aqui você precisa enxergar formas, medidas e o papel de cada parte. "
                   "Fazer um desenho rápido costuma clarear a relação entre elas.",
    "PROC-MUD": "Aqui você acompanha como uma grandeza muda em relação à outra. "
                "Ver o que aumenta, o que diminui e o que se conserva orienta a resposta.",
    "PROC-INC": "Essa questão lida com dados, chances e variabilidade. "
                "Identificar o total e a parte que interessa antes de comparar ajuda muito.",
    "PROC-CAUSAL": "O ponto aqui é explicar por que algo aconteceu. "
                   "Separe o que é causa do que apenas acontece junto.",
    "PROC-LOGICO": "Aqui você julga se a conclusão realmente segue das premissas. "
                   "Vale testar se existe um contraexemplo.",
    "PROC-SIMB": "Essa questão pede traduzir o enunciado para uma expressão ou fórmula. "
                 "Escrever o que cada letra significa evita trocas.",
    "PROC-TEXT": "Aqui o segredo é ler com atenção e separar a informação que importa. "
                 "Sublinhar os dados centrais ajuda bastante.",
    "PROC-EXP": "Essa questão trata de como se investiga algo: hipótese, variável, controle. "
                "Pergunte-se o que precisaria ser mantido fixo para o teste valer.",
    "PROC-SIST": "Aqui você prevê como um sistema responde quando uma parte muda. "
                 "Seguir o efeito passo a passo pelas partes ajuda.",
    "PROC-CLASSIF": "Essa questão pede agrupar por um critério compartilhado. "
                    "Verifique se o critério é estrutural, não apenas aparente.",
}

ERRO_GENERICO = (
    "Não foi dessa vez. Reveja com calma o que a questão pede e tente identificar "
    "em que passo a sua resposta mudou de direção."
)

# Sentinelas do contrato (Error Trace §3, R-2). São respostas válidas da
# anotação, não falhas — e cada uma pede um enquadramento diferente do aluno.
SENTINELAS = {
    "erro-nao-catalogado-nesta-versao": (
        "Esse tipo de engano ainda não está mapeado para o raciocínio que a "
        "questão exige. Vale refazer a questão explicando cada passo em voz alta."
    ),
    "sem-mecanismo-cognitivo-identificavel": (
        "Essa alternativa costuma ser marcada por descuido, não por falta de "
        "entendimento. Reler a pergunta final antes de marcar resolve a maior parte."
    ),
}


def _catalogo_erros() -> dict[str, dict]:
    return {e["id"]: e for e in load_ontology().get("tipos_erro", [])}


def _proc_family(pid: Optional[str]) -> Optional[str]:
    if not pid:
        return None
    parts = pid.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else pid


def _annotated_item(master: dict) -> dict:
    """`item` é a chave canônica (Schema 2.2); `pipeline` é a forma anterior."""
    return master.get("item") or master.get("pipeline") or master


def _processo_nuclear(master: dict) -> Optional[str]:
    ec = _annotated_item(master).get("estrutura_cognitiva") or {}
    procs = ec.get("processos") or []
    nuclear = next((p for p in procs if isinstance(p, dict) and p.get("papel") == "nuclear"), None)
    alvo = nuclear or (procs[0] if procs else None)
    return alvo.get("id") if isinstance(alvo, dict) else None


def _distrator(master: dict, letra: Optional[str]) -> Optional[dict]:
    for d in _annotated_item(master).get("distratores") or []:
        if isinstance(d, dict) and d.get("alternativa") == letra:
            return d
    return None


def _elo_raiz(distrator: dict) -> Optional[dict]:
    """O elo de `ordem: 1` — a falha que, se não tivesse ocorrido, tornaria as
    seguintes improváveis (Error Trace §1.1). Nunca o último elo observado."""
    elos = [e for e in (distrator.get("erros_esperados") or []) if isinstance(e, dict)]
    if not elos:
        return None
    return min(elos, key=lambda e: e.get("ordem") if isinstance(e.get("ordem"), int) else 99)


def _mensagem_de_erro(erro_id: Optional[str]) -> Optional[str]:
    """Explicação do erro, derivada do CATÁLOGO — nunca de um mapa paralelo."""
    if not erro_id:
        return None
    if erro_id in SENTINELAS:
        return SENTINELAS[erro_id]
    erro = _catalogo_erros().get(erro_id)
    if not erro:
        return None
    mecanismo = (erro.get("mecanismo") or "").strip().rstrip(".")
    evidencia = (erro.get("evidencia_observavel") or "").strip().rstrip(".")
    if mecanismo and evidencia:
        return f"O que costuma acontecer aqui: {mecanismo.lower()}. Na prática, {evidencia.lower()}."
    if mecanismo:
        return f"O que costuma acontecer aqui: {mecanismo.lower()}."
    return None


def build_feedback(
    master: Optional[dict], alternativa_escolhida: Optional[str], acertou: Optional[bool]
) -> dict[str, Any]:
    """Feedback qualitativo por templates (sem IA).

    Formato: ``{"acertou": bool|None, "titulo": str, "mensagens": [str, ...]}``
    """
    mensagens: list[str] = []

    if acertou:
        mensagens.append(random.choice(POSITIVOS))
        if master:
            dica = PROCESSOS.get(_proc_family(_processo_nuclear(master)) or "")
            if dica:
                mensagens.append("Para fixar: " + dica)
        return {"acertou": True, "titulo": "Mandou bem!", "mensagens": mensagens}

    # Errou (ou gabarito desconhecido): parte da RAIZ da cadeia de erro esperada.
    if master:
        dist = _distrator(master, alternativa_escolhida)
        raiz = _elo_raiz(dist) if dist else None
        if raiz:
            msg = _mensagem_de_erro(raiz.get("erro"))
            if msg:
                mensagens.append(msg)
            # A dica de estudo acompanha o processo afetado pela RAIZ, não o
            # processo nuclear do item: é ali que a intervenção precisa agir.
            dica = PROCESSOS.get(_proc_family(raiz.get("processo_afetado")) or "")
            if dica:
                mensagens.append(dica)
        if not mensagens:
            dica = PROCESSOS.get(_proc_family(_processo_nuclear(master)) or "")
            if dica:
                mensagens.append(dica)

    if not mensagens:
        mensagens.append(ERRO_GENERICO)

    return {"acertou": bool(acertou), "titulo": "Vamos revisar juntos", "mensagens": mensagens}
