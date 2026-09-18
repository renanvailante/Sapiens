---
tags: [operacao, risco]
atualizado: 2026-09-18
---

# Este repo é editado por várias sessões ao mesmo tempo

Várias sessões do Claude Code trabalham neste repositório **na mesma árvore de
trabalho** — não em worktrees isolados. Observado em 2026-08-24 (7 sessões
concorrentes) e confirmado repetidas vezes desde então. Não é hipótese.

## O que isso quebra

**Arquivos.** Um backend inteiro do Mercado Pago apareceu e foi ligado ao
`server.py` ao longo de ~30 minutos enquanto esta sessão editava outros arquivos do
mesmo repo.

**Deploys.** Em 2026-09-08 outra sessão fez `git stash` → build → deploy →
`git stash pop`. As minhas correções voltaram intactas ao disco, então
`git status` e `diff` **não detectam nada errado** — só comparar o código
realmente rodando em produção revela o buraco. Os dois deploys "tiveram sucesso".

**Commits.** Trabalho concluído desta sessão já foi commitado junto por outra
(commit `222e838` levou reconciliação de Sparks, canal de sugestões e redesenho do
Painel de uma vez). E um commit alheio já apareceu no meio de uma implementação.

## Como trabalhar aqui

- Antes de escrever em arquivo de backend — especialmente `firestore_service.py`,
  `server.py`, `settings.py` ou qualquer um que pareça meio-feito — rode
  `git status --short` e olhe mtimes. Uma nota de "changed on disk since you last
  read it" é **sinal real**, não ruído.
- Releia o arquivo atual em vez de confiar no que foi lido antes na conversa.
- Se uma área parece em construção por outra sessão, **construa em cima do que
  existe** em vez de reescrever — e diga isso ao usuário em vez de duplicar em
  silêncio.
- Deploy sempre de worktree em HEAD. Ver [[deploy]].
- Depois de qualquer deploy, e principalmente se o usuário perguntar "tem certeza
  que está no ar?", prove funcionalmente. Hash de bundle mudando sozinho, sem você
  ter publicado, é o sinal de alerta.
- Se a prova falhar, o reparo é republicar a partir da árvore atual (que já está
  correta) e provar de novo. Não é preciso coordenar com a outra sessão.

---
Relacionado: [[deploy]] · [[ambiente-local]]
