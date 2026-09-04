## documento: Auditoria Integral do Corpus Sapiens — WP 1.0 × WP 2.0 × Documentos Canônicos id: AUD-2026-08-17T03:42:31Z timestamp_utc: 2026-08-17T03:42:31Z timestamp_local: 2026-08-17T00:42:31-03:00 timezone: America/Sao_Paulo tipo: auditoria_de_corpus status: registro — nenhum arquivo canônico foi alterado escopo_canonico: pipeline/docs (= os 9 documentos do Project, por decisão do responsável em 2026-08-17) material_de_apoio: matriz_referencia.pdf (INEP) — nunca normativo autor: Claude (Cowork) sob direção de Sapiens

# Auditoria Integral do Corpus Sapiens

## 0. Nota de escopo e método

**Corpus auditado (canônico):**

|Sigla|Arquivo|
|---|---|
|WP1|`00 WHITE PAPER 1.0 (ANTIGO).md`|
|MAN|`01 Manual Oficial de Anotação Cognitiva Sapiens.md`|
|CON|`02 Constituicao Sapiens.md`|
|WP2|`03 White Paper v2.0.md`|
|ONT-J2|`04 Ontologia Cognitiva Sapiens — v1.4 JSON.md`|
|ONT|`05 Ontologia Cognitiva Sapiens — v1.4.md`|
|SCH|`06 Schema Sapiens 2.1.json.md`|
|BEH|`07 behavior student 1.4.md`|
|ONT-J1|`ontology_v1.4.json`|

**Material de apoio externo:** `matriz_referencia.pdf` (Matriz de Referência ENEM, INEP).

**Método.** Leitura integral de todos os nove documentos; comparação campo a campo dos dois artefatos JSON; verificação aritmética de todas as contagens declaradas; rastreamento de cada ID citado em qualquer documento contra sua definição em todos os demais; verificação de cada remissão interna (§, capítulo, nome de arquivo).

**Convenção de severidade.**

- **BLOQUEANTE** — impede anotação consistente, ou torna a transição 1.4→1.6 irreversível/inauditável.
- **ESTRUTURAL** — contradição entre documentos normativos que produzirá divergência silenciosa.
- **MENOR** — erro de redação, aritmética ou referência, sem consequência de dado.

---

## 1. O que do WP 1.0 foi corrigido, substituído ou removido no WP 2.0

O WP 2.0 não é uma revisão editorial do WP 1.0 — é uma **mudança de gênero documental**. O WP 1.0 é uma especificação de sistema (teoria + arquitetura + engenharia + ontologia povoada, ~4 capítulos, ~120 referências). O WP 2.0 é uma auditoria epistemológica: dois axiomas com grau de confiança, quatro pressupostos, vinte e duas unidades de grau de liberdade, e um mapa de o que se sabe versus o que se decidiu.

Isso explica quase todas as diferenças abaixo — e também explica a perda, tratada na Seção 2: o WP 2.0 auditou o WP 1.0 sem preservá-lo.

### 1.1 Corrigido (o WP 2.0 estava certo em corrigir)

|#|Item|WP 1.0|WP 2.0|Avaliação|
|---|---|---|---|---|
|C-a|Compromisso bayesiano|§2.9.3 prescreve BKT (P(L0), P(T), P(G), P(S)) como _o_ estimador|§4.3: classe de equivalência entre quatro famílias matemáticas; especificidade bayesiana rebaixada a **35%** de confiança|**Correção legítima e importante.** O WP 1.0 confundia uma escolha de implementação com uma consequência da teoria|
|C-b|O grafo simbólico|Tratado como consequência direta da evidência (Princípios 1 e 2)|§12.2: instanciar como grafo tipado é **hipótese arquitetural contingente** a GL-8/GL-16|Correção legítima. O WP 1.0 já sinalizava a distinção em §1.3.4 e §1.6.5, mas não a mantinha|
|C-c|Causalidade entre fatores|Arestas `pre_requisito` usadas com força causal operacional|§5.2: qualificador causal a **35%**; §5.4: a pergunta geral pode ser irrespondível por experimento único|Correção legítima|
|C-d|Competência como nível primário|Nível 2 da hierarquia, com ficha canônica e entidade de banco próprias|Hipótese sob auditoria (**55%**); o WP 2.0 **corrige explicitamente** uma consolidação anterior que a listava como definição aceita|Correção legítima, e exemplarmente registrada|
|C-e|Efeito "dois sigma"|Já qualificado no próprio WP 1.0 §1.6.3 via VanLehn (2011)|Herdado e generalizado como disciplina de calibração|Continuidade, não correção|
|C-f|Arranjo/combinação/permutação|`PROC-INC-001` como processo cognitivo legítimo|§13.4: reconhecido como mistura de capacidade geral com conteúdo procedural; **não corrigido**, registrado como pendência|Diagnóstico correto; pendência ainda aberta (resolvida de fato pela v1.4, que o absorveu em `PROC-INC-04`)|

### 1.2 Substituído (mudou de forma, com custo)

|#|Item|WP 1.0|WP 2.0 / corpus atual|Custo|
|---|---|---|---|---|
|S-a|**Hierarquia**|**5 níveis**: Domínio → Competência → Processo → Habilidade → **Indicador Comportamental**, mais 2 camadas transversais (erro, intervenção)|CON Cap. 4: **6 tipos de nó** + 2 referências externas (Item, Resposta Observada). O Nível 5 desaparece|Ver perda **L1**|
|S-b|**Ficha do nó**|§2.6: template canônico com ~40 campos (base científica, exemplos, contraexemplos, manifestação por área, relações no grafo, desenvolvimento, demandas cognitivas, sinais de identificação, erros, estimação de domínio, geração e intervenção)|ONT-J1: 6 campos por processo (`id`, `nome`, `definicao_operacional`, `dominios`, `competencia`, `tipos_erro`, `origem_v1_3`)|Ver perdas **L4–L9**|
|S-c|**Taxonomia de erro**|13 categorias **psicológicas** (Reason 1990: slip/lapse/mistake; VanLehn 1990: buggy algorithms; diSessa 1993: misconceptions) — conceitual, procedimental, atencional, de interpretação, de leitura, de cálculo, de estratégia, metacognitivo, de memória, sobrecarga, transferência inadequada, viés cognitivo, automatização incorreta|ONT §6: 13 tipos **operacionais indexados a Processo** — leitura literal deficiente, inferência indevida, modelagem/tradução, dimensional, direção proporcional, gráfico/tabela, causa/correlação, generalização, variável de controle, notação simbólica, ordem de grandeza, validade lógica, classificação superficial|**Mesma contagem, conteúdos disjuntos, numeração colidente.** Ver conflito **N1** e perda **L3**|
|S-d|**IDs de processo**|Cap. 2: `RQ-PROP-003`, `LEIT-INF-002`, `HIST-CAUSAL-002`, `ARGUM-CONSTR-003`. Cap. 4: `PROC-QUANT-001`…`005`, `PROC-EXP-001`…`004`, `PROC-ESTR-001/002` (3 dígitos)|`PROC-QUANT-01`…`04`, `PROC-EXP-01/02` (2 dígitos)|Ver conflito **N2**|
|S-e|**Domínios**|Cap. 4: **8** (QUANT, ESPACO, MUDANCA, INCERTEZA, CAUSAL, SISTEMICO, EXPERIMENTAL, **ESTRUTURA**)|ONT: **11** (ESTRUTURA some; SIMBOLICO, TEXTUAL, LOGICO, CLASSIF surgem)|Ver conflito **N5**|
|S-f|**Error Trace**|§2.8: **sequência ordenada** `erro_primário → erro_secundário → …`, cada nó com `{tipo, processo_afetado, confiança}`|CON §4.3: conjunto **ponderado sem ordem**. SCH: **um erro único** por alternativa|Ver perda **L2** — a mais grave da auditoria|
|S-g|**Contrato de saída da IA**|§2.9.4: objeto com `cognitive_mappings[]`, `distratores_estruturais[]`, `nivel_abstracao_estimado`, `carga_cognitiva_estimada`, `confianca_da_anotacao`|SCH 2.1: objeto muito mais rico em fonte/recursos/psicometria, mais pobre em cognição (sem carga cognitiva, sem nível de abstração)|Parcialmente ganho, parcialmente perda|

### 1.3 Removido sem substituto

Nenhum destes reaparece em qualquer documento canônico atual:

1. **Toda a camada de decisão e ação** — motor de recomendação por ZPD (§2.9.3 item 5), agendador de repetição espaçada com interleaving (item 6), detector de chute (item 2), detector de falsa proficiência (item 3), detector de automatização (item 4), motor de geração de itens por variação de superfície (item 7), analisador de cadeia de erro (item 8).
2. **`MasteryEstimate.estado`** — enum `nao_iniciado | em_aquisicao | dominado | automatizado | esquecimento_provavel`, ancorado em Fitts & Posner (1967).
3. **Pipeline de ingestão** — Via A (cadastro manual) e Via B (análise por IA), com especificação de o que entra, o que a IA infere e o que exige validação humana (§3.3).
4. **A regra de governança de ingestão** (§3.3.3): _"nenhum item passa a atualizar `MasteryEstimate` de aluno real sem que seus `cognitive_mappings` de papel nuclear tenham sido confirmados por ao menos um revisor humano"_. É a única regra em todo o corpus que protege o motor de crença de anotação não validada.
5. **As cinco Regras de Modelagem** (§3.6).
6. **Critérios quantitativos de dimensionamento** (§3.5): 80–120 processos; 15–20 itens por processo, 30+ para os priorizados; 1.500–2.500 itens no banco inicial.
7. **Painéis de aluno (§2.9.5) e de professor (§2.9.6)**, incluindo a auditoria estatística contínua de concordância IA×humano.
8. **A bibliografia inteira** — ~120 referências completas em WP1; WP2 cita autores em texto corrido e **não tem seção de referências**.

---

## 2. Conceitos importantes do WP 1.0 perdidos no WP 2.0

Ordenados por consequência. Estes são os candidatos a recuperação — não por nostalgia, mas porque cada um é hoje uma promessa não cumprida de algum documento canônico vigente.

### L1 — Indicador Comportamental (Nível 5) · BLOQUEANTE

WP1 §2.1.3 define o Nível 5 como _"o nível que efetivamente alimenta os algoritmos de estimativa de domínio"_: tempo de resposta, padrão de erro específico, escolha de distrator, sequência de interação.

Hoje: CON Cap. 3 define seis tipos de nó e **nenhum** é o Indicador Comportamental. BEH coleta `tempo_resposta_segundos`, `numero_tentativas`, `mudou_resposta` — dados que **não têm nó ontológico que os interprete**. O Axioma da Crença Calibrada exige revisão de confiança à luz de evidência, e o único canal de evidência formalizado no corpus atual é acerto/erro binário.

Consequência: BEH é hoje um contrato órfão. Ou o Indicador Comportamental volta (como camada transversal, não como sexto nível), ou BEH precisa declarar explicitamente que seus campos de desempenho não alimentam crença.

### L2 — Error Trace como cadeia ordenada · BLOQUEANTE

WP2 §15 lista **Error Trace** como o primeiro ativo protegido, _"identificado de forma independente, em múltiplas rodadas, como o elemento mais original de todo o corpus"_, e declara que _"qualquer arquitetura futura derivada deste documento deve preservá-lo"_.

O que o WP1 §2.8 define, e que é a coisa toda: a **ordem causal**. Um erro procedimental observado na resposta final pode ter raiz em um erro de interpretação anterior; tratar a manifestação de superfície na intervenção seria ineficaz.

Degradação em dois saltos:

- **Salto 1** (CON §4.3): `Resposta Observada → Tipo de Erro` vira N:M ponderada — **conjunto, não sequência**. A ordem some.
- **Salto 2** (SCH `distratores[]`): `erro` é **um** ID por alternativa. A multiplicidade some também.

Resultado: o ativo protegido nº 1 do projeto não é representável em nenhum contrato canônico vigente. E **não existe schema do objeto Error Trace em lugar nenhum** — nem em SCH (que é do item), nem em BEH (que é do evento).

### L3 — Taxonomia de erro por mecanismo psicológico · ESTRUTURAL

As duas taxonomias de 13 erros são **ortogonais, não substitutas**:

- v1.4 responde **o quê** falhou: "confusão de direção em relação proporcional" (`ERR-05`).
- WP1 responde **por quê**: erro conceitual (misconception coerente), erro de estratégia (escolha de abordagem), erro por automatização incorreta (rápido, sem esforço, resistente a feedback), erro atencional (slip).

Sem a segunda dimensão, **a Intervenção não sabe o que remediar**. `INT-03` ("prática guiada de relações proporcionais") é a resposta certa para um erro conceitual e a resposta errada para um erro por automatização incorreta — que exige interferência deliberada no automatismo, não mais prática. As 11 intervenções da v1.4 são todas ambíguas nesse eixo.

Recuperação recomendada: como **atributo do Tipo de Erro** (`mecanismo_psicologico`, vocabulário fechado de 13), não como nova entidade nem como novo nível. Custo baixo, ganho diagnóstico alto.

### L4 — Falsa proficiência com critério operacional · ESTRUTURAL

WP2 §15 preserva "falsa proficiência" como ativo protegido e _"categoria de primeira classe, não ruído estatístico"_. Mas apagou o que a torna detectável.

WP1 dá o critério em cada ficha (`criterio_de_deteccao_de_falsa_proficiencia`) e o algoritmo (§2.9.3 item 3): comparar acurácia em itens que compartilham `cognitive_process_id` mas variam o domínio de superfície; queda sob variação de superfície é o sinal. Exemplo concreto registrado para `RQ-PROP-003`: _"acerto sistemático apenas quando a proporcionalidade é anunciada explicitamente, falha quando embutida em contexto de física/química"_.

Hoje nenhum documento canônico diz como detectá-la. Ativo protegido sem implementação.

### L5 — `grau_transferencia` por processo · ESTRUTURAL

WP2 §15 lista o **campo de grau de transferência** como ativo protegido (o único com ressalva anexada: a ideia é preservada, sua formalização como categoria fixa alto/médio/baixo permanece sob revisão por GL-10).

WP1 Cap. 4 registra o campo em **todos os 28 processos**, com justificativa: `PROC-INC-004` (julgamento sob incerteza) recebe `baixo_medio` porque a própria literatura de Kahneman & Tversky é evidência de que o viés persiste em especialistas treinados — alta relevância cognitiva, baixa transferência natural, exigindo intervenção explícita e repetida.

A v1.4 **não tem o campo**. Ativo protegido declarado, removido sem registro.

### L6 — `frequentemente_confundidas_com` / `frequentemente_mascaradas_por` · ESTRUTURAL

WP1 §2.6. São exatamente os metadados que resolveriam as fronteiras que ONT §10 deixou em aberto e que o MAN teve de resolver por regra ad hoc (DOM-CAUSAL × DOM-EXPERIMENTAL; PROC-CLASSIF-01 × PROC-ESPACO-03).

`frequentemente_mascaradas_por` é ainda mais importante: é o registro operacional do ativo protegido **"inversão disciplinar"** — a competência real escondida atrás de outra aparente. Exemplo do WP1: `LEIT-INF-002` frequentemente mascarada por `MAT-PROB-VERBAL-001` — _"erro de interpretação em matemática é, na raiz, erro desta competência"_.

### L7 — `sinais_de_identificacao_automatica` · ESTRUTURAL, com ressalva

WP1 §2.6: palavras-chave típicas, estruturas linguísticas típicas, operações matemáticas típicas, elementos visuais típicos, comandos típicos do enunciado. Era o insumo do pipeline de anotação por IA e da busca antidiplicação (Regra de Modelagem 3).

**Ressalva obrigatória na recuperação:** MAN §8 proíbe explicitamente atribuir processo por palavra-chave (_"a palavra 'proporção' no texto não implica PROC-QUANT-02"_). Não há contradição — o WP1 define esses sinais como **triagem de candidatos**, nunca como critério de decisão. Mas isso precisa ser dito no documento de recuperação, senão o campo reintroduz exatamente o vício que o Manual combate.

### L8 — Contraexemplos por nó · ESTRUTURAL

WP1 §2.6: `contraexemplos` = _"item que parece exigir a competência mas não exige (distrator estrutural)"_. Exemplo real: para `RQ-PROP-003`, juros compostos — relação não linear frequentemente confundida com proporcionalidade direta.

A v1.4 tem "o que não é" em prosa, o que é diferente: prosa define fronteira conceitual, contraexemplo dá o caso concreto. **É o insumo mais direto para elevar o kappa da anotação dupla que o WP2 Cap. 16 exige.**

### L9 — Vetores de tipo de conhecimento / raciocínio / processamento · MENOR-ESTRUTURAL

WP1 §2.2 (6 tipos de conhecimento), §2.3 (13 tipos de raciocínio), §2.4 (12 tipos de processamento), registrados como **vetores de peso**, não categorias exclusivas.

CON §2.1 mantém **"Conhecimento" como dimensão transversal aplicável a qualquer nó de qualquer nível** — e nenhum documento operacional a implementa. É a dimensão transversal declarada na Constituição e nunca instanciada.

Recuperação parcial recomendada: os 6 tipos de conhecimento (que a Constituição já promete nominalmente). Os 13 tipos de raciocínio e 12 de processamento são provavelmente excesso de granularidade para o estágio atual — registrar como diferido, não recuperar.

### L10 — A camada de decisão não está vazia; foi esvaziada · BLOQUEANTE

WP2 §6.3: _"Nenhuma evidência no corpus examinado sustenta uma formulação de como o sistema deveria selecionar a próxima ação pedagógica a partir dessa crença."_

**Esta afirmação é factualmente incorreta em relação ao WP 1.0.** WP1 §2.9.3 especifica:

- **Item 5 — Motor de recomendação**: seleciona o próximo processo entre os nós cujos pré-requisitos têm `probabilidade_dominio` acima do limiar mas cujo próprio valor está abaixo. É o proxy computacional explícito da ZPD, ancorado em Doignon & Falmagne (1985) e Vygotsky (1978).
- **Item 6 — Agendador de revisão espaçada**: curva de esquecimento parametrizada por Cepeda et al. (2006), com interleaving entre competências (Rohrer & Taylor, 2007).
- **§2.9.7** — as features de entrada do recomendador, incluindo priorização de erro conceitual sobre erro atencional.

O WP2 tem razão em não _aceitar_ isso como axioma — é [DE], decisão de engenharia, não consequência dos dois axiomas. Mas a formulação "não há evidência no corpus" apaga um conteúdo que existe e é ancorado em literatura. **O slot deveria ser declarado como "conteúdo herdado do WP 1.0, rebaixado a proposta de engenharia não derivada dos axiomas", não como vazio.**

### L11 — Estados de maestria (Fitts-Posner) · ESTRUTURAL

`MasteryEstimate.estado` com `automatizado` e `esquecimento_provavel` é a resposta operacional que o WP1 já dava a duas perguntas que o WP2 lista como **abertas**: GL-7 (decaimento é obrigatório?) e GL-5a (existem regimes temporais distintos?). Não resolve as perguntas — mas é uma hipótese específica e testável que foi descartada sem registro.

### L12 — Dimensionamento quantitativo · MENOR

WP1 §3.5: 80–120 processos; 1.500–2.500 itens. A v1.4 tem **25** processos. A redução veio das fusões legítimas da auditoria v1.3 (§2.4 da Constituição, ônus da separação), mas **a discrepância de fator 4 nunca foi conciliada** com o critério de viabilidade do próprio projeto, que argumentava que abaixo de certo tamanho o grafo não tem o que recomendar.

### L13 — Regras de Modelagem e regra de governança de ingestão · BLOQUEANTE

Especialmente a de §3.3.3 (nenhum item alimenta crença sem confirmação humana do mapping nuclear). É a implementação operacional do Princípio 7 do WP1 — o único mecanismo que impede o pipeline de IA de contaminar o motor de crença. Não tem equivalente em CON, MAN, SCH ou BEH.

### L14 — Bibliografia · ESTRUTURAL

WP2 mantém a disciplina [EC]/[IT]/[DE] como ativo protegido e a estende aos próprios axiomas. Mas **sem referências, o rótulo [EC] não é verificável**. Um documento que classifica afirmações por qualidade de evidência e não cita a evidência perdeu a propriedade que o rótulo existe para garantir.

---

## 3. Conflitos que permanecem entre os documentos canônicos

### 3.1 Conflitos revelados pelo WP 1.0 (novos nesta auditoria)

**N1 · BLOQUEANTE — Colisão de namespace de Tipo de Erro entre gerações.** `error_type_id` 1–13 (WP1) e `ERR-01`…`ERR-13` (v1.4) são conjuntos **disjuntos com numeração idêntica**. Prova concreta: o JSON de exemplo do WP1 §3.4 registra `{"error_type_id": 7, "nome": "erro de estratégia"}`; na v1.4, `ERR-07` = "confusão causa/correlação". Qualquer anotação legada produzida sob o WP1 será lida errado pela v1.4 sem levantar exceção.

**N2 · BLOQUEANTE — Três gerações de esquema de ID de processo, com dangling reference interna no WP1.**

- WP1 Cap. 2: `RQ-PROP-003`, `LEIT-INF-002`, `HIST-CAUSAL-002`, `ARGUM-CONSTR-003`
- WP1 Cap. 4: `PROC-QUANT-001`…`005`, `PROC-EXP-001`…`004` (3 dígitos)
- v1.4: `PROC-QUANT-01`…`04` (2 dígitos)

Pior: **o WP1 é internamente inconsistente**. `COMP-QUANT-02` declara `processos: [PROC-QUANT-003, PROC-QUANT-004, PROC-QUANT-005]`, mas o bloco correspondente é declarado com `id: RQ-PROP-003`, e `PROC-QUANT-004` declara `pre_requisitos: [RQ-PROP-003]`. **`PROC-QUANT-003` é referenciado e nunca definido.** O inventário §4.5 registra "PROC-QUANT-001/002/004/005, RQ-PROP-003" — reconhecendo o problema sem corrigir a referência da competência.

Equivalências que precisam ser fixadas explicitamente: `PROC-EXP-001` (WP1) = `PROC-EXP-02` (v1.4); `RQ-PROP-003` = `PROC-QUANT-02`; `PROC-SIST-003` = `PROC-MUD-02`; `PROC-CAUSAL-003` = `PROC-SIST-01`; `PROC-INC-003` = `PROC-INC-02` + `PROC-INC-03`.

**N3 · ESTRUTURAL — WP2 §6.3 contradiz WP1 §2.9.3.** Ver perda L10.

**N4 · MENOR, resolvível agora — WP2 declara depender de um documento que já está no corpus.** WP2 §14.4 afirma que a derivação original produziu "8 domínios, 16 competências e 28 processos" — que é **exatamente** o inventário de WP1 §4.5 — sem citar sua fonte. E a Pendência 2 do WP2 diz que a reprodução integral _"exigirá consulta ao material fonte original do Capítulo 4 do White Paper 1.0"_. Com o WP1 no corpus, **essa pendência está resolvida e deve ser fechada formalmente**.

**N5 · ESTRUTURAL — Um nó que o WP2 declara preservado não existe na v1.4.** WP2 §14.3 lista, entre as duas arestas cross-domínio preservadas, _"reconhecimento de padrão como mecanismo de transferência, ligando PROC-MUD-003 a PROC-ESTR-001 — padrão matemático e padrão científico"_.

`PROC-ESTR-001` (WP1 §4.4: "Identificação de Padrão Estrutural Recorrente entre Fenômenos Distintos", ancorado em Gentner 1983 e NRC 2012) **não tem correspondente na v1.4**. O `DOM-ESTRUTURA` do WP1 foi dividido em `DOM-SIMBOLICO` + `DOM-TEXTUAL` — que não têm relação com seu conteúdo; a parte estrutura-função foi para `PROC-ESPACO-03`; e a parte **padrão recorrente / analogia estrutural desapareceu inteiramente**.

Somado ao rebaixamento de "leitura de gráficos" (ver C8 abaixo), são **dois** elementos declarados protegidos que a v1.4 removeu sem registro.

**N6 · ESTRUTURAL** — `grau_transferencia` é ativo protegido no WP2 e não existe na v1.4. (= L5, registrado também como conflito por ser contradição direta entre dois documentos vigentes.)

**N7 · MENOR — `distratores[].plausibilidade` no SCH ressuscita o objeto que a v1.4 removeu.** ONT §9 removeu `ERR-13` "distrator plausível" da ontologia por ser propriedade do item, não do aluno. SCH o traz de volta como campo do item. **Conceitualmente correto** — é exatamente onde ele deve estar. Mas ninguém declarou essa realocação, e sem registro a próxima auditoria vai removê-lo de novo.

**N8 · ESTRUTURAL — Campos do SCH sem origem normativa.** `processos[].dificuldade_local` e todo o bloco `psicometria` (dificuldade empírica, discriminação, taxa de acerto, tempo médio) não são definidos nem previstos por WP2, CON ou ONT. Vieram do WP1 (`peso_estimado_na_dificuldade_do_item`, `dificuldade_estimada`) sem trilha de proveniência. **O Schema está à frente da teoria em pontos que ninguém arbitrou.**

**N9 · BLOQUEANTE — O Error Trace não tem schema em lugar nenhum.** WP1 tinha `StudentResponse` + `ErrorTrace` como entidades ligadas. Hoje: SCH descreve o **item** anotado; BEH descreve o **evento** de resposta; CON §4.3 diz que `Resposta→Erro` é produzida em runtime e que _"sua especificação de schema pertence à Especificação Técnica"_ — **um documento que não existe no corpus**. O objeto de saída do motor diagnóstico é remetido a um documento fantasma.

**N10 · ESTRUTURAL — A heterarquia está desligada justamente onde o WP1 provou que ela é necessária.** MAN §11: _"Pertencimento Processo↔Domínio é 1:1 nesta versão… não adicione um segundo Domínio por conta própria."_ Mas WP1 Cap. 4 registra arestas cross-domain reais e justificadas: `PROC-ESPACO-003` tem `pre_requisitos: [RQ-PROP-003, PROC-ESPACO-001]` (QUANT + ESPACO); `PROC-EXP-003` tem `pre_requisitos: [PROC-INC-003]` (EXPERIMENTAL ← INCERTEZA); `PROC-MUD-001` tem `pre_requisitos: [LEIT-INF-002, RQ-PROP-003]` (MUDANCA ← TEXTUAL + QUANT). O WP1 conclui, em §4.5, que já não se trata de dois grafos paralelos mas de **um grafo único parcialmente entrelaçado**.

Com Humanas e Linguagens, o entrelaçamento cresce. Manter 1:1 na v1.6 é insustentável.

### 3.2 Conflitos já identificados, que permanecem

**C1 · BLOQUEANTE — `PROC-ESPACO-03 → ERR-13`: quatro estados para um nó.** ONT §3 diz "Erro: ERR-14 (renumerado ERR-13)"; ONT §6 nota diz que **não** foi incluído; ONT §10.3 lista o processo entre os sem erro; MAN declara ter corrigido no JSON. **Ambos os JSONs mantêm o vínculo.** Verificação aritmética: processos com `tipos_erro: []` no JSON = **12**; MAN e ONT §10.3 dizem **13**. Os JSONs do corpus são as versões **não corrigidas**.

**C2 · BLOQUEANTE — SCH viola o Axioma da Crença Calibrada.** `distratores[].erro` é ID único; CON §4.4 proíbe cardinalidade determinística de valor único onde há mais de um candidato plausível. `probabilidade_estimada` mede a probabilidade de **escolha do distrator**, não a distribuição sobre **causas candidatas**.

**C3 · BLOQUEANTE — SCH não registra a versão da ontologia.** `schema_version` diz literalmente _"não confundir com a versão da ontologia"_ e não existe campo `ontology_version`. Todos os IDs referem-se à "ontologia canônica vigente", sem dizer qual. **Pré-requisito absoluto da transição 1.4→1.6.**

**C4 · ESTRUTURAL — Vocabulário divergente MAN × SCH.** SCH: `papel` ∈ {`nuclear`, `secundario`}. MAN: "Central 0.7" / "Secundário Necessário 0.3". MAN impõe máximo de 2 processos com peso; o array do SCH é ilimitado. A "regra definida pelo contrato" que o SCH invoca repetidamente não está localizada em nenhum documento nomeado.

**C5 · BLOQUEANTE — A Constituição cita quatro capítulos que não existem.** Cap. 5 (critérios de inclusão), 7 (granularidade), 11 (protocolo de teste), 12 (questões diferidas) são invocados como remissão normativa em §2.3, §3.4, §3.7.2 e §4.3. O documento termina no Adendo 3.7. **Toda decisão que a Constituição "resolve por remissão" está sem resolução.**

**C6 · ESTRUTURAL — WP2 Parte V está desatualizada e não marcada como superada.** 8 domínios vs. 11; `DOM-ESTRUTURA` vs. sua dissolução; nenhuma indicação de supersessão.

**C7 · ESTRUTURAL — Colisão de ID entre WP2 e v1.4.** (Caso particular de N2: WP2 herda os IDs de 3 dígitos do WP1 Cap. 4.)

**C8 · ESTRUTURAL — "Leitura de gráficos" rebaixada de nó a habilidade.** WP2 §15 lista os cinco nós prioritários como ativo protegido; a v1.4 absorveu leitura de gráfico/tabela como `HAB-44`/`HAB-46` sob `PROC-TEXT-01/02`. Defensável sob CON §3.7.3, mas contraria cláusula de preservação explícita, sem registro.

**C9 · MENOR — Aritmética da tabela ONT §9.** "Tipos de Erro: 13 → 13", descrito como "1 removido, 1 realocado, 1 novo" = 12.

**C10 · MENOR — Nome de arquivo declarado ≠ real.** ONT remete a `sapiens_ontologia_v1.4.json`; o arquivo é `ontology_v1.4.json`. ONT §3 também remete a "tabela §5" para uma tabela que está em §6.

**C11 · BLOQUEANTE — A v1.6 é, hoje, formalmente proibida.** MAN §12.8 congela Manual e Ontologia; WP2 Cap. 16 declara a sequência piloto → anotação dupla cega → kappa → ajuste como _"condição de entrada para qualquer expansão de domínio, não uma recomendação"_; WP2 Cap. 20 condiciona a expansão para Humanas e Linguagens à resolução de GL-12b, aberto. **Não existe procedimento de emenda em documento nenhum.**

### 3.3 Sobreposições internas remanescentes

- **S1** — 4 de 12 competências agrupam exatamente 1 processo (`COMP-03`, `COMP-06`, `COMP-07`, `COMP-12`); `COMP-03` tem nome **idêntico** ao seu único processo.
- **S2** — `DOM-ESPACO` falha o teste §3.7.1: critério de inclusão une por "ou" duas operações (representar/decompor forma **e** inferir função de arranjo estrutural).
- **S3** — Fronteira `PROC-ESPACO-03` × `PROC-CLASSIF-01` resolvida por regra linguística no Manual, não por critério cognitivo.
- **S4** — Fronteira `DOM-CAUSAL` × `DOM-EXPERIMENTAL` resolvida no Manual: inversão de hierarquia normativa (documento operacional arbitrando fronteira de domínio).
- **S5** — Conflação conteúdo/processo sobrevivendo na camada Habilidade: `HAB-22` ("calcular quantidade de calor trocada") sob `PROC-MUD-02` ("rastrear invariante") não manifesta o processo-pai.
- **S6** — `PROC-INC-02` (média/mediana/moda em um nó): já registrado como pendência em ONT §10.2 e MAN §11.

---

## 4. Ações por documento

### 4.1 Documentos existentes

|Doc|Ação|Justificativa|
|---|---|---|
|**WP1** `00 WHITE PAPER 1.0`|**SUPERSEDED, com extração prévia obrigatória**|Não é fonte normativa. Mas é a **única** fonte de L1–L14, e fecha a Pendência 2 do WP2. Marcar como superseded **antes** de extrair repetiria exatamente o erro que esta auditoria documenta|
|**WP2** `03 White Paper v2.0`|**CORRIGIR — errata, sem reabrir o núcleo congelado**|§6.3 e §12.4: declarar a camada de decisão como "conteúdo herdado do WP1, rebaixado a [DE] não derivada dos axiomas", não como vazia (L10/N3). Parte V: marcar como superseded pela Ontologia v1.4 (C6). Pendência 2: fechar (N4). Adicionar seção de referências (L14). Adotar o esquema de ID unificado (C7/N2)|
|**CON** `02 Constituicao Sapiens`|**COMPLETAR**|Redigir ou revogar formalmente os Caps. 5, 7, 11, 12 (C5). Acrescentar capítulo de governança e versionamento. Decidir: Indicador Comportamental (L1), escopo de Arte e Linguagem Corporal, heterarquia PROC↔DOM (N10)|
|**ONT** `05 Ontologia v1.4.md`|**CORRIGIR — patch v1.4.1**|C1 (nota do §3), C9 (aritmética), C10 (nome de arquivo e remissão §5→§6). **Sem alteração de conteúdo ontológico** — é higiene, não emenda|
|**ONT-J1** `ontology_v1.4.json`|**CORRIGIR — patch v1.4.1**|Remover `ERR-13` de `PROC-ESPACO-03` (C1). Acrescentar bloco de versionamento: `supersedes`, `valid_from`, `changelog_ref`, `status`|
|**ONT-J2** `04 Ontologia … JSON.md`|**DEPRECAR**|Duplicata materialmente idêntica ao JSON. Duas cópias manuais do mesmo artefato é o mecanismo pelo qual fontes divergem em silêncio|
|**MAN** `01 Manual`|**ATUALIZAR — v1.1**|Alinhar a contagem 13/12 após o patch; unificar vocabulário de `papel` com o Schema (C4); nomear o documento onde vive a regra de peso; criar seção de registro estruturado de observação de campo; devolver a fronteira DOM-CAUSAL×DOM-EXPERIMENTAL à Constituição (S4)|
|**SCH** `06 Schema Sapiens 2.1`|**CORRIGIR — versão 2.2**|`ontology_version` (C3); `distratores[].erros[]` como lista ponderada com ordem causal (C2/L2); enum de `papel` alinhado (C4); campos estruturados de incerteza; `fonte.matriz_referencia` (código ENEM); declarar proveniência de `dificuldade_local` e `psicometria` (N8); registrar a realocação de `plausibilidade` (N7)|
|**BEH** `07 behavior student 1.4`|**RENOMEAR + ATUALIZAR**|Remover "1.4" do nome (colide com a versão da ontologia); acrescentar `ontology_version`; declarar a relação entre seus campos de desempenho e o Indicador Comportamental (L1)|
|`matriz_referencia.pdf`|**MANTER como apoio externo**|Instrumento de teste de cobertura. Nunca fonte de categorias|

### 4.2 Documentos a criar

|#|Documento|Função|Depende de|
|---|---|---|---|
|**G**|`00 Governança e Versionamento Sapiens v1.0`|Procedimento de emenda; política de numeração (incl. por que 1.4→1.6); estados (rascunho/ativo/congelado/superseded); quem descongela e como; regra de precedência entre documentos|—|
|**E**|`08 Registro de Extração do WP 1.0`|O que foi recuperado (L1–L14), o que foi descartado, e a justificativa de cada decisão|G|
|**R**|`09 Mapa de Rastreabilidade de IDs`|Tabela WP1-Cap2 ↔ WP1-Cap4 ↔ v1.4 ↔ v1.6, para nós **e** para tipos de erro (N1, N2)|E|
|**T**|`10 Especificação do Error Trace v1.0`|O objeto de saída do motor diagnóstico — hoje remetido a uma "Especificação Técnica" inexistente (N9). Recupera L2 e L3|E, R|
|**P**|`11 Protocolo de Piloto e Concordância`|Operacionaliza WP2 Cap. 16: amostra, anotação dupla cega, kappa, critérios de ajuste. É a condição de entrada declarada para a v1.6|MAN v1.1, SCH 2.2|
|**O**|`12 Ontologia Cognitiva Sapiens v1.6`|Só depois de tudo acima|todos|
|**M**|`13 Mapa de Cobertura Matriz ENEM ↔ Ontologia` _(opcional)_|Instrumento de medição de cobertura, não fonte normativa|R|

---

## 5. Ordem de execução por dependência

> **Qual arquivo alterar primeiro: nenhum.** Os três primeiros passos são **criações**. O primeiro arquivo **existente** a ser alterado é `ontology_v1.4.json`, e só no passo 4 — porque ele está formalmente congelado hoje (MAN §12.8) e editá-lo sem procedimento de emenda repetiria o vício que esta auditoria documenta.

### Fase 0 — Desbloqueio normativo

**1. CRIAR `00 Governança e Versionamento Sapiens v1.0`** _Por que primeiro:_ o Manual congela Manual e Ontologia; o WP2 condiciona expansão a um piloto e a GL-12b. Sem procedimento de emenda, **toda** alteração posterior — inclusive corrigir uma vírgula — é uma violação de norma. É também o único documento que pode ser criado agora sem violar nada, porque nenhuma norma existente o proíbe. Todo o resto depende dele.

### Fase 1 — Preservação antes de supersessão

**2. CRIAR `08 Registro de Extração do WP 1.0`** _Por que aqui:_ marcar o WP1 como superseded antes de extrair é literalmente como o projeto perdeu L1–L14 na transição 1.0→2.0. Extrair primeiro, marcar depois. Depende de **1** (autoridade para declarar o que é canônico).

**3. CRIAR `09 Mapa de Rastreabilidade de IDs`** _Por que aqui:_ é insumo obrigatório de todos os patches seguintes — o patch do JSON precisa saber o que `ERR-13` significa em cada geração antes de tocar em `ERR-13`. Depende de **2**.

### Fase 2 — Higiene do que já está congelado

**4. CORRIGIR `ontology_v1.4.json` → v1.4.1** ← _primeiro arquivo existente alterado_ _Por quê agora:_ é o único conflito que **impede anotação consistente hoje** (C1); a correção já foi decidida e declarada pelo Manual, portanto não é decisão nova; e é uma linha. Depende de **1** (autoridade) e **3** (namespace).

**5. CORRIGIR `05 Ontologia v1.4.md` → v1.4.1** _Por que logo depois:_ prosa e JSON precisam voltar a concordar na mesma rodada, ou a divergência C1 apenas troca de lado. Depende de **4**.

**6. DEPRECAR `04 Ontologia … JSON.md`** _Por que aqui:_ só se deprecia uma cópia depois que o substituto está correto. Depende de **4** e **5**.

**7. ATUALIZAR `01 Manual` → v1.1** _Por que aqui:_ o Manual afirma contagens ("13 dos 25 processos") que só se tornam verdadeiras **depois** do patch. Atualizá-lo antes criaria uma terceira versão da mesma contagem. Depende de **4, 5, 6**.

### Fase 3 — Contratos de dados

**8. CRIAR `10 Especificação do Error Trace v1.0`** _Por que antes do Schema:_ o campo `distratores[].erros[]` só pode ser especificado depois que o objeto Error Trace existir. Hoje a Constituição o remete a um documento fantasma. Depende de **2** (L2/L3) e **3**.

**9. CORRIGIR `06 Schema 2.1 → 2.2`** _Por que aqui:_ `ontology_version` é o que torna a transição 1.4→1.6 reversível e auditável. Toda anotação produzida antes deste passo é indatável. Depende de **1, 3, 8**.

**10. ATUALIZAR `07 behavior`** _Por que depois do Schema:_ herda dele a convenção de versionamento e a decisão sobre Indicador Comportamental. Depende de **9**.

### Fase 4 — Camada teórica

**11. CORRIGIR `03 White Paper v2.0` (errata)** _Por que tarde:_ é o documento de maior autoridade do corpus. Corrigi-lo antes de saber exatamente o que foi recuperado do WP1 e como o Error Trace ficou especificado produziria uma segunda errata. Depende de **2, 5, 8**.

**12. COMPLETAR `02 Constituicao Sapiens`** _Por que por último na teoria:_ os capítulos ausentes são justamente critérios de inclusão (5), granularidade (7), protocolo de teste (11) e questões diferidas (12) — todos dependem de o WP2 já ter declarado o que a camada de decisão consome e o que foi recuperado. Depende de **11**.

### Fase 5 — Evidência

**13. CRIAR `11 Protocolo de Piloto e Concordância`** — depende de **7** e **9**.

**14. EXECUTAR o piloto** — único passo que produz informação nova; condição de entrada declarada pelo WP2 Cap. 16 para qualquer expansão de domínio. Resolve simultaneamente ONT §10.1 (limiares), §10.2 (`PROC-INC-02`), L3 (cobertura de erro) e dá o primeiro sinal empírico sobre GL-12b.

### Fase 6 — Expansão

**15. CRIAR `12 Ontologia Cognitiva Sapiens v1.6`** — depende de todo o anterior.

---

## 6. Observação final da auditoria

Três achados merecem destaque por serem do mesmo tipo, e esse tipo é o risco estrutural do projeto:

1. **L2** — Error Trace é declarado o ativo mais original do corpus e perdeu sua estrutura definidora (a ordem causal) em dois saltos sucessivos, sem que nenhum documento registrasse a perda.
2. **N5** — `PROC-ESTR-001` é citado pelo WP2 como aresta cross-domínio preservada e não existe na v1.4.
3. **L10** — a camada de decisão é declarada vazia por falta de evidência, e a evidência estava no capítulo 2 do documento anterior.

Em todos os três, **um documento declara preservar algo que o documento seguinte já havia removido**, e nada no processo detectou a divergência. É exatamente o mecanismo que a Constituição §1.1 identifica como o defeito original da v1.3 — redundância e perda silenciosas por ausência de detecção estrutural — operando agora um nível acima, entre documentos em vez de entre nós.

Daí a ordem da Seção 5: governança e rastreabilidade **antes** de qualquer correção de conteúdo. Não por formalismo. Porque sem elas, a v1.6 herda o mesmo mecanismo.

---

_Fim da auditoria. Nenhum arquivo canônico foi alterado nesta rodada._