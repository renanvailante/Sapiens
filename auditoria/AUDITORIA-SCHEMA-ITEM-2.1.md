# Auditoria read-only — Contrato canônico de Item/Questão (Schema Sapiens 2.1)

**Registrado em:** 2026-08-17T02:53:12Z
**Fonte canônica auditada:** `pipeline/docs/Schema anotador de questoes/06 Schema Sapiens 2.1.json.md` (`schema_version: "2.1"`)
**Método:** leitura de código nos 3 apps (pipeline, aluno, professor) + inspeção de dados reais em Mongo/Firestore. Nenhum arquivo foi alterado, incluindo `pipeline/docs/`.

**Veredito geral: NÃO ALINHADO.** Nenhum dos 3 apps produz, persiste ou consome o Schema Sapiens 2.1 hoje. Existem **quatro** formatos de item/questão diferentes e mutuamente incompatíveis em uso simultâneo no código, nenhum deles o canônico.

---

## O contrato canônico (referência rápida)

Topo: `schema_version, item_id, item_hash, fonte{banca,ano,prova,numero,disciplina,tema,conteudo,arquivo_origem,pagina}, questao{enunciado,alternativas[{letra,texto,correta}],recursos{imagens,graficos,tabelas,formulas}}, estrutura_cognitiva{dominios[],competencias[],processos[{id,papel,peso_no_item,confianca,dificuldade_local,habilidades[],evidencias{trechos,figuras},justificativa}]}, distratores[{alternativa,erro,plausibilidade,probabilidade_estimada,processos_afetados,explicacao}], intervencoes[{id,gatilho{processo,erro},acao,prioridade}], pedagogia{estrategia,passos,erros_comuns,dicas,tempo_estimado_segundos,nivel_dificuldade}, psicometria{dificuldade_empirica,discriminacao,taxa_acerto,tempo_medio}, pipeline{modelo,versao_prompt,versao_pipeline,tokens_entrada,tokens_saida,tempo_processamento_segundos,necessita_revisao}, qualidade{confianca_global,revisado,revisor,observacoes}`.

`item_id` deve ser determinístico e estável entre pipeline/Firestore/aluno/professor (ex. `ITEM-ENEM-2024-CAD01-Q023`).

---

## Os quatro formatos em uso hoje (nenhum é o 2.1)

### Formato A — `pipeline/backend/cognitive_engine.py:DEFAULT_PIPELINE_SCHEMA`
É o schema que o Gemini realmente recebe como instrução de saída (`server.py:build_system_prompt`), e portanto o formato real de tudo que o pipeline gera hoje.

- `questao{disciplina,banca,ano,tema,enunciado,alternativas[{letra,texto}] (sem "correta"!),resposta_correta (fora de alternativas),figuras_detectadas}` — sem objeto `fonte` separado, sem `recursos.imagens/graficos/tabelas/formulas` estruturados.
- `classificacao{dominios[strings],competencias[strings],processos_cognitivos[{id,papel,justificativa}] (sem peso_no_item/confianca/dificuldade_local/habilidades aninhadas),habilidades_observaveis[lista solta, não aninhada em processos],distratores[{alternativa,tipo_erro_id,explicacao}] (sem plausibilidade/probabilidade_estimada/processos_afetados),tipos_erro_previstos[lista solta],intervencoes_sugeridas[lista solta de IDs, não objetos]}`.
- Sem `pedagogia{}`, sem `psicometria{}`, sem `pipeline{}` (metadados do modelo), sem `qualidade{}`, sem `item_id`/`item_hash`/`schema_version` no próprio JSON.
- **Persistência (Mongo `pipelines` / espelho Firestore):** `server.py:generate_pipeline` grava `{id: uuid4(), created_at, updated_at, ontology_version, artifacts, pipeline: <Formato A>, ...campos indexados}`. A chave `"pipeline"` aqui guarda o payload inteiro da anotação — colisão de nome com o `pipeline{}` do contrato canônico, que é só metadados de execução do modelo (modelo, tokens, versão do prompt).
- **`item_id`:** `question_id = str(uuid.uuid4())` — aleatório, não determinístico, viola a recomendação explícita do contrato canônico.

### Formato B — `aluno/backend/admin_routes.py:_build_public_doc` (→ `questoes_master` / `questoes_public`)
Sincroniza da coleção Firestore `itens` (escrita pelo pipeline no Formato A) para dois formatos próprios do aluno.

- Já tenta ler `fonte{disciplina,ano,prova,banca,tema,conteudo}` e `questao.recursos` — nomenclatura **mais próxima do canônico** que o próprio pipeline produz hoje. Só que como o pipeline nunca escreve um objeto `fonte` (Formato A é flat), essa leitura resulta em campos vazios/`None` na prática.
- `item_id` é regenerado **aleatoriamente a cada sync** (`uuid.uuid4().hex`) — nem determinístico nem estável entre pipeline e aluno, violação direta e explícita da regra do contrato ("deve permanecer invariável entre pipeline, Firestore, aluno e professor").
- Não carrega `estrutura_cognitiva`, `distratores`, `intervencoes`, `pedagogia`, `psicometria`, `pipeline{}` ou `qualidade{}` — o comentário do próprio código diz que é proposital ("nenhum processo cognitivo/domínio/competência/metadado interno"), mas isso significa que o formato público do aluno não é um subconjunto declarado do 2.1, é um formato à parte.

### Formato C — `aluno/backend/annotation_models.py` (→ Mongo `question_annotations`, rotas `/admin/annotations`)
Um terceiro contrato de ingestão, completamente independente dos Formatos A e B, alimentado por upload manual via `/admin/annotations` (feature real, roteada em `/admin/annotations` no frontend; 0 documentos no banco local hoje).

- `Item{id, fonte{banca,ano,caderno,numero} (sem prova/disciplina/tema/conteudo/arquivo_origem/pagina), disciplina, tema_objetivo, conteudo_curricular[], enunciado, alternativas[{id,texto}] (sem "correta"; usa "id" em vez de "letra"), gabarito (campo separado, não dentro da alternativa)}`.
- `ProcessoAtivado{cognitive_process_id (não "id"), papel, prioridade (não existe no canônico), peso_ativacao (canônico chama peso_no_item), confianca, dificuldade_local, evidencias: list[str] (canônico separa em trechos[]/figuras[])}` — sem `habilidades[]` aninhadas.
- `DistratorAnalise.error_type_id` é tipado como **inteiro** (`int | None`); o contrato canônico exige `erro` como string com ID exato da ontologia (`"ERR-01"`).
- Tem `Intervencao{cognitive_process_id, tipo}` embutida dentro de `Pedagogia.principal_intervencao` — não é uma lista `intervencoes[]` no formato `{id,gatilho{processo,erro},acao,prioridade}` do canônico.
- Preserva `schema_version` como campo obrigatório (boa prática já presente), mas nunca recebeu o valor `"2.1"` — é um schema_version de um contrato próprio, não do canônico.

### Formato D — `aluno/backend/annotation_service.py` (leitura, perfil cognitivo)
Um quarto ponto, mais sutil: o cálculo do perfil cognitivo do aluno (`compute_cognitive_profile`) espera encontrar, em cada documento Firestore `itens`, a chave `pipeline.estrutura_cognitiva.{dominios,competencias,processos}` — nomenclatura **textualmente idêntica** à do canônico 2.1 (`estrutura_cognitiva`, `dominios`, `competencias`, `processos`), mas:
- Aninhada sob `pipeline.` (o canônico define `estrutura_cognitiva` no **topo** do item, não dentro de um sub-objeto `pipeline`).
- O pipeline nunca escreve essa chave — ele escreve `pipeline.classificacao` (Formato A), não `pipeline.estrutura_cognitiva`.
- **Efeito prático:** `_build_item_hash_map()` só aceita itens onde `pipeline.get("estrutura_cognitiva")` é verdadeiro; como isso nunca acontece com os dados reais do pipeline, o mapa fica sempre vazio e a funcionalidade de perfil cognitivo do aluno fica **estruturalmente incapaz de encontrar correspondências**, independentemente de haver dados de resposta — não é um bug de execução, é uma divergência de schema entre quem escreve (pipeline, Formato A) e quem lê (aluno, expectativa D).

---

## `professor`

Confirmado: **não consome item/questão em nenhum ponto do código** (`grep` por `enunciado`, `alternativas`, `item_id`, `questao` no backend e frontend não retorna nada). Continua operando sobre `imports` (dados agregados, não itens individuais) — não há divergência a registrar aqui simplesmente porque não há contrato de item para violar.

---

## Confirmações adicionais

- `grep` por `"2.1"` ou pelo texto `Schema Sapiens 2.1` em todo o código dos 3 apps (fora de `node_modules`/`venv`): **zero ocorrências**. O contrato canônico ainda não foi adotado em lugar nenhum.
- `item_hash`: a única implementação real (`aluno/backend/firestore_service.py:compute_item_hash`) está correta em espírito (hash determinístico do conteúdo) e é usada de forma consistente entre gravação do evento de behavior e (tentativa de) leitura do perfil cognitivo — mas opera sobre o Formato A/D, não sobre o objeto `questao` no formato canônico.
- `item_id` determinístico no padrão `ITEM-<FONTE>-<ANO>-<CADERNO>-Q<NUMERO>` sugerido pelo contrato: não aparece em nenhum lugar do código de geração (`pipeline/backend`) ou de sync (`aluno/backend`). Só aparece como valor arbitrário em fixtures de teste (`aluno/backend/tests/test_annotations.py`, `test_admin_and_events.py`), não como regra de geração real.

---

## Resumo por app

| App | Produz/consome item? | Formato usado | Alinhado ao 2.1? |
|---|---|---|---|
| `pipeline` | Produz (gera via Gemini) | Formato A (`DEFAULT_PIPELINE_SCHEMA`) | Não |
| `aluno` (sync Firestore→Mongo) | Consome do pipeline, republica filtrado | Formato B (`_build_public_doc`) | Não — nomenclatura parcialmente parecida, mas `item_id` não determinístico e campos-fonte vêm vazios na prática |
| `aluno` (ingestão manual admin) | Consome via upload | Formato C (`annotation_models.py`) | Não — schema independente, tipos divergentes (`error_type_id` int vs `erro` string) |
| `aluno` (perfil cognitivo) | Lê (tentativa) | Formato D (expectativa própria) | Não — usa nomenclatura do canônico mas aninhamento errado; funcionalmente quebrado contra os dados reais do pipeline |
| `professor` | Não consome | — | N/A |

Nenhuma alteração foi feita no código ou em `pipeline/docs/` como parte desta auditoria.
