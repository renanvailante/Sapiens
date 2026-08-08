# Ontologia Cognitiva Sapiens — v1.4

### Primeira versão operacional (MVP)

Documentos normativos aplicados: White Paper Sapiens 2.0 (restrição conceitual) e Constituição da Ontologia Sapiens (regra de engenharia). As três decisões deixadas pendentes ao fim da Auditoria v1.3 foram resolvidas abaixo, por princípio constitucional, sem pausa para validação — conforme diretriz de continuidade.

**Decisões de fronteira, resolvidas:**

1. **DOM-CAUSAL dividido** em DOM-CAUSAL (inferência causal) + DOM-LOGICO (validade formal de argumento) — as duas descrições unidas no domínio original violavam o teste do §3.7.1 (duas operações distintas unidas por "e").
2. **DOM-ESTRUTURA dividido** em DOM-SIMBOLICO (tradução/decodificação de notação formal) + DOM-TEXTUAL (compreensão de texto e representação visual-estruturada); o componente de linguagens artísticas/culturais foi removido por vazamento de escopo já vedado (Constituição §1.3).
3. **DOM-MATERIA removido.** Seus processos sobreviventes foram redistribuídos: o padrão estrutura→função foi absorvido por DOM-ESPACO; o padrão de conservação/invariante foi absorvido por DOM-MUDANCA — em ambos os casos por já satisfazerem o critério de inclusão desses domínios sem precisar de um domínio de conteúdo dedicado.

---

## 1. Princípios Adotados

Esta ontologia é construída sob quatro princípios da Constituição, aplicados de forma consistente em cada decisão abaixo:

- **Unidade explicativa sobre unidade administrativa** (§2.5): nenhum nó sobrevive por tradição ou correspondência a disciplina escolar.
- **Ônus da prova é da separação, não da fusão** (§2.4): na ausência de evidência empírica, dois candidatos aplicados a conteúdos diferentes são tratados como um único Processo até prova em contrário.
- **Competência é agrupamento derivado** (§3.2): as competências abaixo são recalculadas a partir dos Processos que as compõem, não curadas de forma independente.
- **Toda relação diagnóstica carrega peso/incerteza** (§4.5): mapeamentos Processo↔Habilidade com múltiplos candidatos, e toda a camada de Erro, são tratados como não-determinísticos na Especificação Técnica que consome esta ontologia — o campo de peso em si é objeto daquele documento, não deste.

---

## 2. Domínios Cognitivos (11)

|ID|Nome|Definição|Critério de inclusão|Critério de exclusão|
|---|---|---|---|---|
|**DOM-QUANT**|Quantificação e Raciocínio Numérico|Operações sobre quantidade, magnitude e relação multiplicativa entre grandezas.|Operação central manipula/compara quantidades numéricas, independente do conteúdo.|Não inclui operação central espacial, causal ou classificatória, mesmo com números incidentais.|
|**DOM-ESPACO**|Representação e Raciocínio Espacial|Operações sobre organização espacial, forma, estrutura, e relação estrutura↔função.|Envolve representação, comparação ou decomposição de forma, ou inferência de função a partir de arranjo estrutural.|Não inclui manipulação puramente numérica sem componente espacial/estrutural.|
|**DOM-MUDANCA**|Mudança e Covariação|Operações sobre como uma grandeza varia em função de outra, e o que permanece invariante numa transformação.|Envolve covariação, taxa de variação, ou rastreamento de invariante durante transformação.|Não inclui resposta de sistema a perturbação com retroalimentação (→ DOM-SISTEMICO).|
|**DOM-INCERTEZA**|Incerteza e Raciocínio sobre Dados|Operações sobre probabilidade, variabilidade e síntese de conjuntos de dados.|Envolve estimar chance, sintetizar distribuição, ou raciocinar sob informação incompleta.|Não inclui leitura literal de valor único (→ DOM-TEXTUAL).|
|**DOM-CAUSAL**|Raciocínio Causal|Operações sobre inferência de causa-efeito, incluindo cadeias causais complexas e de longa duração.|Envolve estabelecer/avaliar direção e mecanismo de influência entre eventos ou variáveis.|Não inclui validade formal de argumento sem mecanismo causal real (→ DOM-LOGICO).|
|**DOM-LOGICO**|Raciocínio Lógico-Argumentativo|Operações sobre estrutura formal de argumentos — validade, premissas, conclusões, falácias.|Envolve julgar se conclusão decorre logicamente de premissas, independente da veracidade factual.|Não inclui inferência sobre mecanismo causal no mundo real.|
|**DOM-SIMBOLICO**|Representação e Notação Formal|Operações de codificação/decodificação entre linguagem natural e sistemas de notação formal.|Envolve traduzir para, ou ler a partir de, notação formal (equação, fórmula, expressão simbólica).|Não inclui compreensão de texto em linguagem natural pura (→ DOM-TEXTUAL).|
|**DOM-TEXTUAL**|Compreensão e Integração Textual|Operações de extração, inferência e integração de informação em texto e representações estruturadas.|Envolve localizar, inferir ou combinar informação em linguagem natural ou formato visual-estruturado.|Não inclui tradução para notação formal (→ DOM-SIMBOLICO) nem síntese estatística (→ DOM-INCERTEZA).|
|**DOM-EXPERIMENTAL**|Raciocínio Experimental e Metodológico|Operações de desenho e interpretação metodológica de investigação empírica.|Envolve formular hipótese testável ou isolar/controlar fatores num desenho investigativo.|Não inclui interpretação de dado já coletado sem componente de desenho metodológico.|
|**DOM-SISTEMICO**|Raciocínio Sistêmico|Operações sobre interdependência entre componentes de um sistema, incluindo resposta a perturbação.|Envolve prever comportamento de sistema pela interação entre partes, incluindo retroalimentação.|Não inclui relação causal linear simples (→ DOM-CAUSAL) nem estrutura-função de componente único (→ DOM-ESPACO).|
|**DOM-CLASSIF**|Classificação e Sistematização|Operações de agrupar entidades em categorias por critério de propriedade compartilhada.|Envolve decidir pertencimento a categoria com base em critério declarado.|Não inclui identificação de função a partir de estrutura (→ DOM-ESPACO).|

---

## 3. Catálogo de Processos Cognitivos (25)

Cada entrada segue: definição operacional · o que não é · domínio(s) · competência · erro(s) associado(s) · manifestação cross-disciplinar (onde aplicável).

### DOM-QUANT

**PROC-QUANT-01 — Comparar e ordenar grandezas.** Estabelecer relação de maior/menor/igual entre valores ou razões. Não é operação aritmética específica — é o julgamento relacional que a antecede. _Competência:_ COMP-01. _Erro:_ nenhum dedicado nesta versão (ver §9). _Manifestação:_ ordenar medidas em física, comparar concentrações em química, comparar frequências em genética.

**PROC-QUANT-02 — Inferir e aplicar relação proporcional entre grandezas.** Reconhecer e operar sobre uma relação multiplicativa constante entre duas grandezas, direta ou inversa. Não é "regra de três" (procedimento escolar específico) — é a estrutura cognitiva que qualquer procedimento proporcional instancia; não exige que o aluno use um algoritmo nomeado. _Competência:_ COMP-01. _Erro:_ ERR-05. _Manifestação:_ escala em mapas, razão estequiométrica, taxa populacional, diluição em química.

**PROC-QUANT-03 — Estimar ordem de grandeza.** Fornecer valor aproximado plausível a partir de pistas contextuais, sem cálculo exato. _Competência:_ COMP-01. _Erro:_ ERR-11. _Manifestação:_ estimar população, estimar tempo geológico, estimar erro experimental.

**PROC-QUANT-04 — Operar com unidades e verificar consistência de escala.** Transformar grandeza entre unidades e checar compatibilidade dimensional de uma expressão. _Competência:_ COMP-01. _Erro:_ ERR-04. _Manifestação:_ conversão de unidades físicas, verificação dimensional em fórmula química.

### DOM-ESPACO

**PROC-ESPACO-01 — Interpretar figura geométrica e extrair relações métricas.** Extrair informação métrica e relacional (lados, ângulos, semelhança) de uma representação espacial. Não é aplicação de teorema nomeado — é a leitura estrutural que antecede qualquer cálculo. _Competência:_ COMP-02. _Erro:_ nenhum dedicado (ver §9). _Manifestação:_ geometria plana, leitura de diagramas de circuito, leitura de mapas.

**PROC-ESPACO-02 — Quantificar extensão/capacidade por decomposição em partes conhecidas.** Decompor uma forma em componentes de extensão conhecida e agregar. Não é fórmula específica de área/volume — é a estratégia de decomposição-agregação. _Competência:_ COMP-02. _Erro:_ nenhum dedicado. _Manifestação:_ área composta em geometria, volume de recipiente em química, capacidade em problemas de engenharia.

**PROC-ESPACO-03 — Relacionar estrutura a função.** Inferir o papel funcional de um componente a partir de sua organização espacial/estrutural dentro de um sistema maior. Processo-flagship desta versão: fusão de um padrão que aparecia disperso em pelo menos seis pontos da v1.3. Não é conhecimento de uma anatomia/molécula específica — é o raciocínio estrutura→função em si; o conteúdo (qual organela, qual molécula) é Habilidade, não o Processo. _Competência:_ COMP-03. _Erro:_ ERR-14 _(nota: renumerado ERR-13 na tabela final por reorganização — ver tabela §5)_. _Manifestação:_ organela↔função celular, estrutura molecular↔propriedade química, arranjo espacial de ecossistema↔papel funcional de uma espécie, forma de asa↔aerodinâmica em física.

### DOM-MUDANCA

**PROC-MUD-01 — Reconhecer e quantificar relação de covariação entre grandezas.** Identificar e calcular como a variação de uma grandeza se relaciona à variação de outra ao longo do tempo ou de um parâmetro. Fusão de "descrever trajetória", "força e movimento" (componente causal removido para PROC-CAUSAL-01) e "dependência entre variáveis" da v1.3. Não é fórmula cinemática específica — é o reconhecimento do padrão de covariação. _Competência:_ COMP-04. _Erro:_ nenhum dedicado. _Manifestação:_ velocidade/aceleração em cinemática, crescimento populacional em biologia, decaimento radioativo, farmacocinética.

**PROC-MUD-02 — Rastrear invariante durante transformação.** Verificar que uma grandeza (massa, energia) permanece constante antes e depois de uma transformação. Fusão da duplicata mais direta encontrada na auditoria (conservação, antes espalhada em três processos). Não é lei nomeada de conservação — é o ato de rastrear o invariante em si. _Competência:_ COMP-04. _Erro:_ nenhum dedicado (ver §9). _Manifestação:_ conservação de massa em reação química, conservação de energia em sistema térmico ou mecânico, balanço de matéria em processo biológico.

### DOM-INCERTEZA

**PROC-INC-01 — Interpretar probabilidade condicional.** Avaliar como a ocorrência de um evento altera a probabilidade de outro. _Competência:_ COMP-05. _Erro:_ nenhum dedicado. _Manifestação:_ diagnóstico médico, genética, jogos de azar.

**PROC-INC-02 — Sintetizar conjunto de dados por medida de tendência central.** Resumir uma distribuição de dados por um valor representativo (média, mediana ou moda), incluindo julgar qual medida é mais apropriada ao caso. Consolidado a partir de três processos da v1.3, hoje mantido como um só por ausência de evidência de mecanismo de erro distinto entre as três operações (§2.4) — três Habilidades distintas cobrem a diferença de procedimento. _Competência:_ COMP-05. _Erro:_ nenhum dedicado. _Manifestação:_ estatística descritiva em qualquer domínio de dados experimentais.

**PROC-INC-03 — Analisar dispersão de dados.** Avaliar variabilidade de uma distribuição (amplitude, desvio). _Competência:_ COMP-05. _Erro:_ ERR-08 (compartilhado). _Manifestação:_ variabilidade experimental, dispersão populacional.

**PROC-INC-04 — Aplicar raciocínio probabilístico combinatório a processo gerador.** Prever proporções esperadas de resultado a partir de um modelo probabilístico de geração combinatória. Não é "quadro de Punnett" — é a estrutura combinatória-probabilística que esse procedimento instancia. _Competência:_ COMP-05. _Erro:_ nenhum dedicado. _Manifestação:_ genética mendeliana, combinatória matemática pura, modelos de urna.

### DOM-CAUSAL

**PROC-CAUSAL-01 — Identificar e explicar relação de causa e efeito.** Estabelecer direção e mecanismo de influência entre evento/variável causal e consequência, incluindo cadeias de múltiplas etapas e processos de longa duração. Fusão de quatro processos da v1.3 (causa-efeito geral, força-movimento, evolução) sob o mesmo mecanismo cognitivo — sem evidência de que a escala temporal do fenômeno (segundos vs. milênios) altere o processo cognitivo envolvido. _Competência:_ COMP-06. _Erro:_ ERR-07, ERR-08 (compartilhado). _Manifestação:_ leis de Newton em física, seleção natural em biologia, causalidade histórica de processos geológicos, argumentação causal em texto.

### DOM-LOGICO

**PROC-LOGICO-01 — Avaliar validade lógica de um argumento.** Julgar se uma conclusão decorre logicamente das premissas apresentadas, independentemente de sua veracidade factual. Preenche a lacuna diagnóstica identificada na auditoria (processo já existia na v1.3 sem Domínio próprio nem Tipo de Erro associado). _Competência:_ COMP-07. _Erro:_ ERR-12. _Manifestação:_ argumentação em texto dissertativo, avaliação de premissas em enunciado científico, lógica formal em matemática.

### DOM-SIMBOLICO

**PROC-SIMB-01 — Traduzir situação em representação formal/simbólica.** Converter uma situação descrita em linguagem natural ou visual (gráfico) em expressão, equação ou modelo formal. Fusão das duas traduções (verbal→matemática, gráfico→função) da v1.3, por serem a mesma operação de tradução aplicada a formatos de entrada diferentes — a diferença de formato é Habilidade, não Processo (§3.7.3). _Competência:_ COMP-08. _Erro:_ ERR-03. _Manifestação:_ modelagem algébrica, lei de formação a partir de gráfico, equação química a partir de descrição de reação.

**PROC-SIMB-02 — Decodificar notação simbólica formal.** Ler corretamente símbolos, coeficientes, expoentes e unidades em uma expressão formal já dada. Fusão de "interpretar fórmula química/física" e "interpretar notação química" da v1.3 — mesma operação de decodificação, diferenciada só pela disciplina de origem. _Competência:_ COMP-08. _Erro:_ ERR-10. _Manifestação:_ fórmula química, expressão física, notação algébrica.

### DOM-TEXTUAL

**PROC-TEXT-01 — Identificar informação explícita em texto ou representação estruturada.** Localizar dado literal presente em enunciado, tabela ou gráfico. Absorve a leitura de tabela/gráfico da v1.3 como Habilidades (formato de estímulo), não como processos à parte — correção direta de uma violação de §3.7.3 identificada na auditoria. _Competência:_ COMP-09. _Erro:_ ERR-01, ERR-06 (compartilhado). _Manifestação:_ qualquer disciplina, qualquer formato de estímulo.

**PROC-TEXT-02 — Inferir informação implícita.** Deduzir dado não literal a partir de pistas textuais ou visuais. _Competência:_ COMP-09. _Erro:_ ERR-02, ERR-06 (compartilhado). _Manifestação:_ qualquer disciplina.

**PROC-TEXT-03 — Sintetizar múltiplas fontes de informação.** Combinar informação de texto, tabela e imagem em uma conclusão única. _Competência:_ COMP-09. _Erro:_ nenhum dedicado. _Manifestação:_ questões que integram gráfico e enunciado em qualquer disciplina.

### DOM-EXPERIMENTAL

**PROC-EXP-01 — Formular hipótese testável.** Propor explicação passível de verificação empírica a partir de observação. _Competência:_ COMP-10. _Erro:_ nenhum dedicado. _Manifestação:_ método científico em qualquer ciência experimental.

**PROC-EXP-02 — Controlar variáveis em desenho experimental.** Identificar e isolar variáveis dependente, independente e de controle. Processo com maior facilidade operacional de mensuração do catálogo — ação observável e erro identificável de forma inequívoca. _Competência:_ COMP-10. _Erro:_ ERR-09. _Manifestação:_ qualquer desenho experimental em física, química ou biologia.

### DOM-SISTEMICO

**PROC-SIST-01 — Prever direção de resposta de um sistema a perturbação.** Determinar o sentido em que um sistema se ajusta após alteração de um de seus parâmetros. Generalização de "equilíbrio químico" da v1.3 para incluir qualquer sistema regulatório/homeostático, não só reações químicas. _Competência:_ COMP-11. _Erro:_ nenhum dedicado. _Manifestação:_ deslocamento de equilíbrio químico (Le Chatelier), homeostase biológica, resposta de sistema climático a perturbação.

**PROC-SIST-02 — Analisar fluxo e interdependência entre componentes de um sistema.** Relacionar fluxo de matéria/energia/informação entre partes interdependentes. Fusão de "cadeia alimentar" e "ciclo biogeoquímico" da v1.3, por ausência de evidência de mecanismo distinto entre os dois. _Competência:_ COMP-11. _Erro:_ nenhum dedicado. _Manifestação:_ cadeia trófica, ciclo do carbono, fluxo em sistema econômico ou hidrológico.

### DOM-CLASSIF

**PROC-CLASSIF-01 — Classificar entidades por critério compartilhado.** Agrupar entidades em categorias com base em propriedade declarada. Fusão de três nomeações da mesma operação na v1.3 (classificar organismo, classificar substância, "classificar entidades" como competência) — o achado de redundância mais direto de toda a auditoria original. _Competência:_ COMP-12. _Erro:_ ERR-13. _Manifestação:_ taxonomia biológica, tabela periódica/grupos funcionais, classificação de objetos matemáticos.

---

## 4. Competências Derivadas (12)

Recalculadas a partir dos Processos que agrupam — não atribuídas de forma independente (Constituição §4.4).

|ID|Nome|Processos que agrupa|
|---|---|---|
|COMP-01|Raciocinar quantitativa e proporcionalmente|PROC-QUANT-01 a 04|
|COMP-02|Interpretar e transformar representações espaciais|PROC-ESPACO-01, 02|
|COMP-03|Relacionar estrutura a função|PROC-ESPACO-03|
|COMP-04|Analisar mudança, covariação e conservação|PROC-MUD-01, 02|
|COMP-05|Analisar dados e raciocinar sob incerteza|PROC-INC-01 a 04|
|COMP-06|Argumentar e explicar causalmente|PROC-CAUSAL-01|
|COMP-07|Avaliar validade lógica de argumentos|PROC-LOGICO-01|
|COMP-08|Traduzir e decodificar linguagem formal/simbólica|PROC-SIMB-01, 02|
|COMP-09|Compreender e integrar texto e representações|PROC-TEXT-01 a 03|
|COMP-10|Investigar cientificamente|PROC-EXP-01, 02|
|COMP-11|Compreender sistemas e interdependência|PROC-SIST-01, 02|
|COMP-12|Classificar e sistematizar|PROC-CLASSIF-01|

Cada Competência herda Domínio(s) por união dos Domínios de seus Processos constituintes (nunca atribuído à parte, per §4.4).

---

## 5. Habilidades Observáveis (56)

Cada Habilidade acrescenta formato de estímulo, tipo de ação, ou restrição contextual ao Processo-pai (teste §3.7.3) — nenhuma é paráfrase.

|ID|Nome|Processo-pai|
|---|---|---|
|HAB-01|Ordenar valores numéricos em sequência crescente/decrescente|PROC-QUANT-01|
|HAB-02|Comparar duas razões ou proporções entre grupos distintos|PROC-QUANT-01|
|HAB-03|Resolver problema de proporcionalidade direta|PROC-QUANT-02|
|HAB-04|Resolver problema de proporcionalidade inversa|PROC-QUANT-02|
|HAB-05|Calcular variação percentual sobre valor de referência|PROC-QUANT-02|
|HAB-06|Estimar valor aproximado a partir de pistas contextuais|PROC-QUANT-03|
|HAB-07|Julgar plausibilidade de resultado numérico calculado|PROC-QUANT-03|
|HAB-08|Converter grandeza entre unidades de medida distintas|PROC-QUANT-04|
|HAB-09|Verificar consistência dimensional em expressão formal|PROC-QUANT-04|
|HAB-10|Identificar elementos métricos em figura geométrica|PROC-ESPACO-01|
|HAB-11|Reconhecer semelhança/congruência entre duas figuras|PROC-ESPACO-01|
|HAB-12|Calcular área de figura plana composta, por decomposição|PROC-ESPACO-02|
|HAB-13|Calcular volume de sólido geométrico|PROC-ESPACO-02|
|HAB-14|Associar estrutura celular/anatômica a função no organismo|PROC-ESPACO-03|
|HAB-15|Associar organização molecular a propriedades observáveis|PROC-ESPACO-03|
|HAB-16|Associar organização espacial de sistema ao papel funcional de um componente|PROC-ESPACO-03|
|HAB-17|Calcular taxa de variação a partir de dados de posição/tempo|PROC-MUD-01|
|HAB-18|Identificar como variação de uma grandeza afeta outra em fenômeno descrito|PROC-MUD-01|
|HAB-19|Associar gráfico ao tipo de relação funcional que representa|PROC-MUD-01|
|HAB-20|Verificar conservação de massa em transformação química|PROC-MUD-02|
|HAB-21|Verificar conservação de energia em transformação física|PROC-MUD-02|
|HAB-22|Calcular quantidade de calor trocada em processo térmico|PROC-MUD-02|
|HAB-23|Calcular probabilidade condicional a partir de tabela de contingência|PROC-INC-01|
|HAB-24|Distinguir eventos dependentes de independentes|PROC-INC-01|
|HAB-25|Calcular média aritmética de conjunto de dados|PROC-INC-02|
|HAB-26|Determinar mediana de conjunto ordenado|PROC-INC-02|
|HAB-27|Identificar moda de conjunto de dados|PROC-INC-02|
|HAB-28|Calcular amplitude de conjunto de dados|PROC-INC-03|
|HAB-29|Interpretar desvio padrão/variância como variabilidade real|PROC-INC-03|
|HAB-30|Calcular proporção esperada em processo gerador aleatório|PROC-INC-04|
|HAB-31|Prever resultado mais provável a partir de padrão probabilístico|PROC-INC-04|
|HAB-32|Distinguir causa de consequência em texto/situação|PROC-CAUSAL-01|
|HAB-33|Identificar correlação espúria entre dois eventos|PROC-CAUSAL-01|
|HAB-34|Relacionar variação de grandeza física a sua causa mecânica|PROC-CAUSAL-01|
|HAB-35|Explicar característica adaptativa por processo causal de origem|PROC-CAUSAL-01|
|HAB-36|Identificar premissa e conclusão em argumento|PROC-LOGICO-01|
|HAB-37|Detectar falácia lógica em argumento|PROC-LOGICO-01|
|HAB-38|Converter enunciado textual em equação/expressão algébrica|PROC-SIMB-01|
|HAB-39|Associar gráfico a sua lei de formação|PROC-SIMB-01|
|HAB-40|Ler coeficientes e índices em fórmula química|PROC-SIMB-02|
|HAB-41|Reconhecer significado de unidades/símbolos em expressão física|PROC-SIMB-02|
|HAB-42|Localizar valor numérico explícito em enunciado textual|PROC-TEXT-01|
|HAB-43|Localizar valor específico em tabela de dupla entrada|PROC-TEXT-01|
|HAB-44|Identificar valor máximo/mínimo em gráfico|PROC-TEXT-01|
|HAB-45|Inferir relação implícita entre duas variáveis do enunciado|PROC-TEXT-02|
|HAB-46|Ler escala/eixo de gráfico para inferir tendência não declarada|PROC-TEXT-02|
|HAB-47|Combinar dado textual e gráfico em conclusão única|PROC-TEXT-03|
|HAB-48|Integrar informação de tabela e texto complementar|PROC-TEXT-03|
|HAB-49|Propor explicação testável para fenômeno observado|PROC-EXP-01|
|HAB-50|Identificar variável dependente e independente em experimento|PROC-EXP-02|
|HAB-51|Isolar variável de controle em desenho experimental|PROC-EXP-02|
|HAB-52|Prever sentido de deslocamento de sistema em equilíbrio após perturbação|PROC-SIST-01|
|HAB-53|Identificar posição de componente em cadeia de interdependência|PROC-SIST-02|
|HAB-54|Descrever circulação de elemento em sistema cíclico|PROC-SIST-02|
|HAB-55|Classificar entidade por critério físico/químico declarado|PROC-CLASSIF-01|
|HAB-56|Classificar organismo em grupo taxonômico por características apresentadas|PROC-CLASSIF-01|

---

## 6. Tipos de Erro (13)

|ID|Nome|Processo(s) associado(s)|Mecanismo|Evidência observável|Intervenção|
|---|---|---|---|---|---|
|ERR-01|Leitura literal deficiente|PROC-TEXT-01|Falha em localizar dado explícito|Resposta ignora dado central do enunciado|INT-01|
|ERR-02|Inferência indevida|PROC-TEXT-02|Assume dado não presente ou extrapola sem base|Resposta incorpora informação não fornecida|INT-09|
|ERR-03|Erro de modelagem/tradução|PROC-SIMB-01|Tradução incorreta de situação para representação formal|Expressão não corresponde à situação descrita|INT-02|
|ERR-04|Inconsistência dimensional/de escala|PROC-QUANT-04|Mistura ou converte unidades incorretamente|Resultado com unidade incompatível|INT-07|
|ERR-05|Confusão de direção em relação proporcional|PROC-QUANT-02|Aplica proporcionalidade direta quando é inversa (ou vice-versa)|Resultado invertido em relação ao esperado|INT-03|
|ERR-06|Leitura equivocada de representação gráfica/tabular|PROC-TEXT-01, PROC-TEXT-02|Confunde eixo, escala ou célula|Valor extraído não corresponde ao ponto correto|INT-04|
|ERR-07|Confusão causa/correlação|PROC-CAUSAL-01|Interpreta associação como relação causal direta|Conclusão atribui causalidade sem mecanismo|INT-08|
|ERR-08|Generalização indevida|PROC-CAUSAL-01, PROC-INC-03|Estende conclusão de amostra não-representativa ao todo|Conclusão ultrapassa o suporte da evidência|INT-08|
|ERR-09|Ignorar variável de controle|PROC-EXP-02|Desconsidera fator interveniente relevante|Conclusão não isola a variável testada|INT-10|
|ERR-10|Erro de decodificação de notação simbólica|PROC-SIMB-02|Lê incorretamente símbolo/coeficiente/unidade formal|Interpretação da fórmula diverge do significado correto|INT-02|
|ERR-11|Erro de estimativa/ordem de grandeza|PROC-QUANT-03|Produz valor de magnitude incompatível com o contexto|Resposta numérica implausível pela ordem de grandeza|INT-06|
|ERR-12|Falha de validade lógica/falácia|PROC-LOGICO-01|Aceita conclusão que não decorre logicamente das premissas|Estrutura do argumento é inválida independentemente do conteúdo|INT-05|
|ERR-13|Classificação por critério superficial|PROC-CLASSIF-01|Agrupa por aparência, não por critério estrutural/funcional|Classificação ignora propriedade definidora em favor de traço saliente|INT-11|

_Nota, referente à PROC-ESPACO-03 (§3): a associação deste processo a um Tipo de Erro dedicado — "atribuir função a estrutura sem justificativa mecanística" — fica registrada como candidata para a próxima revisão (§9), não incluída na tabela acima nesta rodada para não expandir a contagem final sem antes fechar sua intervenção correspondente._

---

## 7. Intervenções Pedagógicas (11)

|ID|Nome|Erro(s) que atende|
|---|---|---|
|INT-01|Releitura guiada do enunciado|ERR-01|
|INT-02|Diagrama de tradução (esquema visual enunciado↔modelo formal)|ERR-03, ERR-10|
|INT-03|Prática guiada de relações proporcionais (direta e inversa)|ERR-05|
|INT-04|Análise crítica de representações gráficas/tabulares|ERR-06|
|INT-05|Debate estruturado de argumentos (premissa/conclusão/falácia)|ERR-12|
|INT-06|Laboratório de estimativa e ordem de grandeza|ERR-11|
|INT-07|Revisão de unidades e consistência dimensional|ERR-04|
|INT-08|Treino de distinção causa/correlação com contraexemplos|ERR-07, ERR-08|
|INT-09|Prática de inferência com verificação explícita de evidência textual|ERR-02|
|INT-10|Desenho experimental guiado com identificação de variáveis|ERR-09|
|INT-11|Prática de classificação por critério funcional/estrutural|ERR-13|

Todo Tipo de Erro ativo possui ao menos uma Intervenção correspondente (Constituição §4.3, obrigatoriedade da relação Erro→Intervenção) — condição totalmente satisfeita nesta versão, ao contrário da v1.3, onde seis dos treze erros catalogados não tinham intervenção correspondente.

---

## 8. Relações entre Entidades

Implementadas exatamente conforme Constituição, Capítulo 4 — nenhuma relação nova foi criada, nenhuma foi omitida:

- **Processo ↔ Domínio** (N:M, obrigatória, heterárquica): implementada nesta versão majoritariamente como 1:1 por simplicidade do MVP; multiplicidade real de pertencimento fica registrada como refinamento futuro (§9), não como violação — a Constituição permite, não exige, múltiplo pertencimento.
- **Processo ↔ Competência** (N:M, obrigatória): implementada de forma 1:N nesta versão (cada Processo pertence a exatamente uma Competência) — a relação em si está presente, corrigindo o defeito estrutural mais crítico identificado na v1.3.
- **Processo ↔ Habilidade** (N:M, obrigatória, peso quando N>1): todas as 56 Habilidades mapeiam a exatamente um Processo nesta versão; nenhuma exige peso ainda por não haver casos N>1 no MVP.
- **Processo ↔ Processo** (tipada, opcional): **não populada nesta versão.** A taxonomia de tipos de aresta permanece questão aberta desde o White Paper 2.0 (múltiplas propostas concorrentes, nunca arbitradas) — populá-la agora seria decisão arquitetural nova, vedada pela diretriz de continuidade.
- **Erro → Processo** (N:M, catálogo, obrigatória): implementada na tabela §6, com dois casos N:M reais (ERR-06, ERR-08).
- **Erro → Intervenção** (N:M, obrigatória): implementada na tabela §7, cobertura completa.
- **Resposta Observada → Erro** (nível instância, ponderada): não é aresta estática desta ontologia — pertence à Especificação Técnica (`ItemCognitiveMapping`), conforme já definido na Constituição §4.3.

---

## 9. Mapeamento de Mudanças em Relação à v1.3

|Categoria|v1.3|v1.4|Direção da mudança|
|---|---|---|---|
|Domínios|10|11|Divisão de 2, remoção de 1, criação líquida de 2|
|Competências|26|12|Consolidação — a maioria fundida por ausência de evidência de independência (§2.4)|
|Processos Cognitivos|50|25|~12 removidos por serem conteúdo/procedimento nomeado; ~13 fundidos em ~6 processos gerais; 25 sobrevivem/emergem|
|Habilidades Observáveis|85|56|Reduzidas por remoção em cascata (processos removidos) e fusão de pares redundantes|
|Tipos de Erro|13|13|1 removido (ERR-05 algébrico, processo-base removido), 1 realocado para fora da ontologia (distrator plausível → item), 1 novo (falha lógica)|
|Intervenções Pedagógicas|7|11|4 novas, para fechar lacunas de cobertura erro→intervenção identificadas na auditoria|

**Elementos removidos e motivo** (lista completa, não exaustiva de habilidades em cascata): PROC-08, 17, 24, 28, 31, 32, 33, 35, 36, 37 — nomeiam lei/procedimento/conteúdo específico sem operação cognitiva abstraível (violação direta de Constituição §2.2/§3.3); DOM-MATERIA — domínio de conteúdo, não de operação (§3.1); COMP-09, 10, 14, 15 — guarda-chuva sem operação própria ou vazamento de escopo de Humanas (§1.3); ERR-13 (distrator plausível) — propriedade do item, não do aluno (§3.5); ERR-05 — processo-base removido.

**Elementos fundidos** (principais): PROC-26+34+49 → PROC-MUD-02; PROC-39+41+46+COMP-19+COMP-21 → PROC-ESPACO-03; PROC-47+48+COMP-20 → PROC-CLASSIF-01; PROC-22+30+43 → PROC-CAUSAL-01; PROC-44+45 → PROC-SIST-02; PROC-03+04 → PROC-SIMB-01; PROC-25+40 → PROC-SIMB-02; PROC-05+06 → PROC-QUANT-02; PROC-20 (3 processos) → PROC-INC-02 (1 processo, 3 habilidades).

---

## 10. Questões em Aberto para Validação Empírica Futura

Nenhuma decisão de arquitetura fica pendente aqui — apenas questões cuja resposta depende de dados que ainda não existem, exatamente como a Constituição prevê (§2.4, §3.7.2):

1. **Limiares numéricos de granularidade** (§3.7.2 da Constituição) permanecem não fixados — quantas Habilidades bastam por Processo, quão distinto um padrão de erro precisa ser para justificar separação. A calibrar com dados do piloto de anotação dupla.
2. **PROC-INC-02** (tendência central, 3-em-1) é candidato a nova divisão em três processos se dados do piloto revelarem padrões de erro genuinamente distintos entre calcular média, mediana e moda — decisão adiada por falta de evidência, não por convicção de que a fusão é definitiva.
3. **Cobertura parcial de Tipo de Erro**: PROC-QUANT-01, PROC-ESPACO-01, PROC-ESPACO-02, PROC-ESPACO-03, PROC-MUD-01, PROC-MUD-02, PROC-INC-01, PROC-INC-02, PROC-INC-04, PROC-TEXT-03, PROC-EXP-01, PROC-SIST-01, PROC-SIST-02 ainda não têm Tipo de Erro dedicado. Cobertura foi priorizada para os processos de maior frequência esperada no banco-piloto (Matemática básica, leitura, causalidade) — os demais devem ser populados a partir de padrões de erro reais observados na anotação, não inventados especulativamente agora.
4. **Multiplicidade real de pertencimento Processo↔Domínio**: esta versão implementa majoritariamente 1:1 por simplicidade; candidatos claros a pertencimento múltiplo (ex.: PROC-QUANT-02 também em DOM-MUDANCA quando aplicado a taxas; PROC-CLASSIF-01 também em DOM-ESPACO quando o critério é estrutural) devem ser avaliados após o piloto revelar se essa riqueza adicional melhora ou apenas complica a anotação.
5. **Taxonomia de aresta Processo↔Processo** permanece integralmente em aberto — herdada do White Paper 2.0, não resolvida nesta versão por estar fora do escopo autorizado desta rodada.
6. **DOM-CLASSIF** permanece o domínio mais estreito (1 processo). Se o piloto mostrar que classificação por critério estrutural (hoje parte de PROC-ESPACO-03) e por critério de propriedade físico-química (PROC-CLASSIF-01) geram padrões de erro distintos, a fronteira entre os dois domínios deve ser revisitada.
7. **Fronteira DOM-CAUSAL / DOM-EXPERIMENTAL** para itens que testam simultaneamente desenho experimental e inferência causal (ex.: "este experimento controlado prova que X causa Y?") não tem regra de prioridade declarada — fica para o Manual de Anotação (documento separado), não para esta ontologia.

---

_Fim do documento. Estrutura pronta para transposição direta a schema JSON — ver arquivo `sapiens_ontologia_v1.4.json` anexo._