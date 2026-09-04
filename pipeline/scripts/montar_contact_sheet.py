#!/usr/bin/env python
"""Monta uma folha de contato (grade rotulada) a partir do manifesto de
candidatos, para inspeção visual em lote.

    .venv/bin/python montar_contact_sheet.py /tmp/candidatos_2022 /tmp/sheet1.png --inicio 0 --fim 8
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> int:
    pasta = Path(sys.argv[1])
    saida = sys.argv[2]
    inicio = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    fim = int(sys.argv[4]) if len(sys.argv) > 4 else inicio + 8

    manifesto = json.load(open(pasta / "manifesto.json"))
    itens = [m for m in manifesto if "arquivo" in m][inicio:fim]
    if not itens:
        print("nada nesse intervalo")
        return 1

    MAXW = 560
    linhas = []
    for m in itens:
        img = Image.open(pasta / m["arquivo"])
        if img.width > MAXW:
            r = MAXW / img.width
            img = img.resize((MAXW, int(img.height * r)))
        rotulo = (f"Q{m['numero']} [{m['arquivo']}] zona={m['zona']}"
                 f"{('/' + m['letra']) if m.get('letra') else ''} "
                 f"pal={m['n_palavras_residuais']} draw={m['n_drawings']} decl={m['declarado']}")
        linhas.append((rotulo, img))

    pad, rot_h = 8, 20
    w = MAXW + pad * 2
    h = sum(img.height + rot_h + pad for _, img in linhas) + pad
    canvas = Image.new("RGB", (w, h), "white")
    dr = ImageDraw.Draw(canvas)
    y = pad
    for rotulo, img in linhas:
        dr.rectangle([0, y, w, y + rot_h], fill=(30, 30, 30))
        dr.text((pad, y + 3), rotulo, fill="white")
        y += rot_h
        canvas.paste(img, (pad, y))
        y += img.height + pad
    canvas.save(saida)
    print(f"{len(linhas)} candidatos · {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
