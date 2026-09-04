#!/usr/bin/env python
"""Cria/atualiza `sapiens_pipeline.gabaritos_oficiais` a partir dos PDFs do INEP.

Coleção NOVA. Não reutiliza `sapiens_aluno.answer_keys`, que é outra coisa —
os gabaritos de inglês/espanhol de `enem_seed.py`, lidos por `exam_routes.py`
em quatro pontos e contados no painel admin. Reusar aquele nome quebraria as
duas coisas em silêncio.

Imutabilidade: um gabarito nunca é editado no lugar. Se o mesmo caderno voltar
com um PDF de SHA-256 diferente (o INEP republicou), grava-se uma versão nova
e a anterior é marcada `vigente: false`. Um gabarito que muda em silêncio
depois de eventos de behavior gravados contra ele é indepurável.

Idempotência: reexecutar com o mesmo PDF não escreve nada.

    .venv/bin/python ../scripts/seed_gabaritos_oficiais.py --dry-run
    .venv/bin/python ../scripts/seed_gabaritos_oficiais.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")
COLECAO = "gabaritos_oficiais"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gabarito_inep import parse_pdf  # noqa: E402


def chave_prova(prova: dict) -> str:
    return "-".join([
        "ENEM", str(prova.get("ano")), f"D{prova.get('dia')}",
        f"CD{prova.get('caderno')}", str(prova.get("cor")),
    ])


def montar_documento(pdf: Path, procedencia: dict, versao: int, autor: str) -> dict:
    parsed = parse_pdf(pdf)
    prova = {"banca": "ENEM", **parsed["prova"], "aplicacao": "impresso", "reaplicacao": False}
    chave = chave_prova(prova)
    origem = {
        **parsed["origem"],
        "url_oficial": procedencia.get("url_oficial"),
        "http_last_modified": procedencia.get("http_last_modified"),
        "http_etag": procedencia.get("http_etag"),
        "baixado_em": procedencia.get("baixado_em"),
        "conferencia": procedencia.get("conferencia"),
    }
    return {
        "_id": f"{chave}-v{versao}",
        "chave_prova": chave,
        "versao": versao,
        "vigente": True,
        "prova": prova,
        "origem": origem,
        "entradas": parsed["entradas"],
        "cobertura": parsed["cobertura"],
        "confianca": "oficial",
        "imutavel": True,
        "registrado_por": autor,
        "registrado_em": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf-dir", default=str(REPO / ".saneamento" / "gabaritos_inep"))
    ap.add_argument("--autor", default="saneamento-2026-08-26")
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true")
    modo.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir)
    procedencias = {
        p["arquivo"]: p
        for p in json.loads((pdf_dir / "PROCEDENCIA.json").read_text(encoding="utf-8"))
    }

    from pymongo import MongoClient

    db = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)["sapiens_pipeline"]
    col = db[COLECAO]

    planos = []
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        proc = procedencias.get(pdf.name)
        if proc is None:
            print(f"  ! {pdf.name}: sem entrada em PROCEDENCIA.json — ignorado")
            continue

        provisorio = montar_documento(pdf, proc, versao=1, autor=args.autor)
        chave, sha = provisorio["chave_prova"], provisorio["origem"]["sha256"]
        existentes = list(col.find({"chave_prova": chave}).sort("versao", 1))

        if any(d["origem"]["sha256"] == sha for d in existentes):
            planos.append({"acao": "inalterado", "chave": chave, "doc": provisorio})
            continue

        versao = (existentes[-1]["versao"] + 1) if existentes else 1
        doc = montar_documento(pdf, proc, versao=versao, autor=args.autor)
        planos.append({
            "acao": "nova_versao" if existentes else "criar",
            "chave": chave, "doc": doc,
            "supersede": [d["_id"] for d in existentes],
        })

    print(f"{'DRY-RUN' if args.dry_run else 'APLICANDO'} · coleção sapiens_pipeline.{COLECAO}")
    print(f"documentos hoje: {col.estimated_document_count()}\n")
    for p in planos:
        d, c = p["doc"], p["doc"]["cobertura"]
        print(f"  [{p['acao']:>12}] {p['doc']['_id']}")
        print(f"                 faixa {c['faixa'][0]}-{c['faixa'][1]} · {c['declaradas']} entradas · "
              f"anuladas {c['anuladas'] or '—'} · lacunas {c['lacunas'] or '—'}")
        print(f"                 sha256 {d['origem']['sha256'][:24]}…")
        print(f"                 {d['origem']['url_oficial']}")
        if p.get("supersede"):
            print(f"                 supersede {p['supersede']}")

    if args.dry_run:
        print("\nNada foi escrito.")
        return 0

    col.create_index([("chave_prova", 1), ("versao", 1)], unique=True)
    escritos = 0
    for p in planos:
        if p["acao"] == "inalterado":
            continue
        for antigo in p.get("supersede", []):
            col.update_one({"_id": antigo}, {"$set": {"vigente": False}})
        col.replace_one({"_id": p["doc"]["_id"]}, p["doc"], upsert=True)
        escritos += 1
    print(f"\n{escritos} documento(s) gravado(s) · total agora: {col.count_documents({})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
