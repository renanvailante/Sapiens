"""Verificação real e pequena do `book_cache_key` (cache combinado
ontologia+PDF do caderno) — 2ª rodada da auditoria de custo, 2026-08-22.

Ver `auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI-2.md`. Este script NÃO
reprocessa nenhuma das 89 questões do lote auditado, NÃO grava em
`db.pipelines`/`db.books` — só usa `db.gemini_caches` (bookkeeping de nomes
de cache, nunca conteúdo de prompt) e questões sintéticas.

O QUE ELE VERIFICA, com chamadas reais e pagas:
1. Uma 1ª chamada com `book_cache_key="smoke-caderno-X"` cria o cache
   combinado (ontologia + o arquivo sintético) — confere no doc de
   `db.gemini_caches` que o nome do cache existe.
2. Uma 2ª chamada com o MESMO `book_cache_key` reaproveita esse cache: a
   resposta real do Gemini (`usage_metadata.cached_content_token_count`)
   cresce para cobrir o arquivo (não só a ontologia), e
   `usage_metadata.prompt_token_count` (a parte NÃO cacheada, cobrada em
   cheio) fica pequeno — perto de zero — porque o arquivo não foi reenviado.
3. Como controle, roda a MESMA questão sintética SEM `book_cache_key`
   (comportamento anterior) e compara `prompt_token_count` entre as duas
   configurações — deve ser bem maior sem cache de caderno.

Custo real esperado: poucas chamadas pequenas (texto puro, sem PDF grande) —
ordem de centavos de dólar, não um PDF de 32 páginas.

Uso:
    ./.venv/bin/python manual_book_cache_smoke_test.py [--yes]
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import server  # reusa get_active_ontology/get_active_schema/db já configurados
from cognitive_engine import run_cognitive_pipeline

QUESTAO_SINTETICA = """# Questão smoke-test — Matemática

Um reservatório tem capacidade de 900 litros e está sendo enchido a uma vazão
constante de 60 litros por minuto, partindo vazio.

Quantos minutos são necessários para enchê-lo por completo?

A) 10
B) 12
C) 15
D) 18
E) 20

Gabarito: C
"""


async def _call(ontology, schema, *, book_cache_key: str | None, label: str) -> dict:
    usage_holder: dict = {}

    async def _on_usage(u: dict) -> None:
        usage_holder.update(u)

    raw = await run_cognitive_pipeline(
        ontology,
        [("smoke.md", QUESTAO_SINTETICA.encode("utf-8"))],
        focus_hint=None,
        schema=schema,
        cache_collection=server.db.gemini_caches,
        on_usage=_on_usage,
        thinking_level="LOW",  # barato de propósito — este teste é sobre cache, não thinking
        book_cache_key=book_cache_key,
    )
    print(
        f"[{label}] in={usage_holder.get('prompt_token_count')} "
        f"cache={usage_holder.get('cached_content_token_count')} "
        f"out={usage_holder.get('candidates_token_count')} "
        f"thinking={usage_holder.get('thoughts_token_count')} "
        f"dur={usage_holder.get('duration_ms')}ms"
    )
    return usage_holder


async def main() -> None:
    confirm = "--yes" in sys.argv
    print("Plano: até 3 chamadas reais e pequenas ao Gemini (texto puro, sem PDF grande).")
    print("Nenhuma das 89 questões do lote auditado é usada. Nada é gravado em db.pipelines/db.books.")
    if not confirm:
        print("\nRode de novo com --yes para executar (gasta dinheiro real, poucos centavos).")
        return

    ontology = await server.get_active_ontology()
    schema = await server.get_active_schema()
    book_key = "smoke-caderno-cache-2026-08-22"

    print("\n1) SEM book_cache_key (comportamento anterior — arquivo sempre inline):")
    baseline = await _call(ontology, schema, book_cache_key=None, label="sem-cache-caderno")

    print("\n2) COM book_cache_key, 1ª chamada (cria o cache combinado):")
    first = await _call(ontology, schema, book_cache_key=book_key, label="com-cache-caderno-1a")

    print("\n3) COM book_cache_key, 2ª chamada (deve reusar o cache — arquivo não reenviado):")
    second = await _call(ontology, schema, book_cache_key=book_key, label="com-cache-caderno-2a")

    docs = [d async for d in server.db.gemini_caches.find({})]
    print(f"\nDocumentos em gemini_caches após o teste: {len(docs)}")

    print("\n--- Resumo ---")
    print(f"baseline (sem cache de caderno)   prompt_token_count={baseline.get('prompt_token_count')}")
    print(f"1a chamada (cria cache de caderno) prompt_token_count={first.get('prompt_token_count')}")
    print(f"2a chamada (reusa cache de caderno) prompt_token_count={second.get('prompt_token_count')} "
          f"cached_content_token_count={second.get('cached_content_token_count')}")


if __name__ == "__main__":
    asyncio.run(main())
