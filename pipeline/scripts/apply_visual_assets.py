"""Grava `questao.visual_assets` a partir do manifesto gerado por
`extract_book_visuals.py` — Fase 5 da auditoria de recuperação de visuais.

Só mexe em CAMPO ADITIVO NOVO (`visual_assets`), em 3 lugares:
  - sapiens_pipeline.pipelines        (fonte da verdade)      -> item.questao.visual_assets
  - sapiens_aluno.questoes_master     (espelho, mesmo formato) -> item.questao.visual_assets
  - sapiens_aluno.questoes_public     (espelho achatado)       -> questao.visual_assets

NÃO toca em enunciado, alternativas, gabarito, ontologia, classificação
cognitiva ou em `recursos` (o campo legado `recursos.imagens[].arquivo`
continua intacto, exatamente como estava).

`item_hash` é recalculado após adicionar `visual_assets` — mesmo padrão já
usado por `figure_extractor.py` ao anexar `arquivo` a uma imagem (o hash
cobre todo o bloco `questao`, então uma alteração puramente de exibição
visual já invalida o hash hoje; não é uma alteração de comportamento nova).

Cada asset é copiado para o storage endereçado por conteúdo do pipeline
(`storage.put_object_deduped`) — o mesmo mecanismo que `figure_extractor.py`
já usa para `recursos.imagens[].arquivo` — para reaproveitar a rota existente
`GET /api/blobs/{sha256}.{ext}` sem precisar de infraestrutura nova.

Uso (de dentro de `pipeline/backend`, mesmo Mongo/.env do backend):
    .venv/bin/python ../scripts/apply_visual_assets.py dry-run
    .venv/bin/python ../scripts/apply_visual_assets.py backup
    .venv/bin/python ../scripts/apply_visual_assets.py apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


def _load_manifest(audit_root: Path) -> dict:
    return json.loads((audit_root / "manifest.json").read_text(encoding="utf-8"))


def _grouped_assets(manifest: dict) -> dict[str, list[dict]]:
    by_item: dict[str, list[dict]] = {}
    for c in manifest["cases"]:
        if c["classification"] not in ("EXTRAIVEL_DIRETAMENTE", "RECORTE_DETERMINISTICO"):
            continue
        if c.get("duplicate_of"):
            continue  # mesmo elemento já representado por outro caso da mesma questão
        by_item.setdefault(c["item_id"], []).append(c)
    return by_item


def _order_key(c: dict):
    # Visuais ancorados na página (bbox conhecido) vêm primeiro, na ordem em
    # que aparecem na página; fórmulas (sem bbox — LaTeX renderizado à parte,
    # não recortado do PDF) vêm depois, na ordem em que o Gemini as declarou.
    if c.get("bbox"):
        return (0, c.get("page_used") or 0, c["bbox"][1])
    return (1, 0, 0)


def build_visual_assets_by_item(manifest: dict, audit_root: Path, put_object_deduped) -> dict[str, list[dict]]:
    by_item = _grouped_assets(manifest)
    result: dict[str, list[dict]] = {}
    blob_cache: dict[str, str] = {}  # file relativo -> nome do blob (dedup local, evita reler o mesmo arquivo)
    for item_id, cases in by_item.items():
        cases.sort(key=_order_key)
        assets = []
        for pos, c in enumerate(cases):
            file_rel = c["file"]
            if file_rel not in blob_cache:
                data = (audit_root / file_rel).read_bytes()
                stored = put_object_deduped(data, "image/png", f"{c['asset_id']}.png")
                blob_cache[file_rel] = Path(stored["path"]).name
            assets.append(
                {
                    "asset_id": c["asset_id"],
                    "type": c["kind"],
                    "src": blob_cache[file_rel],
                    "position": pos,
                    "source_page": c.get("page_used"),
                }
            )
        result[item_id] = assets
    return result


def _backup(db, item_ids: list[str], out_path: Path) -> None:
    dump = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipelines": list(db_pipeline.pipelines.find({"item_id": {"$in": item_ids}})),
        "questoes_master": list(db_aluno.questoes_master.find({"item_id": {"$in": item_ids}})),
        "questoes_public": list(db_aluno.questoes_public.find({"item_id": {"$in": item_ids}})),
    }
    out_path.write_text(json.dumps(dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"backup gravado: {out_path} ({len(item_ids)} questões x 3 coleções)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["dry-run", "backup", "apply"])
    parser.add_argument("--backend-dir", default=str(BACKEND_DIR))
    args = parser.parse_args()

    backend_dir = Path(args.backend_dir).resolve()
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))
    from dotenv import load_dotenv

    load_dotenv(backend_dir / ".env")

    import pymongo
    from item_contract import compute_item_hash
    from storage import put_object_deduped

    global db_pipeline, db_aluno
    mongo_url = os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017")
    client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    db_pipeline = client[os.environ.get("DB_NAME", "sapiens_pipeline")]
    db_aluno = client["sapiens_aluno"]

    audit_root = backend_dir / "_storage" / "sapiens-cognitive" / "visual_audit"
    manifest = _load_manifest(audit_root)

    if args.mode == "dry-run":
        by_item = _grouped_assets(manifest)
        print(f"questões a atualizar: {len(by_item)}")
        print(f"total de assets: {sum(len(v) for v in by_item.values())}")
        for item_id, cases in list(by_item.items())[:5]:
            print(f"  {item_id}: {[(c['kind'], c['asset_id']) for c in cases]}")
        print("  ...")
        for coll_name, coll in (("pipelines", db_pipeline.pipelines), ("questoes_master", db_aluno.questoes_master), ("questoes_public", db_aluno.questoes_public)):
            found = coll.count_documents({"item_id": {"$in": list(by_item.keys())}})
            print(f"documentos encontrados em {coll_name}: {found}/{len(by_item)}")
        return

    by_item_ids = list(_grouped_assets(manifest).keys())

    if args.mode == "backup":
        out_path = audit_root / "mongo_backup_before_visual_assets.json"
        _backup(db_pipeline, by_item_ids, out_path)
        return

    # apply
    visual_assets_by_item = build_visual_assets_by_item(manifest, audit_root, put_object_deduped)

    updated = {"pipelines": 0, "questoes_master": 0, "questoes_public": 0}
    missing = {"pipelines": [], "questoes_master": [], "questoes_public": []}

    for item_id, assets in visual_assets_by_item.items():
        doc = db_pipeline.pipelines.find_one({"item_id": item_id}, {"item.questao": 1})
        if not doc:
            missing["pipelines"].append(item_id)
        else:
            questao = dict(doc["item"]["questao"])
            questao["visual_assets"] = assets
            new_hash = compute_item_hash(questao)
            db_pipeline.pipelines.update_one(
                {"item_id": item_id},
                {"$set": {"item.questao.visual_assets": assets, "item_hash": new_hash}},
            )
            updated["pipelines"] += 1

        doc = db_aluno.questoes_master.find_one({"item_id": item_id}, {"item.questao": 1})
        if not doc:
            missing["questoes_master"].append(item_id)
        else:
            questao = dict(doc["item"]["questao"])
            questao["visual_assets"] = assets
            new_hash = compute_item_hash(questao)
            db_aluno.questoes_master.update_one(
                {"item_id": item_id},
                {"$set": {"item.questao.visual_assets": assets, "item_hash": new_hash}},
            )
            updated["questoes_master"] += 1

        doc = db_aluno.questoes_public.find_one({"item_id": item_id}, {"questao": 1})
        if not doc:
            missing["questoes_public"].append(item_id)
        else:
            questao = dict(doc["questao"])
            questao["visual_assets"] = assets
            new_hash = compute_item_hash(questao)
            db_aluno.questoes_public.update_one(
                {"item_id": item_id},
                {"$set": {"questao.visual_assets": assets, "item_hash": new_hash}},
            )
            updated["questoes_public"] += 1

    print("atualizados:", updated)
    print("não encontrados:", {k: v for k, v in missing.items() if v})

    _reespelhar_firestore(by_item_ids, db_pipeline)


def _reespelhar_firestore(item_ids: list[str], db_pipeline) -> None:
    """Empurra os itens tocados para o Firestore `itens`.

    Sem este passo, `visual_assets` existe só no Mongo — e `_auto_sync_loop`
    do aluno reconstrói `questoes_public` A PARTIR do Firestore a cada 300 s,
    apagando o que foi aplicado aqui. Até 2026-08-26 o re-espelhamento era
    manual e não documentado; os assets de 24/08 sobreviveram porque alguém
    rodou o sync à mão depois.
    """
    try:
        import firestore_sync
    except ImportError:  # pragma: no cover - só no ambiente do pipeline
        print("  ! firestore_sync indisponível — re-espelhamento NÃO feito")
        return
    enviados = 0
    for item_id in item_ids:
        doc = db_pipeline.pipelines.find_one({"item_id": item_id}, {"_id": 0})
        if not doc:
            continue
        if firestore_sync.update_question_sync(doc.get("id"), doc):
            enviados += 1
    print(f"  re-espelhados para o Firestore: {enviados}/{len(item_ids)}")


if __name__ == "__main__":
    main()
