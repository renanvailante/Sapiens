# Auditoria completa — migração para o contrato canônico de Item/Questão (Schema 2.1)

**Registrado em:** 2026-08-17T03:16:30Z
**Fonte canônica:** `pipeline/docs/Schema anotador de questoes/06 Schema Sapiens 2.1.json.md` (`schema_version: "2.1"`) — único contrato de item/questão válido. Qualquer schema fora de `pipeline/docs/` é legado/não-canônico por definição, independentemente do quão parecido seja.
**Método:** leitura de código nos 3 apps + inspeção de dados reais (Mongo local + Firestore real do projeto `sapiens-dataset`). Nenhum arquivo alterado — nem código, nem `pipeline/docs/`.

Esta auditoria aprofunda e substitui em detalhe `auditoria/AUDITORIA-SCHEMA-ITEM-2.1.md` (2026-08-17T02:53Z), que já havia estabelecido o veredito NÃO ALINHADO. Aqui o foco é: onde tocar, o que diverge campo a campo, e o risco de migrar.

> **Atualização — 2026-08-17T03:39:56Z:** o usuário confirmou que os 20 documentos da coleção Firestore `itens` (citados na §5 abaixo) são **exclusivamente dados de teste/seed**, sem necessidade de preservação. Isso **reclassifica o risco da §5 de "Médio" para "Nenhum"** — não há mais avaliação de perda de completude a fazer sobre esses documentos, porque nenhum dado real está em jogo. **A migração dos 20 itens existentes fica marcada como DESNECESSÁRIA.** O plano de descarte seguro está em `auditoria/PLANO-RESET-ITENS.md` (mesma data). Todo o resto desta auditoria (mapa de leitura/escrita, formatos paralelos, divergência de campos, componentes a migrar) permanece válido — a atualização afeta somente a avaliação de risco de dados da §5.

---

## 1. Mapa de leitura/escrita/transformação de itens, por app

### `pipeline`
| Ponto | Arquivo:linha | Ação |
|---|---|---|
| `run_cognitive_pipeline` | `backend/cognitive_engine.py:238` | **Gera** o item (chamada Gemini), na saída usa `DEFAULT_PIPELINE_SCHEMA` (Formato A, §2). |
| `build_system_prompt` | `backend/cognitive_engine.py:158` | Serializa `DEFAULT_PIPELINE_SCHEMA` (ou schema custom importado via `/schema/import`) como instrução ao modelo — é a fonte da forma real do JSON gerado. |
| `generate_pipeline` | `backend/server.py:492` | **Escreve**: `question_id = uuid4()` (não determinístico), grava `{id, created_at, updated_at, ontology_version, artifacts, pipeline: <saída do Gemini>, ...indexado}` em Mongo `pipelines`. |
| `_index_fields` | `backend/server.py:444` | **Transforma**: extrai `disciplina/banca/ano/tema/resposta_correta/processos/competencias/dominios` de dentro de `pipeline.questao`/`pipeline.classificacao` para colunas de índice/filtro — depende inteiramente da forma do Formato A. |
| `update_pipeline`, `regenerate_pipeline` | `backend/server.py:634,663` | **Atualiza** o mesmo documento in-place (sobrescreve `pipeline{}`), sem versionamento de conteúdo. |
| `create_question_sync`/`update_question_sync` | `backend/firestore_sync.py:293,313` | **Espelha** o documento Mongo inteiro (Formato A) para a coleção Firestore configurada em `FIRESTORE_COLLECTION` (hoje `itens`, confirmado nesta auditoria: 20 documentos reais, todos no Formato A). |
| Frontend — `Gerador de Pipeline`, `Questões Processadas` | `frontend/src/pages/*.jsx` | **Lê/exibe** os campos do Formato A diretamente (`.questao.enunciado`, `.classificacao.processos_cognitivos` etc. — não verificado campo a campo nesta rodada, mas a API que alimenta essas telas é a mesma acima). |

### `aluno`
| Ponto | Arquivo:linha | Ação |
|---|---|---|
| `firestore_sync` (admin) | `backend/admin_routes.py:96` | **Lê** todos os docs de Firestore `itens` (Formato A) → grava verbatim em Mongo `questoes_master` (upsert por `id` original do pipeline). |
| `_build_public_doc` | `backend/admin_routes.py:67` | **Transforma** cada `master` em versão pública: tenta ler `fonte{}`/`questao.recursos` (nomes do canônico, mas o pipeline nunca os preenche) → grava em `questoes_public` com **novo `item_id` aleatório** a cada sync. |
| `update_questao_master` | `backend/admin_routes.py:141` | **Edita** um doc master manualmente via admin e regenera o público correspondente. |
| `GET /questoes` | `backend/server.py:49` | **Lê** `questoes_public` para o app do aluno consumir (feed de questões "reais" fora do fluxo ENEM). |
| `/admin/annotations` (`AnnotationPayload`) | `backend/annotation_routes.py`, `annotation_models.py` | **Escreve** um contrato de item **independente** (Formato C, §2) em Mongo `question_annotations`, via upload manual — não deriva do pipeline nem do Firestore `itens`. |
| `compute_cognitive_profile` / `_build_item_hash_map` | `backend/annotation_service.py:45,124` | **Lê** Firestore `itens` esperando `pipeline.estrutura_cognitiva.{dominios,competencias,processos}` (Formato D, §2) — nomenclatura do canônico, aninhamento e origem errados; **nunca casa** com os 20 documentos reais (confirmado: todos têm `pipeline.classificacao`, nenhum tem `pipeline.estrutura_cognitiva`). |
| `exam_routes.py` (`Exam`/`AnswerKey`) | `backend/models.py:78-101` | **Modelo relacionado, não sobreposto**: só `number`+`letter` (gabarito de prova ENEM oficial), sem `enunciado`/`alternativas`. Não é um 5º formato de item porque não representa conteúdo de questão — mas também não referencia `item_id` do Schema 2.1 em lugar nenhum. |
| `feed_models.py` (`FeedItem`) | `backend/feed_models.py:24` | **Formato E** (§2): conteúdo de aprendizado autoral/demo, com `answer_options[{key,label,is_correct}]` — próprio docstring do módulo diz que é "placeholder" aguardando integração cognitiva futura (`cognitive_mapping_reference`/`difficulty_reference` ficam como string vazia). Não deriva do pipeline. |

### `professor`
Confirmado novamente nesta rodada: **nenhum ponto de leitura, escrita ou transformação de item/questão** em `professor/backend/server.py` ou no frontend (`grep` por `enunciado`, `alternativas`, `item_id`, `questao` retorna vazio). Opera só sobre `imports` (agregados por `no_id`, não itens individuais).

---

## 2. Todos os schemas/formatos paralelos encontrados (nenhum é canônico)

| Formato | Onde vive | Natureza |
|---|---|---|
| **A** | `pipeline/backend/cognitive_engine.py:DEFAULT_PIPELINE_SCHEMA` | O que o Gemini realmente gera. Fonte de tudo que existe hoje em Mongo `pipelines` e Firestore `itens` (20 docs reais). |
| **B** | `aluno/backend/admin_routes.py:_build_public_doc` → `questoes_master`/`questoes_public` | Reshape do Formato A, parcialmente com nomes do canônico, mas campos vazios na prática e `item_id` não determinístico. |
| **C** | `aluno/backend/annotation_models.py` → `question_annotations` | Contrato de ingestão manual independente (rota `/admin/annotations`, real, 0 docs hoje). |
| **D** | `aluno/backend/annotation_service.py` (expectativa de leitura) | Não é um schema gravado em lugar nenhum — é uma **expectativa de leitura** que usa nomenclatura do canônico (`estrutura_cognitiva/processos/competencias/dominios`) mas aninhamento e origem que não existem nos dados reais. |
| **E** | `aluno/backend/feed_models.py:FeedItem` | Conteúdo de feed autoral/demo, com resposta certa embutida em `answer_options[].is_correct` — admitidamente provisório, não deriva do pipeline. |
| *(relacionado, não item)* | `aluno/backend/models.py:Exam/AnswerKey` | Gabarito puro (número+letra), sem conteúdo de questão — não conflita diretamente com o Schema 2.1 mas também não referencia `item_id` canônico. |

Todos os cinco (A–E) são não-canônicos por definição, conforme a regra estabelecida. Nenhum documento de `pipeline/docs/` foi usado como fonte de nenhum deles até hoje.

---

## 3. Divergência campo a campo contra o Schema 2.1

### Topo do objeto
| Campo canônico | Formato A (pipeline) | Formato B (aluno público) | Formato C (annotation) |
|---|---|---|---|
| `schema_version` | ausente | ausente | presente, mas nunca `"2.1"` |
| `item_id` | `uuid4()` aleatório | `uuid4().hex` aleatório, **novo a cada sync** | livre (string qualquer no payload) |
| `item_hash` | ausente | ausente | ausente (existe em outro lugar: `firestore_service.compute_item_hash`, usado só para eventos de behavior, nunca gravado no próprio item) |
| `fonte{}` | não existe como objeto — campos soltos em `questao.{disciplina,banca,ano,tema}` | tenta ler `fonte{disciplina,ano,prova,banca,tema,conteudo}` — **campos ficam vazios** pois A nunca os produz | `fonte{banca,ano,caderno,numero}` — sem `prova/disciplina/tema/conteudo/arquivo_origem/pagina` |

### `questao{}`
| Campo canônico | Formato A | Formato B | Formato C |
|---|---|---|---|
| `enunciado` | presente | presente (herdado de A) | presente |
| `alternativas[].letra` | presente | presente | ausente — C usa `id` em vez de `letra` |
| `alternativas[].texto` | presente | presente | presente |
| `alternativas[].correta` | **ausente** — resposta fica em `questao.resposta_correta`, fora do array | presente na leitura, mas nunca populado por A | **ausente** — C usa `gabarito` solto no item, não por alternativa |
| `recursos.imagens/graficos/tabelas/formulas` | só `figuras_detectadas[{descricao}]`, sem `id`/`tipo`/`arquivo`/`ocr`, sem separar gráficos/tabelas/fórmulas | tenta ler `questao.recursos` — vazio na prática | ausente |

### `estrutura_cognitiva{}`
| Campo canônico | Formato A (`classificacao{}`) | Formato D (expectativa) |
|---|---|---|
| `dominios[{id,peso_no_item,confianca}]` | `dominios: [string]` — lista solta de IDs, sem peso/confiança | espera objetos, mas lê de chave que nunca existe |
| `competencias[{id,peso_no_item,confianca}]` | `competencias: [string]` — idem | idem |
| `processos[{id,papel,peso_no_item,confianca,dificuldade_local,habilidades[],evidencias{trechos,figuras},justificativa}]` | `processos_cognitivos[{id,papel,justificativa:{trechos_enunciado,elementos_figura,regras_ontologia,por_que_este_papel}}]` — **sem** `peso_no_item`, `confianca`, `dificuldade_local`, `habilidades[]` aninhadas; `justificativa` é objeto estruturado em A, string simples no canônico; `evidencias` não existe como chave própria (fica espalhada dentro de `justificativa`) | nomes batem (`processos`), mas nunca há dado real correspondente |
| `habilidades` (dentro de cada processo) | **solta** em `habilidades_observaveis: [string]`, no nível de `classificacao`, não aninhada por processo | — |

### `distratores[]`
| Campo canônico | Formato A |
|---|---|
| `alternativa` | presente |
| `erro` (string ID, ex. `"ERR-01"`) | `tipo_erro_id` — mesmo papel, nome diferente |
| `plausibilidade` | ausente |
| `probabilidade_estimada` | ausente |
| `processos_afetados[]` | ausente |
| `explicacao` | presente |

Formato C (`DistratorAnalise`) diverge ainda mais: `error_type_id` é **inteiro**, não string com ID da ontologia — incompatibilidade de tipo, não só de nome.

### `intervencoes[]`, `pedagogia{}`, `psicometria{}`, `pipeline{}` (metadados de execução), `qualidade{}`
- **`intervencoes[]`**: Formato A tem só `intervencoes_sugeridas: [string]` (lista de IDs) — sem `gatilho{processo,erro}`, `acao`, `prioridade`. Formato C tem uma única `Intervencao{cognitive_process_id,tipo}` embutida dentro de `Pedagogia.principal_intervencao`, não uma lista.
- **`pedagogia{}`**: não existe em A. Existe parcialmente em C (`explicacao_resolucao`, `misconceptions[]`), mas sem `estrategia`, `passos[]`, `erros_comuns[]`, `dicas[]`, `tempo_estimado_segundos`, `nivel_dificuldade`.
- **`psicometria{}`**: não existe em nenhum formato hoje. Nenhum dos apps calcula `dificuldade_empirica`, `discriminacao`, `taxa_acerto` ou `tempo_medio` a partir de dados reais de resposta.
- **`pipeline{}`** (metadados do modelo — `modelo`, `versao_prompt`, `tokens_entrada/saida`, `tempo_processamento_segundos`, `necessita_revisao`): não existe em nenhum formato. Colisão de nome grave: em Formato A, a chave `"pipeline"` no documento Mongo/Firestore guarda o **payload inteiro da anotação**, não metadados de execução — se a migração usar o nome `pipeline{}` do canônico sem primeiro renomear/remover essa chave existente, há colisão direta de namespace.
- **`qualidade{}`**: Formato A não tem. Formato C tem `QualidadeAnotacao{confianca_global,revisado_humano,revisor,data}` — parecido em espírito, mas `revisado_humano` (C) vs `revisado` (canônico), `data` (C) vs sem equivalente direto no canônico.

---

## 4. Componentes que precisariam ser migrados

Lista de arquivos que tocam diretamente a forma do item e precisariam mudar para adotar o Schema 2.1 (nenhum foi alterado nesta auditoria):

**pipeline**
- `backend/cognitive_engine.py` — `DEFAULT_PIPELINE_SCHEMA` inteiro, `_SYSTEM_PROMPT_TEMPLATE` (a instrução dada ao Gemini precisa pedir o formato 2.1).
- `backend/server.py` — `generate_pipeline` (geração de `item_id` determinístico em vez de `uuid4()`; parar de aninhar o payload sob a chave `"pipeline"`), `_index_fields` (campos de origem mudam de `classificacao.*` para `estrutura_cognitiva.*`), `update_pipeline`/`regenerate_pipeline`.
- `backend/firestore_sync.py` — nenhuma mudança estrutural própria (é um mirror genérico), mas o **conteúdo** espelhado muda de forma.

**aluno**
- `backend/admin_routes.py` — `_build_public_doc` (reescrever para ler a partir do Schema 2.1 real, não mais tentar adivinhar `fonte`/`recursos` que hoje nunca vêm preenchidos); parar de gerar `item_id` aleatório e passar a propagar o `item_id` determinístico do canônico.
- `backend/annotation_models.py` + `backend/annotation_routes.py` — `AnnotationPayload`/`Item`/`ProcessoAtivado`/`DistratorAnalise`/`Intervencao`/`Pedagogia`/`QualidadeAnotacao` — todo o Formato C precisaria ser reescrito ou aposentado em favor do 2.1.
- `backend/annotation_service.py` — `_build_item_hash_map`/`compute_cognitive_profile` precisam ler `estrutura_cognitiva` do **topo** do item (não de `pipeline.estrutura_cognitiva`) e no formato de objetos com `id/peso_no_item/confianca`, não listas soltas.
- `backend/feed_models.py`/`feed_seed.py` — decisão de produto pendente: o Feed continua sendo conteúdo autoral solto (Formato E, fora do escopo do Schema 2.1) ou passa a poder referenciar itens reais via `item_id` canônico?

**professor**
- Nenhum arquivo — não há consumo de item hoje.

---

## 5. Risco de perda de dados / incompatibilidade numa eventual migração

Contagens reais nesta data (Mongo local + Firestore real do projeto):

| Coleção | Documentos | Risco |
|---|---|---|
| `pipeline` Mongo `pipelines` | 1 | ~~Baixo~~ → **Nenhum** (atualizado 2026-08-17T03:39:56Z) — confirmado como o mesmo documento de teste gerado nesta sessão de auditoria (`id: b912a1b8-...`, enunciado literal "Nenhuma questão detectada..."). Usuário confirmou: dado de teste/seed, sem necessidade de preservação ou migração. Ver `auditoria/PLANO-RESET-ITENS.md`. |
| Firestore `itens` | **20** | ~~Médio~~ → **Nenhum** (atualizado 2026-08-17T03:39:56Z) — usuário confirmou que os 20 documentos são exclusivamente dados de teste/seed, sem necessidade de preservação. **Migração destes itens específicos fica marcada como DESNECESSÁRIA.** Um deles (`b912a1b8-...`) é o mesmo doc de teste do Mongo `pipelines` acima; os outros 19 são questões ENEM de teste sem vínculo com nenhum Mongo local desta sessão. Ver plano de descarte em `auditoria/PLANO-RESET-ITENS.md`. |
| Mongo aluno `questoes_master`/`questoes_public` | 0 / 0 | Nenhum risco — vazias. |
| Mongo aluno `question_annotations` | 0 | Nenhum risco — vazia. |
| Mongo aluno `feed_items` | 15 | Baixo, mas **não migrável 1:1** — são conteúdo autoral (não vieram do pipeline), sem `item_id`/`fonte` reais. Preservar exigiria decidir se viram itens "manuais" com `item_id` cunhado ad-hoc ou se ficam fora do escopo do Schema 2.1 permanentemente. |
| Mongo aluno `exams`/`answer_keys` | 2 / 3 | Nenhum risco de perda — são gabaritos ENEM oficiais, não item completo; não colidem com o 2.1. |
| Mongo aluno `analyses` (tentativas de prova de usuários) | 1 | **Atenção séparada**: referenciam `exam_id`/`number`, não `item_id`. Uma migração de item não afeta essa coleção diretamente, mas se no futuro as provas ENEM também passarem a ser representadas como itens Schema 2.1, o vínculo `analyses.number → item_id` precisaria ser estabelecido sem quebrar o histórico já gravado. |

**Incompatibilidade estrutural mais séria para qualquer migração futura:** a colisão de nome da chave `"pipeline"` (payload inteiro da anotação, no formato Mongo/Firestore atual) contra `pipeline{}` (metadados de execução do modelo) do Schema 2.1. Qualquer script de migração precisa tratar essa chave explicitamente — um `merge`/`spread` ingênuo sobrescreveria os dados de um pelo do outro.

**Nenhuma ação de migração foi executada nesta auditoria** — apenas mapeamento e avaliação de risco, conforme solicitado.
