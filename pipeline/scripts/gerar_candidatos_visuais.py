#!/usr/bin/env python
"""Gera candidatos a figura/tabela/gráfico para itens ainda pendentes, e
monta contact sheets para inspeção visual — SOMENTE LEITURA, não escreve
asset nenhum. A decisão de aceitar/rejeitar é feita olhando as imagens.

    .venv/bin/python ../scripts/gerar_candidatos_visuais.py --ano 2022 --out-dir /tmp/candidatos
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "pipeline" / "backend"
STORAGE = BACKEND / "_storage" / "sapiens-cognitive"
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")

sys.path.insert(0, str(BACKEND))
import layout_model as lm  # noqa: E402
import vector_figure_finder as vf  # noqa: E402

BOOKS = {
    2022: "6b1c29d5-033e-4a20-9149-64e3179e6d5e/book/2022_PV_impresso_D2_CD5.pdf",
    2023: "6ba5747b-1cfa-4428-b1cb-632b7a44eba1/book/2023_PV_impresso_D2_CD5.pdf",
    2024: "a1ab65fd-8c48-44a9-aa48-9c94ebe0eb0d/book/2024_PV_impresso_D2_CD5.pdf",
}
PAD = 5.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ano", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--numeros", default="", help="lista opcional separada por vírgula, senão todos os pendentes")
    args = ap.parse_args()

    import pymupdf
    from pymongo import MongoClient

    dbp = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)["sapiens_pipeline"]
    caminho = STORAGE / "questions" / BOOKS[args.ano]
    doc = pymupdf.open(str(caminho))
    modelos = lm.modelo_documento(doc)
    regioes = lm.regioes_por_questao(doc, modelos)

    if args.numeros:
        alvo = {int(x) for x in args.numeros.split(",")}
    else:
        alvo = None

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifesto = []

    for d in dbp.pipelines.find({"item.fonte.ano": args.ano}):
        numero = int(d.get("question_number") or 0)
        if alvo is not None and numero not in alvo:
            continue
        item = d.get("item") or {}
        questao = item.get("questao") or {}
        rec = questao.get("recursos") or {}
        declarado = sum(len(rec.get(k) or []) for k in ("imagens", "graficos", "tabelas"))
        va = questao.get("visual_assets") or []
        ja_verificado = sum(1 for a in va if (a.get("verificacao") or {}).get("estado")
                            in ("verificada", "verificada_manual"))
        if alvo is None and (declarado == 0 or ja_verificado > 0):
            continue

        regs = regioes.get(numero, [])
        if not regs:
            manifesto.append({"item_id": item.get("item_id"), "numero": numero,
                              "erro": "sem região no layout_model"})
            continue

        cands = vf.candidatos_por_residuo(doc, modelos, regs, questao)
        cands += vf.candidatos_em_alternativas(doc, modelos, regs, questao)

        for i, c in enumerate(cands):
            x0, y0, x1, y1 = c.bbox
            rect = pymupdf.Rect(x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD)
            nome = f"Q{numero:03d}_{c.zona}{('_' + c.letra) if c.letra else ''}_{i}.png"
            pix = doc[c.pagina].get_pixmap(dpi=250, clip=rect)
            pix.save(str(out_dir / nome))
            manifesto.append({
                "item_id": item.get("item_id"), "numero": numero, "arquivo": nome,
                "pagina": c.pagina, "coluna": c.coluna, "zona": c.zona, "letra": c.letra,
                "bbox": [round(v, 2) for v in c.bbox], "n_palavras_residuais": c.n_palavras_residuais,
                "n_drawings": c.n_drawings, "declarado": declarado,
                "wh_px": [pix.width, pix.height],
            })
        if not cands:
            manifesto.append({"item_id": item.get("item_id"), "numero": numero,
                              "declarado": declarado, "sem_candidato": True})

    (out_dir / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(manifesto)} entradas · {sum(1 for m in manifesto if 'arquivo' in m)} candidatos gerados")
    print(f"sem candidato algum: {sum(1 for m in manifesto if m.get('sem_candidato'))}")
    print(f"pasta: {out_dir}")
    doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
