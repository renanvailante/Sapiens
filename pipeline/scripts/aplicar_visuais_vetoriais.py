#!/usr/bin/env python
"""Aplica candidatos vetoriais REVISADOS VISUALMENTE como `visual_assets`.

Lê um arquivo de decisões (JSON): por questão, a lista de recortes aceitos,
cada um com bbox EXPLÍCITO em pontos do PDF (não o candidato bruto — o bbox
já revisado/ajustado nesta rodada) e papel (principal/alternativa_figura).
Renderiza cada bbox a 300dpi no momento da aplicação (garante bytes
determinísticos e auditáveis a partir da MESMA fonte oficial), grava o blob
deduplicado, e escreve `visual_assets` nos 4 stores.

Mesma disciplina das aplicações anteriores: preserva fórmulas (`FOR-`) e
qualquer asset humano já verificado (`HUM-`) que não esteja sendo
substituído; nunca toca `item_hash` de propósito (só o de conteúdo, que já
diverge por precedente — ver GOV-03); nunca toca enunciado/alternativas/
gabarito/estrutura_cognitiva; idempotente (src é sha256 do render, refazer
não duplica).

Formato de `decisoes.json`:
{
  "2022": {
    "93": [{"papel":"principal","bbox":[x0,y0,x1,y1],"pagina":1}],
    "118": [{"papel":"principal","bbox":[...],"pagina":10},
            {"papel":"alternativa_figura","letra":"A","bbox":[...],"pagina":10}, ...]
  }
}

    .venv/bin/python ../scripts/aplicar_visuais_vetoriais.py decisoes.json --dry-run
    .venv/bin/python ../scripts/aplicar_visuais_vetoriais.py decisoes.json --apply
"""
from __future__ import annotations

import argparse
import collections
import copy
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
DEFAULT_CRED = REPO / ".secrets" / "firebase-service-account.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(BACKEND))
from backfill_gabarito import diff_caminhos  # noqa: E402

BOOKS = {
    2022: ("6b1c29d5-033e-4a20-9149-64e3179e6d5e", "book/2022_PV_impresso_D2_CD5.pdf"),
    2023: ("6ba5747b-1cfa-4428-b1cb-632b7a44eba1", "book/2023_PV_impresso_D2_CD5.pdf"),
    2024: ("a1ab65fd-8c48-44a9-aa48-9c94ebe0eb0d", "book/2024_PV_impresso_D2_CD5.pdf"),
}

CAMINHOS_PERMITIDOS = re.compile(
    r"^item\.questao\.visual_assets(\[\d+\]|\[\])?(\.[a-z_]+(\[\d+\])?)*$"
)


def caminho_permitido(c: str) -> bool:
    return bool(CAMINHOS_PERMITIDOS.match(c))


def planejar(ano: int, numero: int, itens_decisao: list[dict], dbp, doc, agora: str) -> dict | None:
    doc_item = dbp.pipelines.find_one({"item.fonte.ano": ano, "question_number": str(numero)})
    if doc_item is None:
        return {"numero": numero, "erro": "item ausente do banco"}
    item_antes = doc_item.get("item") or {}
    item_novo = copy.deepcopy(item_antes)
    questao = item_novo.setdefault("questao", {})
    antigos = questao.get("visual_assets") or []
    preservados = [a for a in antigos if (a.get("asset_id") or "").startswith(("FOR-", "HUM-"))]

    novos = []
    principais = [d for d in itens_decisao if d["papel"] == "principal"]
    alternativas = [d for d in itens_decisao if d["papel"] == "alternativa_figura"]

    renders = []  # (asset_dict_sem_src, bytes_png)
    for i, d in enumerate(principais):
        renders.append(({
            "asset_id": f"VEC-IMG-{i+1:02d}", "type": "imagem", "papel": "principal",
            "position": i, "origem": "vetorial_pdf_oficial",
            "motivo": d.get("motivo", "residuo vetorial/texto, região correta, conferido visualmente"),
        }, d))
    for d in alternativas:
        renders.append(({
            "asset_id": f"VEC-ALT-{d['letra']}", "type": "imagem", "papel": "alternativa_figura",
            "letra": d["letra"], "position": len(principais), "origem": "vetorial_pdf_oficial",
            "motivo": d.get("motivo", "residuo vetorial/texto, região correta, conferido visualmente"),
        }, d))

    for asset, d in renders:
        pagina = d["pagina"]
        x0, y0, x1, y1 = d["bbox"]
        pix = doc[pagina].get_pixmap(dpi=300, clip=__import__("pymupdf").Rect(x0, y0, x1, y1))
        png_bytes = pix.tobytes("png")
        asset["_dados"] = png_bytes
        asset["_bbox_origem"] = [round(v, 2) for v in (x0, y0, x1, y1)]
        asset["_pagina_origem"] = pagina
        novos.append(asset)

    questao["visual_assets"] = preservados + novos
    item_novo_diff = copy.deepcopy(item_novo)
    for a in item_novo_diff["questao"]["visual_assets"]:
        a.pop("_dados", None)
    caminhos = diff_caminhos({"item": item_antes}, {"item": item_novo_diff})
    return {
        "numero": numero, "item_id": item_antes.get("item_id"), "doc_id": doc_item.get("id"),
        "item_novo": item_novo, "caminhos": caminhos,
        "caminhos_proibidos": [c for c in caminhos if not caminho_permitido(c)],
        "mudou": bool(caminhos), "n_principais": len(principais), "n_alternativas": len(alternativas),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("decisoes")
    ap.add_argument("--cred", default=str(DEFAULT_CRED))
    ap.add_argument("--out-dir", default=str(REPO / ".saneamento"))
    ap.add_argument("--skip-firestore", action="store_true")
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true")
    modo.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    import pymupdf
    from pymongo import MongoClient

    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    dbp, dba = cli["sapiens_pipeline"], cli["sapiens_aluno"]
    decisoes = json.loads(Path(args.decisoes).read_text(encoding="utf-8"))
    agora = datetime.now(timezone.utc).isoformat()

    planos = []
    docs_abertos = {}
    for ano_str, itens in decisoes.items():
        ano = int(ano_str)
        book_id, rel = BOOKS[ano]
        caminho = STORAGE / "questions" / book_id / rel
        doc = pymupdf.open(str(caminho))
        docs_abertos[ano] = doc
        for numero_str, lista in itens.items():
            p = planejar(ano, int(numero_str), lista, dbp, doc, agora)
            if p:
                p["ano"] = ano
                planos.append(p)

    validos = [p for p in planos if "item_novo" in p]
    tocados = [p for p in validos if p["mudou"]]
    erros = [p for p in planos if "item_novo" not in p]
    proibidos = [(p["item_id"], p["caminhos_proibidos"]) for p in validos if p["caminhos_proibidos"]]

    print("=" * 84)
    print(f"{'DRY-RUN' if args.dry_run else 'APLICANDO'} · visuais reconstruídos por resíduo vetorial")
    print("=" * 84)
    for ano in sorted({p["ano"] for p in planos}):
        sub = [p for p in planos if p["ano"] == ano]
        ok = [p for p in sub if "item_novo" in p]
        print(f"  {ano}: {len(sub)} questões · {sum(p['n_principais'] for p in ok)} figuras principais · "
              f"{sum(p['n_alternativas'] for p in ok)} figuras de alternativa")
    if erros:
        print(f"\n  ERROS: {[(e['numero']) for e in erros]}")
    if proibidos:
        print(f"\n  FALHA VIS-01 caminhos fora da allowlist: {proibidos[:3]}")
        print("\nEscrita recusada.")
        return 2

    out = Path(args.out_dir) / f"aplicar_visuais_vetoriais.plano.{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}.json"
    out.write_text(json.dumps([
        {k: v for k, v in p.items() if k != "item_novo"} for p in planos
    ], ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"\n  plano: {out}")

    for doc in docs_abertos.values():
        doc.close()

    if args.dry_run:
        print("Nada foi escrito.")
        return 0
    if not tocados:
        print("\nNADA A FAZER.")
        return 0

    import storage

    gravados = dedup = 0
    for p in tocados:
        for a in p["item_novo"]["questao"]["visual_assets"]:
            dados = a.pop("_dados", None)
            if dados is None:
                continue
            resultado = storage.put_object_deduped(dados, "image/png", "vec.png")
            a["src"] = Path(resultado["path"]).name
            a["ancora"] = {
                "pagina": a.pop("_pagina_origem"), "bbox": a.pop("_bbox_origem"), "dpi": 300,
                "evidencia": "pdf>regiao>residuo_vetorial>bbox>questao",
            }
            a["verificacao"] = {"estado": "verificada_manual", "evidencia": a.get("motivo", ""),
                               "fonte": "vetorial_pdf_oficial", "verificado_em": agora}
            if resultado["deduped"]:
                dedup += 1
            else:
                gravados += 1
    print(f"\nblobs: {gravados} novos, {dedup} deduplicados")

    contagem = collections.Counter()
    firestore_ok = False
    if not args.skip_firestore:
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            if not firebase_admin._apps:
                firebase_admin.initialize_app(credentials.Certificate(args.cred))
            col = firestore.client().collection("itens")
            for p in tocados:
                col.document(p["doc_id"]).update({"item.questao.visual_assets":
                                                   p["item_novo"]["questao"]["visual_assets"]})
                contagem["firestore_itens"] += 1
            firestore_ok = True
        except Exception as exc:  # noqa: BLE001
            print(f"  ! Firestore indisponível ({type(exc).__name__}) — só Mongo; Firestore PENDENTE.")

    for p in tocados:
        contagem["pipelines"] += dbp.pipelines.update_one(
            {"id": p["doc_id"]},
            {"$set": {"item.questao.visual_assets": p["item_novo"]["questao"]["visual_assets"]}},
        ).modified_count
    for p in tocados:
        contagem["questoes_master"] += dba.questoes_master.update_one(
            {"id": p["doc_id"]},
            {"$set": {"item.questao.visual_assets": p["item_novo"]["questao"]["visual_assets"]}},
        ).modified_count
    for p in tocados:
        contagem["questoes_public"] += dba.questoes_public.update_one(
            {"item_id": p["item_id"]},
            {"$set": {"questao.visual_assets": p["item_novo"]["questao"]["visual_assets"]}},
        ).modified_count

    print("\nESCRITA CONCLUÍDA" if firestore_ok or args.skip_firestore else "\nESCRITA PARCIAL (Firestore pendente)")
    for store, n in contagem.items():
        print(f"  {store:<20} {n:>4} documentos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
