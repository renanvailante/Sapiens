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
  dia_cheio — o "padrao" + 2 revisões vencidas e um bloco de hoje no cronograma
              (a trilha do dia com todos os tipos de nó)

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

# O CATÁLOGO vem do próprio backend (`cursos.py` só importa a biblioteca
# padrão): títulos, capas e preços reais, nunca inventados aqui. O que é do
# aluno de teste (acesso, progresso) é que é montado abaixo.
sys.path.insert(0, os.path.join(AQUI, "..", "..", "backend"))
try:
    import cursos as _cursos_reais  # noqa: E402
except Exception:  # pragma: no cover — o servidor sobe mesmo sem o catálogo
    _cursos_reais = None

# Quais cursos têm estação publicada e onde o aluno de teste está em cada um.
_PROGRESSO_TESTE = {
    "cinematica": {"estacoes": 6, "concluidas": 1, "proxima": {"estacao_id": "e2", "titulo": "Velocidade média"}},
    "matematica-basica": {"estacoes": 24, "concluidas": 0, "proxima": {"estacao_id": "e1", "titulo": "Primeira estação"}},
    "calculos-quimicos": {"estacoes": 10, "concluidas": 0, "proxima": {"estacao_id": "e1", "titulo": "Primeira estação"}},
}
_SEM_CONTEUDO = {"hackeando-a-tri"}


def catalogo_de_cursos(c):
    """`GET /cursos` no formato de `cursos_routes.listar`. No cenário `novo`
    o aluno não tem nada (a vitrine com preço); nos outros, o pacote inteiro."""
    if _cursos_reais is None:
        return {"cursos": [], "ebooks": []}
    tem_tudo = c != "novo"
    cursos = []
    for k in _cursos_reais.listar_cursos():
        cid = k["curso_id"]
        item = {**k, "tenho_interesse": False, "tenho_acesso": tem_tudo, "incluso_no_plano": tem_tudo,
                "tem_conteudo": cid not in _SEM_CONTEUDO}
        if item["tem_conteudo"] and tem_tudo:
            p = _PROGRESSO_TESTE.get(cid, {"estacoes": 8, "concluidas": 0, "proxima": None})
            comecou = cid in _PROGRESSO_TESTE
            item["progresso"] = {"estacoes": p["estacoes"], "concluidas": p["concluidas"],
                                 "percentual": round(100 * p["concluidas"] / p["estacoes"]),
                                 "comecou": comecou, "proxima": p["proxima"]}
        cursos.append(item)
    ebooks = [{**e, "tenho_acesso": tem_tudo, "incluso_no_plano": tem_tudo, "tem_conteudo": True}
              for e in _cursos_reais.listar_ebooks()]
    return {"areas": _cursos_reais.listar_areas(), "cursos": cursos, "ebooks": ebooks,
            "custo_ebook": _cursos_reais.EBOOK_CUSTO_SPARKS,
            "live": {"tenho_acesso": tem_tudo, "incluso_no_plano": tem_tudo, "custo_sparks": 200,
                     "duracao_minutos": 60, "ao_vivo_agora": False, "edicao": hoje_local()},
            "direitos": {"cursos_inclusos": tem_tudo}}


# Os cadernos no formato de `server.list_provas_publico`: blocos de 45 por
# (banca, ano, prova). Duas edições, uma delas só com o dia 2 sincronizado —
# o acervo real é assim, irregular.
CADERNOS = [
    {"banca": "ENEM", "ano": 2023, "prova": "AZUL", "numero_min": a, "numero_max": a + 44,
     "count": n, "total_bloco": 45, "disciplinas": [d]}
    for a, n, d in ((1, 45, "Linguagens e Códigos"), (46, 45, "Ciências Humanas"),
                    (91, 44, "Ciências da Natureza"), (136, 45, "Matemática"))
] + [
    {"banca": "ENEM", "ano": 2022, "prova": "AMARELO", "numero_min": a, "numero_max": a + 44,
     "count": n, "total_bloco": 45, "disciplinas": [d]}
    for a, n, d in ((91, 45, "Ciências da Natureza"), (136, 44, "Matemática"))
]

PROVAS_INTEIRAS = [
    {"exam_id": "enem-2023-d1-azul", "year": 2023, "day": 1, "color": "Azul", "title": "ENEM 2023 · 1º dia",
     "total_questions": 90, "has_english": True, "has_spanish": True},
    {"exam_id": "enem-2023-d2-azul", "year": 2023, "day": 2, "color": "Azul", "title": "ENEM 2023 · 2º dia",
     "total_questions": 90, "has_english": False, "has_spanish": False},
]


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
        if c == "dia_cheio" and not ESTADO.get("revisou"):
            return {"itens": [{"processo_id": "P-10", "rotulo": "a reforçar",
                               "praticar": [{"item_id": ITENS[0]}, {"item_id": ITENS[1]}]}],
                    "resumo": {"questoes": 2}}
        return {"itens": [], "resumo": {"questoes": 0}}
    if path == "/api/cronograma":
        if c == "dia_cheio":
            return {"dias": [{"data": hoje_local(), "blocos": [
                {"id": "b1", "titulo": "Matemática · razão e proporção", "inicio": "19:00", "fim": "19:40",
                 "concluido": bool(ESTADO.get("bloco_feito")), "rota": "/estudar/provas?area=Matem%C3%A1tica",
                 "frente_nome": "Matemática"}], "compromissos": []}],
                    "total_blocos": 1, "total_concluidos": 1 if ESTADO.get("bloco_feito") else 0}
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
            # Três missões, como `engajamento.missoes_do_dia` sempre devolve.
            "missoes": [
                {"id": "responder5", "titulo": "Responda 5 questões", "alvo": 5,
                 "progresso": min(5, ESTADO["respostas"]), "concluida": ESTADO["respostas"] >= 5,
                 "sparks": 5, "xp": 20, "rota": "/estudar/provas", "cta": "Praticar",
                 "resgatada": "responder5" in ESTADO.get("resgatadas", set())},
                {"id": "treino", "titulo": "Faça 10 questões do banco de treino", "alvo": 10,
                 "progresso": 0, "concluida": False,
                 "sparks": 10, "xp": 20, "rota": "/estudar/treino", "cta": "Treinar", "resgatada": False},
                {"id": "comunidade", "titulo": "Responda a dúvida de um colega", "alvo": 1,
                 "progresso": 0, "concluida": False,
                 "sparks": 10, "xp": 20, "rota": "/comunidade", "cta": "Ajudar", "resgatada": False},
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
    # O que o Estudar lista: catálogo vazio é o formato certo (lista), e é
    # o que faz `/estudar` montar aqui em vez de quebrar em `exams.reduce`.
    if path == "/api/exams":
        return PROVAS_INTEIRAS
    if path == "/api/provas":
        return {"provas": CADERNOS}
    if path == "/api/cursos":
        return catalogo_de_cursos(c)
    if path == "/api/sparks/packages":
        return {"packages": [], "precos_avulsos": None}
    if path == "/api/mentis/precos":
        return {"explicacao": 7, "intervencao": 10}
    if path == "/api/firestore/students/me/provas-progresso":
        if c == "novo":
            return {"provas": []}
        # Matemática 2023 pela metade e Linguagens 2023 terminada.
        return {"provas": [
            {"banca": "ENEM", "ano": 2023, "prova": "AZUL", "numero_min": 136, "numero_max": 180,
             "respondidas": 18, "total": 45},
            {"banca": "ENEM", "ano": 2023, "prova": "AZUL", "numero_min": 1, "numero_max": 45,
             "respondidas": 45, "total": 45},
        ]}
    if path == "/api/lembretes":
        return {"itens": [], "vencidos": 0, "total": 0}
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
        # As duas questões da revisão vencida: respondidas, a fila esvazia.
        if corpo.get("item_id") in ITENS[:2]:
            ESTADO.setdefault("revisadas", set()).add(corpo.get("item_id"))
            ESTADO["revisou"] = len(ESTADO["revisadas"]) >= 2
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
    if path == "/api/mentis/intervencao":
        # O formato de `mentis_routes`; o texto é o exemplo da receita, que é
        # o caso em que a cor da folha clara já falhou (2026-10-10).
        return {
            "cobrado": 10, "sparks_balance": 110,
            "previa": {"intervencao_id": "INT-03"},
            "conteudo": {
                "o_que_acontece": "Muitas vezes o cérebro tenta simplificar relações complexas usando só somas.",
                "exemplo": {"situacao": "Você adapta uma receita de 4 para 8 pessoas.",
                            "raciocinio_errado": "Somar dois ovos em vez de multiplicar tudo pelo mesmo fator.",
                            "correcao": "Se a escala dobrou, cada componente é multiplicado por dois."},
                "treino": ["Identifique as duas grandezas.", "Escreva a constante antes de calcular."],
                "sinal_de_alerta": "Você somou um valor fixo onde a relação era de multiplicação.",
                "checagem": "Se uma grandeza dobrar, a outra dobra ou cai pela metade?",
            },
        }
    if path.startswith("/api/engajamento/missoes/") and path.endswith("/resgatar"):
        ESTADO.setdefault("resgatadas", set()).add(path.split("/")[4])
        return {"sparks_ganhos": 5, "xp_ganho": 20, "sparks_balance": 125}
    return {}


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))

    def _cors(self):
        # O dev server (`yarn start`, outra porta) também pode falar com este
        # servidor: ecoa a origem e aceita credenciais, como o axios pede
        # (`withCredentials`). Só vale aqui — nada disto existe em produção.
        origem = self.headers.get("Origin")
        if origem:
            self.send_header("Access-Control-Allow-Origin", origem)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
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
            ESTADO["resgatadas"] = set()
            ESTADO["revisou"] = False
            ESTADO["revisadas"] = set()
            ESTADO["bloco_feito"] = False
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
