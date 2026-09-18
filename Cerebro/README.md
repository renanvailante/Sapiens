---
tags: [meta, manutencao]
atualizado: 2026-09-18
---

# Cerebro — memória de longo prazo do Sapiens

Conhecimento durável do projeto, versionado junto do código e navegável no Obsidian.
Comece por [[INDICE]].

## As quatro camadas de conhecimento, e o que é de cada uma

Este repo tem quatro fontes. **Cada fato mora em exatamente uma delas.** Duplicar é
o único jeito garantido de criar contradição.

| Camada | Responde | Quem mantém |
|---|---|---|
| **o código** | qual é o valor, como está implementado hoje | os commits |
| **`graft/`** | onde está, quem chama o quê | gerado automaticamente |
| **`pipeline/docs/`** | o canon pedagógico governado (GOV-1.0, C1–C5) | governança própria |
| **`Cerebro/`** | **por que** é assim, **o que não fazer**, o que já se tentou | você, ao aprender algo |

E, fora do repo, a **memória do Claude** (`~/.claude/projects/…/memory/`): só quem é
o usuário e como ele quer trabalhar. **Nada de projeto vai para lá.**

## O que entra aqui

Só o que tem as três propriedades:

1. **Durável** — continua verdade no mês que vem.
2. **Não derivável** — não se descobre lendo o código nem o `git log`.
3. **Reutilizável** — poupa trabalho ou evita erro em mais de uma tarefa futura.

Na prática, isso é: decisão de produto **e a razão dela**, regra que não pode ser
quebrada, armadilha que já custou tempo, incidente e sua causa raiz, o que foi
tentado e descartado.

## O que NÃO entra

- **Valores que o código já tem.** Cite a constante (`cursos.CURSO_CUSTO_SPARKS`),
  não o número — exceto na tabela de [[economia-de-sparks]], que é a única
  autorizada a listá-los, e ainda assim manda conferir no código.
- **Como o código funciona.** Isso é `graft` e leitura de arquivo.
- **Log de sessão.** "Hoje fiz X" não é conhecimento; o `git log` já faz isso.
- **O canon pedagógico.** Linke para `pipeline/docs/`, não copie.
- **Documentação por documentar.** Se ninguém vai ler isso antes de uma tarefa, não
  escreva.

## Como manter

**Ao aprender algo que se encaixa nos três critérios:** edite o nó existente. Criar
nó novo é a exceção — só quando um assunto novo não cabe em nenhum dos 20 e vai ser
consultado sozinho. Nó novo precisa de uma linha no [[INDICE]], senão ele não existe.

**Ao descobrir que algo aqui está errado ou velho:** corrija **no lugar** e, se a
coisa antiga puder ser "restaurada" por engano, registre em [[superado]]. Não
acumule "ATUALIZAÇÃO em tal data" empilhadas dentro do nó — isso foi exatamente o
que deixou a memória antiga contraditória. **O nó descreve o presente.**

**Ao mudar preço, rota ou nome:** grep no `Cerebro/` antes de commitar.

```bash
grep -rn "<o termo antigo>" Cerebro/
```

**Regras de forma:**

- Português, prosa curta, sem hierarquia profunda. Um nó cabe numa leitura.
- Todo nó termina com uma linha de `Relacionado:`.
- Links no formato `[[nome-do-no]]`, pelo **nome do arquivo sem extensão** — é como
  o Obsidian resolve. Os nomes são únicos no cofre, então não precisa de caminho, e
  **precisam continuar únicos**: dois arquivos com o mesmo nome tornam todo link
  para ele ambíguo.
- Frontmatter mínimo: `tags` e `atualizado`.
- Sempre escreva **por quê**. Um fato sem razão não sobrevive ao primeiro
  refactor — quem vier depois não sabe se pode mudar.

## Verificar antes de afirmar

Um nó daqui é verdade **na data em que foi escrito**. Antes de agir sobre um valor,
caminho ou nome específico que ele cite, **confirme no código** — especialmente
preço, nome de constante e composição de lista. Se divergir: o código vence, e o nó
se corrige no mesmo commit.

## Origem

Migrado em 2026-09-18 de 54 memórias `project_*` do Claude (~200 KB), com
deduplicação, resolução de contradições e verificação dos preços contra o código.
O `CLAUDE.md` da raiz é a ponte: ele carrega só o mínimo e manda ler o [[INDICE]].
