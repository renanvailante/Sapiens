"""Wrapper determinístico do pacote `enem` (v1.0.4).

Expõe:
    extract_enem_pdf(pdf_path: str, output_dir: Optional[str] = None,
                     answer_key_path: Optional[str] = None,
                     minimal: bool = False) -> dict

Fluxo: PDF ENEM -> enem-extractor -> JSON estruturado.

Sem LLM, sem ontologia, sem heurística própria: apenas invoca a função
`extractor` já publicada no pacote e normaliza a saída para dict serializável.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from enem.src.__main__ import extractor as _enem_extractor


def _normalize_alternatives(raw: dict) -> list[dict]:
    """Converte dict {0..4: alt} para list ordenada por 'alternative_value'."""
    if not isinstance(raw, dict):
        return []
    items = []
    for key, alt in raw.items():
        if not isinstance(alt, dict):
            continue
        items.append({
            "index": alt.get("alternative_value", key),
            "label": (alt.get("alternative") or "").strip(),
            "content": alt.get("content") or [],
            "correct": bool(alt.get("correct", False)),
        })
    items.sort(key=lambda a: a["index"])
    return items


def _split_content(content: list[dict]) -> tuple[list[dict], list[str]]:
    """Separa lista mista em blocos textuais e paths de imagens."""
    texts: list[dict] = []
    images: list[str] = []
    for block in content or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "image":
            path = block.get("content")
            if isinstance(path, str):
                images.append(path)
        else:
            texts.append(block)
    return texts, images


def _normalize_question(q: dict) -> dict:
    content = q.get("content") or []
    texts, images = _split_content(content)
    enunciado_str = " ".join(
        (b.get("content") or "").strip()
        for b in texts
        if isinstance(b, dict) and (b.get("content") or "").strip()
    ).strip()
    return {
        "numero": q.get("number"),
        "enunciado": enunciado_str,
        "enunciado_blocos": texts,
        "imagens": images,
        "alternativas": _normalize_alternatives(q.get("alternatives") or {}),
    }


def extract_enem_pdf(
    pdf_path: str,
    output_dir: Optional[str] = None,
    answer_key_path: Optional[str] = None,
    minimal: bool = False,
) -> dict:
    """Executa a extração de um PDF ENEM usando `enem-extractor`.

    :param pdf_path: caminho do PDF de prova ENEM.
    :param output_dir: diretório-raiz onde o pacote gravará assets (imagens).
        Se None, cria um diretório temporário.
    :param answer_key_path: caminho opcional do PDF de gabarito.
    :param minimal: se True, saída resumida (apenas texto e alternativas).
    :return: dict serializável com número, enunciado, alternativas e assets.
    """
    src = Path(pdf_path)
    if not src.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    root_out = output_dir or tempfile.mkdtemp(prefix="enem_extract_")
    os.makedirs(root_out, exist_ok=True)

    if answer_key_path is not None and not Path(answer_key_path).is_file():
        raise FileNotFoundError(f"Gabarito não encontrado: {answer_key_path}")

    result: Optional[tuple[str, list[dict]]] = _enem_extractor(
        file_pdf_path=str(src),
        root_path=root_out,
        test_answer_key_path=answer_key_path,
        minimal=minimal,
    )

    if not result:
        return {
            "source_pdf": str(src),
            "output_dir": root_out,
            "assets_dir": os.path.join(root_out, f"output_{src.stem}", "img"),
            "question_count": 0,
            "questions": [],
        }

    output_root, questions_raw = result
    normalized = [_normalize_question(q) for q in (questions_raw or []) if isinstance(q, dict)]
    return {
        "source_pdf": str(src),
        "output_dir": output_root,
        "assets_dir": os.path.join(output_root, "img"),
        "question_count": len(normalized),
        "questions": normalized,
    }


__all__: list[Any] = ["extract_enem_pdf"]
