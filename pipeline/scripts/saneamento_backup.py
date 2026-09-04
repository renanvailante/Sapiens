#!/usr/bin/env python
"""Snapshot versionado dos stores que o saneamento do corpus pode tocar.

Somente leitura nas fontes. Cada execução cria um diretório NOVO, carimbado
com a hora UTC — nunca sobrescreve um snapshot anterior, porque o valor de um
backup de saneamento é justamente poder comparar o estado antes de cada fase.

Cobre os quatro stores de questão MAIS a série de behavior e os documentos de
aluno. Os dois últimos não estavam no `mongo_backup_before_visual_assets.json`
de 24/08 e são exatamente o que a retificação da Fase 2 precisa para ser
auditável: sem o estado original dos eventos não há como provar o que foi
corrigido.

    .venv/bin/python ../scripts/saneamento_backup.py --label fase0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO / ".saneamento"
DEFAULT_CRED = REPO / ".secrets" / "firebase-service-account.json"
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _json_default(obj):
    # ObjectId, DatetimeWithNanoseconds, Sentinel... nada disso precisa voltar
    # como tipo nativo: o backup é evidência, não fonte de restore automático.
    return str(obj)


def _dump(path: Path, docs: list[dict]) -> dict:
    path.write_text(
        json.dumps(docs, ensure_ascii=False, indent=1, default=_json_default),
        encoding="utf-8",
    )
    raw = path.read_bytes()
    return {
        "arquivo": path.name,
        "documentos": len(docs),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _firestore_client(cred_path: Path):
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(cred_path)))
    return firestore.client()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--label", default="", help="sufixo legível para o diretório")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--cred", default=str(DEFAULT_CRED))
    ap.add_argument("--skip-firestore", action="store_true")
    args = ap.parse_args()

    stamp = _now_stamp() + (f"-{args.label}" if args.label else "")
    out = Path(args.out) / stamp
    out.mkdir(parents=True, exist_ok=False)

    from pymongo import MongoClient

    mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    arquivos: list[dict] = []

    print(f"snapshot -> {out}")

    for db_name, coll_name in (
        ("sapiens_pipeline", "pipelines"),
        ("sapiens_pipeline", "books"),
        ("sapiens_aluno", "questoes_master"),
        ("sapiens_aluno", "questoes_public"),
    ):
        docs = list(mongo[db_name][coll_name].find({}))
        info = _dump(out / f"mongo.{db_name}.{coll_name}.json", docs)
        info["origem"] = f"mongo://{db_name}/{coll_name}"
        arquivos.append(info)
        print(f"  {info['origem']:<46} {info['documentos']:>5} docs")

    if not args.skip_firestore:
        cred = Path(args.cred)
        if not cred.is_file():
            print(f"ERRO: credencial não encontrada: {cred}", file=sys.stderr)
            return 2
        fs = _firestore_client(cred)

        itens = [d.to_dict() | {"_doc_id": d.id} for d in fs.collection("itens").stream()]
        info = _dump(out / "firestore.itens.json", itens)
        info["origem"] = "firestore://itens"
        arquivos.append(info)
        print(f"  {info['origem']:<46} {info['documentos']:>5} docs")

        alunos, eventos = [], []
        for snap in fs.collection("students").stream():
            alunos.append(snap.to_dict() | {"_doc_id": snap.id})
            for ev in fs.collection("students").document(snap.id).collection("behavior").stream():
                eventos.append(ev.to_dict() | {"_doc_id": ev.id, "_student_doc": snap.id})

        for nome, docs in (("firestore.students.json", alunos),
                           ("firestore.behavior.json", eventos)):
            info = _dump(out / nome, docs)
            info["origem"] = f"firestore://{nome[10:-5].replace('.', '/')}"
            arquivos.append(info)
            print(f"  {info['origem']:<46} {info['documentos']:>5} docs")

    manifesto = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "gerado_por": "saneamento_backup.py",
        "label": args.label,
        "mongo_url": MONGO_URL.split("@")[-1],
        "firebase_project": "sapiens-dataset" if not args.skip_firestore else None,
        "somente_leitura": True,
        "arquivos": arquivos,
    }
    (out / "MANIFEST.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nMANIFEST.json gravado · {sum(a['documentos'] for a in arquivos)} documentos no total")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
