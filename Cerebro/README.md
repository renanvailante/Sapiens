---
tags: [meta, manutencao]
atualizado: 2026-09-20
---

# Cerebro — memória de longo prazo do Sapiens

Conhecimento durável do projeto, versionado junto do código e navegável no Obsidian.
Comece por [[INDICE]].

## Para agentes: liberdade aqui, sem pedir permissão

Se você é um agente (qualquer um dos definidos em `.claude/agents/`) trabalhando
neste repo, isto vale antes de qualquer outra coisa:

1. **Leia `CLAUDE.md`** antes de atuar — ele aponta pra cá.
2. **Consulte `Cerebro/` antes de decisões relevantes.** Comece por [[INDICE]],
   que roteia por tarefa e por sintoma; se nada bater, `graft ask` responde
   **onde** o código está, o Cerebro responde **por que** é assim.
3. **Procure primeiro se já existe documentação sobre o problema.** Um nó
   editado vale mais que um nó novo repetindo o mesmo assunto com nome
   diferente.
4. **Você não precisa pedir autorização para criar, editar ou reorganizar
   `.md` dentro de `Cerebro/`** quando isso melhora a memória estrutural do
   projeto. Essa liberdade é sobre **documentação e conhecimento do
   projeto** — não sobre código de produto, arquitetura ou infraestrutura,
   que continuam pedindo confirmação como sempre pediram.
5. **Registre o que é durável**: descoberta arquitetural, decisão, regra,
   contrato entre sistemas, aprendizado, hipótese validada ou refutada —
   qualquer coisa que uma sessão futura (sua ou de outro agente) precisaria
   redescobrir do zero se não estivesse escrita.
6. **Atualize em vez de duplicar.** Se existe um nó sobre o assunto, edite-o
   no lugar. Crie nó novo só quando o conhecimento for uma unidade
   conceitual **realmente distinta** de tudo que já existe.
7. **Conecte com wikilinks** (`[[nome-do-arquivo-sem-extensão]]`) e feche o
   nó com uma linha `Relacionado:` — é o que torna o cofre navegável em vez
   de uma pilha de arquivos soltos.
8. **Não vire log de execução.** "Rodei X", "editei Y", "testei Z" é
   `git log`, não memória. O que entra aqui é o que sobrevive ao commit.
9. **Não apague conhecimento válido só para reorganizar.** Mover, renomear e
   fundir nós é bom; perder uma regra ou um histórico no processo, não.
10. **Contradição não vira duplicata.** Se dois nós (ou um nó e o código)
    dizem coisas diferentes, identifique qual é a fonte certa — normalmente
    o código, ver "Verificar antes de afirmar" abaixo — e corrija o nó
    errado no lugar. Não crie uma segunda versão "atualizada" ao lado da
    antiga.
11. **O que você não sabe ainda não é fato.** Se uma decisão depende de
    informação que você não tem, registre como hipótese ou pendência — ver
    a seção abaixo — em vez de inventar um número ou uma causa.

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
tentado e descartado, hipótese testada (validada ou refutada).

## O que NÃO entra

- **Valores que o código já tem.** Cite a constante (`cursos.CURSO_CUSTO_SPARKS`),
  não o número — exceto na tabela de [[economia-de-sparks]], que é a única
  autorizada a listá-los, e ainda assim manda conferir no código.
- **Como o código funciona.** Isso é `graft` e leitura de arquivo.
- **Log de sessão.** "Hoje fiz X" não é conhecimento; o `git log` já faz isso.
- **O canon pedagógico.** Linke para `pipeline/docs/`, não copie.
- **Documentação por documentar.** Se ninguém vai ler isso antes de uma tarefa, não
  escreva.

## Quatro tipos de registro, e onde cada um mora

O erro mais fácil de cometer aqui não é escrever pouco — é misturar quatro
coisas de natureza diferente no mesmo parágrafo. Antes de escrever, pergunte
qual das quatro você tem na mão:

| Tipo | O que é | Onde mora | Exemplo |
|---|---|---|---|
| **Conhecimento permanente** | Fato estável sobre como o produto funciona e por quê. Verdade até alguém mudar o código. | O nó do assunto (ex. [[motor-cognitivo]], [[dados]]) | "O Firestore é a fonte da verdade para acervo/eventos/saldo." |
| **Decisão** | Número ou regra escolhida deliberadamente por alguém, contra a intuição de "otimizar" — não é parâmetro livre. | [[decisoes-do-dono]] | "Pesos de prioridade do ENEM são 1.00/0.70/0.50, ditados literalmente pelo dono." |
| **Hipótese** | Algo que **ainda não tem evidência confirmada** — uma aposta sobre causa, comportamento do aluno, ou resultado de uma mudança. | O nó do assunto, marcada explicitamente como hipótese (ex. um parágrafo ou lista "Hipóteses abertas"), nunca escrita como se fosse fato | "Hipótese (não testada): reduzir o onboarding para 3 passos aumenta ativação." |
| **Log temporário** | Execução, resultado de uma rodada, o que foi feito numa sessão. | **Não mora em `Cerebro/`.** É `git log`, é o relatório da tarefa, é a conversa. | "Rodei a auditoria X em 20/09 e encontrei 53 achados." |

Uma hipótese que foi testada e confirmada **vira conhecimento permanente** — mova
o parágrafo pro corpo do nó e apague o rótulo de hipótese. Uma hipótese
refutada também é conhecimento (evita repetir o teste) — mantenha registrada
como refutada, não apague.

Quando um nó tiver hipóteses em aberto, isole-as visivelmente (seção própria
ou bloco `> [!hypothesis]`) para que ninguém as leia como fato por engano.

## Como manter

**Ao aprender algo que se encaixa nos três critérios:** edite o nó existente. Criar
nó novo é a exceção — só quando um assunto novo não cabe em nenhum dos nós
existentes e vai ser consultado sozinho. Nó novo precisa de uma linha no [[INDICE]], senão ele não existe.

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
- Prefira **estrutura simples e navegável** a hierarquia profunda. Uma pasta
  nova só se justifica quando há mais de um nó real pedindo esse lugar — não
  crie diretório vazio "para o futuro".

## Áreas de conhecimento hoje, e como elas crescem

```
Cerebro/
├── INDICE.md              ← você está aqui
├── README.md               ← como este cérebro funciona e se mantém
├── ROADMAP_EXECUCAO.md     ← plano de execução datado (não é nó de conhecimento — ver seu próprio aviso de topo)
├── regras/     inviolaveis · decisoes-do-dono
├── operacao/   deploy · ambiente-local · sessoes-concorrentes · incidentes
├── produto/    ecossistema · economia-de-sparks · catalogo · mentis
│               marca · engajamento · contas-e-acesso · afiliados · aquisicao
│               analytics-de-produto
├── arquitetura/ dados · custo-de-leitura · pagamentos · motor-cognitivo
│               cursos-conteudo · redacao · canon-pedagogico · pipeline-e-corpus
├── ux/         sistema-visual · navegacao · padroes-de-tela · mobile
└── historico/  superado
```

Estas seis pastas cobrem o que o produto já tinha até 2026-09-20. Os agentes
especializados em `.claude/agents/` (23 hoje — arquitetura, IA, backend,
banco de dados, frontend, growth, monetização, pedagogia, performance,
segurança, testes, UX e orquestrador, mais marketing, custo, analytics,
conversão, conteúdo, observabilidade, devops, qualidade de dados, pesquisa e
jurídico/privacidade) vão inevitavelmente encontrar conhecimento durável em
áreas que ainda não têm pasta — CAC real de um canal, causa raiz de um
incidente de latência, um contrato de dado entre Mongo e Firestore.

**Isso é esperado, e não se resolve pré-criando pastas vazias.** Uma pasta
nova (`marketing/`, `custo/`, `analytics/`, `observabilidade/` etc.) nasce
quando o **primeiro nó real** daquela área existir, não antes — pré-criar
diretório vazio "para o futuro" é exatamente o tipo de documentação por
documentar que a seção "O que NÃO entra" já proíbe, e é como um cofre vira
cemitério de `.md` gerado por IA sem ninguém ler. Quando isso acontecer,
acrescente a pasta nova ao mapa acima e uma linha no [[INDICE]] — o resto do
cofre não muda.

## Verificar antes de afirmar

Um nó daqui é verdade **na data em que foi escrito**. Antes de agir sobre um valor,
caminho ou nome específico que ele cite, **confirme no código** — especialmente
preço, nome de constante e composição de lista. Se divergir: o código vence, e o nó
se corrige no mesmo commit.

## Origem

Migrado em 2026-09-18 de 54 memórias `project_*` do Claude (~200 KB), com
deduplicação, resolução de contradições e verificação dos preços contra o código.
O `CLAUDE.md` da raiz é a ponte: ele carrega só o mínimo e manda ler o [[INDICE]].

Em 2026-09-20 o time de agentes cresceu de 13 para 23 especialistas (10 novos:
marketing, custo, analytics, conversão, conteúdo, observabilidade, devops,
qualidade de dados, pesquisa, jurídico/privacidade — ver `.claude/agents/` e
`.claude/agents/orchestrator.md`), e este README ganhou a seção "Para agentes"
e a distinção entre conhecimento permanente/decisão/hipótese/log para que a
autonomia nova de criar e editar `Cerebro/` não vire ruído.
