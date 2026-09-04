"""Localiza candidatos a figura/tabela/gráfico por RESÍDUO de conteúdo,
dentro da região correta da questão (`layout_model`), cobrindo texto real
E texto/desenho vetorial (glifos convertidos em curva — comuns neste
caderno para subscrito/sobrescrito e para o próprio desenho de gráficos).

Método: alinha as palavras da região contra o texto já transcrito (enunciado
+ alternativas) com `difflib.SequenceMatcher` — mesma ideia do extrator
antigo (`extract_book_visuals._gap_bbox_for_visual`), mas escopado à região
CORRETA (coluna certa, sem vazar para a questão vizinha) e devolvendo TODAS
as lacunas relevantes agrupadas em clusters espaciais, não só a maior.

Cada candidato é uma HIPÓTESE, não uma verdade — precisa de inspeção visual
antes de virar asset (ver `pipeline/scripts/reconstruir_visuais_pendentes.py`).
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any

import layout_model as lm

RE_WORD = re.compile(r"\w+", re.UNICODE)
RE_ALT_LETRA = re.compile(r"^[A-E]$")
GAP_MERGE_Y_PT = 14.0     # gaps verticais mais próximos que isto se fundem
GAP_MERGE_X_PT = 60.0     # gaps horizontais — mais largo: colunas de uma
                          # tabela do ENEM (dias, categorias) ficam bem
                          # espaçadas, e cada "coluna" não pode virar um
                          # cluster isolado (foi o que fragmentou a Q177 em
                          # 9 pedaços na primeira versão deste filtro)
MIN_CLUSTER_AREA = 120.0  # pt² — descarta ruído (traço de tabela, sublinhado)
# Um cluster só vira candidato se tiver conteúdo vetorial de verdade, ou uma
# quantidade de palavras residuais grande o bastante para não ser apenas
# ruído de alinhamento do SequenceMatcher (acento/pontuação/hifenização que
# não caça perfeito). Elemento visual real quase sempre traz desenho junto —
# mesmo uma legenda "Figura 1" pura-texto está ao LADO de um desenho.
MIN_DRAWINGS_PLAUSIVEL = 3
MIN_PALAVRAS_SEM_DESENHO = 12
# O marcador "A-E" de alternativa fica indentado ~31pt a partir da borda REAL
# da coluna (que é a borda da PÁGINA para a coluna 0, e a borda da calha para
# a coluna 1) — não centrado sobre ela. `abs(x - col_x0) < 12` reprovava todo
# marcador legítimo (Q118/2022: fronteira nunca detectada, todas as 5
# alternativas gráficas caíam na varredura de enunciado). Janela de 0 a +45pt
# cobre o recuo real nas duas colunas.
MARGEM_INDENTACAO = 45.0


def _norm(tok: str) -> str:
    return tok.lower().strip()


def _tokens(text: str) -> list[str]:
    return [_norm(t) for t in RE_WORD.findall(text or "")]


def tokens_referencia(questao: dict) -> tuple[list[str], int]:
    """(tokens de enunciado+alternativas, quantos são do enunciado)."""
    enun = _tokens(questao.get("enunciado") or "")
    alt: list[str] = []
    for a in questao.get("alternativas") or []:
        letra = _norm(a.get("letra") or "")
        if letra:
            alt += [letra, letra]  # a letra aparece 2x impressa (marcador + rótulo)
        alt += _tokens(a.get("texto") or "")
    return enun + alt, len(enun)


@dataclass
class Candidato:
    bbox: tuple[float, float, float, float]
    pagina: int
    coluna: int
    n_palavras_residuais: int
    n_drawings: int
    zona: str  # "enunciado" | "alternativa"
    letra: str | None = None


def _palavras_da_regiao(doc, regiao: lm.RegiaoQuestao, modelo: lm.ModeloPagina) -> list[tuple]:
    col0, col1 = modelo.colunas[regiao.coluna] if regiao.coluna != modelo.LARGURA_TOTAL else (0, modelo.largura)
    marca = set(modelo.marca_dagua)
    out = []
    for w in doc[regiao.pagina].get_text("words"):
        if (w[0], w[1], w[2], w[3]) in marca:
            continue
        if regiao.y0 - 1 <= w[1] and w[3] <= regiao.y1 + 1 and col0 - 2 <= w[0] and w[2] <= col1 + 2:
            out.append(w)
    return sorted(out, key=lambda w: (w[1], w[0]))


def _drawings_da_regiao(doc, regiao: lm.RegiaoQuestao, modelo: lm.ModeloPagina) -> list:
    col0, col1 = modelo.colunas[regiao.coluna] if regiao.coluna != modelo.LARGURA_TOTAL else (0, modelo.largura)
    out = []
    for d in doc[regiao.pagina].get_drawings():
        r = d.get("rect")
        if r is None or r.width <= 0 or r.height <= 0:
            continue
        if regiao.y0 - 1 <= r.y0 and r.y1 <= regiao.y1 + 1 and col0 - 2 <= r.x0 and r.x1 <= col1 + 2:
            out.append(r)
    return out


def _fronteira_alternativas(palavras: list[tuple], col_x0: float) -> float | None:
    """y onde REALMENTE começa o bloco de alternativas (A, B, C... em
    sequência), não a primeira letra solta indentada que aparecer.

    Uma letra "A" isolada no meio do enunciado (símbolo químico, variável)
    também cai na janela de indentação por coincidência de x — foi o que
    truncou a Q93/2022 para quase nada. A alternativa de verdade é sempre
    uma SEQUÊNCIA: A seguida de B mais abaixo, seguida de C... — exige achar
    essa sequência, não confiar na primeira letra que bater.
    """
    candidatos = sorted(
        (w[1], w[4]) for w in palavras if RE_ALT_LETRA.match(w[4])
        and 0 <= (w[0] - col_x0) <= MARGEM_INDENTACAO
    )
    ordem = "ABCDE"
    for i, (y, letra) in enumerate(candidatos):
        if letra != "A":
            continue
        # a partir deste "A", tenta seguir B, C... com espaçamento plausível
        y_anterior, esperado = y, 1
        for y2, letra2 in candidatos[i + 1:]:
            if esperado >= len(ordem):
                break
            if letra2 == ordem[esperado] and 15 <= (y2 - y_anterior) <= 150:
                y_anterior = y2
                esperado += 1
        if esperado >= 2:  # achou pelo menos A seguido de B em sequência real
            return y
    return None


def _clusterizar(itens: list[tuple[float, float, float, float]]) -> list[tuple[float, float, float, float]]:
    """Une bboxes cuja distância (gap) é menor que `GAP_MERGE_PT` em ambos os
    eixos — mesmo critério de vizinhança usado em `_detectar_marca_dagua`
    (proximidade), mas em 2D."""
    boxes = list(itens)
    mudou = True
    while mudou and len(boxes) > 1:
        mudou = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                ax0, ay0, ax1, ay1 = boxes[i]
                bx0, by0, bx1, by1 = boxes[j]
                gx = max(ax0, bx0) - min(ax1, bx1)
                gy = max(ay0, by0) - min(ay1, by1)
                if gx <= GAP_MERGE_X_PT and gy <= GAP_MERGE_Y_PT:
                    novo = (min(ax0, bx0), min(ay0, by0), max(ax1, bx1), max(ay1, by1))
                    boxes = [b for k, b in enumerate(boxes) if k not in (i, j)] + [novo]
                    mudou = True
                    break
            if mudou:
                break
    return boxes


def candidatos_por_residuo(
    doc, modelos: dict[int, lm.ModeloPagina], regioes: list[lm.RegiaoQuestao], questao: dict,
) -> list[Candidato]:
    """Um ou mais candidatos a elemento visual dentro do ENUNCIADO da questão.

    Não procura dentro do bloco de alternativas aqui — ver
    `candidatos_em_alternativas` para figura-por-alternativa.
    """
    ref_tokens, enun_n = tokens_referencia(questao)
    out: list[Candidato] = []
    for regiao in regioes:
        modelo = modelos[regiao.pagina]
        palavras = _palavras_da_regiao(doc, regiao, modelo)
        col0, _ = (modelo.colunas[regiao.coluna] if regiao.coluna != modelo.LARGURA_TOTAL
                  else (0, modelo.largura))
        fronteira = _fronteira_alternativas(palavras, col0)
        limite_y = fronteira if fronteira is not None else regiao.y1
        palavras_enun = [w for w in palavras if w[1] < limite_y]

        page_tokens = [_norm(w[4]) for w in palavras_enun]
        sm = difflib.SequenceMatcher(None, page_tokens, ref_tokens[:enun_n] or ref_tokens, autojunk=False)
        casados = set()
        for blk in sm.get_matching_blocks():
            for i in range(blk.a, blk.a + blk.size):
                casados.add(i)
        residuais = [w for i, w in enumerate(palavras_enun) if i not in casados]

        drawings = [r for r in _drawings_da_regiao(doc, regiao, modelo) if r.y1 <= limite_y + 2]

        caixas = ([(w[0], w[1], w[2], w[3]) for w in residuais]
                 + [(r.x0, r.y0, r.x1, r.y1) for r in drawings])
        for x0, y0, x1, y1 in _clusterizar(caixas):
            if (x1 - x0) * (y1 - y0) < MIN_CLUSTER_AREA:
                continue
            n_pal = sum(1 for w in residuais if x0 - 1 <= w[0] and w[2] <= x1 + 1
                       and y0 - 1 <= w[1] and w[3] <= y1 + 1)
            n_dr = sum(1 for r in drawings if x0 - 1 <= r.x0 and r.x1 <= x1 + 1
                      and y0 - 1 <= r.y0 and r.y1 <= y1 + 1)
            if n_dr < MIN_DRAWINGS_PLAUSIVEL and n_pal < MIN_PALAVRAS_SEM_DESENHO:
                continue
            out.append(Candidato((x0, y0, x1, y1), regiao.pagina, regiao.coluna,
                                 n_pal, n_dr, "enunciado"))
    return out


def candidatos_em_alternativas(
    doc, modelos: dict[int, lm.ModeloPagina], regioes: list[lm.RegiaoQuestao], questao: dict,
) -> list[Candidato]:
    """Um candidato por alternativa (A-E), na faixa entre o marcador da letra
    e o próximo marcador (ou o fim da região)."""
    out: list[Candidato] = []
    alt_por_letra = {(a.get("letra") or "").upper(): a for a in questao.get("alternativas") or []}
    for regiao in regioes:
        modelo = modelos[regiao.pagina]
        palavras = _palavras_da_regiao(doc, regiao, modelo)
        col0, col1 = (modelo.colunas[regiao.coluna] if regiao.coluna != modelo.LARGURA_TOTAL
                     else (0, modelo.largura))
        marcadores = sorted(
            [(w[1], w[4]) for w in palavras if RE_ALT_LETRA.match(w[4])
              and 0 <= (w[0] - col0) <= MARGEM_INDENTACAO]
        )
        if not marcadores:
            continue
        # descarta qualquer "marcador" ANTES do início real da sequência
        # A→B→C validada (mesma checagem de `_fronteira_alternativas`) — uma
        # letra solta no enunciado, indent-alinhada por coincidência, não
        # pode virar fronteira de faixa de alternativa.
        inicio_real = _fronteira_alternativas(palavras, col0)
        if inicio_real is not None:
            marcadores = [m for m in marcadores if m[0] >= inicio_real - 0.5]
        if not marcadores:
            continue
        for i, (y, letra) in enumerate(marcadores):
            y_fim = marcadores[i + 1][0] if i + 1 < len(marcadores) else regiao.y1
            alt = alt_por_letra.get(letra)
            ref = _tokens((alt or {}).get("texto") or "")
            faixa_palavras = [w for w in palavras if y - 1 <= w[1] < y_fim and w[4] != letra]
            page_tokens = [_norm(w[4]) for w in faixa_palavras]
            sm = difflib.SequenceMatcher(None, page_tokens, ref, autojunk=False)
            casados = set()
            for blk in sm.get_matching_blocks():
                for k in range(blk.a, blk.a + blk.size):
                    casados.add(k)
            residuais = [w for k, w in enumerate(faixa_palavras) if k not in casados]
            drawings = [r for r in _drawings_da_regiao(doc, regiao, modelo)
                       if y - 1 <= r.y0 < y_fim]
            caixas = ([(w[0], w[1], w[2], w[3]) for w in residuais]
                     + [(r.x0, r.y0, r.x1, r.y1) for r in drawings])
            fundidas = _clusterizar(caixas)
            if not fundidas:
                continue
            x0 = min(b[0] for b in fundidas); y0 = min(b[1] for b in fundidas)
            x1 = max(b[2] for b in fundidas); y1 = max(b[3] for b in fundidas)
            if (x1 - x0) * (y1 - y0) < MIN_CLUSTER_AREA:
                continue
            if len(drawings) < MIN_DRAWINGS_PLAUSIVEL:
                continue
            out.append(Candidato((x0, y0, x1, y1), regiao.pagina, regiao.coluna,
                                 len(residuais), len(drawings), "alternativa", letra))
    return out
