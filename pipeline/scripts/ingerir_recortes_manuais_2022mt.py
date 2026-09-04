#!/usr/bin/env python
"""Incorpora os recortes manuais do ENEM 2022 Matemática (136-180) como
`visual_assets` — ground truth PRIORITÁRIO sobre o recorte automático.

Fonte: `cadernos enem/revisao humana imagens cadernos/ENEM 2023 Amarelo/`
(pasta rotulada 2023; conteúdo confirmadamente 2022 — ver
`auditoria/PENDENCIAS-SANEAMENTO-2026-08-26.md` §6). 44 arquivos únicos, uma
duplicata de conteúdo detectada e resolvida (ver `motivo` de cada asset).

Duas correções de mapeamento aplicadas com EVIDÊNCIA, não inferência:

1. **Q163 IMG-01/02 mal nomeados como "Q162".** Os dois arquivos dentro de
   `Q163 ENEM 2022 Amarelo/` chamam-se `...Q162__IMG-01/02.png`, mas o
   conteúdo (sequência de dobradura de papel, ponto R) bate exatamente com a
   descrição que o MODELO deu para Q163 (`recursos.imagens` no banco:
   "Sequência de dobraduras" / "Marcação do ponto R"), não com Q162 (cartela
   de bingo). Os arquivos de Q162 no nível raiz da pasta já são os corretos.
   Confirmado por inspeção visual das duas imagens contra as duas descrições.

2. **Q163 alternativa B era cópia de A (mesmo SHA-256).** A alternativa B do
   PDF oficial (INEP, página 25, cluster vetorial ancorado no rótulo "B") é
   um círculo liso — nada a ver com o recorte que o arquivo `IMG-B.png`
   continha (idêntico a `IMG-A.png`, um quadrado recortado). Recorte-se B
   diretamente do PDF oficial, no bbox do cluster vetorial associado ao
   rótulo "B" (mesma fonte de verdade usada para o gabarito), e confere-se
   visualmente antes de gravar. Não é invenção: é extração determinística do
   documento oficial, com verificação visual anexada como evidência.

O que este script NUNCA faz: apagar o arquivo original do ground truth,
alterar `item_hash` sem necessidade real de conteúdo, tocar formulas (`FOR-`),
gabarito, ou qualquer item fora de 2022 Matemática.

    .venv/bin/python ../scripts/ingerir_recortes_manuais_2022mt.py --dry-run
    .venv/bin/python ../scripts/ingerir_recortes_manuais_2022mt.py --apply
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "pipeline" / "backend"
GT_DIR = REPO / "cadernos enem" / "revisao humana imagens cadernos" / "ENEM 2023 Amarelo"
BOOK_PDF = (BACKEND / "_storage/sapiens-cognitive/questions"
            / "6b1c29d5-033e-4a20-9149-64e3179e6d5e/book/2022_PV_impresso_D2_CD5.pdf")
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")
DEFAULT_CRED = REPO / ".secrets" / "firebase-service-account.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(BACKEND))
from backfill_gabarito import diff_caminhos  # noqa: E402

RE_PRINCIPAL = re.compile(r"ITEM-ENEM-2022-AMARELO-Q(\d{3})__([A-Z]+)-(\d{2})\.png$")
RE_ALTERNATIVA = re.compile(r"ITEM-ENEM-2022-AMARELO-Q(\d{3})__IMG-([A-E])\.png$")

# Item -> número REAL (corrige o mislabeling do §1 da docstring). Aplicado só
# aos dois arquivos dentro de `Q163 .../ITEM-...-Q162__IMG-0N.png`.
REMAPEAMENTO_ITEM = {
    ("Q163 ENEM 2022 Amarelo/ITEM-ENEM-2022-AMARELO-Q162__IMG-01.png"): 163,
    ("Q163 ENEM 2022 Amarelo/ITEM-ENEM-2022-AMARELO-Q162__IMG-02.png"): 163,
}
# Ordem dentro da questão, para os dois arquivos remapeados (Figuras 1-3 antes
# de Figuras 4-5, conforme o enunciado e a leitura visual confirmada).
POSICAO_REMAPEADA = {
    "Q163 ENEM 2022 Amarelo/ITEM-ENEM-2022-AMARELO-Q162__IMG-01.png": 0,
    "Q163 ENEM 2022 Amarelo/ITEM-ENEM-2022-AMARELO-Q162__IMG-02.png": 1,
}

# Q163-B: SHA-256 do arquivo de ground truth que está corrompido (cópia de A).
# Detectado automaticamente no dry-run (duplicata de conteúdo com IMG-A) e
# substituído pelo recorte extraído do PDF oficial — ver função `reconstruir_q163_b`.
Q163_B_PATH = "Q163 ENEM 2022 Amarelo/Alternativas Q158 Enem 2022 Amarelo/ITEM-ENEM-2022-AMARELO-Q163__IMG-B.png"

CAMINHOS_PERMITIDOS = re.compile(
    # `visual_assets[]` (sem índice) é como `diff_caminhos` marca uma lista de
    # comprimento diferente — esperado aqui, já que estamos substituindo a
    # lista inteira de assets de imagem/tabela/gráfico por outra de tamanho
    # distinto (fórmulas preservadas + novos recortes humanos).
    r"^item\.questao\.visual_assets(\[\d+\]|\[\])?(\.[a-z_]+(\[\d+\])?)*$"
)


def caminho_permitido(c: str) -> bool:
    return bool(CAMINHOS_PERMITIDOS.match(c))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reconstruir_q163_b(cache: dict) -> bytes:
    """Recorta a alternativa B da Q163 diretamente do PDF oficial.

    Bbox obtido por cluster de desenhos vetoriais ancorado na posição do
    rótulo "B" (mesmo método de evidência do `layout_model`), com padding de
    6pt. Resultado conferido visualmente contra a página renderizada antes
    deste script existir — reproduzido aqui de forma determinística.
    """
    if "q163b" in cache:
        return cache["q163b"]
    import pymupdf

    doc = pymupdf.open(str(BOOK_PDF))
    page = doc[24]  # página 25 (1-based) do caderno impresso
    label_b = next(w for w in page.get_text("words")
                   if w[4] == "B" and w[1] > 500)
    lx, ly = label_b[0], label_b[1]
    cluster = [d["rect"] for d in page.get_drawings()
              if d.get("rect") is not None
              and abs(((d["rect"].y0 + d["rect"].y1) / 2) - (ly + 35)) < 45
              and lx - 5 <= d["rect"].x0 <= lx + 140]
    if not cluster:
        raise RuntimeError("Q163-B: cluster vetorial não encontrado — abortando, não inventar bbox")
    x0 = min(r.x0 for r in cluster) - 6
    y0 = min(r.y0 for r in cluster) - 6
    x1 = max(r.x1 for r in cluster) + 6
    y1 = max(r.y1 for r in cluster) + 6
    pix = page.get_pixmap(dpi=300, clip=pymupdf.Rect(x0, y0, x1, y1))
    data = pix.tobytes("png")
    doc.close()
    cache["q163b"] = data
    cache["q163b_bbox"] = [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]
    return data


def inventariar() -> list[dict]:
    """Varre a pasta de ground truth e classifica cada PNG."""
    itens = []
    conteudo_por_hash: dict[str, list[Path]] = collections.defaultdict(list)
    for f in sorted(GT_DIR.rglob("*.png")):
        conteudo_por_hash[sha256(f.read_bytes())].append(f)

    duplicatas = {h: fs for h, fs in conteudo_por_hash.items() if len(fs) > 1}

    for f in sorted(GT_DIR.rglob("*.png")):
        rel = str(f.relative_to(GT_DIR))
        data = f.read_bytes()
        h = sha256(data)
        corrompido = h in duplicatas

        m_alt = RE_ALTERNATIVA.search(f.name)
        is_alt = "Alternativas" in rel and m_alt is not None

        if is_alt:
            numero, letra = int(m_alt.group(1)), m_alt.group(2)
            if numero == 163 and letra == "B" and corrompido:
                # ground truth corrompido (cópia de A) — substituído por
                # extração direta e verificada do PDF oficial.
                itens.append({
                    "arquivo_origem": rel, "numero": numero, "papel": "alternativa_figura",
                    "letra": letra, "origem": "pdf_oficial_reconstruido",
                    "motivo": "ground truth continha cópia byte-idêntica de IMG-A; "
                             "reconstruído do PDF oficial (INEP, pág. 25) e conferido visualmente",
                    "reconstruir": True,
                })
                continue
            if numero == 163 and letra == "A" and corrompido:
                # A é o lado CORRETO do par duplicado: o conteúdo (quadrado
                # recortado em losango de 4 lobos) bate com a alternativa A
                # renderizada na página 25 do PDF oficial — conferido visual-
                # mente contra o cluster vetorial ancorado no rótulo "A". É o
                # arquivo B que estava com cópia errada, não o A.
                itens.append({
                    "arquivo_origem": rel, "numero": numero, "papel": "alternativa_figura",
                    "letra": letra, "origem": "recorte_manual_humano", "dados": data, "sha256": h,
                    "motivo": "conferido contra o PDF oficial (pág. 25, alternativa A): "
                             "conteúdo bate; o duplicado era o arquivo B, não este",
                })
                continue
            if corrompido:
                # qualquer outra duplicata inesperada: não resolver, marcar pendente
                itens.append({
                    "arquivo_origem": rel, "numero": numero, "papel": "alternativa_figura",
                    "letra": letra, "pendente": True,
                    "motivo": f"conteúdo duplicado de outro arquivo (sha {h[:12]}…) sem "
                             "evidência independente para desambiguar",
                })
                continue
            itens.append({
                "arquivo_origem": rel, "numero": numero, "papel": "alternativa_figura",
                "letra": letra, "origem": "recorte_manual_humano", "dados": data, "sha256": h,
            })
            continue

        # figura principal
        numero_real = REMAPEAMENTO_ITEM.get(rel)
        m = RE_PRINCIPAL.search(f.name)
        if numero_real is None:
            if not m:
                continue
            numero_real = int(m.group(1))
        posicao = POSICAO_REMAPEADA.get(rel)
        if posicao is None:
            # posição por ordem alfabética do nome dentro da própria questão
            # (IMG-01 antes de IMG-02) — mesma ordem que o README descreve.
            posicao = int(m.group(3)) - 1 if m else 0

        item = {
            "arquivo_origem": rel, "numero": numero_real, "papel": "principal",
            "posicao": posicao, "origem": "recorte_manual_humano", "dados": data, "sha256": h,
        }
        if rel in REMAPEAMENTO_ITEM:
            item["motivo"] = ("arquivo nomeado 'Q162' dentro da pasta da Q163; conteúdo "
                              "(dobradura de papel) bate com a descrição do modelo para "
                              "Q163, não com Q162 (cartela de bingo) — remapeado")
        itens.append(item)
    return itens


def planejar(itens: list[dict], dbp) -> tuple[list[dict], dict]:
    reconstrucao_cache: dict = {}
    por_questao: dict[int, list[dict]] = collections.defaultdict(list)
    pendentes = []
    for it in itens:
        if it.get("pendente"):
            pendentes.append(it)
            continue
        if it.get("reconstruir"):
            it["dados"] = reconstruir_q163_b(reconstrucao_cache)
            it["sha256"] = sha256(it["dados"])
            it["bbox_pdf"] = reconstrucao_cache.get("q163b_bbox")
        por_questao[it["numero"]].append(it)

    planos = []
    for numero, lista in sorted(por_questao.items()):
        doc = dbp.pipelines.find_one({"item_id": f"ITEM-ENEM-2022-AMARELO-Q{numero:03d}"})
        if doc is None:
            pendentes.append({"numero": numero, "motivo": "item ausente do banco (lacuna conhecida)"})
            continue
        item_antes = doc.get("item") or {}
        item_novo = copy.deepcopy(item_antes)
        questao = item_novo.setdefault("questao", {})
        antigos = questao.get("visual_assets") or []
        # preserva fórmulas (FOR-) e qualquer asset cujo tipo não seja
        # figura/tabela/gráfico; os demais (oriundos de recorte automático)
        # são SUBSTITUÍDOS pelo ground truth humano, que tem prioridade.
        preservados = [a for a in antigos if (a.get("asset_id") or "").startswith("FOR-")]

        principais = sorted([x for x in lista if x["papel"] == "principal"],
                            key=lambda x: x["posicao"])
        alternativas = sorted([x for x in lista if x["papel"] == "alternativa_figura"],
                              key=lambda x: x["letra"])

        # `src` é endereçado por conteúdo (`storage.build_blob_path`): sha256 +
        # extensão, sem nada aleatório. Prevê-lo aqui — em vez de só depois de
        # gravar o blob — é o que torna a reexecução um NO-OP de verdade: o
        # diff já compara contra o estado final, byte a byte, não contra um
        # esqueleto sem `src`/`verificacao` que pareceria "mudado" para sempre.
        existentes_por_id = {a.get("asset_id"): a for a in antigos
                             if (a.get("asset_id") or "").startswith("HUM-")}

        def _finalizar(asset_id: str, sha: str, extra: dict) -> dict:
            src = f"{sha}.png"
            anterior = existentes_por_id.get(asset_id)
            ja_aplicado = bool(anterior) and anterior.get("src") == src
            return {
                "asset_id": asset_id, "type": "imagem", "src": src,
                "verificacao": {
                    "estado": "verificada_manual",
                    "evidencia": extra.get("motivo", ""),
                    "fonte": extra.get("origem"),
                    # Preserva o timestamp já gravado quando o conteúdo (src)
                    # não mudou — senão cada reexecução envelheceria o
                    # `verificado_em` sem nada realmente ter mudado.
                    "verificado_em": ((anterior or {}).get("verificacao", {}).get("verificado_em")
                                      if ja_aplicado else None),
                },
                **extra,
            }

        novos_assets = []
        for i, p in enumerate(principais):
            novos_assets.append(_finalizar(f"HUM-IMG-{i+1:02d}", p["sha256"], {
                "papel": "principal", "position": i, "_dados": p["dados"],
                "origem": p["origem"],
                "motivo": p.get("motivo", "recorte manual humano, conferido contra o caderno impresso"),
                "arquivo_origem_gt": p["arquivo_origem"],
            }))
        for a in alternativas:
            novos_assets.append(_finalizar(f"HUM-ALT-{a['letra']}", a["sha256"], {
                "papel": "alternativa_figura", "letra": a["letra"], "position": len(principais),
                "_dados": a["dados"], "origem": a["origem"],
                "motivo": a.get("motivo", "recorte manual humano, conferido contra o caderno impresso"),
                "arquivo_origem_gt": a["arquivo_origem"],
                **({"bbox_pdf_oficial": a["bbox_pdf"]} if a.get("bbox_pdf") else {}),
            }))

        questao["visual_assets"] = preservados + novos_assets
        # Diff calculado sobre a forma PÚBLICA do asset (sem os campos
        # internos `_dados`/`_sha256`, que existem só até a gravação do blob
        # e nunca chegam a nenhum store) — senão o invariante de allowlist
        # reprovaria por causa de um campo que nem sequer é persistido.
        item_novo_diff = copy.deepcopy(item_novo)
        for a in item_novo_diff["questao"]["visual_assets"]:
            a.pop("_dados", None)
            a.pop("_sha256", None)
        caminhos = diff_caminhos({"item": item_antes}, {"item": item_novo_diff})
        planos.append({
            "numero": numero, "item_id": item_antes.get("item_id"), "doc_id": doc.get("id"),
            "removidos": [a.get("asset_id") for a in antigos if a not in preservados],
            "adicionados": [a["asset_id"] for a in novos_assets],
            "preservados_formula": [a.get("asset_id") for a in preservados],
            "item_novo": item_novo, "caminhos": caminhos,
            "caminhos_proibidos": [c for c in caminhos if not caminho_permitido(c)],
            "mudou": bool(caminhos),
        })
    return planos, {"pendentes": pendentes}


def validar(planos: list[dict], esperado: dict) -> list[str]:
    falhas = []
    proibidos = [(p["item_id"], p["caminhos_proibidos"]) for p in planos if p["caminhos_proibidos"]]
    if proibidos:
        falhas.append(f"VIS-01 caminhos fora da allowlist: {proibidos[:3]}")

    # VIS-06 é de PRÉ-VOO (só faz sentido quando há trabalho a fazer) — como
    # em `backfill_gabarito.py`, exigi-la também na reexecução converteria
    # "nada a fazer" em erro, o oposto de idempotente.
    n_itens = len([p for p in planos if p["mudou"]])
    if n_itens and n_itens != esperado["itens"]:
        falhas.append(f"VIS-06 esperava {esperado['itens']} itens tocados, encontrou {n_itens}")

    for p in planos:
        letras = [a.split("-")[-1] for a in p["adicionados"] if a.startswith("HUM-ALT-")]
        if len(letras) != len(set(letras)):
            falhas.append(f"VIS-07 {p['item_id']}: letras de alternativa duplicadas {letras}")
        principais = [a for a in p["adicionados"] if a.startswith("HUM-IMG-")]
        if len(principais) != len(set(principais)):
            falhas.append(f"VIS-08 {p['item_id']}: ids de figura principal duplicados")

    return falhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cred", default=str(DEFAULT_CRED))
    ap.add_argument("--out-dir", default=str(REPO / ".saneamento"))
    ap.add_argument("--skip-firestore", action="store_true",
                    help="pula a escrita no Firestore (usar se a cota estiver esgotada)")
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true")
    modo.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    from pymongo import MongoClient

    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    dbp, dba = cli["sapiens_pipeline"], cli["sapiens_aluno"]
    blobs_dir = BACKEND / "_storage" / "sapiens-cognitive" / "blobs"

    itens = inventariar()
    planos, extra = planejar(itens, dbp)
    pendentes = extra["pendentes"]
    esperado = {"itens": 22}
    falhas = validar(planos, esperado)

    tocados = [p for p in planos if p["mudou"]]
    print("=" * 84)
    print(f"{'DRY-RUN' if args.dry_run else 'APLICANDO'} · recortes manuais ENEM 2022 Matemática (136-180)")
    print("=" * 84)
    print(f"  arquivos de ground truth ...... {len(list(GT_DIR.rglob('*.png')))}")
    print(f"  questões afetadas ............. {len(planos)}")
    print(f"  pendentes (sem evidência) ...... {len(pendentes)}")
    for pd in pendentes:
        print(f"      Q{pd.get('numero')}: {pd['motivo']}")

    print(f"\n{'-'*84}\nDIFF POR QUESTÃO\n{'-'*84}")
    total_add = total_rem = 0
    for p in planos:
        total_add += len(p["adicionados"]); total_rem += len(p["removidos"])
        print(f"  Q{p['numero']:<4} remove {p['removidos'] or '—'} "
              f"| adiciona {p['adicionados']} | preserva(fórmula) {p['preservados_formula'] or '—'}")
    print(f"\n  total: -{total_rem} assets antigos, +{total_add} assets novos")

    print(f"\n{'-'*84}\nEVIDÊNCIA DAS DUAS CORREÇÕES DE MAPEAMENTO\n{'-'*84}")
    for p in planos:
        for a in p["item_novo"]["questao"]["visual_assets"]:
            if a.get("asset_id", "").startswith(("HUM-",)) and "motivo" in a and "recorte manual humano, conferido" not in a["motivo"]:
                print(f"  {p['item_id']} / {a['asset_id']}: {a['motivo']}")

    print(f"\n  INVARIANTES: {'todos verificados' if not falhas else 'FALHA'}")
    for f in falhas:
        print(f"    FALHA  {f}")

    out = Path(args.out_dir) / f"ingerir_recortes_2022mt.plano.{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}.json"
    out.write_text(json.dumps([
        {k: v for k, v in p.items() if k != "item_novo"} |
        {"visual_assets_novos": [
            {kk: vv for kk, vv in a.items() if not kk.startswith("_")}
            for a in p["item_novo"]["questao"]["visual_assets"]
        ]}
        for p in planos
    ] + [{"pendentes": pendentes}], ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"\n  plano: {out}")

    if falhas:
        print("\nEscrita recusada.")
        return 2
    if args.dry_run:
        print("Nada foi escrito.")
        return 0
    if not tocados:
        print("\nNADA A FAZER.")
        return 0

    import storage

    # ---- 1) blobs (idempotente por conteúdo) ------------------------------
    # `src` já foi previsto em `_finalizar` (endereçado por sha256, sem nada
    # aleatório); aqui só garante que o blob existe no storage. `verificado_em`
    # só é preenchido se ainda estiver None — reexecutar sobre um asset já
    # aplicado (mesmo `src`) não reescreve o timestamp.
    gravados = dedup = 0
    for p in planos:
        for a in p["item_novo"]["questao"]["visual_assets"]:
            dados = a.pop("_dados", None)
            if dados is None:
                continue
            resultado = storage.put_object_deduped(dados, "image/png", a["src"])
            if a["verificacao"]["verificado_em"] is None:
                a["verificacao"]["verificado_em"] = datetime.now(timezone.utc).isoformat()
            if resultado["deduped"]:
                dedup += 1
            else:
                gravados += 1
    print(f"\nblobs: {gravados} novos, {dedup} deduplicados")

    # ---- 2) escrita nos 4 stores -------------------------------------------
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
            print(f"\n  ! Firestore indisponível ({type(exc).__name__}: {str(exc)[:120]}) — "
                 "seguindo só com os stores Mongo; Firestore fica PENDENTE de re-sincronização.")

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
