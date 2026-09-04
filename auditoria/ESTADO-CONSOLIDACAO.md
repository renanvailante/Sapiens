# Estado da Consolidação de Contratos — Sapiens

**Registrado em:** 2026-08-17T00:58:27Z
**Regra arquitetural vigente:** `pipeline/docs/` é a ÚNICA fonte canônica do ecossistema Sapiens. Qualquer schema, ontologia, modelo ou contrato definido fora dela — em qualquer um dos 3 apps, independentemente de nome ou versão — é NÃO-CANÔNICO por definição, mesmo que coincida em conteúdo com o que os docs descrevem.

Este documento é um retrato do estado real do código nesta data. Não é um plano — é o que já existe, o que ainda não existe, e onde a arquitetura foi deliberadamente deixada em aberto por falta de contrato canônico. `pipeline/docs/` não foi alterado por nenhuma das ações registradas aqui.

---

## 1. Contratos com definição canônica em `pipeline/docs/` e ALINHADOS nos 3 apps

### 1.1 Ontologia Cognitiva
- **Fonte canônica:** `pipeline/docs/ontology/ontology_v1.4.json` (versão `"1.4"`, 11 domínios, 12 competências, 25 processos cognitivos, 56 habilidades observáveis, 13 tipos de erro, 11 intervenções pedagógicas).
- **Estado:** `pipeline/backend/ontology_seed.py` carrega esse JSON diretamente do disco em runtime (não há mais cópia digitada à mão). A ontologia ativa no Mongo do pipeline é `1.4`, confirmado via `GET /ontology/summary` nesta data.
- **Migração:** a ontologia antiga (`1.0.0-seed`, uma seed inventada e divergente do canônico) foi **arquivada** (`is_active:false`) no boot, não deletada. Segue no banco como registro histórico.
- **`professor`**: dados de demonstração (`SAMPLE_NOS` em `professor/backend/server.py`) usam IDs e nomes de processo extraídos verbatim do `ontology_v1.4.json` (ex.: `PROC-QUANT-02`), em vez dos IDs inventados que existiam antes (`MAT.NUM.01` etc.).
- **`pipeline` (motor de anotação)**: `cognitive_engine.py:run_cognitive_pipeline` já injetava a ontologia *ativa* no prompt do Gemini com a instrução "use apenas estes IDs" — como a ontologia ativa agora é a v1.4 real, qualquer anotação nova gerada a partir de hoje usa IDs canônicos automaticamente. Nenhuma mudança de código foi necessária nesse ponto além de corrigir a fonte da ontologia ativa.

### 1.2 Behavior / Evento de resposta do aluno
- **Fonte canônica:** `pipeline/docs/behavior/07 behavior student 1.4.md` — schema do evento: `schema_version, event_id, attempt_id, student_id, item_id, item_schema_version, item_hash, timestamp, contexto{tipo,prova_id,origem}, resposta{alternativa_escolhida,acertou}, desempenho{tempo_resposta_segundos,numero_tentativas,mudou_resposta}, status, metadados{dispositivo,versao_aplicacao}`.
- **Estado:** `aluno/backend/firestore_service.py:write_behavior_event` é a **única** implementação de escrita de evento de resposta no sistema, e reproduz esse schema campo a campo, gravando em `students/{uid}/behavior/{event_id}` no Firestore. É chamada por `POST /api/students/me/answer`.
- **Leitura administrativa**: `GET /api/students` e `GET /api/students/{id}/history` (consumidas pela página `/admin/history` do frontend do aluno) agora leem exclusivamente dessa fonte canônica via Firestore collection-group query — não existe mais nenhum caminho de leitura alternativo.

---

## 2. Implementações antigas/duplicadas DESATIVADAS ou SUBSTITUÍDAS

| O que existia | Onde | O que aconteceu |
|---|---|---|
| Ontologia `1.0.0-seed` (dict hardcoded, divergente da v1.4) | `pipeline/backend/ontology_seed.py` | Substituída por carregamento direto do JSON canônico. O registro antigo permanece no Mongo com `is_active:false` (preservado, não apagado). |
| Backfill parcial de `habilidades_observaveis` copiando 1 campo do v1.4 pra qualquer ontologia ativa | `pipeline/backend/server.py:_maybe_backfill_habilidades` | Removido — era um remendo do problema que a correção da ontologia tornou desnecessário. |
| `StudentResponseEvent`/`ResponseEventIn` (Mongo `response_events`, campos `aluno_id`, `data_hora_resposta`, `tempo_resposta_seg`, `metadata_tecnica` — incompatíveis com o schema canônico de behavior) | `aluno/backend/events_models.py`, rotas `POST /events/responses[/bulk]` em `events_routes.py` | Arquivo `events_models.py` deletado. Rotas de escrita removidas. Coleção Mongo tinha 0 documentos — nada foi perdido. |
| `StudentInterventionEvent`/`InterventionEventIn` (Mongo `intervention_events`) | idem | Removido junto — não tinha (e não tem) contrato canônico correspondente em `pipeline/docs` (ver §3). Coleção tinha 0 documentos. |
| Leitura de histórico do aluno via Mongo `response_events` + join com `question_annotations` | `aluno/backend/events_routes.py` (rotas `GET /students`, `GET /students/{id}/history`) | Reescrita para ler do Firestore canônico (`students/{uid}/behavior`) em vez do Mongo paralelo. A feature (`/admin/history` no frontend) foi **preservada**, não removida — só teve a fonte de dados trocada. Efeito colateral positivo: a nova leitura expõe alunos com eventos reais que a rota antiga nunca via, pois `response_events` estava sempre vazio. |
| Painel de "Intervenções" na tela `/admin/history` | `aluno/frontend/src/pages/StudentHistory.jsx` | Removido da UI (não recriado sobre base nova) — não há contrato canônico de evento de intervenção para sustentá-lo (ver §3). |
| IDs de nó inventados no seed de demonstração do professor (`MAT.NUM.01`, `POR.INT.01`, `CIE.BIO.01` etc.) | `professor/backend/server.py:SAMPLE_NOS` | Substituídos por IDs/nomes reais de `ontology_v1.4.json`. |
| Versões de taxonomia fictícias ("Taxonomia Sapiens v0.8/v0.9 Experimental") no seed de demonstração do professor | `professor/backend/server.py:seed_sample_data` | Substituídas por `"Ontologia Cognitiva Sapiens v1.3"` / `"v1.4"` — únicas versões realmente referenciadas nos docs (`based_on: "1.3"` dentro do próprio `ontology_v1.4.json`). |
| Página de Ontologia do pipeline exibindo campos do schema antigo (`descricao`, `categoria`, `dominio` singular) | `pipeline/frontend/src/pages/Ontology.jsx` | Atualizada para exibir os campos reais do v1.4 (`definicao_operacional`, `dominios[]`, `competencia`, `tipos_erro[]`, `processos[]`, `origem_v1_3[]`, `evidencia_observavel`, `intervencao`). |
| Botões/mensagens "Resetar para versão 1.0" / "ontologia semente (1.0.0-seed)" | `pipeline/backend/server.py`, `pipeline/frontend/src/pages/Ontology.jsx` | Texto atualizado para refletir que o reset restaura a versão canônica, não uma seed própria. |

---

## 3. Contratos SEM especificação canônica em `pipeline/docs/` — nada foi inventado

### 3.1 Item / Questão — o mais importante
`pipeline/docs/` **não define** um schema formal de item/questão (campos como `item_id`, `enunciado`, `alternativas`, `gabarito`, `resource_ids`, versionamento de item). A Constituição (`constitution/02 Constituicao Sapiens.md`) declara explicitamente que Item/Questão é um objeto **externo** à ontologia, e delega seu schema a um documento chamado "Especificação Técnica" — **que não existe em nenhum lugar do repositório**.

Consequência prática, deixada como está:
- `pipeline/backend/cognitive_engine.py:DEFAULT_PIPELINE_SCHEMA` define um formato de item própro do pipeline (`enunciado`, `alternativas[].letra/.texto`, `resposta_correta`), usado para instruir o Gemini.
- `aluno/backend` mantém seu próprio formato em `questoes_master`/`questoes_public` (Mongo), com nomenclatura parecida mas não formalmente derivada de nada canônico.
- `pipeline` gera `item_id` como `uuid.uuid4()` puro; `aluno` gera um `item_id` **novo e diferente** a cada sync do Firestore (`uuid.uuid4().hex`), sem reaproveitar o id de origem do pipeline.

Nenhuma dessas três coisas foi tocada. Unificá-las exigiria inventar um contrato — o que foi explicitamente proibido. **Para desbloquear essa unificação, `pipeline/docs/` precisa ganhar um documento de schema de item/questão** (ex.: `pipeline/docs/item/` ou equivalente).

### 3.2 Evento de Intervenção Pedagógica (aplicada por professor a aluno)
Os docs definem "Intervenção Pedagógica" **somente** como nó de catálogo da ontologia (indexado a Tipo de Erro), nunca como um evento de aplicação professor→aluno com timestamp, autor, etc. O White Paper chama essa camada explicitamente de "slot vazio" (§12.4). Por isso:
- O contrato antigo (`StudentInterventionEvent`) foi removido, não substituído.
- Nenhuma funcionalidade de "professor registra intervenção" existe hoje no código — e não deveria existir até `pipeline/docs/` definir esse contrato.

### 3.3 Turmas, matrícula e vínculo professor↔aluno
Não há menção a "turma" ou "professor" em nenhum documento de `pipeline/docs/`. O app `professor` continua operando sobre sua própria estrutura de dados (`imports`, `Class`/`Enrollment` implícitos), sem nenhuma tentativa de fazê-la "canônica" — porque não há nada em `pipeline/docs/` para alinhar com.

---

## 4. Partes que ainda dependem da Emergent em runtime

(Inalteradas — fora de escopo desta rodada, por instrução explícita do usuário; migração futura planejada.)

| Onde | O quê |
|---|---|
| `aluno/backend/ai_service.py` | Diagnóstico cognitivo (Claude Sonnet 4.5) e OCR de gabarito (Gemini Vision) via proxy `emergentintegrations`, autenticado com `EMERGENT_LLM_KEY`. |
| `aluno/backend/auth.py` | Login com Google depende de `auth.emergentagent.com` / `demobackend.emergentagent.com`. |
| `pipeline/backend/storage.py` | Todo binário do pipeline (PDFs originais, extrações) é armazenado no object storage hospedado pela Emergent, autenticado com `EMERGENT_LLM_KEY`. |
| `pipeline/backend/requirements.txt`, `aluno/backend/requirements.txt` | `emergentintegrations` e `litellm` exigem índice pip privado da Emergent (`d33sy5i8bnduwe.cloudfront.net`) para instalar — não estão no PyPI público. |

O script `assets.emergent.sh` e o PostHog com session recording já haviam sido removidos dos 3 `index.html` numa rodada anterior (client-side apenas) — isso não muda o quadro acima, que é 100% backend/runtime.

---

## 5. Pontos deixados deliberadamente sem alteração, por ausência de contrato canônico

- Formato/geração de `item_id` em `pipeline` e `aluno` (dois esquemas divergentes, nenhum dos dois "corrigido" — ver §3.1).
- `questoes_master`/`questoes_public` (Mongo do aluno) e `DEFAULT_PIPELINE_SCHEMA` (pipeline) — não unificados.
- Ausência de vínculo `item_id` estável entre o que o pipeline gera e o que o aluno lê do Firestore `itens`.
- Funcionalidade de intervenção pedagógica aplicada por professor — removida, não reimplementada.
- Estrutura de dados de turma/matrícula do `professor` — mantida como está, sem tentativa de alinhamento (não há o que alinhar).
- Testes de integração do pipeline (`pipeline/backend/tests/test_ontology_reset_import.py`, `pipeline/backend/tests/backend_test.py`) tiveram apenas as strings de versão corrigidas (`"1.0.0-seed"` → `"1.4"`); **não foram executados** — dependem de infraestrutura residual da Emergent (`REACT_APP_BACKEND_URL`, `/app/frontend/.env`) e, desde a última rodada, também precisariam do header `X-API-Key`. Ficaram corretos no código, não confirmados em execução.
- Migração/remoção das dependências de Emergent em runtime (§4) — explicitamente fora de escopo desta rodada, por instrução do usuário.

---

## Verificação de integridade nesta data

```
$ curl .../ontology/summary → version: "1.4"  (confirmado ao vivo)
$ git status --short pipeline/docs/  → vazio (nenhuma edição minha; 1 arquivo pré-existente
                                        não versionado, presente desde antes desta sessão)
$ grep response_events|StudentResponseEvent|events_models (código) → nenhuma ocorrência,
                                        exceto comentário explicativo em events_routes.py
$ grep EMERGENT_LLM_KEY|emergentintegrations|emergentagent → ai_service.py, auth.py,
                                        storage.py (inalterado, conforme §4)
```
