#!/usr/bin/env python
"""Plano de retificação da série de behavior — SOMENTE LEITURA.

Não escreve nada, em lugar nenhum. Produz:

* o evento de retificação que *seria* gravado para cada evento afetado;
* o `skills_map` que resultaria da série corrigida, recalculado em memória;
* o diff contra o `skills_map` hoje gravado.

Os 249 eventos originais são imutáveis por contrato (behavior 1.1: cada evento
carrega `event_id`, `item_hash` e `ontology_version` do momento da resposta).
A correção acrescenta um evento de retificação que aponta para o original —
nunca edita nem apaga.

    .venv/bin/python ../scripts/plano_retificacao_behavior.py
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ALUNO = REPO / "aluno" / "backend"
MONGO_URL = os.environ.get("SANEAMENTO_MONGO_URL", "mongodb://127.0.0.1:27017")
DEFAULT_CRED = REPO / ".secrets" / "firebase-service-account.json"

sys.path.insert(0, str(ALUNO))

RE_QNUM = re.compile(r"-(\d{4})-[A-Z]+-Q(\d{3})")
MOTIVOS = {
    "gabarito_divergente": "o gabarito do banco apontava outra letra que a oficial do INEP",
    "gabarito_ilegivel": "`correta` não era booleano; o backend gravou acertou=null",
    "questao_anulada": "questão anulada pelo INEP — não há resposta certa a computar",
}


def event_id_retificacao(original: str, gabarito_id: str) -> str:
    """Id DETERMINÍSTICO da retificação.

    É o mecanismo que impede dupla retificação: gravar com
    `document(<este id>).set(...)` é idempotente por construção — reexecutar
    produz o mesmo id e sobrescreve com conteúdo idêntico, nunca um segundo
    evento. Depende do gabarito, então uma correção FUTURA de gabarito (v2)
    geraria uma retificação nova e distinta, como deve.
    """
    return hashlib.sha256(f"retificacao:{original}:{gabarito_id}".encode()).hexdigest()[:32]


def montar_retificacao(ev: dict, oficial: str | None, anulada: bool,
                       gabarito_id: str, motivo: str, agora: str) -> dict:
    resposta = ev.get("resposta") or {}
    escolhida = resposta.get("alternativa_escolhida")
    acertou_novo = None if anulada else (escolhida == oficial)
    original_id = ev.get("event_id")
    return {
        "event_id": event_id_retificacao(original_id, gabarito_id),
        "schema_version": "1.1",
        "status": "retificada",
        "student_id": ev.get("student_id"),
        "item_id": ev.get("item_id"),
        # `item_hash` e `ontology_version` são COPIADOS do evento original: o
        # contrato pede a versão contra a qual o item estava anotado no momento
        # da resposta, não a de agora. Uma retificação não reescreve o passado,
        # descreve-o corretamente.
        "item_hash": ev.get("item_hash"),
        "item_schema_version": ev.get("item_schema_version"),
        "ontology_version": ev.get("ontology_version"),
        "attempt_id": ev.get("attempt_id"),
        "contexto": ev.get("contexto"),
        "desempenho": ev.get("desempenho"),
        "resposta": {"alternativa_escolhida": escolhida, "acertou": acertou_novo},
        "timestamp": agora,
        "retificacao": {
            "retifica_event_id": original_id,
            "timestamp_original": ev.get("timestamp"),
            "motivo": motivo,
            "motivo_descricao": MOTIVOS[motivo],
            "acertou_anterior": resposta.get("acertou"),
            "acertou_corrigido": acertou_novo,
            "gabarito_oficial": oficial,
            "gabarito_id": gabarito_id,
            "origem": "saneamento-fase2",
            "aplicado_em": agora,
        },
    }


def agregar(eventos: list[dict], indice: dict, retificacoes: dict) -> dict:
    """Réplica em memória de `annotation_service._read_firestore_answered`.

    A única diferença: quando existe retificação para um evento, o `acertou`
    usado é o da retificação. O evento de retificação em si NÃO conta como
    resposta nova — senão o aluno apareceria tendo respondido duas vezes.
    """
    procs: set[str] = set()
    doms: set[str] = set()
    stats: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"respondidas": 0, "acertos": 0})
    respondidos = 0

    for ev in eventos:
        if ev.get("status") not in (None, "respondida"):
            continue
        chave = next((k for k in (ev.get("item_id"), ev.get("item_hash"))
                      if k and k in indice), None)
        item = indice.get(chave) if chave else None
        ec = (item or {}).get("estrutura_cognitiva")
        if not ec:
            continue
        respondidos += 1
        ret = retificacoes.get(ev.get("event_id"))
        acertou = bool((ret or ev).get("resposta", {}).get("acertou"))
        for p in ec.get("processos", []) or []:
            pid = p.get("id") if isinstance(p, dict) else p
            if pid:
                procs.add(pid)
        for dom in ec.get("dominios", []) or []:
            did = dom.get("id") if isinstance(dom, dict) else dom
            if did:
                doms.add(did)
                stats[did]["respondidas"] += 1
                if acertou:
                    stats[did]["acertos"] += 1
    return {"processos": procs, "dominios": doms,
            "domain_stats": dict(stats), "eventos_casados": respondidos}


def validar_invariantes(plano: list[dict], eventos: list[dict]) -> list[str]:
    """Barreiras automáticas. Qualquer falha impede a escrita."""
    falhas = []
    ids = [p["evento_retificacao"]["event_id"] for p in plano]
    if len(set(ids)) != len(ids):
        falhas.append("RET-01 event_id de retificação duplicado")

    originais = {e.get("event_id") for e in eventos}
    if set(ids) & originais:
        falhas.append("RET-02 event_id de retificação colide com evento original")

    refs = [p["evento_retificacao"]["retificacao"]["retifica_event_id"] for p in plano]
    if len(set(refs)) != len(refs):
        falhas.append("RET-03 mais de uma retificação para o mesmo evento original")
    if not set(refs) <= originais:
        falhas.append("RET-04 retificação aponta para evento que não existe")

    for p in plano:
        ev = p["evento_retificacao"]
        if not all(ev.get(k) for k in ("item_hash", "ontology_version", "student_id", "item_id")):
            falhas.append(f"RET-05 contrato behavior 1.1 incompleto em {ev['event_id']}")
        esperado = (None if p["gabarito_oficial"] is None
                    else p["alternativa_escolhida"] == p["gabarito_oficial"])
        if ev["resposta"]["acertou"] != esperado:
            falhas.append(f"RET-06 acertou corrigido inconsistente em {ev['event_id']}")
    return falhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cred", default=str(DEFAULT_CRED))
    ap.add_argument("--out-dir", default=str(REPO / ".saneamento"))
    ap.add_argument("--apply", action="store_true",
                    help="grava os eventos de retificação e recalcula skills_map")
    args = ap.parse_args()

    from pymongo import MongoClient
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(args.cred))
    fsdb = firestore.client()
    dbp = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)["sapiens_pipeline"]

    gab, gab_id = {}, {}
    for d in dbp.gabaritos_oficiais.find({"vigente": True}):
        ano = d["prova"]["ano"]
        gab[ano] = {e["numero"]: e for e in d["entradas"]}
        gab_id[ano] = d["_id"]

    itens = {}
    for snap in fsdb.collection("itens").stream():
        doc = snap.to_dict() or {}
        item = doc.get("item") or {}
        for chave in (item.get("item_id"), item.get("item_hash"), doc.get("item_hash")):
            if chave:
                itens[chave] = item

    alunos, eventos = {}, []
    for snap in fsdb.collection("students").stream():
        alunos[snap.id] = snap.to_dict() or {}
        for ev in fsdb.collection("students").document(snap.id).collection("behavior").stream():
            d = ev.to_dict() or {}
            d["_doc_id"] = ev.id
            d.setdefault("student_id", snap.id)
            eventos.append(d)

    agora = datetime.now(timezone.utc).isoformat()
    plano, ja_retificados = [], 0
    existentes = {e.get("retificacao", {}).get("retifica_event_id")
                  for e in eventos if e.get("status") == "retificada"}

    for ev in eventos:
        if ev.get("status") == "retificada":
            continue
        m = RE_QNUM.search(ev.get("item_id") or "")
        if not m:
            continue
        ano, numero = int(m.group(1)), int(m.group(2))
        entrada = gab.get(ano, {}).get(numero)
        if entrada is None:
            continue
        anulada = entrada["status"] == "anulada"
        oficial = entrada.get("gabarito")
        resposta = ev.get("resposta") or {}
        escolhida, gravado = resposta.get("alternativa_escolhida"), resposta.get("acertou")
        correto = None if anulada else (escolhida == oficial)
        if gravado == correto:
            continue
        if ev.get("event_id") in existentes:
            ja_retificados += 1
            continue
        motivo = ("questao_anulada" if anulada else
                  "gabarito_ilegivel" if gravado is None else "gabarito_divergente")
        plano.append({
            "student_id": ev.get("student_id"),
            "event_id_original": ev.get("event_id"),
            "item_id": ev.get("item_id"),
            "item_hash": ev.get("item_hash"),
            "alternativa_escolhida": escolhida,
            "acertou_gravado": gravado,
            "gabarito_oficial": oficial if not anulada else None,
            "acertou_correto": correto,
            "motivo": motivo,
            "timestamp_original": ev.get("timestamp"),
            "evento_retificacao": montar_retificacao(
                ev, oficial, anulada, gab_id[ano], motivo, agora),
        })

    retificacoes = {p["event_id_original"]: p["evento_retificacao"] for p in plano}

    # --- skills_map antes x depois ---------------------------------------
    from cosmetic_skills_map import compute_hexagon, compute_feedback
    from cognitive_ontology import build_ontology_tree
    import firestore_service as fs

    por_aluno = collections.defaultdict(list)
    for ev in eventos:
        por_aluno[ev.get("student_id")].append(ev)

    diffs = []
    for uid in sorted({p["student_id"] for p in plano}):
        evs = por_aluno[uid]
        antes = agregar(evs, itens, {})
        depois = agregar(evs, itens, retificacoes)
        rounds = fs.list_sparks_rounds(uid, limit=200)
        hex_antes = compute_hexagon(build_ontology_tree(antes["processos"]))
        hex_depois = compute_hexagon(build_ontology_tree(depois["processos"]))
        fb_antes = compute_feedback(rounds, antes["domain_stats"])
        fb_depois = compute_feedback(rounds, depois["domain_stats"])
        gravado = fs.read_skills_map(uid) or {}
        diffs.append({
            "student_id": uid,
            "eventos_retificados": sum(1 for p in plano if p["student_id"] == uid),
            "hexagon_muda": hex_antes != hex_depois,
            "hexagon_gravado": gravado.get("hexagon"),
            "hexagon_recalculado": hex_depois,
            "feedback_muda": fb_antes != fb_depois,
            "feedback_antes": fb_antes,
            "feedback_depois": fb_depois,
            "domain_stats_antes": antes["domain_stats"],
            "domain_stats_depois": depois["domain_stats"],
            "tem_skills_map_gravado": bool(gravado.get("hexagon")),
        })

    relatorio = {
        "gerado_em": agora,
        "gerado_por": "plano_retificacao_behavior.py",
        "somente_leitura": True,
        "eventos_lidos": len(eventos),
        "eventos_a_retificar": len(plano),
        "eventos_ja_retificados": ja_retificados,
        "alunos_afetados": sorted({p["student_id"] for p in plano}),
        "por_motivo": dict(collections.Counter(p["motivo"] for p in plano)),
        "plano": plano,
        "skills_map_diff": diffs,
    }
    out = Path(args.out_dir) / f"plano_retificacao.{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}.json"
    out.write_text(json.dumps(relatorio, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    # ---------------- relatório de tela ----------------
    print("=" * 92)
    print("PLANO DE RETIFICAÇÃO DE BEHAVIOR — somente leitura, nada gravado")
    print("=" * 92)
    print(f"  eventos lidos ............ {len(eventos)}")
    print(f"  a retificar .............. {len(plano)}")
    print(f"  já retificados ........... {ja_retificados}")
    print(f"  alunos afetados .......... {len(relatorio['alunos_afetados'])}")
    print(f"  por motivo ............... {relatorio['por_motivo']}")

    print(f"\n{'-'*92}\nDIFF COMPLETO DOS EVENTOS\n{'-'*92}")
    print(f"  {'aluno':<20} {'item':<30} {'esc':>3} {'grav':>5} {'ofic':>5} {'correto':>8}  motivo")
    for p in sorted(plano, key=lambda x: (x["student_id"], x["item_id"])):
        print(f"  {p['student_id']:<20} {p['item_id']:<30} {str(p['alternativa_escolhida']):>3} "
              f"{str(p['acertou_gravado']):>5} {str(p['gabarito_oficial']):>5} "
              f"{str(p['acertou_correto']):>8}  {p['motivo']}")

    print(f"\n{'-'*92}\nDIFF DE skills_map\n{'-'*92}")
    for d in diffs:
        print(f"\n  {d['student_id']}  ({d['eventos_retificados']} eventos retificados)")
        print(f"    hexagon muda ....... {d['hexagon_muda']}")
        print(f"    feedback muda ...... {d['feedback_muda']}")
        if d["feedback_muda"]:
            fa = {p['hub']: p['accuracy'] for p in (d['feedback_antes'].get('pontos_fortes') or [])}
            fd = {p['hub']: p['accuracy'] for p in (d['feedback_depois'].get('pontos_fortes') or [])}
            for hub in sorted(set(fa) | set(fd)):
                if fa.get(hub) != fd.get(hub):
                    print(f"      hub {hub}: acurácia {fa.get(hub)}% -> {fd.get(hub)}%")
        for did in sorted(set(d["domain_stats_antes"]) | set(d["domain_stats_depois"])):
            a = d["domain_stats_antes"].get(did, {})
            b = d["domain_stats_depois"].get(did, {})
            if a.get("acertos") != b.get("acertos"):
                print(f"      {did}: acertos {a.get('acertos')}/{a.get('respondidas')} "
                      f"-> {b.get('acertos')}/{b.get('respondidas')}")

    print(f"\n{'-'*92}\nFORMATO DO EVENTO DE RETIFICAÇÃO\n{'-'*92}")
    if plano:
        print(json.dumps(plano[0]["evento_retificacao"], ensure_ascii=False, indent=1, default=str))

    print(f"\nplano completo: {out}")
    if not args.apply:
        print("Nada foi gravado.")
        return 0

    falhas = validar_invariantes(plano, eventos)
    if falhas:
        for f in falhas:
            print(f"  FALHA  {f}")
        print("\nEscrita ABORTADA pelos invariantes.")
        return 2
    if not plano:
        print("\nNADA A FAZER — a série já está retificada.")
        return 0

    print(f"\n{'-'*92}\nESCRITA\n{'-'*92}")
    gravados = 0
    for p in plano:
        ev = p["evento_retificacao"]
        # `.set()` com id determinístico: reexecutar sobrescreve o MESMO
        # documento com conteúdo idêntico, nunca cria um segundo.
        (fsdb.collection("students").document(p["student_id"])
             .collection("behavior").document(ev["event_id"]).set(ev))
        gravados += 1
    print(f"  eventos de retificação gravados .. {gravados}")

    # `skills_map` só é reescrito para quem JÁ tem um gravado — para os demais
    # o mapa correto nasce na próxima geração, e escrever agora criaria um
    # snapshot que o aluno nunca pediu.
    import firestore_service as fs2
    recalculados = 0
    for d in diffs:
        if not d["tem_skills_map_gravado"]:
            continue
        fs2.write_skills_map(d["student_id"], d["hexagon_recalculado"], d["feedback_depois"])
        recalculados += 1
        print(f"  skills_map recalculado ........... {d['student_id']}")
    print(f"  skills_map reescritos ............ {recalculados}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
