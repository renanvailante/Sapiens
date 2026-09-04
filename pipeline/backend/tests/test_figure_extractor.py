"""Testes de `figure_extractor.py` — extração determinística de figuras.

Totalmente offline: nenhum Mongo, nenhum Gemini, nenhum PDF externo. Os PDFs
de teste são gerados na hora com `reportlab` (já usado por outras suítes,
ver `tests/test_book_endpoints.py`), com imagens embutidas via PIL cujo
tamanho de pixel real (não o tamanho de exibição na página) é o que
`figure_extractor` filtra. `storage.STORAGE_ROOT` é redirecionado para um
diretório temporário (mesmo padrão de `tests/test_batch_queue.py`), para não
escrever no `_storage/` de desenvolvimento.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import storage  # noqa: E402
from figure_extractor import extract_and_attach_figures  # noqa: E402


@pytest.fixture(autouse=True)
def _tmp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path / "_storage")


def _raster(width_px: int, height_px: int, color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (width_px, height_px), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _pdf_with_images(pages: list[list[tuple[bytes, float, float, float, float]]]) -> bytes:
    """`pages`: por página, lista de `(raster_png, x, y, w, h)` — coordenadas
    reportlab nativas (origem inferior-esquerda, y crescendo para cima)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for draws in pages:
        for raw, x, y, w, h in draws:
            c.drawImage(ImageReader(io.BytesIO(raw)), x, y, width=w, height=h)
        c.showPage()
    c.save()
    return buf.getvalue()


def _files(pdf_bytes: bytes) -> list[tuple[str, bytes, str]]:
    return [("caderno.pdf", pdf_bytes, "application/pdf")]


def _item(item_id: str) -> dict:
    return {"item_id": item_id, "questao": {"recursos": {"imagens": []}}}


def test_extrai_figura_unica_e_otimiza():
    figura = _raster(300, 300, (200, 30, 30))
    pdf = _pdf_with_images([[(figura, 150, 400, 200, 200)]])
    manifest = [{"numero": "1", "paginas": [1], "tem_figura": True}]

    item = _item("ITEM-TEST-Q001")
    result = extract_and_attach_figures(item, _files(pdf), manifest, "1")

    assert result["figures_attached"] == 1
    arquivo = item["questao"]["recursos"]["imagens"][0]["arquivo"]
    assert arquivo.endswith(".webp")
    # Blob de fato gravado no storage deduplicado, legível e menor que a fonte.
    data, content_type = storage.get_object(f"{storage.APP_NAME}/blobs/{arquivo}")
    assert content_type == "image/webp"
    assert len(data) < len(figura)
    assert item["item_hash"]


def test_manifesto_sem_tem_figura_nao_extrai():
    figura = _raster(300, 300, (10, 200, 10))
    pdf = _pdf_with_images([[(figura, 150, 400, 200, 200)]])
    manifest = [{"numero": "1", "paginas": [1], "tem_figura": False}]

    item = _item("ITEM-TEST-Q002")
    result = extract_and_attach_figures(item, _files(pdf), manifest, "1")

    assert result["figures_attached"] == 0
    assert result["pages_checked"] == []
    assert item["questao"]["recursos"]["imagens"] == []


def test_sem_manifesto_nao_extrai():
    figura = _raster(300, 300, (10, 10, 200))
    pdf = _pdf_with_images([[(figura, 150, 400, 200, 200)]])

    item = _item("ITEM-TEST-Q003")
    result = extract_and_attach_figures(item, _files(pdf), None, "1")

    assert result["figures_attached"] == 0


def test_dedup_reaproveita_blob_identico():
    figura = _raster(300, 300, (150, 150, 10))
    pdf = _pdf_with_images([[(figura, 150, 400, 200, 200)]])
    manifest = [{"numero": "1", "paginas": [1], "tem_figura": True}]

    item_a = _item("ITEM-TEST-Q004A")
    result_a = extract_and_attach_figures(item_a, _files(pdf), manifest, "1")
    item_b = _item("ITEM-TEST-Q004B")
    result_b = extract_and_attach_figures(item_b, _files(pdf), manifest, "1")

    assert result_a["figures"][0]["deduped"] is False
    assert result_b["figures"][0]["deduped"] is True
    assert (
        item_a["questao"]["recursos"]["imagens"][0]["arquivo"]
        == item_b["questao"]["recursos"]["imagens"][0]["arquivo"]
    )


def test_pagina_dividida_entre_duas_questoes_atribui_pela_ordem_vertical():
    figura_topo = _raster(200, 200, (255, 0, 0))
    figura_base = _raster(200, 200, (0, 0, 255))
    # y alto (reportlab, origem embaixo) = perto do topo da página.
    pdf = _pdf_with_images(
        [[(figura_topo, 100, 600, 150, 150), (figura_base, 100, 100, 150, 150)]]
    )
    manifest = [
        {"numero": "10", "paginas": [1], "tem_figura": True},
        {"numero": "11", "paginas": [1], "tem_figura": True},
    ]

    item_10 = _item("ITEM-TEST-Q010")
    result_10 = extract_and_attach_figures(item_10, _files(pdf), manifest, "10")
    item_11 = _item("ITEM-TEST-Q011")
    result_11 = extract_and_attach_figures(item_11, _files(pdf), manifest, "11")

    assert result_10["figures_attached"] == 1
    assert result_11["figures_attached"] == 1
    blob_10 = item_10["questao"]["recursos"]["imagens"][0]["arquivo"]
    blob_11 = item_11["questao"]["recursos"]["imagens"][0]["arquivo"]
    assert blob_10 != blob_11, "questões vizinhas na mesma página não podem herdar a mesma figura"


def test_pagina_dividida_sem_contagem_batendo_fica_ambigua_e_nao_atribui():
    """Duas questões com figura declarada, mas só uma imagem candidata na
    página: não há como saber de qual das duas é, então nenhuma recebe."""
    figura_unica = _raster(200, 200, (100, 100, 100))
    pdf = _pdf_with_images([[(figura_unica, 100, 400, 150, 150)]])
    manifest = [
        {"numero": "20", "paginas": [1], "tem_figura": True},
        {"numero": "21", "paginas": [1], "tem_figura": True},
    ]

    item_20 = _item("ITEM-TEST-Q020")
    result_20 = extract_and_attach_figures(item_20, _files(pdf), manifest, "20")

    assert result_20["figures_attached"] == 0


def test_imagem_pagina_inteira_e_excluida():
    """Uma imagem cobrindo quase a página toda é tratada como scan da página,
    não como a figura de uma questão específica."""
    pagina_inteira = _raster(1000, 1300, (240, 240, 240))
    w, h = letter
    pdf = _pdf_with_images([[(pagina_inteira, 0, 0, w, h)]])
    manifest = [{"numero": "1", "paginas": [1], "tem_figura": True}]

    item = _item("ITEM-TEST-Q030")
    result = extract_and_attach_figures(item, _files(pdf), manifest, "1")

    assert result["figures_attached"] == 0


def test_icone_pequeno_e_excluido():
    """Resolução real (em pixels) da imagem-fonte abaixo do mínimo — mesmo
    exibida em tamanho maior na página — é ícone/logo, não figura."""
    icone = _raster(40, 40, (0, 150, 0))
    pdf = _pdf_with_images([[(icone, 100, 400, 150, 150)]])
    manifest = [{"numero": "1", "paginas": [1], "tem_figura": True}]

    item = _item("ITEM-TEST-Q031")
    result = extract_and_attach_figures(item, _files(pdf), manifest, "1")

    assert result["figures_attached"] == 0
