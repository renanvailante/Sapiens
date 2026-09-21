---
tags: [produto, visao, entrada]
atualizado: 2026-09-18
---

# O ecossistema Sapiens

Plataforma de estudo para vestibular/ENEM construída sobre uma **ontologia
cognitiva própria**: a tese é que dá para medir *por que* um aluno erra, não só
*quanto* ele erra. Essa medida é o ativo protegido do produto ([[canon-pedagogico]]).

## Quatro superfícies

| | O que é | Estado |
|---|---|---|
| **`aluno/`** | O produto. Onde está ~90% do trabalho. | Em produção, evolui toda semana |
| **`pipeline/`** | Anota questões com a ontologia (Gemini) e é dono do canon em `pipeline/docs/` | **Congelado** por decisão de custo |
| **`professor/`** | Painel de observabilidade pedagógica | No ar, deliberadamente só vitrine |
| **`Cerebro/`** | Este cérebro | — |

`auditoria/`, `cursos/`, `cadernos enem/` e `scripts/` são insumos e relatórios,
não aplicações.

## O app aluno

React (CRA + craco) + Tailwind no frontend, FastAPI no backend. ~40 telas em
**cinco áreas** (Hoje · Agenda · Estudar · Progresso · Comunidade — ver
[[navegacao]]).
Firestore para acervo/eventos/saldo, Mongo para o resto ([[dados]]).

O aluno entra, responde questões, e o sistema mede: **onde** ele vai mal
(`GET /diagnostico`), **por quê** (`GET /motor/*`, o Error Trace) e **o que
fazer agora** (`GET /prioridades`) — três endpoints, que a aba **Progresso** e o
cronograma consomem. Em volta disso há cursos, e-books, redação corrigida, aula ao
vivo, mentoria, comunidade e gamificação — tudo pago em **Sparks**
([[economia-de-sparks]]).

A **Mentis** é a IA e o mascote ([[mentis]]). **Vitor Lara** é o mentor humano —
grava os cursos, dá a live de quinta e atende a mentoria.

## O app professor

Lançado em 2026-09-03, nunca tinha sido publicado antes.

**Ele mostra "sem dado" de propósito.** A própria tela de login dizia, antes de
qualquer mudança minha, que ele "não classifica, visualiza dado já processado por
sistema externo". Só preenche via `POST /imports` (upload manual de JSON).

Por decisão do dono ("não precisa criar duas ferramentas"), **não existe ponte
automática aluno → professor**. O "sistema externo" que ele espera é o
`/diagnostico` do aluno, ligado por link recíproco nas duas telas de login/admin.
Dado real aparecendo automaticamente exigiria ligar o backend do professor ao
Firestore do aluno — **trabalho novo, não feito**.

O Mongo dele é um Atlas fornecido pelo dono, aplicado só como `fly secret`. Não há
cópia local; rotacionar é `fly secrets set MONGO_URL=... --app sapiens-professor`.

## O pipeline

Anota questões com o Gemini contra a Ontologia v1.4. É onde mora `pipeline/docs/`,
o canon governado por GOV-1.0. **Congelado** desde 2026-08-22 — ver
[[pipeline-e-corpus]] e [[decisoes-do-dono]].

## Como encontrar código

Este repo é indexado pelo **graft**. Para "onde está X" / "o que chama Y", use
`graft ask`, `graft grep`, `graft callers` — é mais barato que grep + leitura.
O Cerebro responde **por que** e **o que não fazer**; o graft responde **onde**.

---
Relacionado: [[economia-de-sparks]] · [[dados]] · [[deploy]] · [[inviolaveis]]
