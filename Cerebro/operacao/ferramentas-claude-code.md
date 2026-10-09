---
tags: [operacao, claude-code, tooling]
atualizado: 2026-09-21
---

# Ferramentas do Claude Code neste repo — o que já existe, e o que foi decidido não construir

Auditoria de 2026-09-21: antes de construir qualquer infraestrutura nova de
"otimização do Claude Code" (índice compartilhado, cache de comando, cache de
contexto, observability), confira aqui — a maior parte já existe e funciona.
Reconstruir seria duplicar, não otimizar.

## O que já está resolvido, e por quem

| Camada | Já resolvido por | Evidência |
|---|---|---|
| Índice estrutural do código (arquivos, símbolos, chamadas) | **`graft`**, com reindexação incremental automática | `.claude/settings.json`: hook `PostToolUse` em `Write\|Edit\|MultiEdit` chama `.claude/helpers/graft-hooks.cjs post-edit` a cada edição. `graft check` confirma `stale: []` |
| Cache de saída de comando (grep, find, git, pytest, ls…) | **`rtk`** (binário Homebrew, `~/.claude/RTK.md`) | hook `PreToolUse→Bash` em `~/.claude/settings.json` reescreve comandos crus de forma transparente; cache SQLite (`[retriever] mode="sqlite"`, `max_entries=200`, `retention_days=30`); `rtk gain` mede economia real |
| Conhecimento persistente do projeto, roteado por tarefa/sintoma | **`Cerebro/INDICE.md`** | já existe, já é o índice central — ver `Cerebro/README.md` §"quatro camadas de conhecimento" |
| Reutilização de prefixo de prompt (o "KV cache" que o pedido original queria simular) | **Cache de prompt nativo da Anthropic** (1h de TTL nesta sessão) | não é algo que se implementa por fora — é automático, desde que o prefixo (system prompt, CLAUDE.md, histórico) não mude. `claude-stats` (abaixo) mostra a taxa de cache real medida: **~98%** nas sessões auditadas |
| Cache de build/teste (webpack, yarn, pytest) | **Já nativo** | `aluno/frontend/node_modules/.cache` (webpack/craco) já persiste ~2,2 GB; `.pytest_cache/`, `__pycache__` já existem |
| Dados de observabilidade (tokens, cache hit/miss por mensagem) | **Já gravados nativamente** | transcript JSONL em `~/.claude/projects/<slug>/*.jsonl` carrega o bloco `usage` completo por mensagem — não precisa de instrumentação nova, só de um script que leia o que já está no disco |

**Conclusão da auditoria:** dos ~20 componentes cogitados (índice compartilhado,
cache de conhecimento, cache de comando, cache de arquivo, orçamento de token,
context router, agentes especializados, paralelismo, load balancer, KV cache,
cache semântico, grafo de dependência, cache de teste, cache de build,
observability, snapshot de contexto, memória de sessão, invalidação,
concorrência segura, integração nativa) — a maioria **já está implementada**,
nativa ou via ferramenta já instalada. Construir de novo seria o oposto de
otimizar.

## O que foi deliberadamente NÃO construído, e por quê

Não reabra estes itens sem uma medição concreta que mude a conclusão:

- **Cache semântico/embedding para busca.** `graft` já faz busca estrutural
  precisa (`graft ask`/`grep`/`callers`) — mais barato e sem falso-positivo que
  embeddings, para código. Subir um banco vetorial só para isso seria
  complexidade sem ganho medido.
- **Pipeline fixo de agentes especializados (Explorer→Architect→Coder→Tester→Reviewer→Deploy).**
  Os 23 subagentes de domínio que existiram em `.claude/agents/` foram apagados
  em 2026-10-06: subagente, Workflow e ultracode **não herdam o modo sem
  permissões** da sessão, e cada comando deles virava um pedido de autorização
  ao dono. Regra no `CLAUDE.md`: não se usam neste repo. A trava não é só
  texto: `.claude/settings.local.json` nega as ferramentas `Agent`, `Task` e
  `Workflow`, e a sessão nem as recebe (em 2026-10-09 o
  `subagentStatusLine` órfão também saiu de `.claude/settings.json`). Forçar todo task
  por um pipeline de 6 estágios adiciona latência para o caso comum — a
  maioria das tarefas neste repo é uma edição localizada, não uma
  investigação arquitetural.
- **Grafo de dependência para rodar só testes afetados.** A suíte de backend
  roda 1475 testes em ~21s; a de frontend, 200 testes em ~2,7s (medido em
  2026-09-21). Não há problema de latência real a resolver — a infraestrutura
  para descobrir "quais testes um arquivo afeta" teria custo de manutenção
  maior que o tempo que economizaria.
- **Cache de conteúdo de arquivo entre sessões.** Risco real e documentado:
  [[sessoes-concorrentes]] — outras sessões editam esta árvore agora. Um cache
  de arquivo por hash que não invalida no instante certo produz uma edição em
  cima de conteúdo velho. Dentro de uma sessão isso já não é problema (o
  harness rastreia o estado do arquivo); entre sessões, a defesa que já existe
  é o protocolo de `git status` antes de editar, não um cache.
- **`00_INDEX.md` / `CURRENT_STATE.md` novos.** Duplicariam `Cerebro/INDICE.md`
  e violariam a regra do próprio `Cerebro/README.md` ("cada fato mora em
  exatamente uma camada"; log de execução é `git log`, não memória).
- **Load balancer / router formal entre agentes.** Não há agentes para rotear:
  a sessão principal faz o trabalho inteiro (ver acima).

## O que foi construído

**`scripts/claude/claude-stats`** — lê os transcripts JSONL que o Claude Code
já grava (nenhuma instrumentação nova) e agrega: tokens por tipo (input/output/
cache lido/cache escrito), taxa de cache real, contagem de tool calls por tipo
(o que `rtk` não cobre, porque só vê Bash), arquivos tocados e releituras do
mesmo arquivo, comandos Bash idênticos repetidos. Complementa `rtk
session`/`rtk gain`, que já aparecem no fim do relatório quando o binário
existe.

```bash
scripts/claude/claude-stats            # sessão mais recente
scripts/claude/claude-stats --last 5   # agrega as últimas 5
scripts/claude/claude-stats --list     # lista sessões disponíveis
```

## Decisões em aberto (não tomadas por mim — pedem escolha do dono)

- **`graft build --deep`** (camada semântica/LLM do graft) está em 0% —
  precisa de `GRAFT_API_KEY` e custa chamadas de LLM a cada build. A camada
  barata (wiring, grátis, já em dia) pode ser suficiente; ativar a funda é
  uma escolha de custo vs. profundidade de contexto, não um bug a corrigir.
- **O MCP server `graft`** está declarado em `.mcp.json` mas desligado via
  `disabledMcpjsonServers` em `.claude/settings.local.json`. Pode ser
  intencional (evitar overhead do protocolo MCP quando o CLI já resolve) ou
  esquecimento — não assumi nenhum dos dois.

---
Relacionado: [[sessoes-concorrentes]] · [[deploy]] · [[ambiente-local]]
