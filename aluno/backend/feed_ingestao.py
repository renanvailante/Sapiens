"""O COMPILADOR DO FEED: um texto grande entra, uma pilha de cards sai.

O jeito antigo de pôr conteúdo no feed era um formulário por card: escolher o
tipo, digitar o enunciado, digitar quatro alternativas, marcar a certa, salvar,
repetir. Quarenta cards eram quarenta ciclos disso, e por isso o feed nunca
teve quarenta cards.

Aqui a pessoa escreve (ou manda um modelo de linguagem escrever) **um texto
só**, com dezenas de cards dentro, cola numa caixa e publica. Este módulo é a
ponte, e é a mesma decisão de arquitetura que `cursos_ingestao` já tomou para
os cursos: um parser único, PURO (não fala com banco, não conhece aluno), cujo
formato é frouxo na entrada e rígido na saída.

O contrato do texto — a régua que o painel mostra ao lado do campo
------------------------------------------------------------------
Cada card começa com uma linha de cabeçalho que declara o TIPO:

    ## QUESTÃO — Proporcionalidade
    Se 3 xícaras fazem 12 biscoitos, quantas fazem 20?
    A) 4
    B) 5
    C) 6
    **Resposta:** B
    **Feedback:** Cada biscoito pede 0,25 xícara. A alternativa A divide por 5.

    ## FLASHCARD — Trabalho de uma força
    Qual é a fórmula do trabalho de uma força constante?
    Verso: W = F · d · cos(θ)

O que o compilador faz e um importador ingênuo não faria
-------------------------------------------------------
1. **Embaralha as alternativas** com semente fixa no id do card, e o id da
   alternativa é a POSIÇÃO exibida. Quem escreve põe a certa em A quase
   sempre; publicado assim, o feed ensina a clicar na primeira — e o gabarito
   estaria legível no HTML.
2. **Reparte o feedback por alternativa** (reusando `cursos_ingestao`): a
   explicação da resposta certa vira a explicação do card, e cada comentário
   vira o feedback DAQUELE distrator.
3. **Embaralha os passos do `ordene` e a coluna direita do `relacione`**, e
   guarda a ordem certa só do lado do servidor.
4. **O id do card é o hash do texto dele.** Recompilar exatamente o mesmo
   texto dá o mesmo id — colar o mesmo lote duas vezes (um duplo clique) não
   duplica nada. Reescrever uma frase do card MUDA o hash: o resultado é um
   card novo, e o antigo continua no ar até alguém apagá-lo — publicar nunca
   apaga em silêncio. Mexer num card nunca muda o id dos outros.
5. **Card quebrado vira aviso, não catástrofe.** Uma questão sem `Resposta:`
   sai nominalmente nos avisos e o resto do lote vai ao ar. Só um texto que
   não produziu card NENHUM é recusado.
"""
from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from dataclasses import dataclass, field

import feed_conteudo as fc
from cursos_ingestao import repartir_feedback, como_numero, variantes_aceitas

SCHEMA_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Vocabulário aceito na entrada
# ---------------------------------------------------------------------------

# Um tipo, muitos jeitos de escrevê-lo. Quem gera o texto num modelo de
# linguagem não decora o nome exato, e recusar "PERGUNTA" quando se esperava
# "QUESTÃO" é perder um card por causa de sinônimo.
_SINONIMOS: dict[str, tuple[str, ...]] = {
    "question": ("questao", "questão", "pergunta", "pergunta com alternativas", "quiz", "multipla escolha", "múltipla escolha", "objetiva", "alternativas"),
    "flashcard": ("flashcard", "flash card", "cartao", "cartão"),
    "verdadeiro_falso": ("verdadeiro ou falso", "verdadeiro falso", "verdadeiro/falso", "v ou f", "vf", "mito ou verdade", "certo ou errado"),
    "complete": ("complete", "complete a lacuna", "completar", "lacuna", "preencha", "cloze"),
    "desafio": ("desafio", "desafio final", "challenge", "questao desafio", "prova real"),
    "insight": ("insight", "curiosidade", "sabia", "voce sabia", "você sabia", "fato", "voce sabia que", "você sabia que"),
    "revisao": ("revisao", "revisão", "rememorando", "lembrete", "recall", "voce lembra", "você lembra", "relembrar"),
    "explanation": ("conceito", "explicacao", "explicação", "texto", "resumo", "ideia", "aula", "explicar"),
    "lista": ("lista", "topicos", "tópicos", "carrossel", "enumere", "bullet"),
    "ordene": ("ordene", "ordenar", "ordem", "sequencia", "sequência", "passo a passo", "cronologia", "etapas"),
    "relacione": ("relacione", "relacionar", "associe", "pares", "ligue", "correspondencia", "correspondência"),
    "enquete": ("enquete", "votacao", "votação", "poll", "opiniao", "opinião", "voto"),
}

# Rótulos de linha (`Resposta:`, `Verso:`) e o campo canônico de cada um.
_ROTULOS: dict[str, str] = {
    "resposta": "resposta", "gabarito": "resposta", "resposta certa": "resposta",
    "correta": "resposta", "alternativa correta": "resposta",
    "feedback": "feedback", "por que": "feedback", "porque": "feedback",
    "comentario": "feedback", "comentário": "feedback", "justificativa": "feedback",
    "explicacao": "feedback", "explicação": "feedback",
    "verso": "verso", "atras": "verso", "atrás": "verso", "resposta do card": "verso",
    "frente": "frente", "pergunta": "frente",
    "subtitulo": "subtitulo", "subtítulo": "subtitulo", "linha de apoio": "subtitulo",
    "tag": "tag", "tema": "tag", "assunto": "tag", "materia": "tag", "matéria": "tag", "disciplina": "tag",
    "dica": "dica", "pista": "dica",
    "imagem": "imagem", "figura": "imagem", "foto": "imagem",
    "fonte": "fonte", "referencia": "fonte", "referência": "fonte",
    "cor": "cor", "tema visual": "cor",
    "origem": "origem", "de onde veio": "origem", "visto em": "origem", "revisando": "origem",
    "fecho": "fecho", "depois do voto": "fecho", "resultado": "fecho",
    "tipo": "tipo", "titulo": "titulo", "título": "titulo",
}

# `Cor: roxo` e `Cor: violet` dizem a mesma coisa.
_CORES: dict[str, str] = {
    "cinza": "slate", "grafite": "slate", "slate": "slate", "escuro": "slate",
    "roxo": "violet", "violeta": "violet", "violet": "violet", "lilas": "violet", "lilás": "violet",
    "verde": "emerald", "emerald": "emerald",
    "ambar": "amber", "âmbar": "amber", "amarelo": "amber", "amber": "amber", "laranja": "amber",
    "rosa": "rose", "vermelho": "rose", "rose": "rose", "pink": "rose",
    "azul": "ocean", "oceano": "ocean", "ocean": "ocean", "ciano": "ocean",
}

_VERDADEIROS = ("verdadeiro", "verdade", "v", "certo", "sim", "true", "correto")
_FALSOS = ("falso", "f", "errado", "nao", "não", "no", "false", "mito", "incorreto")

_LETRAS = "abcdefgh"


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------


def chave(texto: str) -> str:
    """`"**Verdadeiro ou Falso**"` -> `"verdadeiro ou falso"`: a forma em que
    dois jeitos de escrever a mesma palavra viram a mesma palavra."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-zA-Z0-9/ ]+", " ", sem_acento).strip().lower()
    return re.sub(r"\s+", " ", limpo)


_TIPO_POR_CHAVE: dict[str, str] = {
    chave(sinonimo): tipo for tipo, sinonimos in _SINONIMOS.items() for sinonimo in sinonimos
}


def tipo_declarado(texto: str) -> str | None:
    """O tipo de card que este pedaço de linha declara, ou `None`."""
    k = chave(texto)
    if k in _TIPO_POR_CHAVE:
        return _TIPO_POR_CHAVE[k]
    # "QUESTÃO 3" e "CARD 2 — FLASHCARD": o número de ordem que quem escreve
    # acrescenta sozinho não pode custar o card.
    sem_numero = re.sub(r"\s*\d+\s*$", "", k).strip()
    sem_prefixo = re.sub(r"^(card|item|bloco)\s*\d*\s*", "", sem_numero).strip()
    for candidato in (sem_numero, sem_prefixo):
        if candidato in _TIPO_POR_CHAVE:
            return _TIPO_POR_CHAVE[candidato]
    return None


def normalizar(texto: str) -> str:
    """Tira do texto tudo que é ruído de cópia, sem tocar no conteúdo.

    Cerca de código (```), traços de separação que os modelos adoram pôr entre
    seções, espaço à direita e a variação de aspas/travessões. O que sobra é o
    mesmo texto, num formato único.
    """
    texto = (texto or "").replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"^\s*```[a-zA-Z]*\s*$", "", texto, flags=re.M)
    texto = re.sub(r"^\s*(?:[-*_]\s*){3,}\s*$", "", texto, flags=re.M)  # ---, ***, ___
    texto = texto.replace(" ", " ").replace("’", "'").replace("“", '"').replace("”", '"')
    linhas = [linha.rstrip() for linha in texto.split("\n")]
    return "\n".join(linhas)


def _sem_negrito(texto: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", texto or "").strip()


def _baralho(semente: str) -> random.Random:
    """Embaralhamento determinístico: recompilar o mesmo texto dá o mesmo
    resultado, byte a byte. Sem isso, a prévia mostraria uma ordem e a
    publicação poria outra no ar."""
    return random.Random(f"sapiens:feed:{semente}")


def _permutacao(n: int, semente: str) -> list[int]:
    """Uma ordem diferente da original sempre que isso for possível — um
    `ordene` que nasce já ordenado é um card sem tarefa."""
    ordem = list(range(n))
    if n < 2:
        return ordem
    baralho = _baralho(semente)
    for _ in range(8):
        baralho.shuffle(ordem)
        if ordem != list(range(n)):
            return ordem
    return ordem[::-1]


# ---------------------------------------------------------------------------
# Fatiar o texto em cards
# ---------------------------------------------------------------------------

_LINHA_HASH = re.compile(r"^\s{0,3}#{1,6}\s*(.+?)\s*$")
_LINHA_COLCHETE = re.compile(r"^\s*\[\s*([^\]]{2,40}?)\s*\]\s*(.*?)\s*$")
_LINHA_CAIXA_ALTA = re.compile(r"^\s*([A-ZÀ-Ý][A-ZÀ-Ý0-9 /]{1,38})\s*$")
_SEPARADOR_DE_TITULO = re.compile(r"^(.*?)(?:\s*[—–:·|]\s*|\s+-\s+)(.*)$")


def _cabecalho(linha: str) -> tuple[str, str] | None:
    """`"## QUESTÃO — Proporcionalidade"` -> `("question", "Proporcionalidade")`.

    Só três formas abrem card: linha de `#`, linha `[TIPO] título` e uma
    palavra de tipo sozinha em caixa alta. A restrição é de propósito — sem
    ela, uma frase do corpo que começasse com "Complete: ..." abriria um card
    no meio da explicação.
    """
    achado = _LINHA_COLCHETE.match(linha)
    if achado:
        tipo = tipo_declarado(achado.group(1))
        if tipo:
            return tipo, _sem_negrito(achado.group(2))
        return None

    bruto = None
    achado = _LINHA_HASH.match(linha)
    if achado:
        bruto = _sem_negrito(achado.group(1))
    elif _LINHA_CAIXA_ALTA.match(linha):
        bruto = linha.strip()
    if bruto is None:
        return None

    tipo = tipo_declarado(bruto)
    if tipo:
        return tipo, ""
    partes = _SEPARADOR_DE_TITULO.match(bruto)
    if partes:
        tipo = tipo_declarado(partes.group(1))
        if tipo:
            return tipo, _sem_negrito(partes.group(2))
    return None


@dataclass
class Pedaco:
    tipo: str
    titulo: str
    corpo: str
    linha: int


def fatiar(texto: str) -> tuple[list[Pedaco], list[str]]:
    """Corta o texto nos cabeçalhos de card. Devolve `(pedaços, avisos)`."""
    linhas = normalizar(texto).split("\n")
    pedacos: list[Pedaco] = []
    avisos: list[str] = []
    atual: Pedaco | None = None
    orfas: list[str] = []
    acumulado: list[str] = []

    for numero, linha in enumerate(linhas, start=1):
        cabecalho = _cabecalho(linha)
        if cabecalho:
            if atual is not None:
                atual.corpo = "\n".join(acumulado).strip()
                pedacos.append(atual)
            atual = Pedaco(tipo=cabecalho[0], titulo=cabecalho[1], corpo="", linha=numero)
            acumulado = []
            continue
        if atual is None:
            if linha.strip():
                orfas.append(linha.strip())
            continue
        acumulado.append(linha)

    if atual is not None:
        atual.corpo = "\n".join(acumulado).strip()
        pedacos.append(atual)

    if orfas:
        avisos.append(
            f"{len(orfas)} linha(s) antes do primeiro card foram ignoradas "
            f"(começa em “{orfas[0][:60]}”). Card só começa numa linha de tipo, "
            "como `## QUESTÃO — título`."
        )
    return pedacos, avisos


# ---------------------------------------------------------------------------
# Ler o corpo de um card
# ---------------------------------------------------------------------------

_ALTERNATIVA = re.compile(r"^\s{0,3}(?:[-*•]\s*)?(?:\*\*)?([A-Ha-h])(?:\*\*)?\s*[\)\.\:\-–—]\s+(.+?)\s*$")
_TOPICO = re.compile(r"^\s{0,3}(?:[-*•]|\d{1,2}[\.\)])\s+(.+?)\s*$")
_SUBTITULO = re.compile(r"^\s{0,3}#{2,6}\s*(.+?)\s*$")
_ROTULO = re.compile(r"^\s{0,3}(?:\*\*)?([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ ]{2,24}?)(?:\*\*)?\s*:\s*\*{0,2}\s*(.*?)\s*$")
_PAR = re.compile(r"^\s{0,3}(?:[-*•]|\d{1,2}[\.\)])?\s*(.+?)\s*(?:<->|->|=>|→|↔|=|\|)\s*(.+?)\s*$")


@dataclass
class Bruto:
    """O corpo do card já classificado, antes de virar card de verdade."""
    rotulos: dict[str, str] = field(default_factory=dict)
    blocos: list[dict] = field(default_factory=list)      # corpo na ordem em que foi escrito
    alternativas: list[tuple[str, str]] = field(default_factory=list)
    itens: list[str] = field(default_factory=list)
    livres: list[str] = field(default_factory=list)       # linhas soltas, para o `relacione`

    @property
    def paragrafos(self) -> list[str]:
        return [b["texto"] for b in self.blocos if b["tipo"] == "texto"]


def ler_corpo(corpo: str) -> Bruto:
    """Classifica linha a linha. Tudo que não é rótulo, alternativa ou tópico
    continua sendo texto — perder um trecho em silêncio é pior que publicá-lo
    fora do lugar."""
    bruto = Bruto()
    paragrafo: list[str] = []
    rotulo_aberto: str | None = None

    def fechar_paragrafo():
        nonlocal paragrafo
        if paragrafo:
            bruto.blocos.append({"tipo": "texto", "texto": " ".join(paragrafo).strip()})
            paragrafo = []

    def abrir_topicos() -> list[str]:
        if not bruto.blocos or bruto.blocos[-1]["tipo"] != "topicos":
            bruto.blocos.append({"tipo": "topicos", "itens": []})
        return bruto.blocos[-1]["itens"]

    for linha in corpo.split("\n"):
        if not linha.strip():
            fechar_paragrafo()
            rotulo_aberto = None
            continue

        achado = _SUBTITULO.match(linha)
        if achado:
            fechar_paragrafo()
            rotulo_aberto = None
            bruto.blocos.append({"tipo": "subtitulo", "texto": _sem_negrito(achado.group(1))})
            continue

        achado = _ALTERNATIVA.match(linha)
        if achado:
            fechar_paragrafo()
            rotulo_aberto = None
            bruto.alternativas.append((achado.group(1).upper(), _sem_negrito(achado.group(2))))
            continue

        achado = _ROTULO.match(linha)
        if achado and chave(achado.group(1)) in _ROTULOS:
            fechar_paragrafo()
            campo = _ROTULOS[chave(achado.group(1))]
            valor = _sem_negrito(achado.group(2))
            anterior = bruto.rotulos.get(campo)
            bruto.rotulos[campo] = f"{anterior} {valor}".strip() if anterior else valor
            rotulo_aberto = campo
            continue

        achado = _TOPICO.match(linha)
        if achado:
            fechar_paragrafo()
            rotulo_aberto = None
            texto = _sem_negrito(achado.group(1))
            bruto.itens.append(texto)
            abrir_topicos().append(texto)
            bruto.livres.append(texto)
            continue

        if rotulo_aberto:
            # Continuação do rótulo anterior: um `**Feedback:**` longo chega
            # quebrado em várias linhas, e cortá-lo na primeira perderia o
            # comentário de metade dos distratores.
            bruto.rotulos[rotulo_aberto] = f"{bruto.rotulos[rotulo_aberto]} {linha.strip()}".strip()
            continue

        paragrafo.append(linha.strip())
        bruto.livres.append(linha.strip())

    fechar_paragrafo()
    return bruto


# ---------------------------------------------------------------------------
# Montar o card
# ---------------------------------------------------------------------------


def id_do_card(tipo: str, corpo_normalizado: str) -> str:
    """O id é o hash do conteúdo, e não um uuid.

    Consequência prática: corrigir um erro de digitação e republicar o texto
    inteiro ATUALIZA aquele card e deixa os outros exatamente como estavam.
    Com uuid, cada publicação criaria um feed inteiro novo e duplicado.
    """
    digest = hashlib.sha1(f"{tipo}\n{corpo_normalizado}".encode("utf-8")).hexdigest()
    return f"fc_{digest[:14]}"


class CardInvalido(ValueError):
    """O card não dá para montar, e adivinhar seria pior do que deixá-lo fora."""


def _tema(bruto: Bruto, tipo: str) -> str:
    declarada = _CORES.get(chave(bruto.rotulos.get("cor", "")))
    return declarada or fc.tema_padrao(tipo)


def _base(pedaco: Pedaco, bruto: Bruto, content_id: str) -> dict:
    meta: dict = {}
    if bruto.rotulos.get("dica"):
        meta["dica"] = bruto.rotulos["dica"]
    if bruto.rotulos.get("fonte"):
        meta["fonte"] = bruto.rotulos["fonte"]

    ativos = []
    if bruto.rotulos.get("imagem"):
        ativos.append({"type": "image", "url": bruto.rotulos["imagem"], "caption": ""})

    return {
        "content_id": content_id,
        "content_type": pedaco.tipo,
        "sequence_order": 0,
        "question_data": {},
        "answer_options": [],
        "explanation_data": {},
        "multimedia_assets": ativos,
        "metadata": meta,
        "cognitive_mapping_reference": "",
        "difficulty_reference": "",
        "learning_objectives": [],
        "background_theme": _tema(bruto, pedaco.tipo),
        "published": True,
    }


def _titulo_e_corpo(pedaco: Pedaco, bruto: Bruto) -> tuple[str, list[dict]]:
    """A manchete do card e o que sobra dela.

    Quando o cabeçalho traz título, ele é a manchete e o corpo inteiro fica.
    Quando não traz, o primeiro parágrafo VIRA a manchete — senão o card
    abriria com a tarja do tipo e nada embaixo.
    """
    titulo = bruto.rotulos.get("titulo") or pedaco.titulo
    blocos = list(bruto.blocos)
    if not titulo:
        primeiro = next((b for b in blocos if b["tipo"] == "texto"), None)
        if primeiro:
            titulo = primeiro["texto"]
            blocos.remove(primeiro)
    return titulo.strip(), blocos


def _enunciado(pedaco: Pedaco, bruto: Bruto) -> str:
    """O enunciado de uma pergunta é o corpo; o título do cabeçalho é assunto."""
    corpo = " ".join(bruto.paragrafos).strip()
    return corpo or bruto.rotulos.get("frente", "").strip() or pedaco.titulo.strip()


def _tag(pedaco: Pedaco, bruto: Bruto, usou_titulo: bool) -> str:
    declarada = bruto.rotulos.get("tag", "").strip()
    if declarada:
        return declarada
    return "" if usou_titulo else pedaco.titulo.strip()


def _card_de_leitura(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    titulo, blocos = _titulo_e_corpo(pedaco, bruto)
    if not titulo:
        raise CardInvalido("card de texto sem nada escrito")
    card["question_data"] = {
        "prompt": titulo,
        "subtitle": bruto.rotulos.get("subtitulo", ""),
        "subject_hint": _tag(pedaco, bruto, usou_titulo=True),
        "corpo": blocos,
    }
    if bruto.rotulos.get("verso"):
        card["explanation_data"] = {"text": bruto.rotulos["verso"]}
    return card


def _card_de_lista(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    if len(bruto.itens) < 2:
        raise CardInvalido("lista com menos de dois tópicos — escreva cada item numa linha com `- `")
    titulo, _ = _titulo_e_corpo(pedaco, bruto)
    itens = []
    for item in bruto.itens:
        partes = re.match(r"^(.{2,60}?)\s*[:—–]\s+(.+)$", item)
        if partes:
            itens.append({"titulo": _sem_negrito(partes.group(1)), "detalhe": partes.group(2)})
        else:
            itens.append({"titulo": item, "detalhe": ""})
    # A introdução da lista é o que estiver escrito ANTES dos tópicos.
    intro = next((b["texto"] for b in bruto.blocos if b["tipo"] == "texto"), "")
    card["question_data"] = {
        "prompt": titulo or intro or "Lista",
        "subtitle": bruto.rotulos.get("subtitulo", "") or (intro if titulo else ""),
        "subject_hint": _tag(pedaco, bruto, usou_titulo=True),
        "corpo": [],
    }
    card["metadata"]["itens"] = itens
    return card


def _card_de_escolha(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    """Questão e Complete: alternativas embaralhadas, feedback repartido."""
    enunciado = _enunciado(pedaco, bruto)
    if not enunciado:
        raise CardInvalido("questão sem enunciado")
    if len(bruto.alternativas) < 2:
        raise CardInvalido("questão com menos de duas alternativas (escreva `A) ...` numa linha cada)")

    marcada = chave(bruto.rotulos.get("resposta", "")).upper()
    letras = [letra for letra, _ in bruto.alternativas]
    if not marcada:
        raise CardInvalido("sem `**Resposta:**` — não há gabarito para corrigir")
    escolhida = next(
        (l for l in letras if marcada == l or marcada.startswith(f"{l} ")), None,
    )
    if escolhida is None:
        raise CardInvalido(
            f"a resposta {bruto.rotulos.get('resposta')!r} não é nenhuma das "
            f"alternativas ({', '.join(letras)})"
        )

    ids_originais = [letra.lower() for letra in letras]
    por_alternativa, explicacao = repartir_feedback(bruto.rotulos.get("feedback", ""), ids_originais)

    ordem = _permutacao(len(bruto.alternativas), card["content_id"])
    de_origem_para_posicao = {
        bruto.alternativas[i][0].lower(): _LETRAS[pos] for pos, i in enumerate(ordem)
    }
    certa = de_origem_para_posicao[escolhida.lower()]
    opcoes = []
    for pos, i in enumerate(ordem):
        letra_original, texto = bruto.alternativas[i]
        opcoes.append({
            "key": _LETRAS[pos],
            "label": texto,
            "is_correct": _LETRAS[pos] == certa,
            "feedback": por_alternativa.get(letra_original.lower(), ""),
        })

    if pedaco.tipo == "complete":
        enunciado = re.sub(r"_{2,}", "___", enunciado)

    card["question_data"] = {
        "prompt": enunciado,
        "subtitle": "",
        "subject_hint": _tag(pedaco, bruto, usou_titulo=False),
        "corpo": [],
    }
    card["answer_options"] = opcoes
    card["explanation_data"] = {"text": explicacao or bruto.rotulos.get("feedback", "")}
    return card


def _card_de_desafio(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    """O Desafio dos dois jeitos que fazem sentido num feed que se desliza:

    **Com alternativas**, é uma pergunta igual às outras — só a tarja e o tema
    mudam (mais difícil, mais chamativo). Reaproveita `_card_de_escolha`
    inteira: mesmo embaralhamento, mesmo feedback por distrator.

    **Sem alternativas**, é resposta curta ou numérica, digitada — o mesmo
    formato do desafio final dos cursos (`cursos_ingestao.bloco_de_desafio`),
    reaproveitado aqui em vez de reinventado: `como_numero` decide se a
    resposta é um número com tolerância, e `variantes_aceitas` cobre as formas
    de escrever a mesma resposta curta (`2×10⁵`, `2x10^5`, `200000`...). Uma
    resposta em prosa não dá para corrigir sozinha e é recusada — publicar um
    gabarito adivinhado é pior que não publicar.
    """
    if bruto.alternativas:
        return _card_de_escolha(pedaco, bruto, card)

    enunciado = _enunciado(pedaco, bruto)
    if not enunciado:
        raise CardInvalido("desafio sem enunciado")
    resposta = bruto.rotulos.get("resposta", "").strip()
    if not resposta:
        raise CardInvalido("sem `**Resposta:**` — desafio de resposta aberta precisa de gabarito")

    numero = como_numero(resposta)
    meta: dict = {"resposta_exibicao": resposta}
    if numero is not None:
        valor, unidade = numero
        meta["numero"] = {"valor": valor, "tolerancia": max(0.01, abs(valor) * 0.001)}
        if unidade:
            meta["unidade"] = unidade
        meta["aceitos"] = variantes_aceitas(resposta)
    elif len(resposta) <= 40:
        meta["aceitos"] = variantes_aceitas(resposta)
    else:
        raise CardInvalido(
            "resposta em prosa não dá para corrigir sozinha — escreva a resposta "
            "como número ou como uma expressão curta, ou acrescente alternativas "
            "(`A) ...`, `B) ...`) para virar múltipla escolha"
        )

    card["formato"] = "aberto"
    card["question_data"] = {
        "prompt": enunciado,
        "subtitle": bruto.rotulos.get("subtitulo", ""),
        "subject_hint": _tag(pedaco, bruto, usou_titulo=False),
        "corpo": [],
    }
    card["metadata"].update(meta)
    _, explicacao = repartir_feedback(bruto.rotulos.get("feedback", ""), [])
    card["explanation_data"] = {"text": explicacao or bruto.rotulos.get("feedback", "")}
    return card


def _card_de_verdadeiro_falso(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    afirmacao = _enunciado(pedaco, bruto)
    if not afirmacao:
        raise CardInvalido("verdadeiro ou falso sem a afirmação")
    veredito = chave(bruto.rotulos.get("resposta", ""))
    if veredito.split(" ")[0] in _VERDADEIROS:
        certa = "v"
    elif veredito.split(" ")[0] in _FALSOS:
        certa = "f"
    else:
        raise CardInvalido("`**Resposta:**` precisa ser `verdadeiro` ou `falso`")

    _, explicacao = repartir_feedback(bruto.rotulos.get("feedback", ""), [])
    card["question_data"] = {
        "prompt": afirmacao,
        "subtitle": "",
        "subject_hint": _tag(pedaco, bruto, usou_titulo=False),
        "corpo": [],
    }
    card["answer_options"] = [
        {"key": "v", "label": "Verdadeiro", "is_correct": certa == "v", "feedback": ""},
        {"key": "f", "label": "Falso", "is_correct": certa == "f", "feedback": ""},
    ]
    card["explanation_data"] = {"text": explicacao or bruto.rotulos.get("feedback", "")}
    return card


def _card_de_memoria(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    """Flashcard e Revisão: uma frente, um verso e um julgamento honesto.

    A FRENTE é o parágrafo do corpo quando ele existe — "## FLASHCARD —
    Trabalho de uma força" seguido de "Qual a fórmula...?" tem um TÍTULO
    (o assunto, que vira tag) e uma PERGUNTA (o que aparece na tela); usar o
    título como frente perderia a pergunta de verdade em silêncio. Só quando
    não há parágrafo nenhum o título do cabeçalho vira a própria frente.
    """
    corpo = " ".join(bruto.paragrafos).strip()
    frente = bruto.rotulos.get("frente", "").strip() or corpo or pedaco.titulo.strip()
    verso = bruto.rotulos.get("verso", "").strip() or bruto.rotulos.get("resposta", "").strip()
    if not verso:
        # Sem rótulo, o último parágrafo é o verso — é assim que a maioria das
        # pessoas escreve um flashcard à mão.
        paragrafos = bruto.paragrafos
        if len(paragrafos) >= 2:
            verso = paragrafos[-1]
            frente = frente if frente != paragrafos[-1] else paragrafos[0]
    if not frente:
        raise CardInvalido("flashcard sem frente")
    if not verso:
        raise CardInvalido("flashcard sem verso — escreva `Verso:` com a resposta")

    card["question_data"] = {
        "prompt": frente,
        "subtitle": bruto.rotulos.get("subtitulo", ""),
        # Se a frente É o título do cabeçalho, ele não pode virar tag também —
        # seria a mesma frase duas vezes na mesma tela.
        "subject_hint": _tag(pedaco, bruto, usou_titulo=(frente == pedaco.titulo)),
        "corpo": [],
    }
    card["explanation_data"] = {
        "text": verso,
        "subtitle": bruto.rotulos.get("feedback", ""),
        "origem": bruto.rotulos.get("origem", ""),
    }
    return card


def _card_de_ordem(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    if len(bruto.itens) < 3:
        raise CardInvalido("ordenar precisa de pelo menos três passos, um por linha com `- `")
    titulo, _ = _titulo_e_corpo(pedaco, bruto)
    intro = next((b["texto"] for b in bruto.blocos if b["tipo"] == "texto"), "")
    passos = [{"id": f"p{i + 1}", "texto": texto} for i, texto in enumerate(bruto.itens)]
    ordem = _permutacao(len(passos), card["content_id"])

    card["question_data"] = {
        "prompt": intro or titulo or "Coloque na ordem certa",
        "subtitle": bruto.rotulos.get("subtitulo", ""),
        "subject_hint": _tag(pedaco, bruto, usou_titulo=bool(intro)),
        "corpo": [],
    }
    card["metadata"]["passos"] = passos
    card["metadata"]["ordem_exibida"] = [passos[i]["id"] for i in ordem]
    card["explanation_data"] = {"text": bruto.rotulos.get("feedback", "")}
    return card


def _card_de_pares(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    pares: list[dict] = []
    for linha in bruto.livres:
        achado = _PAR.match(linha)
        if achado:
            pares.append({
                "id": f"p{len(pares) + 1}",
                "esquerda": _sem_negrito(achado.group(1)),
                "direita": _sem_negrito(achado.group(2)),
            })
    if len(pares) < 2:
        raise CardInvalido("relacionar precisa de pelo menos dois pares, escritos como `termo = definição`")

    ordem = _permutacao(len(pares), card["content_id"])
    for posicao, indice in enumerate(ordem):
        pares[indice]["direita_id"] = f"d{posicao + 1}"

    titulo = bruto.rotulos.get("titulo") or pedaco.titulo
    card["question_data"] = {
        "prompt": titulo or "Relacione as colunas",
        "subtitle": bruto.rotulos.get("subtitulo", ""),
        "subject_hint": _tag(pedaco, bruto, usou_titulo=True),
        "corpo": [],
    }
    card["metadata"]["pares"] = pares
    card["metadata"]["direita_exibida"] = [f"d{i + 1}" for i in range(len(pares))]
    card["explanation_data"] = {"text": bruto.rotulos.get("feedback", "")}
    return card


def _card_de_enquete(pedaco: Pedaco, bruto: Bruto, card: dict) -> dict:
    pergunta = _enunciado(pedaco, bruto)
    opcoes = bruto.alternativas or [(chr(65 + i), t) for i, t in enumerate(bruto.itens)]
    if not pergunta:
        raise CardInvalido("enquete sem pergunta")
    if len(opcoes) < 2:
        raise CardInvalido("enquete com menos de duas opções")

    card["question_data"] = {
        "prompt": pergunta,
        "subtitle": bruto.rotulos.get("subtitulo", ""),
        "subject_hint": _tag(pedaco, bruto, usou_titulo=False),
        "corpo": [],
    }
    card["answer_options"] = [
        {"key": _LETRAS[i], "label": texto, "is_correct": False, "feedback": ""}
        for i, (_, texto) in enumerate(opcoes)
    ]
    card["metadata"]["fecho"] = bruto.rotulos.get("fecho", "")
    card["metadata"]["votos"] = {}
    return card


_MONTADORES = {
    "question": _card_de_escolha,
    "flashcard": _card_de_memoria,
    "verdadeiro_falso": _card_de_verdadeiro_falso,
    "complete": _card_de_escolha,
    "desafio": _card_de_desafio,
    "insight": _card_de_leitura,
    "revisao": _card_de_memoria,
    "explanation": _card_de_leitura,
    "lista": _card_de_lista,
    "ordene": _card_de_ordem,
    "relacione": _card_de_pares,
    "enquete": _card_de_enquete,
}


def montar(pedaco: Pedaco) -> dict:
    """Um pedaço de texto vira um card completo, ou levanta `CardInvalido`."""
    bruto = ler_corpo(pedaco.corpo)
    # `Tipo:` escrito no corpo vence o cabeçalho: é o escape de quem colou
    # o card com o cabeçalho errado e não quer reescrever o texto inteiro.
    declarado = tipo_declarado(bruto.rotulos["tipo"]) if bruto.rotulos.get("tipo") else None
    if declarado:
        pedaco = Pedaco(tipo=declarado, titulo=pedaco.titulo, corpo=pedaco.corpo, linha=pedaco.linha)

    content_id = id_do_card(pedaco.tipo, f"{pedaco.titulo}\n{pedaco.corpo}".strip())
    card = _base(pedaco, bruto, content_id)
    montador = _MONTADORES.get(pedaco.tipo)
    if montador is None:
        raise CardInvalido(f"tipo {pedaco.tipo!r} não tem montador")
    return montador(pedaco, bruto, card)


# ---------------------------------------------------------------------------
# A compilação inteira
# ---------------------------------------------------------------------------


@dataclass
class Compilado:
    cards: list[dict] = field(default_factory=list)
    problemas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def pode_publicar(self) -> bool:
        return bool(self.cards) and not self.problemas


def compilar(texto: str) -> Compilado:
    """Texto colado -> cards prontos para publicar.

    Tolerante por decisão: card que não monta vira AVISO nominal e o lote
    continua. O texto só é recusado quando não sobrou card nenhum — aí não há
    o que pôr no ar.
    """
    pedacos, avisos = fatiar(texto)
    resultado = Compilado(avisos=list(avisos))

    if not pedacos:
        resultado.problemas.append(
            "Nenhum card encontrado. Cada card começa com uma linha de tipo, "
            "como `## QUESTÃO — título` ou `## FLASHCARD`."
        )
        return resultado

    vistos: dict[str, int] = {}
    for pedaco in pedacos:
        rotulo = f"linha {pedaco.linha} ({fc.nome_do_tipo(pedaco.tipo)}{f' — {pedaco.titulo}' if pedaco.titulo else ''})"
        try:
            card = montar(pedaco)
        except CardInvalido as erro:
            resultado.avisos.append(f"{rotulo}: ficou de fora — {erro}")
            continue
        except Exception as erro:  # pragma: no cover - rede de segurança
            resultado.avisos.append(f"{rotulo}: ficou de fora — erro inesperado ({erro})")
            continue

        # Card repetido letra por letra: o id seria o mesmo e o segundo
        # engoliria o primeiro sem ninguém perceber.
        if card["content_id"] in vistos:
            vistos[card["content_id"]] += 1
            resultado.avisos.append(
                f"{rotulo}: idêntico a um card anterior do mesmo texto — publicado uma vez só."
            )
            continue
        vistos[card["content_id"]] = 1

        problemas = fc.validar_card(card)
        if problemas:
            resultado.avisos.append(f"{rotulo}: ficou de fora — {problemas[0]}")
            continue

        card["sequence_order"] = len(resultado.cards) + 1
        resultado.cards.append(card)

    if not resultado.cards:
        resultado.problemas.append(
            f"Nenhum dos {len(pedacos)} card(s) do texto pôde ser publicado. "
            "Os avisos abaixo dizem o que consertar."
        )
    return resultado
