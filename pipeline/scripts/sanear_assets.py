#!/usr/bin/env python
"""Saneamento de `visual_assets` — só onde há evidência determinística.

Duas operações, e nada além delas:

**ARQ-01 · limpar `arquivo` fabricado.** `recursos.*[].arquivo` é campo que o
SERVIDOR carimba com o nome do blob. 16 itens carregam um nome que o modelo
inventou (`screenshot_p31_q178_cubo.png`). Evidência: o valor não casa
`^[0-9a-f]{64}\\.(png|webp)$` **e** não existe no storage — duas checagens
mecânicas, nenhuma visual. Efeito hoje: `exam_images_routes` pede o blob ao
pipeline, recebe 404, devolve 502, e o `<img>` some; e `extract_book_visuals`
trata o campo preenchido como "já resolvido" e pula a questão inteira. Limpar
para `""` não inventa geometria — remove um valor fabricado.

**ANC-01 · registrar âncora VERIFICADA.** Um `visual_asset` recebe `ancora`
apenas quando a cadeia inteira fecha, cada elo verificável:

    PDF → região da questão (layout_model, determinístico)
        → bbox do caso no manifesto congelado
        → PNG renderizado confere com o bbox a 300 dpi (±3 px)
        → bbox contido na região daquela questão, na mesma coluna

Faltando qualquer elo, o asset é marcado `incerta` com o motivo, e **nenhuma
geometria é inventada**. Os 76 assets sem bbox permanecem sem âncora: ausência
de geometria é estado legítimo de incerteza, não lacuna a preencher.

O que este script NUNCA faz: re-renderizar, trocar `src`, apagar blob, mexer em
`item_hash`, enunciado, alternativas, gabarito ou classificação cognitiva.

    .venv/bin/python ../scripts/sanear_assets.py --dry-run
    .venv/bin/python ../scripts/sanear_assets.py --apply
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
MANIFESTO_CONGELADO = STORAGE / "visual_audit" / "manifest.2026-08-26.frozen.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(BACKEND))
from backfill_gabarito import diff_caminhos  # noqa: E402
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

RE_BLOB = re.compile(r"^[0-9a-f]{64}\.(png|webp|jpg|jpeg)$")
DPI = 300
TOLERANCIA_PX = 3

CAMINHOS_PERMITIDOS = re.compile(
    r"^item\.questao\.(?:"
    r"recursos\.[a-z_]+\[\d+\]\.arquivo(?:_modelo)?"
    r"|visual_assets\[\d+\]\.(?:ancora|verificacao)(?:\..*)?"
    r")$"
)


def caminho_permitido(c: str) -> bool:
    return bool(CAMINHOS_PERMITIDOS.match(c))


def _png_confere(blob: Path, bbox) -> tuple[bool, str]:
    """O PNG no storage corresponde ao bbox do manifesto renderizado a 300 dpi?

    É o elo que liga o retângulo declarado ao pixel realmente entregue. Sem
    ele, `ancora` seria uma afirmação sobre geometria que ninguém conferiu.
    """
    if not blob.is_file():
        return False, "blob ausente"
    try:
        from PIL import Image
        largura, altura = Image.open(blob).size
    except Exception as exc:  # noqa: BLE001
        return False, f"png ilegível: {exc}"
    x0, y0, x1, y1 = bbox
    if x1 <= x0 or y1 <= y0:
        return False, "bbox degenerado"
    # O dpi do recorte NÃO é constante no corpus (há assets a 150, 200 e 300).
    # A evidência que importa não é "bate com 300 dpi", e sim "as duas escalas
    # concordam" — o PNG é uma renderização uniforme DESTE retângulo.
    escala_x = largura / (x1 - x0)
    escala_y = altura / (y1 - y0)
    if abs(escala_x - escala_y) > 0.02 * max(escala_x, escala_y):
        return False, (f"escalas divergem: {escala_x:.3f} x {escala_y:.3f} "
                       f"(png {largura}x{altura}, bbox {x1-x0:.1f}x{y1-y0:.1f})")
    return True, f"{escala_x * 72:.0f}dpi"


def planejar(doc, casos, modelos, regioes, blobs: set[str], agora: str) -> dict:
    item_antes = doc.get("item") or {}
    item = copy.deepcopy(item_antes)
    questao = item.get("questao") or {}
    item_id = item.get("item_id") or doc.get("item_id") or ""
    numero = int(doc.get("question_number") or 0)

    limpos, ancoras, incertos = [], [], []

    # ---- ARQ-01 ----------------------------------------------------------
    recursos = questao.get("recursos") or {}
    for chave, lista in (recursos.items() if isinstance(recursos, dict) else []):
        if not isinstance(lista, list):
            continue
        for rec in lista:
            if not isinstance(rec, dict):
                continue
            arquivo = rec.get("arquivo") or ""
            if not arquivo:
                continue
            formato_ok = bool(RE_BLOB.match(arquivo))
            existe = arquivo in blobs
            if formato_ok and existe:
                continue
            if "arquivo_modelo" not in rec:
                rec["arquivo_modelo"] = arquivo
            rec["arquivo"] = ""
            limpos.append({
                "recurso": f"{chave}/{rec.get('id') or '?'}",
                "valor_removido": arquivo,
                "evidencia": {
                    "formato_blob_valido": formato_ok,
                    "existe_no_storage": existe,
                    "regra": "ARQ-01",
                },
            })

    # ---- ANC-01 ----------------------------------------------------------
    for asset in (questao.get("visual_assets") or []):
        asset_id = asset.get("asset_id")
        caso = casos.get((item_id, asset_id))
        motivo = None
        bbox = pagina_idx = None

        if caso is None:
            motivo = "sem caso no manifesto congelado"
        elif not caso.get("bbox") or caso.get("page_used") is None:
            motivo = "caso sem geometria registrada"
        else:
            bbox, pagina_idx = caso["bbox"], pagina_do_caso(caso)
            ok, detalhe = _png_confere(STORAGE / "blobs" / (asset.get("src") or ""), bbox)
            if not ok:
                motivo = f"png não confere com o bbox ({detalhe})"
            dpi_medido = detalhe if ok else None

        coluna = None
        dpi_medido = dpi_medido if motivo is None else None
        if motivo is None:
            modelo = modelos.get(pagina_idx)
            if modelo is None:
                motivo = "página fora do modelo de layout"
            else:
                x0, y0, x1, y1 = bbox
                coluna = modelo.coluna_de(x0, x1)
                if coluna is None:
                    motivo = "bbox cruza a calha entre colunas"
                else:
                    regs = [r for r in regioes.get(numero, [])
                            if r.pagina == pagina_idx
                            and (coluna == modelo.LARGURA_TOTAL or r.coluna == coluna)]
                    if not regs:
                        motivo = "questão sem região nesta página/coluna"
                    elif not any(r.contem((x0, y0, x1, y1)) for r in regs):
                        motivo = "bbox fora da região da questão"

        if motivo is None:
            asset["ancora"] = {
                "pagina": pagina_idx,
                "coluna": coluna,
                "bbox": [round(v, 2) for v in bbox],
                "dpi": dpi_medido,
                "evidencia": "pdf>regiao>asset>bbox>questao",
                "modelo_layout": modelos[pagina_idx].metodo,
                "verificado_em": asset.get("verificacao", {}).get("verificado_em", agora),
            }
            asset["verificacao"] = {"estado": "verificada", "verificado_em":
                                    asset.get("verificacao", {}).get("verificado_em", agora)}
            ancoras.append({"asset_id": asset_id, "pagina": pagina_idx, "coluna": coluna})
        else:
            # Regra de parada: sem evidência suficiente, NÃO se escolhe uma
            # reconstrução. Marca-se o estado e preserva-se o asset.
            asset["verificacao"] = {
                "estado": "incerta",
                "motivo": motivo,
                "verificado_em": asset.get("verificacao", {}).get("verificado_em", agora),
            }
            asset.pop("ancora", None)
            incertos.append({"asset_id": asset_id, "motivo": motivo})

    caminhos = diff_caminhos({"item": item_antes}, {"item": item})
    return {
        "item_id": item_id, "doc_id": doc.get("id"), "numero": numero,
        "book_id": doc.get("book_id"),
        "arquivos_limpos": limpos, "ancoras": ancoras, "incertos": incertos,
        "item_novo": item, "caminhos": caminhos,
        "caminhos_proibidos": [c for c in caminhos if not caminho_permitido(c)],
        "mudou": bool(caminhos),
    }


def validar(planos, blobs_antes: set[str], esperado: dict) -> list[str]:
    falhas = []
    proibidos = [(p["item_id"], p["caminhos_proibidos"]) for p in planos if p["caminhos_proibidos"]]
    if proibidos:
        falhas.append(f"VIS-01 caminhos fora da allowlist: {proibidos[:3]}")

    # nenhum `src` pode mudar, nenhum blob some
    for p in planos:
        antes = [a.get("src") for a in
                 ((p["item_novo"].get("questao") or {}).get("visual_assets") or [])]
        if any(s and s not in blobs_antes for s in antes):
            falhas.append(f"VIS-02 {p['item_id']} referencia blob inexistente")

    if any(p["mudou"] for p in planos):
        n_limpos = sum(len(p["arquivos_limpos"]) for p in planos)
        if n_limpos != esperado["arquivos"]:
            falhas.append(f"VIS-03 esperava limpar {esperado['arquivos']} arquivos "
                          f"fabricados, encontrou {n_limpos}")

    # todo asset tem estado declarado: verificada ou incerta, nunca ausente
    for p in planos:
        for a in ((p["item_novo"].get("questao") or {}).get("visual_assets") or []):
            estado = (a.get("verificacao") or {}).get("estado")
            if estado not in ("verificada", "incerta"):
                falhas.append(f"VIS-04 {p['item_id']}/{a.get('asset_id')} sem estado de verificação")
            if estado == "incerta" and "ancora" in a:
                falhas.append(f"VIS-05 {p['item_id']}/{a.get('asset_id')} incerta COM âncora — "
                              "geometria inventada")
    return falhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cred", default=str(DEFAULT_CRED))
    ap.add_argument("--manifest", default=str(MANIFESTO_CONGELADO))
    ap.add_argument("--out-dir", default=str(REPO / ".saneamento"))
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true")
    modo.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    import pymupdf
    from pymongo import MongoClient

    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    dbp, dba = cli["sapiens_pipeline"], cli["sapiens_aluno"]
    blobs = {p.name for p in (STORAGE / "blobs").glob("*")}
    casos = {(c["item_id"], c.get("asset_id")): c
             for c in json.loads(Path(args.manifest).read_text(encoding="utf-8"))["cases"]}
    agora = datetime.now(timezone.utc).isoformat()

    docs = list(dbp.pipelines.find({}))
    por_book = collections.defaultdict(list)
    for d in docs:
        por_book[d.get("book_id")].append(d)

    planos = []
    for book_id, lista in sorted(por_book.items()):
        caminho = next(iter((STORAGE / "questions" / str(book_id) / "book").glob("*.pdf")), None)
        if caminho is None:
            print(f"  ! book {book_id} sem PDF — assets ficam incertos por falta de fonte")
            modelos, regioes = {}, {}
        else:
            pdf = pymupdf.open(str(caminho))
            modelos = lm.modelo_documento(pdf)
            regioes = lm.regioes_por_questao(pdf, modelos)
            pdf.close()
        for d in lista:
            planos.append(planejar(d, casos, modelos, regioes, blobs, agora))

    tocados = [p for p in planos if p["mudou"]]
    esperado = {"arquivos": 16}
    falhas = validar(planos, blobs, esperado)

    n_anc = sum(len(p["ancoras"]) for p in planos)
    n_inc = sum(len(p["incertos"]) for p in planos)
    n_arq = sum(len(p["arquivos_limpos"]) for p in planos)

    print("=" * 80)
    print(f"{'DRY-RUN' if args.dry_run else 'APLICANDO'} · saneamento de visual_assets")
    print("=" * 80)
    print(f"  itens ......................... {len(planos)}")
    print(f"  documentos a tocar ............ {len(tocados)}")
    print(f"  ARQ-01 arquivos fabricados .... {n_arq}")
    print(f"  ANC-01 âncoras VERIFICADAS .... {n_anc}")
    print(f"  assets marcados INCERTOS ...... {n_inc}")
    motivos = collections.Counter(i["motivo"] for p in planos for i in p["incertos"])
    for m, n in motivos.most_common():
        print(f"      {n:>4}  {m}")
    campos = collections.Counter(
        re.sub(r"\[\d+\]", "[*]", c) for p in tocados for c in p["caminhos"])
    print("\n  diff previsto:")
    for campo, n in sorted(campos.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>5}×  {campo}")

    print("\n  ARQ-01 · evidência por item:")
    for p in planos:
        for l in p["arquivos_limpos"]:
            e = l["evidencia"]
            print(f"    {p['item_id']:<32} {l['recurso']:<16} {l['valor_removido']:<34} "
                  f"formato_ok={e['formato_blob_valido']} existe={e['existe_no_storage']}")

    print(f"\n  INVARIANTES: {'todos verificados' if not falhas else 'FALHA'}")
    for f in falhas:
        print(f"    FALHA  {f}")

    out = Path(args.out_dir) / f"sanear_assets.plano.{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}.json"
    out.write_text(json.dumps(
        [{k: v for k, v in p.items() if k != "item_novo"} for p in planos],
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  plano: {out}")

    if falhas:
        print("\nEscrita recusada.")
        return 2
    if args.dry_run:
        print("Nada foi escrito.")
        return 0
    if not tocados:
        print("\nNADA A FAZER — os quatro stores já refletem esta análise.")
        return 0

    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(args.cred))
    col = firestore.client().collection("itens")

    contagem = collections.Counter()
    for p in tocados:
        col.document(p["doc_id"]).update({"item.questao": p["item_novo"]["questao"]})
        contagem["firestore_itens"] += 1
    for p in tocados:
        contagem["pipelines"] += dbp.pipelines.update_one(
            {"id": p["doc_id"]}, {"$set": {"item.questao": p["item_novo"]["questao"]}}
        ).modified_count
    for p in tocados:
        contagem["questoes_master"] += dba.questoes_master.update_one(
            {"id": p["doc_id"]}, {"$set": {"item.questao": p["item_novo"]["questao"]}}
        ).modified_count
    for p in tocados:
        questao = p["item_novo"]["questao"]
        contagem["questoes_public"] += dba.questoes_public.update_one(
            {"item_id": p["item_id"]},
            {"$set": {"questao.recursos": questao.get("recursos") or {},
                      "questao.visual_assets": questao.get("visual_assets") or []}},
        ).modified_count

    print("\nESCRITA CONCLUÍDA")
    for store, n in contagem.items():
        print(f"  {store:<20} {n:>4} documentos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
