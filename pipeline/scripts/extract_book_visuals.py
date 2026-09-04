"""Auditoria e extração determinística de elementos visuais das provas ENEM
já processadas pelo Sapiens (imagens, tabelas, gráficos, fórmulas).

Sem Gemini, sem qualquer chamada de API externa ou visão de LLM. Toda a
classificação e extração é local:

  - PyMuPDF para abrir o PDF original, localizar imagens raster embutidas,
    ler texto com bounding box por palavra e enumerar objetos vetoriais.
  - Pillow para recodificar os recortes gerados.
  - `matplotlib.mathtext` (offline, sem rede) para renderizar fórmulas que já
    têm LaTeX gravado no banco (`recursos.formulas[].latex`) — não precisa
    tocar no PDF para isso.

Estratégia de classificação (por elemento visual declarado em uma questão):

  EXTRAIVEL_DIRETAMENTE
    - `imagens[]`: já existe exatamente uma imagem raster candidata na(s)
      página(s) do manifesto e a contagem de "questões da página que
      realmente declaram `imagens` não-vazio" bate com a contagem de
      candidatas raster encontradas — igual à heurística de
      `figure_extractor.py`, mas usando `recursos.imagens` real (não o sinal
      ruidoso `manifest.tem_figura`, que mistura tabela/gráfico/imagem).
    - `formulas[]` com `latex` preenchido: renderizado localmente via
      mathtext, não depende do PDF.

  RECORTE_DETERMINISTICO
    - `tabelas[]` / `graficos[]` / `formulas[]` sem `latex`: localizamos a
      faixa vertical da questão na página (entre o marcador "QUESTÃO N" e o
      próximo), extraímos as palavras da página nessa faixa e alinhamos
      contra o texto já conhecido da questão (enunciado + alternativas) com
      `difflib.SequenceMatcher`. O que sobra sem casar (uma lacuna única,
      contígua e de tamanho comedido) é exatamente o conteúdo que o Gemini
      não conseguiu transcrever como texto — normalmente os números de uma
      tabela ou os rótulos de um gráfico. Essa lacuna vira o bounding box do
      recorte, renderizado em alta resolução só daquela região (nunca a
      página inteira).

  NEEDS_MANUAL_REVIEW
    - Qualquer coisa ambígua: página com múltiplas figuras/tabelas/gráficos
      cuja contagem não bate com os candidatos encontrados; lacuna de texto
      ausente, múltipla ou grande demais (ex.: questões em que cada
      alternativa É um gráfico diferente); fórmula sem `latex`; página que
      não foi possível abrir; etc. Nada é adivinhado nesses casos.

Uso:
    .venv/bin/python ../scripts/extract_book_visuals.py classify
    .venv/bin/python ../scripts/extract_book_visuals.py extract

(rodar de dentro de `pipeline/backend`, para usar o mesmo Mongo/.env do
backend; o script também aceita ser chamado de qualquer lugar, indicando
--backend-dir).

Saída (não escreve no Mongo, não altera nenhuma questão):
    pipeline/backend/_storage/sapiens-cognitive/visual_audit/manifest.json
    pipeline/backend/_storage/sapiens-cognitive/visual_audit/assets/<book_id>/<item_id>/<asset_id>.png
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

# Ícone/logo/marca d'água, não uma figura de questão.
_MIN_DIMENSION_PX = 120
# Acima disso a imagem provavelmente é a página inteira escaneada.
_MAX_PAGE_COVERAGE = 0.85
_MAX_LONG_EDGE_PX = 1600
_WEBP_QUALITY = 82

# Limites do heurístico de recorte por lacuna de texto.
_MAX_GAP_WORDS = 40
_MAX_GAP_HEIGHT_PT = 260.0
_MIN_GAP_WORDS = 1
_CROP_PADDING_PT = 10.0
_CROP_DPI = 300


def _norm_word(w: str) -> str:
    w = unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode("ascii")
    w = re.sub(r"[^a-zA-Z0-9]", "", w).lower()
    return w


@dataclass
class VisualCase:
    book_id: str
    item_id: str
    question_number: str
    kind: str  # imagem | tabela | grafico | formula
    asset_ref_id: str  # id declarado (ex IMG-01, TAB-01)
    descricao: str
    pages: list[int]
    classification: str = ""
    reason: str = ""
    bbox: list[float] | None = None
    page_used: int | None = None
    asset_id: str | None = None
    file: str | None = None
    confidence: str = ""
    duplicate_of: str | None = None  # asset_ref_id do elemento original, se for a mesma figura


def _connect_mongo():
    import pymongo

    mongo_url = os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017")
    db_name = os.environ.get("DB_NAME", "sapiens_pipeline")
    client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    return client[db_name]


def _load_books(db) -> dict[str, dict]:
    books = {}
    for b in db.books.find({}):
        books[b["id"]] = b
    return books


def _resolve_book_pdf_path(book: dict, storage_root: Path) -> Path | None:
    files = book.get("files") or []
    for f in files:
        path = f.get("path")
        if path and path.lower().endswith(".pdf"):
            candidate = storage_root / path
            if candidate.exists():
                return candidate
    return None


_WATERMARK_MAX_OCCURRENCES = 12
# Cabeçalho de disciplina ("CN - 2° dia | Caderno 5 - AMARELO - 1ª Aplicação")
# e rodapé/código de barras ("*020125AM10*") do caderno impresso: sempre a
# mesma linha inteira, repetida em toda página — não é conteúdo de questão.
_CHROME_LINE_RE = re.compile(r"diacaderno|aplicacao")
_BARCODE_LINE_RE = re.compile(r"^\*[0-9A-Za-z]+\*$")


def _chrome_boxes(page) -> list[tuple]:
    bad_boxes = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            text = "".join(s.get("text", "") for s in line.get("spans", []))
            if _CHROME_LINE_RE.search(_norm_word(text)) or _BARCODE_LINE_RE.match(text.strip()):
                bad_boxes.append(line["bbox"])
    return bad_boxes


def _strip_chrome_lines(page, words: list[tuple]) -> list[tuple]:
    bad_boxes = _chrome_boxes(page)
    if not bad_boxes:
        return words

    def _in_chrome(w) -> bool:
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        return any(bx[0] - 2 <= cx <= bx[2] + 2 and bx[1] - 2 <= cy <= bx[3] + 2 for bx in bad_boxes)

    return [w for w in words if not _in_chrome(w)]


def _strip_watermark(words: list[tuple]) -> list[tuple]:
    """O caderno impresso tem uma marca d'água repetida dezenas de vezes por
    página ("ENEM 2022" ladrilhado no fundo) que não é conteúdo da questão —
    isso não é uma marca d'água opcional, sem removê-la ela some com a
    detecção de coluna e o casamento de texto. Qualquer token que se repete
    demais numa única página é ruído decorativo, não texto de questão."""
    from collections import Counter

    counts = Counter(_norm_word(w[4]) for w in words)
    return [w for w in words if counts[_norm_word(w[4])] <= _WATERMARK_MAX_OCCURRENCES]


def _detect_column_split(page) -> float | None:
    """Caderno impresso do ENEM costuma ter 2 colunas por página. Palavra
    solta tem indentação/duplicação (marcador de alternativa, camada de
    texto acessível) demais para servir de sinal de coluna — os marcadores
    "QUESTÃO N" são poucos e limpos, então usamos só a posição x deles: se
    formam dois grupos bem separados, o vão entre eles é o vão entre
    colunas. Uma só coluna (ou só 1 questão na página) devolve None."""
    words = page.get_text("words")
    marker_xs = []
    for i, w in enumerate(words):
        if _norm_word(w[4]) == "questao" and i + 1 < len(words) and re.sub(r"\D", "", words[i + 1][4]).isdigit():
            marker_xs.append(w[0])
    xs = sorted({round(x) for x in marker_xs})
    if len(xs) < 2:
        return None
    # x0 de marcador é a margem esquerda da coluna, não o centro do texto —
    # o vão real fica entre o fim do conteúdo da coluna 1 e o início da
    # coluna 2, então o corte correto é o começo da 2ª coluna, não o ponto
    # médio entre as duas margens.
    best_gap, best_start = 0.0, None
    for a, b in zip(xs, xs[1:]):
        gap = b - a
        if gap > best_gap:
            best_gap, best_start = gap, b
    return float(best_start) if best_gap >= 60.0 else None


def _ordered_words(page) -> list[tuple]:
    """Palavras da página (x0,y0,x1,y1,word,block,line,word_no) na ordem de
    leitura real: coluna esquerda de cima a baixo, depois coluna direita de
    cima a baixo (layout padrão do caderno impresso). Em página de coluna
    única, é simplesmente topo→base."""
    words = _strip_chrome_lines(page, _strip_watermark(page.get_text("words")))
    split = _detect_column_split(page)
    if split is None:
        return sorted(words, key=lambda w: (round(w[1], 1), w[0]))
    left = sorted((w for w in words if w[0] < split), key=lambda w: (round(w[1], 1), w[0]))
    right = sorted((w for w in words if w[0] >= split), key=lambda w: (round(w[1], 1), w[0]))
    return left + right


def _question_band(
    ordered: list[tuple], question_number: str, next_question_number: str | None
) -> tuple[int, int] | None:
    """Índices [start, end) em `ordered` que pertencem à questão, delimitados
    pelos marcadores "QUESTÃO N" (início) e "QUESTÃO N+1" (fim) — respeitando
    a ordem de leitura real (por coluna), não a coordenada y bruta."""
    start_idx = None
    end_idx = len(ordered)
    for i, w in enumerate(ordered):
        token = _norm_word(w[4])
        if token == "questao" and i + 1 < len(ordered):
            num_tok = re.sub(r"\D", "", ordered[i + 1][4])
            if num_tok == str(question_number) and start_idx is None:
                start_idx = i + 2
            elif start_idx is not None and next_question_number and num_tok == str(next_question_number):
                end_idx = i
                break
    if start_idx is None:
        return None
    return start_idx, end_idx


def _band_geometry(ordered: list[tuple], band: tuple[int, int], page) -> tuple[float, float, float, float]:
    """Retângulo [x0,y0,x1,y1] que contém toda a questão na página — usado só
    para FILTRAR quais desenhos vetoriais podem pertencer a ela (nunca vira o
    recorte final sozinho). Cobre da palavra "QUESTÃO N" até a próxima
    "QUESTÃO N+1" (ou o fim da página/coluna), incluindo x0/x1 da coluna
    inteira, porque um desenho sem texto (puramente vetorial) não aparece na
    lista de palavras e um bbox baseado só nelas o cortaria fora."""
    start_idx, end_idx = band
    marker = ordered[start_idx - 2] if start_idx >= 2 else None
    y0 = marker[1] if marker else 0.0
    split = _detect_column_split(page)

    def _col(x: float) -> int:
        return 0 if split is None or x < split else 1

    start_col = _col(marker[0]) if marker else 0
    end_marker = ordered[end_idx] if end_idx < len(ordered) else None
    # Marcador de fim só delimita y1 se estiver na MESMA coluna — se a
    # próxima questão já é da coluna seguinte, esta é a última da sua
    # coluna e vai até o fim da página (nunca até um y menor, de uma
    # coluna física diferente, que inverteria o retângulo).
    if end_marker is not None and _col(end_marker[0]) == start_col:
        y1 = end_marker[1]
    else:
        y1 = page.rect.height

    band_words = ordered[start_idx:end_idx]
    xs = [w[0] for w in band_words] + [w[2] for w in band_words]
    if marker:
        xs += [marker[0]]
    if split is not None:
        x0 = 0.0 if start_col == 0 else split
        x1 = split if start_col == 0 else page.rect.width
    else:
        x0 = min(xs) - 5.0 if xs else 0.0
        x1 = max(xs) + 5.0 if xs else page.rect.width
    return x0, y0, x1, y1


_MIN_CLUSTER_AREA_PT2 = 500.0
_MIN_CLUSTER_SIDE_PT = 15.0
_CLUSTER_MERGE_GAP_PT = 12.0
# Moldura/borda decorativa da página inteira (comum em cadernos impressos,
# desenhada como um único retângulo vetorial contínuo) não pode virar "o
# diagrama" — mesma ideia do `_MAX_PAGE_COVERAGE` do raster, mas mais
# rigorosa: um diagrama de verdade não ocupa a página inteira.
_MAX_CLUSTER_PAGE_FRACTION = 0.35
_MAX_CLUSTER_DIM_FRACTION = 0.85


def _bbox_exceeds_page_limits(bbox: list[float], page) -> bool:
    """Mesmo teto de `_vector_clusters_in_band`, aplicado ao bbox FINAL (depois
    de absorver desenho/texto vizinho) — absorver rótulo não pode transformar
    um recorte pequeno num quase-página."""
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    page_area = abs(page.rect) or 1.0
    if w * h > _MAX_CLUSTER_PAGE_FRACTION * page_area:
        return True
    return w > page.rect.width * _MAX_CLUSTER_DIM_FRACTION or h > page.rect.height * _MAX_CLUSTER_DIM_FRACTION


def _vector_clusters_in_band(page, band_rect: tuple[float, float, float, float]) -> list[list[float]]:
    """Agrupa os desenhos vetoriais da página (excluindo cabeçalho/rodapé e
    marcadores de alternativa — quadradinhos minúsculos, linhas separadoras)
    em clusters conectados por proximidade, restritos ao retângulo da
    questão. Um diagrama puramente vetorial (sem texto que "sobre" como
    lacuna) não tem outro jeito determinístico de ser localizado: as linhas
    que o compõem formam um grupo denso e isolado do resto da página."""
    bx0, by0, bx1, by1 = band_rect
    try:
        drawings = page.get_drawings()
    except Exception:
        return []
    rects = []
    for d in drawings:
        r = d.get("rect")
        if r is None or r.is_empty:
            continue
        if r.x1 < bx0 or r.x0 > bx1 or r.y1 < by0 or r.y0 > by1:
            continue
        rects.append([r.x0, r.y0, r.x1, r.y1])

    # União por proximidade (union-find ingênuo: O(n^2), n é pequeno por página).
    n = len(rects)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            ax0, ay0, ax1, ay1 = rects[i]
            bx0_, by0_, bx1_, by1_ = rects[j]
            if ax0 - _CLUSTER_MERGE_GAP_PT <= bx1_ and bx0_ - _CLUSTER_MERGE_GAP_PT <= ax1 and \
               ay0 - _CLUSTER_MERGE_GAP_PT <= by1_ and by0_ - _CLUSTER_MERGE_GAP_PT <= ay1:
                union(i, j)

    groups: dict[int, list[float]] = {}
    for i, rect in enumerate(rects):
        root = find(i)
        if root not in groups:
            groups[root] = list(rect)
        else:
            g = groups[root]
            g[0], g[1] = min(g[0], rect[0]), min(g[1], rect[1])
            g[2], g[3] = max(g[2], rect[2]), max(g[3], rect[3])

    page_area = abs(page.rect) or 1.0
    max_w = page.rect.width * _MAX_CLUSTER_DIM_FRACTION
    max_h = page.rect.height * _MAX_CLUSTER_DIM_FRACTION
    clusters = []
    for g in groups.values():
        w, h = g[2] - g[0], g[3] - g[1]
        area = w * h
        if area < _MIN_CLUSTER_AREA_PT2 or w < _MIN_CLUSTER_SIDE_PT or h < _MIN_CLUSTER_SIDE_PT:
            continue
        if area > _MAX_CLUSTER_PAGE_FRACTION * page_area or w > max_w or h > max_h:
            continue  # provável moldura/borda da página, não um diagrama
        clusters.append(g)
    clusters.sort(key=lambda g: (g[2] - g[0]) * (g[3] - g[1]), reverse=True)
    return clusters


def _absorb_nearby_words(page, bbox: list[float], reference_tokens: list[str], pad: float = 14.0) -> list[float]:
    """Rótulos de texto (átomo, unidade, legenda) perto de um cluster vetorial
    são parte do mesmo desenho — estica o bbox pra incluir qualquer palavra
    da página que não pertença ao texto já conhecido da questão e esteja
    logo ao redor do cluster (não a página toda: só a vizinhança imediata)."""
    x0, y0, x1, y1 = bbox
    ref = set(t for t in reference_tokens if t)
    changed = True
    guard = 0
    while changed and guard < 4:
        changed = False
        guard += 1
        for w in page.get_text("words"):
            wx0, wy0, wx1, wy1, text = w[0], w[1], w[2], w[3], w[4]
            if wx1 < x0 - pad or wx0 > x1 + pad or wy1 < y0 - pad or wy0 > y1 + pad:
                continue
            if _norm_word(text) in ref:
                continue
            nx0, ny0, nx1, ny1 = min(x0, wx0), min(y0, wy0), max(x1, wx1), max(y1, wy1)
            if (nx0, ny0, nx1, ny1) != (x0, y0, x1, y1):
                x0, y0, x1, y1 = nx0, ny0, nx1, ny1
                changed = True
    return [x0, y0, x1, y1]


_MIN_CLUSTER_AREA_BY_KIND_PT2 = {
    # Tabela sem borda vetorial (só texto alinhado) não deixa cluster real —
    # um cluster minúsculo "achado" pra ela quase sempre é um quadradinho de
    # alternativa de outra questão, não a tabela. Uma tabela com grade
    # vetorial de verdade é bem maior que isso.
    "tabela": 6000.0,
}

# Fotografia (retrato/paisagem/cena real) nunca é desenho vetorial — se a
# extração raster não achou nada, um cluster de linhas não é a foto, é
# coincidência. Só tenta recorte por texto/vetor para ilustração/diagrama.
_PHOTO_KEYWORDS = ("foto",)  # "fotografia"/"fotográfico(a)" já casam por "foto" ser prefixo


def _try_vector_cluster_crop(
    page, numero: str, next_num: int | None, questao: dict, n_expected: int = 1,
    kind: str = "imagem", descricao: str = "",
) -> list[list[float]] | None:
    """Último recurso quando não há raster nem lacuna de texto: localiza o(s)
    maior(es) cluster(s) de desenho vetorial dentro da faixa da questão. Só
    devolve algo quando o número de clusters significativos bate exatamente
    com `n_expected` (quantos elementos precisam de bbox) — do contrário,
    None (sem chute)."""
    if any(k in _norm_word(descricao) for k in _PHOTO_KEYWORDS):
        return None
    ordered = _ordered_words(page)
    band = _question_band(ordered, numero, str(next_num) if next_num else None)
    if band is None:
        return None
    band_rect = _band_geometry(ordered, band, page)
    clusters = _vector_clusters_in_band(page, band_rect)
    min_area = _MIN_CLUSTER_AREA_BY_KIND_PT2.get(kind)
    if min_area:
        clusters = [c for c in clusters if (c[2] - c[0]) * (c[3] - c[1]) >= min_area]
    if len(clusters) != n_expected:
        return None
    ref_tokens, _ = _reference_tokens(questao)
    # ordem de leitura: topo -> base
    clusters.sort(key=lambda c: c[1])
    out = []
    for c in clusters:
        # Não roda `_expand_with_drawings` aqui: o cluster já é o resultado
        # de mesclar por proximidade TODOS os desenhos vizinhos — reexpandir
        # arrisca encadear com outra coisa da página (ex.: quadradinhos de
        # alternativa da questão seguinte) sem o teto de tamanho do cluster.
        absorbed = _absorb_nearby_words(page, list(c), ref_tokens)
        padded = _pad_bbox(absorbed, page.rect)
        if _bbox_exceeds_page_limits(padded, page):
            return None  # rótulo vizinho estourou o teto: não confia mais no grupo inteiro
        out.append(padded)
    return out


def _extract_page_raster_candidates(page) -> list[dict]:
    page_area = abs(page.rect) or 1.0
    seen: set[int] = set()
    out = []
    for img in page.get_images(full=True):
        xref = img[0]
        if xref in seen:
            continue
        seen.add(xref)
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        bbox_area = max((abs(r) for r in rects), default=0.0)
        if bbox_area and (bbox_area / page_area) > _MAX_PAGE_COVERAGE:
            continue
        try:
            extracted = page.parent.extract_image(xref)
        except Exception:
            continue
        w, h = extracted.get("width", 0), extracted.get("height", 0)
        if w < _MIN_DIMENSION_PX or h < _MIN_DIMENSION_PX:
            continue
        y0 = min((r.y0 for r in rects), default=0.0)
        rect = rects[0] if rects else None
        out.append({"xref": xref, "raw": extracted["image"], "width": w, "height": h, "y0": y0, "rect": rect})
    return out


def _gap_bbox_for_visual(
    ordered: list[tuple],
    band: tuple[int, int],
    reference_tokens: list[str],
    enun_token_count: int,
) -> tuple[list[float], int] | None:
    """Alinha as palavras da questão (já na ordem de leitura real, ver
    `_ordered_words`/`_question_band`) contra o texto já conhecido (enunciado
    + alternativas); devolve o bbox da maior lacuna não casada e a contagem
    de palavras da lacuna, ou None se não há lacuna utilizável."""
    start_idx, end_idx = band
    words = ordered[start_idx:end_idx]
    page_tokens = [_norm_word(w[4]) for w in words]
    page_tokens_nonempty_idx = [i for i, t in enumerate(page_tokens) if t]
    a = [page_tokens[i] for i in page_tokens_nonempty_idx]
    b = [t for t in reference_tokens if t]

    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    blocks = sm.get_matching_blocks()

    gaps = []  # (a_start_idx_in_words, a_end_idx_in_words) exclusive, in `a` index space
    prev_end = 0
    for blk in blocks:
        if blk.a > prev_end:
            gaps.append((prev_end, blk.a))
        prev_end = blk.a + blk.size

    # As alternativas (A-E) costumam repetir a mesma frase-molde variando só
    # 1-2 palavras (com frequência frases curtas de química/matemática) — o
    # alinhamento aí é ambíguo por natureza e pode "sobrar" como lacuna sem
    # ser figura nenhuma. Elemento visual real do ENEM sempre fica dentro do
    # enunciado, nunca dentro do bloco de alternativas — então nem considera
    # lacuna que já entrou na região onde o texto passou a casar com as
    # alternativas.
    alt_boundary = next((blk.a for blk in blocks if blk.size and blk.b + blk.size > enun_token_count), len(a))
    # Tamanho de TODA lacuna da faixa (antes e depois da fronteira) mede o
    # quanto de conteúdo realmente ficou sem casar na questão inteira —
    # usado abaixo para rejeitar um resto pequeno antes da fronteira quando
    # a maior parte do não-casado está depois dela (sinal de que o visual
    # de verdade atravessa pra dentro do bloco de alternativas, caso em que
    # não dá pra isolar com segurança — ex.: gráfico diferente por
    # alternativa, onde rótulos de eixo tipo "T0" coincidem à toa com o
    # enunciado e fragmentam o casamento).
    total_unmatched = sum(ge - gs for gs, ge in gaps if ge - gs >= _MIN_GAP_WORDS)
    gaps = [(gs, ge) for gs, ge in gaps if ge <= alt_boundary]

    # Traduz índices em `a` (só palavras não-vazias) de volta para índices em `words`.
    real_gaps = []
    for gs, ge in gaps:
        if ge - gs < _MIN_GAP_WORDS:
            continue
        word_idx_start = page_tokens_nonempty_idx[gs]
        word_idx_end = page_tokens_nonempty_idx[ge - 1]
        real_gaps.append((word_idx_start, word_idx_end, ge - gs))

    if not real_gaps:
        return None

    # Referência bibliográfica da fonte ("Disponível em... (Adaptado).") é
    # texto real que o Gemini também costuma não transcrever no enunciado —
    # sobra como lacuna igual a uma tabela/gráfico, mas não é um elemento
    # visual da questão. Descarta esses candidatos antes de escolher.
    def _looks_like_citation(word_idx_start: int, word_idx_end: int) -> bool:
        seq = page_tokens[word_idx_start : word_idx_end + 1]
        toks = set(seq)
        if "adaptado" in toks or "disponivel" in toks:
            return True
        return any(a == "et" and b == "al" for a, b in zip(seq, seq[1:]))

    real_gaps = [g for g in real_gaps if not _looks_like_citation(g[0], g[1])]
    if not real_gaps:
        return None

    # Ruído de tokenização (pontuação diferente, "d.d.p." vs "ddp") e a
    # duplicação de letra de alternativa no PDF ("B" sozinho + "B" colado no
    # texto) sempre deixam lacunas de 1-2 palavras que não são o elemento
    # visual em si. Só considera achado quando há UMA lacuna claramente
    # dominante — grande o bastante e destacada das demais — para não
    # arriscar recortar um fragmento de pontuação como se fosse a figura.
    real_gaps.sort(key=lambda g: g[2], reverse=True)
    biggest = real_gaps[0]
    runner_up = real_gaps[1][2] if len(real_gaps) > 1 else 0
    if biggest[2] < 3 or biggest[2] < 3 * max(runner_up, 1):
        return None
    # Se a maior parte do texto não-casado da questão está DEPOIS da
    # fronteira com as alternativas (que a gente já exclui por segurança),
    # esse resto pequeno antes dela não é o visual inteiro — é só a ponta
    # que sobrou antes de o casamento fragmentado "acertar" um símbolo à
    # toa. Exige que a lacuna escolhida seja a maioria do não-casado total.
    if total_unmatched > 0 and biggest[2] < 0.5 * total_unmatched:
        return None

    ws, we, n = biggest
    if n > _MAX_GAP_WORDS:
        return None
    gap_words = words[ws : we + 1]
    x0 = min(w[0] for w in gap_words)
    gy0 = min(w[1] for w in gap_words)
    x1 = max(w[2] for w in gap_words)
    gy1 = max(w[3] for w in gap_words)
    if (gy1 - gy0) > _MAX_GAP_HEIGHT_PT:
        return None
    # Lacuna não pode ter "voltado" no y (sinal de que atravessou colunas
    # diferentes na ordem de leitura, o que invalida um bbox retangular).
    ys = [w[1] for w in gap_words]
    if ys != sorted(ys) and (max(ys) - min(ys)) > _MAX_GAP_HEIGHT_PT / 2:
        return None
    return [x0, gy0, x1, gy1], n


_MAX_EXPANDED_HEIGHT_PT = 460.0


def _expand_with_drawings(page, bbox: list[float]) -> list[float]:
    """Diagrama de caixas e setas (fluxograma, esquema) é vetorial: o texto
    só cobre os rótulos, não as caixas/setas em si. Se a caixa/legenda do
    topo do diagrama não entrou no enunciado (logo não virou "lacuna"), o
    recorte por texto corta o diagrama pela metade. Aqui a gente estica o
    bbox para incluir qualquer desenho vetorial encostado nele — até um
    teto, para não engolir conteúdo de outra questão."""
    x0, y0, x1, y1 = bbox
    try:
        drawings = page.get_drawings()
    except Exception:
        return bbox
    changed = True
    guard = 0
    while changed and guard < 6:
        changed = False
        guard += 1
        for d in drawings:
            r = d.get("rect")
            if r is None or r.is_empty:
                continue
            pad = 8.0
            if r.x1 < x0 - pad or r.x0 > x1 + pad or r.y1 < y0 - pad or r.y0 > y1 + pad:
                continue
            nx0, ny0, nx1, ny1 = min(x0, r.x0), min(y0, r.y0), max(x1, r.x1), max(y1, r.y1)
            if (ny1 - ny0) > _MAX_EXPANDED_HEIGHT_PT or (nx1 - nx0) > page.rect.width:
                continue
            if (nx0, ny0, nx1, ny1) != (x0, y0, x1, y1):
                x0, y0, x1, y1 = nx0, ny0, nx1, ny1
                changed = True
    return [x0, y0, x1, y1]


def _pad_bbox(bbox: list[float], page_rect, pad: float = _CROP_PADDING_PT) -> list[float]:
    x0, y0, x1, y1 = bbox
    return [
        max(0.0, x0 - pad),
        max(0.0, y0 - pad),
        min(page_rect.width, x1 + pad),
        min(page_rect.height, y1 + pad),
    ]


def _slug(item_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", item_id)


def _reference_tokens(questao: dict) -> tuple[list[str], int]:
    """Devolve (tokens de enunciado+alternativas, quantos desses tokens são
    do enunciado) — a fronteira é usada para nunca deixar o recorte invadir
    o bloco de alternativas."""
    enun_tokens = [t for t in (_norm_word(w) for w in re.findall(r"\w+", questao.get("enunciado") or "")) if t]
    alt_tokens: list[str] = []
    for alt in questao.get("alternativas") or []:
        letra = _norm_word(alt.get("letra") or "")
        # o caderno imprime a letra da alternativa duas vezes (marcador +
        # rótulo), então casamos as duas para não sobrar como "lacuna".
        if letra:
            alt_tokens += [letra, letra]
        alt_tokens += [_norm_word(w) for w in re.findall(r"\w+", alt.get("texto") or "")]
    return enun_tokens + [t for t in alt_tokens if t], len(enun_tokens)


def _try_gap_crop(
    page, numero: str, next_num: int | None, questao: dict
) -> tuple[list[float], int, str] | None:
    """Tenta o recorte determinístico por lacuna de texto. Devolve
    (bbox_com_padding, n_palavras_da_lacuna, motivo) ou None se a página/
    lacuna não permitir um recorte seguro."""
    ordered = _ordered_words(page)
    band = _question_band(ordered, numero, str(next_num) if next_num else None)
    if band is None:
        return None
    ref_tokens, enun_count = _reference_tokens(questao)
    gap = _gap_bbox_for_visual(ordered, band, ref_tokens, enun_count)
    if gap is None:
        return None
    bbox, nwords = gap
    bbox = _expand_with_drawings(page, bbox)
    padded = _pad_bbox(bbox, page.rect)
    # Não deixa o padding comer cabeçalho/rodapé logo abaixo do recorte.
    for cx0, cy0, cx1, cy1 in _chrome_boxes(page):
        if cy0 >= bbox[3] and cx0 < padded[2] and cx1 > padded[0]:
            padded[3] = min(padded[3], max(bbox[3], cy0 - 2.0))
    if _bbox_exceeds_page_limits(padded, page):
        return None  # expansão por desenho vizinho estourou o teto: não confia
    return padded, nwords, f"lacuna de {nwords} palavra(s) não presentes no enunciado/alternativas"


def build_cases(db, storage_root: Path) -> tuple[list[VisualCase], dict[str, Any]]:
    books = _load_books(db)
    pdf_cache: dict[str, Any] = {}
    import pymupdf

    def get_doc(book_id: str):
        if book_id not in pdf_cache:
            book = books.get(book_id)
            path = _resolve_book_pdf_path(book, storage_root) if book else None
            pdf_cache[book_id] = pymupdf.open(str(path)) if path else None
        return pdf_cache[book_id]

    items = list(db.pipelines.find({}))
    # agrupa por (book_id, pagina) para saber quem mais divide a página
    by_book_page: dict[tuple[str, int], list[dict]] = {}
    for it in items:
        item = it.get("item") or {}
        fonte = item.get("fonte") or {}
        pagina = fonte.get("pagina")
        book_id = it.get("book_id")
        if pagina is None or not book_id:
            continue
        by_book_page.setdefault((book_id, int(pagina)), []).append(it)

    cases: list[VisualCase] = []
    stats = {"questoes_processadas": 0, "questoes_sem_pagina": 0, "pdf_ausente": set()}

    numbers_by_book = {}
    for it in items:
        book_id = it.get("book_id")
        num = str(it.get("question_number") or (it.get("item") or {}).get("fonte", {}).get("numero") or "").strip()
        if book_id and num:
            numbers_by_book.setdefault(book_id, set()).add(num)

    for it in items:
        item = it.get("item") or {}
        fonte = item.get("fonte") or {}
        questao = item.get("questao") or {}
        recursos = questao.get("recursos") or {}
        item_id = it.get("item_id")
        book_id = it.get("book_id")
        numero = str(fonte.get("numero") or it.get("question_number") or "").strip()
        pagina = fonte.get("pagina")
        stats["questoes_processadas"] += 1
        if pagina is None or not book_id or not numero:
            stats["questoes_sem_pagina"] += 1
            continue
        pagina = int(pagina)

        doc = get_doc(book_id)
        if doc is None:
            stats["pdf_ausente"].add(book_id)
            page = None
        else:
            idx = pagina - 1
            page = doc[idx] if 0 <= idx < doc.page_count else None

        sharers = by_book_page.get((book_id, pagina), [])
        nums = sorted((int(n) for n in numbers_by_book.get(book_id, set()) if n.isdigit()))
        try:
            next_num = next(n for n in nums if n > int(numero))
        except StopIteration:
            next_num = None

        # --- imagens ---
        imagens = recursos.get("imagens") or []
        missing_imgs = [(i, im) for i, im in enumerate(imagens) if not (im or {}).get("arquivo")]
        if missing_imgs and page is not None:
            real_image_sharers = [
                s
                for s in sharers
                if (((s.get("item") or {}).get("questao") or {}).get("recursos") or {}).get("imagens")
            ]
            candidates = _extract_page_raster_candidates(page)
            for i, im in missing_imgs:
                case = VisualCase(
                    book_id=book_id,
                    item_id=item_id,
                    question_number=numero,
                    kind="imagem",
                    asset_ref_id=im.get("id") or f"IMG-{i+1:02d}",
                    descricao=im.get("descricao") or "",
                    pages=[pagina],
                )
                if len(real_image_sharers) <= 1:
                    chosen = candidates
                else:
                    if len(candidates) != len(real_image_sharers):
                        chosen = []
                    else:
                        rank = next(
                            (
                                j
                                for j, s in enumerate(real_image_sharers)
                                if s.get("item_id") == item_id
                            ),
                            None,
                        )
                        ordered = sorted(candidates, key=lambda c: c["y0"])
                        chosen = [ordered[rank]] if rank is not None else []
                if len(chosen) == 1:
                    case.classification = "EXTRAIVEL_DIRETAMENTE"
                    case.reason = "imagem raster única e inambígua na página"
                    case.page_used = pagina
                    case.bbox = [chosen[0]["rect"].x0, chosen[0]["rect"].y0, chosen[0]["rect"].x1, chosen[0]["rect"].y1] if chosen[0].get("rect") else None
                    case.confidence = "alta"
                    case._raster = chosen[0]  # type: ignore[attr-defined]
                elif len(chosen) > 1:
                    case.classification = "NEEDS_MANUAL_REVIEW"
                    case.reason = f"{len(chosen)} imagens candidatas para 1 declarada"
                else:
                    # sem candidata raster: pode ser um diagrama/estrutura
                    # desenhado como vetor (não como bitmap). Tenta o mesmo
                    # recorte por lacuna de texto usado para tabelas/gráficos;
                    # se não achar, tenta localizar o(s) cluster(s) de desenho
                    # vetorial da questão (último recurso, só quando o número
                    # de clusters bate exatamente com o de imagens faltando).
                    if len(missing_imgs) == 1:
                        gap = _try_gap_crop(page, numero, next_num, questao)
                        if gap is not None:
                            bbox, nwords, reason = gap
                            case.classification = "RECORTE_DETERMINISTICO"
                            case.reason = reason
                            case.bbox = bbox
                            case.page_used = pagina
                            case.confidence = "media"
                        else:
                            vec = _try_vector_cluster_crop(
                                page, numero, next_num, questao, n_expected=1,
                                kind="imagem", descricao=im.get("descricao") or "",
                            )
                            if vec:
                                case.classification = "RECORTE_DETERMINISTICO"
                                case.reason = "cluster único de desenho vetorial isolado na faixa da questão"
                                case.bbox = vec[0]
                                case.page_used = pagina
                                case.confidence = "media"
                            else:
                                case.classification = "NEEDS_MANUAL_REVIEW"
                                case.reason = "sem imagem raster na página e nenhuma lacuna de texto ou cluster vetorial utilizável"
                    else:
                        vec = _try_vector_cluster_crop(
                            page, numero, next_num, questao, n_expected=len(missing_imgs), kind="imagem",
                        )
                        if vec and i < len(vec):
                            case.classification = "RECORTE_DETERMINISTICO"
                            case.reason = f"cluster {i+1}/{len(vec)} de desenho vetorial (contagem bate com {len(missing_imgs)} imagens declaradas)"
                            case.bbox = vec[i]
                            case.page_used = pagina
                            case.confidence = "media"
                        else:
                            case.classification = "NEEDS_MANUAL_REVIEW"
                            case.reason = f"{len(missing_imgs)} imagens declaradas na questão sem raster correspondente"
                cases.append(case)
        elif missing_imgs and page is None:
            for i, im in missing_imgs:
                cases.append(
                    VisualCase(
                        book_id=book_id, item_id=item_id, question_number=numero, kind="imagem",
                        asset_ref_id=im.get("id") or f"IMG-{i+1:02d}", descricao=im.get("descricao") or "",
                        pages=[pagina], classification="NEEDS_MANUAL_REVIEW", reason="PDF do caderno não encontrado",
                    )
                )

        # --- formulas ---
        formulas = recursos.get("formulas") or []
        for i, fo in enumerate(formulas):
            latex = (fo or {}).get("latex")
            case = VisualCase(
                book_id=book_id, item_id=item_id, question_number=numero, kind="formula",
                asset_ref_id=fo.get("id") or f"FOR-{i+1:02d}", descricao=latex or "", pages=[pagina],
            )
            if latex:
                case.classification = "EXTRAIVEL_DIRETAMENTE"
                case.reason = "latex já presente no banco, renderização local via mathtext"
                case.confidence = "alta"
                case._latex = latex  # type: ignore[attr-defined]
            elif page is not None and len(formulas) == 1:
                gap = _try_gap_crop(page, numero, next_num, questao)
                if gap is not None:
                    bbox, nwords, reason = gap
                    case.classification = "RECORTE_DETERMINISTICO"
                    case.reason = reason
                    case.bbox = bbox
                    case.page_used = pagina
                    case.confidence = "media"
                else:
                    vec = _try_vector_cluster_crop(page, numero, next_num, questao, n_expected=1, kind="formula")
                    if vec:
                        case.classification = "RECORTE_DETERMINISTICO"
                        case.reason = "cluster único de desenho vetorial isolado na faixa da questão"
                        case.bbox = vec[0]
                        case.page_used = pagina
                        case.confidence = "media"
                    else:
                        case.classification = "NEEDS_MANUAL_REVIEW"
                        case.reason = "fórmula sem latex e sem lacuna de texto ou cluster vetorial utilizável"
            else:
                case.classification = "NEEDS_MANUAL_REVIEW"
                case.reason = "fórmula sem latex registrado" if page is None else f"{len(formulas)} fórmulas na mesma questão sem latex"
            cases.append(case)

        # --- tabelas / graficos (recorte por lacuna de texto) ---
        for kind, key in (("tabela", "tabelas"), ("grafico", "graficos")):
            entries = recursos.get(key) or []
            if not entries:
                continue
            if page is None:
                for i, e in enumerate(entries):
                    cases.append(
                        VisualCase(
                            book_id=book_id, item_id=item_id, question_number=numero, kind=kind,
                            asset_ref_id=e.get("id") or f"{key[:3].upper()}-{i+1:02d}",
                            descricao=e.get("descricao") or "", pages=[pagina],
                            classification="NEEDS_MANUAL_REVIEW", reason="PDF do caderno não encontrado",
                        )
                    )
                continue

            if len(entries) > 1:
                # mais de um elemento do mesmo tipo na mesma questão: só
                # ordena se achar exatamente esse número de clusters vetoriais
                # isolados na faixa da questão — senão não arrisca.
                vec = _try_vector_cluster_crop(page, numero, next_num, questao, n_expected=len(entries), kind=kind)
                for i, e in enumerate(entries):
                    case = VisualCase(
                        book_id=book_id, item_id=item_id, question_number=numero, kind=kind,
                        asset_ref_id=e.get("id") or f"{key[:3].upper()}-{i+1:02d}",
                        descricao=e.get("descricao") or "", pages=[pagina],
                    )
                    if vec and i < len(vec):
                        case.classification = "RECORTE_DETERMINISTICO"
                        case.reason = f"cluster {i+1}/{len(vec)} de desenho vetorial (contagem bate com {len(entries)} elementos '{key}')"
                        case.bbox = vec[i]
                        case.page_used = pagina
                        case.confidence = "media"
                    else:
                        case.classification = "NEEDS_MANUAL_REVIEW"
                        case.reason = f"{len(entries)} elementos '{key}' na mesma questão"
                    cases.append(case)
                continue

            e = entries[0]
            case = VisualCase(
                book_id=book_id, item_id=item_id, question_number=numero, kind=kind,
                asset_ref_id=e.get("id") or f"{key[:3].upper()}-01", descricao=e.get("descricao") or "", pages=[pagina],
            )
            gap = _try_gap_crop(page, numero, next_num, questao)
            if gap is not None:
                bbox, nwords, reason = gap
                case.classification = "RECORTE_DETERMINISTICO"
                case.reason = reason
                case.bbox = bbox
                case.page_used = pagina
                case.confidence = "media"
            else:
                vec = _try_vector_cluster_crop(
                    page, numero, next_num, questao, n_expected=1, kind=kind, descricao=e.get("descricao") or "",
                )
                if vec:
                    case.classification = "RECORTE_DETERMINISTICO"
                    case.reason = "cluster único de desenho vetorial isolado na faixa da questão"
                    case.bbox = vec[0]
                    case.page_used = pagina
                    case.confidence = "media"
                else:
                    case.classification = "NEEDS_MANUAL_REVIEW"
                    case.reason = "não foi possível localizar a faixa da questão, nenhuma lacuna de texto, nem cluster vetorial isolado"
            cases.append(case)

    _dedupe_same_question(cases)
    return cases, stats


def _bbox_iou(a: list[float], b: list[float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _dedupe_same_question(cases: list[VisualCase]) -> None:
    """O Gemini às vezes descreve o mesmo elemento em duas chaves de
    `recursos` (ex.: como `imagens` e de novo como `graficos`) — o recorte
    determinístico então acha a mesma região da página duas vezes. Marca a
    segunda ocorrência como duplicata do mesmo asset em vez de gerar (e
    contar) um arquivo repetido — 'não duplicar imagens' é regra do produto,
    não só economia de disco."""
    by_item: dict[str, list[VisualCase]] = {}
    for c in cases:
        if c.classification in ("EXTRAIVEL_DIRETAMENTE", "RECORTE_DETERMINISTICO") and c.bbox and c.page_used:
            by_item.setdefault(c.item_id, []).append(c)
    for group in by_item.values():
        for i, a in enumerate(group):
            if a.duplicate_of:
                continue
            for b in group[i + 1 :]:
                if b.duplicate_of or b.page_used != a.page_used:
                    continue
                if _bbox_iou(a.bbox, b.bbox) > 0.4:
                    b.duplicate_of = a.asset_ref_id
                    b.reason = f"mesmo elemento visual já capturado como {a.kind}/{a.asset_ref_id} (bbox equivalente)"


def _render_raster(case: VisualCase, out_path: Path) -> None:
    from PIL import Image
    import io

    raw = case._raster["raw"]  # type: ignore[attr-defined]
    img = Image.open(io.BytesIO(raw))
    img.load()
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > _MAX_LONG_EDGE_PX:
        scale = _MAX_LONG_EDGE_PX / long_edge
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")


def _render_formula(case: VisualCase, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    latex = case._latex  # type: ignore[attr-defined]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(0.01, 0.01))
    try:
        fig.text(0, 0, f"${latex}$", fontsize=22)
        fig.savefig(
            out_path, dpi=200, bbox_inches="tight", pad_inches=0.08, transparent=True,
        )
    finally:
        plt.close(fig)


def _render_crop(doc, case: VisualCase, out_path: Path) -> None:
    import pymupdf

    page = doc[case.page_used - 1]
    rect = pymupdf.Rect(*case.bbox)
    zoom = _CROP_DPI / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))


def run(mode: str, backend_dir: Path) -> None:
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))
    from dotenv import load_dotenv

    load_dotenv(backend_dir / ".env")

    db = _connect_mongo()
    storage_root = backend_dir / "_storage"
    audit_root = storage_root / "sapiens-cognitive" / "visual_audit"
    assets_root = audit_root / "assets"

    cases, stats = build_cases(db, storage_root)

    import pymupdf

    doc_cache: dict[str, Any] = {}

    def get_doc(book_id: str):
        if book_id not in doc_cache:
            books = _load_books(db)
            book = books.get(book_id)
            path = _resolve_book_pdf_path(book, storage_root)
            doc_cache[book_id] = pymupdf.open(str(path)) if path else None
        return doc_cache[book_id]

    extracted = 0
    duplicates = 0
    if mode == "extract":
        primary_lookup: dict[tuple[str, str], VisualCase] = {}
        for c in cases:
            if c.classification not in ("EXTRAIVEL_DIRETAMENTE", "RECORTE_DETERMINISTICO") or c.duplicate_of:
                continue
            asset_id = f"{c.kind[:3].upper()}-{c.asset_ref_id}"
            out_path = assets_root / c.book_id / _slug(c.item_id) / f"{_slug(asset_id)}.png"
            try:
                if c.kind == "imagem" and hasattr(c, "_raster"):
                    _render_raster(c, out_path)
                elif c.kind == "formula" and hasattr(c, "_latex"):
                    _render_formula(c, out_path)
                else:
                    # "imagem"/"tabela"/"grafico" resolvidos pelo recorte de
                    # lacuna de texto (não raster nativo) sempre caem aqui,
                    # independente do `kind` declarado pelo Gemini.
                    doc = get_doc(c.book_id)
                    if doc is None:
                        raise RuntimeError("pdf ausente no momento da extração")
                    _render_crop(doc, c, out_path)
                c.asset_id = asset_id
                c.file = str(out_path.relative_to(audit_root))
                extracted += 1
                primary_lookup[(c.item_id, c.asset_ref_id)] = c
            except Exception as exc:  # nunca deve derrubar o lote inteiro
                c.classification = "NEEDS_MANUAL_REVIEW"
                c.reason = f"falha na extração: {exc}"

        # Duplicatas (mesmo elemento descrito 2x pelo Gemini, ex. em
        # `imagens` e `graficos`) reaproveitam o asset já gerado — nunca
        # geram um segundo arquivo para a mesma figura.
        for c in cases:
            if not c.duplicate_of:
                continue
            primary = primary_lookup.get((c.item_id, c.duplicate_of))
            if primary and primary.asset_id:
                c.asset_id = primary.asset_id
                c.file = primary.file
                duplicates += 1

    # Computado depois da extração: falhas de extração reclassificam o caso
    # para NEEDS_MANUAL_REVIEW, e o resumo tem que refletir isso.
    by_class: dict[str, int] = {}
    by_kind_class: dict[tuple[str, str], int] = {}
    for c in cases:
        by_class[c.classification] = by_class.get(c.classification, 0) + 1
        key = (c.kind, c.classification)
        by_kind_class[key] = by_kind_class.get(key, 0) + 1

    duplicates_detected = sum(1 for c in cases if c.duplicate_of)

    manifest = {
        "generated_by": "extract_book_visuals.py",
        "mode": mode,
        "gemini_or_llm_calls": 0,
        "external_api_calls": 0,
        "totals": {
            "casos": len(cases),
            "por_classificacao": by_class,
            "por_tipo_e_classificacao": {f"{k}/{v}": n for (k, v), n in by_kind_class.items()},
            "extraidos": extracted,
            "duplicatas_mescladas": duplicates if mode == "extract" else duplicates_detected,
        },
        "stats": {**stats, "pdf_ausente": sorted(stats["pdf_ausente"])},
        "cases": [
            {
                "book_id": c.book_id,
                "item_id": c.item_id,
                "question_number": c.question_number,
                "kind": c.kind,
                "asset_ref_id": c.asset_ref_id,
                "descricao": c.descricao[:300],
                "pages": c.pages,
                "classification": c.classification,
                "reason": c.reason,
                "confidence": c.confidence,
                "page_used": c.page_used,
                "bbox": c.bbox,
                "asset_id": c.asset_id,
                "file": c.file,
                "duplicate_of": c.duplicate_of,
                "needs_manual_review": c.classification == "NEEDS_MANUAL_REVIEW",
            }
            for c in cases
        ],
    }
    audit_root.mkdir(parents=True, exist_ok=True)
    manifest_path = audit_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"modo: {mode}")
    print(f"questões avaliadas: {stats['questoes_processadas']} (sem página: {stats['questoes_sem_pagina']})")
    print(f"PDFs ausentes: {sorted(stats['pdf_ausente']) or 'nenhum'}")
    print(f"total de casos visuais: {len(cases)}")
    for k, v in sorted(by_class.items()):
        print(f"  {k}: {v}")
    print("\npor tipo:")
    for (kind, klass), n in sorted(by_kind_class.items()):
        print(f"  {kind:10s} {klass:25s} {n}")
    print(f"\nduplicatas (mesmo elemento em 2 chaves de recursos): {duplicates_detected}")
    if mode == "extract":
        print(f"assets extraídos (arquivos novos): {extracted}")
        print(f"duplicatas resolvidas sem gerar arquivo novo: {duplicates}")
    print(f"\nmanifesto: {manifest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["classify", "extract"])
    parser.add_argument("--backend-dir", default=str(BACKEND_DIR))
    args = parser.parse_args()
    run(args.mode, Path(args.backend_dir).resolve())
