08 Registro de Extração do WP 1.0.md

---

## id: EXT-WP1-1.0 titulo: Registro de Extração do White Paper 1.0 versao: 1.0 estado: ativo camada: C5 criado_em: 2026-08-17T04:11:33Z atualizado_em: 2026-08-17T04:11:33Z supersedes: [] superseded_by: null derivado_de: null governado_por: GOV-1.0 documento_fonte: "00 WHITE PAPER 1.0 (ANTIGO).md" estado_do_documento_fonte: ativo — supersessão BLOQUEADA até aprovação deste registro (GOV-1.0 §8.2) origem_da_demanda: AUD-2026-08-17T03:42:31Z, Fase 1, passo 2 remissoes_pendentes: []

# Registro de Extração do White Paper 1.0

## 0. Função, escopo e limites

### 0.1 Por que este documento existe

O documento `00 WHITE PAPER 1.0 (ANTIGO).md` está destinado ao estado `superseded`. Sob GOV-1.0 §8.2, essa marcação é **proibida** enquanto não existir um Registro de Extração aprovado que enumere o conteúdo nele presente que não foi transportado para o White Paper 2.0.

A regra não é formalismo. A transição 1.0 → 2.0 já ocorreu **sem** registro de extração, e a auditoria documentou o resultado: quatorze elementos perdidos, **três deles declarados ativos protegidos pelo próprio documento sucessor**. Repetir a supersessão sem extração seria repetir, conscientemente, o mecanismo de perda que este trabalho existe para interromper.

### 0.2 O que este documento é

Um **registro de proveniência e preservação**. Ele:

- fixa o texto e a localização exata de cada elemento identificado como potencialmente perdido;
- determina o status de cada um no corpus atual;
- recomenda recuperar, não recuperar, ou recuperar sob condição;
- classifica a **natureza normativa** com que cada elemento pode voltar (norma, hipótese ou decisão de engenharia);
- declara as dependências de cada recuperação;
- e — o ponto mais importante — declara o **risco de reintrodução indevida** de cada um.

### 0.3 O que este documento explicitamente NÃO faz

1. **Não decide a ontologia final.** Nenhum Domínio, Competência, Processo, Habilidade, Tipo de Erro ou Intervenção é criado, alterado ou removido.
2. **Não altera nenhum documento canônico.**
3. **Não promove nada a norma.** Uma recomendação de recuperação aqui é insumo para uma transação futura, não a transação.
4. **Não resolve Graus de Liberdade** do White Paper 2.0.
5. **Não reintroduz conteúdo por nostalgia.** Vários elementos abaixo são recomendados **contra** a recuperação, ou a recuperação parcial, e as razões estão registradas.

### 0.4 Convenções

**Status no corpus atual** — um de:

|Status|Significado|
|---|---|
|`PRESERVADO`|Presente no corpus atual com mesmo conteúdo e mesma força|
|`MODIFICADO`|Presente com identidade reconhecível, conteúdo alterado|
|`REBAIXADO`|Deixou de ser norma; sobrevive como hipótese, proposta ou ativo declarado sem implementação|
|`REMOVIDO`|Ausente do corpus, sem registro de remoção|
|`CONTRADITO`|Um documento vigente afirma o oposto|

**Natureza de recuperação recomendada** — um de: `NORMA`, `DECISÃO DE ENGENHARIA [DE]`, `HIPÓTESE`, `REGISTRO APENAS`, `NÃO RECUPERAR`.

**Etiquetas [EC]/[IT]/[DE]** são transportadas do original conforme GOV-1.0 §10.2, regra 1. Onde o WP 1.0 não etiquetou explicitamente, marca-se `[?]` e registra-se pendência, conforme GOV-1.0 §10.2, regra 6 — nunca se atribui etiqueta por inferência.

---

## L1 — Indicador Comportamental (Nível 5)

**Definição original.** Quinto nível da hierarquia: _"o traço extraível diretamente do comportamento de resposta do aluno — tempo de resposta, padrão de erro específico, escolha de distrator, rascunho, sequência de cliques. Este é o nível que efetivamente alimenta os algoritmos de estimativa de domínio."_ Formalizado como entidade `BehavioralIndicator` com `observable_skill_id`, `tipo` (enum: tempo_resposta, padrao_erro, escolha_distrator, sequencia_interacao) e `valor_observado`.

**Localização exata no WP1.** §2.1.3 (definição operacional e posição na hierarquia); §2.1.2 (justificativa — a lacuna "(c) unidade observável, extraível automaticamente do comportamento" que nenhuma taxonomia precedente cobria); §2.9.1 (entidade `BehavioralIndicator`); §2.10 (síntese).

**Etiqueta original.** [DE] — a hierarquia de cinco níveis é declarada em §2.1.3 como Decisão de Engenharia Sapiens.

**Status no corpus atual.** `REMOVIDO`. A Constituição Cap. 3 define seis tipos de nó e nenhum é o Indicador Comportamental; Cap. 4 §4.2 lista dois objetos externos (Item/Questão e Resposta Observada), também não equivalentes. O contrato `07 behavior student` coleta `tempo_resposta_segundos`, `numero_tentativas` e `mudou_resposta` — dados que hoje **não têm nó ontológico que os interprete**.

**Deve ser recuperado?** **Sim, sob forma alterada.**

**Natureza recomendada.** `DECISÃO DE ENGENHARIA [DE]` — como **camada transversal**, jamais como sexto nível.

A distinção é essencial. A Constituição §4.2 fecha o conjunto em seis tipos de nó formais; acrescentar um sétimo é Emenda Substantiva de Classe IV e exigiria evidência que não existe. Mas a Constituição §2.1 já admite dimensões transversais que não são níveis (é exatamente assim que trata "Conhecimento"), e o Indicador Comportamental cabe nessa figura sem tocar o fechamento do Cap. 4.

**Dependências.** Constituição (decisão sobre camada transversal, etapa 12) → contrato de behavior (etapa 10). A Especificação do Error Trace (etapa 8) depende parcialmente de L1, porque `escolha_distrator` e `padrao_erro` são simultaneamente indicadores comportamentais e insumos do traço de erro.

**Riscos de reintrodução indevida.**

1. **Reabrir a hierarquia de cinco níveis.** O corpus atual abandonou deliberadamente a hierarquia por níveis em favor de tipos de nó com relações tipadas. Reintroduzir o Nível 5 como nível reintroduziria a leitura hierárquica que a Constituição §2.1 rejeita explicitamente ("as cinco categorias não se distinguem por nível de generalidade, mas por função dentro do sistema").
2. **Ligar Indicador a Habilidade Observável, como no original.** No WP1, `BehavioralIndicator` referencia `observable_skill_id`. Na arquitetura atual, a unidade rastreável pelo motor de crença é o **Processo**, não a Habilidade (Constituição §3.3). Transportar a chave estrangeira original criaria um vínculo que a Constituição não autoriza.
3. **Tratar latência como evidência de crença sem resolver GL-3.** O White Paper 2.0 §2.2 mantém aberto o grau de liberdade sobre canais de evidência além de resposta a item, com latência em posição secundária. Recuperar L1 **não** resolve GL-3; a recuperação deve declarar explicitamente que o indicador é **coletado e registrado**, não que **atualiza crença**.

---

## L2 — Error Trace como cadeia causal ordenada

**Definição original.** _"Um erro observado em uma resposta não é modelado como uma etiqueta única, mas como uma sequência ordenada de nós de erro, cada um associado a um Processo Cognitivo do grafo"_:

```
RESPOSTA_INCORRETA
   → nó_de_erro_primario:   {tipo, processo_cognitivo_afetado, confiança}
   → nó_de_erro_secundario: {tipo, processo_cognitivo_afetado, confiança}
   → ...
```

Justificativa registrada: _"a superfície de um erro frequentemente oculta sua causa real: um erro procedimental observado na resposta final pode ter sua raiz em um erro de interpretação anterior, e tratar apenas a manifestação de superfície na intervenção pedagógica seria ineficaz."_

**Localização exata no WP1.** §2.5.2 (antecipação: _"o Sapiens modela o diagnóstico de erro como uma cadeia causal de erro, não como uma etiqueta única"_, marcado [DE]); §2.8 (definição completa, com o esquema acima; justificativa marcada [IT], ancorada em Reason 1990 e VanLehn 1990); §2.9.1 (entidade `ErrorTrace`, com `response_id` e `sequencia` como JSON **ordenado**); §2.9.3 item 8 (Analisador de Cadeia de Erro); §2.9.5 (exibição ao aluno: _"Você aplicou corretamente o procedimento, mas a interpretação inicial do enunciado levou a um valor errado"_); §2.9.7 (consumo pelo recomendador).

**Etiqueta original.** [DE] para o modelo; [IT] para a justificativa.

**Status no corpus atual.** `MODIFICADO`, com perda da propriedade definidora — e simultaneamente `CONTRADITO` em sentido forte, porque o White Paper 2.0 §15 declara o Error Trace **ativo protegido**, afirmando que _"qualquer arquitetura futura derivada deste documento deve preservá-lo"_, enquanto a implementação vigente não o preserva.

Degradação em dois saltos documentados:

- **Salto 1** — Constituição §4.3: `Resposta Observada → Tipo de Erro` é definida como N:M obrigatoriamente ponderada. Isso preserva a **multiplicidade** e elimina a **ordem**. Um conjunto ponderado não é uma cadeia: não há primário e secundário, não há "a raiz de".
- **Salto 2** — Schema Sapiens 2.1, bloco `distratores[]`: o campo `erro` é **um** identificador por alternativa. Elimina também a multiplicidade, violando diretamente a Constituição §4.4 (proibição de cardinalidade determinística de valor único onde mais de um candidato é plausível).

Agravante estrutural: **não existe schema do objeto Error Trace em nenhum documento do corpus.** A Constituição §4.3 remete sua especificação a uma "Especificação Técnica" que não está em `pipeline/docs/` — remissão pendente sob GOV-1.0 §1.4, registrada como G-CONF-04.

**Deve ser recuperado?** **Sim. É a recuperação de maior prioridade de todo este registro.**

**Natureza recomendada.** `NORMA` quanto à **existência e à estrutura** do objeto (a cadeia ordenada com confiança por elo); `DECISÃO DE ENGENHARIA [DE]` quanto ao **mecanismo de produção** (regras, classificadores, IA).

Justificativa da divisão: a Constituição já obriga que a relação seja ponderada e não determinística — isso é norma vigente. O que falta é a **ordem**, que é o conteúdo específico do WP1 e que nenhum documento vigente proíbe. Recuperar a ordem não contraria nada; omiti-la é que contraria o ativo protegido.

**Dependências.** Este documento (registro) → Mapa de Rastreabilidade de IDs (porque a cadeia referencia tipos de erro, cuja numeração colide entre gerações) → **Especificação do Error Trace**, etapa 8 → Schema 2.2, etapa 9. A ordem importa: o campo `distratores[].erros[]` do Schema só é especificável depois que o objeto existir.

**Riscos de reintrodução indevida.**

1. **Confundir cadeia de erro com aresta estática da ontologia.** A Constituição §4.3 é explícita: `Resposta → Erro` é produzida em tempo de execução, não é aresta do catálogo. A cadeia recuperada pertence à camada de instância. Colocá-la na ontologia reintroduziria a confusão catálogo/instância que a Constituição separou com cuidado.
2. **Reintroduzir a taxonomia de erro do WP1 junto com a estrutura.** A cadeia e o vocabulário de tipos são coisas separadas. A estrutura ordenada pode ser recuperada usando os treze `ERR-XX` da v1.4; recuperá-la junto com os treze tipos numéricos do WP1 produziria a colisão de namespace documentada como NS-1 no Mapa de Rastreabilidade. **Separar L2 de L3 é obrigatório.**
3. **Determinismo na ordem.** A cadeia é ordenada, mas cada elo continua sendo uma distribuição, não uma atribuição. Uma cadeia ordenada de rótulos únicos violaria o Axioma da Crença Calibrada tanto quanto o campo único atual.
4. **Profundidade ilimitada.** O WP1 deixa a cadeia aberta (`→ ...`). Sem limite declarado, o objeto é impossível de anotar por humano e de validar. O limite é decisão de engenharia a tomar na etapa 8, e deve ser declarado — não herdado por omissão.

---

## L3 — Taxonomia de erro por mecanismo psicológico

**Definição original.** Treze categorias sintetizadas de Reason (1990), VanLehn (1990) e diSessa (1993):

1. conceitual · 2. procedimental · 3. atencional · 4. de interpretação · 5. de leitura · 6. de cálculo · 7. de estratégia · 8. metacognitivo · 9. de memória · 10. por sobrecarga cognitiva · 11. por transferência inadequada · 12. por viés cognitivo · 13. por automatização incorreta.

Declaração explícita de não-exclusividade: _"estas treze categorias não são mutuamente exclusivas em um evento de erro único"_ — o que é precisamente o que motiva L2.

**Localização exata no WP1.** §2.5.1 (fundamento teórico: Reason — slips/lapses vs. mistakes; VanLehn — buggy algorithms; diSessa/Smith-diSessa-Roschelle — misconceptions como conhecimento prévio real mal aplicado; tudo marcado [EC]); §2.5.2 (as treze categorias, marcadas [DE] quanto à síntese); §2.9.1 (entidade `ErrorType` — _"13 registros fixos"_).

**Etiqueta original.** [EC] para os fundamentos; [DE] para a síntese em treze categorias.

**Status no corpus atual.** `REMOVIDO`, e substituído por um conjunto **disjunto de mesma cardinalidade e numeração colidente**.

Os treze `ERR-XX` da Ontologia v1.4 respondem a uma pergunta diferente. Comparação mínima:

|Eixo|WP 1.0|Ontologia v1.4|
|---|---|---|
|Pergunta que responde|**por que** falhou (mecanismo psicológico)|**o que** falhou (operação cognitiva)|
|Ancoragem|Reason, VanLehn, diSessa|Processo Cognitivo do catálogo|
|Exemplo|"erro por automatização incorreta"|"ERR-05 — confusão de direção em relação proporcional"|

**Deve ser recuperado?** **Sim, como dimensão adicional — nunca como substituto.**

O argumento operacional é o mais forte deste registro inteiro: sem o eixo do mecanismo, **a Intervenção não sabe o que remediar**. `INT-03` ("prática guiada de relações proporcionais") é a resposta correta quando `ERR-05` decorre de erro conceitual, e a resposta errada quando decorre de automatização incorreta — caso em que mais prática reforça o automatismo defeituoso. As onze intervenções da v1.4 são todas ambíguas nesse eixo, e a ambiguidade não é visível no catálogo atual.

**Natureza recomendada.** `DECISÃO DE ENGENHARIA [DE]`, como **atributo do Tipo de Erro** (`mecanismo_psicologico`, vocabulário fechado), **não** como entidade nova, **não** como segunda taxonomia paralela, **não** como novo tipo de nó.

**Dependências.** Mapa de Rastreabilidade de IDs (obrigatório — resolve NS-1) → Especificação do Error Trace, etapa 8 → e, para virar campo de catálogo, uma emenda de Classe IV à Ontologia, condicionada ao piloto (GOV-1.0 §11.2, Classe B). **Não é recuperável antes do piloto** na forma de campo de catálogo; é recuperável imediatamente na forma de registro e de vocabulário da Especificação do Error Trace.

**Riscos de reintrodução indevida.**

1. **Colisão de namespace.** Os identificadores originais são inteiros de 1 a 13. Os da v1.4 são `ERR-01`…`ERR-13`. Reintroduzir os inteiros criaria dois conjuntos disjuntos indexados pelo mesmo intervalo. **Qualquer recuperação deve usar um prefixo distinto e novo** — a escolha do prefixo é decisão da etapa 8, mas a proibição de reutilizar `1..13` ou `ERR-XX` é registrada aqui.
2. **Ser lido como substituição da taxonomia da v1.4.** Os dois eixos são ortogonais. Um documento que apresente as treze categorias psicológicas sem declarar explicitamente que elas **não** substituem os treze `ERR-XX` será lido como substituição.
3. **Sobreposição interna não resolvida.** As treze categorias do WP1 não são mutuamente exclusivas e o próprio WP1 admite isso. Importá-las como vocabulário fechado sem regra de prioridade transferiria a ambiguidade para a anotação, degradando a concordância que o piloto precisa medir.
4. **Reintroduzir "erro de leitura" como categoria.** O item 5 do WP1 é decodificação linguística; `ERR-01` da v1.4 é falha em localizar dado explícito. São nominalmente próximos e conceitualmente distintos — armadilha nominal registrada no Mapa de Rastreabilidade.

---

## L4 — Falsa proficiência com critério operacional

**Definição original.** Campo obrigatório da ficha de cada nó: `criterio_de_deteccao_de_falsa_proficiencia`, definido como _"acerto consistente em itens de superfície repetida, falha em variação estrutural"_, com algoritmo correspondente: comparar a acurácia do aluno em itens que compartilham o mesmo processo mas variam o domínio de superfície; queda de acurácia sob variação de superfície é o sinal.

Instâncias concretas preservadas no original:

- `RQ-PROP-003`: _"acerto sistemático apenas quando a proporcionalidade é anunciada explicitamente ('regra de três'), falha quando embutida em contexto de física/química."_
- `LEIT-INF-002`: _"acerto em textos curtos e familiares, falha sistemática em textos longos ou de domínio de conhecimento prévio baixo."_
- `HIST-CAUSAL-002`: _"acerto restrito a processos históricos memorizados explicitamente em sala, falha ao aplicar a distinção a processo histórico não estudado."_
- `ARGUM-CONSTR-003`: _"uso de repertório sociocultural sofisticado sem articulação causal genuína entre os elementos citados."_

**Localização exata no WP1.** §2.6 (campo do template, bloco `estimacao_de_dominio`); §2.7.1, §2.7.2, §2.7.3, §2.7.4 (as quatro instâncias acima); §2.9.3 item 3 (Detector de Falsa Proficiência); §1.8 Princípio 8 (fundamento — Chi et al. 1981, superfície vs. princípio).

**Etiqueta original.** [EC] para o fundamento (Chi et al., 1981); [DE] para os critérios operacionais.

**Status no corpus atual.** `REBAIXADO` — e é o caso mais nítido de ativo protegido sem implementação. O White Paper 2.0 §15 preserva "falsa proficiência" na lista de ativos protegidos, como _"acerto sem domínio real do processo subjacente, tratado como categoria de primeira classe, não como ruído estatístico"_. Nenhum documento canônico diz como detectá-la.

**Deve ser recuperado?** **Sim.** É recuperação de custo baixíssimo e valor alto: o mecanismo é uma comparação de acurácia entre itens que já compartilham `processo` e diferem em `fonte.disciplina` — dois campos que o Schema 2.1 **já possui**.

**Natureza recomendada.** `DECISÃO DE ENGENHARIA [DE]` para o critério geral (invariância sob variação de superfície); `REGISTRO APENAS` para as quatro instâncias específicas, porque os nós a que se referem não têm equivalência estabelecida na v1.4 (ver Mapa de Rastreabilidade).

**Dependências.** Nenhuma bloqueante para o registro. Para virar campo de catálogo: emenda de Classe III à Ontologia (campo opcional por nó), portanto GOV-1.0 §11.2 Classe B. Para virar detector: depende de L1 (indicadores) e do Schema.

**Riscos de reintrodução indevida.**

1. **Transformar o critério em regra de anotação.** Falsa proficiência é propriedade do **estado do aluno**, inferida ao longo de múltiplos itens. Não é anotável em um item. Introduzi-la no Manual seria erro de camada.
2. **Reintroduzir as quatro instâncias como se fossem da v1.4.** Elas se referem a `RQ-PROP-003`, `LEIT-INF-002`, `HIST-CAUSAL-002` e `ARGUM-CONSTR-003` — identificadores sem equivalência estabelecida no catálogo vigente. Transportá-los criaria referências pendentes.
3. **Confundir com o detector de chute.** São dois algoritmos distintos no original (§2.9.3, itens 2 e 3) com assinaturas diferentes. Fundi-los produziria falsos positivos em ambos.

---

## L5 — Grau de transferência por processo

**Definição original.** Campo `grau_transferencia` registrado em **todos** os nós do Capítulo 4, com valores `alto`, `medio_alto`, `medio`, `medio_baixo`, `baixo_medio` e justificativa ancorada em literatura. Complementado no template por `nivel_de_transferencia_tipico: [proximal | distal]` (Barnett & Ceci, 2002).

Exemplos com a justificativa preservada:

- `PROC-INC-004` — `baixo_medio`: _"a própria literatura de Kahneman e Tversky é a evidência mais direta de que este processo transfere mal espontaneamente (o viés persiste mesmo em especialistas treinados) — alta relevância cognitiva, mas baixa transferência natural, exigindo intervenção pedagógica explícita e repetida em vez de mera exposição."_
- `PROC-SIST-002` — `medio_baixo`: uma das competências de raciocínio científico mais tardias e mais dependentes de instrução explícita.
- `PROC-EXP-001` — `alto`: Chen & Klahr (1999) documentam transferência robusta entre domínios quando ensinada explicitamente como estratégia geral.

**Localização exata no WP1.** §2.6 (campo `nivel_de_transferencia_tipico`, bloco `desenvolvimento`); Capítulo 4, em todos os blocos de processo (`grau_transferencia`); §3.5.4 (os cinco nós de maior poder de transferência).

**Etiqueta original.** Mista: [EC] onde a literatura mede transferência diretamente (Chen & Klahr; De Bock et al.); [IT] onde é extrapolação.

**Status no corpus atual.** `REMOVIDO`, e em contradição direta com documento vigente. O White Paper 2.0 §15 lista o **campo de grau de transferência** como ativo protegido — o único da lista com ressalva anexada: _"a ideia de registrar transferência como propriedade explícita é preservada; sua formalização como categoria otimista fixa (alto/médio/baixo) permanece sob revisão, matéria de GL-10."_ A Ontologia v1.4 não possui o campo em forma alguma.

**Deve ser recuperado?** **Sim — mas o WP 2.0 já determinou a forma da recuperação, e ela não é a forma original.**

**Natureza recomendada.** `HIPÓTESE`, registrada por nó, com incerteza explícita e **sem escala fixa** enquanto GL-10 estiver aberto.

Leitura conjunta das duas fontes: o WP1 fornece o conteúdo (quais processos transferem melhor e por quê); o WP2 fornece a restrição de forma (a escala tripartite fixa é o que está sob revisão, não a ideia). Recuperar o conteúdo respeitando a restrição significa registrar a transferência como **hipótese com justificativa**, não como valor categórico.

**Dependências.** GL-10 (natureza da dependência entre fatores) é o primeiro item do Programa de Pesquisa do WP2. A recuperação como campo de catálogo depende dele. A recuperação como registro anotado neste documento não depende de nada.

**Riscos de reintrodução indevida.**

1. **Reintroduzir a escala fixa alto/médio/baixo.** É exatamente a formalização que o WP2 §15 colocou sob revisão. Reintroduzi-la fecharia, por via lateral, uma questão que o documento de camada C1 mantém aberta — violação de GOV-1.0 §1.3.
2. **Tratar grau de transferência como propriedade validada.** A Constituição §2.3 é explícita: transferibilidade é **critério de candidatura**, não validação; o processo entra como hipótese testável. Um campo `grau_transferencia` preenchido por curadoria seria lido como medida.
3. **Herdar os valores do WP1 sem herdar as justificativas.** O valor isolado é uma opinião; o valor com a justificativa é um registro auditável. Transportar apenas o rótulo destrói exatamente a disciplina [EC]/[IT]/[DE].

---

## L6 — `frequentemente_confundidas_com` e `frequentemente_mascaradas_por`

**Definição original.** Dois campos do bloco `relacoes_no_grafo` da ficha canônica:

- `frequentemente_confundidas_com` — _"falsos positivos de anotação"_: nós que anotadores tendem a trocar entre si.
- `frequentemente_mascaradas_por` — _"competência real escondida atrás de outra aparente"_.

Instâncias preservadas: `RQ-PROP-003` frequentemente confundida com `RQ-NAOPROP-004`, e frequentemente mascarada por `FIS-MRU-001` e `QUIM-CONC-001` (_"aparece 'disfarçada' de física ou química"_); `LEIT-INF-002` confundida com `LEIT-LOC-001` (_"localização literal, erroneamente tratada como inferência por alguns bancos de itens"_) e mascarada por `MAT-PROB-VERBAL-001` (_"erro de interpretação em matemática é, na raiz, erro desta competência"_); `HIST-CAUSAL-002` confundida com `HIST-CRONOLOGIA-001`; `ARGUM-CONSTR-003` confundida com `REDACAO-ENUMERACAO-001`.

Ambos são também valores do enum `tipo_relacao` da entidade `GraphEdge`.

**Localização exata no WP1.** §2.6 (template, bloco `relacoes_no_grafo`); §2.7.1–§2.7.4 (as instâncias); §2.9.1 (entidade `GraphEdge`, enum `tipo_relacao`: pre_requisito, dependente, associada_frequente, **confundida_com**, **mascarada_por**).

**Etiqueta original.** [DE].

**Status no corpus atual.** `REMOVIDO`. A relação `Processo ↔ Processo` da Constituição §4.3 existe e é obrigatoriamente tipada quando presente, mas _"a escolha da taxonomia de tipos permanece questão aberta, remetida ao Capítulo 12"_ — capítulo ausente (G-CONF-05). A Ontologia v1.4 §8 declara a relação **não populada**.

**Deve ser recuperado?** **Sim, e com prioridade prática alta** — porque resolve dois problemas registrados por outra via.

Primeiro: `frequentemente_confundidas_com` é o registro estruturado das fronteiras que a Ontologia v1.4 §10 deixou em aberto e que o Manual §11 teve de resolver por regra de desempate ad hoc — precisamente a inversão de hierarquia normativa registrada como G-CONF-06. Com o campo, a fronteira volta a ser propriedade do catálogo.

Segundo: `frequentemente_mascaradas_por` é a operacionalização do ativo protegido **inversão disciplinar** (WP2 §15 — _"disciplina tratada como metadado de manifestação, não como estrutura organizadora primária"_). É o único mecanismo do corpus que registra que a competência real pode estar escondida atrás da aparente.

**Natureza recomendada.** `DECISÃO DE ENGENHARIA [DE]`, como **dois tipos de aresta** dentro da taxonomia `Processo ↔ Processo` que a Constituição já prevê e deixou por definir.

**Dependências.** Constituição Cap. 12 (taxonomia de aresta), etapa 12 → Ontologia (população das arestas), condicionada ao piloto. **Recuperação parcial imediata possível:** as confusões já conhecidas e documentadas (`PROC-CLASSIF-01` × `PROC-ESPACO-03`; `DOM-CAUSAL` × `DOM-EXPERIMENTAL`) podem ser registradas como observação de campo sem emenda alguma.

**Riscos de reintrodução indevida.**

1. **Popular a relação `Processo ↔ Processo` inteira.** A Constituição §4.3 fixa uma restrição inegociável: quando essa relação existir, deve ser **tipada e ponderada**, nunca uma aresta única indiferenciada tratada implicitamente como pré-requisito. Recuperar dois tipos de aresta não autoriza popular os demais — e em particular **não autoriza popular `pre_requisito`**, que é a aresta cuja taxonomia o WP2 mantém em aberto.
2. **Transportar as instâncias com os IDs originais.** Todos os nós citados (`RQ-NAOPROP-004`, `FIS-MRU-001`, `LEIT-LOC-001`, `MAT-PROB-VERBAL-001`, `HIST-CRONOLOGIA-001`, `REDACAO-ENUMERACAO-001`) são **referências pendentes já no próprio WP1** — nunca foram definidos em lugar algum. Ver Mapa de Rastreabilidade, D2–D5.
3. **Confundir "confundidas_com" com sobreposição real.** O campo registra um fato sobre **anotadores**, não sobre a cognição. Lê-lo como evidência de que dois nós são o mesmo acionaria indevidamente o critério de fusão da Constituição §2.4.

---

## L7 — `sinais_de_identificacao_automatica`

**Definição original.** Bloco da ficha canônica com cinco listas: `palavras_chave_tipicas`, `estruturas_linguisticas_tipicas`, `operacoes_matematicas_tipicas`, `elementos_visuais_tipicos`, `comandos_tipicos_do_enunciado`.

Dupla função declarada: (a) insumo do pipeline de anotação por IA — _"lista candidata de `cognitive_mappings`, com base em similaridade textual/estrutural a itens já anotados"_; (b) **mecanismo antiduplicação** — Regra de Modelagem 3: _"antes de criar um novo `CognitiveProcess`, o curador deve verificar, via busca semântica sobre `sinais_identificacao_automatica`, se o processo já existe sob outro rótulo disciplinar."_

**Localização exata no WP1.** §2.6 (template); §2.7.1–§2.7.4 (instâncias); §2.9.1 (entidade `ObservableSkill`, campo `sinais_identificacao`); §2.9.3 itens 7 e 8; §3.3.2 (Via A do pipeline); §3.6 regra 3.

**Etiqueta original.** [DE].

**Status no corpus atual.** `REMOVIDO`.

**Deve ser recuperado?** **Sim, para a função (b); condicionalmente para a função (a).**

A função antiduplicação é imediatamente valiosa e não tem substituto: é o único mecanismo do corpus que impede a recriação de um processo já existente sob outro rótulo disciplinar — que é o achado de redundância mais direto da auditoria da v1.3 e o risco central da expansão para novas áreas.

**Natureza recomendada.** `DECISÃO DE ENGENHARIA [DE]`, com **cláusula de uso obrigatória e explícita**:

> Sinais de identificação são instrumento de **triagem de candidatos e de busca antiduplicação**. Nunca são critério de decisão de classificação.

**Dependências.** Nenhuma bloqueante para uso como ferramenta de curadoria. Para virar campo de catálogo: emenda de Classe III, portanto GOV-1.0 §11.2 Classe B.

**Riscos de reintrodução indevida.**

1. **Risco principal, e é grave: colisão direta com o Manual §8.** O Manual proíbe explicitamente atribuir processo por presença de palavra-chave: _"a palavra 'proporção' no texto não implica `PROC-QUANT-02` se a resposta correta não depender, de fato, de raciocínio proporcional."_ Não há contradição real — o WP1 define os sinais como triagem, não como decisão — mas **a distinção não está no campo, está apenas no uso**. Recuperar o campo sem a cláusula do parágrafo acima reintroduziria exatamente o vício que o Manual combate. A cláusula é condição de recuperação, não recomendação.
2. **Contaminação do piloto.** Se sinais forem visíveis ao anotador humano durante a anotação dupla cega, a concordância medida deixa de refletir a clareza do catálogo e passa a refletir a clareza dos sinais. Devem ser ocultados dos anotadores durante o piloto.
3. **Sinais como definição.** Um nó cuja identidade dependa de suas palavras-chave é conteúdo disfarçado de processo — violação da Constituição §3.3.

---

## L8 — Contraexemplos por nó

**Definição original.** Campo `contraexemplos` da ficha canônica: _"descrição de item que parece exigir a competência mas não exige (distrator estrutural)."_

Instâncias: para `RQ-PROP-003`, juros compostos — _"relação não linear, frequentemente confundida com proporcionalidade direta por alunos com automatização incorreta de 'regra de três'"_; para `LEIT-INF-002`, _"pergunta que pede repetição literal de uma frase do texto (não é inferência, é localização)"_; para `HIST-CAUSAL-002`, _"pergunta que exige apenas memorização de datas"_; para `ARGUM-CONSTR-003`, _"redação que apenas enumera 'causa 1, causa 2, causa 3' sem articular relação entre elas."_

**Localização exata no WP1.** §2.6 (template, bloco `exemplos`/`contraexemplos`); §2.7.1–§2.7.4 (instâncias).

**Etiqueta original.** [DE].

**Status no corpus atual.** `MODIFICADO` e enfraquecido. A Ontologia v1.4 mantém, para cada processo, um bloco "o que não é" em prosa — que define **fronteira conceitual**. O contraexemplo é outra coisa: um **caso concreto** que cruza a fronteira de forma enganosa.

**Deve ser recuperado?** **Sim.** É o insumo de maior impacto direto sobre o kappa da anotação dupla que o White Paper 2.0 Cap. 16 exige como condição de entrada — e portanto sobre a viabilidade de toda a etapa 14 da árvore de dependências.

**Natureza recomendada.** `DECISÃO DE ENGENHARIA [DE]`, como material do Manual de Anotação, **não** como campo do catálogo ontológico.

Justificativa da alocação: contraexemplos servem ao anotador, e o Manual já possui uma seção de exemplos positivos e negativos (§9) que é exatamente o lugar deles. Colocá-los no catálogo carregaria a ontologia com material didático.

**Dependências.** Manual v1.1 (etapa 7) para os contraexemplos já dedutíveis do corpus atual; piloto (etapa 14) para os que só emergem de discordância real entre anotadores.

**Riscos de reintrodução indevida.**

1. **Contraexemplo como regra de exclusão.** O contraexemplo ilustra; não normatiza. Se for lido como regra, cria exclusões que a definição do processo não sustenta.
2. **Transportar os contraexemplos originais junto com seus nós.** Os quatro exemplares do WP1 referem-se a nós sem equivalência estabelecida na v1.4. Os **casos** (juros compostos; localização literal disfarçada de inferência; memorização de datas; enumeração desarticulada) são reaproveitáveis; os **vínculos a IDs** não são.
3. **Contaminar o piloto**, pelo mesmo mecanismo do L7 risco 2, se forem usados como treinamento imediatamente antes da medição de concordância.

---

## L9 — Vetores de tipo de conhecimento, raciocínio e processamento

**Definição original.** Três taxonomias transversais, registradas como **vetores de peso** por processo, não como categorias exclusivas:

- **Conhecimento (6):** declarativo, procedimental, condicional, conceitual, metacognitivo, estratégico. (§2.2)
- **Raciocínio (13):** dedutivo, indutivo, abdutivo, analógico, probabilístico, causal, espacial, temporal, hipotético-dedutivo, sistêmico, quantitativo, verbal-linguístico, visual. (§2.3)
- **Processamento (12):** reconhecimento, recordação, aplicação, inferência, integração, modelagem, planejamento, monitoramento, avaliação, generalização, transferência, automatização. (§2.4)

Justificativa da forma vetorial: _"esta tabela não é uma partição mutuamente exclusiva no sentido lógico estrito — um mesmo Processo Cognitivo tipicamente envolve mais de um tipo simultaneamente. Por isso, a ficha registra um vetor de pesos sobre os seis tipos, não uma categoria única."_

**Localização exata no WP1.** §2.2, §2.3, §2.4 (as três tabelas, com base científica por linha); §2.6 (bloco `demandas_cognitivas`); §2.7.1–§2.7.4 (vetores preenchidos); §2.9.1 (entidade `CognitiveProcess`, campos `vetor_conhecimento`, `vetor_raciocinio`, `vetor_processamento`).

**Etiqueta original.** [DE] para as taxonomias; [EC] por linha, com citação individual.

**Status no corpus atual.** **Divergente entre as três.**

- **Conhecimento:** `REBAIXADO`. A Constituição §2.1 preserva a ideia — _"Conhecimento não é um nível hierárquico, é uma dimensão transversal que classifica como algo é sabido (declarativo, procedimental, condicional, estratégico/metacognitivo), aplicável a qualquer nó de qualquer nível"_ — e nomeia cinco dos seis tipos. Nenhum documento operacional a implementa. **É a única dimensão transversal declarada na Constituição e nunca instanciada.**
- **Raciocínio:** `REMOVIDO`.
- **Processamento:** `REMOVIDO`.

**Deve ser recuperado?** **Parcialmente. Recomendação diferenciada:**

|Vetor|Recomendação|Razão|
|---|---|---|
|**Conhecimento (6)**|**Recuperar**|A Constituição já o promete nominalmente. Não implementá-lo deixa uma dimensão declarada sem conteúdo — e a Constituição §2.1 identifica a confusão entre "o que se sabe" e "onde isso se organiza" como um dos mecanismos pelos quais a v1.3 perdeu coerência|
|**Raciocínio (13)**|**Não recuperar agora** — `REGISTRO APENAS`|Treze dimensões com peso por nó, sobre 25 nós, sem dado empírico algum, é cristalização prematura. Sobrepõe-se parcialmente aos próprios Domínios da v1.4 (`causal`, `espacial`, `quantitativo`, `sistêmico`, `probabilístico` são simultaneamente tipos de raciocínio e domínios), o que criaria redundância entre eixos|
|**Processamento (12)**|**Não recuperar agora** — `REGISTRO APENAS`|Mesma razão, com sobreposição adicional a `Habilidade Observável` (`aplicação`, `inferência`, `integração`, `modelagem` são operações que a v1.4 já expressa como processos)|

**Natureza recomendada.** Conhecimento: `DECISÃO DE ENGENHARIA [DE]`, como dimensão transversal já prevista pela Constituição. Raciocínio e Processamento: `REGISTRO APENAS`, preservados aqui para consulta futura.

**Dependências.** Constituição (a dimensão transversal precisa sair de §2.1 para uma seção operacional), etapa 12.

**Riscos de reintrodução indevida.**

1. **Ressurgimento por via lateral do quinto nível.** Vetores por nó são atributos, não níveis. Se `vetor_raciocinio` ganhar identidade própria e virar objeto de navegação, reaparece uma hierarquia paralela.
2. **Redundância entre eixos.** Um nó em `DOM-CAUSAL` com `vetor_raciocinio: {causal: 0.9}` não acrescenta informação — reafirma o domínio. Recuperar sem resolver a sobreposição gera ruído com aparência de estrutura.
3. **Pesos sem proveniência.** Os vetores do WP1 vêm preenchidos com valores numéricos (`{declarativo: 0.2, procedimental: 0.4, ...}`) sem indicação de como foram obtidos. Sob GOV-1.0 §10.2 regra 6, são `[?]` e não podem ser transportados como se fossem [EC] ou [DE] justificada.
4. **Inconsistência interna do original.** Os vetores dos exemplares não somam a nenhum total fixo e usam chaves ausentes das tabelas de origem (`sistemico`, `verbal_linguistico` aparecem abreviados de formas diferentes). Transportá-los literalmente importaria essa inconsistência.

---

## L10 — Camada de decisão pedagógica

**Definição original.** Duas especificações concretas, com ancoragem em literatura:

- **Motor de Recomendação de Conteúdo** (§2.9.3, item 5): _"Seleciona o próximo `CognitiveProcess` a praticar dentre os nós cujos `pre_requisitos` têm `probabilidade_dominio` acima de um limiar de mastery, mas cujo próprio `probabilidade_dominio` está abaixo desse limiar — a implementação computacional direta do Princípio 5 (aproximação da ZPD)."_ Ancorado em Doignon & Falmagne (1985) e Vygotsky (1978).
- **Motor de Agendamento de Revisão** (§2.9.3, item 6): agenda reexposição segundo curva de esquecimento parametrizada por Cepeda et al. (2006), priorizando interleaving entre processos de competências distintas (Rohrer & Taylor, 2007).
- **Features de entrada do recomendador** (§2.9.7): estimativas de domínio de todos os processos; estrutura de pré-requisitos; histórico recente de traço de erro (_"para priorizar remediação de erro conceitual sobre erro atencional, já que o primeiro é mais previsível de recorrer"_); parâmetros de agendamento — equilibrando aquisição nova (Princípio 5) e consolidação (Princípio 6).

**Localização exata no WP1.** §1.8 Princípios 5 e 6 (fundamento, com evidência declarada); §2.9.3 itens 5 e 6; §2.9.7; §2.9.5 (justificativa exibida ao aluno).

**Etiqueta original.** [DE] para os motores; [EC] para os fundamentos (Bjork & Bjork; Roediger & Karpicke; Cepeda et al.; Wood, Bruner & Ross).

**Status no corpus atual.** `CONTRADITO`.

O White Paper 2.0 §6.3 afirma: _"Nenhuma evidência no corpus examinado sustenta uma formulação de como o sistema deveria selecionar a próxima ação pedagógica a partir dessa crença. Este documento registra a ausência como lacuna reconhecida — não como axioma a inventar, nem como conteúdo implicitamente coberto pelos dois axiomas existentes."_ Repetido em §12.4 no nível arquitetural.

**A afirmação é factualmente incorreta em relação ao WP 1.0.** O conteúdo existia, era específico e era ancorado em literatura.

**Deve ser recuperado?** **Sim — como registro e como proposta de engenharia. Não como axioma, e não como norma.**

O White Paper 2.0 tem razão no essencial: os motores não são deriváveis dos dois axiomas. São [DE]. O erro não está em recusá-los como axioma — está em declará-los inexistentes.

**Natureza recomendada.** `DECISÃO DE ENGENHARIA [DE]`, explicitamente **não derivada dos axiomas**, registrada no slot que hoje é declarado vazio.

Sob GOV-1.0 §9.2, o status correto do elemento na transição 1.0 → 2.0 é **rebaixado**, não removido: deixou de ser especificação e passou a ser proposta. Foi tratado como inexistente, que não é um status disponível.

**Dependências.** Errata ao White Paper 2.0 (etapa 11) — a correção mínima é substituir "não há evidência no corpus" por uma declaração de rebaixamento com proveniência. A implementação depende de coisas que não existem: a aresta `Processo ↔ Processo` não está populada (Ontologia v1.4 §8), logo o motor de recomendação **não é executável** hoje, porque não há pré-requisitos sobre os quais operar.

**Riscos de reintrodução indevida.**

1. **Ser lido como preenchimento do slot vazio.** O slot do WP2 §6.3 é uma **função objetivo** — o critério pelo qual o sistema escolhe. Os motores do WP1 são uma **política** particular. Recuperar a política não fornece a função objetivo, e apresentá-la como se fornecesse fecharia indevidamente uma lacuna que o documento de camada C1 declara aberta.
2. **Reintroduzir junto o compromisso com BKT.** O motor de recomendação do WP1 opera sobre `probabilidade_dominio` produzida por Bayesian Knowledge Tracing. O WP2 §4.3 rebaixou a especificidade bayesiana a 35% de confiança, demonstrando equivalência entre quatro famílias. A recuperação deve ser formulada sobre "estimativa de domínio", agnóstica quanto à família.
3. **Reintroduzir `pre_requisitos` sem tipagem.** O motor depende de arestas de pré-requisito. A Constituição §4.3 fixa como restrição inegociável que essa relação, quando existir, seja **tipada e ponderada**, e identifica a aresta única indiferenciada tratada implicitamente como pré-requisito como _"a falha estrutural mais repetida identificada ao longo de todo este projeto"_. Recuperar o motor sem essa restrição reintroduziria a falha mais repetida do projeto.
4. **Confundir remediação com sequenciamento.** A Intervenção Pedagógica da v1.4 responde a um erro diagnosticado; o motor do WP1 escolhe o próximo conteúdo. São camadas distintas com gatilhos distintos.

---

## L11 — Estados de maestria (Fitts-Posner)

**Definição original.** Entidade `MasteryEstimate` com dois campos: `probabilidade_dominio` (float 0–1) e `estado` (enum: `nao_iniciado`, `em_aquisicao`, `dominado`, **`automatizado`**, **`esquecimento_provavel`**). Acompanhada do Detector de Automatização (§2.9.3, item 4): regressão do tempo de resposta ao longo do tempo por processo; automatização inferida quando o tempo estabiliza em patamar baixo com acurácia sustentada.

**Localização exata no WP1.** §2.1.1 (fundamento: Fitts & Posner 1967, três estágios — cognitivo, associativo, autônomo; marcado [EC]); §2.9.1 (entidade `MasteryEstimate`); §2.9.3 item 4; §2.9.5 (exibição ao aluno).

**Etiqueta original.** [EC] para Fitts-Posner e Schneider & Shiffrin; [DE] para o enum e o detector.

**Status no corpus atual.** `REMOVIDO`. Nenhum documento canônico define estados de maestria. O White Paper 2.0 mantém como **abertos** dois graus de liberdade que este elemento aborda: GL-7 (decaimento é propriedade obrigatória ou apenas compatível?) e GL-5a (existem regimes de velocidade genuinamente distintos, e quantos?).

**Deve ser recuperado?** **Como hipótese registrada. Não como norma.**

O valor do elemento é preciso: ele é uma **resposta candidata específica e testável** a duas perguntas que o WP2 lista como abertas. `esquecimento_provavel` é uma posição sobre GL-7; a distinção `dominado`/`automatizado` é uma posição sobre GL-5a. Descartar sem registro empobreceu o Programa de Pesquisa — o WP2 catalogou as perguntas e perdeu uma das respostas candidatas.

**Natureza recomendada.** `HIPÓTESE`, registrada como candidata a teste em GL-5a e GL-7.

**Dependências.** Depende de L1 (o detector de automatização opera sobre latência, que é indicador comportamental). Depende de GL-7 e GL-5a para virar norma. Não depende de nada para ser registrado como hipótese.

**Riscos de reintrodução indevida.**

1. **Fechar GL-7 por implementação.** Introduzir `esquecimento_provavel` como estado é afirmar que há decaimento. Isso resolveria GL-7 por via de engenharia, sem a evidência que o WP2 exige — violação de GOV-1.0 §1.3.
2. **Estado discreto sobre representação probabilística.** O Axioma da Crença Calibrada exige distribuição, não valor de verdade. Um enum de estado, se tratado como fato, viola o axioma. Só é admissível como **rótulo derivado** de uma distribuição, com limiar declarado.
3. **Presumir monotonicidade.** O enum sugere progressão ordenada. A crítica documentada ao BKT clássico é exatamente a suposição de estado binário monotônico e sem esquecimento. Recuperar o enum sem essa ressalva reimportaria a limitação que a literatura já corrigiu.

---

## L12 — Dimensionamento quantitativo

**Definição original.** Três parâmetros de escala com justificativa:

- **80 a 120 Processos Cognitivos** no total (Matemática 25–30; Ciências da Natureza 25–30; Humanas 15–20; Linguagens 15–20; transversais 10–15). Critério declarado: _"grande o suficiente para produzir um grafo com dependências reais e não trivial — uma exigência para que o motor de recomendação tenha o que recomendar — mas pequeno o suficiente para que cada nó receba uma ficha completa com qualidade de curadoria adequada antes de escalar."_
- **15 a 20 itens por processo** para estimativa inicial de parâmetros, 30+ para os priorizados.
- **1.500 a 2.500 itens** no banco inicial, com a observação de que uma década de provas históricas de ENEM e Fuvest já supera esse volume.

**Localização exata no WP1.** §3.5.1 (número de processos e distribuição por área); §3.5.2 (itens por processo e total); §3.5.3 (ordem de priorização de áreas); §3.5.4 (cinco nós de maior transferência).

**Etiqueta original.** [DE], com o critério explicitamente declarado como _"viabilidade de curadoria, não um número derivado diretamente da literatura"_ — declaração de honestidade que deve ser transportada junto.

**Status no corpus atual.** `REMOVIDO`. O White Paper 2.0 Cap. 16 exige piloto mas não dimensiona nada: não diz quantos itens, quantos anotadores, qual amostra por processo, qual kappa mínimo.

**Discrepância registrada:** a Ontologia v1.4 tem **25** processos — cerca de um quarto do piso proposto pelo próprio projeto. A redução veio de fusões legítimas sob a Constituição §2.4 (ônus da separação). A discrepância de fator quatro nunca foi conciliada com o critério de viabilidade que a motivava.

**Deve ser recuperado?** **Sim, como referência de dimensionamento do piloto. Não como meta de tamanho da ontologia.**

**Natureza recomendada.** `REGISTRO APENAS` para o número de processos (é referência histórica, e a v1.4 tem razões documentadas para divergir); `DECISÃO DE ENGENHARIA [DE]` para o dimensionamento amostral do piloto (15–20 itens por processo é o parâmetro diretamente utilizável na etapa 13).

**Dependências.** Protocolo de Piloto (etapa 13).

**Riscos de reintrodução indevida.**

1. **Usar 80–120 como meta de expansão da v1.6.** Seria inverter a lógica do projeto: o número de nós deve resultar da aplicação dos critérios da Constituição, não de uma meta de tamanho. A Constituição §2.5 subordina explicitamente critérios administrativos ao critério explicativo, e "atingir 100 nós" é administrativo.
2. **Confundir itens por processo para estimativa de parâmetros com itens por processo para medição de kappa.** São finalidades estatísticas distintas com requisitos amostrais distintos. O número do WP1 foi calculado para a primeira.
3. **Tratar 25 processos como déficit.** A v1.4 chegou a 25 por fusão justificada. O número menor é resultado de disciplina, não de omissão.

---

## L13 — Regras de Modelagem e governança de ingestão

**Definição original.** Duas coisas distintas, agrupadas aqui por proximidade funcional.

**(a) As cinco Regras de Modelagem (§3.6):**

1. _"O sistema não é uma plataforma de banco de questões. Um item só tem valor na medida em que está corretamente ancorado a `cognitive_mappings` válidos; um item sem mapeamento cognitivo não deve ser exposto ao motor de recomendação, mesmo que tecnicamente armazenado."_
2. _"Nenhuma estrutura é organizada primariamente por matéria escolar. `disciplina` e `tema_curricular` existem apenas como metadados de compatibilidade e de filtro de conveniência — nunca como chave estrangeira."_
3. _"Processos cognitivos reutilizáveis são priorizados e protegidos contra duplicação"_ (via busca sobre sinais — ver L7).
4. _"Uma mesma competência pode, e deve, aparecer em diferentes disciplinas"_ — com `origem_do_no: compartilhado_com_<area>` como mecanismo explícito.
5. _"Separação estrita entre conteúdo factual, habilidade, processo cognitivo, erro e intervenção. Nenhuma lógica de sistema deve inferir um a partir do outro por atalho (ex.: nunca inferir o tipo de erro apenas a partir da disciplina do item)."_

**(b) A regra de governança de ingestão (§3.3.3):**

> _"Nenhum item passa a atualizar `MasteryEstimate` de aluno real sem que seus `cognitive_mappings` de papel nuclear tenham sido confirmados por ao menos um revisor humano, independentemente da via de entrada. Este é o mecanismo operacional que implementa o Princípio 7 ('IA estima e otimiza dentro de uma estrutura teoricamente especificada; não a substitui')."_

**Localização exata no WP1.** §3.6 (as cinco regras); §3.3.1 (fluxo geral de ingestão); §3.3.2 (Via A — cadastro manual); §3.3.3 (Via B — análise por IA, e a regra de governança); §1.8 Princípio 7 (fundamento).

**Etiqueta original.** [DE] para todas.

**Status no corpus atual.** **Divergente entre as regras.**

- Regras 2, 4 e 5: `PRESERVADO` em substância. A Constituição §1.3, §2.2 e §4.4 cobrem a proibição de conteúdo disciplinar como nó e a separação estrita; o Manual §8 cobre a proibição de inferir por disciplina.
- Regra 1: `REMOVIDO`. Nenhum documento condiciona a exposição de um item ao motor à existência de mapeamento válido.
- Regra 3: `REMOVIDO` (depende de L7).
- **(b) Regra de governança de ingestão: `REMOVIDO`, sem equivalente em nenhum documento.**

**Deve ser recuperado?** **(b) sim, com prioridade alta. (a) apenas as regras 1 e 3.**

O item (b) merece destaque: é a **única regra de todo o corpus original que protege o motor de crença de anotação não validada**. O Manual regula como o anotador humano trabalha; o Schema regula o formato da anotação; nenhum documento regula **o que qualifica uma anotação a influenciar o estado de um aluno real**. Essa é uma lacuna de segurança, não de completude.

**Natureza recomendada.** `NORMA` para (b) — é regra de governança operacional e o lugar natural dela é uma seção de governança de ingestão, sob GOV-1.0 ou como capítulo do Manual. `DECISÃO DE ENGENHARIA [DE]` para (a) regras 1 e 3.

**Dependências.** (b) não depende de nada e é recuperável na próxima transação apropriada. (a) regra 3 depende de L7.

**Riscos de reintrodução indevida.**

1. **Transportar (b) com `MasteryEstimate`.** A entidade não existe no corpus atual (ver L11). A regra deve ser reformulada em termos do que existe: nenhuma anotação alimenta a camada de crença sem confirmação humana do processo de papel central.
2. **Transportar "papel nuclear" sem reconciliar vocabulário.** O WP1 usa `nuclear`; o Schema 2.1 usa `nuclear`; o Manual usa "Central". Recuperar a regra sem reconciliar consolidaria a divergência de vocabulário já registrada.
3. **Ler a regra 1 como proibição de armazenamento.** O original é explícito: o item pode ser armazenado; não pode ser **exposto ao motor**. A distinção é o que permite ingestão em massa com enriquecimento posterior.
4. **Duplicar as regras 2, 4 e 5.** Já estão preservadas em substância na Constituição e no Manual. Reintroduzi-las como texto novo criaria duplicação de contrato — proibida por GOV-1.0 §12.

---

## L14 — Bibliografia

**Definição original.** Aparato de referências completo em três blocos: Capítulo 1 (~90 referências, da tradição behaviorista e cognitivista à pesquisa em ITS e knowledge tracing); Capítulo 2 ("Referências adicionais a este capítulo", ~50 entradas, cobrindo Reason, VanLehn, diSessa, Toulmin, Gentner, Kahneman & Tversky, Fitts & Posner, Koedinger-Corbett-Perfetti); Capítulo 4 ("Referências adicionais", ~25 entradas, cobrindo os frameworks-quadro — PISA/OECD, NRC/NGSS, Vergnaud, Dehaene, Confrey & Smith, Chen & Klahr, Chi 2005, Kelemen).

**Localização exata no WP1.** Fim do Capítulo 1; fim do Capítulo 2; fim do Capítulo 4. O Capítulo 3 não tem bloco próprio.

**Etiqueta original.** Não aplicável — é o aparato que **sustenta** as etiquetas.

**Status no corpus atual.** `REMOVIDO`. O White Paper 2.0 cita autores em texto corrido (PISA/OECD, NRC/NGSS, Vergnaud, Dehaene, Siegler, Lamon, Tyack & Cuban, Gruber, Guarino, Koedinger-Corbett-Perfetti) e **não possui seção de referências**.

**Consequência sob governança vigente.** GOV-1.0 §10.2, regra 4: _"uma afirmação [EC] sem referência recuperável é rebaixada automaticamente a [IT] até que a referência seja restaurada."_ Aplicada literalmente ao White Paper 2.0, **toda afirmação [EC] nele contida está hoje rebaixada a [IT]**. Isso não é um tecnicismo: a disciplina [EC]/[IT]/[DE] é ativo protegido, e um documento que classifica afirmações por qualidade de evidência sem citar a evidência perdeu a propriedade que a classificação existe para garantir.

**Deve ser recuperado?** **Sim, integralmente e sem controvérsia.** É a recuperação de menor risco e maior efeito sobre a auditabilidade do corpus.

**Natureza recomendada.** `NORMA` quanto à obrigação de citação; `REGISTRO APENAS` quanto ao conteúdo bibliográfico em si — o aparato do WP1 permanece consultável neste registro e no documento fonte.

**Dependências.** Errata ao White Paper 2.0 (etapa 11). Recuperação parcial imediata possível: as referências que sustentam afirmações [EC] citadas nominalmente pelo WP2 já estão no WP1 e podem ser reconciliadas sem trabalho de pesquisa.

**Riscos de reintrodução indevida.**

1. **Duplicar o aparato em vários documentos.** Uma bibliografia replicada é duplicação de contrato sob GOV-1.0 §12. Deve haver um artefato primário de referências; os demais citam por chave.
2. **Citação sem verificação.** Transportar ~165 entradas sem conferência as trata como [EC] verificada quando são, no melhor caso, [EC] herdada. O transporte deve declarar-se como herança de proveniência, não como verificação nova.
3. **Confundir presença de citação com sustentação da afirmação.** Uma referência prova que a literatura existe; não prova que ela sustenta a afirmação específica que a invoca. As reconciliações mais delicadas são as que o WP1 já marcava como [IT] — extrapolações razoáveis, não achados.

---

## 15. Conteúdo do WP 1.0 deliberadamente NÃO extraído

Registrado para completude, conforme GOV-1.0 §8.2: _"um elemento que ninguém examinou não pode ser declarado descartado."_ Os itens abaixo **foram examinados** e a decisão é **não recuperar** — porque o White Paper 2.0 os corrigiu com razão.

|Elemento do WP1|Localização|Correção do WP2|Decisão|
|---|---|---|---|
|BKT como o estimador prescrito|§2.9.3 item 1|§4.3: equivalência entre quatro famílias; especificidade bayesiana a 35%|**Não recuperar.** Recuperar reintroduziria um compromisso que o WP2 desfez com demonstração|
|Grafo simbólico como consequência da evidência|§1.6.5, §1.8 Princípio 1|§12.2: hipótese arquitetural contingente a GL-8/GL-16|**Não recuperar** como necessidade. A forma de grafo permanece em uso como escolha declarada|
|Pré-requisito com força causal operacional|§2.9.1 `GraphEdge`, §2.9.3 item 5|§5.2 (35% no qualificador causal); §5.4 (pergunta possivelmente irrespondível)|**Não recuperar** a leitura causal. A aresta permanece, associativa até prova em contrário|
|Competência como nível ontológico primário com ficha própria|§2.1.3, §2.6, §2.9.1 `Competency`|Hipótese sob auditoria a 55%; Constituição §3.2: agrupamento derivado, recalculável|**Não recuperar.** A ficha de Competência do WP1 pressupõe entidade primária|
|`PROC-INC-001` — distinção arranjo/combinação/permutação como processo|§3.1.1, §4.2|§13.4 do WP2 o identifica como mistura de capacidade geral com conteúdo procedural; a v1.4 o absorveu em `PROC-INC-04`|**Não recuperar** como nó autônomo|
|Efeito "dois sigma" como magnitude|§1.6.3|Já qualificado no próprio WP1 via VanLehn (2011); WP2 generaliza a cautela|**Não recuperar** a magnitude; a direção do achado permanece|

## 16. Síntese das recomendações

|Elemento|Recuperar?|Natureza|Bloqueado por|
|---|---|---|---|
|**L1** Indicador Comportamental|Sim, como camada transversal|[DE]|Constituição (etapa 12)|
|**L2** Error Trace ordenado|**Sim — prioridade máxima**|NORMA (estrutura) + [DE] (produção)|Mapa de IDs → Espec. Error Trace (etapa 8)|
|**L3** Erro por mecanismo psicológico|Sim, como dimensão adicional|[DE], atributo do Tipo de Erro|Mapa de IDs; piloto para virar catálogo|
|**L4** Falsa proficiência|Sim|[DE] (critério) + REGISTRO (instâncias)|Nada para registro|
|**L5** Grau de transferência|Sim, sem escala fixa|HIPÓTESE|GL-10|
|**L6** Confundidas / mascaradas|Sim|[DE], dois tipos de aresta|Constituição Cap. 12|
|**L7** Sinais de identificação|Sim, com cláusula de uso|[DE]|Nada para uso em curadoria|
|**L8** Contraexemplos|Sim, no Manual|[DE]|Manual v1.1 (etapa 7)|
|**L9** Vetores — Conhecimento|Sim|[DE], dimensão transversal|Constituição (etapa 12)|
|**L9** Vetores — Raciocínio, Processamento|**Não agora**|REGISTRO APENAS|—|
|**L10** Camada de decisão|Sim, como proposta rebaixada|[DE], não derivada dos axiomas|Errata ao WP2 (etapa 11)|
|**L11** Estados de maestria|Sim, como hipótese|HIPÓTESE|GL-5a, GL-7|
|**L12** Dimensionamento|Parcial — só o amostral|[DE] (amostra) + REGISTRO (nós)|Protocolo de Piloto (etapa 13)|
|**L13a** Regras de Modelagem 1 e 3|Sim|[DE]|L7 para a regra 3|
|**L13b** Governança de ingestão|**Sim — prioridade alta**|NORMA|Nada|
|**L14** Bibliografia|Sim, integralmente|NORMA (obrigação) + REGISTRO (conteúdo)|Errata ao WP2 (etapa 11)|

**Dois elementos são recuperáveis sem depender de nada:** L13b (governança de ingestão) e L4 (critério de falsa proficiência, como registro). Ambos são de custo baixo e fecham lacunas de segurança e de ativo protegido.

**Um elemento é bloqueante para toda a cadeia de contratos:** L2. A Especificação do Error Trace não pode ser escrita sem ele, e o Schema não pode ser corrigido sem a Especificação.

---

## 17. Efeito sobre o estado do documento fonte

Com a aprovação deste registro, a condição de GOV-1.0 §8.2 fica satisfeita e o White Paper 1.0 torna-se **elegível** para supersessão.

A supersessão **não** é executada nesta transação. Quando o for, exigirá, conforme GOV-1.0 §8.1, declaração bidirecional:

- no White Paper 2.0: `supersedes: [WP-1.0]`
- no White Paper 1.0: `superseded_by: WP-2.0`, `estado: superseded`, `registro_de_extracao: EXT-WP1-1.0`

Até lá, o White Paper 1.0 permanece `ativo` — não como norma concorrente, mas porque nenhuma outra transição é válida sob GOV-1.0 §2.2 antes da declaração formal.

---

## 18. Changelog

|TX|Timestamp|Classe|Alteração|Autoriza|Co-alterados|
|---|---|---|---|---|---|
|`TX-2026-08-17T041133Z-ext-wp1`|2026-08-17T04:11:33Z|— (criação)|Criação do registro em estado `ativo`|AUD-2026-08-17T03:42:31Z, Fase 1, passo 2; GOV-1.0 §8.2|nenhum|

_Fim do documento. Nenhum documento canônico preexistente foi alterado por esta transação. Nenhuma categoria cognitiva foi criada, alterada ou removida._