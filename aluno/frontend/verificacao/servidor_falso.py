"""Servidor de VERIFICAÇÃO local do app do aluno — telas logadas sem login real.

Agente não pode digitar senha, e o dev server fala com produção (ver
`Cerebro/operacao/ambiente-local.md`). Este servidor entrega um BUILD do
frontend e responde às rotas da API com um aluno de teste, na MESMA origem
(sem CORS). Nada aqui toca produção.

    # 1. build apontando para cá (fora da árvore, sem mexer no .env):
    REACT_APP_BACKEND_URL=http://localhost:8799 BUILD_PATH=/tmp/build-verificacao \
      DISABLE_ESLINT_PLUGIN=true GENERATE_SOURCEMAP=false npx craco build
    # 2. servir:
    python3 verificacao/servidor_falso.py /tmp/build-verificacao
    # 3. no navegador: localStorage.setItem("sapiens_token", "teste") e abrir /hoje

Cenários (GET /__cenario/<nome>, também zera os contadores):
  padrao    — 40 respostas de prova, um padrão de erro com causa, uma revisão acertada ontem
  so_provas — 40 respostas, motor sem padrão (Próximo Passo "Continue de onde parou")
  novo      — conta sem resposta nenhuma

Rota sem mock aparece no stderr como "SEM MOCK GET ..." — é o primeiro lugar
para olhar quando uma tela quebra aqui e não em produção (o dado falso
incompleto quebra telas que o dado real não quebra).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

AQUI = os.path.dirname(os.path.abspath(__file__))
BUILD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "..", "build")
# O painel do Progresso usa a fixture que o próprio backend gera
# (`gerar_fixture_do_painel.py`) — formato real, não inventado aqui.
FIXTURE_PAINEL = os.path.join(AQUI, "..", "src", "components", "perfil", "__fixtures__", "painel.json")

ESTADO = {"cenario": "padrao", "respostas": 0, "treino": {"HAB-01": [5, 2]}}


def agora(delta_dias=0):
    return (datetime.now(timezone.utc) - timedelta(days=delta_dias)).isoformat()


def hoje_local():
    return datetime.now().strftime("%Y-%m-%d")


LINHA_CAUSA = {
    "origem": "error_trace", "processo_id": "P-10",
    "processo_nome": "Relacionar grandezas proporcionais",
    "sem_intervencao_catalogada": False, "provisorio": True,
    "ocorrencias_raiz": 4, "peso_raiz": 2.1, "percentual_acerto": 38.5, "respondidas": 13, "acertos": 5,
    "erro_dominante": {"id": "ERR-X", "nome": "Inverter a direção da proporção", "sem_catalogo": False},
    "intervencao": {"id": "INT-03", "nome": "Fixar a direção"},
}

ITENS = [f"ENEM-2023-AZUL-{n}" for n in (136, 141, 150, 158, 172, 177)]


def habilidades():
    nomes = ["Ordenar valores", "Razão entre grandezas", "Proporção direta e inversa"]
    out = []
    for i in range(56):
        hid = f"HAB-{i + 1:02d}"
        r, a = (0, 0)
        if ESTADO["cenario"] == "trilha" and hid in ESTADO["treino"]:
            r, a = ESTADO["treino"][hid]
        out.append({
            "hab_id": hid, "nome": nomes[i] if i < 3 else f"Habilidade {i + 1}",
            "respondidas": r, "acertos": a,
            "percentual": round(100 * a / r, 1) if r else None,
            "classificacao": "sem_dados" if r < 5 else ("forte" if a / r >= 0.8 else "fraco" if a / r <= 0.4 else "neutro"),
        })
    return out


def questao(item_id, n):
    return {
        "item_id": item_id,
        "fonte": {"banca": "ENEM", "ano": 2023, "prova": "AZUL", "numero": n, "disciplina": "Matemática"},
        "questao": {
            "enunciado": (
                f"(Questão de teste {n}) Uma receita usa 3 xícaras de farinha para 12 biscoitos. "
                "Mantida a proporção, quantas xícaras são necessárias para 20 biscoitos?"
            ),
            "alternativas": [
                {"letra": "A", "texto": "4"}, {"letra": "B", "texto": "5"},
                {"letra": "C", "texto": "6"}, {"letra": "D", "texto": "7,2"}, {"letra": "E", "texto": "8"},
            ],
        },
    }


def rota_get(path, q):
    c = ESTADO["cenario"]
    if path == "/api/auth/me":
        return {"user_id": "aluno-teste", "name": "Aluno Teste", "email": "aluno.teste@sapiens.test",
                "whatsapp": "+5511900000000", "role": "student"}
    if path == "/api/firestore/students/me/sparks":
        return {"sparks_balance": 120, "direitos": {}}
    if path == "/api/firestore/students/me/activity":
        return {"dates": [agora(1)[:10]]}
    if path == "/api/skills-map":
        return {"hubs": []}
    if path == "/api/firestore/students/me/respondidas":
        n = 0 if c == "novo" else 40
        return {"item_ids": [f"X-{i}" for i in range(n)]}
    if path == "/api/firestore/students/me/rounds":
        return {"rounds": []}
    if path == "/api/analyses":
        return []
    if path == "/api/motor/perfil":
        linhas = [LINHA_CAUSA] if c == "padrao" else []
        return {"habilidades_prioritarias": linhas, "provisorio": bool(linhas), "mapa_de_erros": []}
    if path == "/api/treino/habilidades":
        return {"habilidades": habilidades()}
    if path == "/api/redacao":
        return {"items": []}
    if path == "/api/revisao/fila":
        return {"itens": [], "resumo": {"questoes": 0}}
    if path == "/api/cronograma":
        return {"dias": []}
    if path == "/api/onboarding":
        return {}
    if path == "/api/engajamento/me":
        return {
            "ofensiva": {"dias": 4 if ESTADO["respostas"] else 3, "recorde": 5, "estudou_hoje": bool(ESTADO["respostas"]),
                         "em_risco": not ESTADO["respostas"], "congeladores": 0,
                         "max_congeladores": 2, "custo_congelador": 50,
                         "semana": [{"dia": agora(i)[:10], "ativo": i in (1, 2, 3), "congelado": False, "hoje": i == 0} for i in range(6, -1, -1)]},
            # XP cresce com as respostas (10 por resposta), como o servidor faria.
            "nivel": {"nivel": 3, "xp_total": 640 + 10 * ESTADO["respostas"], "xp_no_nivel": 140, "xp_do_nivel": 400,
                      "xp_para_o_proximo": 260, "percentual": 35},
            "missoes": [
                {"id": "responder5", "titulo": "Responda 5 questões", "alvo": 5,
                 "progresso": min(5, ESTADO["respostas"]), "concluida": ESTADO["respostas"] >= 5,
                 "sparks": 5, "xp": 20, "rota": "/estudar/provas", "cta": "Praticar",
                 "resgatada": ESTADO.get("resgatou", False)},
            ], "liga": {"liga_id": "bronze", "nome": "Bronze", "cor": "#cd7f32", "minha_posicao": 3, "total": 3, "meus_pontos": 120,
                     "sobem": 3, "caem": 2, "fecha_em": agora(-3),
                     "tabela": [{"posicao": 1, "uid": "u1", "nome": "Colega A", "pontos": 300, "voce": False},
                                {"posicao": 2, "uid": "u2", "nome": "Colega B", "pontos": 200, "voce": False},
                                {"posicao": 3, "uid": "aluno-teste", "nome": "Aluno Teste", "pontos": 120, "voce": True}]},
            "enem": 40, "hoje": hoje_local(), "total_respostas": 40,
        }
    if path == "/api/engajamento/liga":
        return {"liga_id": "bronze", "nome": "Bronze", "cor": "#cd7f32", "minha_posicao": 3, "total": 3, "meus_pontos": 120,
                "sobem": 3, "caem": 2, "fecha_em": agora(-3),
                "tabela": [{"posicao": 1, "uid": "u1", "nome": "Colega A", "pontos": 300, "voce": False},
                           {"posicao": 2, "uid": "u2", "nome": "Colega B", "pontos": 200, "voce": False},
                           {"posicao": 3, "uid": "aluno-teste", "nome": "Aluno Teste", "pontos": 120, "voce": True}]}
    if path == "/api/cursos/precos":
        return {"custo_live": 200}
    if path == "/api/revisao/trajetoria":
        if c == "novo":
            return {"habilidades": [], "nexo_causal": False}
        return {"habilidades": [{"processo_id": "P-7", "processo_nome": "Ler gráficos e tabelas", "provisorio": True,
                                 "marcos": [{"tipo": "raiz", "quando": agora(6), "rotulo": "erro recorrente"},
                                            {"tipo": "reteste_ok", "quando": agora(1), "rotulo": "revisão em dia"}]}],
                "nexo_causal": False, "provisorio": True, "instrumentacao": {"retestes": {"total": 1, "acertos": 1, "taxa": 100}}}
    if path == "/api/firestore/students/me/behavior":
        return {"flags": {"guia_visto": True, "onboarded": True}}
    if path.startswith("/api/motor/habilidade/"):
        return {
            "processo": {"id": "P-10", "nome": "Relacionar grandezas proporcionais"},
            "desempenho": {"respondidas": 13, "acertos": 5, "percentual_acerto": 38.5, "amostra_minima": 5},
            "provisorio": True,
            "intervencao": {
                "origem": "error_trace", "intervencao_id": "INT-03", "intervencao_nome": "Fixar a direção",
                "objetivo": "Fixar a direção da relação: quando uma grandeza sobe, a outra sobe ou desce?",
                "como_praticar": [
                    "Antes de montar a conta, responda em voz alta: se A dobrar, o que acontece com B?",
                    "Teste com um número fácil (dobro, metade) e veja se o resultado tem a direção esperada.",
                    "Escreva se é proporção direta ou inversa antes de escrever a expressão.",
                ],
                "sinal_de_progresso": "Você detecta sozinho a resposta absurda porque ela anda no sentido contrário ao previsto.",
                "praticar": {"itens": [{"item_id": i} for i in ITENS], "total_disponivel": 9},
            },
        }
    if path == "/api/questoes":
        ids = (q.get("item_ids") or [""])[0].split(",")
        ids = [i for i in ids if i] or ITENS[:5]
        return {"items": [questao(i, 136 + k) for k, i in enumerate(ids)]}
    if path == "/api/perfil/painel":
        with open(FIXTURE_PAINEL) as f:
            return json.load(f)
    if path == "/api/treino/precos":
        return {"custo_por_questao": 5}
    if path == "/api/treino/mapa":
        def no(hid, nome, x, y, estado, r=0, a=0):
            return {"hab_id": hid, "nome": nome, "x": x, "y": y, "estado": estado, "respondidas": r, "acertos": a}
        r1, a1 = ESTADO["treino"]["HAB-01"]
        return {
            "biomas": [{"bioma_id": "relacionar", "nome": "Relacionar", "ideia": "comparar", "resumo": "Aparece em receitas, mapas e escalas.",
                        "nodes": [no("HAB-01", "Ordenar valores", 400, 540, "in_progress", r1, a1),
                                  no("HAB-02", "Razão entre grandezas", 440, 580, "available"),
                                  no("HAB-03", "Proporção", 470, 600, "discovered")],
                        "total": 3, "visiveis": 3, "dominadas": 0}],
            "arestas": [{"source": "HAB-01", "target": "HAB-02"}, {"source": "HAB-02", "target": "HAB-03"}],
            "sparks_balance": 120, "custo_conceito": 10,
        }
    if path.startswith("/api/treino/habilidade/") and path.endswith("/base"):
        hid = path.split("/")[4]
        r, a = ESTADO["treino"].get(hid, [0, 0])
        return {"hab_id": hid, "respondidas": r, "acertos": a, "questoes": [
            {"indice": i, "dificuldade": "MEDIO", "enunciado_antes": f"Questão de treino {i}: qual é o dobro de {i * 3}?",
             "alternativas": [{"letra": L, "texto": str(i * 3 * 2 + d)} for L, d in zip("ABCDE", (0, 1, 2, 3, 4))]}
            for i in (1, 2, 3)]}
    return None


def rota_post(path, corpo):
    if path == "/api/firestore/students/me/answer":
        ESTADO["respostas"] += 1
        n = ESTADO["respostas"]
        acertou = n % 5 not in (1, 4)  # 1ª e 4ª de cada cinco erram
        return {
            "acertou": acertou, "correta": "B",
            "feedback": {"titulo": "Mandou bem!" if acertou else "Quase.", "mensagens": [] if acertou else ["Confira a direção da relação."]},
            "causa_raiz": None if acertou else {"erro_id": "ERR-X", "processo_id": "P-10"},
            "event_id": f"ev-{n}", "professor_invisivel": None, "microdiagnostico": None,
        }
    if path.startswith("/api/treino/habilidade/") and path.endswith("/responder"):
        hid = path.split("/")[4]
        r, a = ESTADO["treino"].get(hid, [0, 0])
        acertou = corpo.get("alternativa") == "A"
        ESTADO["treino"][hid] = [r + 1, a + (1 if acertou else 0)]
        r, a = ESTADO["treino"][hid]
        return {"acertou": acertou, "gabarito": ["A"], "elucidacao": "O dobro é a soma do número com ele mesmo.",
                "respondidas": r, "acertos": a,
                "classificacao": "sem_dados" if r < 5 else ("forte" if a / r >= 0.8 else "fraco" if a / r <= 0.4 else "neutro"),
                "sparks_ganhos": 1, "sparks_balance": 121}
    if path == "/api/firestore/students/me/rodada/concluir":
        return {"sparks_ganhos": 0}
    if path.startswith("/api/engajamento/missoes/") and path.endswith("/resgatar"):
        ESTADO["resgatou"] = True
        return {"sparks_ganhos": 5, "xp_ganho": 20, "sparks_balance": 125}
    return {}


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/__cenario/"):
            ESTADO["cenario"] = u.path.split("/")[-1]
            ESTADO["respostas"] = 0
            ESTADO["treino"] = {"HAB-01": [5, 2]}
            ESTADO["resgatou"] = False
            return self._json({"cenario": ESTADO["cenario"]})
        if u.path.startswith("/api/"):
            r = rota_get(u.path, parse_qs(u.query))
            if r is None:
                sys.stderr.write(f"SEM MOCK GET {u.path}\n")
                r = {}
            return self._json(r)
        caminho = os.path.join(BUILD, u.path.lstrip("/"))
        if not os.path.isfile(caminho):
            caminho = os.path.join(BUILD, "index.html")
        tipo = {".js": "application/javascript", ".css": "text/css", ".html": "text/html", ".json": "application/json",
                ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2", ".ico": "image/x-icon"}.get(
            os.path.splitext(caminho)[1], "application/octet-stream")
        with open(caminho, "rb") as f:
            b = f.read()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            corpo = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            corpo = {}
        r = rota_post(u.path, corpo)
        if r == {} and u.path.startswith("/api/"):
            sys.stderr.write(f"POST sem mock específico {u.path}\n")
        return self._json(r)

    do_PUT = do_POST


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8799), H).serve_forever()
