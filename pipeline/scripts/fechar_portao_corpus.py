#!/usr/bin/env python
"""Fecha o portão da camada de crença nos itens já persistidos.

`item_contract.normalize_item` passou a atribuir `revisado = False` de forma
incondicional (Fase 2), mas isso só vale para itens que passem por ele de novo.
Os 268 já gravados continuam carregando o `revisado: true` que o próprio modelo
escreveu — 223 deles. Este backfill fecha o portão no que já está no banco.

O que muda, e nada além disso:

    item.qualidade.revisado                      -> False
    item.qualidade.apto_para_camada_de_crenca    -> {"valor": False}
    item.qualidade.revisado_modelo               -> procedência, gravada uma vez

`revisado_modelo` é ao `revisado` o que `correta_modelo` é ao `correta`: guarda
o que o modelo afirmou, para que o fechamento seja reversível por derivação e
para que a telemetria de "quantos itens o anotador se autoaprovou" continue
existindo depois da correção.

`item_hash` não é tocado — e nem precisaria ser: `compute_item_hash` cobre só o
bloco `questao`, e `qualidade` está fora dele.

O caminho de volta a `revisado: true` passa a ser exclusivamente
`revisao_humana.registrar()`, com revisor identificado.

    .venv/bin/python ../scripts/fechar_portao_corpus.py --dry-run
    .venv/bin/python ../scripts/fechar_portao_corpus.py --apply
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")
DEFAULT_CRED = REPO / ".secrets" / "firebase-service-account.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / "pipeline" / "backend"))
from backfill_gabarito import diff_caminhos  # noqa: E402
import revisao_humana  # noqa: E402

CAMINHOS_PERMITIDOS = (
    "item.qualidade.revisado",
    "item.qualidade.apto_para_camada_de_crenca",
    "item.qualidade.revisado_modelo",
)


def caminho_permitido(c: str) -> bool:
    return any(c == p or c.startswith(p + ".") for p in CAMINHOS_PERMITIDOS)


def planejar(doc: dict, db, agora: str) -> dict:
    item_antes = doc.get("item") or {}
    item = copy.deepcopy(item_antes)
    qual = item.setdefault("qualidade", {}) or {}

    revisado_antes = qual.get("revisado")
    apto_antes = qual.get("apto_para_camada_de_crenca")

    # Derivação a partir do REGISTRO externo, nunca do que o item afirma.
    aprovado = revisao_humana.esta_aprovado(
        db, item.get("item_id") or "", item.get("item_hash") or ""
    )

    if "revisado_modelo" not in qual:
        qual["revisado_modelo"] = {
            "valor": revisado_antes,
            "apto_declarado": (apto_antes.get("valor")
                               if isinstance(apto_antes, dict) else apto_antes),
            "capturado_em": agora,
            "origem": "anotador_gemini",
        }
    qual["revisado"] = aprovado
    qual["apto_para_camada_de_crenca"] = {"valor": aprovado}
    item["qualidade"] = qual

    caminhos = diff_caminhos({"item": item_antes}, {"item": item})
    return {
        "item_id": item.get("item_id") or doc.get("item_id"),
        "doc_id": doc.get("id"),
        "revisado_antes": revisado_antes,
        "revisado_depois": aprovado,
        "tem_registro_humano": aprovado,
        "item_novo": item,
        "caminhos": caminhos,
        "caminhos_proibidos": [c for c in caminhos if not caminho_permitido(c)],
        "mudou": bool(caminhos),
    }


def validar(planos: list[dict], esperado: dict) -> list[str]:
    falhas = []
    proibidos = [(p["item_id"], p["caminhos_proibidos"]) for p in planos if p["caminhos_proibidos"]]
    if proibidos:
        falhas.append(f"POR-04 caminhos fora da allowlist em {len(proibidos)} itens: {proibidos[:3]}")

    abertos = [p["item_id"] for p in planos if p["revisado_depois"] and not p["tem_registro_humano"]]
    if abertos:
        falhas.append(f"POR-01 portão aberto sem registro humano: {abertos[:5]}")

    sem_proc = [p["item_id"] for p in planos if "revisado_modelo" not in p["item_novo"].get("qualidade", {})]
    if sem_proc:
        falhas.append(f"POR-03 revisado_modelo ausente em {len(sem_proc)} itens")

    if any(p["mudou"] for p in planos):
        fechados = [p for p in planos if p["revisado_antes"] and not p["revisado_depois"]]
        if len(fechados) != esperado["fechar"]:
            falhas.append(f"POR-02 esperava fechar {esperado['fechar']} itens, "
                          f"encontrou {len(fechados)}")
    return falhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cred", default=str(DEFAULT_CRED))
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true")
    modo.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    from pymongo import MongoClient

    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    dbp, dba = cli["sapiens_pipeline"], cli["sapiens_aluno"]
    revisao_humana.garantir_indices(dbp)

    agora = datetime.now(timezone.utc).isoformat()
    planos = [planejar(d, dbp, agora) for d in dbp.pipelines.find({})]
    tocados = [p for p in planos if p["mudou"]]
    esperado = {"fechar": 223}

    print("=" * 78)
    print(f"{'DRY-RUN' if args.dry_run else 'APLICANDO'} · fechamento do portão da crença")
    print("=" * 78)
    antes = collections.Counter(p["revisado_antes"] for p in planos)
    depois = collections.Counter(p["revisado_depois"] for p in planos)
    print(f"  itens ......................... {len(planos)}")
    print(f"  revisado antes ................ {dict(antes)}")
    print(f"  revisado depois ............... {dict(depois)}")
    print(f"  com registro humano ........... {sum(1 for p in planos if p['tem_registro_humano'])}")
    print(f"  documentos a tocar ............ {len(tocados)}")
    campos = collections.Counter(c for p in tocados for c in p["caminhos"])
    for campo, n in sorted(campos.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>5}×  {campo}")

    falhas = validar(planos, esperado)
    print(f"\n  INVARIANTES: {'todos verificados' if not falhas else 'FALHA'}")
    for f in falhas:
        print(f"    FALHA  {f}")
    if falhas:
        print("\nEscrita recusada.")
        return 2
    if args.dry_run:
        print("\nNada foi escrito.")
        return 0
    if not tocados:
        print("\nNADA A FAZER — o portão já está fechado nos 4 stores.")
        return 0

    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(args.cred))
    col = firestore.client().collection("itens")

    contagem = collections.Counter()
    for p in tocados:
        col.document(p["doc_id"]).update({"item.qualidade": p["item_novo"]["qualidade"]})
        contagem["firestore_itens"] += 1
    for p in tocados:
        contagem["pipelines"] += dbp.pipelines.update_one(
            {"id": p["doc_id"]}, {"$set": {"item.qualidade": p["item_novo"]["qualidade"]}}
        ).modified_count
    for p in tocados:
        contagem["questoes_master"] += dba.questoes_master.update_one(
            {"id": p["doc_id"]}, {"$set": {"item.qualidade": p["item_novo"]["qualidade"]}}
        ).modified_count
    # `questoes_public` não carrega `qualidade` (o doc do aluno é mínimo, por
    # contrato — ver test_doc_publico_nao_vaza_classificacao_cognitiva). Nada a
    # fazer lá, e é por isso que o portão atua no agregado, não na projeção.

    print("\nESCRITA CONCLUÍDA")
    for store, n in contagem.items():
        print(f"  {store:<20} {n:>4} documentos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
