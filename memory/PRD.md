# Sapiens Dashboard — PRD

## Problem statement (original)
Construa "Sapiens Dashboard" — uma plataforma de OBSERVABILIDADE PEDAGÓGICA para
professores e coordenadores. É uma camada de visualização de dados já processados por
sistemas externos de análise cognitiva do ecossistema Sapiens. NÃO classifica, NÃO
infere, NÃO gera diagnósticos — só visualiza. Sempre exibir a versão da taxonomia
usada em cada dado. Nunca comparar turmas de versões diferentes sem aviso.
Restrições: sem invenção/estimativa/completar dados ausentes ("Sem dado"), sem IA
generativa, sem edição de dados importados. Agregações permitidas: soma, contagem,
média simples, percentual, ordenação, filtro — sempre rotuladas como "Calculado
pelo Dashboard". 5 telas MVP: Turma, Processo cognitivo, Aluno, Evolução temporal,
Exploração da taxonomia. Filtros globais: turma, período, disciplina, ano escolar,
banca, prova.

## Architecture
- Backend: FastAPI + Motor (MongoDB async), bcrypt + PyJWT auth with httpOnly cookies
  (SameSite=None; Secure) for cross-origin preview URL.
- Frontend: React 19 + React Router 7 + Tailwind + shadcn/ui (Swiss/brutalist override:
  no rounding, no shadows). Recharts for graphs. Fonts: Chivo (headings) + IBM Plex
  Sans (body) + IBM Plex Mono (numbers/IDs).
- DB: `sapiens_dashboard`, collections: `users`, `imports`.

## Ecosystem architecture (canonical — for future iterations)
The Sapiens ecosystem is composed of THREE independent applications sharing a single
source of truth per data type. **This Dashboard is App 3** — a READ-ONLY aggregation
layer. It never recomputes annotations and never duplicates data.

- **App 2 — Pipeline Generator / Banco de Itens** (single source of truth for items):
  Ingests PDFs, produces one **Item Annotation JSON** per question following the Sapiens
  schema; extracts text, alternatives, images, tables, graphs, formulas; each asset gets
  a unique `asset_id` referenced by `resource_uri` (assets are NEVER embedded in JSON).
  Cognitive processes, taxonomy, distractors, and pedagogical interventions live here.
- **App 1 — Plataforma do Aluno** (single source of truth for responses):
  Reads items from App 2 by reference to render the question. When a student answers,
  it writes ONLY a **Student Response Event**: {aluno_id, item_id, alternativa_escolhida,
  correto/errado, tempo_resposta, metadata_sessao}. NEVER duplicates cognitive
  processes, taxonomy, distractors or assets.
- **App 3 — Dashboard (THIS APP)** (read + aggregate only):
  Has NO own bank of questions. Every visualization is a JOIN between App 2 (Item
  Annotation) and App 1 (Response Events). Cross-references observed behavior with the
  cognitive structure, taxonomy, distractors and assets of each item. NEVER recomputes
  the annotation, NEVER modifies items or events.

### Consequences for the Dashboard implementation
- No local DB of questions. The current MVP `imports` collection is a **temporary bridge**
  that already holds turma+aluno+`no_id` snapshots pre-joined; the target architecture
  replaces it with two read-only connectors and computes aggregations on demand.
- Assets are rendered directly from `resource_uri` (never re-uploaded / never stored).
- All aggregations are derived from the JOIN — never received "pre-cooked" from another
  base. Rótulo "Calculado pelo Dashboard" continues to apply.
- Taxonomy versioning must always come from the Item Annotation the response points to.
- Rules already implemented remain valid: campos ausentes → "Sem dado"; nunca inferir/
  classificar/recomendar; comparações entre versões de taxonomia disparam aviso.

## Personas
- Professor(a): visualiza turma, aluno individual, evolução ao longo dos períodos.
- Coordenador(a): visão consolidada, exportação CSV, gerenciamento de imports.

## Core requirements (static)
- Nunca inventar dados. Campo ausente → "Sem dado".
- Sempre exibir versão da taxonomia do snapshot atual.
- Alertar em comparações que atravessam versões diferentes.
- Rotular agregações como "Calculado pelo Dashboard".
- Auth simples (email/senha JWT).

## Implemented (2026-02)
- [x] Auth JWT + cookies httpOnly + admin seed (admin@sapiens.edu / admin123).
- [x] Ingestão de snapshot (POST /api/imports) — JSON upload + endpoint.
- [x] Seed com 2 turmas × 3 períodos × 8 alunos × 7 nós (Matemática/Português/Ciências),
  atravessando duas versões de taxonomia (v0.8 e v0.9) para exercitar avisos.
- [x] GET /api/filters — descoberta de opções.
- [x] Visão da turma — matriz aluno×nó com heatmap 5 níveis + "Sem dado" hatched.
- [x] Visão por processo cognitivo — média + distribuição em bins + lista alunos.
- [x] Visão por aluno — comparação com média simples da turma + coluna Δ.
- [x] Evolução temporal — série de períodos + aviso quando versões diferentes.
- [x] Exploração da taxonomia — árvore navegável por disciplina + detalhes.
- [x] Filtros globais (turma/período/disciplina/ano/banca/prova).
- [x] Exportação CSV da matriz da turma.
- [x] Badge de versão da taxonomia no header, sincronizado com o snapshot exibido.

## Backlog / Next
- [P0 — architectural] Substituir o `imports` monolítico por dois conectores read-only:
  - `items_client` → Banco de Itens (App 2): GET item por `item_id`, listagem por
    filtro (banca, prova, disciplina, nó cognitivo, ano); nunca escreve.
  - `responses_client` → Student Response Events (App 1): GET eventos por aluno/turma/
    período/item; nunca escreve.
  - Novo endpoint interno `/api/join/*` que executa o JOIN in-memory (ou via
    aggregation pipeline se App 2 e App 1 forem MongoDBs no mesmo cluster) e devolve
    os mesmos view-models já usados pelas 5 telas (turma, processo, aluno, evolução,
    taxonomia). As telas do frontend NÃO precisam mudar — apenas a origem dos dados.
- [P0 — architectural] Suporte a `resource_uri` de assets: renderizar imagens/tabelas
  da questão via URI direta do App 2, sem cache local.
- [P0 — architectural] Contrato de erro claro quando App 2 devolve `item_id` ausente
  (nó órfão em Response Event) → exibir "Sem dado" e destacar item removido/renomeado.
- [P1] Exportar CSV também de Processo, Aluno e Evolução.
- [P1] Cache/paginação em joins com grande volume de events.
- [P2] Filtro por versão da taxonomia (comparar apenas dentro da mesma versão).
- [P2] Comparação lado-a-lado de dois períodos (com aviso de versão).
- [P2] Papel de "coordenador" com permissão ampliada; teachers com escopo por turma.
- [P2] Auditoria de leituras (quem consultou o quê e quando — sem alterar App 1/2).
- [P3] Modo "drill-down até a questão": clicar no nó → lista de itens (via App 2) →
  eventos dos alunos naquele item (via App 1), sempre por referência.
