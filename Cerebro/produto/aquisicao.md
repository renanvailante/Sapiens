---
tags: [produto, growth, ia, admin]
atualizado: 2026-09-21
---

# Aquisição — o Pesquisador IA no Admin

> **Reescrito em 2026-09-21 (segunda passada), depois de a versão original
> nunca ter funcionado uma vez em produção.** Boa parte do texto abaixo
> descreve o desenho ANTIGO, baseado em `google_search` do Gemini. Leia
> primeiro a seção seguinte; ela diz o que foi medido e o que mudou.

## O que estava errado: a busca nunca aconteceu

O botão devolvia `0/40 leads novos encontrados (fontes públicas verificáveis
não renderam mais candidatos válidos)`. A frase é honesta e o fato é falso: a
busca **nunca rodou**. Medido contra a API real, com a chave de produção, de
dentro do container do Fly — toda chamada com
`tools=[types.Tool(google_search=...)]` responde **429 RESOURCE_EXHAUSTED**,
em 100% das tentativas, em `gemini-3-flash-preview`, `gemini-3.5-flash`,
`gemini-3.6-flash` e `gemini-flash-latest`. A mesma chave, no mesmo minuto,
responde normal SEM a tool. A quota de grounding desta chave é zero (recurso
de tier pago). Detalhe em [[custo-de-ia]].

O `except Exception` de `descobrir_leads` engolia o 429 e devolvia `[], 0`, e
o resumo da rodada interpretava isso como ausência de candidatos. **A lição
que vale para qualquer feature: falha de fonte e resultado vazio nunca podem
sair pelo mesmo cano.** Hoje o resumo carrega `fontes` (estado de cada
consulta) e `erros_tecnicos`, e `AdminInfluencers.jsx` mostra os dois — um
zero sem causa visível é o que não pode voltar.

## A inversão: a IA parou de produzir URL

Antes: a IA devolvia leads prontos e tentávamos verificar depois — o que é
impossível de fazer direito, porque o grounding vem como link de
redirecionamento agregado por chamada. Agora:

1. **`aluno/backend/web_search.py` acha URLs reais.** Busca pública, sem
   chave, sem login, sem cookie. Nenhuma IA participa.
2. **Filtro determinístico** de domínio e formato de perfil
   (`_candidato_de`/`_identificador_de`) — `/p/`, `/explore/`, `/popular/` e
   `/reel/` nunca viram lead.
3. **A IA só CLASSIFICA**, por ÍNDICE. Ela não escreve URL nenhuma; índice
   fora do lote é descartado, não "corrigido".
4. **Se a IA cair, a heurística decide** e o lead nasce
   `classificado_por="heuristica"`. Uma falha de IA não zera uma rodada cujos
   candidatos já são reais.

Cada lead grava `fonte_busca`, `fonte_consulta`, `fonte_pagina`,
`pesquisado_em`, `motivo_inclusao` e `classificado_por`.

## O que cada fonte realmente entrega (medido, não suposto)

| fonte | veredito |
|---|---|
| `html.duckduckgo.com` | melhor-esforço. 2/12 numa rajada, depois **0/6** — o IP do Fly foi banido com captcha. Robots permite; a fonte é que recusa. Fica com circuit breaker: 3 falhas seguidas e o provedor é pausado por 15 min, para não gastar a rodada colecionando o mesmo erro. |
| `bing.com/news/search?format=RSS` | **funciona e é a fonte que sustenta hoje.** Robots permite (`Disallow: /search` não casa com `/news/search`) e o feed traz a URL real do artigo. |
| leitura de página pública + extração de perfis linkados | **a de melhor proveniência.** Numa medição real rendeu 28 perfis únicos de 46 artigos, entre eles `@dosesdahistoria`, `@prof.barbaragarbinato`, `@profgabrielcabral`, `@portuguescomleticia`, `@ameninadamatematica` — criadores de verdade. |
| `bing.com/search?format=RSS` | funciona, mas robots **proíbe**. Não usamos: decisão de conformidade, não de capacidade. |
| yep, ecosia, brave, stract, 4get, SearXNG públicos | 403/429/401. Inutilizáveis de datacenter. |
| Common Crawl para `instagram.com/*` | 404 — o Instagram bloqueia crawler, não há captura nenhuma. |
| YouTube Data API / Custom Search com a `GEMINI_API_KEY` | `401 "API keys are not supported by this API"`. A chave do AI Studio não vale fora da Gemini API. |

**O filtro que separou lead de ruído** foi `mencionado_no_texto`: o perfil que
o artigo DISCUTE aparece no texto visível; o link institucional do veículo
(`jornaloglobo`, `portal_ig`, `tiktokbrasil`) aparece só no HTML. Sem esse
corte, o resultado mais frequente da estratégia de artigos era o Instagram do
próprio jornal.

## A rodada real de 2026-09-21 (banco de produção, código publicado)

`limite_total=10`, CRM de 0 → **10 leads**, 108 s, nenhum aviso de déficit.

| fonte | consultas |
|---|---|
| `bing_news_rss` | 17 OK · 5 de cache · 7 sem resultado |
| `duckduckgo_html` | 2 OK · 19 com falha (captcha, depois pausado pelo breaker) |
| leitura de página | 2 com falha (403 de portal) |

Descartes, todos com motivo: 13 `url_nao_e_perfil`, 2 `ia_considerou_irrelevante`,
2 `so_link_de_rodape`, 1 `dominio_fora_da_allowlist`.

Entre os leads: `instagram.com/repertorioenem` (896.000 seguidores lidos da
própria fonte, prioridade alta, classificado pela IA),
`instagram.com/cursoenemgratuito` (300.000), e os TikTok
`@dosesdahistoria`, `@prof.barbaragarbinato`, `@anglo.vestibulares`,
`@portuguescomleticia`.

**Dois achados dessa rodada que valem guardar:**

1. **A quota do free tier do Gemini é 20 requisições por DIA por modelo**
   (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`) — não só o grounding.
   Uma rodada completa gasta uma chamada de classificação por par
   (plataforma × nicho), então ela sozinha pode estourar o dia. Quando estoura,
   a heurística assume e a rodada continua — mas os leads nascem
   `classificado_por="heuristica"`, `prioridade=baixa`, e o ruído
   institucional passa. **É o sinal para o admin de que aquela rodada precisa
   de triagem manual.**
2. **`influencer_created` nunca foi gravado**: `criar_lead` emitia
   `origem=...` e `growth_events.registrar` não aceita esse nome; o
   `TypeError` morria no `except` de `_emitir`, que só logava. Falha calada
   desde que o Pesquisador nasceu, encontrada só numa rodada contra o banco
   real. Corrigido — `_emitir` manda campo desconhecido para `meta`.

## O teto real sem motor de busca, e como ele se move

A rodada COMPLETA logo depois trouxe **+0 leads**: 28 consultas atendidas pelo
cache, todos os candidatos já no CRM, dedup barrando tudo. Não era teto da
fonte — era teto da **variedade das perguntas**. Cinco nichos genéricos
convergem para os mesmos poucos artigos.

O eixo que move isso é **matéria**, não exame: a imprensa educacional escreve
"professores de redação que viralizaram", "canais de química para o ENEM".
`NICHOS_PADRAO_*` girou para matéria (redação, matemática, biologia, história,
química, física, geografia) e `_nucleo_do_nicho` traduz cada nicho para o
termo curto que cabe numa manchete — um nicho de persona ("estudantes de
Medicina que produzem conteúdo para vestibulandos") não aparece em manchete
nenhuma, e era por isso que rendia zero.

**Regra para quem mexer nisto depois:** mais leads vêm de mais artigos
DIFERENTES, não de mais consultas parecidas. Antes de aumentar
`_ALVO_POR_CHAMADA`, aumente a variedade dos nichos.

## O que destrava volume, quando o dono quiser

`GOOGLE_CSE_KEY` + `GOOGLE_CSE_CX` (Google Programmable Search: 100 consultas
por dia grátis, API oficial, sem cartão). O provedor **já está escrito** em
`web_search._buscar_cse` e entra sozinho, na frente do DuckDuckGo, assim que
as duas variáveis existirem — zero linha de código a mais. Habilitar billing
na chave do Gemini ressuscitaria o grounding, mas é a opção cara e não é
necessária.

---

**Status em 2026-09-21: implementado.** `aluno/backend/acquisition_research.py`
existe e está integrado a `influencers.py`/`influencers_routes.py`/
`AdminInfluencers.jsx` — sem sistema paralelo, sem aba nova no produto do
aluno. O que segue descreve o desenho ANTIGO em vários pontos; onde ele fala
de `generate_grounded_json`, leia as seções acima.

**Uma divergência do desenho original, deliberada:** a implementação NÃO usa
`response_schema` tipado do `google-genai` — usa `response_mime_type=
"application/json"` (igual ao resto de `ai_service.py`) e valida o resultado
em Python com um modelo Pydantic próprio (`acquisition_research.LeadDescoberto`,
`extra="forbid"`), descartando qualquer candidato que não bata. Mesmo efeito
prático (allowlist de schema, não blocklist), mas sem introduzir um segundo
padrão de chamada — `_extract_json` continua sendo a única rede de segurança
de parsing deste arquivo, como já era.

## Onde cada peça mora

- **`aluno/backend/ai_service.generate_grounded_json`** — a ÚNICA função do
  projeto com `tools=[types.Tool(google_search=types.GoogleSearch())]`.
  Devolve `(json, fontes)`; `fontes` vem de
  `grounding_metadata.grounding_chunks[].web.uri`, nunca do texto que o
  modelo escreveu.
- **`acquisition_research.descobrir_leads(db, plataforma, nicho, alvo)`** —
  uma chamada em lote, valida schema + domínio + cruza contra `fontes`,
  devolve `(validados, rejeitados)`. `rejeitados` existe para o resumo da
  rodada poder dizer ONDE um déficit veio, nunca esconder.
- **`acquisition_research.executar_rodada_descoberta(db, admin_email=...)`**
  — orquestra a matriz (plataforma × nicho), dedup contra o banco
  (`influencers.ja_existe`) E contra o que a própria rodada já gravou, insere
  via `influencers.criar_lead`, registra `growth_events` tipo
  `acquisition_research_run` (auditoria — pedido do agente `security`).
- **`acquisition_research.gerar_mensagem_personalizada(db, influencer_id)`**
  — sob demanda, um lead por vez, nunca em lote. Recebe só campos
  estruturados já persistidos (nunca `justificativa_ia` bruta). Muda o
  status para `mensagem_pronta` quando o lead ainda estava em `lead`/
  `qualificado`.
- **Rotas** (`influencers_routes.py`): `POST /admin/influencers/pesquisar`
  (rate limit próprio, `rate_limit.LIMITES["pesquisa_aquisicao"]`, 6/hora por
  admin) e `POST /admin/influencers/{id}/mensagem-ia` (120/hora — mais barato
  por chamada). `GET /admin/influencers` ganhou filtros
  (`plataforma`/`nicho`/`prioridade`/`busca`/`incluir_descartados`) e
  paginação (`skip`/`limit`). `DELETE /admin/influencers/{id}` é o caminho
  manual de remoção exigido pela seção LGPD de [[afiliados]] — apaga de
  verdade, diferente de `status=removido`, e recusa se o influencer já tem
  comissão lançada (registro financeiro).
- **Modelo de dados**: novos campos em `models.Influencer` (`url`, `foco`,
  `localizacao`, `sinais_publicos_relevancia`, `tipo_audiencia`,
  `potencial_parceria`, `justificativa_ia`, `prioridade`, `confianca`,
  `fontes`, `url_normalizada`, `descoberto_em`, `mensagem_gerada`,
  `observacao`, `descartado`, `base_legal`, `finalidade`) — mesma coleção
  `influencers`, `origem="pesquisa_ia"` é o que distingue um lead do
  Pesquisador de um lead manual. Novo status `mensagem_pronta` no pipeline
  (entre `qualificado` e `contato`).
- **Dedup**: `influencers._normalizar_url`/`ja_existe` (checagem
  determinística antes de gravar) + índice único parcial no Mongo
  (`db_indexes.py`, `influencers_url_unica`, só sobre documentos com
  `url_normalizada`).
- **Telemetria de custo**: `db.acquisition_llm_chamadas` via
  `llm_telemetry.persist`, em TODA chamada (descoberta E mensagem) — mesmo
  padrão de `mentis_llm_chamadas`. Classificada em
  `dados_pessoais.COLECOES_SEM_DADO_PESSOAL`.
- **Testes**: `tests/test_acquisition_research.py` (32 testes) — descoberta,
  rejeição de domínio fora da allowlist, injeção de campo extra descartada,
  confiança rebaixada quando a CHAMADA inteira não retorna fonte nenhuma,
  dedup entre rodadas e dentro da mesma chamada, filtros, geração de
  mensagem sob demanda, sanitização de campo antes de reinjeção, transições
  de status, remoção manual vs. descarte, guardrail textual contra qualquer
  SDK de envio de mensagem.

## O achado técnico que importa reter

O **`google-genai` (SDK Python instalado: 2.18.1, `requirements.txt` pede
`>=2.12.1`) suporta `types.Tool(google_search=types.GoogleSearch())`** em
`GenerateContentConfig(tools=[...])` — confirmado inspecionando
`types.Tool.model_fields` (tem `google_search`) e `types.GoogleSearch` no SDK
instalado.

**Historicamente (Gemini 1.5/2.x) grounding e `response_mime_type=
"application/json"` eram MUTUAMENTE EXCLUSIVOS** — a API rejeitava com "Search
Grounding can't be used with JSON/YAML/XML mode" (erro 400). **Isso mudou nos
modelos Gemini 3** — que é exatamente o par que `ai_service.py` usa hoje
(`DEFAULT_MODEL = "gemini-3-flash-preview"`, fallback `gemini-3.5-flash"`): a
documentação oficial (ai.google.dev/gemini-api/docs/gemini-3) afirma que
Gemini 3 combina Structured Outputs com `google_search`, `url_context`, code
execution e function calling na mesma chamada. Ou seja: **`tools=
[types.Tool(google_search=...)]` + `response_mime_type="application/json"` +
`response_schema` devem funcionar juntos**, sem precisar do contorno de "pedir
JSON num bloco de código e extrair com regex" — mas como isto não foi testado
com uma chamada real (sem rede/chave neste ambiente), a primeira implementação
deve manter `_extract_json` como rede de segurança de qualquer forma (já é o
padrão do arquivo) e não assumir sucesso cego do `response_mime_type` estrito
sem medir a primeira chamada real.

**CORRIGIDO em 2026-09-21 (revisão do agente `ai`) — a ideia abaixo estava
ERRADA e o código de fato tinha esse bug.** A hipótese inicial era comparar
`lead.url` (ex. `instagram.com/perfil`) contra
`grounding_chunks[i].web.uri` para confirmar por item. **Isso nunca pode
funcionar**: a Gemini API devolve `web.uri` como um link de REDIRECIONAMENTO
do próprio Google (`vertexaisearch.cloud.google.com/grounding-api-redirect/
...`), nunca a URL final da página — os dois domínios são estruturalmente
diferentes, a comparação falha sempre, incondicionalmente, para todo lead. O
efeito no código antigo era pior que não ter o campo: `confianca` chegava
"baixa" para 100% dos leads, sempre, inclusive achados reais — ensinando o
admin a ignorar o campo, o oposto do que o pedido original queria.

**O que o código faz hoje** (`descobrir_leads`, `acquisition_research.py`):
o sinal é por CHAMADA, não por item — se a chamada inteira não retornou
nenhuma fonte de grounding (`fontes` vazio), a busca não achou nada real e
TODOS os candidatos daquela chamada são rebaixados para `"baixa"`; se
retornou pelo menos uma fonte, a confiança fica a que o próprio modelo
atribuiu. Não existe hoje, na API pública, correlação confiável **por
candidato individual** dentro de uma chamada em lote — só por chamada
inteira (via `grounding_supports`, que mapeia índices de caractere da saída
NARRATIVA para chunks; não é garantido sobreviver com `response_mime_type=
"application/json"` compacto). Isso é uma limitação aceita, documentada, não
escondida — é mais honesto que fingir uma verificação por item que a API não
oferece.

## Prompt injection: o design que protege

O conteúdo que o `google_search` indexa é **dado não confiável** — uma página
adversarial pode conter texto tentando mudar a instrução do modelo. Três
camadas de defesa, nenhuma delas é "pedir educadamente para o modelo
ignorar":

1. **Validação de schema é allowlist, não sanitização de blocklist.** Campo
   fora do schema esperado (`LeadDescoberto`, `extra="forbid"`) é descartado
   no parse, silenciosamente — nunca logado como erro que alguém "conserta"
   aceitando o campo.
2. **URL é revalidada contra domínio esperado** (`instagram.com`,
   `chat.whatsapp.com`, `t.me`), nunca aceita só porque o JSON parseou.
3. **`justificativa_ia` nunca é reinjetada numa segunda chamada de IA** —
   `gerar_mensagem_personalizada` não a inclui. **Correção de 2026-09-21
   (revisão do agente `security`): esta era a única exclusão real; os
   outros campos textuais que o Gemini extrai de uma página pública
   (`nicho`, `foco`, `tipo_audiencia`, `sinais_publicos_relevancia`)
   SOBREVIVEM e são reinjetados** — o docstring do módulo chegava a
   sugerir o contrário. A mitigação real agora é `_sanitizar_campo`
   (colapsa espaço, remove o literal do delimitador `<dado_do_lead>`/
   `</dado_do_lead>`, trunca a ~120 caracteres por campo) — profundidade
   adicional, não uma garantia estrutural. **A barreira que de fato
   importa continua sendo**: saída final capada em 600 caracteres, sem
   link, e a mensagem NUNCA é enviada automaticamente — sempre lida e
   copiada por um admin antes de ir a uma pessoa real.

## Chamadas de uma rodada completa (matriz real)

`acquisition_research.NICHOS_PADRAO_*` fixa 5 nichos de Instagram (ENEM
geral, Fuvest/Unicamp, Medicina, estudantes de Medicina que produzem
conteúdo, professores/educadores independentes) × 12 alvo por chamada, 2
nichos de WhatsApp × 8 e 2 de Telegram × 8 — **9 chamadas de descoberta por
rodada padrão**, com folga sobre o mínimo pedido (40/10/10) para absorver
perda por validação de domínio/fonte. **Geração de mensagem personalizada é 0
chamadas em lote — 1 chamada sob demanda, só quando o admin clica em um lead
específico.** Não é uma suposição arquitetural: é o padrão que a Mentis já
usa (dossiê montado uma vez, nunca por evento) ver [[mentis]] `As cinco
decisões de economia de tokens`.

## Limitações conhecidas (honestas, não escondidas do admin)

- **Não garante os mínimos pedidos (40/10/10) toda vez.** Se fontes públicas
  verificáveis não renderem candidatos suficientes, `executar_rodada_
  descoberta` devolve exatamente quanto achou e um aviso explícito — nunca
  completa o número inventando. WhatsApp em particular tem pouca superfície
  pública indexável pelo Google (grupos raramente aparecem bem), então é a
  plataforma mais provável de ficar abaixo do mínimo numa única rodada;
  rodar de novo (a dedup impede duplicar) tende a somar mais leads ao longo
  do tempo.
- **`response_schema` tipado não foi usado** (ver nota no topo do nó) —
  validação é Pydantic pós-parse, não imposta pela própria API. Efeito
  prático equivalente, mas se o `_extract_json` falhar em extrair QUALQUER
  JSON da resposta (texto fora do formato pedido), a chamada inteira devolve
  zero leads em vez de recuperar parcialmente.
- **Retenção de 24 meses (seção LGPD de [[afiliados]]) não está implementada
  como job automático** — é recomendação do agente `legal-privacy`,
  pendente de confirmação do dono antes de virar código.

## Tabela do CRM — consolidada em 2026-09-21

`AdminInfluencers.jsx` continua sendo cards, não `<table>` HTML — nenhuma
outra tela de Admin usa `<table>` (confirmado por busca no repo), e a
arquitetura existente é o que o pedido de rebranding mandou reutilizar. O
que mudou foi o CONTEÚDO de cada card: colunas explícitas em grid (Lead ·
Plataforma · Nicho · Audiência · Relevância · Prioridade · URL · Status ·
Última ação), prévia da mensagem gerada + botão de copiar direto na linha
(sem precisar abrir o card), e filtro de nicho (o backend já aceitava o
parâmetro, só não estava exposto na tela — lista de nichos vem da UNIÃO dos
que já apareceram nos resultados, não de um enum hardcoded). "Relevância" é
`confianca` (o quão confiável é a identificação, do Pesquisador IA);
"Prioridade" continua sendo a classificação separada. Rótulo do status
`lead` mudou de "Novo" para "Pendente" (só copy, `STATUS_LEAD` continua
`"lead"` no banco). A ordenação já existia — `influencers.priorizar()`, que
o `GET /admin/influencers` já aplicava por padrão (tamanho + estágio do
funil) — não precisou de UI nova.

Relacionado: [[mentis]] · [[afiliados]] · [[economia-de-sparks]] · [[custo-de-leitura]]
