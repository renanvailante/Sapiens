#!/usr/bin/env python
"""Camada C do auditor — geometria dos recortes JÁ APLICADOS. Somente leitura.

Re-analisa o PDF contra o bbox de cada `visual_asset` persistido, usando o
modelo de layout determinístico (`layout_model`). Não re-extrai nada, não
altera nada: produz o boletim de contaminação dos recortes que já estão no
banco.

    C1  o bbox está dentro da região da questão (mesma coluna)?
    C2  o bbox invade a região de outra questão?
    C3  o bbox entra no bloco de alternativas?
    C4  vazamento: o recorte contém texto do enunciado/alternativas?
    C5  truncamento: há traço ou glifo cruzando a borda do bbox?
    C6  o bbox contém glifos da marca d'água?

A geometria vive só no `manifest.json` — `visual_assets` no banco guarda
`asset_id`, `type`, `src`, `position` e `source_page`, sem bbox. Por isso a
auditoria geométrica depende do manifesto, e por isso ele foi congelado antes
de qualquer reprocessamento.

    .venv/bin/python ../scripts/audit_geometria.py
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "pipeline" / "backend"
STORAGE = BACKEND / "_storage" / "sapiens-cognitive"
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")

sys.path.insert(0, str(BACKEND))
import layout_model as lm  # noqa: E402

# `manifest.page_used` é 1-BASED; os índices do PyMuPDF são 0-based. Evidência
# mecânica, medida sobre os 66 assets com bbox nos três cadernos: usando
# `page_used`, ZERO ficam contidos na região da própria questão; usando
# `page_used - 1`, 34 ficam — e os 3 cadernos concordam separadamente
# (2022: 12, 2023: 6, 2024: 16). Não é ajuste de tolerância, é conversão de
# base. Toda a Camada C rodada antes desta descoberta comparava o bbox contra
# o conteúdo da página SEGUINTE, e seus veredictos não valem nada.
DESLOCAMENTO_PAGINA_MANIFESTO = -1


def pagina_do_caso(caso) -> int | None:
    p = caso.get("page_used")
    return None if p is None else p + DESLOCAMENTO_PAGINA_MANIFESTO

RE_ALTERNATIVA = re.compile(r"^[A-E]$")
RE_QNUM = re.compile(r"-(\d{4})-[A-Z]+-Q(\d{3})")
TOKEN_MINIMO = 4          # palavras curtas casam por acaso
VAZAMENTO_MINIMO = 3      # nº de tokens do enunciado dentro do bbox p/ acusar
MARGEM_TRUNCAMENTO = 1.5  # pt


def tokens(texto: str) -> set[str]:
    return {t.strip(".,;:()[]").lower() for t in (texto or "").split()
            if len(t.strip(".,;:()[]")) >= TOKEN_MINIMO}


def auditar_asset(doc, modelos, regioes, item, caso) -> dict:
    bbox = caso.get("bbox")
    pagina_idx = pagina_do_caso(caso)
    numero = int(caso["question_number"])
    achados: list[str] = []

    if not bbox or pagina_idx is None:
        return {"achados": ["SEM-GEOMETRIA"], "auditavel": False}

    x0, y0, x1, y1 = bbox
    pagina = doc[pagina_idx]
    modelo = modelos[pagina_idx]
    regs = [r for r in regioes.get(numero, []) if r.pagina == pagina_idx]

    # C1 — contido na região da questão, na mesma coluna
    coluna = modelo.coluna_de(x0, x1)
    if coluna is None:
        achados.append("C1-CRUZA-CALHA")
    dentro = [r for r in regs if r.coluna == coluna and r.contem((x0, y0, x1, y1))]
    if regs and not dentro:
        achados.append("C1-FORA-DA-REGIAO")

    # C2 — invade a região de outra questão
    for outro, lista in regioes.items():
        if outro == numero:
            continue
        for r in lista:
            if r.pagina != pagina_idx or r.coluna != coluna:
                continue
            if y0 < r.y1 and y1 > r.y0:
                sobreposicao = min(y1, r.y1) - max(y0, r.y0)
                if sobreposicao > 5:
                    achados.append(f"C2-INVADE-Q{outro}")
                    break

    # C3 — entra no bloco de alternativas
    if dentro:
        r = dentro[0]
        col = modelo.colunas[r.coluna]
        alt_ys = [w[1] for w in pagina.get_text("words")
                  if RE_ALTERNATIVA.match(w[4])
                  and r.y0 <= w[1] <= r.y1 and abs(w[0] - col[0]) < 40]
        if alt_ys and y1 > min(alt_ys):
            achados.append("C3-ENTRA-NAS-ALTERNATIVAS")

    # C4 — vazamento de texto do próprio item
    questao = item.get("questao") or {}
    referencia = tokens(questao.get("enunciado") or "")
    for a in questao.get("alternativas") or []:
        referencia |= tokens(a.get("texto") or "")
    dentro_bbox = [w for w in pagina.get_text("words")
                   if w[0] >= x0 - 1 and w[2] <= x1 + 1 and w[1] >= y0 - 1 and w[3] <= y1 + 1]
    marca = set(modelo.marca_dagua)
    conteudo = [w for w in dentro_bbox if (w[0], w[1], w[2], w[3]) not in marca]
    vazados = [w[4] for w in conteudo if w[4].strip(".,;:()[]").lower() in referencia]
    if len(vazados) >= VAZAMENTO_MINIMO:
        achados.append(f"C4-VAZAMENTO({len(vazados)})")

    # C5 — truncamento: traço ou glifo cruzando a borda
    def cruza(bx0, by0, bx1, by1) -> bool:
        dentro_x = bx1 > x0 and bx0 < x1
        dentro_y = by1 > y0 and by0 < y1
        if not (dentro_x and dentro_y):
            return False
        return (bx0 < x0 - MARGEM_TRUNCAMENTO or bx1 > x1 + MARGEM_TRUNCAMENTO
                or by0 < y0 - MARGEM_TRUNCAMENTO or by1 > y1 + MARGEM_TRUNCAMENTO)

    # Um traço só está TRUNCADO se ele nasce dentro do recorte e sai. Um
    # retângulo que ENVOLVE o recorte inteiro (moldura da figura, caixa da
    # página) cruza a borda por construção e não é truncamento — contá-lo
    # acusava recortes que o olho humano aprovou.
    largura_bbox, altura_bbox = x1 - x0, y1 - y0
    cortados = 0
    for d in pagina.get_drawings():
        r = d.get("rect")
        if r is None:
            continue
        envolve = (r.x0 <= x0 + MARGEM_TRUNCAMENTO and r.x1 >= x1 - MARGEM_TRUNCAMENTO
                   and r.y0 <= y0 + MARGEM_TRUNCAMENTO and r.y1 >= y1 - MARGEM_TRUNCAMENTO)
        maior = (r.x1 - r.x0) > largura_bbox and (r.y1 - r.y0) > altura_bbox
        if envolve or maior:
            continue
        if cruza(r.x0, r.y0, r.x1, r.y1):
            cortados += 1
    for w in pagina.get_text("words"):
        if (w[0], w[1], w[2], w[3]) in marca:
            continue
        if cruza(w[0], w[1], w[2], w[3]):
            cortados += 1
    if cortados:
        achados.append(f"C5-TRUNCAMENTO({cortados})")

    # C6 — marca d'água dentro do recorte
    dentro_marca = [w for w in dentro_bbox if (w[0], w[1], w[2], w[3]) in marca]
    if dentro_marca:
        achados.append(f"C6-MARCA-DAGUA({len(dentro_marca)})")

    return {"achados": achados, "auditavel": True,
            "coluna": coluna, "bbox": bbox, "pagina": pagina_idx}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(REPO / ".saneamento"))
    ap.add_argument("--manifest", default=str(STORAGE / "visual_audit" / "manifest.2026-08-26.frozen.json"))
    args = ap.parse_args()

    import pymupdf
    from pymongo import MongoClient

    dbp = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)["sapiens_pipeline"]
    manifesto = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    casos = {(c["item_id"], c.get("asset_id")): c for c in manifesto["cases"]}

    itens, pdfs = {}, {}
    for doc in dbp.pipelines.find({}, {"item_id": 1, "book_id": 1, "item": 1}):
        itens[doc["item_id"]] = doc
    for book in dbp.books.find({}, {"id": 1, "files": 1, "ano": 1}):
        caminho = next(iter((STORAGE / "questions" / book["id"] / "book").glob("*.pdf")), None)
        if caminho:
            pdfs[book["id"]] = caminho

    resultados = []
    for book_id, caminho in sorted(pdfs.items()):
        if not any(d.get("book_id") == book_id for d in itens.values()):
            continue
        doc = pymupdf.open(str(caminho))
        modelos = lm.modelo_documento(doc)
        regioes = lm.regioes_por_questao(doc, modelos)
        print(f"  {caminho.name}: {lm.resumo(modelos)}")

        for item_id, pipeline_doc in itens.items():
            if pipeline_doc.get("book_id") != book_id:
                continue
            item = pipeline_doc.get("item") or {}
            for asset in ((item.get("questao") or {}).get("visual_assets") or []):
                caso = casos.get((item_id, asset.get("asset_id")))
                if caso is None:
                    resultados.append({"item_id": item_id, "asset_id": asset.get("asset_id"),
                                       "type": asset.get("type"), "achados": ["SEM-CASO-NO-MANIFESTO"],
                                       "auditavel": False})
                    continue
                r = auditar_asset(doc, modelos, regioes, item, caso)
                resultados.append({"item_id": item_id, "asset_id": asset.get("asset_id"),
                                   "type": asset.get("type"), **r})
        doc.close()

    auditaveis = [r for r in resultados if r["auditavel"]]
    limpos = [r for r in auditaveis if not r["achados"]]
    codigos = collections.Counter(
        a.split("(")[0].split("-Q")[0] for r in auditaveis for a in r["achados"])

    print(f"\n{'='*74}\nCAMADA C · GEOMETRIA DOS RECORTES APLICADOS\n{'='*74}")
    print(f"  assets no banco .............. {len(resultados)}")
    print(f"  auditáveis (com bbox) ........ {len(auditaveis)}")
    print(f"  sem geometria registrada ..... {len(resultados) - len(auditaveis)}")
    print(f"  LIMPOS ....................... {len(limpos)}")
    print(f"  com pelo menos um defeito .... {len(auditaveis) - len(limpos)}")
    print(f"\n  por código:")
    for c, n in sorted(codigos.items(), key=lambda kv: -kv[1]):
        print(f"    {c:<28} {n:>4}")

    print(f"\n  defeituosos:")
    for r in sorted(auditaveis, key=lambda x: x["item_id"]):
        if r["achados"]:
            print(f"    {r['item_id']:<32} {r['asset_id']:<14} {', '.join(r['achados'])}")

    out = Path(args.out_dir) / f"audit_geometria.{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}.json"
    out.write_text(json.dumps({
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "somente_leitura": True,
        "manifesto": Path(args.manifest).name,
        "resumo": {"assets": len(resultados), "auditaveis": len(auditaveis),
                   "limpos": len(limpos), "por_codigo": dict(codigos)},
        "resultados": resultados,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{out}\nNada foi alterado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
