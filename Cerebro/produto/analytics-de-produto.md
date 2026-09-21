---
tags: [produto, analytics, growth]
atualizado: 2026-09-21
---

# Analytics de produto — activation, TTFV, cohort

Implementado em 2026-09-21 (auditoria de rebranding). Responde uma pergunta
que nem `growth_events` nem `students/{uid}/behavior` respondiam: "o aluno
chegou a usar o produto de um jeito que indica valor percebido?" —
diferente de aquisição (`growth_events`, funil de marketing) e diferente de
desempenho pedagógico (`behavior`, canon do pipeline). Ver o cabeçalho de
`aluno/backend/product_analytics.py` para a razão completa de ser uma
terceira coleção.

## O que existe

- **Coleção `product_events`** (Mongo) — um documento por MARCO, não por
  ação. `TIPOS` fechado: `primeiro_proximo_passo`, `descoberta_prioridade`,
  `primeira_microvitoria`, `primeira_compra`, `recompra`.
- **Idempotência por `_id` determinístico** (`{uid}:{tipo}` para marcos
  "uma vez na vida"; `{uid}:{tipo}:{chave}` para `recompra`, chaveado pelo
  `mp_payment_id`) — mesma disciplina de `influencer_comissoes`.
- **`product_analytics.registrar/tempo_para_primeiro_valor/
  resumo_ativacao/resumo_cohort`** — funções puras sobre a coleção nova +
  `users` (nunca Firestore, nunca O(eventos) — ver `Cerebro/arquitetura/
  custo-de-leitura.md`).
- **Pontos de gravação já ligados:**
  - `primeira_compra`/`recompra` — dentro de `sparks_payments_service.
    process_payment_webhook`, no mesmo bloco que credita Sparks. Falha aqui
    nunca desfaz o crédito (mesma disciplina do resto do webhook).
  - `primeira_microvitoria` — dentro de `engajamento_service.
    resgatar_missao`, depois do crédito confirmado.
  - `primeiro_proximo_passo` — `POST /analytics/proximo-passo-iniciado`
    (rota nova, `product_analytics_routes.py`), chamada fire-and-forget
    pelo clique no CTA principal de `ProximoPasso.jsx`.
- **Painel**: bloco "Ativação de produto" em `AdminDashboard.jsx` (não é
  aba nova) — `GET /admin/analytics/produto` devolve `resumo_ativacao` +
  `resumo_cohort`.

## O que NÃO existe ainda

**`descoberta_prioridade` é um tipo válido em `TIPOS`, mas nada grava
nele.** A ideia (elo "insight → ação → recompensa" pedido no rebranding de
2026-09-21) era: quando `prioridade_enem.ranking()` muda a frente #1 do
aluno para uma nova, com medida real (não `estado == "sem_medida"`), isso é
uma DESCOBERTA e merece ser celebrada, não só servida como dado analítico.

Não foi implementado nesta rodada porque exige decisão de produto que não
dava para resolver sozinho dentro do escopo: onde gravar o "último topo
visto" sem virar leitura extra no caminho quente de `/prioridades` (rota
compartilhada por Painel, cronograma e dossiê da Mentis — ver o cabeçalho
de `cronograma_routes.minhas_prioridades`), e sobretudo SE a celebração
deveria conceder XP/Sparks (arriscando violar `TestLinhaEtica` — "XP não se
compra" — se o gatilho puder ser manipulado) ou ser só visual (reaproveitar
`OQueMudou.jsx`, sem tocar a economia). **Pendente de decisão do dono antes
de implementar.**

Relacionado: [[afiliados]] · [[aquisicao]] · [[custo-de-leitura]] ·
[[engajamento]]
