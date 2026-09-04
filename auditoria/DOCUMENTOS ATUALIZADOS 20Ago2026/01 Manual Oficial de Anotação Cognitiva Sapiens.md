01 Manual Oficial de Anotação Cognitiva Sapiens.md

---

id: MAN-1.2 titulo: Manual Oficial de Anotação Cognitiva Sapiens versao: 1.2 estado: congelado camada: C4 criado_em: 2026-08-17T02:57:48Z atualizado_em: 2026-08-17T17:46:27Z supersedes: ["1.0", "1.1"] superseded_by: null derivado_de: null governado_por: GOV-1.0 governed_by_conteudo:

- "White Paper Sapiens 2.0"
- "Constituição da Ontologia Sapiens"
- "Ontologia Cognitiva Sapiens v1.4.1"
- "Especificação do Error Trace v1.0"
- "Schema Sapiens 2.2" compativel_com: ontologia: ">=1.4.1, <2.0" item_schema: ">=2.2, <3.0" error_trace: ">=1.0, <2.0" geracao_de_ids: G3 cni_membros: [] changelog_ref: TX-2026-08-17T174627Z-manual-v1.2 remissoes_pendentes:
- "§12, regra 5 — 'Plano de Validação' (kappa de Cohen): documento inexistente no corpus canônico. G-CONF-13. Será fechado pelo Protocolo de Piloto."

---

# Manual Oficial de Anotação Cognitiva Sapiens

## v1.2

Documento operacional, construído sobre os artefatos normativos congelados do projeto: **White Paper Sapiens 2.0** (restrição conceitual), **Constituição da Ontologia Sapiens** (regra de engenharia) e **Ontologia Cognitiva Sapiens v1.4.1** (catálogo). Seu processo de alteração é governado por **Governança e Versionamento Sapiens v1.0** (GOV-1.0).

Nenhum Domínio, Processo, Competência, Habilidade, Tipo de Erro ou Intervenção é criado, removido ou reorganizado neste documento — todos os IDs citados abaixo referem-se exclusivamente ao catálogo já congelado (11 Domínios, 25 Processos, 12 Competências, 56 Habilidades, 13 Tipos de Erro, 11 Intervenções).

**Geração de identificadores.** Todos os IDs citados neste Manual pertencem à geração **G3** — a da Ontologia v1.4.x. Isso é declarado explicitamente porque o corpus contém quatro gerações de esquema de identificador, com colisões documentadas: em particular, os treze tipos de erro do White Paper 1.0 são numerados de 1 a 13 e formam um conjunto **disjunto** dos treze `ERR-NN` deste catálogo, e `ERR-05` e `ERR-13` tiveram significados diferentes na v1.3. Ver `09 Mapa de Rastreabilidade de IDs`, §5 e §10 a §12. Nenhuma anotação produzida sob outra geração pode ser lida contra este Manual sem remapeamento explícito.

**Nota histórica de rastreabilidade** _(corrigida na v1.1 — o texto da v1.0 era factualmente incorreto)_: ao construir a v1.0 deste Manual, foi identificada uma inconsistência entre o artefato JSON da ontologia e o documento em prosa — o Tipo de Erro `ERR-13` aparecia vinculado a `PROC-CLASSIF-01` (correto, conforme o texto da Ontologia) **e** a `PROC-ESPACO-03` (incorreto — a Ontologia registra explicitamente, em sua seção de questões em aberto, que `PROC-ESPACO-03` ainda não tem Tipo de Erro catalogado).

A v1.0 deste Manual afirmava que essa correção havia sido aplicada ao arquivo JSON **antes** de sua redação. **Isso não ocorreu.** A auditoria integral do corpus (`AUD-2026-08-17T03:42:31Z`) verificou que ambos os artefatos JSON então existentes mantinham o vínculo indevido. A correção foi efetivamente aplicada em 2026-08-17, pela transação `TX-2026-08-17T043240Z-patch-err13`: primeiro ao artefato JSON, depois ao membro em prosa, elevando o catálogo à versão **1.4.1**. A afirmação da v1.0 é aqui corrigida, e não removida, para preservar o registro do que foi afirmado e quando.

---

## 1. Fluxograma Completo do Processo de Anotação

Não, reler

---

## 2. Ordem Obrigatória de Decisão

A ordem abaixo não é sugestão — é obrigatória, porque cada etapa depende do resultado da anterior. Inverter a ordem (por exemplo, escolher a Habilidade antes do Processo) produz anotações que dois avaliadores independentes não conseguem reproduzir.

1. **Ler o item por completo** — enunciado, todas as alternativas e qualquer recurso visual — antes de classificar qualquer coisa. Classificar a partir de leitura parcial é a causa mais comum de discordância entre anotadores.
2. **Identificar o Domínio** pela operação mental exigida (Seção 3 da Constituição), nunca pela disciplina de origem do item.
3. **Identificar o Processo Cognitivo dominante** dentro do(s) Domínio(s) candidato(s) (Seção 3 deste Manual).
4. **Verificar processos candidatos adicionais** (Seção 4) — só depois de o dominante estar fixado.
5. **Atribuir pesos**, se houver mais de um processo (Seção 5) — só depois de a lista de processos estar fechada.
6. **Selecionar Habilidade(s) Observável(is)** — só depois de o(s) Processo(s) estarem decididos, nunca antes (a Habilidade é definida em função do Processo, não o contrário).
7. **Identificar Tipo(s) de Erro** para as alternativas incorretas — só depois de o Processo estar fixado, porque o catálogo de erro é indexado por processo.
8. **Registrar incerteza**, se houver, de forma explícita (nunca por omissão).
9. **Rodar o Checklist Final** (Seção 10).
10. **Salvar**, com justificativa breve e identificação do anotador.

---

## 3. Como Identificar o Processo Cognitivo Dominante

**Regra central**: o Processo dominante é aquele cuja ausência tornaria o item impossível de responder corretamente, mesmo que todos os outros processos envolvidos estivessem intactos.

**Procedimento (teste de substituição de conteúdo)**: leia o item ignorando deliberadamente o vocabulário disciplinar. Pergunte: _"Se eu trocasse o cenário deste item por um de outra disciplina, mantendo a mesma estrutura de raciocínio, o item continuaria exigindo a mesma operação mental para ser resolvido?"_

- Se **sim** — a operação identificada é candidata legítima a Processo Cognitivo (é transferível, por definição da Constituição §2.3).
- Se **não** — o item provavelmente está testando conhecimento de conteúdo específico, não um Processo desta ontologia; verifique se não é caso de negar classificação (Seção 8).

**Fonte fechada**: o Processo dominante deve ser um dos 25 já catalogados na Ontologia v1.4.1. Não existe exceção. Se nenhum dos 25 parecer adequado, siga o protocolo de item não-classificável (Seção 11) — nunca force o item no processo mais parecido.

**Atalho prático por padrão de pergunta** (não substitui o teste acima, apenas acelera a triagem inicial):

|Se o item pede para...|Domínio provável|Processo(s) mais prováveis|
|---|---|---|
|Comparar, escalar ou converter quantidades|DOM-QUANT|PROC-QUANT-01 a 04|
|Ler forma, medir ou decompor figura|DOM-ESPACO|PROC-ESPACO-01, 02|
|Explicar o papel de uma parte dentro de um todo|DOM-ESPACO|PROC-ESPACO-03|
|Calcular como uma grandeza muda em função de outra, ou verificar o que se conserva|DOM-MUDANCA|PROC-MUD-01, 02|
|Interpretar dado, chance ou distribuição|DOM-INCERTEZA|PROC-INC-01 a 04|
|Explicar por que algo aconteceu|DOM-CAUSAL|PROC-CAUSAL-01|
|Julgar se uma conclusão segue das premissas|DOM-LOGICO|PROC-LOGICO-01|
|Converter enunciado em fórmula, ou ler uma fórmula já dada|DOM-SIMBOLICO|PROC-SIMB-01, 02|
|Localizar, inferir ou combinar informação de texto/gráfico/tabela|DOM-TEXTUAL|PROC-TEXT-01 a 03|
|Formular hipótese ou isolar variável|DOM-EXPERIMENTAL|PROC-EXP-01, 02|
|Prever resposta de um sistema, ou relacionar fluxo entre partes|DOM-SISTEMICO|PROC-SIST-01, 02|
|Agrupar por critério compartilhado|DOM-CLASSIF|PROC-CLASSIF-01|

## 4. Quando Existem Dois ou Mais Processos Candidatos

Registre um segundo Processo **somente** se ele passar, de forma independente, o mesmo teste de necessidade da Seção 3. "Está relacionado" ou "aparece no mesmo enunciado" não é critério suficiente.

Distinga três situações, porque cada uma é anotada de forma diferente:

- **(a) Composição sequencial** — o resultado do Processo A alimenta o Processo B (ex.: primeiro ler um gráfico, depois calcular uma proporção sobre o valor lido). Ambos são candidatos legítimos.
- **(b) Restrição conjunta** — os dois processos são exigidos simultaneamente para chegar à única resposta correta (ex.: proporção **e** conversão de unidade no mesmo cálculo). Ambos são candidatos legítimos.
- **(c) Caminhos alternativos de solução** — alunos diferentes poderiam resolver o item por estratégias cognitivas diferentes. **Não são co-dominantes** — registre ambos como "possíveis", não como par com peso fixo; este caso é sinal de item mal desenhado para diagnóstico preciso, não uma anotação normal.

**Limite obrigatório**: no máximo 2 processos como candidatos com peso nesta versão. Se um terceiro processo genuinamente passar no teste de necessidade, **não** distribua pesos entre três — registre o item como ambiguidade (Seção 11) para revisão futura de governança, e prossiga com os dois processos de maior necessidade diagnóstica.

---

## 5. Como Atribuir Pesos entre Processos

A Ontologia v1.4.1 exige peso sempre que há mais de um Processo candidato (Constituição, §4.5), mas não fixa a fórmula. Para permitir anotação humana consistente **hoje**, este Manual define uma convenção provisória de bins categóricos, não um modelo matemático final:

|Situação|Peso a registrar|
|---|---|
|Processo único identificado|1.0 (implícito, não precisa escrever)|
|Processo cuja ausência tornaria o item **certamente** não-respondível corretamente|**`nuclear` — 0.7**|
|Processo cuja ausência tornaria o item **mais difícil, mas ainda plausivelmente respondível** por um caminho alternativo|**`secundario` — 0.3**|
|Processo cuja presença apenas facilita, mas cuja ausência não muda se o item é respondível|**Não registrar** — não é candidato válido (falha o teste de necessidade da Seção 4)|

**Pergunta de desempate** quando dois candidatos parecem igualmente necessários: qual dos dois, se testado isoladamente em outro item, teria maior valor diagnóstico para decidir a próxima intervenção pedagógica? Esse é o `nuclear`.

Os pesos de todos os processos registrados para um mesmo item devem somar exatamente 1.0. Esta é uma convenção de registro para consistência entre anotadores nesta fase — não uma afirmação científica final sobre como a fatoração de desempenho funciona.

> **Remissão resolvida na v1.2.** A v1.0 remetia a fórmula de peso a uma "Especificação Técnica" inexistente (`G-CONF-04`); a v1.1 registrou a remissão como pendente. A pendência está agora fechada: a regra de peso vigente é **esta seção**, e os dois contratos de máquina a citam nominalmente como fonte — o **Schema Sapiens 2.2** (campo `estrutura_cognitiva.processos[].peso_no_item`) e a **Especificação do Error Trace v1.0** (§5, para a escala de confiança do traço). Não existe outra fórmula de peso em nenhum lugar do corpus.
> 
> **Vocabulário reconciliado na v1.2.** Os rótulos passam a ser `nuclear` e `secundario`, conforme a decisão de reconciliação da Especificação do Error Trace §7 — é a forma presente nos dois contratos de máquina e na fonte original, contra uma única ocorrência em prosa. **A mudança é de rótulo, não de semântica:** os limiares 0.7 e 0.3, o teste de necessidade e o limite de dois processos permanecem exatamente como estavam. Anotações produzidas sob a v1.0 ou v1.1 permanecem válidas; apenas o nome do papel muda.

---

## 6. Critérios para Selecionar Habilidades Observáveis

1. Selecione **apenas** entre as Habilidades já catalogadas sob o(s) Processo(s) já decididos (lista fechada de 56 — nunca invente uma nova).
2. Teste obrigatório: a Habilidade escolhida precisa corresponder ao **formato de estímulo real do item** (texto puro, tabela, gráfico, figura, fórmula) — não escolha "ler gráfico de linhas" (HAB-46, por exemplo) se o item não contém gráfico algum.
3. Se o Processo tiver mais de uma Habilidade candidata plausível (ex.: HAB-03 proporcionalidade direta vs. HAB-04 proporcionalidade inversa, ambas sob PROC-QUANT-02), selecione **apenas a que corresponde à estrutura matemática real do item** — nunca as duas, a menos que o item genuinamente exija as duas em sequência.
4. Se nenhuma Habilidade catalogada corresponder com exatidão ao item, escolha a mais próxima e marque explicitamente como **"aproximado"** — não force um encaixe perfeito artificial, e não invente uma Habilidade nova.

---

## 7. Critérios para Identificar Tipos de Erro

1. Consulte **apenas** os Tipos de Erro já vinculados, em catálogo, ao Processo dominante do item (tabela de referência na Seção 11 lista quais Processos ainda não têm Erro catalogado).
2. Para cada alternativa incorreta, pergunte: _"Se um estudante escolhesse esta alternativa, qual mecanismo cognitivo — não apenas 'errou' — explicaria essa escolha?"_
3. Se a alternativa parece refletir descuido/erro de digitação/erro de leitura de gabarito, não um mecanismo cognitivo real, **não** force um Tipo de Erro — registre "sem mecanismo cognitivo identificável".
4. Se o Processo dominante do item **não** tiver nenhum Tipo de Erro catalogado na v1.4.1 (13 dos 25 processos estão nessa situação — ver Seção 11), registre **"erro não catalogado nesta versão"** para cada alternativa incorreta. Não empreste um Tipo de Erro de outro Processo só por parecer semelhante — a relação Erro→Processo é de catálogo (Constituição §4.3), definida em tempo de construção da ontologia, não em tempo de anotação.

---

## 8. Quando NÃO Atribuir Determinado Processo

- **Não** atribua um Processo pela disciplina de origem do item (ex.: não atribua PROC-MUD-02 só porque o item é de Química — atribua apenas se rastrear um invariante for de fato a operação exigida para resolver o item).
- **Não** atribua um Processo pela presença de palavra-chave no enunciado (a palavra "proporção" no texto não implica PROC-QUANT-02 se a resposta correta não depender, de fato, de raciocínio proporcional).
- **Não** atribua um segundo Processo "para ser mais completo" — todo Processo atribuído precisa passar o teste de necessidade da Seção 4, sem exceção.
- **Não** atribua uma Habilidade cujo formato de estímulo não corresponde ao item real.
- **Não** atribua Domínio pela prova/vestibular de origem do item — atribua pelo Domínio real da operação exigida.
- **Não** "regularize" um item que não se encaixa bem em nenhum Processo forçando-o no mais próximo disponível — use o protocolo de item não-classificável (Seção 11).
- **Não** invente um Tipo de Erro para preencher uma lacuna de catálogo (Seção 7, regra 4).

---

## 9. Exemplos Positivos e Negativos

**Exemplo 1 — Domínio pela operação, não pela disciplina (ilustra Seções 3 e 8)**

> _Item: "Uma fábrica usa 3 máquinas para produzir 300 peças por hora. Mantendo a mesma taxa de produção por máquina, quantas peças por hora serão produzidas com 5 máquinas idênticas?"_

✅ **Correto**: Domínio = DOM-QUANT. Processo = PROC-QUANT-02. Habilidade = HAB-03. Justificativa: a operação exigida é raciocínio proporcional; o cenário "fábrica" é irrelevante para a classificação. ❌ **Incorreto**: classificar como algo ligado a "processo industrial" ou tentar registrar um processo inexistente de "produção fabril". Viola a Seção 8 (classificação por cenário/disciplina) e não existe tal processo no catálogo.

**Exemplo 2 — Não inventar processo de conteúdo (ilustra Seções 3 e 8)**

> _Item de Biologia: pede para associar a mitocôndria à sua função na respiração celular._

✅ **Correto**: Domínio = DOM-ESPACO. Processo = PROC-ESPACO-03. Habilidade = HAB-14. ❌ **Incorreto**: tentar classificar sob um processo de "biologia celular" que não existe no catálogo v1.4.1 — o processo cross-disciplinar correto já existe e cobre exatamente este caso.

**Exemplo 3 — Dois processos com pesos (ilustra Seções 4 e 5)**

> _Item: gráfico mostra concentração de um reagente ao longo do tempo; pede para calcular a quantidade de produto formado em um instante específico, exigindo primeiro ler corretamente o valor no gráfico e depois aplicar uma relação proporcional sobre esse valor._

✅ **Correto**: Processo `nuclear` (0.7) = PROC-QUANT-02 (a operação proporcional é o núcleo do que o item avalia). Processo `secundario` (0.3) = PROC-TEXT-01 (ler o gráfico é pré-condição, mas o item testa primariamente a proporção, não a leitura gráfica em si). Habilidades: HAB-03 + HAB-42/44 conforme o formato exato do gráfico. ❌ **Incorreto**: anotar apenas PROC-QUANT-02 e ignorar a exigência real de leitura gráfica (perde informação diagnóstica sobre uma possível causa alternativa de erro) — ou registrar 3 processos sem aplicar o teste de necessidade a cada um.

**Exemplo 4 — Erro não catalogado (ilustra Seção 7)**

> _Item cujo Processo dominante é PROC-EXP-01 (formular hipótese testável), que não possui Tipo de Erro catalogado na v1.4.1._

✅ **Correto**: para a alternativa incorreta, registrar "erro não catalogado nesta versão". ❌ **Incorreto**: forçar a alternativa em ERR-02 (inferência indevida) só por parecer semelhante — contaminaria a base com um vínculo Erro→Processo que a ontologia não autoriza.

---

## 10. Checklist Final de Validação

Antes de salvar qualquer anotação, confirme item por item:

- [ ]  Li o item completo (enunciado, todas as alternativas, recursos visuais) antes de classificar qualquer coisa?
- [ ]  O Domínio foi identificado pela operação cognitiva exigida, não pela disciplina de origem?
- [ ]  O Processo dominante passa o teste de necessidade (Seção 3)?
- [ ]  Se há mais de um Processo, cada um passou o teste de necessidade individualmente (Seção 4), e os pesos somam 1.0 (Seção 5)?
- [ ]  As Habilidades selecionadas pertencem ao catálogo do(s) Processo(s) escolhido(s), e o formato de estímulo bate com o item real (Seção 6)?
- [ ]  Os Tipos de Erro atribuídos (quando existirem) pertencem ao catálogo do Processo dominante — nenhum emprestado de outro processo (Seção 7)?
- [ ]  Nenhum Processo, Habilidade ou Erro foi atribuído por palavra-chave, disciplina ou prova de origem (Seção 8)?
- [ ]  Toda incerteza foi registrada explicitamente (nenhuma resolvida por suposição silenciosa)?
- [ ]  Se o item não se encaixou bem em nenhum elemento do catálogo, isso foi registrado como ambiguidade (Seção 11), não forçado?
- [ ]  Escrevi uma justificativa breve (1–2 frases) para o Processo dominante?
- [ ]  A anotação está identificada com meu nome/ID e a data?
- [ ]  A anotação declara a versão da ontologia contra a qual foi produzida (**1.4.1**)?

Só salve se todas as caixas estiverem marcadas.

---

## 11. Ambiguidades Conhecidas da Ontologia v1.4.1

Estas ambiguidades são herdadas da própria Ontologia v1.4.1 (sua Seção 10, "Questões em Aberto") — não são falhas deste Manual, e não devem ser resolvidas pelo anotador. O papel do anotador é seguir o protocolo indicado, não decidir a arquitetura.

**Processos ainda sem Tipo de Erro catalogado (13 de 25)** — use "erro não catalogado nesta versão" (Seção 7, regra 4) para qualquer um destes: PROC-QUANT-01, PROC-ESPACO-01, PROC-ESPACO-02, PROC-ESPACO-03, PROC-MUD-01, PROC-MUD-02, PROC-INC-01, PROC-INC-02, PROC-INC-04, PROC-TEXT-03, PROC-EXP-01, PROC-SIST-01, PROC-SIST-02.

**PROC-INC-02 agrupa três operações (média, mediana, moda) em um único Processo.** Se você notar, ao longo de várias anotações, que erros em uma dessas três operações parecem sistematicamente diferentes dos erros nas outras duas, **não separe o processo por conta própria** — registre a observação como nota de ambiguidade recorrente para revisão futura de governança.

**Fronteira DOM-CAUSAL vs. DOM-EXPERIMENTAL.** Regra de desempate obrigatória: se a pergunta central do item pede para **avaliar ou desenhar** um experimento (isolar variável, identificar controle), classifique DOM-EXPERIMENTAL / PROC-EXP-02. Se pede para **explicar ou prever** uma relação causal usando dados já fornecidos, sem exigir desenho experimental, classifique DOM-CAUSAL / PROC-CAUSAL-01.

> **Estatuto desta regra, declarado na v1.1 (GOV-1.0 §1.3).** Esta é uma **convenção provisória de camada operacional**, não uma decisão de fronteira de domínio. A Ontologia v1.4.1 §10, item 7, deixa a fronteira explicitamente sem regra de prioridade declarada; um documento de camada C4 não pode resolver questão que a camada C3 mantém aberta. Portanto: **(i)** esta regra é provisória e existe apenas para tornar a anotação executável hoje; **(ii)** ela **não vincula** a Ontologia nem a Constituição; **(iii)** está registrada como pendência de arbitragem no changelog da Ontologia v1.4.1. Ver `G-CONF-06`. A arbitragem definitiva pertence à Constituição.

**Fronteira PROC-CLASSIF-01 vs. PROC-ESPACO-03.** Regra de desempate: se a pergunta pede para **agrupar/categorizar** a entidade, é PROC-CLASSIF-01. Se pede para **explicar o papel funcional** de uma estrutura, é PROC-ESPACO-03. _(Mesmo estatuto provisório declarado acima: a Ontologia v1.4.1 §10, item 6, mantém a fronteira em aberto.)_

**Pertencimento Processo↔Domínio é 1:1 nesta versão**, embora a Constituição permita pertencimento múltiplo. Anote sempre pelo Domínio único já listado no catálogo, mesmo que o item pareça tocar mais de um Domínio — não adicione um segundo Domínio por conta própria.

**Relações Processo↔Processo (pré-requisito, facilitação etc.) não estão populadas nesta versão.** Não tente inferir ou registrar dependências entre processos — está fora do escopo deste Manual.

---

## 12. Convenções Obrigatórias de Consistência

1. Cite sempre o **ID exato** do catálogo (ex.: `PROC-QUANT-02`) — nunca parafraseie o nome do Processo, Habilidade ou Erro. Todos os IDs são da geração **G3** (ver preâmbulo).
2. Registre toda incerteza com a notação padronizada: `candidato-secundário: incerto`, `aproximado`, `erro não catalogado nesta versão`, `ambiguidade — ver Seção 11`. Nunca deixe um campo obrigatório em branco.
3. Nunca renomeie, abrevie ou "corrija" um ID do catálogo, mesmo que pareça haver erro de digitação — reporte separadamente, não altere na anotação.
4. Toda anotação exige uma **justificativa breve** (1–2 frases) para o Processo dominante, escrita de forma que um segundo anotador, sem acesso ao raciocínio do primeiro, consiga entender a decisão.
5. **Não consulte a anotação de outro anotador antes de finalizar a sua.** A independência entre anotadores é pré-condição para que a medição de concordância (kappa de Cohen) seja válida. _(Remissão pendente: a v1.0 remetia essa medição a um "Plano de Validação" inexistente no corpus — `G-CONF-13`. A exigência de anotação dupla e independente permanece válida por força do White Paper 2.0, Cap. 16, que a declara condição de entrada para qualquer expansão de escopo.)_
6. Em caso de dúvida legítima entre dois Processos permitidos, prefira a interpretação de **menor generalidade** que ainda explica integralmente a exigência do item — evita inflar processos genéricos demais com itens que na verdade testam algo mais específico já catalogado.
7. Toda sessão de anotação deve ser **datada e assinada** (nome ou ID do anotador), sem exceção, para rastreabilidade.
8. Este Manual, assim como a Ontologia v1.4.1 que ele opera, está **congelado**. Sugestões de mudança na ontologia (novos processos, fusões, remoções) devem ser registradas separadamente como observação de campo — nunca implementadas unilateralmente durante a anotação.

> **Caminho de descongelamento, acrescentado na v1.1.** A v1.0 declarava o congelamento sem indicar como ele poderia ser levantado, o que tornava impossível até a correção de erros materiais (`G-CONF-02`). O caminho é o de GOV-1.0: correções de fidelidade e erratas (Classe I e II, §3.3) são aplicáveis **sem** descongelamento, mediante transação registrada; emendas aditivas e substantivas (Classes III e IV) exigem ato formal de descongelamento pelo Curador (§3.4), com escopo fechado e compromisso de recongelamento. Mudanças de estrutura do catálogo exigem, ainda, a evidência do §11.2. O congelamento continua em vigor; deixou de ser sem saída.

---

## 13. Registro de Observação de Campo

Esta seção existe porque o §12, regra 8, obriga o anotador a **registrar** sugestões de mudança em vez de implementá-las, e até a v1.1 não havia formato para esse registro. Sem formato, a observação vira texto livre e não alimenta revisão alguma — que é exatamente o sinal que a Ontologia §10 e o White Paper 2.0 Cap. 16 esperam do piloto.

O formato abaixo espelha os campos estruturados de incerteza do Schema Sapiens 2.2 (bloco `incerteza`), para que observação de campo e anotação sejam consultáveis pelo mesmo eixo.

**Uma observação de campo NÃO é uma anotação.** Ela não altera o item anotado, não entra na medição de concordância e não tem efeito sobre nenhum catálogo. É insumo de governança.

|Campo|Obrigatório|Conteúdo|
|---|---|---|
|`obs_id`|Sim|Identificador único|
|`data`|Sim|ISO-8601 UTC|
|`anotador`|Sim|Nome ou ID (§12, regra 7)|
|`ontology_version`|Sim|Versão contra a qual a observação foi feita (GOV-1.0 §6.1)|
|`item_id`|Quando aplicável|Item que motivou a observação|
|`marcador`|Sim|Vocabulário fechado, idêntico ao do Schema 2.2: `candidato-secundario-incerto`, `aproximado`, `erro-nao-catalogado-nesta-versao`, `sem-mecanismo-cognitivo-identificavel`, `ambiguidade-fronteira`, `item-nao-classificavel`, `tres-ou-mais-processos-necessarios`|
|`elementos_envolvidos`|Sim|IDs do catálogo (geração G3) a que a observação se refere|
|`descricao`|Sim|1–3 frases, factuais. O que foi observado, não o que deveria mudar|
|`recorrencia`|Recomendado|Quantas vezes o anotador já viu o mesmo padrão|
|`sugestao`|Não|Se houver. Marcada explicitamente como sugestão, nunca como decisão|

**Quatro padrões que o corpus já pede que sejam observados**, cada um remetendo à questão aberta que o motiva:

|O que observar|Motivo registrado|
|---|---|
|Erros em média, mediana e moda que pareçam sistematicamente distintos entre si|Ontologia §10, item 2 — `PROC-INC-02` é candidato a divisão|
|Itens em que a fronteira `DOM-CAUSAL` × `DOM-EXPERIMENTAL` ou `PROC-CLASSIF-01` × `PROC-ESPACO-03` exija a regra de desempate do §11|Ontologia §10, itens 6 e 7 — fronteiras em aberto; a regra do §11 é provisória|
|Itens que pareçam tocar mais de um Domínio|Ontologia §10, item 4 — pertencimento múltiplo Processo↔Domínio|
|Processos sem Tipo de Erro catalogado em que um padrão de erro real e recorrente apareça|Ontologia §10, item 3 — 13 dos 25 processos; os erros devem ser populados a partir de observação, não inventados|

**O que o anotador nunca faz**, mesmo tendo observado o padrão muitas vezes: criar, dividir, fundir ou renomear qualquer elemento do catálogo; alterar a regra de desempate do §11; ou tratar sua própria sugestão como decisão. A promoção de uma observação a mudança de catálogo exige evidência de piloto e ato do Curador (GOV-1.0 §3.4 e §11.2).

---

## 14. Itens Deferidos

Registrados aqui conforme GOV-1.0 §1.4 e §6.3. Nenhum é resolvível por este Manual no estado atual do corpus, e nenhum foi antecipado.

|Item|Descrição|Estado|Depende de|
|---|---|---|---|
|**D-1**|Reconciliação do vocabulário de papel do processo|**RESOLVIDO na v1.2** — adotado `nuclear` / `secundario` (Error Trace §7)|—|
|**D-2**|Localização definitiva da regra de peso, antes remetida a documento inexistente (§5)|**RESOLVIDO na v1.2** — a regra é o §5 deste Manual, citado nominalmente pelo Schema 2.2 e pela Especificação do Error Trace|—|
|**D-3**|Seção de registro estruturado de observação de campo|**RESOLVIDO na v1.2** — §13, alinhada ao bloco `incerteza` do Schema 2.2|—|
|**D-4**|Arbitragem definitiva das fronteiras `DOM-CAUSAL` × `DOM-EXPERIMENTAL` e `PROC-CLASSIF-01` × `PROC-ESPACO-03` (§11)|**ABERTO** — convenção provisória em vigor, registrada como pendência de arbitragem no changelog da Ontologia|Constituição; evidência de piloto|
|**D-5**|Fechamento da remissão a "Plano de Validação" (§12, regra 5)|**ABERTO** — `G-CONF-13`|Protocolo de Piloto|

## 15. Changelog

|TX|Timestamp|Classe|Alteração|
|---|---|---|---|
|`TX-2026-08-17T174623Z-manual-v1.1`|2026-08-17T17:46:23Z|I — Correção de Fidelidade, com itens de Classe II|**(1)** Referências de versão do catálogo atualizadas de `v1.4` para `v1.4.1` (preâmbulo, §1, §3, §5, §7, §9, §11, §12). **(2)** §12.8: acrescentado o caminho de descongelamento ausente (G-CONF-02). **(3)** Cabeçalho canônico YAML e `compativel_com` (G-CONF-08, GOV-1.0 §7.1 e §6.2). **(4)** Changelog criado. **(5)** Nota histórica de rastreabilidade corrigida — a v1.0 afirmava, de forma factualmente incorreta, que a correção do vínculo `PROC-ESPACO-03 → ERR-13` havia sido aplicada antes de sua redação. **(6)** Registradas duas remissões pendentes a documentos inexistentes: "Especificação Técnica" (§5, G-CONF-04) e "Plano de Validação" (§12, regra 5, G-CONF-13, **novo**). **(7)** Declarada a geração `G3` de todos os IDs citados (preâmbulo e §12, regra 1). **(8)** §11: declarado o estatuto de convenção provisória das duas regras de desempate de fronteira, conforme as três condições de GOV-1.0 §1.3 (G-CONF-06). **(9)** §10: acrescentado item de checklist sobre declaração da versão da ontologia. **(10)** §13 criada para registrar itens deferidos.|

| `TX-2026-08-17T174627Z-manual-v1.2` | 2026-08-17T17:46:27Z | I — Correção de Fidelidade, com itens de Classe II | **(1)** D-1 resolvido: vocabulário de papel passa a `nuclear` / `secundario` (§1, §5, §9), conforme Especificação do Error Trace §7. Mudança de rótulo, não de semântica; limiares 0.7/0.3 intactos; anotações anteriores permanecem válidas. **(2)** D-2 resolvido: remissão a "Especificação Técnica" fechada — a regra de peso é o §5, citado nominalmente pelo Schema 2.2 e pela Especificação do Error Trace. `G-CONF-04` fechado quanto à regra de peso. **(3)** D-3 resolvido: criada a §13, Registro de Observação de Campo, alinhada ao bloco `incerteza` do Schema 2.2. **(4)** Antigas §13 e §14 renumeradas para §14 e §15 — ambas introduzidas na v1.1 e não citadas por nenhum documento externo; as seções §1 a §12, que são citadas externamente, permanecem intactas. **(5)** Acrescentado `D-5` (remissão a "Plano de Validação", `G-CONF-13`). **(6)** `compativel_com` estendido a `item_schema` e `error_trace`. |

Nenhum Domínio, Processo, Competência, Habilidade, Tipo de Erro ou Intervenção foi criado, removido ou reorganizado. Nenhuma seção de 1 a 12 foi renumerada em nenhuma das versões acima.

---

_Fim do documento._