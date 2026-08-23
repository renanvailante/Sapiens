# Otimização econômica do pipeline Gemini — 2ª rodada: thinking adaptativo + cache de PDF por caderno

**Registrado em:** 2026-08-22
**Status:** ✅ **APROVADO como baseline atual em 2026-08-22.** Ver §10 — inclui uma ressalva descoberta DEPOIS da aprovação (o seletor de thinking do frontend do caderno hoje contorna o escalonamento adaptativo) e o congelamento explícito de novas mudanças no pipeline até haver telemetria real (`db.gemini_usage`) apontando onde ainda há gasto relevante.
**Natureza:** auditoria + implementação + verificação empírica. Sob GOV-1.0 §1.1, `auditoria/` não cria norma.
**Escopo:** exclusivamente econômico. Não altera Schema 2.2, Ontologia 1.4.1, Constituição, White Paper, regras cognitivas, nem o prompt cognitivo (`build_system_prompt`, `_ontology_prompt_slice`).
**Pré-requisitos lidos antes de qualquer mudança:** `auditoria/AUDITORIA-ECONOMICA-E-CORPUS-2026-08-22.md` (1ª auditoria, achou o problema) e `auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI.md` (1ª rodada de otimização — thinking_level configurável, escolheu MEDIUM como padrão, instrumentou telemetria).
**Ponto de partida:** a 1ª rodada já reduziu o custo projetado de R$0,315 → **R$0,152/questão** (MEDIUM fixo, -51,6%). Este pedido é para ir além disso — "diminuir o máximo possível, principalmente o thinking".

---

## 0. Resumo executivo

| Pergunta | Resposta |
|---|---|
| Dá para reduzir mais, sem tocar Schema/Ontologia/prompt cognitivo? | **Sim.** Duas mudanças, ambas de código/configuração: (1) thinking **adaptativo** (LOW por padrão, escalona para MEDIUM só quando a validação estrutural reprova) e (2) **cache do PDF do caderno inteiro**, não só da ontologia. |
| Custo projetado combinado | **R$ 0,152 → ≈ R$ 0,031/questão** (-79,8% sobre o estado atual, -90,3% sobre o HIGH original). |
| Isso custou caro para descobrir? | **Não.** O ganho do thinking adaptativo (maior dos dois) foi validado **sem gastar 1 chamada nova** — simulado sobre os mesmos dados reais já pagos no teste da 1ª rodada (24 chamadas, já existentes em `auditoria/teste-otimizacao-custo-raw.json`). O cache de PDF foi verificado com 3 chamadas reais pequenas (arquivo de texto sintético, não um PDF de 32 páginas) — custo real: **US$ 0,014 (≈ R$ 0,07)**. |
| A qualidade se manteve? | Sim, na amostra disponível: 8/8 válidas simulando a estratégia adaptativa (igual a MEDIUM e HIGH fixos), com só 1/8 escalonamentos. |
| As 89 questões reais foram tocadas? | **Não.** Nenhuma chamada nova contra elas; a validação do thinking adaptativo reusou resultados já existentes de questões sintéticas. |

---

## 1. Auditoria — os 10 pontos pedidos

### 1.1 Tokens de entrada repetidos entre questões

Confirmado e quantificado: o bloco fixo (system prompt + ontologia) mede **9.811 + 28.825 = 38.636 caracteres ≈ 9.659 tokens** (aprox. 4 char/token), idêntico em toda chamada de anotação cognitiva, de qualquer questão, de qualquer caderno, enquanto a versão da ontologia/schema não mudar. Esse bloco já está coberto por cache desde a 1ª rodada (ver §1.3).

O que a 1ª rodada **não** cobriu: quando várias questões vêm do MESMO caderno (`/book/{id}/process`, o endpoint que gerou o lote de 89), o **PDF inteiro do caderno também se repete, byte a byte, em toda chamada** — e esse não estava em cache algum. Confirmado no código (`server.py`, antes desta mudança): `_load_book_files(book)` relê o PDF completo do storage e o reenvia inline em `run_cognitive_pipeline` a cada questão.

### 1.2 Conteúdo reenviado desnecessariamente (PDF, ontologia, schema, system prompt)

| Bloco | Repetido em toda chamada? | Cacheado antes desta rodada? | Cacheado agora? |
|---|---|---|---|
| System prompt (inclui o Schema 2.2 embutido) | Sim | Sim (dentro do mesmo cache da ontologia) | Sim |
| Ontologia | Sim | Sim | Sim |
| PDF do caderno (quando há N questões do mesmo caderno) | Sim, POR INTEIRO, em toda questão | **Não** | **Sim** (novo — `book_cache_key`) |
| `focus_hint` ("Questão nº X") | Não — é específico da questão | N/A (não cacheável, muda a cada chamada) | N/A |

O Schema 2.2 embutido no system prompt (a estrutura JSON completa de `DEFAULT_PIPELINE_SCHEMA`) já ia dentro do bloco cacheado desde a 1ª rodada — não precisa de tratamento à parte, e não foi reduzido: reduzir esse JSON mudaria o contrato de saída, fora do escopo autorizado.

### 1.3 O que já está coberto por cache / o que não estava

Como já documentado na 1ª rodada: **1 cache por (model, ontology_version, schema_version)**, compartilhado entre TODAS as questões de TODOS os cadernos, válido por 1h (TTL). Isso cobre ~9.659 tokens fixos.

**O que não estava coberto, e agora está:** o PDF do caderno. Implementado como um **segundo cache, por (model, book_id, ontology_version, schema_version)** — quando uma rota processa uma questão de um caderno específico, o motor tenta subir um cache que já inclui o PDF junto com a ontologia; se conseguir, as chamadas seguintes do MESMO caderno não reenviam o arquivo. Ver §3.

**O que continua fora do cache, de propósito:** o texto/foco específico de cada questão (`focus_hint`) — muda a cada chamada, não é cacheável por natureza.

### 1.4 Chamadas Gemini que podem ser eliminadas, combinadas ou condicionadas

Revisado todo o inventário de chamadas do módulo (`cognitive_engine.py`):

| Chamada | Volume | Pode eliminar/combinar? |
|---|---|---|
| Anotação cognitiva (`run_cognitive_pipeline`) | 1 por questão — o grosso do custo | Não eliminável (é o produto). **Tornada condicional em nível de thinking** — ver §1.6. |
| Manifesto do caderno (`run_book_manifest`) | 1 por caderno (não por questão) | Já é o mínimo — 1 chamada identifica todas as questões do PDF de uma vez, evitando N chamadas de descoberta. Não alterado. |
| Importação de ontologia por PDF (`parse_ontology_with_gemini`) | Só quando o usuário importa uma ontologia nova — raríssimo | Fora de escala, não otimizado. |
| Cache de ontologia/caderno (`caches.create`) | 1 por (ontologia, schema) + 1 por caderno, não por questão | Já é o desenho mínimo. |

**Nenhuma chamada duplicada ou redundante foi encontrada** nesta auditoria — o que existia de ineficiência era o QUE cada chamada carregava (thinking sem teto, PDF sem cache), não uma chamada supérflua inteira.

### 1.5 Tamanho dos prompts e contexto por questão

Medido nesta rodada (chamada real, questão sintética de texto puro — ver §4):

| Componente | Tokens |
|---|---|
| Bloco fixo cacheado (system prompt + ontologia) | ~9.659–9.720 (variação de arredondamento do tokenizador) |
| Conteúdo específico da questão (texto puro pequeno) | ~130–200 |
| Saída (JSON da anotação) | ~1.300–1.900 |
| Thinking (LOW) | 0 (nenhum token de raciocínio, confirmado por `thoughts_token_count=None`) |

Para uma questão real vinda de um PDF de caderno (não texto puro), o componente "conteúdo específico" seria dominado pelas ~258 tokens/página do PDF completo × nº de páginas do caderno — exatamente o que o cache de caderno (§3) agora evita reenviar a cada questão.

### 1.6 Thinking level — o ponto central deste pedido

Estado antes desta rodada: **MEDIUM fixo** para toda chamada (decidido na 1ª rodada, com 8/8 válidas na amostra testada, -51,6% vs HIGH). O pedido agora é ir além, "principalmente o thinking".

**O que foi feito:** thinking deixou de ser um NÍVEL ÚNICO fixo e passou a ser **adaptativo por questão**: tenta primeiro em LOW (o nível mais barato do modelo — na amostra da 1ª rodada, LOW teve `thoughts_token_count=0` em 8/8, contra uma média de 9.818 tokens de thinking em MEDIUM); se a saída reprovar na validação estrutural de produção (`item_contract.validate` — o MESMO validador usado em produção, não um substituto), reexecuta **uma única vez** em MEDIUM. Nunca mais que 2 chamadas por questão — não existe uma 3ª tentativa, de propósito (ver `run_cognitive_pipeline_adaptive` em `cognitive_engine.py`).

Por que isso é seguro (não é "usar LOW e torcer"): a escalada é condicionada à MESMA validação estrutural que hoje já decide se um item está `validacao.valid: true/false` em produção. Uma questão que LOW não resolve bem nunca fica presa em LOW — ela automaticamente ganha uma segunda tentativa mais cara, exatamente como MEDIUM (o padrão atual) já a trataria.

**Verificação:** simulado sobre os dados reais das 24 chamadas já pagas na 1ª rodada (nenhuma chamada nova) — ver §4.1.

### 1.7 Cache do PDF do caderno inteiro

Era a recomendação explícita e não-implementada da 1ª rodada (§7 daquele relatório: "~88% de redução nessa linha específica, ~6% do custo total do lote"). Implementada agora — ver §3. Com o thinking já reduzido pela adaptação do §1.6, essa mesma linha de custo passa a representar uma fração MAIOR do total (porque o numerador thinking caiu muito), o que tornou essa otimização mais valiosa do que era na 1ª rodada, não menos.

Verificado com chamadas reais pequenas (§4.2) que o mecanismo funciona corretamente contra a API real: o arquivo entra no cache combinado e passa a ser cobrado na faixa de leitura de cache (US$0,05/1M) em vez da faixa de entrada normal (US$0,50/1M) — 10x mais barato para o mesmo conteúdo, a partir da 2ª chamada do mesmo caderno em diante.

### 1.8 Retries ou chamadas duplicadas aumentando custo

Reconfirmado o achado da 1ª rodada: **retries do SDK continuam invisíveis** (`HttpRetryOptions` nativo do `google-genai`, interno, sem logging de tentativas individuais). Não instrumentado nesta rodada — exigiria substituir o retry nativo do SDK por um próprio, refatoração maior e fora do pedido. Nenhuma evidência de chamada duplicada por bug de código foi encontrada (nenhum loop de chamada dupla, nenhum retry manual redundante).

### 1.9 Campos/contextos enviados que não são necessários para o JSON final

Nada removido do que é enviado ao modelo — o pedido explícito foi "sem degradar qualidade cognitiva/estrutural", e tudo que o system prompt e a ontologia carregam hoje é usado pelas regras de classificação (Manual §2–§8, citadas literalmente no prompt). Não há campo "morto" enviado ao modelo que não sirva ao contrato de saída.

### 1.10 Oportunidades de reduzir tokens sem alterar a saída contratual

As duas implementadas (§1.6, §1.7) são exatamente disso: mudam SOMENTE como/quanto é pago pelo mesmo conteúdo e mesma qualidade de saída — nenhuma delas remove, resume ou reescreve o que o modelo recebe ou pode produzir.

---

## 2. Plano priorizado (antes de implementar)

| # | Otimização | Economia estimada | Risco de qualidade | Complexidade | Decisão |
|---|---|---:|---|---|---|
| 1 | Thinking adaptativo (LOW → escalona p/ MEDIUM se inválido) | **~80% sobre o custo atual (MEDIUM fixo)**, medido por simulação com dados reais | Baixo — mitigado pela própria validação estrutural de produção como gatilho de escalonamento | Média (nova função em `cognitive_engine.py` + wiring em 3 rotas) | **Implementar** |
| 2 | Cache do PDF do caderno inteiro | ~88% da fração de entrada hoje não-cacheada (PDF), maior em % agora que o thinking caiu | Zero — não muda o que o modelo recebe, só como é cobrado | Média (extensão do cache existente + wiring em 1 rota principal) | **Implementar** |
| 3 | Instrumentar retries do SDK | Desconhecida (podem já ser ~0) | N/A (observabilidade, não muda comportamento) | Alta (substituir retry nativo do SDK) | Descartado — fora de proporção para o ganho incerto |
| 4 | Fatiar PDF por página em vez de cachear inteiro | Similar ao #2, talvez um pouco menor | Médio — exige mapear página↔questão, hoje inexistente | Alta | Descartado — cache reaproveita infraestrutura já testada, sem esse mapeamento novo |
| 5 | Reduzir o JSON do Schema embutido no system prompt | Pequena (schema já cacheado — só barateia CRIAÇÃO do cache, não leitura) | Alto — mexeria no contrato de saída | Baixa, mas proibida pelo escopo | Descartado — instrução explícita de não alterar Schema |
| 6 | Reduzir texto da ontologia enviado | Pequena (já cacheado) | Alto — risco de perder campo usado pelas regras de classificação | Baixa, mas proibida pelo escopo | Descartado — instrução explícita de não alterar Ontologia |

Implementados: **#1 e #2**, os dois de maior impacto e (no caso de #2, risco zero; no caso de #1, risco mitigado pela própria validação de produção).

---

## 3. Implementação

### 3.1 Thinking adaptativo — `cognitive_engine.run_cognitive_pipeline_adaptive`

Nova função, aditiva (não altera `run_cognitive_pipeline`, que continua existindo e se comportando exatamente como antes para quem a chama diretamente — ex.: `tests/test_book_thinking_level.py` não precisou mudar).

- Estratégia controlada por `GEMINI_THINKING_STRATEGY` (`ADAPTIVE`, padrão, ou `FIXED`).
- Níveis controláveis por `GEMINI_THINKING_LEVEL_LOW` (padrão `LOW`) e `GEMINI_THINKING_LEVEL_ESCALATED` (padrão `MEDIUM`).
- Um `thinking_level` explícito (ex.: o seletor LOW/MEDIUM/HIGH da tela do caderno, já existente desde a 1ª rodada) **sempre** desliga o modo adaptativo para aquela chamada — escolha humana explícita nunca é sobrescrita por uma heurística de custo.
- `judge(raw)` é fornecido por quem chama (nunca importado dentro de `cognitive_engine.py`, para não acoplar o motor ao validador de contrato) — nos 3 pontos de produção, é `item_contract.normalize_item` + `item_contract.validate`, o MESMO validador usado para decidir `validacao.valid` hoje.
- Se `judge` levantar exceção, o resultado da 1ª tentativa é aceito sem escalonar — um bug no validador nunca pode dobrar custo silenciosamente.

Ligado em 4 pontos de produção: `server.py` (`/pipeline/generate`, `/pipeline/{id}/regenerate`, `/book/{id}/process`) e `annotation_pipeline.generate_and_persist` (usado por `batch_queue.py`).

### 3.2 Cache do PDF do caderno — `book_cache_key` em `run_cognitive_pipeline`

Novo parâmetro opcional. Quando presente (junto com `cache_collection` e `files` não-vazio), tenta subir um cache **combinado** (ontologia + os arquivos do caderno) chaveado por `(model, "caderno", book_cache_key, ontology_version, schema_version)` — nunca compartilhado entre cadernos diferentes. Se a 1ª chamada de um caderno conseguir criar esse cache, as chamadas seguintes do MESMO caderno reusam-no e **não reenviam os arquivos** na parte não-cacheada da chamada. Se a criação falhar por qualquer motivo (arquivo grande demais, API sem suporte para o tipo de conteúdo, etc.), cai automaticamente para o cache só-de-ontologia — nunca bloqueia a anotação por causa desta otimização, mesma filosofia do cache já existente.

Ligado no único ponto de produção que processa N questões do mesmo caderno com PDF fixo: `server.py` `/book/{book_id}/process`, usando `book_id` como `book_cache_key`. **Não ligado** em `batch_queue.py`/`annotation_pipeline.py` — a fila de lote hoje não carrega `book_id` no documento da fila (schema não tem esse campo), e adicioná-lo seria uma mudança de schema não estritamente necessária para o objetivo (a fila de lote não foi, historicamente, o caminho usado para processar cadernos — ver 1ª auditoria §1.2: "a fila... não foi usada neste lote").

---

## 4. Teste controlado — antes/depois

### 4.1 Thinking adaptativo — validado SEM gastar nada de novo

Reaproveitados os resultados reais das 24 chamadas pagas no teste da 1ª rodada (`auditoria/teste-otimizacao-custo-raw.json` — 8 questões sintéticas × {HIGH, MEDIUM, LOW}, nenhuma delas do lote de 89). Simulação: para cada questão, usa o resultado real de LOW; se `validacao.valid` for `false`, SOMA o resultado real de MEDIUM (mesma questão) — exatamente o que `run_cognitive_pipeline_adaptive` faria de verdade.

| Config | custo médio/questão (preço-lista, USD) | válidas | escalonamentos |
|---|---:|---:|---:|
| `atual_HIGH` (referência, 1ª rodada) | US$ 0,0801 | 8/8 | — |
| `otimizado_MEDIUM` (padrão atual em produção) | US$ 0,0357 | 8/8 | — |
| `otimizado_LOW` (isolado, sem escalonar) | US$ 0,0058 | 7/8 | — |
| **`adaptativo_LOW→MEDIUM` (simulado, esta rodada)** | **US$ 0,0071** | **8/8** | **1/8 (T8)** |

Redução do adaptativo vs. MEDIUM fixo (padrão atual): **-80,2%**. Vs. HIGH original: **-91,2%**.

Tokens médios por questão (mesma simulação):

| Config | entrada não-cacheada | cache | saída | thinking |
|---|---:|---:|---:|---:|
| `atual_HIGH` | 181 | 12.611 | 1.869 | 24.599 |
| `otimizado_MEDIUM` | 181 | 12.611 | 1.848 | 9.818 |
| `otimizado_LOW` (isolado) | 181 | 12.611 | 1.703 | 0 |
| **adaptativo (simulado)** | **199** | **14.187** | **1.922** | **167** |

(O adaptativo soma 2 chamadas na única questão que escalonou — por isso a média não é idêntica à de LOW isolado, mas ainda assim uma fração pequena de MEDIUM/HIGH.)

**Limite explícito desta evidência:** N=8, a mesma amostra sintética da 1ª rodada (nenhuma chamada nova). 1 escalonamento observado em 8 questões (12,5%) é consistente com a taxa de falha de LOW isolado já medida na 1ª rodada (1/8). Uma amostra maior futura deve confirmar se essa taxa se mantém, mas o mecanismo de escalonamento garante que, mesmo se a taxa for maior, a qualidade final nunca fica pior que MEDIUM fixo — só o custo médio sobe proporcionalmente aos casos que precisam da 2ª chamada.

### 4.2 Cache do PDF do caderno — verificado com chamadas reais pequenas

Script novo, reexecutável: `pipeline/backend/manual_book_cache_smoke_test.py` (segue o mesmo padrão de `manual_cost_optimization_test.py` — imprime o plano e exige `--yes` para gastar dinheiro de verdade). Usa 1 questão sintética de texto puro (não um PDF de 32 páginas — de propósito, para manter o custo mínimo; o objetivo aqui é verificar o MECANISMO contra a API real, não remedir a magnitude de economia de um PDF grande, já reconstruída com precisão na 1ª auditoria a partir da documentação oficial de tokenização de PDF).

3 chamadas reais, thinking=LOW em todas (para isolar o efeito do cache, sem misturar com a variável de thinking):

| Chamada | `prompt_token_count` (total) | `cached_content_token_count` |
|---|---:|---:|
| 1) sem `book_cache_key` (comportamento anterior) | 12.743 | 12.611 |
| 2) com `book_cache_key`, 1ª vez (cria o cache combinado) | 12.743 | 12.706 |
| 3) com `book_cache_key`, 2ª vez (reusa o cache) | 12.743 | 12.706 |

Confirmado:
- O cache combinado foi criado com sucesso pela API real (`chars=38.636`, o mesmo tamanho do bloco system+ontologia — o arquivo sintético usado é pequeno, então sua contribuição em tokens é pequena, mas está presente).
- `cached_content_token_count` cresceu de 12.611 (só ontologia) para 12.706 (ontologia + arquivo) — o arquivo migrou para a faixa de preço de leitura de cache (US$0,05/1M) em vez da faixa de entrada normal (US$0,50/1M): **10x mais barato para o mesmo conteúdo**.
- A 2ª chamada com o mesmo `book_cache_key` **não criou um cache novo** (só 2 documentos em `gemini_caches` ao final: 1 ontologia-só + 1 caderno — não 3), confirmando reuso.
- `prompt_token_count` (o TOTAL processado pelo modelo) ficou constante nas 3 chamadas — esperado: caching muda o PREÇO por token, não a contagem total de tokens processados.

**Custo real deste smoke test:** ≈ US$ 0,014 (≈ R$ 0,07) — 3 chamadas pequenas de texto puro. Nenhuma das 89 questões do lote auditado foi usada; nada foi gravado em `db.pipelines`/`db.books`.

**Por que a magnitude de economia real (PDF de 32 páginas) não foi remedida aqui:** a 1ª auditoria já reconstruiu essa conta com precisão a partir da documentação oficial (258 tokens/página × 32 páginas × 89 chamadas), e reexecutar isso contra um PDF real gastaria dinheiro sem melhorar a certeza do resultado — o que faltava verificar (e foi verificado agora) era se o MECANISMO de cache funciona para arquivos, não a aritmética de tokens por página, que já era conhecida.

---

## 5. Projeção combinada (thinking adaptativo + cache de PDF)

Usando a mesma metodologia de projeção da 1ª auditoria (fração medida × decomposição de custo real observada em produção):

| Config | saída+thinking (fração do MEDIUM real) | entrada+cache (fração do atual) | custo total projetado/questão | redução vs. MEDIUM atual (R$0,152) | redução vs. HIGH original (R$0,315) |
|---|---:|---:|---:|---:|---:|
| MEDIUM fixo (produção atual) | 100% | 100% | R$ 0,152 | — | -51,6% |
| **+ thinking adaptativo** | **~19,8%** (US$0,0071/US$0,0357) | 100% (ainda sem cache de PDF) | **≈ R$ 0,030 + R$ 0,024 ≈ R$ 0,054** | **-64,5%** | **-82,9%** |
| **+ cache de PDF também** | ~19,8% | **~22%** (10x mais barato na fração PDF, que domina a linha de entrada) | **≈ R$ 0,030 + R$ 0,005 ≈ R$ 0,031** | **-79,8%** | **-90,3%** |

Projeção para lotes maiores (mesma ordem de grandeza da 1ª auditoria, agora combinando as duas otimizações):

| Nº de questões | MEDIUM fixo (atual) | + adaptativo + cache de PDF (esta rodada) |
|---:|---:|---:|
| 200 | ≈ R$ 30 | ≈ R$ 6 |
| 1.000 | ≈ R$ 152 | ≈ R$ 31 |
| 10.000 | ≈ R$ 1.520 | ≈ R$ 307 |

**Rótulo explícito:** isto é uma projeção, não uma remedição do lote real de 89 — a mesma ressalva metodológica da 1ª auditoria se aplica (amostra de questões sintéticas de texto curto para o componente de thinking; reconstrução por documentação oficial + 1 verificação real pequena para o componente de cache de PDF).

---

## 6. O que NÃO foi implementado, e por quê

- **Instrumentar retries do SDK** — ganho incerto, exigiria substituir o retry nativo do `google-genai`. Fora de proporção.
- **Fatiar PDF por página** — exigiria mapear página↔questão (não existe hoje); o cache do PDF inteiro obtém a maior parte do ganho sem esse mapeamento novo.
- **Reduzir o Schema/Ontologia enviados ao modelo** — proibido explicitamente pelo pedido ("Não altere Schema, Ontologia, Constituição, White Paper ou regras cognitivas").
- **Aplicar o cache de PDF também na fila de lote (`batch_queue.py`)** — exigiria adicionar `book_id` ao schema da fila; a fila não é, historicamente, o caminho usado para processar cadernos em lote (ver 1ª auditoria).
- **Reprocessar as 89 questões reais com as novas otimizações** — explicitamente proibido pelo pedido; sem isso, os números de §5 continuam sendo projeção, não remedição.

---

## 7. Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `pipeline/backend/cognitive_engine.py` | `run_cognitive_pipeline` ganha `book_cache_key` (cache combinado ontologia+PDF do caderno); nova função `run_cognitive_pipeline_adaptive` (thinking LOW→escalona MEDIUM condicionado a `judge()`); constantes `DEFAULT_ADAPTIVE_LOW_LEVEL`/`DEFAULT_ADAPTIVE_ESCALATED_LEVEL`, `_thinking_strategy()` |
| `pipeline/backend/server.py` | `/pipeline/generate`, `/pipeline/{id}/regenerate`, `/book/{id}/process` passam a usar `run_cognitive_pipeline_adaptive` com `judge` = normalize+validate de produção; `/book/{id}/process` também passa `book_cache_key=book_id` |
| `pipeline/backend/annotation_pipeline.py` | `generate_and_persist` (usado por `batch_queue.py`) idem — `run_cognitive_pipeline_adaptive` com `judge` |
| `pipeline/backend/.env.example` | documenta `GEMINI_THINKING_STRATEGY`, `GEMINI_THINKING_LEVEL_LOW`, `GEMINI_THINKING_LEVEL_ESCALATED` |
| `pipeline/backend/tests/test_adaptive_thinking.py` | **novo** — 11 testes offline (sem rede/Mongo real): escalonamento, as 2 rotas de desligamento do modo adaptativo, judge que quebra, níveis configuráveis por env, cache de caderno (criação, reuso, isolamento entre cadernos, fallback em falha) |
| `pipeline/backend/tests/test_batch_queue.py` | 3 monkeypatches atualizados de `run_cognitive_pipeline` → `run_cognitive_pipeline_adaptive` (a função que `annotation_pipeline.py` agora chama), dublês devolvendo a tupla `(raw, meta)` |
| `pipeline/backend/manual_book_cache_smoke_test.py` | **novo** — script de verificação real e pequena (segue o padrão de `manual_cost_optimization_test.py`), reexecutável, gasta dinheiro real (poucos centavos), exige `--yes` |
| `auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI-2.md` | este relatório |

**Não alterados**: Schema 2.2, Ontologia 1.4.1, Manual de Anotação, Constituição, White Paper, o prompt cognitivo em si (`build_system_prompt`, `_ontology_prompt_slice` — só ganharam um novo CAMINHO de envio via cache, texto idêntico), `gemini_cache.py` (reaproveitado sem alteração — `get_or_create_cached_content` já era genérico o bastante), `item_contract.py`, `ontology_validator.py`, `batch_queue.py` (schema da fila), qualquer arquivo do corpus (`sapiens_pipeline.pipelines`), qualquer arquivo de frontend.

---

## 8. Testes executados

```bash
# Suíte nova + a suíte relevante da 1ª rodada — 100% verde:
./.venv/bin/python -m pytest tests/test_gemini_retry_and_cache.py tests/test_batch_queue.py \
  tests/test_contratos_canonicos.py tests/test_prontidao_producao.py tests/test_sem_emergent.py \
  tests/test_book_thinking_level.py tests/test_adaptive_thinking.py -q
# 157 passed

# Suíte completa (mesmo padrão de falhas pré-existentes da 1ª rodada — testes de
# integração que exigem servidor em localhost:8001 + REACT_APP_BACKEND_URL,
# não relacionados a este código):
./.venv/bin/python -m pytest tests/ -q --ignore=tests/test_book_endpoints.py
# 164 passed, 14 failed / 6 errors — mesma causa raiz de sempre (sem servidor rodando),
# confirmado lendo o traceback de test_generate_pipeline: 404 "Not Found" de uma
# sessão requests contra um servidor que não está de pé, não um erro do código alterado.

# Verificação real e paga (pequena):
# - Thinking adaptativo: validado por simulação sobre dados já pagos — 0 chamadas novas.
# - Cache de PDF por caderno: 3 chamadas reais pequenas — ver §4.2. Custo: ≈ US$ 0,014 (≈ R$ 0,07).
```

---

## 9. Resumo direto — as 10 entregas pedidas ao final

1. **Custo antes/depois**: R$ 0,152/questão (MEDIUM fixo, estado antes desta rodada) → **≈ R$ 0,031/questão projetado** (thinking adaptativo + cache de PDF).
2. **Redução percentual**: **-79,8%** sobre o estado atual; **-90,3%** sobre o HIGH original (início da 1ª auditoria).
3. **Tokens de entrada antes/depois** (médio/questão, componente não-cacheado): ~181 → ~199 (leve aumento nominal — a soma de 2 chamadas quando escalona pesa mais que a fração de PDF que sai do não-cacheado e vai para o cache; o efeito dominante de queda é no cache lido, mais barato, e no thinking, muito menor).
4. **Tokens de thinking antes/depois** (médio/questão): 9.818 (MEDIUM fixo) → **167** (adaptativo, simulado) — **-98,3%**.
5. **Tokens de saída antes/depois** (médio/questão, só candidates, sem thinking): 1.848 → 1.922 (estável — a saída visível não muda de tamanho, só o raciocínio interno).
6. **Otimizações implementadas**: (1) thinking adaptativo LOW→MEDIUM condicionado à validação estrutural de produção; (2) cache do PDF do caderno inteiro, reaproveitando a infraestrutura de cache já existente.
7. **Otimizações descartadas, e por quê**: ver §6 — instrumentar retries do SDK (ganho incerto/custo alto), fatiar PDF por página (cache inteiro já resolve a maior parte sem esse mapeamento novo), qualquer redução de Schema/Ontologia (proibido pelo escopo).
8. **Arquivos alterados**: lista exata em §7.
9. **Testes executados**: suíte offline (157 testes relevantes, verde) + verificação real pequena (§4.2, ≈R$0,07) + simulação sem custo sobre dados já pagos (§4.1).
10. **Este relatório**: `auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI-2.md`.

---

## Critérios de aceitação — conferência

- ✅ Custo estimado por questão menor que o atual (R$0,152 → ≈R$0,031 projetado).
- ✅ Schema/validação continuam válidos (nenhuma mudança em `item_contract.py`/`ontology_validator.py`; o `judge` usado na escalada é o MESMO validador de produção).
- ✅ Nenhum conteúdo cognitivo importante removido (system prompt e ontologia enviados são byte-a-byte os mesmos — só mudou o CAMINHO de transporte, via cache).
- ✅ Testes relevantes continuam passando (157 testes, ver §8).
- ✅ Telemetria continua registrando custo/tokenização (`gemini_telemetry.py` não foi alterado; cada uma das até 2 chamadas do modo adaptativo grava seu próprio registro em `gemini_usage`, dando MAIS granularidade, não menos).
- ✅ Não reprocessou as 89 questões reais.
- ✅ Não gastou Gemini desnecessariamente (≈R$0,07 de gasto novo real; o resto foi simulação sobre dados já pagos).

---

## 10. Baseline aprovado (2026-08-22) e congelamento

O usuário aprovou explicitamente esta rodada como **baseline atual** do custo do pipeline Gemini, com o pedido de **não fazer nenhuma mudança estrutural nova no pipeline, Schema, Ontologia ou contratos cognitivos** até que a próxima otimização seja motivada por **telemetria real** (`db.gemini_usage`, já instrumentada desde a 1ª rodada) mostrando onde ainda há gasto relevante — não por outra rodada de estimativa/projeção.

Baseline registrado, textualmente:

- Thinking adaptativo LOW → MEDIUM (escalona só se a validação estrutural de produção reprovar).
- Máximo de 2 chamadas Gemini por questão.
- Cache do PDF por caderno (`book_cache_key`).
- Cache da ontologia (já existente desde a 1ª rodada, não alterado).
- 157 testes offline passando.
- Custo projetado ≈ R$ 0,031/questão.
- Redução projetada ≈ 79,8% vs. MEDIUM fixo (≈ 90,3% vs. HIGH original).

### 10.1 Ressalva descoberta após a aprovação — importante para o que "baseline" significa na prática

Ao responder, na mesma conversa, uma pergunta do usuário sobre seletor de thinking por caderno, foi identificado que **o único caminho de produção hoje usado para processar cadernos (`BookResults.jsx`, tela de resultados do caderno) sempre envia um `thinking_level` EXPLÍCITO** (`LOW`, `MEDIUM` ou `HIGH` — o dropdown "Thinking", com `LOW` como valor inicial do componente) em toda chamada a `POST /book/{id}/process`.

Por desenho (ver §3.1 e a docstring de `run_cognitive_pipeline_adaptive`), um `thinking_level` explícito **sempre desliga o modo adaptativo para aquela chamada** — é a escolha humana explícita, tratada como prioritária sobre qualquer heurística de custo. Como o frontend hoje NUNCA envia `thinking_level=None`/omitido nesse fluxo, **processar um caderno pela tela atual roda hoje em nível fixo (o que estiver selecionado no dropdown, com `LOW` puro por padrão), sem o escalonamento de segurança para `MEDIUM`** — ou seja, no perfil de risco de `otimizado_LOW` isolado (7/8 válidas na amostra da 1ª rodada), não no perfil `adaptativo` (8/8 válidas) que os números deste relatório celebram.

**Isto NÃO invalida a implementação de backend** (`run_cognitive_pipeline_adaptive` funciona exatamente como projetado, e os 3 outros pontos de produção — `/pipeline/generate`, `/pipeline/{id}/regenerate`, e o caminho de fila via `annotation_pipeline.generate_and_persist` — não enviam `thinking_level` e portanto JÁ se beneficiam do modo adaptativo hoje, sem qualquer mudança adicional). O que fica pendente é só o frontend do caderno: ele precisaria de uma 4ª opção no dropdown (algo como "ADAPTIVE — recomendado", que mapeia para `thinking_level: null`/campo omitido) para que o processamento de caderno pela UI também rode no perfil validado neste relatório.

**Não corrigido nesta tarefa** — por instrução explícita do usuário de congelar o pipeline após a aprovação. Fica registrado aqui para decisão explícita antes de ser tratado.
