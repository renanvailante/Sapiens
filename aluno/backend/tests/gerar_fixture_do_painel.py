"""Gera o payload de exemplo do painel do perfil, a partir do MESMO código que
serve a rota.

É isso que dá valor ao arquivo: `src/components/perfil/__fixtures__/painel.json`
não é um JSON escrito à mão que concorda com a tela por acaso — ele é a saída
real de `perfil_painel.montar` sobre um aluno inventado com cinco meses de
histórico. O teste do frontend monta a tela inteira contra ele, e é assim que
um nome de campo trocado no servidor aparece como teste vermelho em vez de
aparecer como "0" na tela de alguém.

    python tests/gerar_fixture_do_painel.py

Rode isto sempre que `perfil_painel.montar` mudar de formato — o teste
`test_fixture_do_painel_continua_em_dia` acusa quando esqueceram.
"""
import json, os, random, sys
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import perfil_painel as pp
import prioridade_enem

HOJE = date(2026, 9, 16)
rnd = random.Random(7)

por_dia, por_hora, por_semana_dia = {}, {}, {}
faixa, decisao, origem, frente_semana = {}, {}, {}, {}
FRENTES = ["matematica", "biologia", "quimica", "humanas", "linguagens", "fisica"]

def soma(balde, chave, r, a):
    alvo = balde.setdefault(chave, {"respondidas": 0, "acertos": 0})
    alvo["respondidas"] += r
    alvo["acertos"] += a

total_seg = 0.0
com_tempo = 0
for i in range(150, -1, -1):
    dia = HOJE - timedelta(days=i)
    # Fins de semana mais fracos, e uma pausa de 12 dias em julho.
    if rnd.random() < (0.55 if dia.weekday() >= 5 else 0.25):
        continue
    if date(2026, 7, 5) <= dia <= date(2026, 7, 17):
        continue
    n = rnd.randint(3, 22)
    # A taxa sobe devagar ao longo dos cinco meses: é a história do aluno.
    base = 0.42 + (150 - i) / 150 * 0.28
    acertos = sum(1 for _ in range(n) if rnd.random() < base)
    soma(por_dia, dia.isoformat(), n, acertos)
    for _ in range(n):
        hora = rnd.choice([8, 9, 10, 14, 15, 19, 20, 21, 21, 22, 22, 23])
        soma(por_hora, str(hora), 1, 1 if rnd.random() < base else 0)
    soma(por_semana_dia, str(dia.weekday()), n, acertos)
    seg = rnd.choice([18, 25, 40, 55, 70, 95, 120, 180, 240])
    total_seg += seg * n
    com_tempo += n
    chave_faixa = "rapido" if seg < 45 else ("medio" if seg <= 150 else "longo")
    peso = {"rapido": 0.34, "medio": 0.62, "longo": 0.7}[chave_faixa]
    soma(faixa, chave_faixa, n, sum(1 for _ in range(n) if rnd.random() < peso))
    mudou = rnd.random() < 0.3
    soma(decisao, "mudou" if mudou else "manteve", n,
         sum(1 for _ in range(n) if rnd.random() < (0.44 if mudou else 0.68)))
    soma(origem, rnd.choice(["pratica_questoes"] * 4 + ["treino_habilidade", "curso"]), n, acertos)
    frente = rnd.choice(FRENTES)
    segunda = (dia - timedelta(days=dia.weekday())).isoformat()
    soma(frente_semana, f"{frente}|{segunda}", n, acertos)

telemetria = {
    "por_dia": por_dia, "por_hora": por_hora, "por_dia_semana": por_semana_dia,
    "por_faixa_de_tempo": faixa, "por_decisao": decisao, "por_origem": origem,
    "frente_por_semana": frente_semana,
    "tempo_total_segundos": total_seg, "respostas_com_tempo": com_tempo,
}

disciplina_stats = {}
for chave, valor in frente_semana.items():
    f = chave.split("|")[0]
    soma(disciplina_stats, f, valor["respondidas"], valor["acertos"])

avaliacoes = [
    {"nota_total": 560, "nota_pontos_estimados": 80, "created_at": "2026-06-14T18:00:00+00:00",
     "estado_geral": "AVALIAVEL", "competencias": [
         {"id": "COMP-I", "nivel_pontos": 120}, {"id": "COMP-II", "nivel_pontos": 120},
         {"id": "COMP-III", "nivel_pontos": 120}, {"id": "COMP-IV", "nivel_pontos": 120},
         {"id": "COMP-V", "nivel_pontos": 80}]},
    {"nota_total": 680, "nota_pontos_estimados": 0, "created_at": "2026-07-28T18:00:00+00:00",
     "estado_geral": "AVALIAVEL", "competencias": [
         {"id": "COMP-I", "nivel_pontos": 160}, {"id": "COMP-II", "nivel_pontos": 160},
         {"id": "COMP-III", "nivel_pontos": 120}, {"id": "COMP-IV", "nivel_pontos": 160},
         {"id": "COMP-V", "nivel_pontos": 80}]},
    {"nota_total": 760, "nota_pontos_estimados": 40, "created_at": "2026-09-02T18:00:00+00:00",
     "estado_geral": "AVALIAVEL", "competencias": [
         {"id": "COMP-I", "nivel_pontos": 160}, {"id": "COMP-II", "nivel_pontos": 200},
         {"id": "COMP-III", "nivel_pontos": 160}, {"id": "COMP-IV", "nivel_pontos": 160},
         {"id": "COMP-V", "nivel_pontos": 80}]},
]

painel = pp.montar(
    telemetria=telemetria,
    prioridades=prioridade_enem.ranking(disciplina_stats, {"melhor_nota": 760, "corrigidas": 3}),
    forcas={
        "pontos_fortes": [
            {"rotulo": "Ler nas entrelinhas",
             "explicacao": "Você deduz bem informações que não estão escritas de forma literal, a partir de pistas do texto."},
            {"rotulo": "Localizar informação explícita",
             "explicacao": "Você encontra rápido um dado que está escrito literalmente no texto, tabela ou gráfico."},
        ],
        "pontos_a_desenvolver": [
            {"rotulo": "Raciocínio proporcional",
             "explicacao": "Relacionar duas grandezas que variam juntas ainda é um ponto a fortalecer."},
            {"rotulo": "Converter unidades e escalas",
             "explicacao": "Trocar entre unidades de medida ainda merece atenção."},
        ],
    },
    diagnostico={"total_events": com_tempo, "matched_events": int(com_tempo * 0.72)},
    avaliacoes_redacao=avaliacoes,
    hoje=HOJE,
)
# parents: [0] tests, [1] backend, [2] aluno. O destino é o frontend do app do
# aluno — subir um nível a mais escreve na raiz do repositório.
destino = str(Path(__file__).resolve().parents[2]
           / "frontend/src/components/perfil/__fixtures__/painel.json")
import os
os.makedirs(os.path.dirname(destino), exist_ok=True)
with open(destino, "w", encoding="utf-8") as f:
    json.dump(painel, f, ensure_ascii=False, separators=(",", ":"))
print("respondidas:", painel["resumo"]["respondidas"], "| leituras:", [l["id"] for l in painel["mentis"]["leituras"]])
print("tendencia:", [(t["nome"], t["delta"]) for t in painel["frentes"]["tendencia"]])
print("tamanho:", os.path.getsize(destino) // 1024, "KB")
