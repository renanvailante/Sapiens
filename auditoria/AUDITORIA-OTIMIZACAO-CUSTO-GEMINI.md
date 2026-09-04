# Otimização econômica do pipeline Gemini — thinking_level + instrumentação + teste controlado

**Registrado em:** 2026-08-22
**Natureza:** implementação + verificação empírica. Sob GOV-1.0 §1.1, `auditoria/` não cria norma.
**Escopo:** exclusivamente econômico, conforme solicitado. Não altera Schema 2.2, Ontologia 1.4.1, Constituição, White Paper, regras cognitivas, nem a arquitetura do pipeline além do estritamente necessário para controlar `thinking` e medir custo por chamada.
**Pré-requisito lido antes de qualquer mudança:** `auditoria/AUDITORIA-ECONOMICA-E-CORPUS-2026-08-22.md` (auditoria anterior, que identificou o problema).

---

## 0. Resumo executivo

| Pergunta do pedido | Resposta |
|---|---|
| Meta: reduzir custo/questão em ≥10% | **Atingida, com folga larga.** MEDIUM (novo padrão): **~52% de redução projetada** sobre o custo real observado (R$0,315 → ~R$0,152/questão). LOW (disponível, não padrão): **~86%** (→ ~R$0,043/questão). |
| A qualidade da saída se manteve? | MEDIUM: sim, na amostra testada (8/8 estruturalmente válidas, igual a HIGH). LOW: 7/8 válidas na amostra — 1 falha do mesmo tipo que já existia no corpus de produção. Por isso **MEDIUM foi escolhido como padrão**, não LOW. |
| O que causava o custo? | Confirmado empiricamente, não só por reconstrução: `thinking` em HIGH (o padrão do modelo, nunca configurado antes) chegou a **62.913 tokens numa única chamada** — mais que o dobro do output visível — em 3 de 8 questões testadas, com chamadas de 223–288 segundos, perto do timeout de 5min do frontend. |
| Foi preciso mudar o prompt cognitivo, Schema, Ontologia? | Não. Nenhuma alteração fora do controle de `thinking_level` e da instrumentação. |
| Alguma decisão exigiu mudança conceitual? | Sim, uma — **não implementada, só relatada**: o campo `qualidade.apto_para_camada_de_crenca` não é decidido pelo modelo em nenhuma configuração de thinking — é **sobrescrito por código** (`item_contract.py:210`) para sempre copiar `qualidade.revisado`. Isso explica um achado da auditoria anterior (§2.2) e é uma decisão de schema/comportamento, fora do escopo desta tarefa. Ver §6. |

---

## 1. Investigação do SDK — o que `thinking_level` realmente é

Inspecionado o pacote **`google-genai` 2.12.1** de fato instalado em `pipeline/backend/.venv` (não documentação externa):

```python
>>> from google.genai import types
>>> list(types.ThinkingLevel)
[THINKING_LEVEL_UNSPECIFIED, MINIMAL, LOW, MEDIUM, HIGH]

>>> types.ThinkingConfig.model_fields.keys()
dict_keys(['include_thoughts', 'thinking_budget', 'thinking_level'])

>>> types.GenerateContentResponseUsageMetadata.model_fields.keys()
dict_keys([..., 'cached_content_token_count', 'candidates_token_count',
           'prompt_token_count', 'thoughts_token_count', 'total_token_count', ...])
```

Achados relevantes que mudaram o desenho da implementação:

- **`thinking_level` é o parâmetro certo** para `gemini-3-flash-preview` (o SDK também expõe `thinking_budget`, herdado da família Gemini 2.5, mas a família Gemini 3 usa nível categórico, não orçamento em tokens).
- **`types.ThinkingLevel("qualquer-string")` não levanta exceção** para valor desconhecido — é um enum "aberto" do SDK que só emite um `UserWarning` e aceita o valor mesmo assim. Por isso a validação de `GEMINI_THINKING_LEVEL` no código é **explícita contra um `set` fechado**, não via `try/except ValueError` (que não teria pego o erro).
- `resp.usage_metadata.thoughts_token_count` **vem `None`, não `0`, quando o nível de thinking não gera nenhum token de raciocínio** (confirmado no teste: todas as 8 chamadas em `LOW` retornaram `thoughts_token_count=None` com `total_token_count = prompt + candidates` exato, sem parcela de thinking).
- `thinking_config` pode ser combinado com `cached_content` na mesma chamada sem conflito (verificado instanciando `GenerateContentConfig` com os dois campos).

---

## 2. Prioridade 1 — `thinking_level` configurável

### 2.1 Implementação

Arquivo: **`pipeline/backend/cognitive_engine.py`**.

- Nova constante `DEFAULT_THINKING_LEVEL` (decidida em §4, depois do teste — não antes).
- Nova função `_get_thinking_level()`: lê `GEMINI_THINKING_LEVEL` do ambiente (`MINIMAL`/`LOW`/`MEDIUM`/`HIGH`, case-insensitive); vazio ou um dos sentinelas `UNSET`/`DEFAULT`/`NONE` devolve `None` (não configura `thinking_config`, preservando o padrão nativo do modelo — rota de rollback imediato sem tocar código); valor inválido é logado como warning e ignorado (nunca derruba a chamada).
- `_generate_json` passa a montar `config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=...)` quando configurado — aplicado a **toda** chamada `generate_content` do módulo (anotação cognitiva, manifesto de caderno, importação de ontologia por PDF), não só ao caminho de anotação, porque é o único ponto de entrada real para a API (`_generate_json`).

Controlável por variável de ambiente (`GEMINI_THINKING_LEVEL`), documentada em `pipeline/backend/.env.example`.

### 2.2 O que o teste real revelou sobre HIGH (o comportamento atual, sem essa mudança)

Não foi preciso "assumir" nada — os números abaixo (§4) vêm de 8 chamadas reais em `HIGH`, na mesma sessão, mesma ontologia, mesmo schema:

- **3 das 8 chamadas (37,5%) bateram exatamente em 62.913 tokens de thinking** (uma quarta, em `MEDIUM`, bateu em 62.915 — 2 tokens de diferença, ruído de contagem). Esse número repetido sugere um **teto interno do modelo/SDK para o orçamento de "thinking" em HIGH**, não variância orgânica — o modelo não decide "pensar mais", ele bate num limite e para.
- Essas 3 chamadas duraram **223s, 225s e 288s** — a terceira a **12 segundos do timeout de cliente de 300s** (`BookResults.jsx:104,169`), o mesmo timeout que already causou "1 questão com erro" no lote de 89 auditado anteriormente. **Isto é evidência direta de que HIGH thinking não é só caro em média — ele é o mecanismo mais provável por trás do timeout relatado no lote original.**

---

## 3. Prioridade 2 — instrumentação por chamada

### 3.1 Novo módulo: `pipeline/backend/gemini_telemetry.py`

Extrai só números de `resp.usage_metadata` — nunca lê `resp.text`, nunca recebe `system_instruction`, `user_text` ou bytes de arquivo. Campos gravados por chamada:

```
model, thinking_level, cached (bool), duration_ms,
prompt_token_count, cached_content_token_count,
candidates_token_count, thoughts_token_count, total_token_count,
success, error_type, http_status,
context, book_id, question_number, item_id, created_at
```

`error_type` grava só o **nome da classe** da exceção (ex.: `ClientError`, `GeminiQuotaExhaustedError`) e `http_status` o código HTTP quando disponível — nunca a mensagem completa da exceção, que ocasionalmente pode ecoar fragmentos da requisição. Nenhuma chave de API é lida ou logada em lugar algum deste módulo.

`persist()` nunca propaga exceção — uma falha ao gravar telemetria é logada e engolida, para não derrubar uma anotação que já foi paga ao modelo (mesma filosofia de `gemini_cache.py`).

### 3.2 Fiação: `cognitive_engine.py`, `server.py`, `annotation_pipeline.py`

- `_generate_json` e `run_cognitive_pipeline` ganharam um parâmetro opcional `on_usage` (callback assíncrono), propagado sem quebrar nenhum chamador existente (default `None` preserva o comportamento anterior nos 2 pontos que não foram tocados: manifesto de caderno e importação de ontologia).
- Os **4 pontos** que chamam `run_cognitive_pipeline` para anotação cognitiva agora passam um `on_usage` que grava em **`db.gemini_usage`** (nova coleção Mongo, paralela a `gemini_caches`):
  - `POST /pipeline/generate` (`server.py`)
  - `POST /pipeline/{id}/regenerate` (`server.py`) — usa o `pipeline_id` existente como `item_id`, sem gerar um novo
  - `POST /book/{id}/process` (`server.py`) — **o endpoint que processou as 89 questões auditadas**
  - `annotation_pipeline.generate_and_persist` (usado por `batch_queue.py`, a fila com retry/backoff)
- Em 2 lugares (`/pipeline/generate` e `/book/{id}/process`), o `question_id` passou a ser gerado **antes** da chamada ao modelo (em vez de depois), só para existir a tempo de correlacionar a telemetria ao item — nenhuma outra mudança de fluxo.

### 3.3 Verificado, sem gastar com o Gemini

```
$ ./.venv/bin/python -c "... gemini_telemetry.persist(server.db.gemini_usage, fake, ...) ..."
inserted doc found: True
cleaned up: 1
```

O caminho de gravação no Mongo foi testado e limpo em seguida — confirma que a próxima vez que `/book/{id}/process` (ou qualquer outro dos 4 pontos) rodar de verdade, `db.gemini_usage` terá um documento por chamada, com os campos exatos listados em §3.1.

### 3.4 O que continua fora de alcance

- **Retries do SDK continuam invisíveis.** `_get_client()` usa `HttpRetryOptions` nativo do `google-genai` (`attempts=6`, backoff exponencial) — tentativas internas por 429/500/503/504 acontecem dentro do SDK, antes de qualquer exceção chegar ao nosso código, e não são contáveis com a API pública do cliente. Instrumentar isso exigiria substituir o retry do SDK por um próprio (envolveria refatoração maior, fora do pedido "não faça refatoração desnecessária").
- **A fatura real do Google Cloud/AI Studio continua sendo a única fonte de verdade absoluta.** `db.gemini_usage` aproxima isso por chamada bem-sucedida (ou que falhou depois de gerar resposta), mas não substitui o extrato de cobrança.

---

## 4. Prioridade 3 — teste controlado

### 4.1 O que foi testado, e por que dessa forma

**Não foram usadas nenhuma das 89 questões do lote auditado** — nem o PDF `2023_PV_impresso_D2_CD5.pdf`, nem texto extraído dele, nem os `item_id`s existentes. Em vez disso, o script `pipeline/backend/manual_cost_optimization_test.py` usa **8 questões sintéticas originais**, estilo ENEM (Matemática/Ciências da Natureza), escritas para este teste, cobrindo processos cognitivos variados (proporcionalidade, semelhança de triângulos, leitura de gráfico, raciocínio causal, interpretação textual, escala, leitura de rótulo de segurança) — para não enviesar o teste para um único tipo de questão.

Cada uma das 8 questões rodou em **3 configurações**, todas chamadas reais e pagas:

| Config | `thinking_level` |
|---|---|
| `atual_HIGH` | não configurado — comportamento de produção antes desta mudança (padrão do modelo, HIGH) |
| `otimizado_MEDIUM` | `MEDIUM` |
| `otimizado_LOW` | `LOW` |

Total: **24 chamadas**. Nada foi gravado em `db.pipelines` nem `db.books` — os resultados foram escritos em `auditoria/teste-otimizacao-custo-raw.json` (evidência bruta, preservada) e a validação estrutural rodou com o **mesmo** `item_contract.validate` de produção.

**Custo real deste teste**: US$ 0,97 (~**R$ 5,00**, calculado com o mesmo preço-lista e câmbio da auditoria anterior) — pequeno e proporcional, gasto para responder com dados reais, não estimativa, se a otimização funciona.

Antes das 24 chamadas, dois testes isolados (1 chamada em `LOW`, 1 em `HIGH`, mesma questão) confirmaram que a chave `GEMINI_API_KEY` ainda funciona e que a instrumentação nova captura os números corretos, antes de comprometer o orçamento maior.

### 4.2 Resultado agregado (médias sobre as 8 questões, por config)

| Config | saída+thinking (tokens, média) | thinking (média) | custo/chamada (USD, preço-lista) | duração média | válidas | bateu no teto ~62,9k |
|---|---:|---:|---:|---:|---:|---:|
| `atual_HIGH` | 26.468 | 24.599 | US$ 0,0801 | 102,1 s | 8/8 | **3/8 (37,5%)** |
| `otimizado_MEDIUM` | 11.666 | 9.818 | US$ 0,0357 | 46,6 s | 8/8 | 1/8 (12,5%) |
| `otimizado_LOW` | 1.703 | **0** | US$ 0,0058 | 8,1 s | **7/8** | 0/8 |

`prompt_token_count` e `cached_content_token_count` foram **idênticos entre as 3 configs para a mesma questão** (ex.: questão T1 — `in=12763, cache=12611` nas 3) — confirma que o teste isola exatamente a variável testada (`thinking_level`), sem confundir com variação de entrada.

### 4.3 Redução medida nesta amostra (preço-lista, USD)

- `MEDIUM` vs `HIGH`: **-55,4% de custo por chamada**, -55,9% de tokens de saída+thinking.
- `LOW` vs `HIGH`: **-92,7% de custo por chamada**, -93,6% de tokens de saída+thinking.

### 4.4 Projeção sobre a economia REAL observada (o lote de 89 questões, R$28)

Os números de §4.3 são de questões sintéticas de texto curto — não reproduzem sozinhos o custo real do lote de 89 (que processava um PDF de 32 páginas por chamada). Para responder "quanto isso muda a conta de R$28", a fração de redução medida foi aplicada sobre a decomposição real já reconstruída na auditoria anterior (§1.5 daquele relatório: R$0,0243/questão de entrada+cache, reconstrução por código+preço-lista; R$0,2903/questão de saída+thinking, por resíduo):

| Config | fração de saída+thinking retida | resíduo projetado/questão | **custo total projetado/questão** | redução vs. R$0,315 real |
|---|---:|---:|---:|---:|
| `atual_HIGH` (real, referência) | 100% | R$ 0,2903 | **R$ 0,315** | — |
| `otimizado_MEDIUM` | 44,1% | R$ 0,1280 | **R$ 0,152** | **-51,6%** |
| `otimizado_LOW` | 6,4% | R$ 0,0187 | **R$ 0,043** | **-86,3%** |

Isto é uma **projeção**, explicitamente rotulada como tal: combina uma fração medida em chamadas reais (thinking) com uma decomposição de custo real já observada em produção (entrada/cache/residual), não uma medição direta do lote de 89 refeito. A meta pedida (≥10% de redução) é batida por MEDIUM sozinho com folga de mais de 5x.

### 4.5 Verificação de qualidade — não só "o custo caiu"

- **Validade estrutural** (`item_contract.validate`, o validador de produção): `HIGH` 8/8, `MEDIUM` 8/8, `LOW` 7/8. A única falha (`LOW`, questão T8) foi `('ERR-11', 'PROC-QUANT-02')` — par erro/processo que não existe no catálogo 1.4.1, **o mesmo tipo exato de defeito já presente no corpus de produção** (`Q172` na auditoria anterior, mesma classe de erro). Com N=8 por config, 1 falha está dentro do ruído esperado de uma taxa-base de ~4,5% já observada em produção (HIGH, 89 questões reais) — não dá para concluir que `LOW` piora a taxa de erro com esta amostra, mas também não dá para descartar. **Essa incerteza, mais que a magnitude da falha em si, é o motivo de MEDIUM ter sido escolhido como padrão em vez de LOW.**
- **Controle negativo**: `qualidade.confianca_global` saiu **0,7 nas 24 chamadas, nas 3 configs, sem exceção** — reproduz exatamente o colapso de confiança já documentado na auditoria anterior (§2.3), e confirma que **esse defeito é independente de `thinking_level`** — baixar o nível de raciocínio não piora nem melhora esse problema específico (ele já não varia com pensamento).
- **`n_processos`** (1 ou 2, nunca mais) e a ausência de warnings incomuns se mantiveram estáveis entre as 3 configs.

**Veredito**: `MEDIUM` não mostrou degradação de qualidade mensurável nesta amostra controlada, com redução de custo muito acima da meta. `LOW` é mais barato ainda, mas carrega um sinal de risco (não uma certeza) que não foi resolvido com N=8 — fica documentado e disponível, não como padrão.

---

## 5. Decisão final e como usar

`cognitive_engine.DEFAULT_THINKING_LEVEL = "MEDIUM"` — aplicado automaticamente a toda chamada, sem exigir nenhuma variável de ambiente.

Para mudar sem editar código:

```bash
# pipeline/backend/.env
GEMINI_THINKING_LEVEL=LOW      # mais barato (~86%), 1 sinal de risco não resolvido — ver §4.5
GEMINI_THINKING_LEVEL=HIGH     # comportamento antigo, sem controle
GEMINI_THINKING_LEVEL=MINIMAL  # não testado nesta rodada — ver §7
GEMINI_THINKING_LEVEL=UNSET    # remove o thinking_config da chamada; modelo usa seu próprio padrão
```

---

## 6. Achado fora de escopo — não implementado, só relatado (pedido explícito do usuário)

Ao ler `item_contract.py` para montar o teste de validação, apareceu a causa exata de um achado da auditoria anterior (§2.2: `qualidade.revisado` e `qualidade.apto_para_camada_de_crenca.valor` concordavam em 89/89 itens, sem exceção — lá descrito como "provável erro de prompt/código"). A causa real é **só código**, não thinking, não prompt:

```python
# item_contract.py:205-211 (normalize_item, já existia antes desta tarefa)
qual = item.setdefault("qualidade", {}) or {}
qual.setdefault("revisado", False)
# EXT-WP1-1.0 L13b / Error Trace §6: um item pode ser ARMAZENADO sem revisão
# humana; não pode influenciar o estado de um estudante real sem ela. O
# pipeline nunca marca isto como verdadeiro — só a revisão humana marca.
qual["apto_para_camada_de_crenca"] = {"valor": bool(qual.get("revisado"))}
```

`normalize_item` **sempre sobrescreve** `apto_para_camada_de_crenca.valor` para ser exatamente `bool(revisado)`, depois que o item sai do modelo — qualquer julgamento independente que o modelo tenha tentado emitir para esse campo é descartado. Isso confirma, com o código na mão, que a inconsistência achada na auditoria anterior (`apto_para_camada_de_crenca: true` em itens estruturalmente inválidos) **não é o modelo mentindo** — é o código derivando um campo do outro por regra fixa, e a regra em si (herdar de `revisado`, que também não é setado por revisão humana real) é o que produz o problema.

**Não alterado nesta tarefa** — é uma decisão sobre o significado de dois campos do Schema/comportamento do pipeline, não uma otimização econômica. Fica registrado para decisão futura.

---

## 7. Fatiamento de PDF / Gemini Files API — avaliado, não implementado (pedido explícito)

Conforme instruído, nenhum dos dois foi implementado. Estimativa do potencial, para decisão futura:

- **Cache do PDF do caderno inteiro** (extensão natural de `gemini_cache.py`, que já cacheia o texto da ontologia — bastaria incluir o `Part` do PDF no mesmo `contents` cacheado, já que o PDF é fixo por caderno, igual à ontologia é fixa por versão): a auditoria anterior reconstruiu ~R$1,91 para os 89 envios do PDF sem cache (33 páginas × 258 tok/página × $0,50/1M × 89). Cacheado, isso cairia para ~R$0,23 (1 envio integral + 88 leituras de cache a $0,05/1M) — **~88% de redução nessa linha específica**, ~6% do custo total do lote de R$28. Menor impacto que `thinking_level`, mas de risco de qualidade zero (não muda o que o modelo vê) e reaproveita infraestrutura já existente.
- **Fatiamento por página antes do envio**: reduziria a mesma linha de forma parecida (~32x menos páginas por chamada), mas exige mapear qual página pertence a qual questão (hoje só existe `focus_hint` textual, sem esse mapeamento) — mais código novo que a opção de cache.
- **Gemini Files API**: resolve limite de tamanho de payload (hoje 16MB de folga sobre um limite documentado de 20MB inline) e latência de upload repetido, mas **não reduz custo por token sozinha** — o modelo ainda processa o conteúdo do arquivo a cada chamada referenciada, a menos que combinada com cache explícito (mesmo mecanismo do item acima).

**Recomendação para quando isso for priorizado**: cache do PDF do caderno, não fatiamento — reaproveita `gemini_cache.py` já testado em produção, sem exigir mapeamento página↔questão.

---

## 8. Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `pipeline/backend/cognitive_engine.py` | `thinking_level` configurável (`_get_thinking_level`, `DEFAULT_THINKING_LEVEL="MEDIUM"`); captura de `usage_metadata` (tokens + duração) em toda chamada, com/sem sucesso; parâmetro `on_usage` propagado por `_generate_json`/`run_cognitive_pipeline` |
| `pipeline/backend/gemini_telemetry.py` | **novo módulo** — extração segura de uso (`usage_from_response`/`usage_from_error`) e persistência best-effort (`persist`) |
| `pipeline/backend/server.py` | import de `gemini_telemetry`; 3 rotas (`/pipeline/generate`, `/pipeline/{id}/regenerate`, `/book/{id}/process`) passam a gravar telemetria por chamada em `db.gemini_usage`, com `question_id` movido para antes da chamada ao modelo em 2 delas (para existir a tempo de correlacionar) |
| `pipeline/backend/annotation_pipeline.py` | `generate_and_persist` (usado por `batch_queue.py`) grava telemetria da mesma forma |
| `pipeline/backend/.env.example` | documenta `GEMINI_THINKING_LEVEL` |
| `pipeline/backend/manual_cost_optimization_test.py` | **novo, não faz parte do pytest** — script de teste controlado usado nesta tarefa (reexecutável; gasta dinheiro real; exige `--yes`) |
| `auditoria/teste-otimizacao-custo-raw.json` | **novo** — evidência bruta das 24 chamadas do teste (§4) |
| `auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI.md` | este relatório |

**Não alterados**: Schema 2.2, Ontologia 1.4.1, Manual de Anotação, Constituição, White Paper, `gemini_cache.py`, `gemini_batch.py`, `batch_queue.py` (estrutura), `item_contract.py`, `ontology_validator.py`, qualquer arquivo do corpus (`sapiens_pipeline.pipelines`), qualquer arquivo de frontend.

---

## 9. Testes executados

```bash
./.venv/bin/python -m pytest tests/ -q --ignore=tests/test_book_endpoints.py
# 144 passed, 14 failed / 6 errors — todas as falhas são testes de integração que
# exigem um servidor rodando em localhost:8001 + REACT_APP_BACKEND_URL, prévias a
# esta tarefa (connection refused / env var ausente, nada relacionado ao código
# alterado — nenhum teste que toca cognitive_engine/server/annotation_pipeline
# por importação direta falhou).

./.venv/bin/python -m pytest tests/test_gemini_retry_and_cache.py tests/test_batch_queue.py \
  tests/test_contratos_canonicos.py tests/test_prontidao_producao.py tests/test_sem_emergent.py -q
# 137 passed — suíte relevante ao código tocado, 100% verde, antes e depois de
# trocar DEFAULT_THINKING_LEVEL de LOW (escolha inicial) para MEDIUM (escolha
# final, pós-teste).

# Verificação manual (sem custo de Gemini): gravação em db.gemini_usage
# confirmada com documento sintético, inserido e removido.

# Teste controlado real: 24 chamadas Gemini pagas — ver §4. Custo: ~R$5,00.
```

---

## 10. Resumo direto das 7 entregas pedidas

1. **Alterações implementadas**: só as listadas em §8 — nenhuma refatoração além do necessário para `thinking_level` configurável + instrumentação por chamada.
2. **Testes executados**: suíte automatizada (137 testes relevantes, verde) + teste controlado real de 24 chamadas (§4).
3. **Arquivos alterados**: lista exata em §8.
4. **Custo/tokenização antes vs. depois**: §4.2 (medido, amostra sintética) e §4.4 (projetado sobre o custo real de R$0,315/questão).
5. **Redução percentual**: MEDIUM ≈ **-51,6%** projetado sobre o custo real; LOW ≈ **-86,3%** (não é o padrão — ver §4.5).
6. **Meta de ≥10% atingida?** **Sim**, com folga de mais de 5x usando a configuração escolhida como padrão (MEDIUM).
7. **Este relatório**: `auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI.md`.

---

## O que NÃO foi alterado (preservado)

- As 89 questões do lote auditado (`sapiens_pipeline.pipelines`, `book_id 6ba5747b-...`) — nenhuma chamada nova foi feita contra elas, nenhum dado foi lido nem reescrito.
- Schema 2.2, Ontologia 1.4.1, Manual de Anotação, Constituição, White Paper.
- O prompt cognitivo (`build_system_prompt`, `_ontology_prompt_slice`) — a única mudança de comportamento de chamada é `thinking_config`, um parâmetro de configuração da API, não texto de prompt.
- A arquitetura do pipeline (rotas, coleções existentes, `batch_queue`, cache de ontologia) — só uma coleção nova (`gemini_usage`) foi adicionada, sem remover ou alterar nenhuma existente.
- O achado de `apto_para_camada_de_crenca` (§6) — relatado, não corrigido, por ser decisão conceitual fora do escopo desta tarefa.
