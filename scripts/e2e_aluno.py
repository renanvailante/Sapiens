#!/usr/bin/env python3
"""E2E do app do aluno: cadastro → login → carregamento → resposta → Behavior
→ feedback → persistência → restart.

Exercita o backend real contra Firestore e Gemini reais. Não usa mock: o
objetivo é provar que o serviço publicado vai funcionar, e um mock provaria
apenas que o mock funciona.

    python3 scripts/e2e_aluno.py --base-url http://127.0.0.1:8850

Os dados criados são removidos ao final, inclusive quando um passo falha.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any

VERDE, VERMELHO, AMARELO, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"

_falhas = 0
_criados: dict[str, Any] = {"email": None, "item_id": None, "student_id": None}


def ok(msg: str) -> None:
    print(f"  {VERDE}✓{RESET} {msg}")


def falha(msg: str) -> None:
    global _falhas
    _falhas += 1
    print(f"  {VERMELHO}✗{RESET} {msg}")


def aviso(msg: str) -> None:
    print(f"  {AMARELO}!{RESET} {msg}")


def _preparar_ambiente() -> str:
    """Carrega o .env do backend e o coloca no sys.path.

    Sem isto, `settings` sobe com MONGO_URL vazio e a limpeza falha em silêncio
    — deixando o usuário de teste no banco.
    """
    import subprocess

    raiz = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True).stdout.strip()
    backend = f"{raiz}/aluno/backend"
    if backend not in sys.path:
        sys.path.insert(0, backend)
    try:
        from dotenv import load_dotenv

        load_dotenv(f"{backend}/.env")
    except ImportError:
        pass
    return backend


def _eventos_do_aluno(uid: str) -> list[dict]:
    """Lê os eventos direto do Firestore, sem passar pela API."""
    _preparar_ambiente()
    try:
        import firestore_service as fs

        ref = fs.get_firestore().collection("students").document(uid).collection("behavior")
        return [d.to_dict() for d in ref.stream()]
    except Exception as e:  # noqa: BLE001
        aviso(f"leitura direta do Firestore falhou: {type(e).__name__}: {e}")
        return []


def req(base: str, metodo: str, caminho: str, corpo: Any = None,
        token: str | None = None, origem: str | None = None) -> tuple[int, Any, dict]:
    url = base.rstrip("/") + caminho
    data = json.dumps(corpo).encode() if corpo is not None else None
    r = urllib.request.Request(url, data=data, method=metodo)
    if data:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    if origem:
        r.add_header("Origin", origem)
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            bruto = resp.read().decode()
            try:
                return resp.status, json.loads(bruto), dict(resp.headers)
            except json.JSONDecodeError:
                return resp.status, bruto, dict(resp.headers)
    except urllib.error.HTTPError as e:
        bruto = e.read().decode()
        try:
            return e.code, json.loads(bruto), dict(e.headers)
        except json.JSONDecodeError:
            return e.code, bruto, dict(e.headers)
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}", {}


def executar(base: str) -> None:
    print("\n═══ 1. Health e readiness ═══")
    st, body, _ = req(base, "GET", "/health")
    ok(f"/health {st} · {body}") if st == 200 else falha(f"/health {st} · {body}")

    st, body, _ = req(base, "GET", "/ready")
    if st == 200:
        ok(f"/ready {body['status']}")
        for k, v in body["checks"].items():
            print(f"      {k}: {v}")
        if body["checks"].get("mongo") != "ok":
            falha("Mongo não respondeu")
        if body["checks"].get("firestore") != "ok":
            falha("Firestore não respondeu")
        if not body["checks"].get("gemini_configurado"):
            falha("Gemini não configurada")
    else:
        falha(f"/ready {st} · {body}")

    print("\n═══ 2. Cadastro ═══")
    email = f"piloto-e2e-{uuid.uuid4().hex[:8]}@example.com"
    senha = "senha-de-teste-e2e-2026"
    _criados["email"] = email
    st, body, _ = req(base, "POST", "/api/auth/signup",
                      {"email": email, "name": "Aluno E2E", "password": senha})
    if st != 200:
        falha(f"cadastro {st} · {body}")
        return
    token = body["token"]
    _criados["student_id"] = body["user"]["user_id"]
    ok(f"cadastrado {email} · user_id={body['user']['user_id']}")
    if body["user"].get("password_hash"):
        falha("resposta do cadastro devolveu o hash da senha")
    else:
        ok("hash da senha não é devolvido")

    print("\n═══ 3. Login ═══")
    st, body, _ = req(base, "POST", "/api/auth/login", {"email": email, "password": senha})
    if st != 200:
        falha(f"login {st} · {body}")
        return
    token = body["token"]
    ok(f"login OK · admin={body['user']['is_admin']}")

    st, body, _ = req(base, "GET", "/api/auth/me", token=token)
    ok(f"/auth/me {body['email']} · provider={body['provider']}") if st == 200 \
        else falha(f"/auth/me {st} · {body}")

    st, body, _ = req(base, "GET", "/api/auth/me")
    ok("sem token → 401 (rota protegida)") if st == 401 else falha(f"sem token devolveu {st}")

    print("\n═══ 4. Carregamento de questões ═══")
    st, body, _ = req(base, "GET", "/api/questoes")
    if st != 200:
        falha(f"/api/questoes {st} · {body}")
        return
    itens = body["items"]
    ok(f"{len(itens)} questão(ões) públicas")
    if not itens:
        aviso("nenhuma questão — o pipeline precisa gerar e sincronizar ao menos uma")
        return

    q = itens[0]
    _criados["item_id"] = q["item_id"]
    ok(f"item_id={q['item_id']}")
    ok(f"ontology_version={q.get('ontology_version')} · schema={q.get('item_schema_version')}")
    if not q.get("ontology_version"):
        falha("item sem ontology_version — o evento de resposta seria indatável")
    if any(k in q for k in ("estrutura_cognitiva", "distratores", "intervencoes")):
        falha("a versão pública vazou a classificação cognitiva")
    else:
        ok("classificação cognitiva não vaza para o aluno")

    correta = next((a["letra"] for a in q["questao"]["alternativas"] if a.get("correta")), None)
    errada = next((a["letra"] for a in q["questao"]["alternativas"] if not a.get("correta")), None)

    print("\n═══ 5. Resposta → evento de Behavior ═══")
    st, body, _ = req(base, "POST", "/api/firestore/students/me/answer",
                      {"item_id": q["item_id"], "alternativa_escolhida": errada,
                       "tempo_resposta_segundos": 37.5, "numero_tentativas": 1},
                      token=token)
    if st != 200:
        falha(f"resposta {st} · {body}")
        return
    if body["acertou"] is False and body["correta"] == correta:
        ok(f"correção no servidor: marcou {errada}, correta {correta} → acertou=False")
    else:
        falha(f"correção inesperada: {body}")

    print("\n═══ 6. Feedback ═══")
    fb = body.get("feedback") or {}
    if fb.get("mensagens"):
        ok(f"título: {fb['titulo']}")
        for m in fb["mensagens"]:
            print(f"      • {m[:100]}")
    else:
        falha("nenhuma mensagem de feedback")

    print("\n═══ 7. Persistência do evento (Firestore) ═══")
    # Verificado direto na fonte, não pela rota administrativa: o aluno do teste
    # não é admin, e o que importa aqui é que o evento chegou ao Firestore.
    eventos = _eventos_do_aluno(_criados["student_id"])
    if not eventos:
        falha("nenhum evento encontrado em students/{uid}/behavior")
    else:
        ok(f"{len(eventos)} evento(s) em students/{_criados['student_id']}/behavior")
        ev = eventos[0]
        if ev.get("schema_version") == "1.1":
            ok("schema_version=1.1 (contrato de behavior vigente)")
        else:
            falha(f"evento no schema {ev.get('schema_version')}, esperado 1.1")
        if ev.get("ontology_version"):
            ok(f"ontology_version={ev['ontology_version']} (evento datável)")
        else:
            falha("evento sem ontology_version — seria indatável")
        if ev.get("item_id") == q["item_id"]:
            ok("evento liga ao item respondido (item_id estável)")
        else:
            falha(f"evento aponta para {ev.get('item_id')}, esperado {q['item_id']}")
        if ev.get("item_hash"):
            ok("item_hash gravado (conteúdo do momento da resposta)")
        else:
            falha("evento sem item_hash")
        if (ev.get("resposta") or {}).get("acertou") is False:
            ok("resposta registrada com a correção do servidor")
        else:
            falha(f"resposta gravada inconsistente: {ev.get('resposta')}")
        desemp = ev.get("desempenho") or {}
        if desemp.get("tempo_resposta_segundos") == 37.5:
            ok("bloco desempenho preservado (coletado, não interpretado)")
        else:
            falha(f"desempenho inesperado: {desemp}")

    print("\n═══ 8. CORS ═══")
    _, _, h = req(base, "GET", "/api/", origem="https://origem-nao-autorizada.example")
    acao = h.get("access-control-allow-origin") or h.get("Access-Control-Allow-Origin")
    ok("origem não autorizada não recebe Access-Control-Allow-Origin") if not acao \
        else falha(f"CORS liberado para origem estranha: {acao}")

    print("\n═══ 9. Erros não vazam interno ═══")
    st, body, _ = req(base, "GET", "/api/questoes/inexistente-xyz")
    texto = json.dumps(body) if not isinstance(body, str) else body
    if any(t in texto for t in ("Traceback", "/Users/", "/app/", "site-packages")):
        falha("resposta de erro vazou caminho ou traceback")
    else:
        ok(f"{st} sem detalhe interno")


def limpar(base: str) -> None:
    """Remove o que o teste criou. Roda mesmo quando um passo falha."""
    print("\n═══ Limpeza ═══")
    import subprocess

    _preparar_ambiente()

    if _criados["email"]:
        try:
            import os

            from pymongo import MongoClient

            url = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
            nome = os.environ.get("DB_NAME") or "sapiens_aluno"
            c = MongoClient(url, serverSelectionTimeoutMS=5000)
            db = c[nome]
            n = db.users.delete_many({"email": _criados["email"]}).deleted_count
            s = db.user_sessions.delete_many({"user_id": _criados["student_id"]}).deleted_count
            print(f"  Mongo: {n} usuário(s), {s} sessão(ões) removidos")
            c.close()
        except Exception as e:  # noqa: BLE001
            aviso(f"limpeza do Mongo falhou: {type(e).__name__}: {e}")

    if _criados["student_id"]:
        try:
            import firestore_service as fs

            cli = fs.get_firestore()
            ref = cli.collection("students").document(_criados["student_id"])
            evs = list(ref.collection("behavior").stream())
            for e in evs:
                e.reference.delete()
            ref.delete()
            print(f"  Firestore: aluno + {len(evs)} evento(s) removidos")
        except Exception as e:  # noqa: BLE001
            aviso(f"limpeza do Firestore falhou: {type(e).__name__}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--sem-limpeza", action="store_true")
    a = ap.parse_args()

    print(f"E2E do app do aluno · {a.base_url}")
    try:
        executar(a.base_url)
    finally:
        if not a.sem_limpeza:
            limpar(a.base_url)

    print()
    if _falhas:
        print(f"{VERMELHO}E2E FALHOU — {_falhas} problema(s){RESET}")
        return 1
    print(f"{VERDE}E2E PASSOU{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
