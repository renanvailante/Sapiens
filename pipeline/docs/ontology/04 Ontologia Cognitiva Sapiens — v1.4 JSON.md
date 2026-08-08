  

## Sapiens ontologia v1.4 · JSON

`{`

`"version": "1.4",`

`"name": "Ontologia Cognitiva Sapiens (Matematica + Ciencias da Natureza) - v1.4",`

`"description": "Primeira versao operacional (MVP), reconstruida a partir da auditoria da v1.3, sob a Constituicao da Ontologia Sapiens e o White Paper 2.0. Corrige: elo Competencia-Processo agora explicito; conflacao processo/conteudo removida; taxonomia de erro sem mistura de niveis; cobertura completa Erro->Intervencao.",`

`"dominios": [`

`{`

`"id": "DOM-QUANT",`

`"nome": "Quantificacao e Raciocinio Numerico",`

`"descricao": "Operacoes sobre quantidade, magnitude e relacao multiplicativa entre grandezas."`

`},`

`{`

`"id": "DOM-ESPACO",`

`"nome": "Representacao e Raciocinio Espacial",`

`"descricao": "Operacoes sobre organizacao espacial, forma, estrutura, e relacao estrutura-funcao."`

`},`

`{`

`"id": "DOM-MUDANCA",`

`"nome": "Mudanca e Covariacao",`

`"descricao": "Operacoes sobre como uma grandeza varia em funcao de outra, e o que permanece invariante numa transformacao."`

`},`

`{`

`"id": "DOM-INCERTEZA",`

`"nome": "Incerteza e Raciocinio sobre Dados",`

`"descricao": "Operacoes sobre probabilidade, variabilidade e sintese de conjuntos de dados."`

`},`

`{`

`"id": "DOM-CAUSAL",`

`"nome": "Raciocinio Causal",`

`"descricao": "Operacoes sobre inferencia de causa-efeito, incluindo cadeias causais complexas e de longa duracao."`

`},`

`{`

`"id": "DOM-LOGICO",`

`"nome": "Raciocinio Logico-Argumentativo",`

`"descricao": "Operacoes sobre estrutura formal de argumentos - validade, premissas, conclusoes, falacias."`

`},`

`{`

`"id": "DOM-SIMBOLICO",`

`"nome": "Representacao e Notacao Formal",`

`"descricao": "Operacoes de codificacao/decodificacao entre linguagem natural e sistemas de notacao formal."`

`},`

`{`

`"id": "DOM-TEXTUAL",`

`"nome": "Compreensao e Integracao Textual",`

`"descricao": "Operacoes de extracao, inferencia e integracao de informacao em texto e representacoes estruturadas."`

`},`

`{`

`"id": "DOM-EXPERIMENTAL",`

`"nome": "Raciocinio Experimental e Metodologico",`

`"descricao": "Operacoes de desenho e interpretacao metodologica de investigacao empirica."`

`},`

`{`

`"id": "DOM-SISTEMICO",`

`"nome": "Raciocinio Sistemico",`

`"descricao": "Operacoes sobre interdependencia entre componentes de um sistema, incluindo resposta a perturbacao."`

`},`

`{`

`"id": "DOM-CLASSIF",`

`"nome": "Classificacao e Sistematizacao",`

`"descricao": "Operacoes de agrupar entidades em categorias por criterio de propriedade compartilhada."`

`}`

`],`

`"processos_cognitivos": [`

`{`

`"id": "PROC-QUANT-01",`

`"nome": "Comparar e ordenar grandezas",`

`"definicao_operacional": "Estabelecer relacao de maior/menor/igual entre valores ou razoes.",`

`"dominios": [`

`"DOM-QUANT"`

`],`

`"competencia": "COMP-01",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-12"`

`]`

`},`

`{`

`"id": "PROC-QUANT-02",`

`"nome": "Inferir e aplicar relacao proporcional entre grandezas",`

`"definicao_operacional": "Reconhecer e operar sobre relacao multiplicativa constante entre duas grandezas, direta ou inversa.",`

`"dominios": [`

`"DOM-QUANT"`

`],`

`"competencia": "COMP-01",`

`"tipos_erro": [`

`"ERR-05"`

`],`

`"origem_v1_3": [`

`"PROC-05",`

`"PROC-06"`

`]`

`},`

`{`

`"id": "PROC-QUANT-03",`

`"nome": "Estimar ordem de grandeza",`

`"definicao_operacional": "Fornecer valor aproximado plausivel a partir de pistas contextuais, sem calculo exato.",`

`"dominios": [`

`"DOM-QUANT"`

`],`

`"competencia": "COMP-01",`

`"tipos_erro": [`

`"ERR-11"`

`],`

`"origem_v1_3": [`

`"PROC-13"`

`]`

`},`

`{`

`"id": "PROC-QUANT-04",`

`"nome": "Operar com unidades e verificar consistencia de escala",`

`"definicao_operacional": "Transformar grandeza entre unidades e checar compatibilidade dimensional de uma expressao.",`

`"dominios": [`

`"DOM-QUANT"`

`],`

`"competencia": "COMP-01",`

`"tipos_erro": [`

`"ERR-04"`

`],`

`"origem_v1_3": [`

`"PROC-07"`

`]`

`},`

`{`

`"id": "PROC-ESPACO-01",`

`"nome": "Interpretar figura geometrica e extrair relacoes metricas",`

`"definicao_operacional": "Extrair informacao metrica e relacional (lados, angulos, semelhanca) de uma representacao espacial.",`

`"dominios": [`

`"DOM-ESPACO"`

`],`

`"competencia": "COMP-02",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-16"`

`]`

`},`

`{`

`"id": "PROC-ESPACO-02",`

`"nome": "Quantificar extensao/capacidade por decomposicao em partes conhecidas",`

`"definicao_operacional": "Decompor uma forma em componentes de extensao conhecida e agregar.",`

`"dominios": [`

`"DOM-ESPACO"`

`],`

`"competencia": "COMP-02",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-18"`

`]`

`},`

`{`

`"id": "PROC-ESPACO-03",`

`"nome": "Relacionar estrutura a funcao",`

`"definicao_operacional": "Inferir o papel funcional de um componente a partir de sua organizacao espacial/estrutural dentro de um sistema maior.",`

`"dominios": [`

`"DOM-ESPACO"`

`],`

`"competencia": "COMP-03",`

`"tipos_erro": [`

`"ERR-13"`

`],`

`"origem_v1_3": [`

`"COMP-19",`

`"COMP-21",`

`"PROC-39",`

`"PROC-41",`

`"PROC-46"`

`]`

`},`

`{`

`"id": "PROC-MUD-01",`

`"nome": "Reconhecer e quantificar relacao de covariacao entre grandezas",`

`"definicao_operacional": "Identificar e calcular como a variacao de uma grandeza se relaciona a variacao de outra ao longo do tempo ou de um parametro.",`

`"dominios": [`

`"DOM-MUDANCA"`

`],`

`"competencia": "COMP-04",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-29",`

`"PROC-50"`

`]`

`},`

`{`

`"id": "PROC-MUD-02",`

`"nome": "Rastrear invariante durante transformacao",`

`"definicao_operacional": "Verificar que uma grandeza (massa, energia) permanece constante antes e depois de uma transformacao.",`

`"dominios": [`

`"DOM-MUDANCA"`

`],`

`"competencia": "COMP-04",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-26",`

`"PROC-34",`

`"PROC-49"`

`]`

`},`

`{`

`"id": "PROC-INC-01",`

`"nome": "Interpretar probabilidade condicional",`

`"definicao_operacional": "Avaliar como a ocorrencia de um evento altera a probabilidade de outro.",`

`"dominios": [`

`"DOM-INCERTEZA"`

`],`

`"competencia": "COMP-05",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-19"`

`]`

`},`

`{`

`"id": "PROC-INC-02",`

`"nome": "Sintetizar conjunto de dados por medida de tendencia central",`

`"definicao_operacional": "Resumir uma distribuicao de dados por um valor representativo (media, mediana ou moda).",`

`"dominios": [`

`"DOM-INCERTEZA"`

`],`

`"competencia": "COMP-05",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-20"`

`]`

`},`

`{`

`"id": "PROC-INC-03",`

`"nome": "Analisar dispersao de dados",`

`"definicao_operacional": "Avaliar variabilidade de uma distribuicao (amplitude, desvio).",`

`"dominios": [`

`"DOM-INCERTEZA"`

`],`

`"competencia": "COMP-05",`

`"tipos_erro": [`

`"ERR-08"`

`],`

`"origem_v1_3": [`

`"PROC-21"`

`]`

`},`

`{`

`"id": "PROC-INC-04",`

`"nome": "Aplicar raciocinio probabilistico combinatorio a processo gerador",`

`"definicao_operacional": "Prever proporcoes esperadas de resultado a partir de um modelo probabilistico de geracao combinatoria.",`

`"dominios": [`

`"DOM-INCERTEZA"`

`],`

`"competencia": "COMP-05",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-42"`

`]`

`},`

`{`

`"id": "PROC-CAUSAL-01",`

`"nome": "Identificar e explicar relacao de causa e efeito",`

`"definicao_operacional": "Estabelecer direcao e mecanismo de influencia entre evento/variavel causal e consequencia, incluindo cadeias de multiplas etapas.",`

`"dominios": [`

`"DOM-CAUSAL"`

`],`

`"competencia": "COMP-06",`

`"tipos_erro": [`

`"ERR-07",`

`"ERR-08"`

`],`

`"origem_v1_3": [`

`"PROC-22",`

`"PROC-30",`

`"PROC-43"`

`]`

`},`

`{`

`"id": "PROC-LOGICO-01",`

`"nome": "Avaliar validade logica de um argumento",`

`"definicao_operacional": "Julgar se uma conclusao decorre logicamente das premissas apresentadas, independentemente de sua veracidade factual.",`

`"dominios": [`

`"DOM-LOGICO"`

`],`

`"competencia": "COMP-07",`

`"tipos_erro": [`

`"ERR-12"`

`],`

`"origem_v1_3": [`

`"PROC-23"`

`]`

`},`

`{`

`"id": "PROC-SIMB-01",`

`"nome": "Traduzir situacao em representacao formal/simbolica",`

`"definicao_operacional": "Converter uma situacao descrita em linguagem natural ou visual em expressao, equacao ou modelo formal.",`

`"dominios": [`

`"DOM-SIMBOLICO"`

`],`

`"competencia": "COMP-08",`

`"tipos_erro": [`

`"ERR-03"`

`],`

`"origem_v1_3": [`

`"PROC-03",`

`"PROC-04"`

`]`

`},`

`{`

`"id": "PROC-SIMB-02",`

`"nome": "Decodificar notacao simbolica formal",`

`"definicao_operacional": "Ler corretamente simbolos, coeficientes, expoentes e unidades em uma expressao formal ja dada.",`

`"dominios": [`

`"DOM-SIMBOLICO"`

`],`

`"competencia": "COMP-08",`

`"tipos_erro": [`

`"ERR-10"`

`],`

`"origem_v1_3": [`

`"PROC-25",`

`"PROC-40"`

`]`

`},`

`{`

`"id": "PROC-TEXT-01",`

`"nome": "Identificar informacao explicita em texto ou representacao estruturada",`

`"definicao_operacional": "Localizar dado literal presente em enunciado, tabela ou grafico.",`

`"dominios": [`

`"DOM-TEXTUAL"`

`],`

`"competencia": "COMP-09",`

`"tipos_erro": [`

`"ERR-01",`

`"ERR-06"`

`],`

`"origem_v1_3": [`

`"PROC-01",`

`"PROC-14",`

`"PROC-15"`

`]`

`},`

`{`

`"id": "PROC-TEXT-02",`

`"nome": "Inferir informacao implicita",`

`"definicao_operacional": "Deduzir dado nao literal a partir de pistas textuais ou visuais.",`

`"dominios": [`

`"DOM-TEXTUAL"`

`],`

`"competencia": "COMP-09",`

`"tipos_erro": [`

`"ERR-02",`

`"ERR-06"`

`],`

`"origem_v1_3": [`

`"PROC-02"`

`]`

`},`

`{`

`"id": "PROC-TEXT-03",`

`"nome": "Sintetizar multiplas fontes de informacao",`

`"definicao_operacional": "Combinar informacao de texto, tabela e imagem em uma conclusao unica.",`

`"dominios": [`

`"DOM-TEXTUAL"`

`],`

`"competencia": "COMP-09",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-27"`

`]`

`},`

`{`

`"id": "PROC-EXP-01",`

`"nome": "Formular hipotese testavel",`

`"definicao_operacional": "Propor explicacao passivel de verificacao empirica a partir de observacao.",`

`"dominios": [`

`"DOM-EXPERIMENTAL"`

`],`

`"competencia": "COMP-10",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-10"`

`]`

`},`

`{`

`"id": "PROC-EXP-02",`

`"nome": "Controlar variaveis em desenho experimental",`

`"definicao_operacional": "Identificar e isolar variaveis dependente, independente e de controle.",`

`"dominios": [`

`"DOM-EXPERIMENTAL"`

`],`

`"competencia": "COMP-10",`

`"tipos_erro": [`

`"ERR-09"`

`],`

`"origem_v1_3": [`

`"PROC-11"`

`]`

`},`

`{`

`"id": "PROC-SIST-01",`

`"nome": "Prever direcao de resposta de um sistema a perturbacao",`

`"definicao_operacional": "Determinar o sentido em que um sistema se ajusta apos alteracao de um de seus parametros.",`

`"dominios": [`

`"DOM-SISTEMICO"`

`],`

`"competencia": "COMP-11",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-38"`

`]`

`},`

`{`

`"id": "PROC-SIST-02",`

`"nome": "Analisar fluxo e interdependencia entre componentes de um sistema",`

`"definicao_operacional": "Relacionar fluxo de materia/energia/informacao entre partes interdependentes.",`

`"dominios": [`

`"DOM-SISTEMICO"`

`],`

`"competencia": "COMP-11",`

`"tipos_erro": [],`

`"origem_v1_3": [`

`"PROC-44",`

`"PROC-45"`

`]`

`},`

`{`

`"id": "PROC-CLASSIF-01",`

`"nome": "Classificar entidades por criterio compartilhado",`

`"definicao_operacional": "Agrupar entidades em categorias com base em propriedade declarada.",`

`"dominios": [`

`"DOM-CLASSIF"`

`],`

`"competencia": "COMP-12",`

`"tipos_erro": [`

`"ERR-13"`

`],`

`"origem_v1_3": [`

`"PROC-47",`

`"PROC-48",`

`"COMP-20"`

`]`

`}`

`],`

`"competencias": [`

`{`

`"id": "COMP-01",`

`"nome": "Raciocinar quantitativa e proporcionalmente",`

`"processos": [`

`"PROC-QUANT-01",`

`"PROC-QUANT-02",`

`"PROC-QUANT-03",`

`"PROC-QUANT-04"`

`]`

`},`

`{`

`"id": "COMP-02",`

`"nome": "Interpretar e transformar representacoes espaciais",`

`"processos": [`

`"PROC-ESPACO-01",`

`"PROC-ESPACO-02"`

`]`

`},`

`{`

`"id": "COMP-03",`

`"nome": "Relacionar estrutura a funcao",`

`"processos": [`

`"PROC-ESPACO-03"`

`]`

`},`

`{`

`"id": "COMP-04",`

`"nome": "Analisar mudanca, covariacao e conservacao",`

`"processos": [`

`"PROC-MUD-01",`

`"PROC-MUD-02"`

`]`

`},`

`{`

`"id": "COMP-05",`

`"nome": "Analisar dados e raciocinar sob incerteza",`

`"processos": [`

`"PROC-INC-01",`

`"PROC-INC-02",`

`"PROC-INC-03",`

`"PROC-INC-04"`

`]`

`},`

`{`

`"id": "COMP-06",`

`"nome": "Argumentar e explicar causalmente",`

`"processos": [`

`"PROC-CAUSAL-01"`

`]`

`},`

`{`

`"id": "COMP-07",`

`"nome": "Avaliar validade logica de argumentos",`

`"processos": [`

`"PROC-LOGICO-01"`

`]`

`},`

`{`

`"id": "COMP-08",`

`"nome": "Traduzir e decodificar linguagem formal/simbolica",`

`"processos": [`

`"PROC-SIMB-01",`

`"PROC-SIMB-02"`

`]`

`},`

`{`

`"id": "COMP-09",`

`"nome": "Compreender e integrar texto e representacoes",`

`"processos": [`

`"PROC-TEXT-01",`

`"PROC-TEXT-02",`

`"PROC-TEXT-03"`

`]`

`},`

`{`

`"id": "COMP-10",`

`"nome": "Investigar cientificamente",`

`"processos": [`

`"PROC-EXP-01",`

`"PROC-EXP-02"`

`]`

`},`

`{`

`"id": "COMP-11",`

`"nome": "Compreender sistemas e interdependencia",`

`"processos": [`

`"PROC-SIST-01",`

`"PROC-SIST-02"`

`]`

`},`

`{`

`"id": "COMP-12",`

`"nome": "Classificar e sistematizar",`

`"processos": [`

`"PROC-CLASSIF-01"`

`]`

`}`

`],`

`"habilidades_observaveis": [`

`{`

`"id": "HAB-01",`

`"nome": "Ordenar valores numericos em sequencia crescente/decrescente",`

`"processos_cognitivos": [`

`"PROC-QUANT-01"`

`]`

`},`

`{`

`"id": "HAB-02",`

`"nome": "Comparar duas razoes ou proporcoes entre grupos distintos",`

`"processos_cognitivos": [`

`"PROC-QUANT-01"`

`]`

`},`

`{`

`"id": "HAB-03",`

`"nome": "Resolver problema de proporcionalidade direta",`

`"processos_cognitivos": [`

`"PROC-QUANT-02"`

`]`

`},`

`{`

`"id": "HAB-04",`

`"nome": "Resolver problema de proporcionalidade inversa",`

`"processos_cognitivos": [`

`"PROC-QUANT-02"`

`]`

`},`

`{`

`"id": "HAB-05",`

`"nome": "Calcular variacao percentual sobre valor de referencia",`

`"processos_cognitivos": [`

`"PROC-QUANT-02"`

`]`

`},`

`{`

`"id": "HAB-06",`

`"nome": "Estimar valor aproximado a partir de pistas contextuais",`

`"processos_cognitivos": [`

`"PROC-QUANT-03"`

`]`

`},`

`{`

`"id": "HAB-07",`

`"nome": "Julgar plausibilidade de resultado numerico calculado",`

`"processos_cognitivos": [`

`"PROC-QUANT-03"`

`]`

`},`

`{`

`"id": "HAB-08",`

`"nome": "Converter grandeza entre unidades de medida distintas",`

`"processos_cognitivos": [`

`"PROC-QUANT-04"`

`]`

`},`

`{`

`"id": "HAB-09",`

`"nome": "Verificar consistencia dimensional em expressao formal",`

`"processos_cognitivos": [`

`"PROC-QUANT-04"`

`]`

`},`

`{`

`"id": "HAB-10",`

`"nome": "Identificar elementos metricos em figura geometrica",`

`"processos_cognitivos": [`

`"PROC-ESPACO-01"`

`]`

`},`

`{`

`"id": "HAB-11",`

`"nome": "Reconhecer semelhanca/congruencia entre duas figuras",`

`"processos_cognitivos": [`

`"PROC-ESPACO-01"`

`]`

`},`

`{`

`"id": "HAB-12",`

`"nome": "Calcular area de figura plana composta, por decomposicao",`

`"processos_cognitivos": [`

`"PROC-ESPACO-02"`

`]`

`},`

`{`

`"id": "HAB-13",`

`"nome": "Calcular volume de solido geometrico",`

`"processos_cognitivos": [`

`"PROC-ESPACO-02"`

`]`

`},`

`{`

`"id": "HAB-14",`

`"nome": "Associar estrutura celular/anatomica a funcao no organismo",`

`"processos_cognitivos": [`

`"PROC-ESPACO-03"`

`]`

`},`

`{`

`"id": "HAB-15",`

`"nome": "Associar organizacao molecular a propriedades observaveis",`

`"processos_cognitivos": [`

`"PROC-ESPACO-03"`

`]`

`},`

`{`

`"id": "HAB-16",`

`"nome": "Associar organizacao espacial de sistema ao papel funcional de um componente",`

`"processos_cognitivos": [`

`"PROC-ESPACO-03"`

`]`

`},`

`{`

`"id": "HAB-17",`

`"nome": "Calcular taxa de variacao a partir de dados de posicao/tempo",`

`"processos_cognitivos": [`

`"PROC-MUD-01"`

`]`

`},`

`{`

`"id": "HAB-18",`

`"nome": "Identificar como variacao de uma grandeza afeta outra em fenomeno descrito",`

`"processos_cognitivos": [`

`"PROC-MUD-01"`

`]`

`},`

`{`

`"id": "HAB-19",`

`"nome": "Associar grafico ao tipo de relacao funcional que representa",`

`"processos_cognitivos": [`

`"PROC-MUD-01"`

`]`

`},`

`{`

`"id": "HAB-20",`

`"nome": "Verificar conservacao de massa em transformacao quimica",`

`"processos_cognitivos": [`

`"PROC-MUD-02"`

`]`

`},`

`{`

`"id": "HAB-21",`

`"nome": "Verificar conservacao de energia em transformacao fisica",`

`"processos_cognitivos": [`

`"PROC-MUD-02"`

`]`

`},`

`{`

`"id": "HAB-22",`

`"nome": "Calcular quantidade de calor trocada em processo termico",`

`"processos_cognitivos": [`

`"PROC-MUD-02"`

`]`

`},`

`{`

`"id": "HAB-23",`

`"nome": "Calcular probabilidade condicional a partir de tabela de contingencia",`

`"processos_cognitivos": [`

`"PROC-INC-01"`

`]`

`},`

`{`

`"id": "HAB-24",`

`"nome": "Distinguir eventos dependentes de independentes",`

`"processos_cognitivos": [`

`"PROC-INC-01"`

`]`

`},`

`{`

`"id": "HAB-25",`

`"nome": "Calcular media aritmetica de conjunto de dados",`

`"processos_cognitivos": [`

`"PROC-INC-02"`

`]`

`},`

`{`

`"id": "HAB-26",`

`"nome": "Determinar mediana de conjunto ordenado",`

`"processos_cognitivos": [`

`"PROC-INC-02"`

`]`

`},`

`{`

`"id": "HAB-27",`

`"nome": "Identificar moda de conjunto de dados",`

`"processos_cognitivos": [`

`"PROC-INC-02"`

`]`

`},`

`{`

`"id": "HAB-28",`

`"nome": "Calcular amplitude de conjunto de dados",`

`"processos_cognitivos": [`

`"PROC-INC-03"`

`]`

`},`

`{`

`"id": "HAB-29",`

`"nome": "Interpretar desvio padrao/variancia como variabilidade real",`

`"processos_cognitivos": [`

`"PROC-INC-03"`

`]`

`},`

`{`

`"id": "HAB-30",`

`"nome": "Calcular proporcao esperada em processo gerador aleatorio",`

`"processos_cognitivos": [`

`"PROC-INC-04"`

`]`

`},`

`{`

`"id": "HAB-31",`

`"nome": "Prever resultado mais provavel a partir de padrao probabilistico",`

`"processos_cognitivos": [`

`"PROC-INC-04"`

`]`

`},`

`{`

`"id": "HAB-32",`

`"nome": "Distinguir causa de consequencia em texto/situacao",`

`"processos_cognitivos": [`

`"PROC-CAUSAL-01"`

`]`

`},`

`{`

`"id": "HAB-33",`

`"nome": "Identificar correlacao espuria entre dois eventos",`

`"processos_cognitivos": [`

`"PROC-CAUSAL-01"`

`]`

`},`

`{`

`"id": "HAB-34",`

`"nome": "Relacionar variacao de grandeza fisica a sua causa mecanica",`

`"processos_cognitivos": [`

`"PROC-CAUSAL-01"`

`]`

`},`

`{`

`"id": "HAB-35",`

`"nome": "Explicar caracteristica adaptativa por processo causal de origem",`

`"processos_cognitivos": [`

`"PROC-CAUSAL-01"`

`]`

`},`

`{`

`"id": "HAB-36",`

`"nome": "Identificar premissa e conclusao em argumento",`

`"processos_cognitivos": [`

`"PROC-LOGICO-01"`

`]`

`},`

`{`

`"id": "HAB-37",`

`"nome": "Detectar falacia logica em argumento",`

`"processos_cognitivos": [`

`"PROC-LOGICO-01"`

`]`

`},`

`{`

`"id": "HAB-38",`

`"nome": "Converter enunciado textual em equacao/expressao algebrica",`

`"processos_cognitivos": [`

`"PROC-SIMB-01"`

`]`

`},`

`{`

`"id": "HAB-39",`

`"nome": "Associar grafico a sua lei de formacao",`

`"processos_cognitivos": [`

`"PROC-SIMB-01"`

`]`

`},`

`{`

`"id": "HAB-40",`

`"nome": "Ler coeficientes e indices em formula quimica",`

`"processos_cognitivos": [`

`"PROC-SIMB-02"`

`]`

`},`

`{`

`"id": "HAB-41",`

`"nome": "Reconhecer significado de unidades/simbolos em expressao fisica",`

`"processos_cognitivos": [`

`"PROC-SIMB-02"`

`]`

`},`

`{`

`"id": "HAB-42",`

`"nome": "Localizar valor numerico explicito em enunciado textual",`

`"processos_cognitivos": [`

`"PROC-TEXT-01"`

`]`

`},`

`{`

`"id": "HAB-43",`

`"nome": "Localizar valor especifico em tabela de dupla entrada",`

`"processos_cognitivos": [`

`"PROC-TEXT-01"`

`]`

`},`

`{`

`"id": "HAB-44",`

`"nome": "Identificar valor maximo/minimo em grafico",`

`"processos_cognitivos": [`

`"PROC-TEXT-01"`

`]`

`},`

`{`

`"id": "HAB-45",`

`"nome": "Inferir relacao implicita entre duas variaveis do enunciado",`

`"processos_cognitivos": [`

`"PROC-TEXT-02"`

`]`

`},`

`{`

`"id": "HAB-46",`

`"nome": "Ler escala/eixo de grafico para inferir tendencia nao declarada",`

`"processos_cognitivos": [`

`"PROC-TEXT-02"`

`]`

`},`

`{`

`"id": "HAB-47",`

`"nome": "Combinar dado textual e grafico em conclusao unica",`

`"processos_cognitivos": [`

`"PROC-TEXT-03"`

`]`

`},`

`{`

`"id": "HAB-48",`

`"nome": "Integrar informacao de tabela e texto complementar",`

`"processos_cognitivos": [`

`"PROC-TEXT-03"`

`]`

`},`

`{`

`"id": "HAB-49",`

`"nome": "Propor explicacao testavel para fenomeno observado",`

`"processos_cognitivos": [`

`"PROC-EXP-01"`

`]`

`},`

`{`

`"id": "HAB-50",`

`"nome": "Identificar variavel dependente e independente em experimento",`

`"processos_cognitivos": [`

`"PROC-EXP-02"`

`]`

`},`

`{`

`"id": "HAB-51",`

`"nome": "Isolar variavel de controle em desenho experimental",`

`"processos_cognitivos": [`

`"PROC-EXP-02"`

`]`

`},`

`{`

`"id": "HAB-52",`

`"nome": "Prever sentido de deslocamento de sistema em equilibrio apos perturbacao",`

`"processos_cognitivos": [`

`"PROC-SIST-01"`

`]`

`},`

`{`

`"id": "HAB-53",`

`"nome": "Identificar posicao de componente em cadeia de interdependencia",`

`"processos_cognitivos": [`

`"PROC-SIST-02"`

`]`

`},`

`{`

`"id": "HAB-54",`

`"nome": "Descrever circulacao de elemento em sistema ciclico",`

`"processos_cognitivos": [`

`"PROC-SIST-02"`

`]`

`},`

`{`

`"id": "HAB-55",`

`"nome": "Classificar entidade por criterio fisico/quimico declarado",`

`"processos_cognitivos": [`

`"PROC-CLASSIF-01"`

`]`

`},`

`{`

`"id": "HAB-56",`

`"nome": "Classificar organismo em grupo taxonomico por caracteristicas apresentadas",`

`"processos_cognitivos": [`

`"PROC-CLASSIF-01"`

`]`

`}`

`],`

`"tipos_erro": [`

`{`

`"id": "ERR-01",`

`"nome": "Leitura literal deficiente",`

`"processos_cognitivos": [`

`"PROC-TEXT-01"`

`],`

`"mecanismo": "Falha em localizar dado explicito",`

`"evidencia_observavel": "Resposta ignora dado central do enunciado",`

`"intervencao": "INT-01"`

`},`

`{`

`"id": "ERR-02",`

`"nome": "Inferencia indevida",`

`"processos_cognitivos": [`

`"PROC-TEXT-02"`

`],`

`"mecanismo": "Assume dado nao presente ou extrapola sem base",`

`"evidencia_observavel": "Resposta incorpora informacao nao fornecida",`

`"intervencao": "INT-09"`

`},`

`{`

`"id": "ERR-03",`

`"nome": "Erro de modelagem/traducao",`

`"processos_cognitivos": [`

`"PROC-SIMB-01"`

`],`

`"mecanismo": "Traducao incorreta de situacao para representacao formal",`

`"evidencia_observavel": "Expressao nao corresponde a situacao descrita",`

`"intervencao": "INT-02"`

`},`

`{`

`"id": "ERR-04",`

`"nome": "Inconsistencia dimensional/de escala",`

`"processos_cognitivos": [`

`"PROC-QUANT-04"`

`],`

`"mecanismo": "Mistura ou converte unidades incorretamente",`

`"evidencia_observavel": "Resultado com unidade incompativel",`

`"intervencao": "INT-07"`

`},`

`{`

`"id": "ERR-05",`

`"nome": "Confusao de direcao em relacao proporcional",`

`"processos_cognitivos": [`

`"PROC-QUANT-02"`

`],`

`"mecanismo": "Aplica proporcionalidade direta quando e inversa (ou vice-versa)",`

`"evidencia_observavel": "Resultado invertido em relacao ao esperado",`

`"intervencao": "INT-03"`

`},`

`{`

`"id": "ERR-06",`

`"nome": "Leitura equivocada de representacao grafica/tabular",`

`"processos_cognitivos": [`

`"PROC-TEXT-01",`

`"PROC-TEXT-02"`

`],`

`"mecanismo": "Confunde eixo, escala ou celula",`

`"evidencia_observavel": "Valor extraido nao corresponde ao ponto correto",`

`"intervencao": "INT-04"`

`},`

`{`

`"id": "ERR-07",`

`"nome": "Confusao causa/correlacao",`

`"processos_cognitivos": [`

`"PROC-CAUSAL-01"`

`],`

`"mecanismo": "Interpreta associacao como relacao causal direta",`

`"evidencia_observavel": "Conclusao atribui causalidade sem mecanismo",`

`"intervencao": "INT-08"`

`},`

`{`

`"id": "ERR-08",`

`"nome": "Generalizacao indevida",`

`"processos_cognitivos": [`

`"PROC-CAUSAL-01",`

`"PROC-INC-03"`

`],`

`"mecanismo": "Estende conclusao de amostra nao-representativa ao todo",`

`"evidencia_observavel": "Conclusao ultrapassa o suporte da evidencia",`

`"intervencao": "INT-08"`

`},`

`{`

`"id": "ERR-09",`

`"nome": "Ignorar variavel de controle",`

`"processos_cognitivos": [`

`"PROC-EXP-02"`

`],`

`"mecanismo": "Desconsidera fator interveniente relevante",`

`"evidencia_observavel": "Conclusao nao isola a variavel testada",`

`"intervencao": "INT-10"`

`},`

`{`

`"id": "ERR-10",`

`"nome": "Erro de decodificacao de notacao simbolica",`

`"processos_cognitivos": [`

`"PROC-SIMB-02"`

`],`

`"mecanismo": "Le incorretamente simbolo/coeficiente/unidade formal",`

`"evidencia_observavel": "Interpretacao da formula diverge do significado correto",`

`"intervencao": "INT-02"`

`},`

`{`

`"id": "ERR-11",`

`"nome": "Erro de estimativa/ordem de grandeza",`

`"processos_cognitivos": [`

`"PROC-QUANT-03"`

`],`

`"mecanismo": "Produz valor de magnitude incompativel com o contexto",`

`"evidencia_observavel": "Resposta numerica implausivel pela ordem de grandeza",`

`"intervencao": "INT-06"`

`},`

`{`

`"id": "ERR-12",`

`"nome": "Falha de validade logica/falacia",`

`"processos_cognitivos": [`

`"PROC-LOGICO-01"`

`],`

`"mecanismo": "Aceita conclusao que nao decorre logicamente das premissas",`

`"evidencia_observavel": "Estrutura do argumento e invalida independentemente do conteudo",`

`"intervencao": "INT-05"`

`},`

`{`

`"id": "ERR-13",`

`"nome": "Classificacao por criterio superficial",`

`"processos_cognitivos": [`

`"PROC-CLASSIF-01"`

`],`

`"mecanismo": "Agrupa por aparencia, nao por criterio estrutural/funcional",`

`"evidencia_observavel": "Classificacao ignora propriedade definidora em favor de traco saliente",`

`"intervencao": "INT-11"`

`}`

`],`

`"intervencoes_pedagogicas": [`

`{`

`"id": "INT-01",`

`"nome": "Releitura guiada do enunciado",`

`"tipos_erro": [`

`"ERR-01"`

`]`

`},`

`{`

`"id": "INT-02",`

`"nome": "Diagrama de traducao (esquema visual enunciado-modelo formal)",`

`"tipos_erro": [`

`"ERR-03",`

`"ERR-10"`

`]`

`},`

`{`

`"id": "INT-03",`

`"nome": "Pratica guiada de relacoes proporcionais (direta e inversa)",`

`"tipos_erro": [`

`"ERR-05"`

`]`

`},`

`{`

`"id": "INT-04",`

`"nome": "Analise critica de representacoes graficas/tabulares",`

`"tipos_erro": [`

`"ERR-06"`

`]`

`},`

`{`

`"id": "INT-05",`

`"nome": "Debate estruturado de argumentos (premissa/conclusao/falacia)",`

`"tipos_erro": [`

`"ERR-12"`

`]`

`},`

`{`

`"id": "INT-06",`

`"nome": "Laboratorio de estimativa e ordem de grandeza",`

`"tipos_erro": [`

`"ERR-11"`

`]`

`},`

`{`

`"id": "INT-07",`

`"nome": "Revisao de unidades e consistencia dimensional",`

`"tipos_erro": [`

`"ERR-04"`

`]`

`},`

`{`

`"id": "INT-08",`

`"nome": "Treino de distincao causa/correlacao com contraexemplos",`

`"tipos_erro": [`

`"ERR-07",`

`"ERR-08"`

`]`

`},`

`{`

`"id": "INT-09",`

`"nome": "Pratica de inferencia com verificacao explicita de evidencia textual",`

`"tipos_erro": [`

`"ERR-02"`

`]`

`},`

`{`

`"id": "INT-10",`

`"nome": "Desenho experimental guiado com identificacao de variaveis",`

`"tipos_erro": [`

`"ERR-09"`

`]`

`},`

`{`

`"id": "INT-11",`

`"nome": "Pratica de classificacao por criterio funcional/estrutural",`

`"tipos_erro": [`

`"ERR-13"`

`]`

`}`

`],`

`"id": "1.4",`

`"based_on": "1.3",`

`"governed_by": [`

`"White Paper Sapiens 2.0",`

`"Constituicao da Ontologia Sapiens"`

`],`

`"is_active": true`

`}`