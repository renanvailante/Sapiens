# Sapiens

Plataforma de estudo para ENEM/vestibular. Quatro pastas: **`aluno/`** (o produto,
onde está quase todo o trabalho), **`pipeline/`** (anotação cognitiva — congelado,
e dono do canon em `pipeline/docs/`), **`professor/`** (painel, só vitrine) e
**`Cerebro/`** (a memória do projeto).

Responda em **português**.

## O conhecimento do projeto está em `Cerebro/`

**Antes de trabalhar, leia [`Cerebro/INDICE.md`](Cerebro/INDICE.md)** e só os nós que
a sua tarefa exigir. Ele roteia por tarefa e por sintoma. O `Cerebro/` responde *por
que* é assim e *o que não fazer*; para *onde está o código*, use `graft`.

Quando aprender algo durável sobre o projeto, **escreva no `Cerebro/`** — não na
memória do Claude, que fica só para preferências do usuário. As regras de manutenção
estão em `Cerebro/README.md`.

## O mínimo que vale antes de qualquer leitura

Não use subagentes, Workflow nem ultracode neste repositório.

**Outras sessões do Claude editam esta mesma árvore agora.** Não são worktrees
isolados. Antes de escrever em arquivo de backend, `git status --short` e olhe
mtimes; releia o arquivo em vez de confiar no que leu antes. Um aviso de "changed on
disk" é sinal real. → `Cerebro/operacao/sessoes-concorrentes.md`

**Deploy publica a ÁRVORE, não o commit.** Commite primeiro e publique de um
worktree em HEAD, com `.env` copiado à mão e `--branch main` no wrangler. O backend
do aluno só builda **da raiz do repo**. Valide sempre por evidência no alvo, nunca
pela saída do comando. → `Cerebro/operacao/deploy.md`

Publicar o frontend do aluno depois de mudá-lo é **pré-autorizado** (o dono pediu
"SEMPRE faça isso"). Nada mais é.

**Nenhum aluno baixa nada do ecossistema** — só admin. Regra permanente e sem
escopo: material se lê dentro do app.

**Nenhuma requisição pode custar O(eventos do aluno) em leituras do Firestore.**
Uma violação disso já derrubou o produto inteiro por um dia.
→ `Cerebro/arquitetura/custo-de-leitura.md`

**Preço nunca é escrito à mão** — nem no JS, nem em arquivo de conteúdo, nem numa
resposta ao usuário sem conferir a constante no backend.
→ `Cerebro/produto/economia-de-sparks.md`

**Os nomes reais da ontologia nunca aparecem para o aluno.** São a IP do produto.

## Convenções de teste

Backend: chamada direta de função, offline, `asyncio.run()` em teste síncrono, sem
`pytest-asyncio`; fixture `fake_db` em `tests/conftest.py`.
Frontend: `CI=true npx craco test --watchAll=false`.
Detalhes e armadilhas do ambiente local → `Cerebro/operacao/ambiente-local.md`.
