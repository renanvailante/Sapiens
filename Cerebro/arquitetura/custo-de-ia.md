---
tags: [arquitetura, custo, ia, gemini]
atualizado: 2026-09-21
---

# Custo de IA — grounding, busca web nativa e o que isso muda no desenho

Primeiro nó do agente `cost` (ver "Áreas sem nó ainda" em [[INDICE]]). Nasceu
da avaliação do "Pesquisador IA de Aquisição" (leads de Instagram/WhatsApp/
Telegram via Gemini), mas a descoberta central vale para **qualquer** feature
futura que precise a IA pesquisar a web pública — não é específico daquele
módulo.

> [!warning] Tarifa pública, não medição interna
> Os números abaixo vêm da documentação de preço da Gemini API e de
> agregadores de pricing consultados em 2026-09-21 — **não** de
> `db.gemini_usage`. Confirme na página oficial (`ai.google.dev/gemini-api/
> docs/pricing`) antes de orçar algo real; isso aqui é o teto para decidir
> desenho, não um número para citar como fato medido.

## ⚠️ CORREÇÃO DE 2026-09-21 — o grounding NÃO funciona nesta chave

**Tudo o que esta seção e a seguinte dizem sobre `google_search` continua
verdadeiro sobre o SDK e sobre a documentação, e continua FALSO na prática
para este projeto.** Medido contra a API real, com a `GEMINI_API_KEY` de
produção, de dentro do container do Fly (não local, não em teoria):

```
POST …/models/{modelo}:generateContent  com tools=[{google_search:{}}]
  gemini-3-flash-preview → 429 RESOURCE_EXHAUSTED
  gemini-3.5-flash       → 429 RESOURCE_EXHAUSTED
  gemini-3.6-flash       → 429 RESOURCE_EXHAUSTED
  gemini-flash-latest    → 429 RESOURCE_EXHAUSTED
  (100% das tentativas; a MESMA chave, no mesmo minuto, responde normalmente
   SEM a tool — o 503 ocasional que aparece sem tool é outra coisa, demanda
   do modelo em preview)
```

A quota de grounding desta chave é **zero**: é recurso de tier pago, e os
"5.000 prompts grounded grátis por mês" da seção abaixo não valem para ela.
Nenhuma troca de modelo, retry ou timeout conserta — é billing, não código.

Duas consequências que valem para qualquer feature futura:

1. **"O SDK expõe" nunca é "o servidor aceita, nesta conta".** Este nó já
   avisava (na nota de revisão do agente `ai`) que inspecionar o pacote só
   prova o primeiro. A distância entre os dois custou uma feature inteira que
   nasceu sem funcionar nenhuma vez em produção.
2. **Nenhum `except Exception` pode transformar erro de fonte em resultado
   vazio.** O Pesquisador engolia o 429 e reportava "0/40 leads — fontes
   públicas não renderam mais candidatos", que é uma frase honesta descrevendo
   um fato que não aconteceu. Ver [[aquisicao]].

O que a descoberta usa hoje está em `aluno/backend/web_search.py`: busca
pública sem chave, com a medição de cada fonte no próprio docstring.
Habilitar billing na chave, ou configurar `GOOGLE_CSE_KEY`+`GOOGLE_CSE_CX`
(Programmable Search, 100 consultas/dia grátis, sem cartão), destrava volume
sem mudar nenhuma linha de código.

## O SDK já tem busca web nativa — não precisa contratar nada

`google-genai` (o projeto usa `>=2.12.1` em `aluno/backend/requirements.txt`;
instalado hoje é `2.18.1` — numeração do SDK Python, sem relação com a
numeração da família de MODELO Gemini 3.x citada abaixo, coincidência de
dígito) expõe `types.GoogleSearch()` e
`types.Tool(google_search=types.GoogleSearch())` nativamente — confirmado
inspecionando o pacote instalado, não só a doc. Passar esse `Tool` em
`config.tools` faz o Gemini pesquisar a web como parte da MESMA chamada,
sem SerpAPI/Tavily/Bing nem qualquer serviço pago novo. Isso decide a favor
de "nenhum serviço externo novo" para qualquer feature de pesquisa web via IA
neste projeto.

*(Revisão de 2026-09-21, agente `ai`: a inspeção do pacote instalado só
comprova que o SDK EXPÕE a chamada — que o SERVIDOR do Google de fato aceita
grounding + JSON estruturado juntos na família 3.x, e rejeitava em 1.5/2.x, é
comportamento do lado do servidor, confirmado contra documentação e issues
públicas do `googleapis/python-genai`, não contra o pacote local. Os dois
são achados diferentes; nenhum dos dois é medição interna deste projeto.)*

## Grounding é cobrado por REQUISIÇÃO grounded, separado de tokens

Família Gemini 3.x (que inclui `gemini-3-flash-preview`, o `GEMINI_MODEL`
default do projeto): **5.000 prompts grounded grátis por mês**, depois
**US$ 14 por 1.000 requisições grounded**. Cobrança só ocorre em requisições
que de fato retornam pelo menos uma URL de suporte (grounding support) — uma
chamada que usa a tool mas não encontra nada relevante não é cobrada como
grounded. Isso é caro por CHAMADA, não por lead: uma chamada que descobre 15
leads de uma vez custa o mesmo que uma que descobre 1. **Consequência de
desenho: sempre agregar/batelar a descoberta (N leads por chamada), nunca uma
chamada por lead.** Gemini 2.x tinha tarifa antiga diferente (US$ 35/1.000,
1.500 RPD grátis) — irrelevante aqui, o projeto já está em 3.x.

## Gemini 3 (ao contrário do 2.x) combina grounding com saída JSON estruturada

Em modelos antigos da família Gemini, `tools` (function calling / grounding)
e `response_mime_type="application/json"` eram **mutuamente exclusivos** — a
API rejeitava a combinação. A família Gemini 3 removeu essa restrição:
Structured Outputs (`response_mime_type`/`response_schema`) pode ser
combinado com Grounding with Google Search na mesma chamada. Isso importa
porque `_generate_json` em `aluno/backend/ai_service.py` é construído em
cima exatamente dessa combinação (`response_mime_type="application/json"` +
`system_instruction`) — uma feature que precisasse de grounding NÃO
precisaria abandonar esse padrão nem inventar um segundo caminho de chamada
para extrair texto solto com regex. Funciona com `gemini-3-flash-preview`
(já é o default do projeto); não pressupor que funcione se o `GEMINI_MODEL`
for trocado para algo fora da família 3.x sem reconferir.

## O que isso implica para qualquer feature de "IA pesquisa a web"

- **Descoberta em lote por categoria**, não por lead: uma chamada por
  (plataforma × segmento de público), pedindo um array de N resultados
  estruturados, é ordens de grandeza mais barata que uma chamada por
  resultado — tanto em requisições grounded (US$ 14/1k) quanto em tokens de
  `system_instruction` repetidos.
- **Geração de mensagem por lead continua sendo outro assunto.**
  `influencers.gerar_mensagem_prospeccao`/`gerar_kit` (ver [[afiliados]]) são
  100% template determinístico por decisão explícita — "gerar 50 mensagens
  não custa nada além de CPU". Isso não muda: mensagem em lote continua
  template. Se um fluxo pedir personalização a partir de dado público
  encontrado pela IA, isso é **uma chamada sob demanda, por lead, só quando
  o admin pedir explicitamente** — nunca disparada automaticamente para
  todos os leads de uma execução, porque aí o custo volta a escalar com o
  número de leads em vez de ficar preso ao número de chamadas de descoberta.
- **Cache/dedup de leads já descobertos é dedup de dado, não de chamada de
  IA.** A pergunta certa antes de re-perguntar ao Gemini "existe X?" é
  sempre "já tenho X no banco?" — uma checagem determinística (índice único
  por handle/link normalizado) é grátis comparada a gastar uma chamada
  grounded para redescobrir o que já existe.
- **Rate limit próprio no endpoint de descoberta, além de `require_admin`.**
  `require_admin` impede estranho de chamar; não impede um admin (ou um bug
  de retry/loop no frontend) de disparar a mesma execução cara repetidas
  vezes no mesmo dia. Um teto (ex.: N execuções/dia, guardado em Mongo por
  data) é barato de implementar e é a mesma disciplina que já existe em
  outros lugares do projeto para não deixar custo de IA saltar por loop.

---
Relacionado: [[afiliados]] · [[economia-de-sparks]] (preço ao aluno é outra
coisa — nunca confundir com custo de infra) · [[pipeline-e-corpus]] (o
`pipeline/` é congelado, este nó não se aplica a ele)
