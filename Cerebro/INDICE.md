---
tags: [indice, entrada]
atualizado: 2026-10-01
---

# Índice — o que ler antes de cada tarefa

Tabela de roteamento. **Leia só as linhas que casam com a sua tarefa**, e depois só
os nós apontados. Carregar o Cerebro inteiro anula o propósito dele.

Se nada aqui casar, vá direto ao código (`graft ask "<tarefa>"`) — o Cerebro cobre
**por que** e **o que não fazer**, não **onde**.

## Por tarefa

| Vou… | Leia |
|---|---|
| **publicar / fazer deploy** | [[deploy]] |
| citar, mudar ou criar um **preço** | [[economia-de-sparks]] |
| mexer em **pagamento, Pix, webhook, crédito** | [[pagamentos]] |
| mexer em **curso, e-book, estação, conteúdo** | [[cursos-conteudo]] · [[catalogo]] |
| mexer na **aula ao vivo, mentoria, pacotes, direitos** | [[catalogo]] |
| mexer em **texto de IA, chat, dossiê, prompt** | [[mentis]] |
| mexer em **diagnóstico, error trace, prioridade, cronograma, perfil** | [[motor-cognitivo]] |
| mexer na **correção de redação** | [[redacao]] · [[canon-pedagogico]] |
| escrever **leitura nova do Firestore** | [[custo-de-leitura]] |
| criar **coleção ou campo novo** | [[dados]] |
| mexer em **CSS, cor, tema escuro** | [[sistema-visual]] |
| **acrescentar área, item de menu ou ROTA** | [[navegacao]] |
| criar **tela nova** | [[padroes-de-tela]] · [[sistema-visual]] |
| mexer no **Próximo Passo, prática dirigida, fechamento de série, desfecho de missão** | [[padroes-de-tela]] · [[motor-cognitivo]] |
| mexer em algo que o **celular** toca | [[mobile]] |
| mexer em **gamificação, liga, mural, venda** | [[engajamento]] |
| mexer em **copy, landing, logo, mentor** | [[marca]] |
| mexer em **landing de anúncio, `/ads/*`, criativo pago** | [[landings-de-anuncio]] |
| mexer em **Meta Pixel, `fbq`, evento de conversão, `Lead`, rastreio de anúncio** | [[meta-pixel]] |
| mexer em **cadastro, login, WhatsApp** | [[contas-e-acesso]] |
| mexer em **influencer, afiliado, comissão, tracking/atribuição, campanha, UTM** | [[afiliados]] |
| mexer no **Pesquisador IA de Aquisição, lead de Instagram/YouTube/TikTok, busca web pública, "0 leads encontrados", grounding do Gemini dando 429** | [[aquisicao]] |
| fazer a **IA pesquisar a web** (grounding, custo de chamada de IA) | [[custo-de-ia]] |
| mexer em **activation, TTFV, cohort, marco de produto, primeira compra/recompra/microvitória** | [[analytics-de-produto]] |
| mexer no **pipeline, ontologia, schema, corpus** | [[pipeline-e-corpus]] · [[canon-pedagogico]] |
| rodar **testes ou o app local** | [[ambiente-local]] |
| otimizar/instrumentar o **próprio Claude Code** (índice, cache, tokens, `graft`, `rtk`) | [[ferramentas-claude-code]] |
| **restaurar** algo que "parece errado" no produto | [[superado]] |
| entender o projeto pela primeira vez | [[ecossistema]] |
| saber o que falta para o funil de ativação/monetização | [[ROADMAP_EXECUCAO]] |

## Por sintoma

| Sintoma | Provável causa | Nó |
|---|---|---|
| O app parou **inteiro**, sem erro de deploy | cota do Firestore estourada | [[incidentes]] |
| Publiquei e produção não mudou | worktree → preview, ou stash de outra sessão | [[deploy]] · [[sessoes-concorrentes]] |
| O site inteiro quebrou com `TypeError` depois de publicar | build sem `.env` → `undefined/api` | [[deploy]] |
| Texto sumiu / invisível numa tela | camada de tradução, `.leitura-clara` na mesma tag, ou `hover:` | [[sistema-visual]] |
| Página preta e lisa, sem brilho nos cantos | algo entre `html` e o conteúdo ganhou fundo opaco | [[sistema-visual]] |
| CORS no console em desenvolvimento | o `craco.config.js` anula `.env.development.local` | [[ambiente-local]] |
| Texto espremido a uma palavra por linha no celular | `flex-wrap` com filho `flex-1 min-w-0` | [[mobile]] |
| Rótulo cortado na barra do celular, sem estouro nem quebra | `ellipsis` silencioso a 320px | [[mobile]] |
| Regra de CSS casa a media query e não pinta | bloco de celular vem antes da definição | [[mobile]] |
| Dado fantasma no Mongo depois de rodar testes | módulo com `set_db` fora da fixture | [[ambiente-local]] |
| Pagamento entrou e Sparks não | ver o laço de reconciliação e `/admin/sparks/pendentes` | [[pagamentos]] |
| Correção só no Mongo "não pega" | o Firestore é a fonte da verdade e reconstrói tudo | [[dados]] |
| Tela branca no login com Google | handler cross-origin do Firebase | [[contas-e-acesso]] |
| Erro genérico na tela e o log do servidor diz outra coisa | 500 sai sem CORS, o navegador bloqueia e o `errMsg` cai no texto padrão | [[incidentes]] |
| Mudei a definição de um índice e o banco não mudou | `create_index` não redefine índice existente | [[incidentes]] |
| Cadastro/escrita falha por duplicata num campo que está vazio | `sparse` indexa o campo presente valendo `null` | [[incidentes]] |
| Tela logada quebra só no servidor de verificação local | dado falso incompleto, não o código | [[ambiente-local]] |

## Antes de qualquer coisa

Dois nós curtos que valem para **toda** tarefa. Leia-os quando a tarefa envolver
mudar comportamento de produto, preço, dado de aluno ou dinheiro:

- [[inviolaveis]] — o que nunca se faz.
- [[decisoes-do-dono]] — números e ordens que não são meus para mudar.

E um que vale sempre que você for **escrever** neste repo:

- [[sessoes-concorrentes]] — outras sessões editam esta mesma árvore agora.

Se você é um **agente** (`.claude/agents/`) e é a primeira vez que toca no
Cerebro nesta sessão: leia a seção "Para agentes" do [[README]] — ela explica
a liberdade que você tem para criar/editar/reorganizar aqui, e a diferença
entre conhecimento permanente, decisão, hipótese e log (o que **não** entra).

## Áreas sem nó ainda — não é omissão

Dez agentes especializados (marketing, cost, analytics, conversion, content,
observability, devops, data-quality, research, legal-privacy — ver
`.claude/agents/orchestrator.md`) cobrem domínios que o Sapiens ainda não tem
nó dedicado no Cerebro, porque até 2026-09-20 ninguém tinha registrado
conhecimento durável real sobre eles aqui. **Isso é deliberado** — o
[[README]] explica por que não se pré-cria pasta vazia. Se sua tarefa é numa
dessas áreas e você encontrar algo durável, você cria o primeiro nó (e a
pasta, se fizer sentido) e acrescenta a linha aqui. Se ainda não achou nada
que sobreviva à sessão, não force um nó só para preencher a lacuna.

## O mapa inteiro

```
Cerebro/
├── INDICE.md               ← você está aqui
├── README.md                ← como este cérebro funciona e se mantém, e como agentes devem usá-lo
├── ROADMAP_EXECUCAO.md      ← plano de execução datado (não é nó de conhecimento)
├── regras/     inviolaveis · decisoes-do-dono
├── operacao/   deploy · ambiente-local · sessoes-concorrentes · incidentes
│               ferramentas-claude-code
├── produto/    ecossistema · economia-de-sparks · catalogo · mentis
│               marca · engajamento · contas-e-acesso · afiliados · aquisicao
│               analytics-de-produto · landings-de-anuncio · meta-pixel
├── arquitetura/ dados · custo-de-leitura · custo-de-ia · pagamentos · motor-cognitivo
│               cursos-conteudo · redacao · canon-pedagogico · pipeline-e-corpus
├── ux/         sistema-visual · navegacao · padroes-de-tela · mobile
└── historico/  superado
```
