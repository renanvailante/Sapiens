#!/usr/bin/env python3
"""Reset completo dos dados dos três apps Sapiens.

Apaga **dados**. Preserva código, contratos, ontologia, testes e documentação.

O que é apagado:

* Mongo `sapiens_pipeline`  — pipelines (itens anotados), books, ontologias
  carregadas no banco, schemas importados.
* Mongo `sapiens_aluno`     — usuários, sessões, provas, gabaritos, análises,
  questões master/públicas, anotações, feed e interações.
* Mongo `sapiens_professor` — imports, turmas, usuários.
* Firestore                 — coleção de itens e a árvore de estudantes
  (`students/{uid}` + subcoleção `behavior`), além da estrutura legada
  `students_behavior`.
* Artefatos binários do pipeline (`STORAGE_MODE`).

O que **não** é tocado:

* `pipeline/docs/` — corpus canônico.
* Qualquer arquivo de código, teste ou configuração.
* O catálogo é **re-semeado** no próximo boot do pipeline, a partir do JSON
  canônico do disco — apagar `ontologies` do Mongo não perde ontologia nenhuma,
  porque o Mongo nunca foi a fonte dela.

Uso::

    python3 scripts/reset_dados.py --dry-run     # só lista o que apagaria
    python3 scripts/reset_dados.py --yes         # executa
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MONGO_ALVOS = {
    "sapiens_pipeline": ["pipelines", "books", "ontologies", "pipeline_schemas"],
    "sapiens_aluno": [
        "users", "user_sessions", "exams", "answer_keys", "analyses",
        "questions", "questoes_master", "questoes_public", "question_annotations",
        "feed_items", "feed_interactions", "feed_progress", "settings",
    ],
    "sapiens_professor": ["imports", "users", "turmas"],
}


def _load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def reset_mongo(dry: bool) -> list[str]:
    from pymongo import MongoClient

    env = _load_env(ROOT / "pipeline" / "backend" / ".env")
    url = os.environ.get("MONGO_URL") or env.get("MONGO_URL") or "mongodb://localhost:27017"
    linhas: list[str] = []
    client = MongoClient(url, serverSelectionTimeoutMS=4000)
    client.admin.command("ping")  # falha cedo e claro se não houver Mongo
    existentes = set(client.list_database_names())
    for dbname, cols in MONGO_ALVOS.items():
        if dbname not in existentes:
            linhas.append(f"  {dbname}: ausente (nada a fazer)")
            continue
        db = client[dbname]
        presentes = set(db.list_collection_names())
        for col in cols:
            if col not in presentes:
                continue
            n = db[col].count_documents({})
            linhas.append(f"  {dbname}.{col}: {n} doc(s)")
            if not dry and n:
                db[col].delete_many({})
        # coleções que não estão na lista: reportadas, nunca apagadas em silêncio
        for extra in sorted(presentes - set(cols)):
            n = db[extra].count_documents({})
            linhas.append(f"  {dbname}.{extra}: {n} doc(s) — NÃO listada, preservada")
    client.close()
    return linhas


def reset_firestore(dry: bool) -> list[str]:
    sys.path.insert(0, str(ROOT / "aluno" / "backend"))
    env = _load_env(ROOT / "aluno" / "backend" / ".env")
    for k in ("FIREBASE_SERVICE_ACCOUNT_PATH", "FIREBASE_PROJECT_ID", "GOOGLE_APPLICATION_CREDENTIALS"):
        if k in env and k not in os.environ:
            os.environ[k] = env[k]
    import firestore_service as fs

    linhas: list[str] = []
    client = fs.get_firestore()

    colecao_itens = os.environ.get("FIRESTORE_COLLECTION") or _load_env(
        ROOT / "pipeline" / "backend" / ".env"
    ).get("FIRESTORE_COLLECTION", "itens")

    def apaga(ref, rotulo: str) -> None:
        docs = list(ref.stream())
        linhas.append(f"  {rotulo}: {len(docs)} doc(s)")
        if dry:
            return
        for d in docs:
            d.reference.delete()

    apaga(client.collection(colecao_itens), f"firestore/{colecao_itens}")

    alunos = list(client.collection("students").stream())
    linhas.append(f"  firestore/students: {len(alunos)} aluno(s)")
    for snap in alunos:
        # a subcoleção precisa morrer antes do documento pai: apagar o pai não
        # apaga as subcoleções no Firestore, deixaria eventos órfãos invisíveis
        eventos = list(snap.reference.collection("behavior").stream())
        linhas.append(f"    students/{snap.id}/behavior: {len(eventos)} evento(s)")
        if not dry:
            for e in eventos:
                e.reference.delete()
            snap.reference.delete()

    legado = client.collection("students_behavior").document("students_id")
    subs = list(legado.collections())
    if subs:
        linhas.append(f"  firestore/students_behavior (legado): {len(subs)} subcoleção(ões)")
        if not dry:
            for sub in subs:
                for d in sub.stream():
                    d.reference.delete()
    return linhas


def reset_storage(dry: bool) -> list[str]:
    env = _load_env(ROOT / "pipeline" / "backend" / ".env")
    modo = (os.environ.get("STORAGE_MODE") or env.get("STORAGE_MODE") or "local").lower()
    if modo == "firebase":
        sys.path.insert(0, str(ROOT / "pipeline" / "backend"))
        for k in ("GOOGLE_APPLICATION_CREDENTIALS", "FIREBASE_STORAGE_BUCKET", "APP_NAME"):
            if k in env and k not in os.environ:
                os.environ[k] = env[k]
        import storage

        if dry:
            return ["  storage(firebase): contagem exige varredura do bucket — pulada em dry-run"]
        n = storage.delete_prefix(f"{storage.APP_NAME}/questions")
        return [f"  storage(firebase): {n} objeto(s) removido(s)"]

    root = Path(env.get("STORAGE_ROOT") or (ROOT / "pipeline" / "backend" / "_storage"))
    if not root.exists():
        return [f"  storage(local): {root} não existe"]
    arquivos = [p for p in root.rglob("*") if p.is_file()]
    linhas = [f"  storage(local) {root}: {len(arquivos)} arquivo(s)"]
    if not dry:
        shutil.rmtree(root)
    return linhas


def main() -> int:
    ap = argparse.ArgumentParser(description="Reset de dados dos 3 apps Sapiens.")
    ap.add_argument("--yes", action="store_true", help="executa de fato")
    ap.add_argument("--dry-run", action="store_true", help="apenas lista")
    ap.add_argument("--skip-firestore", action="store_true")
    ap.add_argument("--skip-mongo", action="store_true")
    ap.add_argument("--skip-storage", action="store_true")
    args = ap.parse_args()

    if not args.yes and not args.dry_run:
        print("Use --dry-run para inspecionar, ou --yes para executar.")
        return 2
    dry = not args.yes

    print("=== RESET DE DADOS SAPIENS " + ("(dry-run) ===" if dry else "(EXECUTANDO) ==="))
    falhas = 0
    for rotulo, skip, fn in (
        ("MongoDB", args.skip_mongo, reset_mongo),
        ("Firestore", args.skip_firestore, reset_firestore),
        ("Object storage", args.skip_storage, reset_storage),
    ):
        print(f"\n{rotulo}:")
        if skip:
            print("  (pulado)")
            continue
        try:
            for linha in fn(dry):
                print(linha)
        except Exception as exc:  # noqa: BLE001
            falhas += 1
            print(f"  INDISPONÍVEL — {type(exc).__name__}: {exc}")

    print("\nPreservados: pipeline/docs/, código, testes, configuração.")
    print("O catálogo é re-semeado no próximo boot do pipeline, a partir do JSON canônico.")
    if falhas:
        print(f"\n{falhas} destino(s) indisponível(is) — nada foi apagado neles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
