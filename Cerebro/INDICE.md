---
tags: [indice, entrada]
atualizado: 2026-09-18
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
| **acrescentar item à barra** de navegação | [[navegacao]] |
| criar **tela nova** | [[padroes-de-tela]] · [[sistema-visual]] |
| mexer em algo que o **celular** toca | [[mobile]] |
| mexer em **gamificação, liga, mural, venda** | [[engajamento]] |
| mexer em **copy, landing, logo, mentor** | [[marca]] |
| mexer em **cadastro, login, WhatsApp** | [[contas-e-acesso]] |
| mexer no **pipeline, ontologia, schema, corpus** | [[pipeline-e-corpus]] · [[canon-pedagogico]] |
| rodar **testes ou o app local** | [[ambiente-local]] |
| **restaurar** algo que "parece errado" no produto | [[superado]] |
| entender o projeto pela primeira vez | [[ecossistema]] |

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
| Dado fantasma no Mongo depois de rodar testes | módulo com `set_db` fora da fixture | [[ambiente-local]] |
| Pagamento entrou e Sparks não | ver o laço de reconciliação e `/admin/sparks/pendentes` | [[pagamentos]] |
| Correção só no Mongo "não pega" | o Firestore é a fonte da verdade e reconstrói tudo | [[dados]] |
| Tela branca no login com Google | handler cross-origin do Firebase | [[contas-e-acesso]] |

## Antes de qualquer coisa

Dois nós curtos que valem para **toda** tarefa. Leia-os quando a tarefa envolver
mudar comportamento de produto, preço, dado de aluno ou dinheiro:

- [[inviolaveis]] — o que nunca se faz.
- [[decisoes-do-dono]] — números e ordens que não são meus para mudar.

E um que vale sempre que você for **escrever** neste repo:

- [[sessoes-concorrentes]] — outras sessões editam esta mesma árvore agora.

## O mapa inteiro

```
Cerebro/
├── INDICE.md              ← você está aqui
├── README.md              ← como este cérebro funciona e se mantém
├── regras/     inviolaveis · decisoes-do-dono
├── operacao/   deploy · ambiente-local · sessoes-concorrentes · incidentes
├── produto/    ecossistema · economia-de-sparks · catalogo · mentis
│               marca · engajamento · contas-e-acesso
├── arquitetura/ dados · custo-de-leitura · pagamentos · motor-cognitivo
│               cursos-conteudo · redacao · canon-pedagogico · pipeline-e-corpus
├── ux/         sistema-visual · navegacao · padroes-de-tela · mobile
└── historico/  superado
```
