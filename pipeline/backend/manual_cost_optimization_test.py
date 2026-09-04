"""Teste controlado de custo — `GEMINI_THINKING_LEVEL` atual vs. otimizado.

Contexto: a auditoria de 2026-08-22 (`auditoria/AUDITORIA-ECONOMICA-E-CORPUS-
2026-08-22.md`) reconstruiu que o "thinking" do `gemini-3-flash-preview`,
nunca configurado nem medido, era a causa mais provável de um lote de 89
questões ter custado ~R$28 contra uma expectativa de ~R$2. Este script mede
isso de verdade, com chamadas reais e pagas, pequenas e controladas.

O QUE ESTE SCRIPT NÃO FAZ:
- Não reprocessa nenhuma das 89 questões do lote auditado (não usa o PDF
  `2023_PV_impresso_D2_CD5.pdf`, nem texto extraído dele, nem os IDs/dados
  dessas 89 questões).
- Não grava nada em `db.pipelines` nem `db.books` — a coleção de produção e
  o corpus auditado ficam intocados.
- Não altera nenhum default de configuração — só define
  `GEMINI_THINKING_LEVEL` no próprio processo do script, chamada a chamada.

O QUE ELE FAZ:
- Usa um pequeno conjunto de questões SINTÉTICAS, originais, estilo ENEM
  (texto puro, escritas para este teste — não são de nenhuma prova real),
  como entrada multimodal (arquivo .md) para `run_cognitive_pipeline`.
- Roda cada questão em 3 configurações de thinking_level: HIGH (o
  comportamento atual antes desta otimização — nenhuma config = padrão do
  modelo), MEDIUM e LOW.
- Para cada chamada, captura tokens/duração via o novo `on_usage` de
  `cognitive_engine`, e valida a saída estruturalmente com
  `item_contract.validate` (o mesmo validador de produção).
- Grava tudo em `auditoria/teste-otimizacao-custo-raw.json` (evidência bruta)
  e imprime um resumo agregado por config.

Custo real: 8 questões × 3 configs = 24 chamadas pagas ao Gemini. Ordem de
grandeza esperada (ver estimativa impressa antes de confirmar): poucos reais.

Uso:
    ./.venv/bin/python manual_cost_optimization_test.py [--yes]

Sem `--yes`, o script imprime o plano e para, esperando confirmação manual
antes de gastar dinheiro de verdade.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import server  # reusa get_active_ontology/get_active_schema/db já configurados
from cognitive_engine import run_cognitive_pipeline
from item_contract import normalize_item, validate as validate_item
from ontology_validator import OntologyRegistry

OUT_PATH = Path(__file__).parent.parent.parent / "auditoria" / "teste-otimizacao-custo-raw.json"

CONFIGS = [
    {"label": "atual_HIGH", "thinking_level": "HIGH"},
    {"label": "otimizado_MEDIUM", "thinking_level": "MEDIUM"},
    {"label": "otimizado_LOW", "thinking_level": "LOW"},
]

# 8 questões sintéticas, originais, estilo ENEM — cobrindo processos
# cognitivos variados para não enviesar o teste para um único tipo de
# raciocínio. NENHUMA vem de prova real nem do lote auditado.
QUESTOES = [
    {
        "numero": "T1",
        "titulo": "Diluição de solução salina",
        "texto": """# Questão T1 — Ciências da Natureza

Um técnico prepara 2 litros de uma solução salina com concentração de 40 g/L.
Para reduzir a concentração pela metade, ele decide adicionar água pura à
solução, sem remover sal algum.

Qual volume final, em litros, a solução deve ter para atingir a nova
concentração desejada?

A) 1 L
B) 2 L
C) 3 L
D) 4 L
E) 8 L

Gabarito: D
""",
    },
    {
        "numero": "T2",
        "titulo": "Sombra e triângulos semelhantes",
        "texto": """# Questão T2 — Matemática

Um poste de 6 m de altura projeta uma sombra de 4 m no chão, no mesmo
instante em que uma árvore próxima projeta uma sombra de 10 m. Assumindo que
os raios solares incidem paralelos sobre poste e árvore, qual é a altura da
árvore, em metros?

A) 6
B) 9
C) 12
D) 15
E) 16

Gabarito: D
""",
    },
    {
        "numero": "T3",
        "titulo": "Leitura de gráfico de vendas",
        "texto": """# Questão T3 — Matemática

Uma loja registrou vendas mensais crescentes de janeiro a abril e, a partir
de maio, as vendas caíram pela metade a cada mês seguinte, mantendo esse
padrão até agosto. Em abril foram vendidas 320 unidades.

Quantas unidades foram vendidas em julho?

A) 20
B) 40
C) 80
D) 160
E) 320

Gabarito: B
""",
    },
    {
        "numero": "T4",
        "titulo": "Causa do apagão em bairro isolado",
        "texto": """# Questão T4 — Ciências da Natureza

Um bairro sofreu um apagão total após uma tempestade. Moradores notaram que
bairros vizinhos, servidos pela mesma subestação, não tiveram problema, mas
todos ficaram sem luz exatamente no momento em que uma árvore caiu sobre a
linha de distribuição que atende exclusivamente aquele bairro.

Qual é a explicação mais adequada para o apagão restrito a esse bairro?

A) Sobrecarga geral da rede elétrica da cidade.
B) Interrupção do circuito local causada pela queda da árvore sobre o cabo.
C) Falha simultânea e coincidente em todos os transformadores domésticos.
D) Corte de energia programado pela concessionária.
E) Curto-circuito na subestação central que atende toda a região.

Gabarito: B
""",
    },
    {
        "numero": "T5",
        "titulo": "Leitura de texto informativo sobre reciclagem",
        "texto": """# Questão T5 — Ciências da Natureza (texto)

Leia o texto: "A reciclagem do alumínio consome cerca de 5% da energia
necessária para produzir o mesmo alumínio a partir do minério bauxita. Por
isso, embora o Brasil já recicle a maior parte das latas que produz, o maior
ganho ambiental não vem de reciclar mais latas, e sim de reduzir o descarte
de outros materiais recicláveis com taxas de reciclagem muito mais baixas,
como certos plásticos."

De acordo com o texto, a afirmação que ele sustenta diretamente é:

A) Reciclar alumínio não traz benefício ambiental relevante.
B) O Brasil deveria parar de reciclar latas de alumínio.
C) O maior ganho ambiental futuro está em melhorar a reciclagem de outros materiais, não do alumínio.
D) Plásticos não podem ser reciclados de forma alguma.
E) A bauxita é mais barata de processar que o alumínio reciclado.

Gabarito: C
""",
    },
    {
        "numero": "T6",
        "titulo": "Escala de mapa e distância real",
        "texto": """# Questão T6 — Matemática

Em um mapa na escala 1:50.000, a distância entre duas cidades é de 8 cm.

Qual é a distância real entre essas cidades, em quilômetros?

A) 0,4
B) 4
C) 40
D) 400
E) 4000

Gabarito: B
""",
    },
    {
        "numero": "T7",
        "titulo": "Símbolos de segurança em rótulo químico",
        "texto": """# Questão T7 — Ciências da Natureza

Um frasco de produto de limpeza traz três símbolos: uma chama (inflamável),
uma caveira (tóxico) e um ponto de exclamação (irritante). Um usuário decide
guardar esse produto próximo ao fogão, pois avalia que o símbolo mais
relevante é o de "irritante" e que os demais não se aplicam ao
armazenamento doméstico.

O raciocínio do usuário está equivocado porque:

A) O símbolo de irritante já implica risco de incêndio.
B) A combinação dos três símbolos exige interpretação conjunta, e o símbolo de chama indica risco de incêndio que é agravado por proximidade ao fogão.
C) Produtos tóxicos nunca são inflamáveis ao mesmo tempo.
D) Símbolos de segurança são apenas recomendações estéticas do fabricante.
E) O ponto de exclamação anula o significado dos outros dois símbolos.

Gabarito: B
""",
    },
    {
        "numero": "T8",
        "titulo": "Proporção em receita culinária",
        "texto": """# Questão T8 — Matemática

Uma receita rende 12 pães com 3 xícaras de farinha. Um padeiro quer fazer
30 pães, mantendo a mesma proporção de farinha por pão.

Quantas xícaras de farinha ele deve usar?

A) 6
B) 6,5
C) 7
D) 7,5
E) 8

Gabarito: D
""",
    },
]


def _files_for(q: dict) -> list[tuple[str, bytes]]:
    return [(f"sintetica-{q['numero']}.md", q["texto"].encode("utf-8"))]


async def _run_one(ontology, schema, registry, q: dict, config: dict) -> dict:
    os.environ["GEMINI_THINKING_LEVEL"] = config["thinking_level"]

    usage_holder: dict = {}

    async def _on_usage(u: dict) -> None:
        usage_holder.update(u)

    start_wall = datetime.now(timezone.utc)
    error: str | None = None
    validacao = None
    item = None
    try:
        raw = await run_cognitive_pipeline(
            ontology,
            _files_for(q),
            focus_hint=None,
            schema=schema,
            cache_collection=server.db.gemini_caches,
            on_usage=_on_usage,
        )
        item = normalize_item(raw, ontology, arquivo_origem=f"teste-otimizacao/{q['numero']}", registry=registry)
        validacao = validate_item(item, registry)
    except Exception as exc:  # noqa: BLE001 — resultado de teste, não deve derrubar o loop
        error = f"{type(exc).__name__}: {exc}"

    return {
        "questao": q["numero"],
        "titulo": q["titulo"],
        "config": config["label"],
        "thinking_level": config["thinking_level"],
        "started_at": start_wall.isoformat(),
        "usage": usage_holder or None,
        "error": error,
        "validacao": validacao,
        "qualidade_confianca_global": (item or {}).get("qualidade", {}).get("confianca_global") if item else None,
        "qualidade_revisado": (item or {}).get("qualidade", {}).get("revisado") if item else None,
        "n_processos": len(((item or {}).get("estrutura_cognitiva", {}) or {}).get("processos") or []) if item else None,
        "item_id_teste": (item or {}).get("item_id") if item else None,
    }


async def main() -> None:
    confirm = "--yes" in sys.argv
    total_calls = len(QUESTOES) * len(CONFIGS)
    print(f"Plano: {len(QUESTOES)} questões sintéticas × {len(CONFIGS)} configs = {total_calls} chamadas reais ao Gemini.")
    print(f"Configs: {[c['label'] for c in CONFIGS]}")
    print("Nenhuma das 89 questões do lote auditado é usada. Nada é gravado em db.pipelines/db.books.")
    if not confirm:
        print("\nRode de novo com --yes para executar (gasta dinheiro real).")
        return

    ontology = await server.get_active_ontology()
    schema = await server.get_active_schema()
    registry = OntologyRegistry.from_dict(ontology)

    results: list[dict] = []
    for config in CONFIGS:
        for q in QUESTOES:
            print(f"→ {config['label']} · {q['numero']} ({q['titulo']})...", flush=True)
            r = await _run_one(ontology, schema, registry, q, config)
            results.append(r)
            u = r["usage"] or {}
            print(
                f"  in={u.get('prompt_token_count')} cache={u.get('cached_content_token_count')} "
                f"out={u.get('candidates_token_count')} thinking={u.get('thoughts_token_count')} "
                f"total={u.get('total_token_count')} dur={u.get('duration_ms')}ms "
                f"valid={r['validacao']['valid'] if r['validacao'] else 'ERRO: ' + str(r['error'])}"
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados brutos salvos em {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
