10 Especificação do Error Trace v1.0.md

---

id: ETRACE-1.0 titulo: Especificação do Error Trace versao: 1.0 estado: ativo camada: C4 criado_em: 2026-08-17T17:46:24Z atualizado_em: 2026-08-17T17:46:24Z supersedes: [] superseded_by: null derivado_de: null governado_por: GOV-1.0 governed_by_conteudo:

- "White Paper Sapiens 2.0 (Axioma da Crença Calibrada; Error Trace como ativo protegido)"
- "Constituição da Ontologia Sapiens §3.5, §4.3, §4.4, §4.5"
- "Ontologia Cognitiva Sapiens v1.4.1" compativel_com: ontologia: ">=1.4.1, <2.0" geracao_de_ids: G3 proveniencia_principal: "EXT-WP1-1.0, itens L2 e L3 (White Paper 1.0 §2.5, §2.8, §2.9.1, §2.9.3 item 8)" changelog_ref: TX-2026-08-17T174624Z-etrace-v1.0 remissoes_pendentes: []

---

# Especificação do Error Trace — v1.0

## 0. Por que este documento existe

A Constituição §4.3 define a relação `Resposta Observada → Tipo de Erro` como pertencente ao nível de **instância**, produzida em tempo de execução, e remete sua especificação de schema a uma "Especificação Técnica". **Esse documento não existe no corpus canônico** — remissão pendente registrada como `G-CONF-04`. Consequência: o objeto de saída do motor diagnóstico não tem contrato em lugar nenhum. Nem o Schema Sapiens (que descreve o **item** anotado) nem o contrato de behavior (que descreve o **evento** de resposta) o cobrem.

Ao mesmo tempo, o White Paper 2.0 §15 declara o **Error Trace** o primeiro de seus ativos protegidos, _"identificado de forma independente, em múltiplas rodadas, como o elemento mais original de todo o corpus"_, com a instrução de que _"qualquer arquitetura futura derivada deste documento deve preservá-lo"_.

A auditoria integral verificou que a propriedade definidora do objeto — a **ordem causal** — havia sido perdida em dois saltos: a Constituição §4.3 o reduziu a conjunto ponderado (perdeu a ordem) e o Schema 2.1 a um erro único por alternativa (perdeu a multiplicidade). Este documento restaura a estrutura e fornece o contrato ausente.

Ele fecha `G-CONF-04` no que diz respeito ao Error Trace. A remissão da Constituição §3.4 a "Especificação Técnica" para outros fins permanece pendente.

## 0.1 Escopo e limites

**Este documento especifica** a estrutura do objeto Error Trace, seu vocabulário, suas restrições de integridade e as regras de anotação humana que o produzem.

**Este documento NÃO:**

1. cria, altera ou remove qualquer elemento do catálogo ontológico;
2. define o **mecanismo de produção** do traço (regras, classificadores, modelos) — isso é implementação;
3. resolve qualquer Grau de Liberdade do White Paper 2.0. Em particular, GL-14 (atribuição suave vs. dura de causa de erro) permanece **aberto**: esta especificação exige atribuição ponderada porque a Constituição §4.4 já a exige, não porque GL-14 tenha sido decidido;
4. introduz canal de evidência novo. A relação entre latência e crença permanece regida por GL-3, aberto.

---

## 1. O objeto

Um **Error Trace** é a explicação diagnóstica de **uma** resposta incorreta de **um** estudante a **um** item, expressa como uma **cadeia ordenada** de elos de erro.

```
ErrorTrace
├── trace_id
├── event_id            → evento de resposta (contrato de behavior)
├── item_id
├── item_hash
├── ontology_version    → obrigatório
├── etrace_version      → versão desta especificação
├── alternativa_escolhida
├── cadeia[]            → ORDENADA, 1..3 elos
│   └── Elo
│       ├── ordem              1 = primário (raiz), 2 = decorrente, 3 = decorrente
│       ├── erro               ID do catálogo (G3) ou sentinela declarada
│       ├── processo_afetado   ID de Processo do catálogo (G3)
│       ├── confianca          distribuição, nunca valor de verdade
│       ├── mecanismo          OPCIONAL e PROVISÓRIO — ver §4
│       └── evidencia          trechos/figuras que sustentam o elo
├── confianca_global
├── produtor            humano | modelo | regra
└── revisado_por_humano
```

### 1.1 A ordem é a propriedade definidora

O elo de `ordem: 1` é a **raiz** — a falha que, se não tivesse ocorrido, tornaria os elos seguintes improváveis. Os elos subsequentes são **decorrentes**: falhas que se explicam pela anterior.

A razão está registrada no White Paper 1.0 §2.8 e é operacional, não estética: _"a superfície de um erro frequentemente oculta sua causa real — um erro procedimental observado na resposta final pode ter sua raiz em um erro de interpretação anterior, e tratar apenas a manifestação de superfície na intervenção pedagógica seria ineficaz."_

**Consequência para a Intervenção Pedagógica.** A intervenção é selecionada a partir do elo de `ordem: 1`, nunca do último elo observado. Um traço cuja raiz é leitura deficiente e cuja manifestação é erro proporcional pede `INT-01`, não `INT-03`. Esta é a única regra deste documento que altera comportamento pedagógico, e ela decorre diretamente da estrutura que o ativo protegido descreve.

### 1.2 Um conjunto não é uma cadeia

Registrado para que a distinção não se perca outra vez: `{ERR-01, ERR-05}` e `[ERR-01 → ERR-05]` não são o mesmo objeto. O primeiro diz que dois erros são candidatos; o segundo diz qual causou qual. A Constituição §4.3 garante o primeiro. Esta especificação acrescenta o segundo, sem contrariá-la — a Constituição não proíbe a ordem, apenas não a exigia.

---

## 2. Campos

### 2.1 Cabeçalho do traço

|Campo|Obrigatório|Definição|
|---|---|---|
|`trace_id`|Sim|Identificador único e estável do traço|
|`event_id`|Sim|Evento de resposta que originou o traço. Chave para o contrato de behavior|
|`item_id`, `item_hash`|Sim|Item e hash do conteúdo canônico no momento da resposta|
|`ontology_version`|**Sim**|Versão da ontologia contra a qual os IDs foram resolvidos. GOV-1.0 §6.1 proíbe referência não versionada|
|`etrace_version`|Sim|Versão desta especificação|
|`alternativa_escolhida`|Sim|Alternativa incorreta que o traço explica|
|`confianca_global`|Sim|Confiança de que a cadeia, como um todo, explica a resposta|
|`produtor`|Sim|`humano` \| `modelo` \| `regra`|
|`revisado_por_humano`|Sim|Booleano. Ver §6|

Um traço explica **uma** alternativa. Um item com quatro distratores admite até quatro traços independentes; eles não se combinam em um objeto único.

### 2.2 Elo da cadeia

|Campo|Obrigatório|Definição|
|---|---|---|
|`ordem`|Sim|Inteiro 1..3, contíguo e sem repetição. `1` é a raiz|
|`erro`|Sim|ID de Tipo de Erro do catálogo (G3), ou uma das sentinelas do §3|
|`processo_afetado`|Sim|ID de Processo Cognitivo do catálogo (G3)|
|`confianca`|**Sim**|Confiança de que este elo, nesta posição, ocorreu. Escala declarada no §5|
|`mecanismo`|Não|Vocabulário provisório do §4|
|`evidencia.trechos[]`|Recomendado|Trechos literais do enunciado/alternativa que sustentam o elo|
|`evidencia.figuras[]`|Recomendado|IDs de recursos visuais que constituem evidência|
|`justificativa`|Sim para `ordem: 1`|1–2 frases, reproduzíveis por um segundo anotador sem acesso ao raciocínio do primeiro|

## 3. Restrições de integridade

**R-1 — Vínculo de catálogo.** Se `erro` é um ID de Tipo de Erro, o par (`erro`, `processo_afetado`) **precisa existir** no catálogo da `ontology_version` declarada. O catálogo é a fonte da possibilidade; o traço é a fonte da ocorrência. Um traço não pode inventar um vínculo Erro→Processo que a ontologia não autoriza (Constituição §4.3; Manual §7, regra 4).

**R-2 — Sentinelas.** Quando não há ID aplicável, `erro` assume exclusivamente um destes valores, e a razão é declarada:

|Sentinela|Quando|
|---|---|
|`erro-nao-catalogado-nesta-versao`|O `processo_afetado` não tem Tipo de Erro no catálogo. São 13 dos 25 processos na v1.4.1|
|`sem-mecanismo-cognitivo-identificavel`|A alternativa reflete descuido, erro de digitação ou leitura de gabarito, não falha cognitiva (Manual §7, regra 3)|

Sentinelas são valores de primeira classe, não ausência de dado. Um elo com sentinela é um elo válido e informativo: ele registra que houve falha e que o catálogo não a nomeia.

**R-3 — Proibição de determinismo.** `confianca` é obrigatória em **todo** elo. Um traço em que qualquer elo tenha confiança implícita, ausente, ou igual a 1 por convenção de preenchimento viola a Constituição §4.4 e o Axioma da Crença Calibrada. Confiança 1 só é admissível se for uma afirmação empírica sobre aquele elo — o que, para atribuição de causa de erro, praticamente nunca é o caso.

**R-4 — Profundidade máxima: 3 elos.** [DE, provisório]

Limite necessário porque o White Paper 1.0 deixava a cadeia aberta (`→ …`), o que a torna inanotável por humano e invalidável. O valor **3** é uma decisão de engenharia, escolhida por dois motivos declarados: acomoda o padrão que a literatura de origem descreve (interpretação → procedimento, com um terceiro elo de manifestação) e mantém a carga de anotação compatível com o limite de 2 processos com peso do Manual §4.

**O número é provisório e calibrável pelo piloto.** Se uma cadeia genuína exigir um quarto elo, o traço é registrado com os três de maior necessidade diagnóstica e o excedente vai para observação de campo — nunca comprimido em um elo existente.

**R-5 — Ordem contígua.** `ordem` começa em 1 e não salta. Um traço de dois elos usa 1 e 2, nunca 1 e 3.

**R-6 — Sem ciclo, sem repetição de posição.** Um mesmo par (`erro`, `processo_afetado`) não aparece duas vezes na mesma cadeia.

**R-7 — O traço não é aresta da ontologia.** Nenhum Error Trace altera o catálogo. Padrões observados em traços são **insumo** para revisão de ontologia sob GOV-1.0 §11.2, Classe B — nunca alteração automática.

**R-8 — Referência versionada.** Nenhum campo pode referir-se a "a ontologia vigente". Ver GOV-1.0 §6.1.

---

## 4. `mecanismo` — vocabulário provisório

### 4.1 O que é, e por que é opcional

O catálogo de Tipos de Erro da v1.4.1 responde **o que** falhou: `ERR-05` é "confusão de direção em relação proporcional". Ele não responde **por que**. E a escolha da intervenção depende do porquê: `INT-03` (prática guiada de relações proporcionais) é a resposta correta quando `ERR-05` decorre de concepção equivocada, e a resposta **errada** quando decorre de um automatismo mal formado — caso em que mais prática reforça o defeito.

O eixo do mecanismo é recuperado do White Paper 1.0 §2.5, com proveniência registrada em `EXT-WP1-1.0`, item L3. Ancoragem original: Reason (1990), sobre a distinção entre falha de execução e falha de planejamento; VanLehn (1990), sobre regras procedimentais sistemáticas porém incorretas; diSessa (1993) e Smith, diSessa & Roschelle (1994), sobre concepções alternativas como conhecimento prévio real mal aplicado.

### 4.2 Estatuto normativo — declarado sem ambiguidade

Sob GOV-1.0 §6.4 (regra de não-antecipação), um contrato C4 não pode conter campo cuja semântica não esteja definida em C1, C2 ou C3. A semântica do mecanismo psicológico **não está** definida em nenhum documento de camada superior. Portanto:

```
mecanismo:
  provisorio: true
  motivo: "eixo recuperado de EXT-WP1-1.0 L3; sem definição em C1/C2/C3"
  promocao_exige: "evidência de piloto (GOV-1.0 §11.2, Classe B)"
```

Consequências vinculantes:

1. O campo é **opcional**. Nenhuma anotação é inválida por omiti-lo.
2. Ele **não substitui** o `erro` do catálogo, e **não é** um Tipo de Erro. São eixos ortogonais: um traço tem os dois ou apenas o primeiro.
3. Ele **não é** nó da ontologia, não tem Intervenção indexada a si, e não entra em nenhuma relação do Capítulo 4 da Constituição.
4. Sua promoção a campo do catálogo ontológico exige piloto. Até então, vive apenas aqui.

### 4.3 Vocabulário

Prefixo `MEC-`, **novo e sem colisão** com qualquer geração de identificador do corpus. A escolha é obrigatória, não estilística: os treze mecanismos do White Paper 1.0 são numerados de `1` a `13` e formam conjunto **disjunto** dos treze `ERR-NN` da v1.4.1 — reutilizar a numeração original ou o prefixo `ERR-` recriaria a colisão `NS-1` documentada em `09 Mapa de Rastreabilidade de IDs`, §5.1 e §10.

|ID|Mecanismo|Ancoragem original|
|---|---|---|
|`MEC-01`|Conceitual — aplicação de concepção equivocada, porém sistemática e coerente, sobre um princípio|diSessa (1993)|
|`MEC-02`|Procedimental — execução incorreta e sistemática de um algoritmo, com o conceito subjacente possivelmente correto|VanLehn (1990)|
|`MEC-03`|Atencional — falha por desatenção momentânea, sem indicar déficit de conhecimento|Reason (1990), _slip_|
|`MEC-04`|De interpretação — compreensão incorreta do comando da questão, anterior ao processamento do conteúdo|—|
|`MEC-05`|De leitura — falha de decodificação ou compreensão linguística, distinta da de interpretação|Perfetti & Stafura (2014)|
|`MEC-06`|De cálculo — falha em operação aritmética isolada, com procedimento e conceito corretos|—|
|`MEC-07`|De estratégia — escolha de abordagem inadequada, mesmo com passos internos corretos|Newell & Simon (1972)|
|`MEC-08`|Metacognitivo — falha em monitorar, avaliar ou corrigir o próprio processo|Flavell (1979)|
|`MEC-09`|De memória — falha na recuperação de informação declarativa aprendida|Tulving (1985)|
|`MEC-10`|Por sobrecarga cognitiva — degradação por excesso de elementos simultâneos na memória de trabalho|Sweller (1988)|
|`MEC-11`|Por transferência inadequada — aplicação de princípio aprendido a situação estruturalmente distinta|Barnett & Ceci (2002)|
|`MEC-12`|Por viés cognitivo — desvio sistemático de julgamento sob incerteza|Kahneman & Tversky (1974)|
|`MEC-13`|Por automatização incorreta — execução rápida de procedimento automatizado de forma equivocada, resistente a feedback|Schneider & Shiffrin (1977); Logan (1988)|

**Etiquetas.** A ancoragem de cada linha é `[EC]` **herdada** do White Paper 1.0 — não verificada de novo neste documento. Sob GOV-1.0 §10.2, regra 4, uma afirmação `[EC]` cuja referência não seja recuperável é rebaixada a `[IT]`; as referências acima estão recuperáveis no White Paper 1.0, cujo aparato bibliográfico está preservado. A síntese em treze categorias é `[DE]`.

### 4.4 Ambiguidade reconhecida

As treze categorias **não são mutuamente exclusivas**, e o próprio White Paper 1.0 o declara. Nesta versão não há regra de prioridade entre elas.

Regra provisória de anotação: registre **no máximo um** `mecanismo` por elo, o de maior evidência; se dois parecerem igualmente sustentados, **omita o campo** e registre observação de campo. Forçar a escolha transferiria ambiguidade para dentro do dado e degradaria a concordância que o piloto precisa medir.

---

## 5. Escala de confiança

Bins categóricos, não um modelo probabilístico. Mesma disciplina do Manual §5: forma exigida agora, valor calibrado depois.

|Rótulo|Valor de registro|Significado|
|---|---|---|
|`alta`|0.7|A evidência do item sustenta este elo, nesta posição, contra as alternativas plausíveis|
|`media`|0.4|O elo é plausível; ao menos uma explicação concorrente não foi descartada|
|`baixa`|0.15|O elo é registrado por completude diagnóstica; a evidência é fraca|

**Os valores não somam 1 dentro de uma cadeia.** Os elos de um traço não são hipóteses concorrentes — são etapas de uma mesma explicação. Somá-los seria erro de tipo. A normalização, se algum consumidor a exigir, é responsabilidade daquele consumidor e não deste contrato.

[DE, provisório] Os três valores são calibráveis pelo piloto. A **forma** — bins declarados, obrigatórios, não determinísticos — não é.

---

## 6. Produção e validação

**Ordem de anotação.** O traço é produzido **depois** de o Processo dominante estar fixado, porque o catálogo de erro é indexado por processo (Manual §2, item 7). Nunca antes.

**Regra de governança de ingestão.** Recuperada de `EXT-WP1-1.0`, item L13b — a única regra do corpus original que protege a camada de crença de anotação não validada, e que não tinha equivalente em nenhum documento vigente:

> **Nenhum Error Trace com `produtor: modelo` ou `produtor: regra` pode alimentar a camada de crença sobre o estado de um estudante real sem que seu elo de `ordem: 1` tenha sido confirmado por ao menos um revisor humano.**

Reformulada em termos do que existe no corpus atual: o original falava de `MasteryEstimate`, entidade que não existe aqui, e de "papel nuclear", vocabulário reconciliado no §7 abaixo. O traço pode ser **armazenado** sem revisão; não pode **influenciar estado de estudante** sem ela. A distinção é o que permite ingestão em escala com enriquecimento posterior.

**Independência.** Traços produzidos para medição de concordância seguem o Manual §12, regra 5: o anotador não consulta o traço de outro anotador antes de finalizar o seu.

---

## 7. Vocabulário de papel — reconciliação

O corpus usava dois vocabulários para o papel de um processo em um item: `nuclear`/`secundario` (White Paper 1.0 §2.9.1 e §2.9.4; Schema Sapiens 2.1) e "Central"/"Secundário Necessário" (Manual §5).

**Decisão de reconciliação: prevalece `nuclear` | `secundario`.** Critério: é a forma presente nos dois contratos de máquina e na fonte original, contra uma única ocorrência em prosa operacional. A mudança é de rótulo, não de semântica — os limiares 0.7/0.3 do Manual §5 permanecem intactos.

Esta especificação e o Schema Sapiens adotam `nuclear` | `secundario`. O Manual alinha seus rótulos de prosa em sua próxima revisão. Registrado como item `D-1` do Manual.

---

## 8. O que este contrato não resolve

|Questão|Estado|
|---|---|
|GL-14 — atribuição suave vs. dura de causa de erro|**Aberto.** A exigência de ponderação aqui vem da Constituição §4.4, não de GL-14 resolvido|
|GL-3 — canais de evidência além de resposta a item|**Aberto.** Latência e sequência de interação não entram no traço nesta versão|
|Promoção de `MEC-*` a campo do catálogo|Exige piloto (GOV-1.0 §11.2, Classe B)|
|Regra de prioridade entre mecanismos|Não existe (§4.4)|
|Valores de confiança e profundidade máxima|Provisórios, calibráveis pelo piloto|
|Camada de decisão pedagógica|Fora de escopo. O traço informa a seleção de intervenção; não escolhe conteúdo seguinte. Ver `EXT-WP1-1.0`, item L10|

## 9. Changelog

|TX|Timestamp|Classe|Alteração|
|---|---|---|---|
|`TX-2026-08-17T174624Z-etrace-v1.0`|2026-08-17T17:46:24Z|— (criação)|Criação do documento em estado `ativo`. Recupera `EXT-WP1-1.0` L2 (cadeia ordenada), L3 (mecanismo psicológico, como campo provisório) e L13b (governança de ingestão). Fecha `G-CONF-04` quanto ao Error Trace. Reconcilia o vocabulário de papel (§7)|

_Fim do documento. Nenhum elemento do catálogo ontológico foi criado, alterado ou removido. Nenhum Grau de Liberdade foi fechado._