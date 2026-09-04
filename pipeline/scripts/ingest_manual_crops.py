"""Ingere os recortes feitos manualmente (ver `questoes_para_recorte_manual.md`)
para os casos que a extração determinística não conseguiu resolver sozinha.

Cada arquivo PNG deve se chamar `{item_id}__{asset_ref_id}.png`, ex.:
    ITEM-ENEM-2022-AMARELO-Q093__IMG-01.png

O que este script faz, por arquivo encontrado:
  1. Localiza o caso correspondente em `manifest.json` (por item_id + asset_ref_id).
  2. Copia o PNG para o storage do pipeline, endereçado por conteúdo
     (mesmo mecanismo de `figure_extractor.py`/`extract_book_visuals.py`).
  3. Marca o caso como resolvido no manifesto: `classification: EXTRAIVEL_DIRETAMENTE`,
     `confidence: "manual_humana"`, `reason: "recorte manual do usuário"`.
  4. Grava uma cópia em `visual_audit/human_ground_truth.jsonl` — um registro por
     elemento (item_id, banca/ano/prova/numero, tipo, descrição, página de origem,
     nome do arquivo) para servir de dataset de referência (imagem final + contexto
     textual) caso vocês queiram treinar/avaliar um modelo de extração no futuro.

NÃO escreve no Mongo/Firestore sozinho — depois de rodar este script, rode
`apply_visual_assets.py dry-run` (pra conferir) e depois `backup`/`apply`, exatamente
como no lote anterior.

Uso:
    .venv/bin/python ../scripts/ingest_manual_crops.py /caminho/da/pasta/com/pngs
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pasta", help="Pasta com os PNGs recortados manualmente")
    parser.add_argument("--backend-dir", default=str(BACKEND_DIR))
    args = parser.parse_args()

    backend_dir = Path(args.backend_dir).resolve()
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))
    from dotenv import load_dotenv

    load_dotenv(backend_dir / ".env")

    audit_root = backend_dir / "_storage" / "sapiens-cognitive" / "visual_audit"
    manifest_path = audit_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    by_key = {(c["item_id"], c["asset_ref_id"]): c for c in manifest["cases"]}

    pasta = Path(args.pasta)
    pngs = sorted(pasta.glob("*.png"))
    if not pngs:
        print(f"Nenhum .png encontrado em {pasta}")
        return

    gt_path = audit_root / "human_ground_truth.jsonl"
    gt_lines = []
    updated, nao_reconhecidos, ja_resolvidos = 0, [], []

    for png in pngs:
        stem = png.stem  # {item_id}__{asset_ref_id}
        if "__" not in stem:
            nao_reconhecidos.append(png.name)
            continue
        item_id, asset_ref_id = stem.split("__", 1)
        case = by_key.get((item_id, asset_ref_id))
        if case is None:
            nao_reconhecidos.append(png.name)
            continue
        if case["classification"] != "NEEDS_MANUAL_REVIEW":
            ja_resolvidos.append(png.name)
            continue

        data = png.read_bytes()
        asset_id = case.get("asset_id") or f"{case['kind'][:3].upper()}-{asset_ref_id}"
        # Só grava a cópia local aqui — o envio pro storage endereçado por
        # conteúdo (put_object_deduped) já é feito por `apply_visual_assets.py`
        # a partir deste arquivo, exatamente como no lote extraído automaticamente.
        rel_path = Path("assets") / case["book_id"] / item_id.replace("/", "_") / f"{asset_id}_manual.png"
        out_path = audit_root / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)

        case["classification"] = "EXTRAIVEL_DIRETAMENTE"
        case["confidence"] = "manual_humana"
        case["reason"] = "recorte manual do usuário"
        case["needs_manual_review"] = False
        case["asset_id"] = asset_id
        case["file"] = str(rel_path)
        case["bbox"] = None  # recorte feito fora do PDF, sem bbox determinístico associado
        updated += 1

        gt_lines.append(json.dumps({
            "item_id": item_id,
            "asset_ref_id": asset_ref_id,
            "kind": case["kind"],
            "descricao": case.get("descricao", ""),
            "book_id": case["book_id"],
            "source_page": case.get("pages", [None])[0],
            "arquivo": png.name,
        }, ensure_ascii=False))

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if gt_lines:
        with gt_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(gt_lines) + "\n")

    print(f"atualizados: {updated}")
    print(f"já estavam resolvidos (ignorados): {len(ja_resolvidos)} {ja_resolvidos}")
    print(f"nome não reconhecido (ignorados): {len(nao_reconhecidos)} {nao_reconhecidos}")
    print(f"manifesto atualizado: {manifest_path}")
    if gt_lines:
        print(f"dataset de referência: {gt_path} (+{len(gt_lines)} linhas)")
    print("\nPróximo passo: .venv/bin/python ../scripts/apply_visual_assets.py dry-run")


if __name__ == "__main__":
    main()
