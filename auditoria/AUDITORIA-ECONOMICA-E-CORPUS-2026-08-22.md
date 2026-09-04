# Auditoria econômica + auditoria do corpus — lote ENEM 2023 D2 Caderno Amarelo

**Registrado em:** 2026-08-22
**Natureza:** registro de execução (leitura + análise). Sob GOV-1.0 §1.1, `auditoria/` não cria norma.
**Escopo:** o lote de 90 questões processado hoje via `pipeline/backend`, endpoint `/book/{id}/process`, entre 08:02 e 08:47 (horário local, UTC-3). Nenhum dado foi alterado, nenhuma questão foi reprocessada, nenhuma chamada ao Gemini foi feita para produzir este relatório.

**⚠️ Achado de segurança fora de escopo, mas urgente:** durante esta auditoria, ao inspecionar `pipeline/backend/.env`, um filtro de redação mal escrito neste próprio processo imprimiu a `GEMINI_API_KEY` completa em texto puro no transcript desta conversa. **Recomendo revogar essa chave no Google AI Studio agora** e gerar uma nova, independentemente do restante deste relatório.

---

## Como cada número foi obtido

Para que nenhum número abaixo seja tratado como mais confiável do que é:

| Fonte | O que forneceu | Confiabilidade |
|---|---|---|
| `mongosh` sobre `sapiens_pipeline` (Mongo local) | Contagens exatas de itens, campos, distribuições — dado primário, consultado ao vivo, somente leitura (`find`/`aggregate`) | Alta — são os documentos realmente persistidos |
| `pipeline/backend/_storage/.../questions/` (filesystem) | Timestamps de criação, tamanho e nº de páginas do PDF original | Alta — metadados de arquivo, não alterados |
| Código-fonte (`cognitive_engine.py`, `gemini_cache.py`, `gemini_batch.py`, `batch_queue.py`, `server.py`, `settings.py`) | O que o pipeline **de fato** faz — não o que a documentação descreve que ele faz | Alta — é o código que rodou |
| `ai.google.dev/gemini-api/docs/pricing` (consultado agora, via busca) | Preços oficiais por 1M tokens do `gemini-3-flash-preview` | Alta para o preço-lista; **não é o extrato de cobrança real do projeto** |
| Cotação USD/BRL de hoje (~5,14) | Conversão de USD para BRL nas projeções | Aproximada — câmbio varia ao longo do dia |
| `.logs/pipeline-backend.log` | — | **Inútil para este lote**: o arquivo foi rotacionado/reiniciado às 03:33, antes do lote (08:02–08:47) começar. Contém só o boot do processo, nada da execução real |
| Tokens de entrada/saída/pensamento reais por chamada | — | **Indisponível.** O código nunca lê nem persiste `response.usage_metadata` em lugar nenhum. Ver §1.6 |

---

# 1. AUDITORIA ECONÔMICA

## 1.1 O que o lote realmente foi

- **90 questões solicitadas**, do caderno ENEM 2023, 2º dia, **Prova Amarela** (`2023_PV_impresso_D2_CD5.pdf`, 32 páginas, 3,85 MB, PDF escaneado/impresso — não é PDF de texto nativo).
- **89 processadas com sucesso** e persistidas em `sapiens_pipeline.pipelines` (confirmado por contagem direta no Mongo).
- **1 com erro de timeout**, conforme relatado — consistente com o timeout de cliente de **300.000 ms (5 min)** configurado em `BookResults.jsx:104,169`. Não há registro de qual questão foi, nem da causa exata do lado do servidor (o log já não existe).
- Todas as 89 pertencem ao mesmo `book_id`, sem duplicatas de `question_number` — nenhuma questão foi processada duas vezes e faturada duas vezes.
- Todas as 89 carregam `schema_version: "2.2"` e `ontology_version: "1.4.1"` corretamente.

## 1.2 Como as chamadas foram feitas — achado central

O endpoint usado foi `POST /api/book/{book_id}/process`, **um por questão**. Cada chamada:

```python
# server.py:962-973
incoming = await _load_book_files(book)          # relê o PDF INTEIRO do storage
files_bytes = [(n, d) for n, d, _ in incoming]
...
raw = await run_cognitive_pipeline(
    ontology, files_bytes, focus_hint=focus_hint, schema=schema,
    cache_collection=db.gemini_caches,
)
```

Confirmado no filesystem: **o PDF de 32 páginas e 3,85 MB inteiro está copiado, byte-idêntico, dentro da pasta de artefato de cada uma das 89 questões** (`original/2023_PV_impresso_D2_CD5.pdf`, mesmo tamanho em todas). Não existe fatiamento por questão, nem upload único reutilizado via Gemini Files API — é o PDF completo, em base64 inline, **em cada uma das 89 chamadas**. O único mecanismo que reduz o que é reenviado é o `focus_hint` textual ("Questão nº 92") pedindo ao modelo para *ignorar* as demais questões do documento — isso não reduz tokens de entrada, só instrui o modelo sobre o que responder.

A fila de lote com retry/backoff (`batch_queue.py`, `pipeline_queue`) **não foi usada neste lote** — a coleção `pipeline_queue` não existe no banco. O caminho realmente executado foi o síncrono, disparado pelo frontend com `runInParallel(tasks, concurrency=3)` (`BookResults.jsx:40,115`): **até 3 questões em paralelo**, cada uma sua própria chamada HTTP → sua própria chamada Gemini.

Isso também explica o comportamento relatado ("atualizei a página e o backend continuou processando"): o loop que dispara as chamadas roda no navegador, mas cada requisição HTTP já aceita pelo `uvicorn` **continua executando no servidor mesmo se o cliente desconectar** — não há checagem de `request.is_disconnected()` em nenhuma das rotas do pipeline. Um refresh não cancela trabalho já em andamento no servidor; só interrompe o disparo de novas chamadas a partir daquela aba.

## 1.3 Cache: existe, funcionou, mas nunca foi o problema

Existe exatamente **1 documento** em `gemini_caches`:

```
_id: bb98f670d98a93b4b9a6d36e47ad6cce52eb0781
created_at: 2026-08-22T11:02:17 UTC  (08:02:17 local)
expire_time: 2026-08-22T12:02:18 UTC (TTL de 1h)
model: gemini-3-flash-preview
```

O primeiro item do Mongo foi criado às `11:02:46 UTC` — 29s depois. Como o TTL de 1h cobre toda a janela do lote (08:02–08:47 local), **as 89 chamadas plausivelmente reutilizaram o mesmo cache**, exatamente como o código pretende (`gemini_cache.get_or_create_cached_content`, chamado nos 3 pontos de `server.py` que invocam `run_cognitive_pipeline`, todos passando `cache_collection=db.gemini_caches`).

O que é cacheado: **só o prompt de sistema + o texto da ontologia** (`system_instruction` + `ontology_text`), medido em `~9.811 + ~24.030 = ~33.841` caracteres (~8.450 tokens, aproximação de 4 char/token). **O PDF não entra no cache** — `_build_inline_request`/`run_cognitive_pipeline` sempre reenviam os `files_bytes` como parte nova da chamada, nunca como `contents` do `cachedContent`.

Ou seja: o cache está corretamente implementado e correto para o que ele cobre, mas **o que ele cobre (~8.450 tokens) é uma fração pequena do que domina o custo real da chamada** (ver §1.5). Descartar a hipótese "cache não funcionou" — funcionou; só não ataca o componente caro.

## 1.4 Preço-lista oficial do modelo usado

`GEMINI_MODEL=gemini-3-flash-preview` no `.env` — **não** é o Flash 2.0/2.5 "barato" que provavelmente embasou a estimativa original de US$0,50–1,00/200 questões. É a linha de **modelo preview da geração 3**, com preço de tier pago (o header do módulo até documenta um `DEFAULT_MODEL` incorreto — `"gemini-3.1-pro-preview"` no docstring, `"gemini-3-flash-preview"` na constante real; inconsistência cosmética, não afetou este lote porque a env var está explícita).

Preço oficial consultado agora em `ai.google.dev/gemini-api/docs/pricing` [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing), tier pago (o único compatível com uma cobrança real de R$28 — o tier gratuito é `"Free of charge"` para tudo, o que não gera fatura):

| Item | Preço (tier pago, chamada padrão) |
|---|---|
| Entrada (texto/imagem/vídeo) | US$ 0,50 / 1M tokens |
| **Saída — inclui tokens de "thinking"/raciocínio** | **US$ 3,00 / 1M tokens** |
| Cache — leitura | US$ 0,05 / 1M tokens |
| Cache — armazenamento | US$ 1,00 / 1M tokens/hora |
| Batch API — entrada / saída | US$ 0,25 / US$ 1,50 por 1M (não usado neste lote — ver §1.2) |

Tokenização de PDF documentada: **258 tokens por página** para páginas renderizadas como imagem (caso deste PDF escaneado) [Document understanding](https://ai.google.dev/gemini-api/docs/document-processing).

## 1.5 O achado que explica a discrepância: "thinking" nunca foi configurado

`gemini-3-flash-preview` **tem "thinking" ligado por padrão, no nível "high"** — a busca à documentação e ao fórum de desenvolvedores do Gemini confirma isso explicitamente para este modelo preview. O parâmetro que controla isso é `thinking_level` (substituiu `thinking_budget` na família Gemini 3).

Busca no código inteiro do pipeline por esse parâmetro:

```
grep -rn "thinking" cognitive_engine.py settings.py server.py gemini_batch.py gemini_cache.py
→ zero ocorrências
```

**Nenhuma chamada do pipeline jamais configura `thinking_level` nem `max_output_tokens`.** O `config_kwargs` de toda chamada (`cognitive_engine.py:462-467`) contém só `response_mime_type`, `temperature=0.2` e, quando aplicável, `cached_content`. Isso significa que **as 89 chamadas rodaram no nível de raciocínio mais caro disponível, por omissão, sem que ninguém tivesse decidido isso** — e como o preço de saída ($3,00/1M) **inclui os tokens de pensamento**, e nenhum lugar do código lê ou grava `response.usage_metadata`, esse custo é gerado, cobrado e **completamente invisível** a qualquer log ou documento do sistema.

### Reconstrução quantitativa (estimativa, não medição)

Com os números confirmados acima:

| Componente | Cálculo | Custo estimado |
|---|---|---|
| Cache (armazenamento, ~8.450 tokens × ~1h) | 8.450 × $1,00/1M | ≈ US$ 0,008 |
| Cache (leitura, 89 chamadas × ~8.450 tokens) | 89 × 8.450 × $0,05/1M | ≈ US$ 0,038 |
| PDF sem cache (89 × 32 páginas × 258 tok/página) | 743.150 × $0,50/1M | ≈ US$ 0,372 |
| **Subtotal — tudo que o pipeline "sabe" que está enviando** | | **≈ US$ 0,42 (≈ R$ 2,16)** |
| Total real cobrado (relatado) | R$ 28 ÷ ~5,14 | ≈ US$ 5,45 |
| **Resíduo não explicado por entrada/cache** | | **≈ US$ 5,03 (≈ R$ 25,84)** |

O único componente de preço restante é **saída + thinking, a $3,00/1M**. US$ 5,03 ÷ $3,00 por 1M ÷ 89 chamadas ≈ **~18.800 tokens de saída+pensamento por chamada, em média**. O JSON visível de uma anotação típica (ver amostra em §2) tem tipicamente 1.000–2.500 tokens de saída — o que sobra, **~16.000–17.500 tokens por chamada**, é consistente com uma cadeia de raciocínio interna em nível "high", nunca limitada, nunca contabilizada.

**Conclusão da reconstrução:** o subtotal de entrada/cache (~R$ 2,16) bate quase exatamente com a expectativa original do usuário para este lote (~R$ 2). **O excedente de ~R$ 25,84 é explicado, com alta plausibilidade, por tokens de "thinking" descontrolados** — não por ausência de cache, não por reprocessamento em modo individual em vez de Batch (Batch nem está disponível no tier gratuito, e não teria mudado o nível de thinking), e não por retries duplicados (sem evidência de duplicação — ver §1.2).

## 1.6 O que NÃO pôde ser reconstruído, e exatamente por quê

Cumprindo a exigência de não aceitar estimativa superficial sem dizer o que falta:

| Métrica pedida | Disponível? | Por quê / onde deveria estar |
|---|---|---|
| Tokens de entrada totais (reais) | **Não** | `_generate_json` (`cognitive_engine.py:470-483`) descarta `resp.usage_metadata` — só lê `resp.text`. Precisaria ser adicionado ao código e persistido por chamada. |
| Tokens de saída totais (reais) | **Não** | Mesmo motivo. |
| Tokens de "thinking" (reais) | **Não** | Mesmo motivo — e é o número mais importante que falta. |
| Tokens vindos de cache vs não-cacheados (reais) | **Não** | `usage_metadata.cached_content_token_count` existe na API mas nunca é lido. |
| Número total de chamadas à API | **Parcial** | 89 chamadas bem-sucedidas são inferíveis (1 doc Mongo = 1 chamada `generate_content` bem-sucedida, pela estrutura do código). A chamada que deu timeout não deixou rastro — não sabemos se ela chegou a completar do lado do Gemini (e ser cobrada) antes do cliente desistir aos 5 min. |
| Número de retries (SDK) | **Não** | O cliente Gemini tem retry nativo automático para 429/500/503/504 (`_get_client`, `attempts=6`, backoff exponencial) — **interno ao SDK, silencioso, sem logging**. Se alguma das 89 chamadas precisou de 2-3 tentativas internas por um 503 passageiro, isso é uma cobrança adicional (ou não, dependendo de onde a tentativa falhou) totalmente invisível aqui. |
| Chamadas que falharam e foram repetidas manualmente | **Não** (mas plausivelmente zero) | Não há duplicata de `question_number` no Mongo, e `pipeline_queue` (que teria histórico de tentativas) não existe. Se o usuário clicou "retry" em alguma questão após timeout, não sobrou registro de quantas vezes. |
| Custo por categoria (entrada/saída/thinking/cache) | **Parcial** | Só a parte de entrada/cache é reconstruível a partir do código+preço-lista (§1.5). Saída e thinking são inferidos por resíduo, não medidos. |
| Custo médio e mediano por questão | **Parcial** | Médio: R$ 28 ÷ 89 ≈ **R$ 0,315/questão** processada com sucesso (ou ÷90 ≈ R$ 0,311 se ratear a que deu timeout — não se sabe se ela foi cobrada). Mediano: **indisponível** — exigiria custo por chamada individual, que não existe. |
| Custo dos retries | **Não** | Depende do dado do SDK acima, indisponível. |

**Onde essas métricas deveriam ser coletadas, a partir de agora:**
1. **Google AI Studio → Billing / Google Cloud Console → APIs & Services → Gemini API → métricas de uso**: é a única fonte que tem o número real, por dia, por modelo, idealmente já discriminando tokens de entrada/saída/thinking/cache. É o extrato de cobrança em si — a fonte de verdade para "quanto custou de fato", que nenhum dado local pode substituir.
2. **No código**: `_generate_json` deveria persistir `resp.usage_metadata` (existe no SDK `google-genai`) em cada registro salvo em `pipelines`, ou em uma coleção separada `gemini_calls` com `prompt_token_count`, `candidates_token_count`, `thoughts_token_count`, `cached_content_token_count`, timestamp e `item_id`. Sem isso, esta reconstrução continuará sendo estimativa a cada novo lote.

## 1.7 Projeções

Usando o custo médio observado (R$ 0,315/questão bem-sucedida) e, separadamente, um cenário "otimizado" assumindo que travar `thinking_level` num nível baixo/médio e fatiar o PDF por questão eliminaria a maior parte do resíduo de §1.5 (mantendo uma margem de segurança — não é garantido que o nível baixo produza a mesma qualidade de anotação, ver §5 Plano de Ação):

| Nº de questões | Custo no ritmo observado hoje | Custo se otimizado (estimativa, ~80-90% de redução no componente de saída/thinking) |
|---|---|---|
| 200 | ≈ R$ 63 (≈ US$ 12,25) | ≈ R$ 8–13 (≈ US$ 1,6–2,5) — próximo da estimativa original de US$0,50–1 |
| 1.000 | ≈ R$ 315 (≈ US$ 61) | ≈ R$ 42–63 |
| 10.000 | ≈ R$ 3.150 (≈ US$ 612) | ≈ R$ 420–630 |
| 100.000 | ≈ R$ 31.500 (≈ US$ 6.124) | ≈ R$ 4.200–6.300 |

**Estas são extrapolações lineares de uma amostra de 89 questões de um único caderno de Matemática/Ciências da Natureza.** Outras disciplinas (mais texto corrido, ex.: Linguagens) ou cadernos com mais páginas mudam a base de entrada; a proporção de thinking pode variar com a dificuldade percebida pelo modelo. Tratar como ordem de grandeza, não como orçamento fechado.

---

# 2. AUDITORIA DO CORPUS

## 2.1 Conformidade estrutural (Schema 2.2)

- **85/89 (95,5%)** passam na validação estrutural do próprio pipeline (`validacao.valid: true`, produzida por `item_contract.validate` → `ontology_validator.py`).
- **4/89 (4,5%)** falham (`validacao.valid: false`), com estes erros exatos:

| item_id | Erro |
|---|---|
| `Q117` | 4× `distratores[i].erros_esperados[0].ordem: inteiro obrigatório` (campo ausente) |
| `Q122` | `peso_no_item` ausente em 2 processos + pesos não somam 1,0 (soma = 0,0) |
| `Q172` | Par `('ERR-06', 'PROC-MUD-01')` não existe no catálogo 1.4.1 — o modelo "emprestou" um tipo de erro de outro processo, proibido pelo Manual §7 regra 4 |
| `Q176` | `HAB-47` não é catalogada sob `PROC-TEXT-01` — habilidade errada para o processo |

Nenhum desses 4 é falha de código (o validador os capturou corretamente); todos são **o modelo emitindo um JSON estruturalmente incompleto ou com referência cruzada inválida ao catálogo**.

## 2.2 O achado mais grave desta auditoria: o campo que deveria proteger o futuro aluno está quebrado

`qualidade.apto_para_camada_de_crenca.valor` é, pela própria descrição do Schema 2.2, o sinal de que um item está pronto para alimentar a camada de crença do estudante. Cruzando com `validacao.valid`:

```
Q117 (inválido) → apto_para_camada_de_crenca: true, revisado: true
Q172 (inválido) → apto_para_camada_de_crenca: true, revisado: true
Q176 (inválido) → apto_para_camada_de_crenca: true, revisado: true
Q122 (inválido) → apto_para_camada_de_crenca: false, revisado: false
```

**3 dos 4 itens estruturalmente inválidos (75%) se autodeclaram prontos para a camada de crença.** O campo cujo único propósito é impedir que dado ruim chegue ao modelo cognitivo do aluno **erra exatamente nesse propósito, em 3/4 dos casos onde já se sabe, por outra via, que o item está quebrado.**

Além disso: `qualidade.revisado` e `qualidade.apto_para_camada_de_crenca.valor` **concordam em 89/89 itens, sem exceção** (60× `true`/`true`, 29× `false`/`false`, zero combinações cruzadas). Dois campos que o Schema apresenta como julgamentos distintos (um sobre revisão, outro sobre aptidão) se comportam como **um único bit mecânico**, não como duas avaliações independentes — evidência de que não há dois julgamentos reais acontecendo, e sim um valor sendo copiado ou derivado do outro.

## 2.3 Confiança: colapso quase total em um valor único

| Campo | Distribuição observada |
|---|---|
| `qualidade.confianca_global` | **0,7 em 89 de 89 itens (100%).** Nenhuma exceção. |
| `estrutura_cognitiva.processos[].confianca` | **0,7 em 145 de 146 ocorrências (99,3%)**; 1 única ocorrência em 0,4. |
| `distratores[].erros_esperados[].confianca` | Somente **3 valores discretos** em 298 ocorrências: 0,7 (177×), 0,4 (104×), 0,15 (17×) |

Isso não é "confiança frequentemente igual a 0,7" — é **confiança quase constante**. Um score de confiança que não varia entre 89 questões de dificuldade e ambiguidade claramente diferentes (a própria distribuição de `plausibilidade.valor` nos distratores varia: alta 70×, media 132×, baixa 88×) não está sendo calibrado por item — está sendo emitido como valor-padrão.

Os 3 valores discretos de `erros_esperados[].confianca` (0,7 / 0,4 / 0,15) mapeiam de forma suspeitosamente limpa sobre os 3 valores de `plausibilidade.valor` (alta / media / baixa). É consistente com a hipótese de que **`confianca` não é uma estimativa independente — é `plausibilidade` remapeada por uma tabela fixa de 3 valores**, o que violaria o próprio propósito declarado do campo (nota do item de amostra, §_estatuto: *"A única relação ponderada com valor diagnóstico neste contrato é `distratores[].erros_esperados[].confianca`"*). Isto é uma hipótese testável com uma junção direta por item — não confirmada aqui com certeza, mas fortemente sugerida pela coincidência dos valores e pela ausência de qualquer valor intermediário nas 298 ocorrências.

Isso ameaça diretamente o "Axioma da Crença Calibrada" citado nos próprios documentos normativos: uma confiança que não varia não é uma confiança.

## 2.4 `requer_arbitragem`: nunca acionado, mesmo quando o próprio item sinaliza incerteza

- `incerteza.requer_arbitragem`: **false em 89 de 89 itens — 100%, sem exceção.**
- Ao mesmo tempo, **35 de 89 itens (39,3%)** carregam ao menos 1 marcador em `incerteza.marcadores` (39 ocorrências: 28× `erro-nao-catalogado-nesta-versao`, 11× `aproximado`).
- O próprio Schema 2.2 define `erro-nao-catalogado-nesta-versao` como sinal de que **"o `processo_afetado` não tem Tipo de Erro no catálogo"** — uma fronteira que a ontologia mantém literalmente em aberto (13 dos 25 processos na v1.4.1 não têm tipo de erro catalogado). Pela própria definição de `requer_arbitragem` no Schema (*"verdadeiro quando a incerteza envolve fronteira que a ontologia mantém em aberto"*), este é exatamente o caso em que o campo deveria ser `true`. Ele nunca é.

**Duas hipóteses, não mutuamente exclusivas:** (a) o modelo aprendeu a preencher `marcadores` (task mais "de superfície": listar sinais) mas nunca conecta esse sinal ao booleano `requer_arbitragem` (task mais "de julgamento": decidir se isso importa) — um atalho de prompt clássico; (b) o prompt nunca amarra explicitamente as duas coisas, deixando a decisão a critério do modelo, que converge para "não" por padrão. De qualquer forma, **a fila de arbitragem de governança que este campo deveria alimentar está, na prática, vazia — 0 itens — apesar de 39% do lote carregar incerteza registrada.**

## 2.5 Vocabulário de incerteza: 5 de 7 valores nunca usados

O Manual e o Schema 2.2 definem 7 marcadores possíveis para `incerteza.marcadores`. Nos 89 itens, apenas 2 aparecem:

| Marcador | Usado? |
|---|---|
| `erro-nao-catalogado-nesta-versao` | ✅ 28× |
| `aproximado` | ✅ 11× |
| `candidato-secundario-incerto` | ❌ nunca |
| `sem-mecanismo-cognitivo-identificavel` | ❌ nunca *(usado 6× como valor de `erro`, mas nunca refletido aqui)* |
| `ambiguidade-fronteira` | ❌ nunca |
| `item-nao-classificavel` | ❌ nunca |
| `tres-ou-mais-processos-necessarios` | ❌ nunca |

Consistente com isso: **nenhum item usa mais de 2 processos cognitivos** (32 itens com 1, 57 com 2, zero com 3+) — o teto de "máx. 2 processos" do Manual está sendo respeito à risca, mas o marcador que existiria para sinalizar "esse teto está me impedindo de descrever este item direito" nunca dispara. Não dá para saber, sem leitura pedagógica item a item, se isso é porque nenhuma das 89 questões realmente precisava de um 3º processo, ou porque o modelo nunca considera essa saída.

## 2.6 A sentinela `erro-nao-catalogado-nesta-versao` é usada mais que qualquer erro real — e é mal-usada em 1 a cada 6 vezes

Distribuição de `distratores[].erros_esperados[].erro` (318 ocorrências, 89 itens):

| Valor | Ocorrências |
|---|---|
| **`erro-nao-catalogado-nesta-versao`** | **123** |
| `ERR-03` | 35 |
| `ERR-01` | 25 |
| `ERR-02` | 22 |
| `ERR-13` | 22 |
| `ERR-06` | 21 |
| `ERR-07` | 15 |
| `ERR-04` | 13 |
| `ERR-05` | 9 |
| `ERR-10` | 7 |
| `sem-mecanismo-cognitivo-identificavel` | 6 |
| `ERR-08`, `ERR-09`, `ERR-11`, `ERR-12` | **0 — nunca usados** |

A sentinela sozinha (123) é usada **mais que o dobro** do tipo de erro real mais comum (`ERR-03`, 35). O validador do próprio pipeline confirma que isso não é só um padrão estatístico neutro: **22 dessas 123 ocorrências (17,9%), espalhadas por 10 itens distintos, são uso indevido confirmado** — a sentinela aplicada a um processo que *tem* tipo de erro catalogado (ex.: `PROC-QUANT-02` com `ERR-05` disponível, `PROC-CAUSAL-01` com `ERR-07`/`ERR-08` disponíveis). Isso é registrado como **warning**, não como erro bloqueante — por isso os 10 itens ainda aparecem como `validacao.valid: true`, mascarando o problema de uma leitura superficial da taxa de conformidade.

`ERR-08` é um exemplo direto: catalogado e disponível para `PROC-CAUSAL-01` (o mesmo processo que usou `ERR-07` 15 vezes), e **nunca escolhido uma única vez** nos 89 itens. Consistente com um modelo que, diante de ambiguidade entre dois erros próximos do mesmo processo, converge sistematicamente para um e evita o outro — ou converge para a sentinela de "sem catálogo" em vez de investigar qual dos dois se aplica.

## 2.7 Cobertura da ontologia — processos, domínios, competências nunca usados

De 25 processos cognitivos catalogados na v1.4.1, **6 nunca aparecem** nas 89 questões: `PROC-QUANT-03`, `PROC-INC-01`, `PROC-INC-03`, `PROC-LOGICO-01`, `PROC-EXP-01`, `PROC-EXP-02`. Correspondentemente, **`DOM-LOGICO` e `DOM-EXPERIMENTAL`** (2 de 11 domínios) e **`COMP-07` e `COMP-10`** (2 de 12 competências) também nunca aparecem.

**Ressalva importante:** isto é uma amostra de 89 questões de **um único caderno** (Matemática + Ciências da Natureza, ENEM dia 2). É plausível que processos como `PROC-EXP-01`/`PROC-EXP-02` (provavelmente ligados a raciocínio experimental) e `PROC-LOGICO-01` estejam de fato sub-representados no conteúdo real dessas 89 questões, não necessariamente por viés do modelo. **Não é possível separar, com esta amostra, "o modelo evita esses nós" de "essas 89 questões não pedem esses processos"** — isso exigiria um lote de controle (outro caderno, outra disciplina) ou revisão pedagógica manual de uma amostra dos itens. Fica como item de verificação, não como conclusão fechada.

O que já é mais forte, dentro dos processos efetivamente usados: `PROC-QUANT-02` (20×) e `PROC-TEXT-01` (17×) concentram uma fração desproporcional das 89 questões, o que pode refletir tanto o conteúdo real do caderno quanto uma tendência do modelo a convergir para os processos "mais fáceis de justificar" quando há ambiguidade.

## 2.8 Campos sistematicamente vazios ou subutilizados

| Campo | Estado |
|---|---|
| `distratores[].probabilidade_estimada` | Preenchido em **31 de 290 (10,7%)**; nulo em 89,3%. O Schema 2.2 permite explicitamente que seja uma *estimativa do modelo* (distinta de medida empírica futura) — não está claro no Manual se o modelo deveria preenchê-lo sempre ou se é aceitável deixá-lo majoritariamente nulo até haver dado real de alunos. **Decisão conceitual pendente, não bug.** |
| `distratores[].erros_esperados[].mecanismo` | Ausente em **209 de 318 (65,7%)**. É campo declarado "opcional e provisório" no próprio Schema — comportamento esperado, não defeito. |
| `intervencoes[]` | Vazio (0 itens) em **24 de 89 (27%)** questões. Validador aponta, à parte, **4 casos** em que a intervenção existente aponta para um elo de erro que não é a raiz da cadeia (`ordem` ≠ 1), violando a Especificação de Error Trace §1.1 — a intervenção pedagógica, quando existe, às vezes mira o sintoma, não a causa raiz. |

## 2.9 O que está genuinamente correto

Para não distorcer o quadro para o pior — o que funcionou:

- **Versionamento**: 89/89 itens carregam `schema_version` e `ontology_version` corretos e consistentes.
- **`item_id` determinístico**: todos seguem o padrão `ITEM-{banca}-{ano}-{prova}-Q{nnn}`, sem colisões, sem IDs opacos — o defeito de alucinação de procedência documentado no lote anterior (`LOTE-ENEM-2023-D2-CD11.md`) não se repetiu aqui, porque a correção feita naquele momento (parâmetro `?fonte=` sobrescrevendo o modelo) está em uso via `banca`/`ano`/`prova` obrigatórios no upload do caderno.
- **Teto de 2 processos**: respeitado em 100% dos itens.
- **Nenhuma questão duplicada** ou reprocessada e contabilizada duas vezes.
- **`erro-nao-catalogado-nesta-versao` e `sem-mecanismo-cognitivo-identificavel` não são bugs** — são vocabulário legítimo e documentado do Schema 2.2/Manual; o problema não é a existência desses valores, é a **frequência e o uso incorreto** deles (§2.6).
- O validador estrutural (`ontology_validator.py`) está fazendo seu trabalho corretamente — pegou os 4 itens inválidos e as 22 más-utilizações da sentinela; o problema está no que passa *pela* validação, não na validação em si.

---

# 3. PADRÕES, NÃO SÓ ERROS INDIVIDUAIS — RESUMO QUANTIFICADO

| Padrão | Magnitude | Classificação |
|---|---|---|
| `confianca_global` constante em 0,7 | 89/89 (100%) | **Erro de prompt/modelo** — ausência de calibração real |
| `processos[].confianca` quase constante em 0,7 | 145/146 (99,3%) | **Erro de prompt/modelo** |
| `requer_arbitragem` nunca `true` apesar de incerteza registrada em 39% dos itens | 89/89 false | **Erro de prompt** — desconexão entre dois campos que deveriam ser lidos juntos |
| `revisado` ≡ `apto_para_camada_de_crenca` sem exceção | 89/89 | **Erro de prompt/código** — dois campos, um sinal |
| `apto_para_camada_de_crenca: true` em item estruturalmente inválido | 3/4 dos itens inválidos | **Erro de prompt/modelo, com impacto direto na integridade futura do corpus** |
| Sentinela `erro-nao-catalogado-nesta-versao` dominando o campo `erro` | 123/318 (38,7%) do campo, 22 delas (17,9%) confirmadas mal-usadas | **Erro de modelo (atalho de classificação)**, capturado parcialmente pelo validador |
| 5 de 7 marcadores de incerteza nunca usados | 71% do vocabulário ocioso | **Erro de prompt ou lacuna ontológica** — indistinguível sem mais dados |
| 6 de 25 processos, 4 de 13 erros nunca usados | 24%/31% do catálogo | **Possivelmente comportamento esperado** (amostra de 1 caderno) — requer lote de controle |
| Tokens de "thinking" nunca limitados nem medidos | 100% das chamadas | **Erro de código** — gap de configuração, não de prompt |
| `usage_metadata` nunca persistido | 100% das chamadas | **Erro de código** — lacuna de observabilidade |
| PDF completo reenviado a cada chamada, sem fatiamento nem File API | 89/89 chamadas | **Erro de código/arquitetura** — ineficiente mas não a causa principal do custo |

---

# 4. QUESTÕES CRÍTICAS — RESPOSTAS DIRETAS

- **`erro-nao-catalogado-nesta-versao`**: legítimo como vocabulário, mas usado 3,5× mais que o tipo de erro catalogado mais comum, com 17,9% de uso confirmado incorreto pelo próprio validador. Ver §2.6.
- **`requer_arbitragem: false` quando existe incerteza**: confirmado em 100% dos casos onde incerteza foi registrada (35/89 itens). A fila de arbitragem de governança está vazia por construção, não por ausência real de casos de fronteira. Ver §2.4.
- **Confiança frequentemente igual a 0,7**: subestimado no enunciado do pedido — é **quase universalmente** 0,7 (99,3%–100% conforme o campo). Ver §2.3.
- **`apto_para_camada_de_crenca: false`**: 29/89 (32,6%) — mas o problema maior não é a taxa, é que o campo **erra no sentido oposto** em 75% dos casos onde já se sabe que o item está quebrado (diz `true` quando deveria dizer `false`). Ver §2.2.
- **Divergência entre classificação e evidências**: não auditada exaustivamente item a item nesta passada (exigiria leitura pedagógica humana de 89 enunciados contra seus `evidencias.trechos`); a amostra lida manualmente (Q092, reproduzida acima) está coerente enunciado↔processo↔evidência. Recomenda-se amostragem humana antes de qualquer decisão de confiar no corpus.
- **Informação inferida pelo modelo que deveria ser determinada pelo sistema**: o caso mais claro é `qualidade.revisado`/`apto_para_camada_de_crenca` — comportam-se como um valor derivado mecanicamente, não como dois julgamentos. Se a intenção é que `revisado` seja um flag operacional (setado por humano depois, não pelo modelo na anotação inicial), o modelo não deveria estar preenchendo-o como `true` para 60 itens que nenhum humano revisou ainda.
- **Campo capaz de contaminar futuramente o modelo cognitivo do aluno**: `qualidade.apto_para_camada_de_crenca.valor`, exatamente pelo motivo do §2.2 — é o portão de entrada para a camada de crença, e o portão está com defeito de abertura falsa positiva.

---

# 5. RELATÓRIO FINAL

## A. Diagnóstico econômico

- **Custo real relatado**: R$ 28 para 90 questões solicitadas, 89 processadas com sucesso — **R$ 0,315/questão bem-sucedida**. Não há extrato de cobrança local para confirmar o número exatamente; é o valor informado.
- **Tokens**: entrada e cache são reconstruíveis pelo código (~8.450 tokens fixos cacheados + ~8.350 tokens/chamada de PDF não-cacheado). Saída e thinking **não são reconstruíveis com precisão** — só por resíduo (~18.800 tokens/chamada estimados, majoritariamente thinking).
- **Chamadas**: 89 bem-sucedidas confirmadas; 1 com timeout de cliente (destino real da chamada no servidor, desconhecido); retries internos do SDK, não instrumentados, portanto desconhecidos.
- **Cache**: implementado corretamente, coberto ~89/89 chamadas, custo desprezível (~R$ 0,24), nunca foi o problema.
- **Causa mais provável da discrepância**: `thinking_level` nunca configurado em um modelo preview cujo padrão é "high" — plausivelmente ~85-90% do custo total, com o reenvio do PDF completo (sem fatiamento) como segundo fator secundário (~7-13% do custo, mas 100% desnecessário arquiteturalmente).
- **Projeções**: ver tabela em §1.7. Ordem de grandeza: R$ 63 / R$ 315 / R$ 3.150 / R$ 31.500 para 200 / 1.000 / 10.000 / 100.000 questões no ritmo observado; potencialmente 1/5 a 1/8 disso com `thinking_level` controlado.

## B. Diagnóstico de qualidade

- **Taxa de conformidade estrutural**: 95,5% (85/89) — mas essa métrica sozinha esconde o problema real, porque passa itens com uso incorreto de vocabulário (warnings, não errors) e não captura a inconsistência de `apto_para_camada_de_crenca`.
- **Principais problemas, por item afetado**: colapso de confiança (89/89), arbitragem nunca acionada (89/89), campo de aptidão para camada de crença não confiável (75% de falso-positivo nos itens já sabidamente inválidos), sentinela de erro sobre-usada e mal-usada (10/89 itens com má-uso confirmado).
- **Exemplos concretos**: Q117, Q122, Q172, Q176 (inválidos); Q092 (bem formado, usado como amostra de referência ao longo deste relatório).

## C. Problemas sistêmicos — ranking por impacto

1. **`apto_para_camada_de_crenca` não é confiável** (§2.2) — impacto direto e imediato em qualquer decisão de usar o corpus atual para alimentar a camada de crença do aluno. Bloqueante para o objetivo declarado do usuário.
2. **`thinking` descontrolado e não instrumentado** (§1.5, §1.6) — impacto econômico direto; sem correção, cada lote futuro repete o mesmo padrão de custo, e continuará invisível até a fatura chegar.
3. **Colapso de confiança em 0,7** (§2.3) — corrompe silenciosamente qualquer uso futuro de confiança como sinal de incerteza real; sem isso, a camada de crença do aluno herdaria uma confiança que não significa nada.
4. **`requer_arbitragem` nunca acionado** (§2.4) — a fila de governança que deveria existir para revisar fronteiras da ontologia está vazia por construção, não por ausência real de casos.
5. **Sentinela de erro sobre-usada/mal-usada** (§2.6) — degrada a qualidade diagnóstica dos distratores em ~14% dos itens (10/89 já confirmados; possivelmente mais, dado que o validador só pega os casos onde o processo tem erro catalogado — casos de uso correto-mas-preguiçoso não são detectáveis automaticamente).
6. **PDF reenviado inteiro por chamada** (§1.2, §1.3) — ineficiência real, mas de impacto econômico secundário frente ao item 2; relevante principalmente em escala (10k+ questões).

## D. Diagnóstico arquitetural

**Correto:**
- Separação `annotation_pipeline.py`/`batch_queue.py` vs. rota síncrona antiga em `server.py` (decisão deliberada, documentada, para não arriscar regressão).
- Validador estrutural (`ontology_validator.py`) capturando exatamente o que deveria capturar.
- Cache explícito, com fallback seguro (nunca bloqueia a anotação) e invalidação automática em 404.
- `item_id` determinístico com procedência injetada pelo servidor, não inferida do modelo — correção efetiva de um defeito documentado no lote anterior.

**Precisa ser corrigido no código:**
- Configurar `thinking_level` explicitamente em toda chamada (`cognitive_engine.py:462-467`) — hoje ausente.
- Persistir `response.usage_metadata` (tokens de entrada/saída/thinking/cache) em cada `record` salvo em `pipelines`, ou em coleção própria — hoje ausente.
- Parar de reenviar o PDF completo por questão: fatiar por página antes da chamada, ou usar a Gemini Files API para upload único reaproveitado entre as N questões do mesmo caderno.
- Restaurar rotação/retenção de log persistente para `.logs/pipeline-backend.log` — o arquivo perdeu o histórico do próprio lote auditado.

**Precisa ser corrigido no prompt:**
- Amarrar explicitamente `incerteza.marcadores` → `incerteza.requer_arbitragem`: se o marcador indicar fronteira ontológica aberta (ex.: `erro-nao-catalogado-nesta-versao`), o prompt deveria instruir o modelo a setar `requer_arbitragem: true` por regra, não por julgamento livre.
- Reforçar a instrução de que `confianca` deve refletir incerteza real por item, não um valor-padrão — possivelmente pedindo explicitamente uma justificativa textual para o valor numérico escolhido, como já existe para `processos[].justificativa`.
- Esclarecer que `erro-nao-catalogado-nesta-versao` só é válido para os processos sem tipo de erro catalogado, e listar explicitamente, no prompt, quais processos são esses (em vez de deixar o modelo inferir da ontologia).

**Precisa ser corrigido no código E no schema/manual juntos:**
- `qualidade.revisado` deveria provavelmente **não ser preenchido pelo modelo** — é um campo de fluxo de revisão humana, não de anotação automática. Se o modelo estiver setando-o, o pipeline está simulando uma revisão que nunca aconteceu.

**Exige decisão conceitual (não é bug, é ambiguidade de especificação):**
- `distratores[].probabilidade_estimada`: o modelo deve estimá-lo sempre, ou ele deve ficar nulo até haver dado empírico real de alunos? Hoje está em um meio-termo inconsistente (10,7% preenchido).
- Os "13 dos 25 processos sem tipo de erro catalogado" — é aceitável que 38,7% dos distratores caiam na sentinela, ou isso sinaliza que a Ontologia 1.4.1 tem uma lacuna de cobertura de tipos de erro que deveria ser fechada antes de escalar o corpus?

## E. Economia futura

Ver tabela completa em §1.7. Resumo:

| Questões | Ritmo atual | Otimizado (thinking controlado + PDF fatiado) |
|---|---|---|
| 200 | ≈ R$ 63 | ≈ R$ 8–13 |
| 1.000 | ≈ R$ 315 | ≈ R$ 42–63 |
| 10.000 | ≈ R$ 3.150 | ≈ R$ 420–630 |
| 100.000 | ≈ R$ 31.500 | ≈ R$ 4.200–6.300 |

## F. Plano de ação — em ordem de prioridade

Começando pelo que compromete a validade dos dados ou a viabilidade econômica:

1. **Não processar novas questões até `thinking_level` estar configurado e `usage_metadata` estar sendo persistido.** Sem isso, qualquer novo lote repete exatamente este mesmo risco econômico, agora sabidamente evitável.
2. **Rotacionar a `GEMINI_API_KEY`** (achado de segurança desta sessão, independente do restante).
3. **Não tratar `apto_para_camada_de_crenca: true` como sinal confiável** até o prompt ser corrigido e o corpus atual ser revalidado — atualmente ele erra a favor de deixar passar itens ruins.
4. **Decidir e corrigir a desconexão `incerteza.marcadores` → `requer_arbitragem`** no prompt, para que a fila de arbitragem de governança volte a existir de fato.
5. **Investigar e corrigir o colapso de `confianca`** — sem isso, qualquer trabalho futuro de "camada de crença calibrada" herda um sinal que não carrega informação.
6. **Corrigir a má-utilização da sentinela `erro-nao-catalogado-nesta-versao`** no prompt, com a lista explícita dos processos sem catálogo.
7. **Decidir a política de `qualidade.revisado`** — modelo não deveria simular revisão humana.
8. **Otimizar a arquitetura de envio de PDF** (fatiamento por página ou Files API) — importante para escala, secundário frente aos itens acima.
9. **Restaurar retenção de log** para que a próxima auditoria não dependa de reconstrução via filesystem/Mongo.

## G. NÃO ALTERAR AINDA — preservado como evidência

- As **89 questões processadas** em `sapiens_pipeline.pipelines` (book_id `6ba5747b-1cfa-4428-b1cb-632b7a44eba1`) — inclusive as 4 marcadas como estruturalmente inválidas e os 10 itens com má-uso de sentinela confirmado. São a evidência primária deste relatório.
- Os artefatos originais em `pipeline/backend/_storage/sapiens-cognitive/questions/` (PDFs, extrações, JSONs de pipeline por questão).
- O documento único em `gemini_caches` (`bb98f670...`) — histórico do cache usado neste lote (expira sozinho; não precisa ação).
- **Nenhuma alteração de Schema 2.2, Ontologia 1.4.1, Manual de Anotação ou Constituição** foi proposta ou deve ser feita a partir só deste relatório — os itens da seção D marcados "decisão conceitual" exigem decisão do usuário, não implementação automática.
- O código do pipeline (`cognitive_engine.py`, `gemini_cache.py`, `gemini_batch.py`, `batch_queue.py`, `server.py`, `settings.py`) não foi modificado durante esta auditoria — só lido.

---

## Resumo para as duas perguntas que motivaram esta auditoria

**1. Quanto realmente custa produzir uma anotação cognitiva?**
Ao ritmo observado hoje: **≈ R$ 0,315/questão**, dos quais a maior parte (~85-90%, por reconstrução) é tokens de "thinking" nunca configurados nem medidos — não entrada, não cache, não retries. Com `thinking_level` controlado, a mesma anotação plausivelmente custaria uma fração disso (ordem de R$ 0,04–0,07/questão), muito mais próxima da estimativa original de US$0,50–1,00/200 questões.

**2. Essas anotações são confiáveis o suficiente para futuramente alimentar o modelo cognitivo dinâmico do estudante?**
**Ainda não.** O campo desenhado especificamente para responder essa pergunta por item (`apto_para_camada_de_crenca`) está, ele mesmo, comprovadamente não confiável — diz "sim" em 75% dos casos onde já se sabe, por validação estrutural independente, que o item está quebrado. Some-se a isso um sinal de confiança que não varia (99,3%–100% em 0,7) e uma fila de arbitragem que nunca é alimentada apesar de 39% dos itens carregarem incerteza registrada, e a conclusão é que **o corpus de 89 itens é uma base de teste válida para depurar o pipeline, mas não uma base pronta para decisão pedagógica sobre um aluno real.**
