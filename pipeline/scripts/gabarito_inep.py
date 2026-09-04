#!/usr/bin/env python
"""Parse determinístico do PDF de gabarito oficial do INEP.

Sem LLM, sem OCR, sem fonte secundária: o único insumo é o PDF publicado em
`download.inep.gov.br/enem/provas_e_gabaritos/`, e o único algoritmo é ler a
sequência de tokens `<número> <letra|Anulado>` que a tabela do PDF produz.

Módulo compartilhado entre `audit_corpus.py` (Fase 0, leitura) e
`seed_gabaritos_oficiais.py` (Fase 1, escrita) — o mesmo parser nos dois lados
garante que o que a auditoria mede é exatamente o que o backfill aplica.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

# Faixa válida de numeração do ENEM em qualquer caderno de qualquer dia.
NUM_MIN, NUM_MAX = 1, 180

_ANULADA = "ANULADA"
_RE_NUM = re.compile(r"^\d{1,3}$")
_RE_LETRA = re.compile(r"^[A-E]$")
_RE_ANULADO = re.compile(r"^anulad", re.IGNORECASE)

_RE_CABECALHO = re.compile(
    r"(?P<cor>AMARELO|AZUL|ROSA|CINZA|BRANCO|VERDE|LARANJA)|"
    r"CADERNO\s*(?P<caderno>\d+)|"
    r"Gabarito\s*(?P<ano>\d{4})|"
    # 2022 imprime "2º DIA"; 2023 e 2024 imprimem os mesmos glifos em outra
    # ordem ("diaº 2"), e o extrator de texto devolve o que está no PDF.
    r"(?P<dia>\d)\s*º?\s*DIA|"
    r"DIA\s*º?\s*(?P<dia_pos>\d)",
    re.IGNORECASE,
)


class GabaritoInvalido(RuntimeError):
    pass


def sha256_arquivo(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _texto(path: Path) -> str:
    import pymupdf

    doc = pymupdf.open(str(path))
    try:
        return "\n".join(pagina.get_text() for pagina in doc)
    finally:
        doc.close()


def _identificar(texto: str) -> dict:
    """Lê ano, dia, número do caderno e cor do cabeçalho do próprio PDF.

    Nunca inferido do nome do arquivo: o nome é rótulo humano, o cabeçalho é o
    documento se declarando. Foi assim que a auditoria descartou a hipótese de
    troca de ano no corpus.
    """
    achados: dict[str, str] = {}
    for m in _RE_CABECALHO.finditer(texto[:600]):
        for chave, valor in m.groupdict().items():
            if valor and chave not in achados:
                achados[chave] = valor
    dia = achados.get("dia") or achados.get("dia_pos")
    return {
        "ano": int(achados["ano"]) if "ano" in achados else None,
        "dia": int(dia) if dia else None,
        "caderno": achados.get("caderno"),
        "cor": (achados.get("cor") or "").upper() or None,
    }


def parse_pdf(path: str | Path) -> dict:
    """Devolve procedência + entradas do gabarito de um PDF oficial do INEP.

    `entradas` é uma lista ordenada de `{numero, gabarito, status}`, com
    `gabarito=None` e `status="anulada"` para as questões anuladas.
    """
    path = Path(path)
    if not path.is_file():
        raise GabaritoInvalido(f"arquivo não encontrado: {path}")

    texto = _texto(path)
    palavras = texto.split()
    pares: dict[int, str] = {}

    i = 0
    while i < len(palavras) - 1:
        atual, proxima = palavras[i], palavras[i + 1]
        if _RE_NUM.match(atual):
            numero = int(atual)
            if NUM_MIN <= numero <= NUM_MAX:
                if _RE_LETRA.match(proxima):
                    pares[numero] = proxima
                    i += 2
                    continue
                if _RE_ANULADO.match(proxima):
                    pares[numero] = _ANULADA
                    i += 2
                    continue
        i += 1

    if not pares:
        raise GabaritoInvalido(f"nenhum par número/gabarito extraído de {path.name}")

    numeros = sorted(pares)
    faixa = (numeros[0], numeros[-1])
    lacunas = [n for n in range(faixa[0], faixa[1] + 1) if n not in pares]
    if lacunas:
        raise GabaritoInvalido(
            f"{path.name}: faixa {faixa[0]}-{faixa[1]} com lacunas {lacunas}. "
            "Um gabarito parcial não pode virar fonte da verdade."
        )

    ident = _identificar(texto)
    entradas = [
        {
            "numero": n,
            "gabarito": None if pares[n] == _ANULADA else pares[n],
            "status": "anulada" if pares[n] == _ANULADA else "valida",
        }
        for n in numeros
    ]
    return {
        "prova": ident,
        "entradas": entradas,
        "cobertura": {
            "faixa": list(faixa),
            "declaradas": len(entradas),
            "lacunas": [],
            "anuladas": [e["numero"] for e in entradas if e["status"] == "anulada"],
        },
        "origem": {
            "tipo": "pdf_oficial",
            "arquivo": path.name,
            "sha256": sha256_arquivo(path),
            "bytes": path.stat().st_size,
        },
    }


def como_mapa(parsed: dict) -> dict[int, str]:
    """`{numero: "A".."E" | "ANULADA"}` — forma de consulta usada nas checagens."""
    return {
        e["numero"]: (e["gabarito"] or _ANULADA)
        for e in parsed["entradas"]
    }


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdfs", nargs="+")
    args = ap.parse_args()
    for p in args.pdfs:
        d = parse_pdf(p)
        print(json.dumps(
            {"prova": d["prova"], "cobertura": d["cobertura"], "origem": d["origem"]},
            ensure_ascii=False,
        ))
