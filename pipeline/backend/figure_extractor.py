"""Extração determinística de figuras de questões, direto do PDF do caderno.

Sem Gemini: usa PyMuPDF para localizar imagens embutidas nas páginas indicadas
pelo manifesto (`book.manifest[].paginas`) e Pillow para otimizar para web
(WebP). O resultado é gravado no storage já deduplicado por SHA-256
(`storage.put_object_deduped`) e o nome do blob (`{sha256}.webp`) é carimbado
em `questao.recursos.imagens[].arquivo` — o único campo que o Schema 2.2 já
reserva para isto (hoje sempre uma string vazia, porque o modelo só descreve a
figura, nunca produz os bytes dela).

Não recorta a figura de dentro da página: o manifesto não tem bounding box,
só número de página (ver `cognitive_engine.MANIFEST_PROMPT`). O que dá para
fazer sem Gemini é identificar, entre as imagens embutidas na página, quais
não cobrem quase a página inteira — isso distingue uma figura isolada (foto,
gráfico, diagrama) de um scan da página inteira. Quando isso não é possível
(a única imagem da página é o próprio scan completo), a questão fica sem
`arquivo` — mais seguro do que entregar a página inteira como se fosse a
figura de uma questão específica.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image

from item_contract import compute_item_hash
from storage import put_object_deduped

logger = logging.getLogger("sapiens.figure_extractor")

# Abaixo disso é ícone/logo/marca d'água, não uma figura de questão.
_MIN_DIMENSION_PX = 120
# Acima disso, a imagem provavelmente É a página (scan completo), não uma
# figura isolada dentro dela.
_MAX_PAGE_COVERAGE = 0.85
_MAX_LONG_EDGE_PX = 1600
_WEBP_QUALITY = 82


def _as_int_pages(paginas: Any) -> list[int]:
    out: list[int] = []
    for p in paginas or []:
        try:
            out.append(int(p))
        except (TypeError, ValueError):
            continue
    return out


def _manifest_entry_for(manifest: list[dict] | None, question_number: str) -> dict | None:
    numero = str(question_number).strip()
    for entry in manifest or []:
        if str(entry.get("numero", "")).strip() == numero:
            return entry
    return None


def _page_sharers(manifest: list[dict] | None, page_number: int) -> list[dict]:
    """Entradas do manifesto (na ordem declarada) cuja lista de páginas inclui
    `page_number` — ou seja, todas as questões que dividem essa página."""
    return [e for e in (manifest or []) if page_number in _as_int_pages(e.get("paginas"))]


def _optimize(raw: bytes) -> tuple[bytes, str, str] | None:
    """Recomprime para WebP, limitando o lado maior. `None` se ilegível."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        return None
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > _MAX_LONG_EDGE_PX:
        scale = _MAX_LONG_EDGE_PX / long_edge
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=_WEBP_QUALITY, method=6)
    return buf.getvalue(), "image/webp", ".webp"


def _extract_page_figures(doc: "pymupdf.Document", page_number: int) -> list[dict]:
    """Imagens embutidas numa página, excluindo scans de página inteira e
    ícones. `y0` é a coordenada vertical do topo da imagem na página — serve
    só para ordená-las na ordem de leitura (topo → base) quando a página é
    dividida entre várias questões."""
    idx = page_number - 1
    if idx < 0 or idx >= doc.page_count:
        return []
    page = doc[idx]
    page_area = abs(page.rect) or 1.0
    seen: set[int] = set()
    figures: list[dict] = []
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
            extracted = doc.extract_image(xref)
        except Exception:
            logger.debug("Falha ao extrair xref %s da página %s", xref, page_number)
            continue
        width, height = extracted.get("width", 0), extracted.get("height", 0)
        if width < _MIN_DIMENSION_PX or height < _MIN_DIMENSION_PX:
            continue
        y0 = min((r.y0 for r in rects), default=0.0)
        figures.append(
            {"page": page_number, "raw": extracted["image"], "width": width, "height": height, "y0": y0}
        )
    return figures


def _select_figures_for_question(
    candidates: list[dict], manifest: list[dict] | None, page_number: int, question_number: str
) -> list[dict]:
    """Entre as imagens candidatas de uma página, decide quais pertencem à
    questão `question_number`.

    Sem bounding box por questão no manifesto, uma página com só uma questão
    marcada `tem_figura` é inambígua: todas as imagens candidatas são dela.
    Quando duas ou mais questões da mesma página têm figura declarada, só há
    como parear com confiança se o número de candidatas bater exatamente com
    o número de questões-com-figura da página — nesse caso, pareia por ordem
    de leitura (topo → base) contra a ordem das questões no manifesto. Fora
    isso (contagens não batem), é mais seguro não atribuir nenhuma imagem a
    nenhuma das questões do que arriscar mostrar a figura errada a um aluno.
    """
    sharers_with_figure = [
        e for e in _page_sharers(manifest, page_number) if e.get("tem_figura")
    ]
    if len(sharers_with_figure) <= 1:
        return candidates
    if len(candidates) != len(sharers_with_figure):
        return []
    rank = next(
        (
            i
            for i, e in enumerate(sharers_with_figure)
            if str(e.get("numero", "")).strip() == str(question_number).strip()
        ),
        None,
    )
    if rank is None:
        return []
    ordered = sorted(candidates, key=lambda f: f["y0"])
    return [ordered[rank]]


def extract_question_figures(
    files: list[tuple[str, bytes, str]],
    pages: list[int],
    manifest: list[dict] | None,
    question_number: str,
    item_id: str,
) -> list[dict]:
    """Extrai, otimiza e persiste (deduplicado) as figuras das páginas indicadas.

    Devolve uma lista ordenada de dicts `{"path", "blob", "content_type",
    "size_before", "size_after", "deduped", "page"}`. Nunca levanta — uma
    página ilegível ou sem imagens simplesmente não contribui nenhuma figura.
    """
    if not pages:
        return []
    pdf_bytes = next(
        (
            data
            for name, data, ct in files
            if (ct or "").lower() == "application/pdf" or name.lower().endswith(".pdf")
        ),
        None,
    )
    if not pdf_bytes:
        return []

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        logger.exception("Falha ao abrir PDF do caderno para extração de figuras (%s)", item_id)
        return []

    results: list[dict] = []
    try:
        for page_number in pages:
            candidates = _extract_page_figures(doc, page_number)
            if not candidates:
                continue
            chosen = _select_figures_for_question(candidates, manifest, page_number, question_number)
            for fig in chosen:
                optimized = _optimize(fig["raw"])
                if not optimized:
                    continue
                webp_bytes, content_type, ext = optimized
                try:
                    stored = put_object_deduped(webp_bytes, content_type, f"{item_id}{ext}")
                except Exception:
                    logger.exception(
                        "Falha ao gravar figura no storage (%s, página %s)", item_id, page_number
                    )
                    continue
                results.append(
                    {
                        "path": stored["path"],
                        "blob": Path(stored["path"]).name,
                        "content_type": content_type,
                        "size_before": len(fig["raw"]),
                        "size_after": len(webp_bytes),
                        "deduped": stored["deduped"],
                        "page": page_number,
                    }
                )
    finally:
        doc.close()
    return results


def _attach_figures(item: dict, figures: list[dict]) -> int:
    """Carimba `arquivo` nas entradas de `recursos.imagens` já declaradas pelo
    modelo, na ordem em que as figuras foram encontradas; sobras viram novas
    entradas mínimas. Não inventa `tipo`/`descricao` — quem descreve a figura
    continua sendo o Gemini, quando o fez."""
    if not figures:
        return 0
    questao = item.setdefault("questao", {}) or {}
    recursos = questao.setdefault("recursos", {}) or {}
    imagens = recursos.get("imagens") or []
    attached = 0
    for i, fig in enumerate(figures):
        if i < len(imagens) and isinstance(imagens[i], dict):
            imagens[i]["arquivo"] = fig["blob"]
        else:
            imagens.append(
                {"id": f"IMG-{i + 1:02d}", "tipo": "outro", "descricao": "", "arquivo": fig["blob"], "ocr": ""}
            )
        attached += 1
    recursos["imagens"] = imagens
    questao["recursos"] = recursos
    item["questao"] = questao
    return attached


def extract_and_attach_figures(
    item: dict[str, Any],
    files: list[tuple[str, bytes, str]],
    manifest: list[dict] | None,
    question_number: str,
) -> dict:
    """Ponto de entrada usado por `/book/{id}/process`.

    Só tenta extrair quando o próprio manifesto (gerado uma vez, por página,
    sem custo adicional) já declarou `tem_figura=true` para esta questão —
    sem isso não há sinal nenhum de que a página tenha uma figura, e olhar
    mesmo assim arriscaria atribuir a uma questão a imagem de uma vizinha na
    mesma página (ver `_select_figures_for_question`).

    Muta `item` in-place (preenche `arquivo` e recalcula `item_hash` se algo
    foi anexado — `compute_item_hash` inclui `recursos`). Nunca levanta: uma
    falha na extração de figura não pode derrubar um item cognitivo que já
    custou uma chamada ao Gemini.
    """
    entry = _manifest_entry_for(manifest, question_number)
    if not entry or not entry.get("tem_figura"):
        return {
            "pages_checked": [],
            "figures_found": 0,
            "figures_attached": 0,
            "figures": [],
            "skipped_reason": "sem_manifesto" if not manifest else "manifesto_nao_indica_figura",
        }

    pages = _as_int_pages(entry.get("paginas"))
    try:
        figures = extract_question_figures(files, pages, manifest, question_number, item.get("item_id") or "item")
    except Exception:
        logger.exception(
            "Extração de figuras falhou para %s (questão %s)", item.get("item_id"), question_number
        )
        figures = []
    attached = _attach_figures(item, figures)
    if attached:
        item["item_hash"] = compute_item_hash(item.get("questao"))
    return {
        "pages_checked": pages,
        "figures_found": len(figures),
        "figures_attached": attached,
        "figures": figures,
    }
