"""Modelo de documento determinístico para cadernos de prova.

Separa **geometria** de **semântica**: o PDF é a fonte da verdade sobre onde as
coisas estão; o LLM lê, não mede. Este módulo só olha o PDF.

O que substitui:

`extract_book_visuals._detect_column_split` derivava a divisória das colunas da
posição x dos marcadores "QUESTÃO N", exigindo ≥2 marcadores por página. Nas
páginas em que uma questão longa ocupa a folha inteira — 25, 28 e 30 do caderno
de 2022 — não há dois marcadores, `split` vira `None`, e a ordem de leitura
passa a intercalar as duas colunas linha a linha. Todo o resto opera sobre essa
ordem corrompida.

Aqui a divisória vem da **projeção de densidade de glifos no eixo x**: a calha
entre colunas é a faixa vertical por onde quase nenhum glifo passa. É um sinal
que existe em toda página com texto, inclusive nas de questão única, porque não
depende de haver marcador nenhum.
"""
from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field
from typing import Any

# Fração mínima da altura útil em que a calha precisa estar vazia para ser
# aceita como divisória real, e não como um espaço fortuito entre palavras.
CALHA_VAZIA_MINIMA = 0.80
# Largura mínima da calha, em pontos. Abaixo disto é espaço entre palavras.
CALHA_LARGURA_MINIMA = 8.0
LINHAS_DE_AMOSTRA = 60

RE_QUESTAO = re.compile(r"^QUEST[ÃA]O$", re.IGNORECASE)
RE_QUESTAO_INLINE = re.compile(r"QUEST[ÃA]O\s+(\d{1,3})", re.IGNORECASE)


@dataclass
class ModeloPagina:
    numero: int
    largura: float
    altura: float
    colunas: list[tuple[float, float]]
    calhas: list[tuple[float, float]]
    chrome: list[tuple[float, float, float, float]] = field(default_factory=list)
    marca_dagua: list[tuple[float, float, float, float]] = field(default_factory=list)
    metodo: str = "densidade_glifos"

    LARGURA_TOTAL = -1

    def coluna_de(self, x0: float, x1: float) -> int | None:
        """Índice da coluna que contém [x0, x1], ou `LARGURA_TOTAL`.

        Uma tabela ou gráfico que ocupa a largura útil inteira da página é
        legítimo no ENEM e cruza a calha por construção. Tratar isso como
        contaminação confundia "figura larga" com "recorte que invadiu a
        coluna vizinha" — são coisas diferentes e só a segunda é defeito.
        """
        margem = self.largura * 0.10
        if x0 <= margem * 1.6 and x1 >= self.largura - margem * 1.6:
            return self.LARGURA_TOTAL
        centro = (x0 + x1) / 2
        for i, (c0, c1) in enumerate(self.colunas):
            if c0 <= centro <= c1:
                return i if (x0 >= c0 - 2 and x1 <= c1 + 2) else None
        return None

    def coluna_do_ponto(self, x: float) -> int | None:
        for i, (c0, c1) in enumerate(self.colunas):
            if c0 <= x <= c1:
                return i
        return None


@dataclass
class RegiaoQuestao:
    numero: int
    pagina: int
    coluna: int
    y0: float
    y1: float

    def contem(self, bbox: tuple[float, float, float, float], folga: float = 2.0) -> bool:
        _, by0, _, by1 = bbox
        return by0 >= self.y0 - folga and by1 <= self.y1 + folga


def _palavras(page) -> list[tuple]:
    return page.get_text("words") or []


def _detectar_calhas(page, largura: float, altura: float,
                     ignorar: set[tuple] | None = None) -> list[tuple[float, float]]:
    """Faixas verticais por onde quase nenhum glifo passa.

    Discretiza x em colunas de 1 pt e marca, para cada faixa, em quantas linhas
    de amostra há glifo. Uma calha é um intervalo contíguo de faixas livres em
    ≥ `CALHA_VAZIA_MINIMA` das linhas, com largura ≥ `CALHA_LARGURA_MINIMA`.
    """
    # A marca d'água é LADRILHADA e atravessa a calha: com ela na projeção,
    # nenhuma faixa de x fica vazia e a calha nunca aparece. Descobrir a marca
    # d'água é, portanto, PRÉ-REQUISITO da detecção de coluna — não um detalhe
    # de renderização. Foi o que a primeira versão deste módulo errou: 30 das
    # 32 páginas caíam no fallback geométrico.
    ignorar = ignorar or set()
    palavras = [w for w in _palavras(page) if (w[0], w[1], w[2], w[3]) not in ignorar]
    if not palavras:
        return []

    ys = [w[1] for w in palavras]
    topo, base = min(ys), max(w[3] for w in palavras)
    if base <= topo:
        return []

    passo = (base - topo) / LINHAS_DE_AMOSTRA
    ocupacao = collections.Counter()
    linhas_com_texto = 0
    for i in range(LINHAS_DE_AMOSTRA):
        y = topo + i * passo
        na_linha = [w for w in palavras if w[1] <= y <= w[3]]
        if not na_linha:
            continue
        linhas_com_texto += 1
        for w in na_linha:
            for x in range(int(w[0]), int(w[2]) + 1):
                ocupacao[x] += 1
    if not linhas_com_texto:
        return []

    limite = 0  # faixa livre = nenhum glifo em nenhuma linha de amostra
    livres = [x for x in range(int(largura) + 1) if ocupacao.get(x, 0) <= limite]

    calhas: list[tuple[float, float]] = []
    if not livres:
        return calhas
    inicio = anterior = livres[0]
    for x in livres[1:] + [None]:
        if x is not None and x == anterior + 1:
            anterior = x
            continue
        if anterior - inicio >= CALHA_LARGURA_MINIMA:
            calhas.append((float(inicio), float(anterior)))
        if x is not None:
            inicio = anterior = x

    # Margens não são calhas: descarta as que encostam na borda da página.
    margem = largura * 0.12
    return [c for c in calhas if c[0] > margem and c[1] < largura - margem]


def _detectar_marca_dagua(page) -> list[tuple[float, float, float, float]]:
    """Bboxes dos glifos da marca d'água ladrilhada.

    `_strip_watermark` do extrator atual remove a marca d'água da LISTA de
    palavras, para não estragar o casamento de texto — mas `_render_crop`
    renderiza a página com `get_pixmap`, e a marca continua desenhada no pixel.
    Guardar as bboxes aqui é o que permite redigi-las antes de renderizar.

    Identificação: um texto curto que se repete muitas vezes na mesma página é
    ladrilho, não conteúdo.
    """
    palavras = _palavras(page)
    contagem = collections.Counter(w[4] for w in palavras if len(w[4]) >= 3)
    ladrilhos = {t for t, n in contagem.items() if n >= 8}
    return [(w[0], w[1], w[2], w[3]) for w in palavras if w[4] in ladrilhos]


def _detectar_chrome(page, altura: float) -> list[tuple[float, float, float, float]]:
    """Cabeçalho e rodapé: o que está fora da faixa central de conteúdo."""
    faixa = altura * 0.06
    return [
        (w[0], w[1], w[2], w[3])
        for w in _palavras(page)
        if w[3] <= faixa or w[1] >= altura - faixa
    ]


def modelo_pagina(page, numero: int, colunas_declaradas: int = 2) -> ModeloPagina:
    largura, altura = page.rect.width, page.rect.height
    marca = _detectar_marca_dagua(page)
    chrome = _detectar_chrome(page, altura)
    calhas = _detectar_calhas(page, largura, altura, ignorar=set(marca) | set(chrome))
    metodo = "densidade_glifos"

    if not calhas and colunas_declaradas == 2:
        # Página sem calha detectável (só figura, ou texto corrido). O caderno
        # é declaradamente de duas colunas e a largura é constante — cair para
        # a divisória geométrica é melhor que tratar a página como coluna
        # única, que é o que corrompe a ordem de leitura hoje.
        meio = largura / 2
        calhas = [(meio - 4, meio + 4)]
        metodo = "fallback_geometrico"

    bordas = [0.0]
    for c0, c1 in sorted(calhas):
        bordas += [c0, c1]
    bordas.append(largura)
    colunas = [(bordas[i], bordas[i + 1]) for i in range(0, len(bordas) - 1, 2)]

    return ModeloPagina(
        numero=numero, largura=largura, altura=altura,
        colunas=colunas, calhas=sorted(calhas),
        chrome=chrome,
        marca_dagua=marca,
        metodo=metodo,
    )


def modelo_documento(doc, colunas_declaradas: int = 2) -> dict[int, ModeloPagina]:
    return {
        i: modelo_pagina(pagina, i, colunas_declaradas)
        for i, pagina in enumerate(doc)
    }


def regioes_por_questao(doc, modelos: dict[int, ModeloPagina]) -> dict[int, list[RegiaoQuestao]]:
    """Uma questão é uma LISTA ORDENADA de regiões `(página, coluna, y0, y1)`.

    Uma questão pode atravessar coluna→coluna e página→página; tratá-la como
    uma faixa única é o que permite atribuir a ela um objeto da coluna vizinha.
    Escopar toda operação a estas regiões torna essa atribuição impossível por
    construção, não por heurística.
    """
    marcadores: list[tuple[int, int, float, int]] = []  # (pagina, coluna, y, numero)
    for idx, pagina in enumerate(doc):
        modelo = modelos[idx]
        palavras = _palavras(pagina)
        for w in palavras:
            numero = None
            inline = RE_QUESTAO_INLINE.match(w[4])
            if inline:
                numero = int(inline.group(1))
            elif RE_QUESTAO.match(w[4]):
                # O extrator devolve "QUESTÃO" e "175" como palavras separadas.
                # O número é o primeiro dígito à direita, na mesma linha de base.
                for v in palavras:
                    if abs(v[1] - w[1]) < 3 and 0 < v[0] - w[2] < 40 and v[4].isdigit():
                        numero = int(v[4])
                        break
            if numero is None or not (1 <= numero <= 180):
                continue
            coluna = modelo.coluna_do_ponto(w[0])
            if coluna is None:
                continue
            marcadores.append((idx, coluna, w[1], numero))

    marcadores.sort(key=lambda m: (m[0], m[1], m[2]))
    regioes: dict[int, list[RegiaoQuestao]] = collections.defaultdict(list)
    for i, (pagina, coluna, y, numero) in enumerate(marcadores):
        modelo = modelos[pagina]
        proximo = marcadores[i + 1] if i + 1 < len(marcadores) else None
        if proximo and proximo[0] == pagina and proximo[1] == coluna:
            y1 = proximo[2]
        else:
            # Sem marcador seguinte na MESMA coluna, a região termina no último
            # glifo de conteúdo da coluna — não no rodapé da página. Esticar
            # até embaixo fazia as regiões de questões vizinhas se sobreporem,
            # e qualquer checagem de invasão acusava todo mundo.
            col0, col1 = modelo.colunas[coluna]
            marca = set(modelo.marca_dagua) | set(modelo.chrome)
            fundo = [w[3] for w in _palavras(doc[pagina])
                     if col0 <= w[0] <= col1 and w[1] >= y
                     and (w[0], w[1], w[2], w[3]) not in marca]
            y1 = max(fundo) if fundo else modelo.altura * 0.94
        regioes[numero].append(
            RegiaoQuestao(numero=numero, pagina=pagina, coluna=coluna, y0=y, y1=y1)
        )

        # Continuação coluna→coluna EXISTIA aqui (docstring da função ainda
        # descreve o caso), e foi REMOVIDA em 2026-08-27: produzia região
        # inteira bogus sempre que o marcador seguinte na lista global estava
        # "longe" (outra coluna/página) por qualquer motivo — inclusive
        # quando o motivo era só uma coluna sem NENHUM marcador (ex.: 2022
        # pág. 30 col. 1, que pertence ao enunciado longo da Q175, não a
        # nenhuma continuação da Q177) ou um `modelo_pagina` com colunas
        # fantasmas por ruído. Evidência: Q177/2022 herdava uma "continuação"
        # de ~700pt cruzando página, e Q108/118/135 chegavam a herdar 4-5
        # colunas fantasmas. Nenhum caso de continuação real foi confirmado
        # neste corpus — a escolha conservadora (Constituição: não inventar
        # geometria) é não reivindicar coluna nenhuma por proximidade de
        # marcador. Cada questão agora é só a região onde o próprio marcador
        # dela apareceu.
    return dict(regioes)


def resumo(modelos: dict[int, ModeloPagina]) -> dict[str, Any]:
    metodos = collections.Counter(m.metodo for m in modelos.values())
    n_colunas = collections.Counter(len(m.colunas) for m in modelos.values())
    return {
        "paginas": len(modelos),
        "metodo": dict(metodos),
        "colunas_por_pagina": dict(n_colunas),
        "calha_mediana": sorted(
            (m.calhas[0][0] + m.calhas[0][1]) / 2 for m in modelos.values() if m.calhas
        )[len([m for m in modelos.values() if m.calhas]) // 2] if any(m.calhas for m in modelos.values()) else None,
        "glifos_marca_dagua": sum(len(m.marca_dagua) for m in modelos.values()),
    }
