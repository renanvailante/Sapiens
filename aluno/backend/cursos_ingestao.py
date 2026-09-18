"""O COMPILADOR DE CURSO: texto cru entra, estação publicável sai.

Quem escreve um curso escreve **texto** — a explicação, os exemplos, as
questões com as alternativas, a resposta certa e o porquê dela. O produto
serve **blocos tipados** validados pelo contrato de `cursos_conteudo`. Este
módulo é a ponte entre os dois, e é a única implementação dela: o script
`scripts/ingerir_curso_markdown.py` (que publica o markdown de autoria em
arquivo) e o painel do admin (que publica texto colado, na hora) chamam as
MESMAS funções. Dois parsers do mesmo formato divergiriam em um mês, e a
divergência apareceria como "a estação que eu publiquei ficou diferente".

O que o compilador transforma, e o que ele se recusa a adivinhar
----------------------------------------------------------------
1. **Tabela vira bloco `tabela`.** O subconjunto de markdown do curso não tem
   tabela de propósito; o que passa dele vira TIPO DE BLOCO.
2. **O feedback é repartido por alternativa.** No texto ele é um parágrafo só
   ("A multiplicação vem antes. B soma primeiro. C ignora o 4."): a explicação
   da conta certa vira `solucao` e cada comentário vira o `feedback` DAQUELA
   alternativa — a frase que responde "por que a MINHA conta deu isso".
3. **As alternativas são embaralhadas**, com semente fixa no id da questão.
   Quem escreve tende a pôr a resposta certa em A; publicado assim, o curso
   ensina a clicar na primeira opção. Determinístico: recompilar o mesmo texto
   dá exatamente o mesmo JSON.
4. **O id da alternativa é a POSIÇÃO na tela, nunca a letra do original.** O
   id viaja para o navegador; se fosse a letra, o gabarito estaria escrito no
   HTML.
5. **Nada de preço, nada de gabarito inventado.** Resposta que não é nem
   número nem texto curto PARA a compilação daquele desafio com uma mensagem,
   em vez de publicar um gabarito que ninguém conferiu.

O formato aceito é o do material de autoria, e é FROUXO de propósito
-------------------------------------------------------------------
    ---
    station_id: 01
    title: "Operações fundamentais"
    ---
    # Estação 01 — Operações fundamentais
    ## Objetivo
    Ao final desta estação, você saberá ...
    ## Conteúdo
    ...
    ## Exemplos resolvidos
    **Exemplo 1.** `7 + 3 × 4`
    - Multiplicação primeiro: `3 × 4 = 12`
    ## Exercícios
    ### Questão 1
    Calcule `6 + 4 × 5`.
    A) 50
    B) 26
    **Resposta:** B
    **Feedback:** A multiplicação vem antes da soma. A alternativa A soma primeiro.
    ## Desafio final
    ...
    **Resposta:** 44

`normalizar()` aceita as variações que aparecem quando alguém cola texto de
outro lugar: `Gabarito:` no lugar de `Resposta:`, `Por quê:` no lugar de
`Feedback:`, questão em `##` ou em negrito, seção de exercícios sem título.
Toda seção que o compilador não reconhece vira bloco de texto com o título
dela — perder um trecho de aula em silêncio seria pior que publicá-lo fora
do lugar.

Puro: não fala com banco, não conhece aluno e não escreve arquivo. Quem
persiste é `cursos_publicados` (admin) ou o script (arquivo em git).
"""
from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

SCHEMA_VERSION = "1.0"

# `difficulty` do material -> `nivel` (1-5) do contrato. Aceita o vocabulário
# em inglês do material de autoria, o em português de quem escreve à mão e o
# número cru — três formas de dizer a mesma coisa, e nenhuma delas vale um
# erro de publicação.
NIVEL_POR_DIFICULDADE = {
    "basic": 1, "beginner": 1, "básico": 1, "basico": 1, "facil": 1, "fácil": 1,
    "intermediate": 2, "intermediário": 2, "intermediario": 2, "medio": 2, "médio": 2,
    "advanced": 3, "avançado": 3, "avancado": 3, "dificil": 3, "difícil": 3,
    "transfer": 4, "applied": 4, "aplicado": 4, "transferencia": 4, "transferência": 4,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
}
NIVEL_DO_DESAFIO = 5

# Quanto tempo a estação leva. É ESTIMATIVA declarada, não medida: 180
# palavras por minuto de leitura, um minuto por exercício.
PALAVRAS_POR_MINUTO = 180
MINUTOS_MIN, MINUTOS_MAX = 8, 25

# 70% e não 100%: dez exercícios obrigatórios por estação fariam de cada uma um
# muro, e o que sobra não some — vira prática de quem quiser.
FRACAO_PARA_CONCLUIR = 0.7


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------


def slug(texto: str) -> str:
    """`"Notação científica"` -> `"notacao-cientifica"`, no formato de id que o
    contrato exige (minúsculas, números e hífen)."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-").lower()
    return re.sub(r"-{2,}", "-", limpo)


def frontmatter(bruto: str) -> tuple[dict, str]:
    """Lê o bloco `---` do topo. Subconjunto de YAML deliberado: `chave: valor`
    e listas de `- item`. Nada mais aparece nestes arquivos, e uma dependência
    de YAML para ler doze linhas seria uma dependência a manter para sempre."""
    if not bruto.startswith("---"):
        return {}, bruto
    fim = bruto.find("\n---", 3)
    if fim == -1:
        return {}, bruto
    cabeca, corpo = bruto[3:fim], bruto[fim + 4:]

    dados: dict = {}
    chave_de_lista: str | None = None
    for linha in cabeca.splitlines():
        if not linha.strip():
            continue
        if linha.lstrip().startswith("- ") and chave_de_lista:
            dados[chave_de_lista].append(linha.lstrip()[2:].strip().strip('"'))
            continue
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        chave, valor = chave.strip(), valor.strip().strip('"')
        if valor in ("", "[]"):
            dados[chave] = []
            chave_de_lista = chave if valor == "" else None
            if valor == "[]":
                chave_de_lista = None
        else:
            dados[chave] = valor
            chave_de_lista = None
    return dados, corpo.lstrip("\n")


def secoes(corpo: str) -> dict[str, str]:
    """`## Título` -> texto da seção. Preserva a ordem de aparição."""
    partes: dict[str, str] = {}
    atual: str | None = None
    acumulado: list[str] = []
    def guardar(nome: str, conteudo: list[str]) -> None:
        # Título repetido SOMA. Um texto com dois `## Exercícios` é comum
        # (uma leva antes do desafio, outra depois); sobrescrever o primeiro
        # apagaria metade das questões sem erro nenhum.
        texto = "\n".join(conteudo).strip()
        if not texto:
            partes.setdefault(nome, "")
            return
        partes[nome] = f"{partes[nome]}\n\n{texto}" if partes.get(nome) else texto

    for linha in corpo.splitlines():
        if linha.startswith("## "):
            if atual is not None:
                guardar(atual, acumulado)
            atual = linha[3:].strip()
            acumulado = []
        elif atual is not None:
            acumulado.append(linha)
    if atual is not None:
        guardar(atual, acumulado)
    return partes


def sem_letra(texto: str) -> str:
    """Primeira letra maiúscula e ponto final — um fragmento de feedback que
    perdeu a letra da alternativa ("B soma primeiro" -> "Soma primeiro.")."""
    t = texto.strip()
    if not t:
        return t
    t = t[0].upper() + t[1:]
    if t[-1] not in ".!?":
        t += "."
    return t


# ---------------------------------------------------------------------------
# Blocos de conteúdo: texto e tabela
# ---------------------------------------------------------------------------

_LINHA_DE_TABELA = re.compile(r"^\s*\|.*\|\s*$")
_SEPARADOR_DE_TABELA = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def _celulas(linha: str) -> list[str]:
    """Divide a linha nas barras que separam células — e só nelas.

    A barra dentro de crases é conteúdo, não separador: `√(a²) = |a|` é uma
    célula só, e um `split("|")` ingênuo a parte em três e desalinha a tabela
    inteira. O contador de crases resolve porque o subconjunto de markdown não
    tem escape: dentro de código, tudo é literal.
    """
    celulas: list[str] = []
    atual: list[str] = []
    dentro_de_codigo = False
    for char in linha.strip().strip("|"):
        if char == "`":
            dentro_de_codigo = not dentro_de_codigo
        if char == "|" and not dentro_de_codigo:
            celulas.append("".join(atual).strip())
            atual = []
        else:
            atual.append(char)
    celulas.append("".join(atual).strip())
    return celulas


def fatiar_tabelas(texto: str) -> list[tuple[str, object]]:
    """Separa um trecho em pedaços de `("texto", str)` e `("tabela", dict)`.

    Uma tabela de markdown não cabe no subconjunto que a tela renderiza, e
    fingir que cabe produziria um parágrafo com barras verticais no meio. Aqui
    ela vira dado estruturado — colunas e linhas — e o bloco `tabela` a
    desenha do outro lado.
    """
    pedacos: list[tuple[str, object]] = []
    buffer: list[str] = []
    linhas = texto.splitlines()
    i = 0

    def descarregar():
        if buffer and "".join(buffer).strip():
            pedacos.append(("texto", "\n".join(buffer).strip()))
        buffer.clear()

    while i < len(linhas):
        linha = linhas[i]
        tabela_aqui = (
            _LINHA_DE_TABELA.match(linha)
            and i + 1 < len(linhas)
            and _SEPARADOR_DE_TABELA.match(linhas[i + 1])
        )
        if not tabela_aqui:
            buffer.append(linha)
            i += 1
            continue

        descarregar()
        colunas = _celulas(linha)
        i += 2
        corpo: list[list[str]] = []
        while i < len(linhas) and _LINHA_DE_TABELA.match(linhas[i]):
            corpo.append(_celulas(linhas[i]))
            i += 1
        pedacos.append(("tabela", {"colunas": colunas, "linhas": corpo}))

    descarregar()
    return pedacos


def blocos_de_texto(conteudo: str, prefixo: str, variante: str = "padrao") -> list[dict]:
    """Uma seção do markdown vira uma sequência de blocos `texto`/`tabela`.

    O corte é por `###`: cada subtítulo do original vira um bloco com título
    próprio, porque a estação é lida rolando e um bloco de 40 linhas é uma
    parede. Sem subtítulo nenhum, a seção inteira vira um bloco só.
    """
    partes: list[tuple[str | None, str]] = []
    titulo: str | None = None
    acumulado: list[str] = []
    for linha in conteudo.splitlines():
        if linha.startswith("### "):
            if acumulado and "".join(acumulado).strip():
                partes.append((titulo, "\n".join(acumulado).strip()))
            titulo = linha[4:].strip()
            acumulado = []
        else:
            acumulado.append(linha)
    if acumulado and "".join(acumulado).strip():
        partes.append((titulo, "\n".join(acumulado).strip()))

    blocos: list[dict] = []
    n = 0
    for titulo_da_parte, texto in partes:
        primeiro_do_grupo = True
        for tipo, carga in fatiar_tabelas(texto):
            n += 1
            bloco_id = f"{prefixo}-{n:02d}"
            if tipo == "tabela":
                bloco = {"tipo": "tabela", "bloco_id": bloco_id, **carga}
                if primeiro_do_grupo and titulo_da_parte:
                    bloco["titulo"] = titulo_da_parte
                    primeiro_do_grupo = False
                blocos.append(bloco)
                continue
            bloco = {
                "tipo": "texto",
                "bloco_id": bloco_id,
                "variante": variante,
                "markdown": carga,
            }
            if primeiro_do_grupo and titulo_da_parte:
                bloco["titulo"] = titulo_da_parte
                primeiro_do_grupo = False
            blocos.append(bloco)
    return blocos


# ---------------------------------------------------------------------------
# Exemplos resolvidos
# ---------------------------------------------------------------------------

# O começo de um exemplo resolvido. Duas formas, e a primeira existe por um
# erro que custou conteúdo: a regra antiga era `^\*\*Exemplo\s+\d+\.?\*\*`, que
# não reconhece `**Exemplo 1 (direta).**` — e a seção inteira de exemplos da
# estação de regra de três foi publicada VAZIA, sem erro nenhum, porque um
# exemplo que não casa simplesmente não vira bloco. Agora o cabeçalho em
# negrito termina onde o negrito termina, seja lá o que ele diga no meio.
_EXEMPLO_NEGRITO = re.compile(r"^\*\*\s*Exemplo\b[^*]*\*\*[\s.:—–-]*(.*)$", re.IGNORECASE)
_EXEMPLO_SIMPLES = re.compile(r"^Exemplo\s*\d*[^\w\n]*[\.:—–-]\s*(.*)$", re.IGNORECASE)


def cabeca_de_exemplo(linha: str) -> str | None:
    """O enunciado, se esta linha abre um exemplo resolvido. Senão, `None`."""
    for regra in (_EXEMPLO_NEGRITO, _EXEMPLO_SIMPLES):
        achado = regra.match(linha)
        if achado:
            return achado.group(1).strip()
    return None


def blocos_de_exemplo(conteudo: str, prefixo: str) -> list[dict]:
    """`**Exemplo 1.** <enunciado>` seguido de `- passo` vira um bloco
    `exemplo`, que é o modelo resolvido — enunciado, passos numerados e fecho.
    """
    blocos: list[dict] = []
    atual: dict | None = None

    for linha in conteudo.splitlines():
        cabeca = cabeca_de_exemplo(linha.strip())
        if cabeca is not None:
            if atual and atual["passos"]:
                blocos.append(atual)
            atual = {
                "tipo": "exemplo",
                "bloco_id": f"{prefixo}-{len(blocos) + 1:02d}",
                "enunciado": cabeca,
                "passos": [],
            }
            continue
        if atual is None:
            continue
        crua = linha.strip()
        if crua.startswith("- "):
            atual["passos"].append({"texto": crua[2:].strip()})
        elif crua and atual["passos"]:
            # Linha solta depois dos passos: é o fecho do exemplo, o que se
            # generaliza dele.
            atual["fecho"] = ((atual.get("fecho", "") + " ") + crua).strip()
        elif crua:
            atual["enunciado"] = (atual["enunciado"] + " " + crua).strip()

    if atual and atual["passos"]:
        blocos.append(atual)
    return blocos


# ---------------------------------------------------------------------------
# Exercícios
# ---------------------------------------------------------------------------

# As marcas de uma questão. Frouxas de propósito: quem cola o enunciado de
# outro lugar escreve `Gabarito:` ou `Por quê:`, com e sem negrito, com e sem
# parêntese na letra. Recusar a variação obrigaria a reformatar o material à
# mão — que é exatamente o trabalho que este módulo existe para não pedir.
# `- A) 50`, `**A)** 50`, `(a) 50`, `A - 50`: a mesma alternativa escrita de
# cinco jeitos. O marcador de lista e o negrito à frente são ruído de quem
# colou de outro lugar, não informação.
_ALTERNATIVA = re.compile(r"^(?:[-*\u2022]\s*)?\*{0,2}\(?([A-Ha-h])\)?\*{0,2}\s*[\)\.:\-–]\s*(.+)$")
# Os dois-pontos são OBRIGATÓRIOS, e isto não é rigor gratuito: com eles
# opcionais, o enunciado "Por que um gráfico que começa em 90 distorce a
# leitura?" era lido como a linha de feedback da questão — e a questão ia para
# o ar sem enunciado nenhum. A marca precisa ser inconfundível; uma frase que
# por acaso começa com "Por que" não é uma.
_MARCA = r"\s*\*{0,2}\s*:\s*\*{0,2}\s*"
_RESPOSTA = re.compile(
    r"^\*{0,2}\s*(?:Resposta|Gabarito)(?:\s+correta)?" + _MARCA + r"(.+?)\s*\*{0,2}\s*$",
    re.IGNORECASE,
)
_FEEDBACK = re.compile(
    r"^\*{0,2}\s*(?:Feedback|Coment[áa]rio|Explica[çc][ãa]o|Justificativa|Por\s*qu[eê])"
    + _MARCA + r"(.+)$",
    re.IGNORECASE,
)
# A questão dissertativa: sem alternativas, corrigida pela Mentis. As marcas
# são as que quem escreve usa sem ser ensinado — "Critérios de correção:",
# "Resposta esperada:", "Tipo: dissertativa".
_CRITERIOS = re.compile(
    r"^\*{0,2}\s*Crit[ée]rios?(?:\s+de\s+corre[çc][ãa]o)?" + _MARCA + r"(.*)$",
    re.IGNORECASE,
)
_REFERENCIA = re.compile(
    r"^\*{0,2}\s*(?:Resposta\s+esperada|Espera-se|Resposta\s+modelo|Refer[êe]ncia)"
    + _MARCA + r"(.+)$",
    re.IGNORECASE,
)
_TIPO = re.compile(r"^\*{0,2}\s*(?:Tipo|Formato)" + _MARCA + r"(.+?)\s*\*{0,2}\s*$", re.IGNORECASE)
_ITEM_DE_LISTA = re.compile(r"^[-*\u2022]\s+(.+)$")

_META = re.compile(
    r"^\*{0,2}\s*(question_id|id|difficulty|dificuldade|n[íi]vel|nivel|skill|habilidade|conceito)"
    + _MARCA + r"(.+?)\s*\*{0,2}\s*$",
    re.IGNORECASE,
)
# O nome que cada sinônimo tem DENTRO da questão. Um mapa explícito, e não um
# `setattr` no que veio do texto: campo inventado por quem escreve não vira
# atributo silencioso de um objeto do produto.
_CAMPO_DA_META = {
    "question_id": "question_id", "id": "question_id",
    "difficulty": "difficulty", "dificuldade": "difficulty",
    "nível": "difficulty", "nivel": "difficulty",
    "skill": "skill", "habilidade": "skill", "conceito": "skill",
}
# O começo de uma questão: `### Questão 1`, `#### 1`, ou a linha em negrito
# que `normalizar()` ainda não promoveu.
_CABECA_DE_QUESTAO = re.compile(r"^#{3,6}\s+(.+)$")

# Um "período" do feedback. O corte exige espaço depois do ponto, o que deixa
# `1.000` e `4,900` inteiros — separador de milhar em português é ponto, e
# cortar neles picaria toda conta do curso.
_PERIODO = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú`*])")

# Como uma frase de feedback aponta para uma alternativa. A ordem é a
# precedência; a última regra NÃO aceita `A` sozinho de propósito: no corpus
# inteiro, `A` no começo de frase é sempre o artigo ("A multiplicação vem
# antes"), e a referência de verdade à alternativa A vem sempre escrita por
# extenso ("A alternativa A corresponde a…", "A resposta B também está…").
_REFERENCIAS = (
    re.compile(r"^A[s]?\s+(?:alternativas?|respostas?|opç[õo]es?|opção)\s+([A-H])(?:\s*,\s*([A-H]))*\s+e\s+([A-H])\b[\s,:]*"),
    re.compile(r"^A[s]?\s+(?:alternativa|resposta|opção)\s+([A-H])\b[\s,:]*"),
    re.compile(r"^([A-H])(?:\s*,\s*([A-H]))*\s+e\s+([A-H])\b[\s,:]*"),
    re.compile(r"^([B-H])\b\s+(?=[a-zà-ú])"),
)


def repartir_feedback(texto: str, ids: list[str]) -> tuple[dict[str, str], str]:
    """Separa a explicação da conta certa dos comentários de cada distrator.

    No markdown os dois vêm no mesmo parágrafo. No produto eles têm destinos
    diferentes e momentos diferentes: a explicação é a `solucao` (que o aluno
    recebe ao acertar, ou no terceiro erro), e cada comentário é o `feedback`
    da alternativa que ele escolheu — a frase que responde "por que a MINHA
    conta deu isso", que é a única devolutiva que ensina alguma coisa.

    Devolve `({id_da_alternativa: comentário}, explicação)`. A letra some do
    texto: é o que permite embaralhar as alternativas sem que o feedback passe
    a mentir sobre a posição delas.
    """
    por_alternativa: dict[str, str] = {}
    explicacao: list[str] = []

    for frase in _PERIODO.split(texto.strip()):
        frase = frase.strip()
        if not frase:
            continue
        for regra in _REFERENCIAS:
            achado = regra.match(frase)
            if not achado:
                continue
            letras = [g for g in achado.groups() if g]
            resto = frase[achado.end():].strip()
            if not resto:
                break
            # Frase que cobre várias alternativas de uma vez ("C e D ignoram
            # a interseção") vai para TODAS elas, e o verbo no plural ganha um
            # sujeito: sem isso o aluno que escolheu C leria "Ignoram a
            # interseção." e teria de adivinhar quem são os outros.
            for letra in letras:
                chave = letra.lower()
                if chave not in ids:
                    continue
                if len(letras) > 1:
                    comentario = sem_letra("esta é uma das que " + resto[0].lower() + resto[1:])
                else:
                    comentario = sem_letra(resto)
                anterior = por_alternativa.get(chave)
                por_alternativa[chave] = f"{anterior} {comentario}".strip() if anterior else comentario
            break
        else:
            explicacao.append(frase)

    return por_alternativa, " ".join(explicacao).strip()



@dataclass
class Questao:
    numero: str
    enunciado: str
    alternativas: list[tuple[str, str]] = field(default_factory=list)
    resposta: str = ""
    feedback: str = ""
    question_id: str = ""
    difficulty: str = ""
    skill: str = ""
    criterios: list[str] = field(default_factory=list)
    referencia: str = ""
    tipo: str = ""

    @property
    def dissertativa(self) -> bool:
        """Dissertativa é a questão que não tem alternativa para escolher.

        O tipo declarado manda quando existe; sem ele, a ausência de
        alternativas com critérios escritos é a assinatura inconfundível —
        e é assim que a maioria do texto colado chega.
        """
        declarado = _chave(self.tipo)
        if declarado.startswith("dissertativ") or declarado.startswith("discursiv"):
            return True
        if declarado.startswith("multipla") or declarado.startswith("objetiv"):
            return False
        return not self.alternativas and bool(self.criterios or self.referencia)


def ler_questoes(conteudo: str, *, exigir_id: bool = False) -> list[Questao]:
    """Lê as questões de uma seção de exercícios, na ordem em que aparecem.

    `exigir_id` existe para o material de autoria, onde `question_id` é a
    marca de versão final: quando a revisão encontrou um gabarito impossível,
    a questão foi reescrita logo abaixo ("Questão 10 (versão corrigida)") e só
    a última leva os metadados. Filtrar por `question_id` descarta os
    rascunhos sem ninguém decidir na mão.

    Texto colado no admin não tem essa convenção — e exigir um id que a pessoa
    não sabe que precisa existir descartaria a questão inteira em silêncio,
    que é a pior falha possível aqui. Ali o id é gerado pelo compilador.
    """
    questoes: list[Questao] = []
    atual: Questao | None = None
    lendo_enunciado = False
    lendo_criterios = False

    for linha in conteudo.splitlines():
        crua = linha.strip()
        cabeca = _CABECA_DE_QUESTAO.match(crua)
        if cabeca:
            if atual:
                questoes.append(atual)
            atual = Questao(numero=cabeca.group(1).strip(), enunciado="")
            lendo_enunciado = True
            lendo_criterios = False
            continue
        if atual is None:
            continue

        criterios = _CRITERIOS.match(crua)
        if criterios:
            # `Critérios:` abre uma lista embaixo, ou traz tudo na mesma linha
            # separado por `;`. As duas formas aparecem no texto colado.
            inline = criterios.group(1).strip().strip("*").strip()
            if inline:
                atual.criterios += [c.strip() for c in re.split(r"\s*;\s*", inline) if c.strip()]
            lendo_criterios = True
            lendo_enunciado = False
            continue

        referencia = _REFERENCIA.match(crua)
        if referencia:
            atual.referencia = referencia.group(1).strip().strip("*").strip()
            lendo_criterios = lendo_enunciado = False
            continue

        tipo = _TIPO.match(crua)
        if tipo:
            atual.tipo = tipo.group(1).strip()
            lendo_criterios = lendo_enunciado = False
            continue

        if lendo_criterios:
            item = _ITEM_DE_LISTA.match(crua)
            if item:
                atual.criterios.append(item.group(1).strip().strip("*").strip())
                continue
            if crua:
                lendo_criterios = False

        alternativa = _ALTERNATIVA.match(crua)
        if alternativa:
            # O negrito da letra (`- **A)** 50`) sobra no texto quando a
            # marcação fecha depois do parêntese. Asterisco solto na ponta é
            # ruído de marcação, nunca conteúdo da alternativa.
            texto_alt = alternativa.group(2).strip().strip("*").strip()
            atual.alternativas.append((alternativa.group(1).upper(), texto_alt))
            lendo_enunciado = False
            continue

        resposta = _RESPOSTA.match(crua)
        if resposta:
            atual.resposta = resposta.group(1).strip()
            lendo_enunciado = False
            continue

        feedback = _FEEDBACK.match(crua)
        if feedback:
            atual.feedback = feedback.group(1).strip()
            lendo_enunciado = False
            continue

        meta = _META.match(crua)
        if meta:
            campo = _CAMPO_DA_META.get(meta.group(1).lower())
            if campo:
                setattr(atual, campo, meta.group(2).strip())
            lendo_enunciado = False
            continue

        if lendo_enunciado and crua:
            atual.enunciado = (atual.enunciado + " " + crua).strip()

    if atual:
        questoes.append(atual)
    if exigir_id:
        return [q for q in questoes if q.question_id]
    return [q for q in questoes if q.enunciado and (q.alternativas or q.dissertativa)]


def nivel_da_questao(questao: Questao, minimo: int) -> int:
    """O nível declarado, ou o do exercício anterior.

    Herdar o anterior (em vez de chutar 1, ou de recusar a questão) é o que
    mantém a regra do contrato — o nível não retrocede dentro da estação —
    verdadeira para texto que não declara dificuldade nenhuma. Quem declarar
    ganha a progressão de verdade; quem não declarar publica tudo no mesmo
    degrau, que é honesto: ninguém disse que havia degraus.
    """
    bruto = (questao.difficulty or "").strip().lower()
    declarado = NIVEL_POR_DIFICULDADE.get(bruto)
    if declarado is None:
        return max(1, minimo)
    return max(declarado, minimo)


def _bloco_dissertativo(questao: Questao, *, bloco_id: str, nivel: int, origem: dict | None) -> dict:
    """A questão que se responde escrevendo — corrigida pela Mentis, por Sparks.

    Ela não tem gabarito, e é por isso que precisa de `criterios`: a régua
    escrita por quem fez a questão é o que impede que cada aluno seja
    corrigido por um padrão diferente. O aluno VÊ os critérios antes de
    escrever (é o que faz a questão ensinar, e não adivinhar) e nunca vê a
    `referencia`, que é a resposta esperada.

    Sem critério nenhum, a questão PARA a compilação em vez de virar uma
    correção improvisada: "a Mentis que se vire" é o jeito de publicar uma
    nota que ninguém sabe explicar.
    """
    criterios = [c for c in questao.criterios if c.strip()]
    if not criterios and questao.referencia:
        # Quem escreveu a resposta esperada e não a régua: a resposta vira o
        # critério único, explicitamente, e não um padrão implícito.
        criterios = [f"A resposta contempla o que se espera: {questao.referencia}"]
    if not criterios:
        raise ValueError(
            f"{questao.numero or bloco_id}: questão dissertativa sem régua de correção. "
            "Escreva `**Critérios:**` e liste em `- ` o que a resposta precisa ter"
        )

    bloco = {
        "tipo": "exercicio",
        "bloco_id": bloco_id,
        "nivel": nivel,
        "formato": "dissertativo",
        "enunciado": questao.enunciado,
        "criterios": criterios[:6],
    }
    if questao.referencia:
        bloco["referencia"] = questao.referencia
    if questao.feedback:
        bloco["solucao"] = questao.feedback
    if questao.skill:
        bloco["conceitos"] = [slug(questao.skill)]
    if origem:
        bloco["origem"] = origem
    return bloco


def bloco_de_exercicio(questao: Questao, *, bloco_id: str, nivel: int, origem: dict | None = None) -> dict:
    """Uma questão do texto vira um exercício do contrato.

    Aqui acontecem as duas transformações que o topo do arquivo explica: o
    feedback é repartido por alternativa e as alternativas são embaralhadas
    com semente fixa no `bloco_id`.
    """
    if questao.dissertativa:
        return _bloco_dissertativo(questao, bloco_id=bloco_id, nivel=nivel, origem=origem)

    letras_do_texto = {letra.upper() for letra, _ in questao.alternativas}
    if not questao.resposta:
        raise ValueError(f"{questao.numero or bloco_id}: sem `Resposta:` — nenhum gabarito para corrigir")
    marcada = questao.resposta.strip().upper()
    # "B) 26" e "B" dizem a mesma coisa; quem cola costuma trazer a linha
    # inteira da alternativa certa.
    escolhida = next((l for l in letras_do_texto if marcada == l or marcada.startswith(f"{l})") or marcada.startswith(f"{l} ")), None)
    if escolhida is None:
        raise ValueError(
            f"{questao.numero or bloco_id}: a resposta {questao.resposta!r} não é "
            f"nenhuma das alternativas ({', '.join(sorted(letras_do_texto))})"
        )

    ids = [letra.lower() for letra, _ in questao.alternativas]
    por_alternativa, explicacao = repartir_feedback(questao.feedback, ids)

    ordem = list(range(len(questao.alternativas)))
    random.Random(f"sapiens:{bloco_id}").shuffle(ordem)

    # O id da alternativa é a POSIÇÃO em que ela vai ser exibida, e não a
    # letra que ela tinha no texto.
    #
    # Isto não é cosmético: o id viaja para o navegador dentro de cada
    # alternativa. Se ele fosse a letra original, o gabarito estaria escrito
    # no HTML — quem escreve põe a resposta certa em A quase sempre, e
    # bastaria abrir o inspetor para gabaritar o curso inteiro.
    #
    # De quebra, `chave` nos eventos passa a ser a alternativa que o aluno
    # VIU: "a alternativa C atrai mais gente" no painel significa a terceira
    # da tela, que é a frase que alguém consegue interpretar.
    letras = "abcdefgh"
    alternativas = [
        {"id": letras[pos], "texto": questao.alternativas[i][1]}
        for pos, i in enumerate(ordem)
    ]
    de_origem_para_posicao = {
        questao.alternativas[i][0].lower(): letras[pos] for pos, i in enumerate(ordem)
    }

    bloco = {
        "tipo": "exercicio",
        "bloco_id": bloco_id,
        "nivel": nivel,
        "formato": "multipla_escolha",
        "enunciado": questao.enunciado,
        "alternativas": alternativas,
        "gabarito": de_origem_para_posicao[escolhida.lower()],
    }
    # O comentário da alternativa CERTA sairia daqui igual à `solucao` — a
    # mesma explicação, duas vezes na mesma tela. Quem acerta recebe a
    # `solucao`, e o `feedback` fica só com os distratores.
    distratores = {
        de_origem_para_posicao[k]: v
        for k, v in por_alternativa.items()
        if de_origem_para_posicao.get(k) and de_origem_para_posicao[k] != bloco["gabarito"]
    }
    if distratores:
        bloco["feedback"] = distratores
    if explicacao:
        bloco["solucao"] = explicacao
    if questao.skill:
        bloco["conceitos"] = [slug(questao.skill)]
    if origem:
        bloco["origem"] = origem
    return bloco


# ---------------------------------------------------------------------------
# Desafio final
# ---------------------------------------------------------------------------


_UNIDADES = (
    ("R$", "reais"), ("%", "%"), ("m/s", "m/s"), ("km/h", "km/h"),
    ("meses", "meses"), ("mês", "meses"), ("m²", "m²"), ("cm", "cm"), ("m", "m"),
)


def como_numero(texto: str) -> tuple[float, str] | None:
    """`"R$ 2.400"` -> `(2400.0, "reais")`. `"4x + 10"` -> `None`.

    Só aceita a resposta que é UM número com, no máximo, uma unidade colada.
    Qualquer outra coisa não é pergunta de campo numérico.
    """
    bruto = texto.strip().rstrip(".")
    unidade = ""
    for marca, nome in _UNIDADES:
        if bruto.startswith(marca):
            bruto, unidade = bruto[len(marca):].strip(), nome
            break
        if bruto.endswith(marca):
            bruto, unidade = bruto[: -len(marca)].strip(), nome
            break
    limpo = bruto.replace(".", "").replace(",", ".").replace(" ", "")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", limpo):
        return None
    return float(limpo), unidade


_SOBRESCRITOS = str.maketrans("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079", "0123456789")


def variantes_aceitas(resposta: str) -> list[str]:
    """Todas as formas de ESCREVER a mesma resposta curta.

    `cursos_conteudo` já ignora acento, caixa e espaço repetido na comparação,
    mas não sabe que `2 × 10⁵`, `2x10^5` e `200000` são a mesma coisa. Sem
    isto, um desafio cuja resposta tem expoente sobrescrito é literalmente
    impossível de digitar num teclado — o aluno acerta a conta e o campo diz
    que errou.

    Só transformações de NOTAÇÃO entram aqui. Nada que aceite uma resposta
    diferente da que o autor escreveu.
    """
    base = resposta.strip().rstrip(".")
    formas = {base}
    for forma in list(formas):
        formas.add(forma.replace("\u00d7", "x"))
        formas.add(forma.replace("\u00d7", "*"))
    for forma in list(formas):
        # `10\u2075` -> `10^5` e -> `105`? Não: o expoente vira `^5`, e o
        # valor por extenso entra só quando dá para calculá-lo sem inventar.
        traduzido = forma.translate(_SOBRESCRITOS)
        if traduzido != forma:
            formas.add(re.sub(r"(\d)([\u2070\u00b9\u00b2\u00b3\u2074-\u2079]+)", lambda m: m.group(1) + "^" + m.group(2).translate(_SOBRESCRITOS), forma))
    for forma in list(formas):
        formas.add(forma.replace(" ", ""))
        if "=" in forma:
            formas.add(forma.split("=", 1)[1].strip())
    # `4x + 10` e `10 + 4x` são a mesma expressão escrita nas duas ordens.
    soma = re.fullmatch(r"(\S+)\s\+\s(\S+)", base)
    if soma:
        formas.add(f"{soma.group(2)} + {soma.group(1)}")
        formas.add(f"{soma.group(2)}+{soma.group(1)}")

    # `2 × 10^5` também vale digitado por extenso.
    potencia = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*[x*\u00d7]\s*10\s*\^?\s*(-?\d+)\s*", base.translate(_SOBRESCRITOS).replace("\u2075", "5"))
    if potencia:
        try:
            valor = float(potencia.group(1).replace(",", ".")) * (10 ** int(potencia.group(2)))
            formas.add(f"{valor:.0f}" if valor == int(valor) else str(valor))
        except (ValueError, OverflowError):
            pass
    return sorted(f for f in formas if f)


def bloco_de_desafio(
    secao: str, *, bloco_id: str, nivel_maximo: int, encodado: dict | None = None,
) -> dict | None:
    """O desafio da estação: mesmo formato de exercício, teto de dificuldade.

    Nunca conta para concluir (o contrato garante isso) e o nível não pode ser
    menor que o do exercício mais difícil — desafio é o topo, não um degrau
    para trás.

    `encodado` é a saída para o desafio cuja resposta escrita é uma FRASE
    ("99% do original, ou seja, 1% menor"): alguém leu e disse que número ela
    afirma. Sem ele, uma resposta em prosa PARA a compilação em vez de virar
    gabarito adivinhado — "o primeiro número do parágrafo" é como se publica
    um gabarito errado sem ninguém perceber.
    """
    if not secao.strip():
        return None

    # `_RESPOSTA` é ancorada na linha; aqui a busca é no bloco inteiro.
    marca = re.compile(_RESPOSTA.pattern, re.IGNORECASE | re.MULTILINE).search(secao)
    if not marca:
        return None
    corpo = secao[: marca.start()]
    resto = secao[marca.start():]
    resposta = marca.group(1).strip()
    _, _, resolucao = resto.partition("**Resolução:**")
    enunciado = "\n".join(
        l for l in corpo.splitlines() if not _RESPOSTA.match(l.strip())
    ).strip()
    if not enunciado or not resposta:
        return None

    bloco: dict = {
        "tipo": "desafio",
        "bloco_id": bloco_id,
        "nivel": max(NIVEL_DO_DESAFIO, nivel_maximo),
        "enunciado": enunciado,
    }

    numero = como_numero(resposta)
    if encodado:
        bloco["formato"] = "numerico"
        bloco["gabarito"] = {"valor": encodado["valor"], "tolerancia": encodado["tolerancia"]}
        if encodado.get("unidade"):
            bloco["unidade"] = encodado["unidade"]
    elif numero is not None:
        valor, unidade = numero
        bloco["formato"] = "numerico"
        # Tolerância proporcional, com piso: `7,1` aceita `7,1`; `2400` aceita
        # o arredondamento de quem calculou por outro caminho.
        bloco["gabarito"] = {"valor": valor, "tolerancia": max(0.01, abs(valor) * 0.001)}
        if unidade:
            bloco["unidade"] = unidade
    elif len(resposta) <= 24:
        bloco["formato"] = "texto_curto"
        bloco["gabarito"] = {"aceitos": variantes_aceitas(resposta)}
    else:
        raise ValueError(
            f"desafio com resposta em prosa ({resposta[:60]!r}): não dá para "
            "corrigir sozinho. Escreva a resposta como número ou como uma "
            "expressão curta, ou tire a seção de desafio."
        )

    if resolucao.strip():
        passos = [l.strip()[2:].strip() for l in resolucao.splitlines() if l.strip().startswith("- ")]
        bloco["solucao"] = "\n".join(f"- {p}" for p in passos) if passos else resolucao.strip()
    return bloco


# ---------------------------------------------------------------------------
# A estação inteira
# ---------------------------------------------------------------------------

_PRE_REQUISITO = re.compile(r"Esta[çc][ãa]o\s+(\d{1,2})", re.IGNORECASE)
_TITULO_DA_ESTACAO = re.compile(r"^#\s+(?:Esta[çc][ãa]o\s*(\d{1,3})\s*[—–:\-]?\s*)?(.*)$", re.IGNORECASE)

# Como cada seção conhecida entra na estação. A chave é o nome normalizado
# (sem acento, minúsculo); a ordem desta tabela NÃO manda — quem manda é a
# ordem em que as seções aparecem no texto, porque é a ordem em que a aula foi
# escrita para ser lida.
# Os nomes de seção que o compilador RECONHECE. A lista é longa de propósito:
# cada sinônimo que falta aqui não perde conteúdo (seção desconhecida vira
# leitura com o título dela), mas perde a VARIANTE visual — "Erros comuns"
# escrito como "Pegadinhas" viraria um parágrafo cinza em vez do bloco de
# atenção. Ampliar a lista é mais barato que pedir a alguém que reescreva o
# título da seção.
SECOES_DE_LEITURA = {
    "conteudo": ("c", "padrao"),
    "aula": ("c", "padrao"),
    "explicacao": ("c", "padrao"),
    "teoria": ("c", "padrao"),
    "desenvolvimento": ("c", "padrao"),
    "introducao": ("c", "padrao"),
    "fundamentos": ("c", "padrao"),
    "conceitos": ("c", "padrao"),
    "aprofundamento": ("c", "padrao"),
    "resumo": ("c", "padrao"),
    "sintese": ("c", "padrao"),
    "visual sugerido": ("v", "padrao"),
    "estrategias": ("es", "destaque"),
    "estrategia": ("es", "destaque"),
    "dicas": ("es", "destaque"),
    "dica": ("es", "destaque"),
    "macetes": ("es", "destaque"),
    "como cai na prova": ("es", "destaque"),
    "erros comuns": ("er", "atencao"),
    "erro comum": ("er", "atencao"),
    "pegadinhas": ("er", "atencao"),
    "armadilhas": ("er", "atencao"),
    "atencao": ("er", "atencao"),
    "cuidado": ("er", "atencao"),
}
SECOES_DE_EXEMPLO = (
    "exemplos resolvidos", "exemplos", "exemplo resolvido", "exemplo",
    "resolvidos", "passo a passo", "modelo resolvido",
)
SECOES_DE_EXERCICIO = (
    "exercicios", "exercicio", "questoes", "questao", "pratica", "atividades",
    "atividade", "exercicios propostos", "questoes propostas", "praticar",
    "hora de praticar", "teste seus conhecimentos", "fixacao", "treino",
)
SECOES_DE_DESAFIO = ("desafio final", "desafio", "questao desafio")
SECOES_IGNORADAS = (
    "objetivo", "objetivos", "pre-requisitos", "pre requisitos", "prerequisitos",
    "pre-requisito", "video", "metadados", "gabarito comentado",
)


def _chave(nome: str) -> str:
    """O nome de uma seção reduzido ao que importa para reconhecê-la.

    Cai fora acento, caixa, negrito e a numeração que quem escreve põe no
    título (`## 2. Conteúdo`, `## Parte 3 — Exercícios`). Sem isto, a MESMA
    seção escrita com um "2." na frente deixava de ser reconhecida e a aula
    inteira ia para o lugar errado, sem erro nenhum.
    """
    sem_acento = unicodedata.normalize("NFKD", nome or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = sem_acento.replace("*", "").replace("#", "")
    limpo = re.sub(r"^\s*(?:parte\s*)?\d+\s*[.)\-\u2014\u2013:]?\s*", "", limpo, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", limpo).strip().lower().rstrip(":")


def normalizar(texto: str) -> str:
    """Endireita o que é variação de escrita, e só isso.

    Nada aqui muda conteúdo: só promove um cabeçalho de questão ao nível que o
    leitor de seções espera e declara a seção de exercícios quando ela está
    implícita. É a diferença entre "cole o texto" e "cole o texto no formato
    exato" — e é a segunda que faz alguém desistir de publicar.
    """
    limpo = texto.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    linhas = limpo.split("\n")
    saida: list[str] = []
    for linha in linhas:
        crua = linha.strip()
        # `## Questão 3` quebraria a seção de exercícios em três seções — o
        # leitor de seções corta em `##`. Vira `### Questão 3`.
        if re.match(r"^##\s+(?:Quest[ãa]o|Exerc[íi]cio)\b", crua, re.IGNORECASE):
            saida.append("#" + crua)
            continue
        # `**Questão 3**` sozinha na linha é cabeçalho escrito em negrito.
        marca = re.match(r"^\*\*\s*((?:Quest[ãa]o|Exerc[íi]cio)\s*\d+[^*]*)\*\*[.:]?$", crua, re.IGNORECASE)
        if marca:
            saida.append(f"### {marca.group(1).strip()}")
            continue
        # `Questão 3` ou `QUESTÃO 3 —` sozinha na linha, sem marcação nenhuma:
        # é o jeito mais comum de um texto colado separar as questões, e sem
        # isto TODAS elas viravam um parágrafo só de leitura.
        nua = re.match(r"^(?:Quest[ãa]o|Exerc[íi]cio)\s*\d+\s*[.:)\u2014\u2013-]?\s*$", crua, re.IGNORECASE)
        if nua:
            saida.append(f"### {crua.rstrip('.:)—– ')}")
            continue
        saida.append(linha)

    texto_limpo = "\n".join(saida)
    linhas_limpas = texto_limpo.split("\n")

    # Onde começa a primeira questão, e se alguém já declarou uma seção de
    # exercícios ANTES dela. A checagem é posicional e não global: questões
    # escritas no meio da seção de conteúdo (que é onde elas aparecem quando
    # ninguém separa nada) precisam da seção nascendo em cima delas, mesmo
    # que exista um `## Exercícios` mais adiante no texto.
    primeira_questao = next(
        (i for i, l in enumerate(linhas_limpas)
         if re.match(r"^#{3,6}\s+(?:Quest[ãa]o|Exerc[íi]cio)\b", l, re.IGNORECASE)),
        None,
    )
    if primeira_questao is not None:
        declarada = any(
            _chave(l[3:]) in SECOES_DE_EXERCICIO
            for l in linhas_limpas[:primeira_questao] if l.startswith("## ")
        )
        if not declarada:
            linhas_limpas.insert(primeira_questao, "## Exercícios")
            texto_limpo = "\n".join(linhas_limpas)
    return texto_limpo


def fatiar_estacoes(texto: str) -> list[str]:
    """Um texto colado pode trazer várias estações. Corta entre elas.

    Dois sinais de começo, que é o que os materiais usam: o bloco de
    frontmatter (`---`) e o título de primeiro nível (`# Estação 02 — …`). O
    título que vem logo depois de um frontmatter NÃO corta de novo: ele é o
    título daquela mesma estação.
    """
    linhas = texto.split("\n")
    cortes: list[int] = []
    fim_do_frontmatter = -10
    i = 0
    while i < len(linhas):
        crua = linhas[i].strip()
        if crua == "---" and _abre_frontmatter(linhas, i):
            cortes.append(i)
            fim = _fecha_frontmatter(linhas, i)
            fim_do_frontmatter = fim
            i = fim + 1
            continue
        if linhas[i].startswith("# "):
            anterior = next((j for j in range(i - 1, -1, -1) if linhas[j].strip()), -1)
            if anterior != fim_do_frontmatter:
                cortes.append(i)
        i += 1

    if not cortes:
        return [texto] if texto.strip() else []
    pedacos = []
    for n, inicio in enumerate(cortes):
        fim = cortes[n + 1] if n + 1 < len(cortes) else len(linhas)
        pedaco = "\n".join(linhas[inicio:fim]).strip()
        if pedaco:
            pedacos.append(pedaco)
    return pedacos


def _abre_frontmatter(linhas: list[str], i: int) -> bool:
    seguinte = next((l for l in linhas[i + 1:i + 4] if l.strip()), "")
    return bool(re.match(r"^[\w][\w -]*\s*:", seguinte)) and _fecha_frontmatter(linhas, i) > i


def _fecha_frontmatter(linhas: list[str], i: int) -> int:
    for j in range(i + 1, min(len(linhas), i + 60)):
        if linhas[j].strip() == "---":
            return j
    return -1


def _secao(partes: dict[str, str], nomes: tuple[str, ...]) -> str:
    """O conteúdo da primeira seção cujo nome normalizado está em `nomes`.

    Busca por chave normalizada e não por título exato: `## Objetivos`,
    `## 1. Objetivo` e `## **Objetivo**` são a mesma seção, e a versão antiga
    (`partes.get("Objetivo")`) só enxergava uma delas.
    """
    for nome, conteudo in partes.items():
        if _chave(nome) in nomes:
            return conteudo
    return ""


def _titulo_provavel(corpo: str) -> str:
    """O título quando ninguém escreveu `# Título`: o primeiro cabeçalho que
    não é uma seção conhecida, ou a primeira linha curta do texto."""
    for linha in corpo.splitlines():
        crua = linha.strip()
        if crua.startswith("#"):
            nome = crua.lstrip("#").strip()
            chave = _chave(nome)
            conhecida = (
                chave in SECOES_DE_LEITURA or chave in SECOES_IGNORADAS
                or chave in SECOES_DE_EXERCICIO or chave in SECOES_DE_DESAFIO
                or chave in SECOES_DE_EXEMPLO
            )
            if nome and not conhecida:
                return nome[:80]
    for linha in corpo.splitlines():
        crua = linha.strip().strip("*").strip()
        if 3 <= len(crua) <= 80:
            return crua
    return ""


def _primeira_frase(partes: dict[str, str]) -> str:
    """A primeira frase de aula do texto — o objetivo de emergência."""
    for nome, conteudo in partes.items():
        if _chave(nome) in SECOES_DE_EXERCICIO or _chave(nome) in SECOES_DE_DESAFIO:
            continue
        for linha in conteudo.splitlines():
            crua = linha.strip().strip("*").strip()
            if len(crua) >= 20 and not crua.startswith(("#", "|", "-")):
                frase = re.split(r"(?<=[.!?])\s", crua)[0]
                return " ".join(frase.split())[:240]
    return ""


@dataclass
class EstacaoLida:
    numero: int | None
    titulo: str
    objetivo: str
    conceitos: list[str]
    habilidades: list[str]
    pre_requisitos_numeros: list[int]
    blocos: list[dict]
    exercicios: int
    avisos: list[str] = field(default_factory=list)


def ler_estacao_de_texto(
    texto: str, *, prefixo: str, encodados: dict | None = None, exigir_id: bool = False,
    resumo_do_video: str | None = None,
) -> EstacaoLida:
    """Um texto de estação vira blocos, na ordem em que foi escrito.

    Levanta `ValueError` com uma frase que diz o que falta — é ela que aparece
    no painel de quem colou o texto, e por isso fala de "seção" e de
    "resposta", e não de campo de JSON.
    """
    avisos: list[str] = []
    meta, corpo = frontmatter(normalizar(texto))
    partes = secoes(corpo)

    cabeca = next((l for l in corpo.split("\n") if l.startswith("# ")), "")
    achado = _TITULO_DA_ESTACAO.match(cabeca) if cabeca else None

    numero_bruto = str(meta.get("station_id") or (achado.group(1) if achado and achado.group(1) else "")).strip()
    numero = int(numero_bruto) if numero_bruto.isdigit() else None

    titulo = str(meta.get("title") or "").strip() or (achado.group(2).strip() if achado else "")
    if not titulo:
        titulo = _titulo_provavel(corpo)
        if titulo:
            avisos.append(
                f"ninguém declarou o título: a estação entrou como `{titulo}`. "
                "Para escolher outro, comece o texto com `# Título da estação`"
            )
    if not titulo:
        raise ValueError(
            "sem título: comece com uma linha `# Título da estação` (ou declare "
            "`title:` no bloco do topo)"
        )

    objetivo = " ".join(_secao(partes, ("objetivo", "objetivos")).split())
    if not objetivo:
        # Estação sem `## Objetivo` NÃO para a publicação: a frase é
        # importante, mas fazer alguém reescrever o texto inteiro por causa
        # dela é o jeito mais rápido de a pessoa desistir de publicar. Sai a
        # primeira frase da aula, e o aviso diz que dá para melhorar.
        objetivo = _primeira_frase(partes)
        if objetivo:
            avisos.append(
                "sem a seção `## Objetivo`: entrou a primeira frase da aula. "
                "Escreva `## Objetivo` com o que o aluno sai sabendo fazer — é "
                "essa frase que aparece no mapa do curso"
            )
    if not objetivo:
        raise ValueError(
            f"`{titulo}`: sem a seção `## Objetivo` — é a frase que diz o que o "
            "aluno sai sabendo fazer, e é ela que dá sentido à ordem das estações"
        )

    # Pré-requisito sai da PROSA ("Frações (Estação 02)"), que é onde ele está
    # escrito sem ambiguidade.
    pre = sorted({int(n) for n in _PRE_REQUISITO.findall(
        _secao(partes, ("pre-requisitos", "pre requisitos", "prerequisitos", "pre-requisito"))
    )})

    blocos: list[dict] = []
    questoes: list[Questao] = []
    desafio_bruto = ""
    contadores: dict[str, int] = {}

    for nome, conteudo in partes.items():
        chave = _chave(nome)
        if not conteudo.strip() or chave in SECOES_IGNORADAS:
            continue
        if chave in SECOES_DE_EXERCICIO:
            questoes += ler_questoes(conteudo, exigir_id=exigir_id)
            continue
        if chave in SECOES_DE_DESAFIO:
            desafio_bruto = conteudo
            continue
        if chave in SECOES_DE_EXEMPLO:
            achados = blocos_de_exemplo(conteudo, f"{prefixo}-ex")
            if achados:
                blocos += achados
                continue
            # Exemplo sem passos em lista não é bloco de exemplo: vira leitura,
            # com o título da seção. Some-lo seria perder uma parte da aula.
            avisos.append(
                f"`{nome}` entrou como texto: um exemplo resolvido precisa dos "
                "passos em lista (`- passo`)"
            )
            blocos += blocos_de_texto(conteudo, f"{prefixo}-ex", "padrao")
            continue
        sufixo, variante = SECOES_DE_LEITURA.get(chave, ("t", "padrao"))
        contadores[sufixo] = contadores.get(sufixo, 0) + 1
        marca = f"{prefixo}-{sufixo}" if contadores[sufixo] == 1 else f"{prefixo}-{sufixo}{contadores[sufixo]}"
        novos = blocos_de_texto(conteudo, marca, variante)
        # Seção que o compilador não conhece mantém o próprio título: é o que
        # permite um curso com outras seções ("Linha do tempo", "Glossário")
        # sem tocar em código.
        if novos and chave not in SECOES_DE_LEITURA and not novos[0].get("titulo"):
            novos[0]["titulo"] = nome
        blocos += novos

    if any(_chave(nome) == "video" for nome in partes):
        # O lugar do vídeo já existe no roteiro; a gravação, não. `ref: null` é
        # pendência DECLARADA: não vai para o aluno e aparece no inventário do
        # admin como "vídeo pendente".
        blocos.append({
            "tipo": "video",
            "bloco_id": f"{prefixo}-video",
            "titulo": f"{titulo} — aula em vídeo",
            "provedor": "youtube",
            "ref": None,
            **({"resumo": resumo_do_video} if resumo_do_video else {}),
        })

    if not questoes:
        raise ValueError(
            f"`{titulo}`: nenhuma questão encontrada. Toda estação precisa de "
            "pelo menos uma — é respondendo que o aluno conclui. Cada questão "
            "começa com `### Questão N` e é de um dos dois tipos: alternativas "
            "em `A)`, `B)`… com a linha `**Resposta:**`, ou dissertativa, com "
            "`**Critérios:**` e a régua em `- `"
        )

    nivel = 1
    exercicios: list[dict] = []
    for i, questao in enumerate(questoes, start=1):
        nivel = nivel_da_questao(questao, nivel)
        bloco_id = slug(questao.question_id) if questao.question_id else f"{prefixo}-q{i:02d}"
        # `origem` é o endereço do exercício NO MATERIAL — é o que permite
        # voltar do painel de análise ("a questão 7 desta estação derruba
        # todo mundo") para o parágrafo que alguém precisa reescrever.
        origem = {k: v for k, v in (("estacao", numero), ("questao", questao.numero)) if v}
        try:
            exercicios.append(bloco_de_exercicio(
                questao, bloco_id=bloco_id, nivel=nivel, origem=origem or None,
            ))
        except ValueError as exc:
            # UMA questão quebrada não derruba a aula inteira. Antes, um
            # `**Resposta:**` esquecido na questão 7 fazia as outras nove
            # sumirem junto — e o texto voltava inteiro para quem colou, sem
            # nada publicado. Agora a questão fica de fora, nominalmente, e o
            # resto vai para o ar.
            avisos.append(f"questão fora da estação — {exc}")
    if not exercicios:
        # Todas as questões caíram nos avisos: a estação não tem como ser
        # concluída. Aqui a tolerância acaba — publicar uma aula que ninguém
        # consegue terminar é pior que recusar o texto.
        raise ValueError(
            f"`{titulo}`: nenhuma das {len(questoes)} questões pôde ser compilada. "
            + " ".join(avisos[-len(questoes):])
        )

    if all(not q.difficulty for q in questoes) and len(questoes) > 1:
        avisos.append(
            "nenhuma questão declarou dificuldade: todas entraram como nível 1. "
            "Para a estação ter progressão, escreva `dificuldade: básico` "
            "(ou intermediário, avançado) embaixo de cada questão."
        )
    blocos += exercicios

    try:
        desafio = bloco_de_desafio(
            desafio_bruto,
            bloco_id=f"{prefixo}-desafio",
            nivel_maximo=max((e["nivel"] for e in exercicios), default=1),
            encodado=(encodados or {}).get(numero),
        )
    except ValueError as exc:
        # Desafio é o único bloco OPCIONAL da estação. Recusar a aula inteira
        # por causa dele seria cobrar do texto uma seção que ele nem precisa
        # ter.
        avisos.append(f"o desafio final ficou de fora — {exc}")
        desafio = None
    if desafio:
        blocos.append(desafio)

    conceitos = [slug(s) for s in (meta.get("skills") or []) if str(s).strip()]
    habilidades = [str(h).strip().upper() for h in (meta.get("habilidades") or []) if str(h).strip()]
    return EstacaoLida(
        numero=numero,
        titulo=titulo,
        objetivo=objetivo,
        conceitos=conceitos,
        habilidades=habilidades,
        pre_requisitos_numeros=pre,
        blocos=blocos,
        exercicios=len(exercicios),
        avisos=avisos,
    )


def duracao(blocos: list[dict], exercicios: int) -> int:
    palavras = 0
    for b in blocos:
        if b["tipo"] == "texto":
            palavras += len(b["markdown"].split())
        elif b["tipo"] == "exemplo":
            palavras += len(b["enunciado"].split()) + sum(len(p["texto"].split()) for p in b["passos"])
    minutos = round(palavras / PALAVRAS_POR_MINUTO) + exercicios
    return max(MINUTOS_MIN, min(MINUTOS_MAX, minutos))


def sigla_do_curso(curso_id: str) -> str:
    """`matematica-basica` -> `mb`. É o prefixo dos ids de bloco.

    Sai do `curso_id` e não de uma tabela: curso novo não pode exigir uma
    linha de código para ter estação publicável, que é o ponto inteiro deste
    módulo. Pedaço que começa com número não entra (em `redacao-0-1000` a
    sigla é `r`), porque id de bloco começa por letra no contrato.
    """
    letras = [parte[0] for parte in str(curso_id).split("-") if parte and parte[0].isalpha()]
    return ("".join(letras)[:3] or "cs").lower()


# ---------------------------------------------------------------------------
# O curso inteiro
# ---------------------------------------------------------------------------


@dataclass
class Compilada:
    """O resultado de compilar um texto: o que virou estação e o que não deu.

    As duas metades juntas, sempre. Publicar metade de um texto e engolir o
    resto é como se perde um exercício sem ninguém notar; o painel mostra as
    duas colunas e quem colou decide.
    """
    estacoes: dict[str, dict] = field(default_factory=dict)
    ordem: list[str] = field(default_factory=list)
    problemas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.estacoes) and not self.problemas


def compilar(
    curso_id: str,
    texto: str,
    *,
    versao: str,
    numero_inicial: int = 1,
    ids_existentes: Iterable[str] = (),
) -> Compilada:
    """Texto cru -> estações no formato do contrato, prontas para validar.

    `numero_inicial` é o número da primeira estação sem número declarado: quem
    cola a estação 25 de um curso que já tem 24 não deveria ter de dizer isso
    duas vezes. `ids_existentes` evita que uma estação nova nasça com o id de
    uma que já existe — dois conteúdos com o mesmo endereço seriam um só, e o
    que o aluno veria é o último a ser gravado.

    Não valida o contrato (quem valida é `cursos_conteudo.validar_estacao`) e
    não escreve nada. Só compila.
    """
    resultado = Compilada()
    pedacos = fatiar_estacoes(texto or "")
    if not pedacos:
        resultado.problemas.append("O texto está vazio.")
        return resultado

    sigla = sigla_do_curso(curso_id)
    usados = set(ids_existentes)
    proximo = max(1, int(numero_inicial))

    for i, pedaco in enumerate(pedacos, start=1):
        # O número é lido duas vezes de propósito: uma para escolher o prefixo
        # dos ids de bloco (que precisa ser estável) e outra depois de saber o
        # título. Ler o cabeçalho antes custa uma linha e evita ids de bloco
        # com o número errado.
        numero = numero_declarado(pedaco) or proximo
        prefixo = f"{sigla}-{numero:02d}"
        try:
            lida = ler_estacao_de_texto(pedaco, prefixo=prefixo)
        except ValueError as exc:
            resultado.problemas.append(f"Bloco {i} do texto: {exc}")
            continue

        estacao_id = f"{sigla}-{numero:02d}-{slug(lida.titulo)}"[:80].strip("-")
        if estacao_id in usados:
            resultado.problemas.append(
                f"`{lida.titulo}`: já existe uma estação com o endereço "
                f"`{estacao_id}` neste curso. Mude o título ou o número."
            )
            continue
        usados.add(estacao_id)
        proximo = numero + 1

        contam = [b for b in lida.blocos if b["tipo"] == "exercicio"]
        dados = {
            "schema_version": SCHEMA_VERSION,
            "estacao_id": estacao_id,
            "titulo": lida.titulo,
            "objetivo": lida.objetivo,
            "versao": versao,
            "duracao_minutos": duracao(lida.blocos, len(contam)),
            "numero": numero,
            "conclusao": {
                "tipo": "minimo_de_acertos",
                "minimo": max(1, round(len(contam) * FRACAO_PARA_CONCLUIR)),
            },
            "blocos": lida.blocos,
        }
        if lida.conceitos:
            dados["conceitos"] = lida.conceitos
        if lida.habilidades:
            dados["habilidades"] = lida.habilidades
        resultado.estacoes[estacao_id] = dados
        resultado.ordem.append(estacao_id)
        resultado.avisos += [f"`{lida.titulo}`: {a}" for a in lida.avisos]

    return resultado


def numero_declarado(pedaco: str) -> int | None:
    """O número da estação declarado no texto (`station_id:` ou `# Estação 07`)."""
    meta, corpo = frontmatter(normalizar(pedaco))
    bruto = str(meta.get("station_id") or "").strip()
    if bruto.isdigit():
        return int(bruto)
    cabeca = next((l for l in corpo.split("\n") if l.startswith("# ")), "")
    achado = _TITULO_DA_ESTACAO.match(cabeca) if cabeca else None
    if achado and achado.group(1):
        return int(achado.group(1))
    return None
