#!/usr/bin/env python
"""Auditor do corpus de questões — SOMENTE LEITURA, sem LLM, sem rede.

Emite um boletim por item com semáforo:

    BLOQUEADO  dano ao aluno agora — gabarito invertido, enunciado vazio,
               alternativa vazia, questão anulada em circulação. Não deve
               circular até correção.
    DEGRADADO  jogável mas incompleto — figura faltando, recorte sujo,
               placeholder no texto, hash divergente.
    OK

O gabarito oficial vem, por ordem de preferência, da coleção
`sapiens_pipeline.gabaritos_oficiais` (a partir da Fase 1) ou do parse direto
dos PDFs do INEP em `--gabaritos-dir` (Fase 0, antes de a coleção existir).
Nenhuma fonte secundária é aceita nos dois caminhos.

    .venv/bin/python ../scripts/audit_corpus.py --out-dir ../../.saneamento
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "pipeline" / "backend"
STORAGE = BACKEND / "_storage" / "sapiens-cognitive"
DEFAULT_CRED = REPO / ".secrets" / "firebase-service-account.json"
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gabarito_inep import como_mapa, parse_pdf  # noqa: E402

BLOQUEADO, DEGRADADO, OK = "BLOQUEADO", "DEGRADADO", "OK"

# Severidade por código de achado. Quem decide se um item sai de circulação é
# esta tabela — não o texto da mensagem.
SEVERIDADE = {
    "GAB-01": BLOQUEADO,  # correta diverge do gabarito oficial
    "GAB-02": BLOQUEADO,  # nenhuma ou mais de uma alternativa correta
    "GAB-03": BLOQUEADO,  # questão anulada pelo INEP, em circulação
    "GAB-04": BLOQUEADO,  # `correta` não é booleano (backend testa `is True`)
    "GAB-05": DEGRADADO,  # item sem gabarito oficial disponível
    "GAB-06": DEGRADADO,  # letra citada em observacoes diverge da marcada
    "EST-01": BLOQUEADO,  # enunciado vazio
    "EST-02": BLOQUEADO,  # alternativa com texto vazio
    "EST-03": BLOQUEADO,  # letras não são exatamente A-E, únicas
    "EST-04": BLOQUEADO,  # número de alternativas diferente de 5
    "EST-05": DEGRADADO,  # placeholder fabricado no texto
    "ARQ-01": DEGRADADO,  # `arquivo` fora do formato de blob
    "ARQ-02": DEGRADADO,  # blob referenciado não existe no storage
    "ARQ-03": DEGRADADO,  # asset persistido sem caso válido no manifesto
    "ARQ-04": DEGRADADO,  # recurso declarado sem visual_asset entregue
    "GOV-01": DEGRADADO,  # revisado=true sem registro de revisão humana
    "GOV-02": BLOQUEADO,  # apto_para_camada_de_crenca=true com achado vermelho
    "GOV-03": DEGRADADO,  # item_hash de topo diverge do interno
    "SYN-01": BLOQUEADO,  # stores divergem entre si
}

RE_BLOB = re.compile(r"^[0-9a-f]{64}\.(png|webp|jpg|jpeg)$")
RE_QNUM = re.compile(r"-(\d{4})-[A-Z]+-Q(\d{3})")
RE_PLACEHOLDER = re.compile(
    r"\[(Gráfico|Grafico|Tabela|Figura|Imagem|Quadro|Ilustra|Esquema|Diagrama|"
    r"Mapa|Foto|Charge|Tirinha|Texto)[^\]]{0,160}\]",
    re.IGNORECASE,
)
RE_LETRA_EM_PROSA = re.compile(
    r"alternativa\s+(?:correta\s+)?(?:é\s+)?\(?([A-E])\)?"
    r"|correta\s*(?:é|:)\s*\(?([A-E])\)?"
    r"|\(([A-E])\)\s*(?:é|resulta|está)\s*(?:a\s*)?correta",
    re.IGNORECASE,
)
LETRAS = ["A", "B", "C", "D", "E"]


# --------------------------------------------------------------------------
# leitura das fontes
# --------------------------------------------------------------------------
def carregar_gabaritos(db_pipeline, pdf_dir: Path | None) -> tuple[dict, dict]:
    """`({ano: {numero: letra|ANULADA}}, procedência)`."""
    if "gabaritos_oficiais" in db_pipeline.list_collection_names():
        mapas, proc = {}, {}
        for doc in db_pipeline.gabaritos_oficiais.find({}):
            ano = (doc.get("prova") or {}).get("ano")
            mapas[ano] = {
                e["numero"]: (e.get("gabarito") or "ANULADA")
                for e in doc.get("entradas", [])
            }
            proc[ano] = {"fonte": "gabaritos_oficiais", **(doc.get("origem") or {})}
        if mapas:
            return mapas, proc

    if not pdf_dir or not pdf_dir.is_dir():
        raise SystemExit(
            "sem gabarito: a coleção `gabaritos_oficiais` não existe e "
            "--gabaritos-dir não aponta para um diretório."
        )
    mapas, proc = {}, {}
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        parsed = parse_pdf(pdf)
        ano = parsed["prova"]["ano"]
        mapas[ano] = como_mapa(parsed)
        proc[ano] = {"fonte": "pdf_oficial_inep", **parsed["origem"]}
    return mapas, proc


def numero_do_item(item_id: str, fallback) -> int | None:
    m = RE_QNUM.search(item_id or "")
    if m:
        return int(m.group(2))
    try:
        return int(fallback)
    except (TypeError, ValueError):
        return None


def letra_correta(alternativas: list[dict]) -> tuple[list[str], str]:
    """Letras marcadas segundo a MESMA regra do backend (`is True`), e o tipo.

    `register_answer` usa `a.get("correta") is True`. Reproduzir a comparação
    estrita aqui é o que faz a auditoria enxergar os itens em que `correta` é
    a string 'true' — que o backend não consegue ler e grava `acertou: null`.
    """
    tipos = sorted({type(a.get("correta")).__name__ for a in alternativas})
    return [a.get("letra") for a in alternativas if a.get("correta") is True], "|".join(tipos)


# --------------------------------------------------------------------------
# checagens por item
# --------------------------------------------------------------------------
def auditar_item(doc, ctx) -> dict:
    item = doc.get("item") or {}
    questao = item.get("questao") or {}
    fonte = item.get("fonte") or {}
    qualidade = item.get("qualidade") or {}
    alternativas = questao.get("alternativas") or []

    item_id = item.get("item_id") or doc.get("item_id") or ""
    ano = fonte.get("ano")
    numero = numero_do_item(item_id, doc.get("question_number"))

    achados: list[dict] = []

    def achar(codigo, detalhe, **extra):
        achados.append({"codigo": codigo, "severidade": SEVERIDADE[codigo],
                        "detalhe": detalhe, **extra})

    # ---- gabarito ---------------------------------------------------------
    marcadas, tipos = letra_correta(alternativas)
    oficial = (ctx["gabaritos"].get(ano) or {}).get(numero)

    if tipos not in ("bool", ""):
        achar("GAB-04", f"`correta` com tipo {tipos}; o backend testa `is True`", tipos=tipos)

    if oficial is None:
        achar("GAB-05", f"sem gabarito oficial para {ano} Q{numero}")
    elif oficial == "ANULADA":
        achar("GAB-03", f"anulada pelo INEP e em circulação marcando '{marcadas[0] if marcadas else '—'}'")
    elif len(marcadas) != 1:
        achar("GAB-02", f"{len(marcadas)} alternativas com `correta is True` (oficial: {oficial})",
              oficial=oficial, marcadas=marcadas)
    elif marcadas[0] != oficial:
        achar("GAB-01", f"oficial {oficial}, banco {marcadas[0]}",
              oficial=oficial, banco=marcadas[0])

    prosa = RE_LETRA_EM_PROSA.search(qualidade.get("observacoes") or "")
    if prosa:
        citada = next(g for g in prosa.groups() if g).upper()
        if len(marcadas) == 1 and citada != marcadas[0]:
            achar("GAB-06", f"observacoes cita '{citada}', `correta` marca '{marcadas[0]}'"
                            + (f" (oficial {oficial})" if oficial else ""), citada=citada)

    # ---- estrutura --------------------------------------------------------
    if not (questao.get("enunciado") or "").strip():
        achar("EST-01", "enunciado vazio")

    vazias = [a.get("letra") for a in alternativas if not (a.get("texto") or "").strip()]
    if vazias:
        achar("EST-02", f"alternativa(s) sem texto: {', '.join(str(v) for v in vazias)}", letras=vazias)

    letras = [a.get("letra") for a in alternativas]
    if len(alternativas) != 5:
        achar("EST-04", f"{len(alternativas)} alternativas")
    elif sorted(letras) != LETRAS:
        achar("EST-03", f"letras {letras}")

    texto_todo = " ".join(
        [questao.get("enunciado") or ""] + [(a.get("texto") or "") for a in alternativas]
    )
    ph = RE_PLACEHOLDER.search(texto_todo)
    if ph:
        achar("EST-05", f"placeholder fabricado no texto: {ph.group(0)[:70]}")

    # ---- assets -----------------------------------------------------------
    recursos = questao.get("recursos") or {}
    declarados = 0
    for chave, lista in (recursos.items() if isinstance(recursos, dict) else []):
        if not isinstance(lista, list):
            continue
        for rec in lista:
            if not isinstance(rec, dict):
                continue
            declarados += 1
            arquivo = rec.get("arquivo") or ""
            if arquivo and not RE_BLOB.match(arquivo):
                achar("ARQ-01", f"{chave}/{rec.get('id') or '?'} aponta para '{arquivo}'",
                      arquivo=arquivo)

    assets = questao.get("visual_assets") or []
    for asset in assets:
        src = asset.get("src") or ""
        if src and src not in ctx["blobs"]:
            achar("ARQ-02", f"blob ausente no storage: {src[:16]}…", src=src)
        # Assets `HUM-*` (recorte manual humano ou extração verificada do PDF
        # oficial, ver `ingerir_recortes_manuais_2022mt.py`) não vêm do
        # extrator automático e nunca terão caso no manifesto dele — isso não
        # é ausência de evidência, é uma FONTE de evidência diferente e mais
        # forte. `verificacao.estado == "verificada_manual"` já é a prova.
        verificado_manual = (asset.get("verificacao") or {}).get("estado") == "verificada_manual"
        caso = ctx["casos"].get((item_id, asset.get("asset_id")))
        if verificado_manual:
            pass
        elif caso is None:
            achar("ARQ-03", f"asset '{asset.get('asset_id')}' sem caso correspondente no manifesto")
        elif caso.get("needs_manual_review"):
            achar("ARQ-03", f"asset '{asset.get('asset_id')}' persistido com caso NEEDS_MANUAL_REVIEW")

    nao_formula = [a for a in assets if a.get("type") != "formula"]
    formulas = len((recursos or {}).get("formulas") or [])
    if declarados - formulas > 0 and not nao_formula:
        achar("ARQ-04", f"{declarados - formulas} recurso(s) visual(is) declarado(s), 0 entregue(s)")

    # ---- governança -------------------------------------------------------
    apto = qualidade.get("apto_para_camada_de_crenca")
    apto_valor = apto.get("valor") if isinstance(apto, dict) else apto
    if qualidade.get("revisado") and item_id not in ctx["revisoes_humanas"]:
        achar("GOV-01", "revisado=true sem registro de revisão humana")

    if doc.get("item_hash") and item.get("item_hash") and doc["item_hash"] != item["item_hash"]:
        achar("GOV-03", "item_hash de topo diverge de item.item_hash")

    # ---- consistência entre stores ---------------------------------------
    for nome, espelho in ctx["espelhos"].items():
        alt_espelho = espelho.get(item_id)
        if alt_espelho is None:
            achar("SYN-01", f"ausente em {nome}")
        elif alt_espelho != marcadas:
            achar("SYN-01", f"{nome} marca {alt_espelho}, pipeline marca {marcadas}")

    # GOV-02 depende do resultado das demais: avaliado por último.
    if apto_valor is True and any(a["severidade"] == BLOQUEADO for a in achados):
        achar("GOV-02", "apto_para_camada_de_crenca=true com achado BLOQUEADO aberto")

    severidade = OK
    if any(a["severidade"] == BLOQUEADO for a in achados):
        severidade = BLOQUEADO
    elif achados:
        severidade = DEGRADADO

    return {
        "item_id": item_id,
        "ano": ano,
        "numero": numero,
        "book_id": doc.get("book_id"),
        "semaforo": severidade,
        "gabarito_oficial": oficial,
        "correta_banco": marcadas[0] if len(marcadas) == 1 else marcadas,
        "tipo_correta": tipos,
        "revisado": qualidade.get("revisado"),
        "apto_para_camada_de_crenca": apto_valor,
        "achados": achados,
    }


# --------------------------------------------------------------------------
# checagens de corpus
# --------------------------------------------------------------------------
def auditar_cobertura(db_pipeline, itens) -> list[dict]:
    persistidos = collections.defaultdict(set)
    for it in itens:
        persistidos[it["book_id"]].add(it["numero"])

    out = []
    for book in db_pipeline.books.find({}, {"id": 1, "ano": 1, "manifest": 1}):
        bid = book.get("id")
        if bid not in persistidos:
            continue
        declarados = {int(m["numero"]) for m in (book.get("manifest") or []) if m.get("numero")}
        faltando = sorted(declarados - persistidos[bid])
        out.append({
            "book_id": bid, "ano": book.get("ano"),
            "declarados": len(declarados), "persistidos": len(persistidos[bid]),
            "faltando": faltando,
        })
    return out


def auditar_behavior(fs, itens) -> dict:
    por_item = {i["item_id"]: i for i in itens}
    eventos, invertidos, nulos = 0, [], 0
    for aluno in fs.collection("students").stream():
        for ev in fs.collection("students").document(aluno.id).collection("behavior").stream():
            d = ev.to_dict()
            eventos += 1
            item = por_item.get(d.get("item_id"))
            if not item:
                continue
            resposta = d.get("resposta") or {}
            escolhida, gravado = resposta.get("alternativa_escolhida"), resposta.get("acertou")
            if gravado is None:
                nulos += 1
                continue
            oficial = item.get("gabarito_oficial")
            if oficial in (None, "ANULADA"):
                continue
            if (escolhida == oficial) != gravado:
                invertidos.append({
                    "student_id": aluno.id, "event_id": d.get("event_id"),
                    "item_id": d.get("item_id"), "escolhida": escolhida,
                    "acertou_gravado": gravado, "acertou_correto": escolhida == oficial,
                    "oficial": oficial, "timestamp": d.get("timestamp"),
                })
    return {
        "eventos_totais": eventos,
        "eventos_invertidos": len(invertidos),
        "falsos_erros": sum(1 for e in invertidos if e["acertou_correto"]),
        "falsos_acertos": sum(1 for e in invertidos if not e["acertou_correto"]),
        "eventos_acertou_null": nulos,
        "alunos_afetados": sorted({e["student_id"] for e in invertidos}),
        "detalhe": invertidos,
    }


# --------------------------------------------------------------------------
def montar_markdown(rel: dict) -> str:
    r = rel["resumo"]
    L = [
        "# Auditoria do corpus — boletim por item",
        "",
        f"**Gerado:** {rel['gerado_em']}  ",
        f"**Modo:** somente leitura, sem LLM  ",
        f"**Gabarito:** {', '.join(sorted({p['fonte'] for p in rel['procedencia'].values()}))}",
        "",
        "## Resumo",
        "",
        "| Semáforo | Itens |",
        "|---|---:|",
        f"| BLOQUEADO | {r['BLOQUEADO']} |",
        f"| DEGRADADO | {r['DEGRADADO']} |",
        f"| OK | {r['OK']} |",
        f"| **total** | **{r['total']}** |",
        "",
        "## Achados por código",
        "",
        "| Código | Severidade | Itens |",
        "|---|---|---:|",
    ]
    for codigo, n in sorted(rel["por_codigo"].items()):
        L.append(f"| {codigo} | {SEVERIDADE[codigo]} | {n} |")

    L += ["", "## Cobertura por caderno", "",
          "| Caderno | Declarados | Persistidos | Faltando |", "|---|---:|---:|---|"]
    for c in rel["cobertura"]:
        L.append(f"| {c['ano']} | {c['declarados']} | {c['persistidos']} | "
                 f"{', '.join(str(x) for x in c['faltando']) or '—'} |")

    if rel.get("behavior"):
        b = rel["behavior"]
        L += ["", "## Contaminação já ocorrida", "",
              f"- eventos lidos: **{b['eventos_totais']}**",
              f"- `acertou` invertido: **{b['eventos_invertidos']}** "
              f"({b['falsos_erros']} falsos-erros, {b['falsos_acertos']} falsos-acertos)",
              f"- `acertou: null`: **{b['eventos_acertou_null']}**",
              f"- alunos afetados: **{len(b['alunos_afetados'])}**"]

    L += ["", "## Itens BLOQUEADOS", "", "| Item | Oficial | Banco | Achados |", "|---|---|---|---|"]
    for it in rel["itens"]:
        if it["semaforo"] != BLOQUEADO:
            continue
        codigos = ", ".join(sorted({a["codigo"] for a in it["achados"]
                                    if a["severidade"] == BLOQUEADO}))
        L.append(f"| {it['ano']} Q{it['numero']} | {it['gabarito_oficial']} | "
                 f"{it['correta_banco']} | {codigos} |")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gabaritos-dir", default=str(REPO / ".saneamento" / "gabaritos_inep"))
    ap.add_argument("--out-dir", default=str(REPO / ".saneamento"))
    ap.add_argument("--cred", default=str(DEFAULT_CRED))
    ap.add_argument("--skip-firestore", action="store_true")
    args = ap.parse_args()

    from pymongo import MongoClient

    mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    dbp, dba = mongo["sapiens_pipeline"], mongo["sapiens_aluno"]

    gabaritos, procedencia = carregar_gabaritos(dbp, Path(args.gabaritos_dir))

    blobs = {p.name for p in (STORAGE / "blobs").glob("*")} if (STORAGE / "blobs").is_dir() else set()

    casos = {}
    manifesto_path = STORAGE / "visual_audit" / "manifest.json"
    if manifesto_path.is_file():
        for caso in json.loads(manifesto_path.read_text())["cases"]:
            casos[(caso["item_id"], caso.get("asset_id"))] = caso

    revisoes = set()
    if "revisoes_humanas" in dbp.list_collection_names():
        revisoes = {d["item_id"] for d in dbp.revisoes_humanas.find({}, {"item_id": 1})}

    espelhos: dict[str, dict] = {}
    espelhos["questoes_master"] = {
        d["item_id"]: [a.get("letra") for a in
                       (((d.get("item") or {}).get("questao") or {}).get("alternativas") or [])
                       if a.get("correta") is True]
        for d in dba.questoes_master.find({}, {"item_id": 1, "item.questao.alternativas": 1})
    }
    espelhos["questoes_public"] = {
        d["item_id"]: [a.get("letra") for a in
                       ((d.get("questao") or {}).get("alternativas") or [])
                       if a.get("correta") is True]
        for d in dba.questoes_public.find({}, {"item_id": 1, "questao.alternativas": 1})
    }

    fs = None
    if not args.skip_firestore:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(args.cred))
        fs = firestore.client()
        espelhos["firestore_itens"] = {
            (d := snap.to_dict()).get("item_id"):
                [a.get("letra") for a in
                 (((d.get("item") or {}).get("questao") or {}).get("alternativas") or [])
                 if a.get("correta") is True]
            for snap in fs.collection("itens").stream()
        }

    ctx = {"gabaritos": gabaritos, "blobs": blobs, "casos": casos,
           "revisoes_humanas": revisoes, "espelhos": espelhos}

    itens = [auditar_item(doc, ctx) for doc in dbp.pipelines.find({})]
    itens.sort(key=lambda i: (i["ano"] or 0, i["numero"] or 0))

    resumo = collections.Counter(i["semaforo"] for i in itens)
    por_codigo = collections.Counter(a["codigo"] for i in itens for a in i["achados"])

    relatorio = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "gerado_por": "audit_corpus.py",
        "somente_leitura": True,
        "procedencia": procedencia,
        "resumo": {**{k: resumo.get(k, 0) for k in (BLOQUEADO, DEGRADADO, OK)},
                   "total": len(itens)},
        "por_codigo": dict(por_codigo),
        "cobertura": auditar_cobertura(dbp, itens),
        # Órfão só faz sentido para blob de imagem: o storage guarda também os
        # PDFs de caderno e um sidecar `.content-type` por objeto, e nenhum dos
        # dois é referenciado por `visual_assets` nem deveria ser.
        "blobs_orfaos": sorted(
            {b for b in blobs if RE_BLOB.match(b)}
            - {a.get("src") for doc in dbp.pipelines.find({}, {"item.questao.visual_assets": 1})
               for a in (((doc.get("item") or {}).get("questao") or {}).get("visual_assets") or [])}
        ),
        "behavior": auditar_behavior(fs, itens) if fs else None,
        "itens": itens,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    json_path = out_dir / f"audit_corpus.{stamp}.json"
    md_path = out_dir / f"audit_corpus.{stamp}.md"
    json_path.write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
    md_path.write_text(montar_markdown(relatorio), encoding="utf-8")

    # Lista de cerco consumida por `aluno/backend/circulacao.py`. Caminho fixo
    # (sem carimbo de hora) porque é o arquivo que a variável de ambiente
    # aponta: reexecutar a auditoria atualiza o cerco no lugar.
    bloqueados_path = out_dir / "bloqueados.json"
    bloqueados_path.write_text(json.dumps({
        "gerado_em": relatorio["gerado_em"],
        "origem": json_path.name,
        "criterio": "semaforo == BLOQUEADO em audit_corpus.py",
        "total": sum(1 for i in itens if i["semaforo"] == BLOQUEADO),
        "item_ids": [i["item_id"] for i in itens if i["semaforo"] == BLOQUEADO],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    r = relatorio["resumo"]
    print(f"BLOQUEADO {r[BLOQUEADO]}   DEGRADADO {r[DEGRADADO]}   OK {r[OK]}   total {r['total']}")
    for codigo, n in sorted(por_codigo.items()):
        print(f"  {codigo}  {SEVERIDADE[codigo]:<10} {n:>4}")
    print(f"\n{json_path}\n{md_path}\n{bloqueados_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
