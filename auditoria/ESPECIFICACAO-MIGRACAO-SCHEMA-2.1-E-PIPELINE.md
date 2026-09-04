# Especificação técnica integrada — migração para Schema 2.1 e arquitetura do anotador

**Registrado em:** 2026-08-17T03:48:27Z
**Base exclusiva:** `pipeline/docs/` (13 documentos canônicos) + auditorias já registradas em `auditoria/` (`ESTADO-CONSOLIDACAO.md`, `AUDITORIA-SCHEMA-ITEM-2.1.md`, `AUDITORIA-MIGRACAO-ITEM-2.1.md`, `PLANO-RESET-ITENS.md`).
**Escopo:** leitura e especificação apenas. Nenhum código, dado ou documento de `pipeline/docs/` foi alterado. Nenhum contrato intermediário foi criado. Nenhum campo, ID, integração ou comportamento foi inventado — onde o dado necessário não existe em `pipeline/docs/`, isso é registrado como lacuna, não preenchido.

**Aviso preliminar, antes de tudo o mais:** a arquitetura de referência descrita nesta tarefa (`PDF → enem-extractor → item + assets → LOTUS/LLM → Schema 2.1`) **não está documentada em `pipeline/docs/`**. Confirmado por busca exaustiva (repetida nesta auditoria e já registrada em `AUDITORIA-MIGRACAO-ITEM-2.1.md`): zero ocorrências de "LOTUS" ou "enem-extractor" nos 13 documentos canônicos. O papel de cada componente ("enem-extractor: extração determinística...", "LOTUS: orquestração...") vem da descrição fornecida nesta conversa, não de `pipeline/docs/`. Este documento trata essa arquitetura como **arquitetura pretendida fornecida externamente**, e é explícito, em cada seção, sobre o que é canônico (rastreável a `pipeline/docs/`) versus o que é premissa desta tarefa (não rastreável a `pipeline/docs/`).

---

## ESTADO ATUAL

### 1. Arquitetura real do pipeline hoje

```
PDF/imagem (upload via POST /api/pipeline/generate)
        │
        ▼
run_cognitive_pipeline()  [cognitive_engine.py]
        │  — UMA ÚNICA chamada multimodal ao Gemini, recebendo os bytes
        │    brutos do arquivo + a ontologia ativa como texto no prompt
        ▼
JSON no "Formato A" (DEFAULT_PIPELINE_SCHEMA — não é o Schema 2.1)
        │
        ▼
Mongo `sapiens_pipeline.pipelines`  +  espelho Firestore (`itens`)
```

Não há estágio de extração determinística separado. Não há camada de orquestração entre extração e LLM. Uma única chamada ao modelo faz **extração de texto/alternativas/figuras E classificação cognitiva ao mesmo tempo**, no mesmo prompt, na mesma resposta.

### 2. Onde os itens são produzidos, transformados e consumidos

Mapeado em detalhe em `auditoria/AUDITORIA-MIGRACAO-ITEM-2.1.md §1` (não repetido aqui na íntegra). Resumo:

- **Produzido em:** `pipeline/backend/server.py:generate_pipeline` (linha 492), via `cognitive_engine.run_cognitive_pipeline`.
- **Transformado em:** `pipeline/backend/server.py:_index_fields` (linha 444, extrai colunas de índice do Formato A); `aluno/backend/admin_routes.py:_build_public_doc` (linha 67, reshape parcial para formato público do aluno).
- **Consumido em:** `aluno/backend/admin_routes.py:firestore_sync` (lê Firestore `itens`); `aluno/backend/annotation_service.py` (tenta ler `estrutura_cognitiva`, nunca encontra — ver §5); `aluno/backend/server.py:GET /questoes` (serve `questoes_public` ao frontend do aluno).
- **`professor`:** não produz, não transforma, não consome item/questão em nenhum ponto (confirmado por grep vazio, repetidas vezes nas auditorias anteriores).

### 3. Onde `enem-extractor` está integrado hoje

**Não está integrado.** Existe como código morto:

- `pipeline/backend/enem_service.py` — wrapper determinístico completo em torno do pacote PyPI `enem==1.0.4` (presente em `requirements.txt:131`), função `extract_enem_pdf(pdf_path, output_dir=None, answer_key_path=None, minimal=False)`.
- Confirmado nesta auditoria: aceita **`answer_key_path`** — quando fornecido, o pacote `enem` já retorna `alternativa["correct"]: bool` por alternativa. O wrapper normaliza para `{"numero","enunciado","enunciado_blocos","imagens","alternativas":[{"index","label","content","correct"}]}`.
- **Nenhuma rota em `server.py` chama `enem_service.extract_enem_pdf`.** `generate_pipeline` recebe os arquivos e os manda direto para `run_cognitive_pipeline` (Gemini), nunca passando por `enem_service.py`.

### 4. Onde LOTUS está integrado hoje

**Não existe em lugar nenhum** — nem como dependência (`requirements.txt` não lista nada chamado "lotus"), nem como módulo próprio, nem como menção em comentário ou docstring. Não há orquestração alguma entre uma etapa de extração e uma etapa de classificação, porque essas duas etapas hoje são a mesma chamada.

### 5. Como `cognitive_engine.py` diverge da arquitetura pretendida

| Arquitetura pretendida | `cognitive_engine.py` hoje |
|---|---|
| Recebe **item já estruturado** (texto, alternativas, assets) de uma etapa de extração anterior | Recebe os **bytes brutos do PDF/imagem** diretamente (`files: list[tuple[str, bytes]]` em `run_cognitive_pipeline`) |
| LLM só produz a **anotação cognitiva** sobre um item já extraído | LLM faz **extração + anotação** na mesma chamada — o prompt (`_SYSTEM_PROMPT_TEMPLATE`) instrui simultaneamente "extrair estruturadamente a questão" e "classificar exclusivamente usando os IDs da ontologia" |
| Existe uma camada de orquestração (LOTUS) entre extração e LLM | Chamada direta e única ao SDK `google-genai`, sem camada intermediária |
| Saída no Schema 2.1 | Saída no Formato A (`DEFAULT_PIPELINE_SCHEMA`) — estrutura, nomes de campo e granularidade diferentes (detalhado em `AUDITORIA-MIGRACAO-ITEM-2.1.md §3`) |
| `item_id`/`item_hash` presentes no item desde a extração | Nenhum dos dois é gerado por `cognitive_engine.py`; `item_id` só é atribuído depois, em `server.py`, como `uuid4()` aleatório |

---

## ARQUITETURA PRETENDIDA (conforme fornecida nesta tarefa — não documentada em `pipeline/docs/`)

```
PDF ──▶ enem-extractor ──▶ item estruturado + assets ──▶ LOTUS/LLM ──▶ Schema Sapiens 2.1
        (determinístico,       (texto, alternativas,      (orquestra +      (contrato final,
         sem LLM)               gabarito se disponível,    chama LLM;        único formato
                                 paths de assets)           NÃO define        de saída válido)
                                                             ontologia/schema)
```

Papéis conforme descritos nesta tarefa: `enem-extractor` extrai deterministicamente (sem classificar cognitivamente); `LOTUS` orquestra e integra com o LLM (sem definir ontologia nem schema); o `LLM` produz a anotação **dentro** dos contratos Sapiens; `pipeline/docs/` permanece a única fonte de ontologia, critérios e Schema 2.1.

Como nenhum documento canônico descreve essa separação de estágios, o que segue nas próximas seções é **compatibilidade estrutural** entre o que existe hoje e o que essa arquitetura exigiria — não uma leitura de requisito documentado.

---

## LACUNAS

### 6. Arquivos que precisam escrever/ler o Schema 2.1

**Escrever (produzir a saída final no formato 2.1):**
- `pipeline/backend/cognitive_engine.py` — `DEFAULT_PIPELINE_SCHEMA` e `_SYSTEM_PROMPT_TEMPLATE` precisam mudar para instruir o LLM a preencher exclusivamente as partes do Schema 2.1 que cabem a ele (ver §8).
- `pipeline/backend/server.py` — `generate_pipeline` precisa montar o documento final combinando: saída determinística do enem-extractor + saída do LLM + metadados de execução (`pipeline{}` do contrato — hoje esse nome de chave já é usado para outra coisa, ver §7) + `item_id`/`item_hash` computados.
- `pipeline/backend/enem_service.py` — precisa de uma função de reshape que converta sua saída própria (`numero/enunciado/enunciado_blocos/imagens/alternativas[{index,label,content,correct}]`) para os campos correspondentes de `questao{}`/`fonte{}` do Schema 2.1 (mapeamento mecânico, não inventivo — ver §7).

**Ler (consumir o Schema 2.1 depois de escrito):**
- `aluno/backend/admin_routes.py:_build_public_doc` — hoje já tenta ler `fonte{}`/`questao.recursos` (nomes corretos, mas a fonte nunca preenche); passaria a funcionar de verdade.
- `aluno/backend/annotation_service.py:_build_item_hash_map` — precisa ler `estrutura_cognitiva` do **topo** do item (não de dentro de `pipeline.*`).
- `pipeline/frontend/src/pages/*.jsx` (Gerador de Pipeline, Questões Processadas) — telas que hoje exibem campos do Formato A.

### 7. Campos atuais que precisam ser removidos, renomeados ou reestruturados

Tabela completa campo a campo já está em `AUDITORIA-MIGRACAO-ITEM-2.1.md §3`. Pontos que afetam diretamente a arquitetura de dois estágios (extração → LLM):

| Ação | Onde | Detalhe |
|---|---|---|
| **Renomear** | `enem_service._normalize_alternatives` | `label`→`letra`, `content` (lista de blocos)→`texto` (string), `correct`→`correta`, `index`→ descartar (não existe no canônico) |
| **Reestruturar** | `enem_service.extract_enem_pdf` saída | `imagens: [path]` (lista de strings) → `recursos.imagens: [{id, tipo, descricao, arquivo, ocr}]` — só `arquivo` (o path) vem pronto; `id/tipo/descricao/ocr` não existem na saída atual do extractor (ver §8) |
| **Resolver colisão de nome** | `server.py:generate_pipeline` | A chave `"pipeline"` hoje guarda o payload inteiro da anotação (Formato A). No Schema 2.1, `pipeline{}` é só metadados de execução do modelo. Um merge ingênuo entre os dois sobrescreveria dados — precisa de renomeação explícita antes de qualquer geração real (já registrado em `AUDITORIA-MIGRACAO-ITEM-2.1.md §5` como risco crítico) |
| **Remover** | `classificacao.processos_cognitivos[].justificativa` (objeto estruturado: `trechos_enunciado/elementos_figura/regras_ontologia/por_que_este_papel`) | Schema 2.1 define `justificativa` como **string simples** e separa evidências em `evidencias.trechos[]`/`evidencias.figuras[]` — a forma atual (objeto com 4 subchaves) não tem equivalente 1:1, precisa ser desmembrada |
| **Achatar → aninhar** | `classificacao.habilidades_observaveis: [string]` (solta) | Schema 2.1 aninha habilidades **dentro de cada processo** (`processos[].habilidades[]`), não como lista solta no nível de classificação |
| **Gerar em vez de atribuir aleatoriamente** | `server.py:question_id = str(uuid.uuid4())` | Precisa virar `item_id` determinístico a partir de `fonte.banca/ano/prova/numero` (formato sugerido pelo próprio Schema 2.1: `ITEM-ENEM-2024-CAD01-Q023`) |

### 8. Campos do Schema 2.1 que NÃO podem ser preenchidos automaticamente sem inventar dados

Esta é a lacuna mais importante para a implementação, porque toca diretamente a instrução de não inventar. Três categorias:

**(a) Automatizáveis hoje, com a peça certa no lugar certo**
- `item_id`, `item_hash` — computáveis deterministicamente a partir de `fonte.*` e do conteúdo canônico (mecanismo de hash já existe, em `aluno/backend/firestore_service.py:compute_item_hash`, mas não no `pipeline`).
- `fonte.banca/ano/prova/numero/arquivo_origem/pagina` — extraíveis deterministicamente pelo `enem-extractor` (confirmado: o pacote `enem` já resolve `number`; banca/ano/prova viriam do nome do arquivo/caderno, não do conteúdo — ver ressalva abaixo).
- `questao.enunciado`, `alternativas[].letra/texto` — extraíveis deterministicamente pelo `enem-extractor`.
- `alternativas[].correta` — **automatizável somente se um `answer_key_path` (gabarito) for fornecido ao `enem-extractor`**. Hoje nenhuma rota do pipeline aceita ou roteia um arquivo de gabarito separado do PDF de questões. Sem gabarito, este campo não deveria ser preenchido pelo LLM como palpite — o próprio Schema 2.1 diz "deve ser preenchido apenas quando o gabarito for conhecido e validado".
- `recursos.imagens[].arquivo` — o path do asset extraído é determinístico.
- `pipeline.modelo/tokens_entrada/tokens_saida/tempo_processamento_segundos` — metadados de execução, computáveis pelo próprio código (resposta da API do Gemini expõe contagem de tokens; tempo é wall-clock).
- `qualidade.revisado` (= `false` por padrão) — verdade objetiva no momento da geração, ninguém revisou ainda.

**(b) Requerem decisão de produto/escala ausente em `pipeline/docs/` — não podem ser preenchidos sem inventar a escala**
O Schema 2.1 referencia repetidamente "escala definida pelo contrato", "valores permitidos pelo contrato" ou "regra definida pelo contrato" para os seguintes campos — mas a própria descrição do campo é a única definição existente; nenhum documento em `pipeline/docs/` enumera essas escalas/valores:
- `estrutura_cognitiva.dominios[].peso_no_item`, `.competencias[].peso_no_item`, `.processos[].peso_no_item`, `.habilidades[].peso_no_processo` — escala/normalização não definida (0–1? percentual? ranking?). **[Correção — 2026-08-17T23:38:43Z]** Leitura completa do Manual de Anotação mostrou que `processos[].peso_no_item` **está**, sim, definido (bins 1.0/0.7/0.3, Manual §5 — "convenção provisória"). O restante (`dominios`/`competencias`/`habilidades`) permanece sem escala. Mapeamento completo e corrigido em `auditoria/DECISOES-PENDENTES-CONTRATOS.md §1`.
- `estrutura_cognitiva.*.confianca` (em todos os níveis) — escala não definida.
- `processos[].dificuldade_local` — escala não definida, e o contrato só diz que é distinta da "dificuldade psicométrica global" sem dizer qual é a escala local.
- `distratores[].plausibilidade` — "valores permitidos pelo contrato" não enumerados em lugar nenhum.
- `distratores[].probabilidade_estimada` — "escala previamente definida" não definida.
- `processos[].papel` — o texto do contrato dá só exemplos ("por exemplo 'nuclear' ou 'secundario'"), não uma enumeração fechada e explícita (o Formato A antigo tinha `nuclear|secundario|facilitador`, mas isso não pode ser assumido como o conjunto válido do 2.1 sem confirmação, pois é um documento diferente).
- `pedagogia.nivel_dificuldade` — "valores definidos pelo contrato" não enumerados.
- `qualidade.confianca_global` — mesma lacuna de escala.

Preencher qualquer um desses campos hoje exigiria **inventar** uma escala ou enumeração — exatamente o que esta tarefa proíbe. Ficam como lacuna documentada, não como decisão de implementação.

**(c) Estruturalmente impossíveis de preencher no momento da geração, por definição do próprio contrato**
- `psicometria.dificuldade_empirica`, `.discriminacao`, `.taxa_acerto`, `.tempo_medio` — o próprio Schema 2.1 exige que sejam "calculado a partir de dados reais de resposta"/"observado". No momento em que um item é gerado (antes de qualquer aluno responder), esses dados não existem. Só podem ser calculados depois, a partir do event store de behavior (`students/{uid}/behavior`, já auditado e alinhado em `ESTADO-CONSOLIDACAO.md`) — é um processo de **atualização posterior** do item, não de geração inicial.
- `qualidade.revisor` — não pode ser preenchido sem uma revisão humana real ter ocorrido; fica `null` até isso acontecer.
- `recursos.imagens[].descricao/ocr` — o `enem-extractor` só entrega o *path* do asset, não a descrição nem o texto OCR. Preencher exigiria uma etapa adicional (OCR determinístico e/ou descrição via LLM vision) que não está mapeada em nenhum dos dois componentes descritos (`enem-extractor` diz explicitamente que não classifica; não está claro, sem definição adicional, se essa etapa é responsabilidade do LOTUS, do LLM principal, ou de um terceiro processo — não documentado, não inventado aqui).

### 9. Como validar a saída contra o Schema 2.1

`pipeline/docs/Schema anotador de questoes/06 Schema Sapiens 2.1.json.md` está escrito como um objeto JSON onde cada valor é uma **descrição textual em português**, não um JSON Schema formal (sem `type`, sem `enum`, sem `required` machine-readable). Isso por si só é uma lacuna: não existe hoje um artefato validável programaticamente derivado diretamente de `pipeline/docs/`.

O que pode ser validado **sem inventar** nada além do que já está em `pipeline/docs/`:
1. **Presença estrutural** — todas as chaves de topo (`schema_version, item_id, item_hash, fonte, questao, estrutura_cognitiva, distratores, intervencoes, pedagogia, psicometria, pipeline, qualidade`) e suas subchaves diretas, conforme o próprio arquivo `.md` enumera.
2. **Tipo básico inferido do texto da descrição** — ex. "Booleano indicando..." → `bool`; "Sequência ordenada de..." → `list`; campos com sub-objetos → `dict`. É uma inferência textual direta, não uma invenção de regra nova.
3. **Cross-check de IDs contra a ontologia ativa** — todo `id` referenciado em `estrutura_cognitiva.*`, `distratores[].erro`, `intervencoes[].id/gatilho.*` **pode e deve** ser validado contra os IDs reais existentes em `pipeline/docs/ontology/ontology_v1.4.json` (isso está previsto no próprio Schema 2.1: "ID exato ... existente na ontologia canônica vigente"). Esta é a única validação de conteúdo (não só estrutura) que pode ser feita hoje sem inventar nenhuma regra nova.
4. **O que NÃO pode ser validado hoje:** qualquer regra de faixa/enum listada em §8(b) — não dá para validar `peso_no_item` está "correto" ou `plausibilidade` é um "valor permitido" quando esses valores nunca foram enumerados em `pipeline/docs/`. Uma validação desses campos hoje só poderia checar "está presente e é do tipo esperado" (string/número), não "está dentro da regra do contrato", porque essa regra não está escrita em lugar nenhum.

### 10. Dependências e configurações necessárias para reprodutibilidade

| Dependência | Estado atual |
|---|---|
| `enem==1.0.4` (pacote do `enem-extractor`) | Já em `pipeline/backend/requirements.txt:131`, instalado no ambiente local, **não usado** em runtime. |
| `GEMINI_API_KEY` | Configurada e validada (confirmado em sessão anterior, `live_probe: ok`). |
| Ontologia ativa (`ontology_v1.4.json`) | Consolidada e ativa desde `ESTADO-CONSOLIDACAO.md`. |
| Fonte de gabarito (answer key) para o pipeline | **Não existe hoje um mecanismo no `pipeline` para receber/rotear um PDF de gabarito** junto com o PDF de questões — pré-requisito para automatizar `alternativas[].correta` (ver §8a). O `aluno` tem seu próprio parser de gabarito colado (`enem_seed.py`), mas é para provas completas do módulo "Provas", desconectado do fluxo de geração de item único do `pipeline`. |
| Esquema formal (JSON Schema/tipos) do Schema 2.1 | **Não existe.** Só o `.md` descritivo. Necessário para validação automatizada real (§9), mas sua criação por mim aqui seria "criar um contrato intermediário" — fora do escopo permitido nesta tarefa. |
| Definição de `versao_pipeline`/`versao_prompt` | **Não existe hoje um esquema de versionamento de prompt/pipeline no código** — `pipeline{}` do Schema 2.1 pressupõe que essas versões sejam rastreáveis, mas hoje não há nenhuma constante/tag de versão de prompt no `cognitive_engine.py`. |
| Componente/pacote "LOTUS" | **Não identificado em `pipeline/docs/` nem no código.** Nenhuma dependência instalada, nenhuma referência a um produto ou biblioteca específica com esse nome. Sua natureza exata (biblioteca de terceiros vs. módulo próprio a construir) não está definida em nenhum documento canônico. |
| Object storage dos assets extraídos | Hoje depende da infraestrutura da Emergent (`pipeline/backend/storage.py`) — já registrado como pendência de migração futura em `ESTADO-CONSOLIDACAO.md`, fora do escopo desta especificação. |

### 11. Ordem exata de implementação, por dependência

Cada item depende do anterior estar resolvido. Itens marcados **[BLOQUEIO DE DECISÃO]** não podem avançar sem que alguém defina algo que hoje não está em `pipeline/docs/` — não é um passo de código, é uma lacuna documental a preencher primeiro.

1. **[BLOQUEIO DE DECISÃO]** Formalizar em `pipeline/docs/` as escalas/enums que o Schema 2.1 referencia mas não define (`peso_no_item`, `confianca`, `dificuldade_local`, `plausibilidade`, `probabilidade_estimada`, `papel`, `nivel_dificuldade`, `confianca_global`) — §8(b). Sem isso, qualquer implementação que preencha esses campos estará inventando a regra.
2. **[BLOQUEIO DE DECISÃO]** Definir o que é "LOTUS" nesta arquitetura — biblioteca externa específica ou módulo de orquestração próprio a construir — e seu contrato de entrada/saída. Não documentado hoje.
3. Definir e implementar um mecanismo para o `pipeline` receber (opcionalmente) um arquivo de gabarito junto com o PDF de questões, para viabilizar `alternativas[].correta` automatizado via `enem_service.extract_enem_pdf(..., answer_key_path=...)`.
4. Ativar `enem_service.py`: chamar `extract_enem_pdf` a partir de `server.py:generate_pipeline`, antes de qualquer chamada ao LLM, produzindo a extração determinística (texto, alternativas, paths de assets).
5. Construir a função de reshape do output do `enem-extractor` para os nomes/estrutura de `fonte{}`/`questao{}` do Schema 2.1 (mapeamento mecânico descrito em §7 — não depende dos bloqueios 1–2).
6. Implementar geração de `item_id` determinístico e `item_hash` no `pipeline` (réplica do padrão já existente em `aluno/backend/firestore_service.compute_item_hash`).
7. Construir a camada LOTUS/orquestração (depende do item 2 estar decidido) que recebe a saída do passo 5 e invoca o LLM só para a parte de classificação cognitiva.
8. Reescrever `cognitive_engine.py` (`DEFAULT_PIPELINE_SCHEMA`, `_SYSTEM_PROMPT_TEMPLATE`) para pedir ao LLM **somente** os campos que cabem a ele — `estrutura_cognitiva`, `distratores`, `intervencoes`, `pedagogia` (partes qualitativas), `qualidade.confianca_global`/`observacoes` — usando as escalas definidas no item 1.
9. Em `server.py:generate_pipeline`, montar o documento final combinando (5) + (8) + metadados de execução reais (`pipeline{}` do contrato, resolvendo a colisão de nome do item 7 da §7) — deixando `psicometria{}` e `qualidade.revisor` explicitamente `null` (não preenchíveis na geração, §8c).
10. Construir a validação estrutural + cross-check de IDs contra a ontologia (§9), como etapa antes de persistir.
11. Atualizar os consumidores (`aluno/backend/admin_routes.py:_build_public_doc`, `annotation_service.py`) para ler a nova forma.
12. Executar o plano de reset já registrado em `auditoria/PLANO-RESET-ITENS.md` (limpar os 21 registros de teste/seed).
13. Gerar o primeiro item real end-to-end e validar contra os passos 10–11.

---

## Resumo do que está fora de alcance sem mais informação

Dois bloqueios de decisão (itens 1 e 2 da ordem de implementação) impedem que a arquitetura pretendida seja totalmente implementada só com o que existe hoje em `pipeline/docs/` e no código. Nenhuma solução foi proposta para esses dois pontos nesta auditoria — propor uma seria inventar exatamente o que a tarefa pediu para não inventar.
