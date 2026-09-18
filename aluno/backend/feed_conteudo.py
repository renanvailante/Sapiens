"""O CONTRATO DO CARD DE FEED: o que existe, o que vai para a tela, quem corrige.

O feed é a tela mais parecida com Reels que o produto tem: uma coisa por vez,
tela cheia, o dedo sobe e vem a próxima. O que separa isto de um mural de
questões é que **todo card pede uma ação** — escolher, revelar, votar, montar,
admitir que não lembrava. Um card que só se lê é um card que se pula.

Este módulo é o CONTRATO dessa ação. Ele responde três perguntas, e só elas:

1. **Que tipos de card existem** (`TIPOS_DE_CARD`), e como cada um se
   apresenta.
2. **O que desce para o navegador** (`para_a_tela`) — e, principalmente, o que
   NÃO desce. Gabarito, comentário por alternativa, ordem certa, pareamento
   certo e resultado de enquete ficam no servidor até a pessoa responder.
   Mesma regra de `cursos_conteudo.sanitizar_bloco` e de
   `test_gabarito_nao_vaza`: o feed é público, e `curl` não pode gabaritar.
3. **Quem corrige** (`corrigir`) — o servidor, sempre, a partir do que ele
   guardou. Nada do que o cliente manda sobre acerto é lido.

Quem ESCREVE card é `feed_ingestao` (texto colado → card). Quem GUARDA é
`feed_routes`. Este arquivo não fala com banco e não conhece aluno.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# O vocabulário
# ---------------------------------------------------------------------------

TEMAS = ("slate", "violet", "emerald", "amber", "rose", "ocean")

# Cada tipo declara o nome que aparece na tarja do card e o tema visual padrão.
# O tema padrão importa: quem cola um texto de 80 cards não vai escolher cor
# card a card, e um feed inteiro da mesma cor parece uma página só.
TIPOS_DE_CARD: dict[str, dict[str, str]] = {
    # Os sete pedidos, com o nome exato que aparece no guia e na tarja do card.
    "question":         {"nome": "Pergunta com alternativas", "tema": "violet"},
    "flashcard":        {"nome": "Flashcard",                 "tema": "emerald"},
    "verdadeiro_falso": {"nome": "Verdadeiro ou Falso",       "tema": "ocean"},
    "complete":         {"nome": "Complete a lacuna",         "tema": "violet"},
    "desafio":          {"nome": "Desafio",                   "tema": "rose"},
    "insight":          {"nome": "Insight",                   "tema": "rose"},
    "revisao":          {"nome": "Revisão",                   "tema": "amber"},
    # Extensões que fazem sentido no mesmo feed — a mesma abertura que o
    # pedido deixa ("podem ser adicionados outros tipos").
    "explanation":      {"nome": "Conceito",                  "tema": "slate"},
    "lista":            {"nome": "Lista",                     "tema": "slate"},
    "ordene":           {"nome": "Ordene",                    "tema": "amber"},
    "relacione":        {"nome": "Relacione",                 "tema": "ocean"},
    "enquete":          {"nome": "Enquete",                   "tema": "rose"},
    # Herdados do primeiro feed. O compilador de texto não os produz (imagem
    # ainda entra por URL, e vídeo por link), mas eles continuam válidos e
    # continuam sendo servidos — apagar tipo é apagar card que está no ar.
    "diagram":          {"nome": "Diagrama",                  "tema": "ocean"},
    "video":            {"nome": "Vídeo",                     "tema": "slate"},
}

# As famílias de interação. É por elas que `para_a_tela` e `corrigir` decidem
# o que esconder e o que conferir — e não por uma cadeia de `if tipo ==`
# espalhada pelo código. `desafio` entra em duas: pode vir com alternativas
# (então é corrigido como uma pergunta) ou com resposta curta/numérica aberta
# (`card["formato"] == "aberto"`, ver `corrigir`).
CORRIGIDOS = ("question", "complete", "verdadeiro_falso", "desafio")   # têm gabarito
AUTOAVALIADOS = ("flashcard", "revisao")                               # o aluno se julga
MONTAGEM = ("ordene", "relacione")                          # monta e o servidor confere
LEITURA = ("explanation", "insight", "lista", "diagram", "video")

# Mesma regra do conteúdo de curso: preço não mora em conteúdo. Um lote gerado
# por IA que inventasse `"custo_sparks": 50` seria promessa de preço publicada
# sem decisão de produto.
CHAVES_PROIBIDAS = ("custo", "custo_sparks", "preco", "preço", "sparks", "valor_sparks", "desconto")


def nome_do_tipo(tipo: str) -> str:
    return (TIPOS_DE_CARD.get(tipo) or {}).get("nome", tipo)


def tema_padrao(tipo: str) -> str:
    return (TIPOS_DE_CARD.get(tipo) or {}).get("tema", "slate")


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def _chaves_de_preco(valor: Any, caminho: str = "") -> list[str]:
    achados: list[str] = []
    if isinstance(valor, dict):
        for chave, dentro in valor.items():
            if str(chave).lower() in CHAVES_PROIBIDAS:
                achados.append(f"{caminho}{chave}")
            achados.extend(_chaves_de_preco(dentro, f"{caminho}{chave}."))
    elif isinstance(valor, list):
        for i, dentro in enumerate(valor):
            achados.extend(_chaves_de_preco(dentro, f"{caminho}{i}."))
    return achados


def validar_card(card: dict) -> list[str]:
    """Os problemas do card, em português, prontos para aparecer no painel.

    Lista vazia = pode ir ao ar. Cada regra aqui existe para impedir um card
    que CHEGA na tela do aluno e não funciona — que é bem pior do que um card
    que não é publicado.
    """
    problemas: list[str] = []
    tipo = card.get("content_type")
    rotulo = (card.get("question_data") or {}).get("prompt") or card.get("content_id") or "card"
    diz = lambda p: problemas.append(f"{rotulo[:60]}: {p}")  # noqa: E731

    if tipo not in TIPOS_DE_CARD:
        return [f"{rotulo[:60]}: tipo de card desconhecido ({tipo!r})"]
    if not (card.get("question_data") or {}).get("prompt", "").strip():
        diz("sem texto principal — o card ficaria em branco na tela")
    if card.get("background_theme") not in TEMAS:
        diz(f"tema visual {card.get('background_theme')!r} não existe")

    opcoes = card.get("answer_options") or []
    meta = card.get("metadata") or {}

    if tipo == "desafio" and card.get("formato") == "aberto":
        if not meta.get("aceitos"):
            diz("desafio de resposta aberta sem gabarito — escreva `Resposta:` com um número ou texto curto")
    elif tipo in CORRIGIDOS:
        if len(opcoes) < 2:
            diz("precisa de pelo menos duas alternativas")
        certas = [o for o in opcoes if o.get("is_correct")]
        if len(certas) != 1:
            diz(f"precisa de exatamente uma alternativa certa (tem {len(certas)})")
        if any(not str(o.get("label", "")).strip() for o in opcoes):
            diz("tem alternativa vazia")
    elif tipo == "enquete":
        if len(opcoes) < 2:
            diz("enquete precisa de pelo menos duas opções")
        if any(o.get("is_correct") for o in opcoes):
            diz("enquete não tem resposta certa — é opinião, e marcar uma certa quebra isso")
    elif tipo in AUTOAVALIADOS:
        if not (card.get("explanation_data") or {}).get("text", "").strip():
            diz("sem verso — não há o que revelar")
    elif tipo == "ordene":
        passos = meta.get("passos") or []
        exibida = meta.get("ordem_exibida") or []
        if len(passos) < 3:
            diz("ordenar com menos de três passos não é desafio nenhum")
        if sorted(exibida) != sorted(p.get("id") for p in passos):
            diz("a ordem de exibição não bate com os passos")
    elif tipo == "relacione":
        pares = meta.get("pares") or []
        if len(pares) < 2:
            diz("relacionar precisa de pelo menos dois pares")
        if len({p.get("direita_id") for p in pares}) != len(pares):
            diz("dois pares apontam para a mesma coluna da direita")
    elif tipo == "lista":
        if len(meta.get("itens") or []) < 2:
            diz("uma lista de um item só é um conceito, não uma lista")

    for caminho in _chaves_de_preco(meta) + _chaves_de_preco(card.get("question_data")):
        diz(f"conteúdo não declara preço, e `{caminho}` é preço")

    return problemas


# ---------------------------------------------------------------------------
# O que desce para o navegador
# ---------------------------------------------------------------------------

# Campos que nunca saem daqui, em nenhum tipo de card.
_SEGREDOS_DA_META = ("pares", "votos", "fecho", "ordem_certa", "aceitos", "numero", "resposta_exibicao")


def para_a_tela(card: dict) -> dict:
    """O card como o navegador o recebe.

    O que some, e por quê:

    * `is_correct` e o `feedback` de cada alternativa — o comentário do
      distrator quase sempre entrega qual é a certa ("A soma antes de
      multiplicar").
    * `explanation_data` dos tipos com gabarito — é a explicação do DEPOIS.
      Ela volta na resposta do POST, no instante em que ensina alguma coisa.
    * a ordem certa de `ordene` e o pareamento de `relacione` — o card desce
      já embaralhado, com os ids que o servidor sabe conferir.
    * os votos da enquete, que só fazem sentido depois do próprio voto.

    Fica: `tem_dica`, porque a tela precisa saber que existe dica para decidir
    se mostra o botão — sem saber qual é.
    """
    limpo = {k: v for k, v in card.items() if k != "_id"}
    tipo = card.get("content_type")
    meta = dict(card.get("metadata") or {})

    limpo["answer_options"] = [
        {"key": o.get("key"), "label": o.get("label")}
        for o in card.get("answer_options") or []
    ]

    if tipo in CORRIGIDOS or tipo in MONTAGEM or tipo == "enquete":
        limpo.pop("explanation_data", None)

    if tipo == "ordene":
        passos = {p["id"]: p for p in meta.get("passos") or []}
        ordem = meta.get("ordem_exibida") or list(passos)
        meta["passos"] = [
            {"id": i, "texto": passos[i]["texto"]} for i in ordem if i in passos
        ]
        meta.pop("ordem_exibida", None)
    elif tipo == "relacione":
        pares = meta.get("pares") or []
        meta["esquerda"] = [{"id": p["id"], "texto": p["esquerda"]} for p in pares]
        # A direita desce na ORDEM EMBARALHADA, e com id próprio: se ela
        # descesse com o id do par, o pareamento certo estaria no HTML.
        exibida = meta.get("direita_exibida") or [p["direita_id"] for p in pares]
        por_id = {p["direita_id"]: p["direita"] for p in pares}
        meta["direita"] = [{"id": i, "texto": por_id[i]} for i in exibida if i in por_id]
        meta.pop("direita_exibida", None)

    meta["tem_dica"] = bool(meta.get("dica"))
    meta.pop("dica", None)
    for chave in _SEGREDOS_DA_META:
        meta.pop(chave, None)
    limpo["metadata"] = meta
    limpo["rotulo"] = nome_do_tipo(tipo)
    return limpo


# ---------------------------------------------------------------------------
# A correção
# ---------------------------------------------------------------------------


def _chave_certa(card: dict) -> str | None:
    return next((o.get("key") for o in card.get("answer_options") or [] if o.get("is_correct")), None)


def _normalizar(texto: str) -> str:
    """Ignora acento, caixa e espaço repetido — mesma régua de
    `cursos_conteudo._normalizar`, para o desafio de resposta aberta."""
    import unicodedata
    sem_acento = unicodedata.normalize("NFKD", (texto or "").strip().lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.split())


def corrigir(card: dict, resposta: dict) -> tuple[bool | None, dict]:
    """Confere a resposta e devolve `(acertou, o que revelar agora)`.

    `acertou` é `None` quando a pergunta não tem certo nem errado (leitura,
    enquete, autoavaliação sem julgamento). A REVELAÇÃO é o pagamento da
    interação: é aqui — e só aqui — que o gabarito, o comentário da
    alternativa escolhida e a explicação saem do servidor.
    """
    tipo = card.get("content_type")
    resposta = resposta or {}
    explicacao = (card.get("explanation_data") or {}).get("text") or ""
    meta = card.get("metadata") or {}
    revelacao: dict[str, Any] = {}

    if tipo == "desafio" and card.get("formato") == "aberto":
        digitado = str(resposta.get("texto") or "").strip()
        if not digitado:
            return None, {}
        numero = meta.get("numero")
        if numero:
            try:
                valor = float(digitado.replace(",", "."))
                acertou = abs(valor - float(numero["valor"])) <= float(numero.get("tolerancia", 0) or 0)
            except (TypeError, ValueError):
                acertou = _normalizar(digitado) in {_normalizar(a) for a in meta.get("aceitos") or []}
        else:
            acertou = _normalizar(digitado) in {_normalizar(a) for a in meta.get("aceitos") or []}
        return acertou, {
            "resposta_certa": meta.get("resposta_exibicao") or "",
            "explicacao": explicacao,
        }

    if tipo in CORRIGIDOS:
        escolhida = resposta.get("selected")
        if not escolhida:
            return None, {}
        certa = _chave_certa(card)
        acertou = escolhida == certa
        opcao = next((o for o in card.get("answer_options") or [] if o.get("key") == escolhida), {})
        revelacao = {
            "correct_key": certa,
            # O comentário da alternativa QUE ELE ESCOLHEU. É a única
            # devolutiva que responde "por que a MINHA conta deu isso".
            "feedback": opcao.get("feedback") or "",
            "explicacao": explicacao,
        }
        return acertou, revelacao

    if tipo == "enquete":
        escolhida = resposta.get("selected")
        if not escolhida:
            return None, {}
        return None, {"fecho": meta.get("fecho") or "", "explicacao": explicacao}

    if tipo == "ordene":
        enviada = [str(i) for i in (resposta.get("ordem") or [])]
        if not enviada:
            return None, {}
        certa = [p["id"] for p in meta.get("passos") or []]
        acertou = enviada == certa
        return acertou, {
            "ordem_certa": certa,
            "passos_certos": meta.get("passos") or [],
            "explicacao": explicacao,
        }

    if tipo == "relacione":
        enviados = resposta.get("pares") or {}
        if not enviados:
            return None, {}
        pares = meta.get("pares") or []
        certos = {p["id"]: p["direita_id"] for p in pares}
        acertou = all(enviados.get(k) == v for k, v in certos.items()) and len(enviados) == len(certos)
        return acertou, {
            "pares_certos": certos,
            "explicacao": explicacao,
        }

    if tipo in AUTOAVALIADOS:
        if "lembrou" not in resposta:
            return None, {}
        # Autoavaliação: quem julga é o aluno, e o servidor registra o que ele
        # disse. Não há gabarito para conferir — e inventar um seria mentir
        # sobre o que o dado significa na análise.
        return bool(resposta.get("lembrou")), {"explicacao": explicacao}

    return None, {"explicacao": explicacao}
