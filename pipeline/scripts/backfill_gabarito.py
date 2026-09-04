#!/usr/bin/env python
"""Deriva `alternativas[].correta` do gabarito oficial nos quatro stores.

O que muda em cada item, e nada além disso:

    item.questao.alternativas[*].correta   booleano derivado do gabarito
    item.gabarito_oficial                  procedência (irmão de `questao`)
    item.correta_modelo                    estado ORIGINAL, gravado uma vez só
    item.divergencia_gabarito              só quando o modelo divergiu
    resposta_correta                       letra denormalizada, no topo

O que NÃO muda, e é verificado automaticamente antes de escrever: `item_hash`
(nem o de topo nem o interno), enunciado, letra e texto das alternativas,
`recursos`, `visual_assets`, `estrutura_cognitiva`, `qualidade`, `fonte` e
qualquer outro campo. A checagem é um diff de caminhos com allowlist — um
caminho fora da lista aborta a execução inteira.

`item_hash` fica intocado de propósito. Ele é a chave de junção entre os
eventos de behavior já gravados e o item respondido; recalculá-lo aqui
orfanaria os 249 eventos existentes. A divergência que isso mantém entre
`item_hash` e `compute_item_hash(questao)` já existe em 105 itens e é matéria
da Fase 4 (hash de conteúdo + `render_hash` separado), não desta.

Idempotência: a segunda execução não encontra nada para mudar. `correta_modelo`
é gravado apenas se ausente, então reexecutar nunca sobrescreve o estado
original com o já corrigido.

Reversibilidade: `correta_modelo.bruto` guarda o valor cru de cada letra com o
tipo original (inclusive as strings 'true'/'false' e o `null`), de modo que o
rollback é uma segunda derivação, não uma restauração de backup.

    .venv/bin/python ../scripts/backfill_gabarito.py --dry-run
    .venv/bin/python ../scripts/backfill_gabarito.py --apply
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
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")
DEFAULT_CRED = REPO / ".secrets" / "firebase-service-account.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gabarito_inep import parse_pdf  # noqa: E402
from seed_gabaritos_oficiais import chave_prova  # noqa: E402

RE_QNUM = re.compile(r"-(\d{4})-[A-Z]+-Q(\d{3})")
RE_LETRA_EM_PROSA = re.compile(
    r"alternativa\s+(?:correta\s+)?(?:é\s+)?\(?([A-E])\)?"
    r"|correta\s*(?:é|:)\s*\(?([A-E])\)?",
    re.IGNORECASE,
)

# Único conjunto de caminhos que esta migração tem permissão de alterar.
CAMINHOS_PERMITIDOS = {
    "item.gabarito_oficial",
    "item.correta_modelo",
    "item.divergencia_gabarito",
    "resposta_correta",
}
RE_CAMINHO_CORRETA = re.compile(r"^item\.questao\.alternativas\[\d+\]\.correta$")


def caminho_permitido(caminho: str) -> bool:
    if RE_CAMINHO_CORRETA.match(caminho):
        return True
    return any(caminho == p or caminho.startswith(p + ".") or caminho.startswith(p + "[")
               for p in CAMINHOS_PERMITIDOS)


def diff_caminhos(antes, depois, prefixo="") -> list[str]:
    """Todos os caminhos JSON em que os dois objetos diferem."""
    if isinstance(antes, dict) and isinstance(depois, dict):
        out = []
        for chave in set(antes) | set(depois):
            p = f"{prefixo}.{chave}" if prefixo else chave
            if chave not in antes or chave not in depois:
                out.append(p)
            else:
                out += diff_caminhos(antes[chave], depois[chave], p)
        return out
    if isinstance(antes, list) and isinstance(depois, list):
        if len(antes) != len(depois):
            return [f"{prefixo}[]"]
        out = []
        for i, (a, d) in enumerate(zip(antes, depois)):
            out += diff_caminhos(a, d, f"{prefixo}[{i}]")
        return out
    return [] if antes == depois else [prefixo]


# --------------------------------------------------------------------------
def carregar_gabaritos(db, pdf_dir: Path) -> dict:
    """`{ano: {mapa, gabarito_id, sha256, fonte}}`.

    Prefere a coleção; antes de ela existir (dry-run da Fase 1) cai no parse
    dos mesmos PDFs, calculando o `gabarito_id` que o seeder vai gravar — de
    modo que o dry-run mostra exatamente o que a escrita vai produzir.
    """
    out = {}
    if "gabaritos_oficiais" in db.list_collection_names():
        for doc in db.gabaritos_oficiais.find({"vigente": True}):
            out[doc["prova"]["ano"]] = {
                "mapa": {e["numero"]: e for e in doc["entradas"]},
                "gabarito_id": doc["_id"],
                "sha256": doc["origem"]["sha256"],
                "fonte": "gabaritos_oficiais",
                "cobertura": doc["cobertura"],
            }
    if out:
        return out

    for pdf in sorted(pdf_dir.glob("*.pdf")):
        parsed = parse_pdf(pdf)
        prova = {"banca": "ENEM", **parsed["prova"]}
        out[parsed["prova"]["ano"]] = {
            "mapa": {e["numero"]: e for e in parsed["entradas"]},
            "gabarito_id": f"{chave_prova(prova)}-v1",
            "sha256": parsed["origem"]["sha256"],
            "fonte": "pdf_oficial_inep (coleção ainda não criada)",
            "cobertura": parsed["cobertura"],
        }
    return out


def numero_do_item(item_id: str, fallback) -> int | None:
    m = RE_QNUM.search(item_id or "")
    if m:
        return int(m.group(2))
    try:
        return int(fallback)
    except (TypeError, ValueError):
        return None


def planejar(doc: dict, gabaritos: dict, agora: str) -> dict | None:
    item_antes = doc.get("item") or {}
    item = copy.deepcopy(item_antes)
    questao = item.get("questao") or {}
    alternativas = questao.get("alternativas") or []

    item_id = item.get("item_id") or doc.get("item_id") or ""
    ano = (item.get("fonte") or {}).get("ano")
    numero = numero_do_item(item_id, doc.get("question_number"))

    gab = gabaritos.get(ano)
    entrada = (gab or {}).get("mapa", {}).get(numero)
    if entrada is None:
        return {"item_id": item_id, "ano": ano, "numero": numero,
                "acao": "sem_gabarito", "mudou": False}

    bruto = {a.get("letra"): a.get("correta") for a in alternativas}
    tipos = sorted({type(v).__name__ for v in bruto.values()})
    marcadas = [a.get("letra") for a in alternativas if a.get("correta") is True]
    # Leniente serve só para telemetria: é como as strings 'true' foram
    # marcadas pelo modelo, ainda que o backend nunca as tenha enxergado.
    marcadas_lenientes = [a.get("letra") for a in alternativas
                          if str(a.get("correta")).strip().lower() == "true"]
    modelo_marcou = (marcadas_lenientes[0] if len(marcadas_lenientes) == 1 else None)

    anulada = entrada["status"] == "anulada"
    oficial = entrada.get("gabarito")

    for a in alternativas:
        a["correta"] = False if anulada else bool(a.get("letra") == oficial)

    if "correta_modelo" not in item:
        item["correta_modelo"] = {
            "letra": modelo_marcou,
            "bruto": bruto,
            "tipo": "|".join(tipos),
            "capturado_em": agora,
        }

    item["gabarito_oficial"] = {
        "letra": oficial,
        "status": entrada["status"],
        "gabarito_id": gab["gabarito_id"],
        "sha256": gab["sha256"],
        "aplicado_em": item.get("gabarito_oficial", {}).get("aplicado_em", agora),
    }

    divergiu = (not anulada) and (modelo_marcou != oficial)
    if divergiu:
        prosa = RE_LETRA_EM_PROSA.search((item.get("qualidade") or {}).get("observacoes") or "")
        item["divergencia_gabarito"] = {
            "modelo_marcou": modelo_marcou,
            "oficial": oficial,
            "modelo_citou_em_observacoes": (
                next(g for g in prosa.groups() if g).upper() if prosa else None),
            "tipo_original": "|".join(tipos),
            "detectada_em": item.get("divergencia_gabarito", {}).get("detectada_em", agora),
        }

    # Duas noções de "errado", e elas não coincidem:
    #
    #   divergiu           o modelo apontou outra letra que não a oficial
    #   corrigido_efetivo  a resposta que o BACKEND enxerga muda
    #
    # 2023 Q94 separa as duas: o modelo acertou a letra ('A') e serializou
    # como a string 'true', que `register_answer` — testando `is True` — lê
    # como "nenhuma alternativa correta". Não é divergência de gabarito, mas é
    # uma das 60 questões que hoje respondem errado ao aluno.
    esperado_estrito = [] if anulada else [oficial]
    corrigido_efetivo = marcadas != esperado_estrito

    resposta_correta = None if anulada else oficial
    caminhos = diff_caminhos({"item": item_antes, "resposta_correta": doc.get("resposta_correta")},
                             {"item": item, "resposta_correta": resposta_correta})
    proibidos = [c for c in caminhos if not caminho_permitido(c)]

    return {
        "item_id": item_id, "ano": ano, "numero": numero, "doc_id": doc.get("id"),
        "acao": "anulada" if anulada else ("corrigir" if divergiu else "confirmar"),
        "oficial": oficial, "modelo_marcou": modelo_marcou,
        "marcadas_estritas": marcadas, "tipo_original": "|".join(tipos),
        "divergiu": divergiu, "anulada": anulada,
        "corrigido_efetivo": corrigido_efetivo,
        "item_novo": item, "resposta_correta": resposta_correta,
        "caminhos": caminhos, "caminhos_proibidos": proibidos,
        "mudou": bool(caminhos),
    }


# --------------------------------------------------------------------------
def validar_invariantes(planos: list[dict], gabaritos: dict, esperado: dict) -> list[str]:
    """Portões de segurança. Qualquer falha impede a escrita.

    Duas famílias, e confundi-las quebra a idempotência:

    * **de estado** (I3..I7) — descrevem como o corpus tem de ficar. Valem em
      toda execução, inclusive na segunda, quando não há nada a fazer.
    * **de pré-voo** (I1, I2) — descrevem o que se espera *encontrar* para
      corrigir. Só fazem sentido quando ainda há trabalho: exigi-las numa
      reexecução transformaria "nada a fazer" em erro, que é exatamente o
      oposto de idempotente.
    """
    falhas = []
    aplicaveis = [p for p in planos if p["acao"] != "sem_gabarito"]
    ha_trabalho = any(p["mudou"] for p in planos)

    proibidos = [(p["item_id"], p["caminhos_proibidos"]) for p in planos if p.get("caminhos_proibidos")]
    if proibidos:
        falhas.append(f"I7 caminhos fora da allowlist em {len(proibidos)} itens: {proibidos[:3]}")

    nao_bool = [p["item_id"] for p in aplicaveis
                if any(not isinstance(a.get("correta"), bool)
                       for a in p["item_novo"]["questao"]["alternativas"])]
    if nao_bool:
        falhas.append(f"I2 `correta` não booleana depois da derivação: {nao_bool}")

    if ha_trabalho:
        corrigidos = [p for p in aplicaveis if p["corrigido_efetivo"]]
        if len(corrigidos) != esperado["divergencias"]:
            falhas.append(f"I1 esperava {esperado['divergencias']} itens com a resposta efetiva "
                          f"corrigida, encontrou {len(corrigidos)}")
        convertidos = [p["item_id"] for p in aplicaveis if p["tipo_original"] != "bool"]
        if len(convertidos) != esperado["tipos_corrigidos"]:
            falhas.append(f"I2 esperava {esperado['tipos_corrigidos']} itens de tipo irregular, "
                          f"encontrou {len(convertidos)}: {convertidos}")

    for p in aplicaveis:
        n = sum(1 for a in p["item_novo"]["questao"]["alternativas"] if a.get("correta") is True)
        if p["anulada"] and n != 0:
            falhas.append(f"I4 item anulado {p['item_id']} com {n} alternativa(s) correta(s)")
        if not p["anulada"] and n != 1:
            falhas.append(f"I3 {p['item_id']} ficaria com {n} alternativas corretas")

    sem_modelo = [p["item_id"] for p in aplicaveis if "correta_modelo" not in p["item_novo"]]
    if sem_modelo:
        falhas.append(f"I6 correta_modelo ausente em {sem_modelo}")
    for p in aplicaveis:
        cm = p["item_novo"].get("correta_modelo") or {}
        if sorted(cm.get("bruto", {})) != ["A", "B", "C", "D", "E"]:
            falhas.append(f"I6 correta_modelo.bruto incompleto em {p['item_id']}")

    presentes = {(p["ano"], p["numero"]) for p in planos}
    for ano, alvo in esperado["lacunas"]:
        if (ano, alvo) in presentes:
            falhas.append(f"I5 {ano} Q{alvo} deveria permanecer ausente, mas há item planejado")
    inventados = [p["item_id"] for p in planos if p.get("acao") == "criado"]
    if inventados:
        falhas.append(f"I5 itens inventados: {inventados}")

    return falhas


def relatorio_dry_run(planos, gabaritos, esperado) -> None:
    por_acao = collections.Counter(p["acao"] for p in planos)
    print("=" * 78)
    print("FASE 1 — DRY-RUN · nenhuma escrita")
    print("=" * 78)
    for ano, g in sorted(gabaritos.items()):
        c = g["cobertura"]
        print(f"  gabarito {ano}: {g['gabarito_id']}  ({g['fonte']})")
        print(f"                faixa {c['faixa'][0]}-{c['faixa'][1]} · anuladas {c['anuladas']} · sha {g['sha256'][:16]}…")

    print(f"\n{'-'*78}\nCONTAGEM POR CADERNO\n{'-'*78}")
    print(f"  {'ano':>6} {'itens':>6} {'confirmar':>10} {'corrigir':>9} {'anulada':>8} "
          f"{'s/gabarito':>11} {'resp. efetiva muda':>19}")
    for ano in sorted({p["ano"] for p in planos}):
        sub = [p for p in planos if p["ano"] == ano]
        c = collections.Counter(p["acao"] for p in sub)
        ef = sum(1 for p in sub if p.get("corrigido_efetivo"))
        print(f"  {ano:>6} {len(sub):>6} {c['confirmar']:>10} {c['corrigir']:>9} "
              f"{c['anulada']:>8} {c['sem_gabarito']:>11} {ef:>19}")
    ef_total = sum(1 for p in planos if p.get("corrigido_efetivo"))
    print(f"  {'TOTAL':>6} {len(planos):>6} {por_acao['confirmar']:>10} {por_acao['corrigir']:>9} "
          f"{por_acao['anulada']:>8} {por_acao['sem_gabarito']:>11} {ef_total:>19}")

    corrigidos = [p for p in planos if p.get("corrigido_efetivo")]
    print(f"\n{'-'*78}\nDIVERGÊNCIAS ITEM A ITEM · correta_modelo → gabarito oficial "
          f"({len(corrigidos)} itens)\n{'-'*78}")
    print(f"  {'item':<32} {'backend lê':>10} {'modelo':>7} {'tipo':>14} {'oficial':>8} {'obs':>4}")
    for p in corrigidos:
        div = p["item_novo"].get("divergencia_gabarito") or {}
        lido = p["marcadas_estritas"][0] if len(p["marcadas_estritas"]) == 1 else (
            "nenhuma" if not p["marcadas_estritas"] else ",".join(p["marcadas_estritas"]))
        print(f"  {p['item_id']:<32} {lido:>10} {str(p['modelo_marcou']):>7} {p['tipo_original']:>14} "
              f"{str(p['oficial']):>8} {str(div.get('modelo_citou_em_observacoes') or '—'):>4}")

    anuladas = [p for p in planos if p["anulada"]]
    print(f"\n{'-'*78}\nANULADAS ({len(anuladas)})\n{'-'*78}")
    for p in anuladas:
        print(f"  {p['item_id']}  modelo marcava '{p['modelo_marcou']}' → 0 alternativas corretas, "
              f"resposta_correta=None")

    print(f"\n{'-'*78}\nLACUNAS · número no gabarito oficial sem item persistido\n{'-'*78}")
    presentes = collections.defaultdict(set)
    for p in planos:
        presentes[p["ano"]].add(p["numero"])
    for ano, g in sorted(gabaritos.items()):
        faltando = sorted(set(g["mapa"]) - presentes[ano])
        for n in faltando:
            e = g["mapa"][n]
            print(f"  {ano} Q{n:<4} status={e['status']:<8} gabarito={e['gabarito'] or '—'}  "
                  f"→ permanece ausente, NÃO será criado")
    sem_gab = [p for p in planos if p["acao"] == "sem_gabarito"]
    print(f"  itens persistidos sem entrada no gabarito: {len(sem_gab)}")

    print(f"\n{'-'*78}\nDIFF ESPERADO NOS 4 STORES\n{'-'*78}")
    tocados = [p for p in planos if p["mudou"]]
    campos = collections.Counter()
    for p in tocados:
        for c in p["caminhos"]:
            campos[RE_CAMINHO_CORRETA.sub("item.questao.alternativas[*].correta", c)] += 1
    for campo, n in sorted(campos.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>5}×  {campo}")
    print()
    print(f"  firestore://itens          {len(tocados):>4} docs · update({{'item', 'resposta_correta'}})")
    print(f"  mongo://pipelines          {len(tocados):>4} docs · $set item, resposta_correta")
    print(f"  mongo://questoes_master    {len(tocados):>4} docs · $set item, resposta_correta")
    print(f"  mongo://questoes_public    {len(tocados):>4} docs · $set questao.alternativas")
    print(f"\n  itens sem nenhuma mudança: {len(planos) - len(tocados)}")
    print(f"  item_hash alterado:        0  (intocado por decisão explícita)")


# --------------------------------------------------------------------------
def aplicar(planos, dbp, dba, fs, autor: str) -> dict:
    contagem = collections.Counter()
    tocados = [p for p in planos if p["mudou"]]

    # 1) Firestore `itens` — fonte da verdade de onde `run_firestore_sync`
    #    reconstrói os espelhos do aluno. Vai primeiro por isso.
    col = fs.collection("itens")
    for p in tocados:
        col.document(p["doc_id"]).update({
            "item": p["item_novo"],
            "resposta_correta": p["resposta_correta"],
        })
        contagem["firestore_itens"] += 1

    for p in tocados:
        r = dbp.pipelines.update_one(
            {"id": p["doc_id"]},
            {"$set": {"item": p["item_novo"], "resposta_correta": p["resposta_correta"]}},
        )
        contagem["pipelines"] += r.modified_count

    for p in tocados:
        r = dba.questoes_master.update_one(
            {"id": p["doc_id"]},
            {"$set": {"item": p["item_novo"], "resposta_correta": p["resposta_correta"]}},
        )
        contagem["questoes_master"] += r.modified_count

    for p in tocados:
        r = dba.questoes_public.update_one(
            {"item_id": p["item_id"]},
            {"$set": {"questao.alternativas": [
                {"letra": a.get("letra"), "texto": a.get("texto"), "correta": a.get("correta")}
                for a in p["item_novo"]["questao"]["alternativas"]
            ]}},
        )
        contagem["questoes_public"] += r.modified_count

    return dict(contagem)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf-dir", default=str(REPO / ".saneamento" / "gabaritos_inep"))
    ap.add_argument("--cred", default=str(DEFAULT_CRED))
    ap.add_argument("--autor", default="saneamento-2026-08-26")
    ap.add_argument("--out-dir", default=str(REPO / ".saneamento"))
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true")
    modo.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    from pymongo import MongoClient

    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    dbp, dba = cli["sapiens_pipeline"], cli["sapiens_aluno"]
    gabaritos = carregar_gabaritos(dbp, Path(args.pdf_dir))
    agora = datetime.now(timezone.utc).isoformat()

    esperado = {
        "divergencias": 60,        # 53 GAB-01 + 6 GAB-02 + 1 GAB-03
        "tipos_corrigidos": 3,     # 2 strings + 1 null
        "lacunas": [(2022, 175), (2023, 177)],
    }

    planos = [p for p in (planejar(d, gabaritos, agora) for d in dbp.pipelines.find({})) if p]
    planos.sort(key=lambda p: (p["ano"] or 0, p["numero"] or 0))

    if args.dry_run:
        relatorio_dry_run(planos, gabaritos, esperado)
        falhas = validar_invariantes(planos, gabaritos, esperado)
        print(f"\n{'='*78}\nINVARIANTES\n{'='*78}")
        if falhas:
            for f in falhas:
                print(f"  FALHA  {f}")
            print("\nA escrita seria RECUSADA.")
        else:
            print("  todos os invariantes verificados — a escrita seria permitida")
        out = Path(args.out_dir) / f"backfill_gabarito.plano.{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}.json"
        out.write_text(json.dumps(
            [{k: v for k, v in p.items() if k != "item_novo"} for p in planos],
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nplano completo: {out}\nNada foi escrito.")
        return 1 if falhas else 0

    falhas = validar_invariantes(planos, gabaritos, esperado)
    if falhas:
        for f in falhas:
            print(f"FALHA  {f}")
        print("\nEscrita ABORTADA pelos invariantes.")
        return 2

    fontes = {g["fonte"] for g in gabaritos.values()}
    if fontes != {"gabaritos_oficiais"}:
        print(f"FALHA  a escrita exige a coleção `gabaritos_oficiais` semeada; fonte atual: {fontes}")
        return 2

    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(args.cred))
    fs = firestore.client()

    if not any(p["mudou"] for p in planos):
        print("NADA A FAZER — os quatro stores já refletem o gabarito oficial.")
        print(f"  {len(planos)} itens verificados · 0 documentos escritos")
        return 0

    contagem = aplicar(planos, dbp, dba, fs, args.autor)
    print("ESCRITA CONCLUÍDA")
    for store, n in contagem.items():
        print(f"  {store:<20} {n:>4} documentos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
