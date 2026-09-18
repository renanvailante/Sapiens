---
tags: [arquitetura, pipeline, corpus, congelado]
atualizado: 2026-09-18
---

# Pipeline e corpus — congelados

> [!danger] O pipeline está sob congelamento declarado
> Nenhuma mudança estrutural em pipeline, Schema, Ontologia ou contratos cognitivos
> como parte de trabalho de custo. Ver [[decisoes-do-dono]].

## O baseline de custo do Gemini (aprovado 2026-08-22)

Documentado em `auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI-2.md`:

- **Thinking adaptativo LOW → MEDIUM** (`cognitive_engine.run_cognitive_pipeline_adaptive`):
  tenta LOW e escala para MEDIUM **só** se o validador estrutural de produção
  (`item_contract.validate`) rejeitar a saída.
- **Máximo 2 chamadas por questão**, sem terceira tentativa, por desenho.
- Cache de PDF por livro (`book_cache_key`), sobre o cache de ontologia que já
  existia.
- Custo projetado ≈ **R$0,031/questão** (era R$0,152 com MEDIUM fixo, R$0,315 com o
  HIGH original não configurado) — redução de ≈ 79,8% e ≈ 90,3%.

**A próxima otimização tem de ser dirigida por telemetria real** (`db.gemini_usage`,
instrumentado desde a 1ª rodada), mostrando onde o gasto ainda ocorre — não por
outra rodada de estimativa. Antes de propor qualquer mudança de custo aqui,
**consulte `db.gemini_usage` primeiro**.

## A ressalva que ninguém corrigiu

`pipeline/frontend/src/components/BookResults.jsx` tem um dropdown "Thinking"
(LOW/MEDIUM/HIGH, padrão `LOW`) que é **sempre** enviado como `thinking_level`
explícito em todo `POST /book/{id}/process`. Não há opção "adaptativo".

Por desenho, `run_cognitive_pipeline_adaptive` trata `thinking_level` explícito como
escolha humana deliberada e **pula o escalonamento inteiro**. Logo:

> **Processar um livro pela UI existente roda hoje em nível fixo (LOW), sem rede de
> segurança** — o perfil mais arriscado do teste controlado (7/8 válidas), não o
> adaptativo (8/8) em que os números do baseline se baseiam.

As outras 3 entradas de produção (`/pipeline/generate`, `/pipeline/{id}/regenerate`
e a fila em lote) **não** enviam o campo e já usam o modo adaptativo.

**Não corrigido** porque o congelamento veio logo depois da aprovação. Se perguntarem
"por que o comportamento adaptativo não aparece para o livro X", é isto. A correção,
quando autorizada, é pequena e só de frontend: uma opção "ADAPTATIVO — recomendado"
que omite o campo.

## Saneamento do corpus (2026-08-26)

A partir da auditoria em `auditoria/AUDITORIA-EXTRACAO-VISUAL-E-GABARITO-2026-08-25.md`.

**Fatos estruturais que valem para qualquer trabalho futuro** estão em [[dados]]
(Firestore manda, `page_used` é 1-based). Mais um:

- `compute_hexagon` do skills_map dependia só de **cobertura**, não de acerto, então
  corrigir gabarito não mudava o hexágono — mudava só `feedback.pontos_fortes`.
  (A régua mudou depois; ver [[decisoes-do-dono]].)
- A marca d'água ladrilhada atravessa a calha entre colunas: **detectá-la é
  pré-requisito** da detecção de coluna por densidade de glifos.

**Aplicado (fases 0–3 + parte da 4):** auditor `pipeline/scripts/audit_corpus.py`
(read-only), cerco de circulação `aluno/backend/circulacao.py`, `_auto_sync_loop`
congelável, coleção `gabaritos_oficiais` (3 cadernos ENEM D2 CD5 amarelo), 60
gabaritos corrigidos nos 4 stores com `correta_modelo` preservado como rollback,
portão da crença fechado (223 itens), 24 eventos de retificação gravados (249
originais intactos), skills_map de 3 alunos recalculado, 16 `arquivo` fabricados
limpos, 34 âncoras verificadas / 108 assets marcados `incerta`.
**`item_hash` deliberadamente intocado.**

**Pendente:** re-extração de recortes (não há detector validado de figura **dentro**
da região — escolher bbox novo seria arbitrário), contrato `blocos[]`, `item_hash`
sobre projeção de conteúdo, LaTeX inline + KaTeX.

Backups em `.saneamento/` (gitignored — contém dado de aluno e gabaritos do INEP).

## O tamanho real do corpus anotado de ENEM oficial

**Três questões no total** (piloto ENEM 2023 D2 CD11, ver
`auditoria/LOTE-ENEM-2023-D2-CD11.md`), nem sincronizadas para produção.

Isso é o que impede ligar o fluxo legado de correção de gabarito
(`exam_routes.POST /analyses` → `Diagnostic.jsx`) à ontologia real. Esse fluxo gera
"diagnóstico" via LLM solto usando só acerto/erro **por área** (LC/CH/CN/MT), sem
nenhum `item_id` — provavelmente é o que o dono sentiu como "não fidedigno".
**A lacuna é de conteúdo/anotação, não de código.**

---
Relacionado: [[canon-pedagogico]] · [[dados]] · [[motor-cognitivo]] · [[decisoes-do-dono]]
