# TX-2026-08-21T000000Z-migracao-corpus-para-canonico

**Registrado em:** 2026-08-21
**Natureza:** registro de transação. Sob GOV-1.0 §1.1, `auditoria/` **não cria norma** — este documento descreve o que foi feito, não decide nada.
**Papel exercido:** Curador, por instrução explícita do usuário ("total autonomia para mudar os códigos, respeitando os documentos atualizados").
**Classe predominante:** **I — Correção de Fidelidade** (GOV-1.0 §3.3). Nenhuma decisão cognitiva nova foi introduzida; o código foi alinhado a decisões já registradas nos documentos entregues em `auditoria/DOCUMENTOS ATUALIZADOS 20Ago2026/`.

**Nenhum Domínio, Competência, Processo, Habilidade, Tipo de Erro ou Intervenção foi criado, alterado ou removido. Nenhum Grau de Liberdade foi fechado. A Ontologia v1.6 permanece não autorizada.**

---

## 1. Promoção do corpus ao espaço canônico

Os documentos atualizados estavam em `auditoria/`, que é espaço de **registro**. Um contrato ali não vincula (GOV-1.0 §1.1), e portanto código nenhum poderia legitimamente depender dele. Foram promovidos para `pipeline/docs/`, byte a byte, sem edição normativa.

| Documento | Destino | Antes → Depois |
|---|---|---|
| Governança e Versionamento | `00 Governanca e Versionamento Sapiens v1.0.md` | **novo** (GOV-1.0) |
| Ontologia (JSON) | `ontology/ontology_v1.4.json` | 1.4 → **1.4.1** |
| Ontologia (prosa) | `ontology/05 Ontologia … v1.4.md` | 1.4 → **1.4.1** |
| Schema do item | `Schema anotador de questoes/06 Schema Sapiens 2.1.json.md` | 2.1 → **2.2** |
| Behavior | `behavior/07 behavior student 1.4.md` | 1.0 → **1.1** |
| Manual de Anotação | `annotation/01 Manual …` | 1.0/1.1 → **1.2** |
| Constituição | `constitution/02 Constituicao Sapiens.md` | s/versão → **1.1** |
| Error Trace | `error-trace/10 Especificacao do Error Trace v1.0.md` | **novo** (ETRACE-1.0) |
| Mapa de IDs | `traceability/09 Mapa de Rastreabilidade de IDs.md` | **novo** (MAP-IDS-1.0) |
| Registro de Extração WP 1.0 | `traceability/08 Registro de Extracao do WP 1.0.md` | **novo** (EXT-WP1-1.0) |
| White Paper | `white-paper/03 White Paper v2.0.md` | 2.0 → **2.0.1** |

A **Parte V (Caps. 13–14)** do White Paper passa a portar a marcação de supersessão parcial que faltava: `[SUPERSEDED por ONT-1.4.1]` quanto ao inventário. Sob GOV-1.0 §8.3, a seção superada perde força normativa imediatamente, mesmo permanecendo no texto. Ponto de atenção registrado: **sete identificadores `DOM-*` são idênticos nos dois inventários com extensão comprovadamente divergente** (colisão `NS-4`, BLOQUEANTE).

**Nomes de arquivo preservados** onde o próprio documento declara estabilidade de citação (GOV-1.0 §6.1: a versão vive no campo, não no nome). O `06 Schema … 2.1.json.md` contém `schema_version: "2.2"`; o `07 behavior student 1.4.md` contém `schema_version: "1.1"`.

**Supersessão declarada bidirecionalmente** (GOV-1.0 §8.1): versões anteriores preservadas em `pipeline/docs/_superseded/`, cada uma com banner declarando `superseded_by` e a transação de origem. Nenhuma foi apagada (§9.3: silêncio não remove).

**`04 Ontologia … v1.4 JSON.md` aposentado** (GOV-1.0 §12.3): comparação campo a campo executada contra o artefato primário — **zero divergências**, portanto nenhum incidente a registrar. Reduzido a stub de proveniência; conteúdo integral em `_superseded/`.

### Verificação de integridade do catálogo

```
1.4 → 1.4.1: única diferença de conteúdo = PROC-ESPACO-03.tipos_erro ['ERR-13'] → []
128 identificadores (11 DOM + 12 COMP + 25 PROC + 56 HAB + 13 ERR + 11 INT)
relação Erro↔Processo bidirecionalmente coerente em todos os 13 tipos de erro
13 dos 25 processos sem tipo de erro catalogado — bate com a lista nominal do Manual §11
```

---

## 2. Cadeia de dependências seguida

Ordem de propagação exigida por GOV-1.0 §6.3:

```
C3 (ontologia 1.4.1) → Error Trace → Schema 2.2 → behavior 1.1 → Manual
```

---

## 3. Alterações de código, por app

### `pipeline` — motor de anotação

| Onde | O quê |
|---|---|
| `cognitive_engine.py` | `DEFAULT_PIPELINE_SCHEMA` deixa de ser o "Formato A" (`questao`/`classificacao`/`meta`, sem proveniência documental) e passa a ser o **Schema 2.2**. |
| `cognitive_engine.py` | Prompt do modelo reescrito com as regras vinculantes do Manual: ordem de decisão §2, teste de necessidade §3, limite de 2 processos §4, pesos 0.7/0.3 §5, catálogo fechado de habilidades §6, sentinelas §7, proibição de classificar por disciplina §8. |
| `cognitive_engine.py` | **Defeito corrigido:** `_ontology_prompt_slice` pedia `descricao`, `categoria` e `dominio` — campos que não existem em nenhum nó do catálogo v1.4.x. A definição operacional de cada processo, o mecanismo de cada erro e a evidência observável chegavam ao modelo como `null`; ele classificava por semelhança de nome, exatamente o que o Manual §8 proíbe. |
| `item_contract.py` (**novo**) | Normalização: carimbo de `schema_version`/`ontology_version`, `item_id` estável, `item_hash` determinístico, derivação de domínios/competências, normalização de bins de confiança. |
| `ontology_validator.py` | Reescrito. Validava um formato intermediário (`processo_dominante`/`processos_secundarios`) sem nenhum consumidor. Agora valida **Schema 2.2** e **Error Trace 1.0**, com cada regra citando a cláusula que a autoriza. |
| `server.py` | Os quatro pontos que produzem item (`generate`, `book/process`, `update`, `regenerate`) passam pela normalização e gravam o resultado da validação. `item_id` preservado em edição e regeneração. |

### `aluno` — app do estudante

| Onde | O quê |
|---|---|
| `canonical_ontology.py` (**novo**) | Resolve o catálogo canônico e o validador compartilhado. |
| `cognitive_ontology.py` | Passa a ler `pipeline/docs/ontology/ontology_v1.4.json`. |
| `docs/ontology JSON v1.4` | **Removido.** Duplicata sob GOV-1.0 §12.2; §12.3 passo 2 executado, zero divergências. |
| `ontology.py`, `ontology_routes.py` | **Removidos.** Taxonomia CHC de 5 níveis cujo nível 5 era o **Indicador Comportamental** — nó que a Constituição §4.2 não define. Código morto (zero importadores, rota não registrada) que reintroduziria uma geração superseded. |
| `firestore_service.py` | `write_behavior_event` grava `schema_version: "1.1"` e exige `ontology_version`. |
| `firestore_routes.py` | `ontology_version` e `item_hash` vêm do **item respondido**, não da ontologia ativa nem de recálculo. Item sem `ontology_version` → **409**, não evento indatável. |
| `admin_routes.py` | **Violação corrigida:** `_build_public_doc` sorteava `uuid4().hex` novo **a cada sync**, contra a exigência explícita de que `item_id` "permaneça invariável entre pipeline, Firestore, aluno e professor". Agora é copiado do item. |
| `annotation_service.py` | **Defeito corrigido:** o índice recalculava o hash sobre `pipeline.questao` e lia `pipeline.estrutura_cognitiva` — chave que o pipeline nunca escreveu. Nenhum evento casava com nenhum item e todo perfil cognitivo saía vazio **sem erro visível**. |
| `annotation_models.py` | Reescrito para o Schema 2.2. **Colisão NS-1 fechada:** `error_type_id: int` forçava a geração G0/G1, cujos inteiros 1–13 são conjunto disjunto dos `ERR-01`–`ERR-13`, com mesma cardinalidade e mesmo intervalo. |
| `feedback_templates.py` | Lê a **cadeia ordenada** e parte do elo de `ordem: 1`. **Colisão NS-2 fechada:** havia um dicionário hard-coded atribuindo a cada `ERR-NN` significado divergente do catálogo (`ERR-01` = "parou numa etapa intermediária" vs. catálogo "Leitura literal deficiente"). A explicação passa a ser derivada do catálogo. |
| `admin_routes.py` | **Bug pré-existente corrigido:** `update_user` não tinha `return` — o bloco `if res.matched_count == 0` havia migrado para o fim de `update_questao_master`, como código morto. A rota devolvia `null` e nunca sinalizava usuário inexistente. |

### `professor`

Nenhuma migração de contrato necessária: **não produz, não transforma e não consome item/questão** em nenhum ponto (confirmado por grep). `SAMPLE_NOS` já usava IDs e nomes verbatim do catálogo. Único ajuste: rótulo de versão da taxonomia `v1.4` → `v1.4.1`, com nota de que a "v1.3" citada é referência histórica — a v1.3 **não existe no corpus** (G-CONF-09).

### Frontends

`PipelineResult.jsx` reescrito para o 2.2: derivação auditável (mostra de quais processos cada domínio veio), **cadeia de erro com a raiz marcada**, bloco de incerteza, e o resultado da validação exibido. `BookResults.jsx`, `BatchResults.jsx`, `ProcessedQuestions.jsx`, `Ontology.jsx` e `AdminAnnotations.jsx` migrados. Todos leem `item` com fallback para `pipeline`, para não perder documentos anteriores à migração.

---

## 4. Decisões de engenharia — revisadas contra o corpus completo (com WP 2.0.1)

Cada decisão foi reexaminada depois da chegada do White Paper 2.0.1. **Duas mudaram de estatuto e uma foi corrigida.**

### 4.1 Determinadas pelo corpus — não eram decisões minhas

| # | Estatuto revisado | Cláusula que determina |
|---|---|---|
| **D-E1** | **CONFIRMADA.** O Schema separa força: *obrigação* — "Deve permanecer invariável entre pipeline, Firestore, aluno e professor"; *recomendação* — "Recomenda-se um formato determinístico baseado em fonte, ano, prova e número". A bifurcação do código espelha exatamente essa separação. | Schema 2.2, `item_id` |
| **D-E2** | **CONFIRMADA e reclassificada.** Não é preferência: um id derivado do conteúdo mudaria a cada correção de vírgula, contradizendo a obrigação de invariância. A divisão de trabalho está no contrato — `item_hash` "deve mudar quando o conteúdo estrutural relevante mudar"; `item_id` não. | Schema 2.2, `item_id` + `item_hash` |
| **D-E3** | **CONFIRMADA.** `item_hash` é "hash do conteúdo canônico do item **no momento da resposta**" nos três contratos. A classificação cognitiva não é conteúdo da questão. | Schema 2.2; behavior 1.1; ETRACE §2.1 |
| **D-E5** | **RECLASSIFICADA — determinada pelo corpus, não decisão de engenharia.** `EXT-WP1-1.0` L13 lista "ler a regra 1 como proibição de armazenamento" entre os **riscos de reintrodução indevida**: *"o item pode ser armazenado; não pode ser exposto ao motor. A distinção é o que permite ingestão em massa com enriquecimento posterior."* Bloquear na ingestão seria violação. | EXT-WP1-1.0, L13, risco 3 |

### 4.2 Corrigida

| # | O que estava errado | Correção aplicada |
|---|---|---|
| **D-E4** | Emitia `peso_no_item` e `confianca` nos blocos derivados como números nus, o que faz um consumidor tomá-los por quantidades evidenciais. A Constituição §4.5 diz o oposto: Processo↔Domínio e Processo↔Competência são relações de **classificação/organização** — *"peso é opcional e reservado a refinamento futuro (ex.: centralidade), nunca obrigatório, porque a função destas relações é navegação e agrupamento, **não evidência**"*. | Cada bloco derivado passa a carregar `_estatuto` declarando `evidencial: false`, a autoridade (§4.5) e a nota de que não alimentam a camada de crença. A **função de herança** permanece provisória e agora se declara como tal, sob GOV-1.0 §6.4 — o WP 2.0.1 §4.2 registra que o Axioma da Crença Calibrada "não exige nenhuma família matemática específica", então nenhuma camada superior a define. |

### 4.3 Permanecem decisões locais, sem contradizer o corpus

| # | Decisão | Por quê |
|---|---|---|
| **D-E6** | Uma **única** implementação de validação, compartilhada via `SAPIENS_CONTRACTS_PATH`. | Duas implementações do mesmo contrato divergem — modo de falha que GOV-1.0 §12 existe para impedir. |
| **D-E7** | O `aluno` lê a ontologia do repositório; em deploy separado, `SAPIENS_ONTOLOGY_PATH`. | Elimina a réplica privada sem inventar um serviço de catálogo. |
| **D-E8** | Sem fallback silencioso para catálogo ausente — falha explícita. | Um catálogo vazio produziria perfis cognitivos silenciosamente errados. |

---

## 5. O que **não** foi feito, e por quê

| Item | Estado |
|---|---|
| **Produtor de Error Trace** | O contrato (ETRACE-1.0) foi implementado e é validável; **nenhum código produz traços**. Criar um produtor exigiria especificar o motor diagnóstico, que nenhum documento define (§0.1 item 2 é explícito: "não define o mecanismo de produção"). Inventá-lo seria inventar arquitetura. |
| **Falsa proficiência** | Ativo protegido (WP §15) declarado **"ativo sem implementação"** pela própria errata 2.0.1: "o critério operacional que o torna detectável não existe em nenhum documento canônico". Não implementado — exigiria inventar o critério. |
| **Regra 1 de modelagem (L13a)** | "Item sem mapeamento cognitivo não deve ser exposto ao motor de recomendação." Status `REMOVIDO`, recuperação **recomendada** por EXT-WP1-1.0 com natureza `[DE]` — recomendação em documento C5, ainda não norma. Não implementada. O motor de recomendação também não existe. |
| **Camada de decisão pedagógica** | Formalmente vazia no corpus. A aresta Processo↔Processo não está populada — nem pré-requisitos existem. |
| **Turma / matrícula / vínculo professor↔aluno** | Sem menção em nenhum documento. `professor` segue com estrutura própria, sem tentativa de alinhamento — não há com o que alinhar. |
| **Evento de intervenção aplicada** | A Intervenção existe apenas como nó de catálogo. Nenhum contrato de evento professor→aluno. |
| **Dependências Emergent em runtime** | `ai_service.py`, `auth.py`, `storage.py`. Fora de escopo desta rodada. |
| **Migração dos dados existentes** | Nenhum dado foi tocado. O `PLANO-RESET-ITENS.md` continua não executado. Itens já sincronizados sem `ontology_version` são recusados no `/answer` com 409 e instrução de reingestão. |
| **Suítes de teste legadas** | Marcadas como asserindo contrato superseded. **Não foram reescritas**: falham na coleta (exigem `REACT_APP_BACKEND_URL` e servidor no ar) e já falhavam antes desta migração. Reescrever asserção que não roda seria ficção. |

---

## 6. Validações executadas

```
pipeline/backend/tests/test_contratos_canonicos.py ....... 60 passed
aluno/backend/tests/test_contratos_aluno.py .............. 20 passed
compileall (pipeline, aluno, professor) .................. OK
import dos módulos de contrato ........................... OK
parse dos 9 JSX migrados (babel) ......................... OK
cadeia ponta a ponta (anotar→sync→responder→feedback) .... OK
professor/backend/tests/test_auth_strip.py ............... 10 failed
    ^ falha ambiental pré-existente: aponta para host Emergent morto (404).
      Sem relação com esta migração — nenhuma linha de auth foi tocada.
```

Cobertura dos testes novos, por cláusula: catálogo 1.4.1 e cardinalidade; carimbo obrigatório de `ontology_version`; identidade vs. conteúdo (`item_id`/`item_hash`); derivação §4.4; **estatuto não-evidencial dos blocos derivados §4.5**; **herança de confiança declarada provisória §6.4**; papel fechado §7; limite de 2 processos §4; pesos §5; justificativa §12.4; habilidade sob o processo-pai §6.1; truncamento G1→G3 (NS-3); campos removidos da 2.1; confiança obrigatória R-3; ordem contígua R-5; profundidade R-4; vínculo de catálogo R-1; sentinelas R-2; vocabulário `MEC-*` §4.3; marcadores de incerteza; governança de ingestão L13b; **item inválido permanece armazenável (L13, risco 3)**; **ordem causal do Error Trace como ativo protegido (WP §15)**; **disciplina como metadado de manifestação**; behavior 1.1 campo a campo; `item_id` invariável entre sincronizações; feedback a partir da raiz.

---

## 7. Conflitos registrados e não resolvidos

Herdados do corpus, **nenhum decidido aqui**:

- **G-CONF-03** — numeração 1.4 → 1.6 salta 1.5; a mudança pretendida tem características de Classe IV, que corresponderia a 2.0.
- **G-CONF-09** — toda a proveniência `origem_v1_3` aponta para uma v1.3 ausente do corpus. Cadeia rompida.
- **G-CONF-13** — remissão a "Plano de Validação" (kappa), inexistente.
- **D-4 do Manual** — arbitragem das fronteiras `DOM-CAUSAL` × `DOM-EXPERIMENTAL` e `PROC-CLASSIF-01` × `PROC-ESPACO-03`. Convenção provisória em vigor.
- **Três números do piloto** — amostra por processo, número de anotadores, limiar de kappa. Bloqueiam a v1.6.

---

_Fim do registro. Nenhum documento canônico teve conteúdo normativo alterado por esta transação: os documentos foram movidos para o espaço canônico tal como recebidos._
