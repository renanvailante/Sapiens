## id: CON-1.1 titulo: Constituição da Ontologia Sapiens versao: 1.1 estado: ativo camada: C2 criado_em: 2026-08-17T02:56:16Z atualizado_em: 2026-08-17T18:44:59Z supersedes: ["1.0 (estado anterior, não versionado)"] superseded_by: null derivado_de: null governado_por: GOV-1.0 governed_by_conteudo: ["White Paper Sapiens 2.0.1"] compativel_com: ontologia: ">=1.4.1, <2.0" changelog_ref: TX-2026-08-17T184459Z-constituicao-v1.1 remissoes_pendentes: []

# Constituição da Ontologia Sapiens — v1.1

> **Natureza desta versão.** A 1.1 acrescenta os Capítulos 5, 7, 11 e 12, que a 1.0 invocava como remissão normativa e não continha — situação em que, sob GOV-1.0 §1.4, _"uma regra que se resolve 'conforme o Capítulo X' onde X não existe é, para todos os efeitos, uma regra sem conteúdo"_. Isso encerra `G-CONF-05`.
> 
> **Nenhum critério novo foi criado.** O Capítulo 5 é **consolidação** de regras já dispersas nos Capítulos 1 a 4, com tabela de rastreabilidade de cada critério à sua seção de origem. Os Capítulos 7 e 11 são **deferimentos declarados**: seu conteúdo depende de dados de piloto, e a própria 1.0 (§3.7.2) já o declarava; eles convertem uma remissão pendente em um deferimento explícito, sem inventar os limiares. O Capítulo 12 é **registro** de questões diferidas, sem decisão.
> 
> Os Capítulos 1 a 4 e o Adendo 3.7 estão preservados na íntegra. Acréscimos em blocos marcados **`[Errata 1.1]`**. Detalhe em `TX-2026-08-17T184459Z-constituicao-v1.1`.

# Capítulo 1 — Objetivo da Ontologia

## 1.1 O problema que ela resolve

A organização curricular por disciplina tem origem administrativa, não cognitiva — a "gramática da escolarização" documentada por Tyack & Cuban (1995) consolidou-se por razões de escala de gestão escolar, não por corresponder a como o conhecimento é estruturado na mente. A consequência prática já foi observada empiricamente, não apenas argumentada em abstrato, na própria auditoria da v1.3 deste projeto: o mesmo padrão cognitivo (estrutura→função, por exemplo) apareceu fragmentado em quatro lugares diferentes do dataset (COMP-19, COMP-21, PROC-41, PROC-46), sem que a arquitetura reconhecesse que era a mesma coisa manifestando-se em contextos distintos. E o inverso também ocorreu: rótulos que pareciam categorias cognitivas (PROC-29 a PROC-50) eram, no exame direto do dado, nomes de tópico disciplinar — o campo `categoria` mudava de natureza na metade exata da lista, sem que nenhum mecanismo estrutural detectasse a mudança de convenção.

O problema que esta ontologia existe para resolver é, portanto, específico e testável, não retórico: **fornecer um vocabulário e uma gramática estrutural para dimensões cognitivas latentes de desempenho que sejam (a) independentes da superfície disciplinar em que se manifestam, (b) reutilizáveis entre essas superfícies, e (c) empiricamente distinguíveis de dimensões adjacentes** — conhecimento de conteúdo, estratégia procedimental específica, estado momentâneo de desempenho.

Esta formulação não é nova a este documento: é exatamente a exigência de multidimensionalidade distinguível já estabelecida como parte da fundamentação teórica do Sapiens (Axioma da Fatoração). O que este documento acrescenta é a camada que faltava entre a exigência abstrata — "deve haver múltiplos fatores latentes distinguíveis" — e a prática de curadoria — "como um humano decide, de forma reproduzível, se um candidato a fator satisfaz essa exigência." A ontologia é a instância nomeada e auditável desses fatores; esta Constituição é o conjunto de regras que decide quais nomeações são admissíveis.

> **`[Errata 1.1]`** Os identificadores citados nesta seção (`COMP-19`, `COMP-21`, `PROC-41`, `PROC-46`, `PROC-29` a `PROC-50`) pertencem à **geração G2** — a Ontologia v1.3, **ausente do corpus canônico** (`G-CONF-09`). São, portanto, remissões pendentes: a argumentação desta seção permanece válida em substância, porque os exemplos ilustram princípios e os princípios não dependem da inspeção dos exemplos, mas **nenhum leitor pode verificá-los**. Ver `09 Mapa de Rastreabilidade de IDs` §8.

## 1.2 O que ela pretende representar

A ontologia pretende representar:

**Processos cognitivos** como unidades de operação mental definidas em um nível de abstração no qual, em princípio, mais de uma superfície disciplinar pode instanciá-las — o critério formal para essa admissibilidade é objeto do Capítulo 5, não deste capítulo.

**Habilidades observáveis** como a manifestação operacionalizada e mensurável de um processo cognitivo em um contexto avaliativo específico. Registro aqui, sem desenvolver ainda, uma tensão que a auditoria da v1.3 já tornou visível e que retomo no Capítulo 12: em parte substancial dos dados examinados, a relação Processo→Habilidade aproximou-se de correspondência 1:1, o que levanta a pergunta legítima de se os dois níveis são, de fato, ontologicamente distintos ou se um deles é redundante em relação ao outro. Não decido isso aqui.

**Relações estruturadas** entre essas unidades — a natureza exata dessas relações (tipagem, direção, peso) é matéria do Capítulo 4; o que importa neste capítulo é que a ontologia pretende ser um grafo com semântica declarada, não uma lista plana de rótulos, que foi precisamente o formato que permitiu à v1.3 acumular redundância silenciosa sem detecção.

**Tipos de erro** como categorias diagnósticas ancoradas a falha de um processo cognitivo específico — não de um procedimento específico. A distinção importa: a auditoria encontrou tipos de erro (ex.: "confusão entre proporção direta e inversa") que nomeiam falha em uma técnica, não em um mecanismo cognitivo generalizável, repetindo na camada de diagnóstico o mesmo problema já identificado na camada de processo.

**Intervenções pedagógicas** indexadas ao mecanismo de erro diagnosticado, não ao conteúdo da questão em que o erro ocorreu.

## 1.3 O que ela deliberadamente não pretende representar

Esta seção é normativa, não descritiva: cada item abaixo é uma fronteira de escopo que qualquer expansão futura da ontologia deve respeitar, salvo revisão explícita desta Constituição.

**Conteúdo declarativo disciplinar como objeto ontológico de primeira classe.** Fatos, fórmulas nomeadas, leis específicas, procedimentos de sala de aula (o exemplo mais citado ao longo de todo este projeto é "regra de três") não são processos, competências ou habilidades — são manifestações, e pertencem a uma camada distinta (empírica/de conteúdo), não à ontologia cognitiva propriamente dita. Isto não é uma preferência estética; é a correção direta ao problema mais caro identificado na auditoria da v1.3, presente em pelo menos 20 dos 50 processos examinados.

**Uma taxonomia final e completa da cognição humana.** A ontologia é, e permanece, hipótese de engenharia sujeita a revisão empírica — a mesma disciplina epistemológica (evidência científica / interpretação teórica / decisão de engenharia) que governa o restante deste projeto aplica-se aqui, e nenhuma categoria desta ontologia deve ser apresentada como fato estabelecido.

**Estado motivacional, afetivo ou de desempenho momentâneo.** Fadiga, ansiedade, engajamento e variáveis correlatas pertencem a uma camada distinta do modelo de estado do Sapiens (a camada de escala temporal rápida do Axioma da Crença Calibrada), não à estrutura de fatores que esta ontologia nomeia.

**Lógica de decisão pedagógica ou sequenciamento curricular.** A ontologia fornece o vocabulário que uma camada de decisão consumiria; ela não decide o que ensinar a seguir. Essa camada permanece, no projeto Sapiens como um todo, deliberadamente não especificada.

**O instrumento de medição em si.** Itens e questões são classificados pela ontologia; não são parte dela.

**Uma alegação de realismo psicológico ou neurológico sobre a mente humana.** A ontologia é um sistema representacional funcional para fins de engenharia — não um modelo da arquitetura neural ou psicológica real. Esta fronteira precisa ser declarada explicitamente, não deixada implícita, exatamente para prevenir a crítica antecipada em estágios anteriores deste projeto ("vocês estão afirmando que o cérebro é um banco de dados?").

## 1.4 Nota crítica: precisão terminológica sobre o próprio termo "ontologia"

Um ponto que merece registro explícito, não apenas cosmético. Na tradição de Engenharia de Ontologias (Gruber, 1993; Guarino, 1998), uma ontologia é definida como especificação formal e explícita de uma conceitualização — o que, na prática dessa literatura, normalmente implica axiomas expressos em uma lógica formal (tipicamente Description Logics/OWL), governando o que pode e não pode ser assertado sobre cada categoria, incluindo propriedades meta-ontológicas como rigidez, identidade e unidade (Guarino & Welty, 2002).

O que o Sapiens vem construindo, e o que esta Constituição vai governar, não satisfaz esse padrão formal — é, com mais precisão, uma **taxonomia com relações tipadas**, no espírito do Q-matrix usado em modelos de diagnóstico cognitivo psicométricos e do framework de Knowledge Components de Koedinger, Corbett & Perfetti (2012). Isso não é uma deficiência a esconder: é uma escolha de escopo legítima, desde que declarada. Chamar isso de "ontologia" ao longo deste documento preserva a continuidade terminológica já estabelecida no projeto, mas esta Constituição registra, aqui e agora, que o termo é usado no sentido mais fraco e mais comum entre os tipos de ontologia que a própria literatura reconhece (ontologia de referência/leve), não no sentido formal-axiomático. Onde isso tiver consequência prática — por exemplo, ao definir critérios de inclusão no Capítulo 5 — retomo esta distinção.

---

# Capítulo 2 — Princípios Filosóficos

## 2.1 As cinco categorias e o critério que as separa

A confusão mais cara encontrada na auditoria da v1.3 não foi falta de rigor — foi ausência de um critério explícito para saber a qual categoria um candidato pertence antes de nomeá-lo. Este capítulo fornece esse critério; o Capítulo 3 lhe dá forma de definição.

As cinco categorias não se distinguem por nível de generalidade (mais amplo/mais específico), mas por **função dentro do sistema**:

- **Conhecimento** não é um nível hierárquico — é uma dimensão transversal que classifica _como_ algo é sabido (declarativo, procedimental, condicional, estratégico/metacognitivo), aplicável a qualquer nó de qualquer nível. Tratar tipo de conhecimento como se fosse mais um degrau na hierarquia foi, precisamente, um dos mecanismos pelos quais a v1.3 perdeu coerência interna — a dimensão "o que se sabe" foi confundida com a dimensão "onde isso se organiza".
- **Competência** agrupa, para fins de comunicação curricular e navegação humana, um feixe recorrente de processos cognitivos que tendem a coocorrer na resolução de um mesmo tipo de situação. **Esta Constituição adota, como posição operativa a partir deste ponto — não como observação lateral —: Competência é tratada como agrupamento derivado, não como entidade ontológica fundamental.** Ela não possui poder explicativo próprio além do que herda dos processos cognitivos que agrupa; não é, portanto, rastreada pelo motor de crença como unidade independente de estado. Esta posição é adotada com grau de confiança parcial, não como fato estabelecido: o White Paper 2.0 registra a hipótese de rebaixamento de "Competência" a agrupamento derivado com confiança de 55% — insuficiente para tratar como conclusão fechada, suficiente para governar o trabalho de definição formal do Capítulo 3. Se evidência futura invalidar essa hipótese, é o Capítulo 4 (Relações) que precisará ser revisado — não os fundamentos deste capítulo.
- **Processo Cognitivo** é a unidade candidata a transferível — a operação mental cuja identidade não depende da superfície disciplinar em que aparece. **Nota de escopo, a ser mantida em toda expansão futura desta ontologia: "Processo Cognitivo" é uma unidade funcional de análise de desempenho, não uma afirmação neuropsicológica.** Nomear um processo não é reivindicar a existência de um módulo, circuito ou substrato neural correspondente — é postular uma regularidade suficientemente estável no comportamento observável para justificar rastreamento e intervenção. Esta distinção não é nova: estende ao nível operacional da ontologia a mesma fronteira que o White Paper 2.0 já declara em sua Parte I — a de que a arquitetura Sapiens é um sistema representacional funcional para fins de engenharia, não um modelo da mente real.
- **Habilidade Observável** é a manifestação mensurável de um processo em um contexto avaliativo determinado — o ponto em que a operação mental encontra um item real.
- **Conteúdo Disciplinar** não é uma categoria da ontologia cognitiva; é o material através do qual um processo se manifesta, e existe nesta Constituição apenas como o termo contra o qual a transferibilidade (2.3) é definida por contraste.

> **`[Errata 1.1]`** Registro de estado sobre a dimensão transversal **Conhecimento**: ela é declarada nesta seção e **nenhum documento operacional do corpus a implementa**. É a única dimensão transversal prometida pela Constituição e nunca instanciada. Sua recuperação — os seis tipos de conhecimento do White Paper 1.0 §2.2 — está registrada em `EXT-WP1-1.0`, item L9, com recomendação de recuperação. **Nenhuma decisão é tomada aqui**; a instanciação é emenda aditiva e depende de ato próprio. Registrado no Capítulo 12.

## 2.2 Estrutura cognitiva versus currículo escolar

O critério operacional que separa as duas é este: **um elemento pertence ao currículo se sua unidade organizadora for a disciplina, a série ou a sequência de ensino; pertence à ontologia cognitiva se sua unidade organizadora for o processo mental exigido, independentemente de em qual disciplina, série ou momento curricular ele apareça.**

Este critério não é uma reformulação estética do argumento histórico já estabelecido no White Paper 2.0 (Capítulo 1, §1.2) — é sua consequência operacional direta. Se a organização disciplinar tem origem administrativa e não cognitiva, então qualquer candidato a nó desta ontologia cuja única justificativa de existência seja "isso é ensinado na disciplina X, na série Y" já falhou o teste de pertencimento, independentemente de quão bem definido esteja tecnicamente. A auditoria da v1.3 tornou isso concreto: PROC-17 ("aplicar teorema de Pitágoras") é tecnicamente bem escrito, sem ambiguidade de redação — e ainda assim não pertence a esta ontologia, porque sua unidade organizadora é uma disciplina e uma lei nomeada, não uma operação mental.

## 2.3 Critérios de transferibilidade

Transferibilidade é o critério que autoriza um candidato a se tornar Processo Cognitivo. A formulação mínima: **um candidato é elegível como Processo Cognitivo se for hipoteticamente instanciável em pelo menos duas superfícies disciplinares distintas, sem que essa instanciação dependa de vocabulário, fórmula ou procedimento específico de nenhuma delas.**

**Primeira precisão — semelhança formal não é transferibilidade.** Dois itens que parecem estruturalmente parecidos ("3 máquinas produzem 300 peças, quantas produzem 5 máquinas" e um problema de estequiometria) não demonstram, por si, que compartilham processo cognitivo — podem compartilhar apenas um padrão superficial de tarefa. O White Paper 2.0 já registra esta tensão como não resolvida (a questão central do Axioma da Fatoração, sobre se a multiplicidade de fatores existe dentro de uma única tarefa ou apenas entre tarefas distintas) e a mantém como item de pesquisa aberto, não como fato assumido. Esta Constituição, portanto, trata transferibilidade hipotética como **critério de candidatura**, não como validação — o processo entra na ontologia como hipótese testável (o teste em si é matéria do Capítulo 11), nunca como fato estabelecido pela sua simples nomeação.

**Segunda precisão — transferibilidade não exige ausência de conhecimento de domínio.** Um processo pode ser genuinamente cognitivo e ainda assim depender de conhecimento de conteúdo para se manifestar (dominar "regra de três" não garante sucesso em estequiometria, que soma a esse processo conhecimento químico específico). A exigência não é que o processo funcione sozinho, sem conteúdo algum — é que o processo seja **conceitualmente separável** do conteúdo que o veste em cada superfície. Isto corresponde diretamente à separação entre fatores latentes distintos e parcialmente correlacionados que o Axioma da Fatoração do White Paper 2.0 exige; esta Constituição não redefine o axioma, apenas o traduz em critério de decisão para quem está nomeando um nó.

## 2.4 Critérios de independência entre categorias

Dois candidatos só devem existir como nós separados se houver razão para esperar que se comportem de forma distinguível sob evidência — não porque têm nomes diferentes, nem porque aparecem em domínios de conteúdo diferentes. A auditoria da v1.3 já demonstrou o custo de não aplicar este critério: PROC-47 ("classificar organismo"), PROC-48 ("classificar substância") e COMP-20 ("classificar entidades") são três nomeações da mesma operação cognitiva — "agrupar por critério compartilhado" — diferenciadas apenas pelo conteúdo ao qual se aplicam, não por nenhuma propriedade cognitiva real.

O teste de independência proposto aqui é negativo, não positivo: **dois candidatos são independentes até que se demonstre o contrário; a demonstração de que são o mesmo processo exige evidência de que produzem os mesmos padrões de erro, a mesma dependência de pré-requisito, e a mesma assinatura de tempo de resposta — não apenas nomes ou domínios de aplicação diferentes que soem distintos.**

**Tensão registrada.** Este critério de independência pressupõe que exista, em algum momento, evidência empírica disponível para aplicá-lo — mas na fase de construção inicial da ontologia (antes de qualquer piloto de anotação), essa evidência ainda não existe. A Constituição resolve isso transferindo o ônus da prova, não eliminando a tensão: **na ausência de evidência, dois candidatos que descrevem a mesma operação cognitiva aplicada a conteúdos diferentes devem ser tratados como um único Processo Cognitivo com múltiplas manifestações disciplinares, não como dois processos** — a fusão é o estado padrão; a separação é que precisa ser justificada, nunca o inverso.

## 2.5 Princípio de fechamento

Os quatro critérios acima — separação por função, não por currículo; transferibilidade como candidatura; independência como ônus da prova; Competência como agrupamento derivado — convergem para um único princípio, que esta Constituição declara como cláusula permanente, a ser invocada sempre que um critério mais específico faltar ou entrar em conflito com conveniência administrativa:

> **A ontologia deve priorizar unidades explicativas em detrimento de unidades administrativas.**

Uma unidade é explicativa quando sua existência aumenta a capacidade do sistema de prever ou diagnosticar desempenho; é administrativa quando sua existência serve apenas à conveniência de organização curricular, editorial ou de conteúdo. Nenhum nó desta ontologia deve sobreviver a uma revisão futura apenas por já constar em uma versão anterior, por corresponder a uma disciplina reconhecida, ou por facilitar a redação de um currículo — critérios administrativos legítimos em outros contextos, mas que este princípio subordina explicitamente, dentro desta ontologia, ao critério explicativo.

---

# Capítulo 3 — Definição Formal dos Objetos

Cada objeto é definido pelo mesmo formato tripartite: o que é, o que não é, qual sua função na ontologia. "Conhecimento", por ser dimensão transversal e não nível (§2.1), não recebe entrada própria nesta lista de seis — sua definição já está completa no capítulo anterior.

## 3.1 Domínio

**O que é.** Uma agregação de mais alto nível que reúne Processos Cognitivos por parentesco de família de operação mental — por exemplo, operações sobre quantidade e magnitude, ou operações sobre relação causal — não por área de conteúdo escolar.

**O que não é.** Não é sinônimo de disciplina ("Física", "Biologia") nem de área de conteúdo ("Matéria e Energia", "Classificação"). A auditoria da v1.3 identificou exatamente essa falha: dois domínios (DOM-MATERIA, DOM-CLASSIF) descreviam _o que se pensa_ (matéria, energia, categorias taxonômicas), não _como se pensa_ — a mesma confusão que o Capítulo 2 proíbe no nível de Processo, aqui reaparecendo um nível acima. Domínio também não é licença para amplitude sem coesão: DOM-SISTEMICO, na v1.3, cobria fenômenos naturais, sociais, históricos e tecnologia-sociedade simultaneamente — um domínio sem operação mental unificadora identificável não satisfaz esta definição, por mais abrangente que pareça.

**Função na ontologia.** Fornece o nível de agregação mais alto para navegação humana e comunicação do sistema. Não é, por si, unidade consumida diretamente pelo motor de crença do Sapiens — essa função pertence ao Processo Cognitivo (3.3). Domínio existe para que um humano consiga se orientar dentro do grafo, não para que o sistema calcule algo a partir dele.

> **`[Errata 1.1]` — esclarecimento necessário, sem alteração de critério.** Os identificadores `DOM-MATERIA`, `DOM-CLASSIF` e `DOM-SISTEMICO` citados acima pertencem à **geração G2** (Ontologia v1.3). A crítica a eles permanece válida. Mas dois desses identificadores **foram reutilizados na v1.4 com definições diferentes e conformes**:
> 
> - **`DOM-CLASSIF`** existe no catálogo vigente, redefinido como _"operações de agrupar entidades em categorias por critério de propriedade compartilhada"_ — que **é** uma operação, e portanto **não incorre** na crítica desta seção.
> - **`DOM-SISTEMICO`** existe no catálogo vigente com extensão estreitada, sem a amplitude sem coesão criticada acima.
> - **`DOM-MATERIA`** foi removido e não existe no catálogo vigente.
> 
> Sem este esclarecimento, um leitor que cruze esta seção com o catálogo vigente concluiria, **erroneamente**, que a Ontologia v1.4.1 mantém um domínio que esta Constituição reprova. A reutilização de identificador aposentado é vedada prospectivamente por GOV-1.0 §5.3 e está registrada como incidente `MAP-INC-01`.

## 3.2 Competência

**O que é.** Um agrupamento derivado de Processos Cognitivos que tendem a coocorrer na resolução de um mesmo tipo de situação prática ou acadêmica — útil para comunicação curricular e para dar nome, em linguagem acessível a educadores, a um feixe de operações que o sistema já rastreia em granularidade mais fina.

**O que não é.** Não é, sob a posição adotada no Capítulo 2 (§2.1), uma entidade ontológica fundamental com poder explicativo próprio — não é rastreada de forma independente pelo motor de crença, e sua instabilidade observada na literatura de diagnóstico cognitivo (nível mais dependente de framework pedagógico entre todos os da hierarquia) é consequência esperada de sua natureza derivada, não uma falha de definição a corrigir com mais regras de governança. Também não é sinônimo de habilidade escolar ("saber resolver equações") nem de tópico de conteúdo.

**Função na ontologia.** Interface de tradução entre a granularidade fina em que Processos Cognitivos operam e a linguagem que currículos, educadores e relatórios de desempenho utilizam. É recalculável a partir dos processos que agrupa; não é fonte primária de verdade sobre o estado do estudante.

## 3.3 Processo Cognitivo

**O que é.** A unidade funcional de análise de desempenho — uma operação mental postulada como necessária para a resolução de uma classe de tarefas, formulada em nível de abstração que permite, mas não garante, instanciação em mais de uma superfície disciplinar (critério de transferibilidade, §2.3).

**O que não é.** Não é uma afirmação sobre módulo neural, circuito cerebral ou estrutura psicológica real (§2.1) — é um construto funcional, sujeito a revisão empírica, não uma alegação sobre a arquitetura da mente. Não é um procedimento, técnica ou fórmula nomeada — a auditoria da v1.3 identificou entre 20 e 24 dos 50 processos daquela versão como violando este critério (ex.: "aplicar regra de três", "balancear equação química", que nomeiam técnica, não operação mental). Não é, tampouco, garantidamente transferível apenas por ter sido nomeado como candidato — transferibilidade permanece hipótese até validação (§2.3, Capítulo 11).

**Função na ontologia.** É a unidade central rastreável pelo motor de crença do Sapiens — o nível em que o Axioma da Fatoração do White Paper 2.0 opera, e o nível sobre o qual o sistema mantém e atualiza confiança calibrada de domínio. Toda a arquitetura de estado dinâmico do Sapiens é construída em torno deste objeto, não de Competência nem de Domínio.

## 3.4 Habilidade Observável

**O que é.** A manifestação mensurável e operacionalizada de um Processo Cognitivo em um contexto avaliativo específico — o ponto de contato entre a operação mental hipotetizada e um item real, redigido em linguagem suficientemente concreta para orientar a anotação humana de uma questão.

**O que não é.** Não é o Processo Cognitivo em si — é sua manifestação, e a distinção só tem valor se as duas entidades puderem, em princípio, variar de forma independente. A auditoria da v1.3 encontrou correspondência 1:1 entre Processo e Habilidade em proporção alta dos casos examinados — o que levanta, sem resolver aqui, a pergunta legítima de se os dois níveis são, de fato, distintos ou redundantes na prática atual da ontologia. Este documento não decide essa questão; registra-a como item a examinar no Capítulo 12.

**Função na ontologia.** Fornece o grão em que a anotação humana efetivamente opera sobre um item real. É o elo que conecta a ontologia cognitiva à Especificação Técnica (documento separado) — especificamente ao objeto `ItemCognitiveMapping`, cuja definição de schema não é matéria desta Constituição.

> **`[Errata 1.1]`** A remissão a uma "Especificação Técnica" e ao objeto `ItemCognitiveMapping` estava pendente: **esse documento nunca existiu no corpus canônico** (`G-CONF-04`). O contrato do item anotado é o **Schema Sapiens 2.2**, documento de camada C4. A remissão fica assim resolvida. `ItemCognitiveMapping` é nomenclatura da geração G0/G1 (White Paper 1.0 §2.9.1) e permanece citável apenas como proveniência.

## 3.5 Tipo de Erro

**O que é.** Uma categoria diagnóstica que descreve um mecanismo de falha em um Processo Cognitivo, ou na aplicação deste a uma Habilidade Observável específica — a unidade que torna uma resposta errada informativa sobre _qual_ operação mental não ocorreu como esperado, não apenas sobre _que_ a resposta estava errada.

**O que não é.** Não é uma propriedade do item avaliativo — a auditoria da v1.3 identificou um caso claro dessa confusão ("distrator plausível", que descreve qualidade da alternativa incorreta, não falha do aluno). Não é um rótulo de conteúdo disciplinar ("erro de estequiometria", "confusão entre proporção direta e inversa") — a mesma auditoria encontrou pelo menos cinco tipos de erro, de treze catalogados, violando este critério ao nomear falha em procedimento específico em vez de mecanismo cognitivo generalizável. Não é, tampouco, a única explicação possível de uma resposta observada — o White Paper 2.0 trata atribuição de causa de erro como distribuição de confiança sobre múltiplas causas candidatas, não como rótulo único e determinístico (matéria da Especificação Técnica, não desta Constituição).

**Função na ontologia.** Alimenta o mecanismo de Error Trace, ativo protegido do projeto Sapiens desde o White Paper 2.0 — é o objeto que conecta evidência observada (a resposta errada) de volta à distribuição de crença sobre qual Processo Cognitivo falhou, e por qual mecanismo.

> **`[Errata 1.1]`** Duas resoluções de remissão. **(a)** A distribuição de confiança sobre causas candidatas tem contrato canônico na **`Especificação do Error Trace v1.0`** (C4), que restaura também a **ordem causal** da cadeia — propriedade que esta seção pressupõe ao falar de "mecanismo" e que havia sido perdida. **(b)** A propriedade do item corretamente excluída daqui ("distrator plausível") foi **realocada** para o campo `distratores[].plausibilidade` do Schema Sapiens 2.2, onde é propriedade do item e não do aluno. A realocação é conforme e fica registrada para que não seja desfeita por leitura apressada.

## 3.6 Intervenção Pedagógica

**O que é.** Uma ação ou recurso pedagógico indexado a um Tipo de Erro, ou a um estado de baixa confiança em um Processo Cognitivo específico — a resposta do sistema à pergunta "dado este diagnóstico, o que fazer".

**O que não é.** Não é um plano de aula nem conteúdo didático completo. Não é definida por disciplina ou tópico — uma intervenção indexada a "erro de leitura literal deficiente", por exemplo, deve ser aplicável independentemente de a leitura deficiente ter ocorrido em um enunciado de matemática ou de ciências.

**Função na ontologia.** Fecha o ciclo diagnóstico–remediação. É consumida por uma camada de decisão pedagógica que o White Paper 2.0 reconhece explicitamente como ainda não especificada (o "slot vazio" da função objetivo de decisão) — dentro desta ontologia, a Intervenção Pedagógica existe como candidata de ação associada a um diagnóstico, não como política de seleção automática entre candidatas.

> **`[Errata 1.1]`** Precisão de estado, conforme a errata do White Paper 2.0.1 §6.3: o slot é vazio quanto à **função objetivo**, não quanto a conteúdo. Duas políticas de seleção existiam no White Paper 1.0 e estão registradas como `rebaixadas` a decisão de engenharia não derivada dos axiomas (`EXT-WP1-1.0`, item L10). A afirmação desta seção — que a Intervenção não é política de seleção automática **dentro desta ontologia** — permanece correta e inalterada. Acréscimo operacional decorrente da `Especificação do Error Trace v1.0` §1.1: quando o diagnóstico é uma cadeia, a Intervenção é indexada ao **elo raiz**, nunca à manifestação de superfície.

---

# Adendo ao Capítulo 3 — Restrições de Engenharia Incorporadas

## 3.7.1 Critério operacional de agrupamento em Domínio _(referente a §3.1)_

A definição original ("família de operação mental") era insuficiente para decidir casos de fronteira. Teste operacional adotado a partir de agora: **dois Processos pertencem ao mesmo Domínio somente se o que têm em comum puder ser descrito em uma frase que nomeia um tipo de operação ou relação mental (comparar magnitude, rastrear causa, classificar por critério) — não um tipo de fenômeno ou entidade do mundo real (matéria, seres vivos, sociedade).** Se a descrição do que é comum exigir enumerar classes de fenômeno unidas por "e" (fenômenos naturais _e_ sociais _e_ tecnológicos), o agrupamento falha o teste e é candidato a subdivisão. Este critério invalida, por construção — não por decisão editorial desta Constituição, que não redesenha a v1.3 — qualquer Domínio organizado em torno de classe de entidade em vez de tipo de operação.

## 3.7.2 Tamanho mínimo/máximo de um Processo Cognitivo _(referente a §3.3)_

Fixar um número aqui seria cristalização prematura — a mesma disciplina já aplicada a parâmetros ao longo de todo este projeto (forma exigida agora, valor calibrado depois, empiricamente). Esta Constituição fixa o **teste**, não o número:

- **Gatilho de fragmentação excessiva**: um Processo mapeado a exatamente uma Habilidade Observável, sem que uma segunda manifestação plausível possa ser descrita, é candidato a fusão — para cima, em um Processo mais amplo, ou reclassificação como Habilidade disfarçada de Processo (viola §3.7.3, abaixo).
- **Gatilho de fusão excessiva**: se dois componentes hipotéticos dentro de um único Processo já indicam, mesmo informalmente, padrões de erro ou dependências de pré-requisito distintos, isso aciona o critério de independência do §2.4 e o Processo é candidato a divisão.
- Os limiares numéricos exatos — quantas Habilidades bastam, quão diferente um padrão de erro precisa ser — permanecem deliberadamente em aberto, remetidos ao Capítulo 7 (Granularidade) e, em última instância, à calibração empírica com dados de anotação piloto.

## 3.7.3 Critério de não-sinonímia entre Processo e Habilidade _(referente a §3.4)_

Resolve a tensão registrada em §3.4 sem esperar pelo Capítulo 12. **Uma Habilidade Observável só é válida se especificar algo que a definição do Processo, sozinha, não determina**: (a) um formato concreto de estímulo/representação (tabela, gráfico, texto, fórmula, diagrama), (b) um tipo específico de ação/resposta esperada, ou (c) uma restrição contextual de aplicação. Teste prático: _se a descrição da Habilidade for obtida apenas parafraseando a do Processo, sem acrescentar nenhum dos três elementos acima, a Habilidade é redundante e deve ser removida — o Processo passa a ser mapeado diretamente ao item._ Corolário: um Processo com exatamente uma Habilidade não é automaticamente inválido, mas é sinalizado para a revisão de §3.7.2 — pode ser cobertura incompleta (ainda não se escreveram as demais manifestações) ou duplicata disfarçada.

---

# Capítulo 4 — Relações Permitidas

## 4.1 Princípio geral

Toda relação nesta ontologia precisa satisfazer um teste adicional ao de validade de nó (Capítulo 3): precisa corresponder a algo que o motor de crença do Sapiens consome, ou a algo que um humano navegando a ontologia precisa para se orientar. Nenhuma relação existe "por completude" — é a extensão, ao nível de aresta, do princípio de fechamento do Capítulo 2 (§2.5): unidades explicativas, não administrativas, e isso vale tanto para nós quanto para as ligações entre eles.

## 4.2 Nós formais e nós de referência externa

Seis tipos de nó são formalmente definidos por esta Constituição (Capítulo 3): Domínio, Competência, Processo Cognitivo, Habilidade Observável, Tipo de Erro, Intervenção Pedagógica. Dois objetos adicionais são referenciados nas relações abaixo sem pertencer a esta ontologia — Item/Questão e Resposta Observada — por decisão já registrada no Capítulo 1 (§1.3): o instrumento de medição e a evidência bruta não são objetos ontológicos, apenas pontos de ancoragem externos.

> **`[Errata 1.1]`** Registro de questão aberta, sem alteração do fechamento em seis tipos: o White Paper 1.0 definia um sétimo nível — o **Indicador Comportamental** (latência, padrão de erro, escolha de distrator, sequência de interação) — declarado ali como _"o nível que efetivamente alimenta os algoritmos de estimativa de domínio"_. Esse nível não existe aqui. Consequência verificada: os campos de desempenho do contrato de behavior não têm nó que os interprete, e o contrato declara explicitamente que eles são **coletados e não consumidos como evidência de crença**, por força de GL-3, aberto. A recuperação recomendada em `EXT-WP1-1.0` item L1 é **como camada transversal, nunca como sétimo tipo de nó** — o fechamento desta seção permanece intacto. Decisão diferida ao Capítulo 12.

## 4.3 Relações formalizadas

|Relação|Direção semântica|Cardinalidade|Peso/incerteza|Obrigatória?|Nota|
|---|---|---|---|---|---|
|**Processo Cognitivo ↔ Domínio**|Processo pertence a Domínio|N:M|Opcional (ex.: centralidade)|Sim — mínimo 1 Domínio por Processo|Direção heterárquica, não arborescente — um Processo pode pertencer a mais de um Domínio simultaneamente. Esta é uma correção deliberada em relação à v1.3, onde Domínio só se ligava a Competência: aqui a relação primária de pertencimento parte do Processo, unidade rastreável real (§3.3); Competência herda, não define, seu próprio pertencimento (ver §4.4). Validade sujeita ao teste de §3.7.1.|
|**Processo Cognitivo ↔ Competência**|Processo é agrupado por Competência|N:M|Não|Sim — mínimo 1 Competência por Processo|Esta é exatamente a relação cuja ausência a auditoria da v1.3 identificou como o achado estrutural mais crítico do dataset original. Sua existência é o que torna Competência recalculável, não arbitrária (§3.2).|
|**Processo Cognitivo ↔ Habilidade Observável**|Habilidade manifesta/instancia Processo|N:M (uma Habilidade pode manifestar mais de um Processo; um Processo idealmente manifesta-se em ≥2 Habilidades — gatilho de §3.7.2 quando não)|Obrigatório quando N>1 do lado da Habilidade: peso de papel (central/secundário)|Sim — mínimo 1 Habilidade por Processo ativo|Direção semântica: geral→específico (Processo→Habilidade). A implementação típica em banco de dados inverte isso como chave estrangeira (Habilidade referencia Processo) — convenção técnica, não mudança de significado; formalização exata é matéria da Especificação Técnica, não desta Constituição. Validade sujeita ao teste de §3.7.3.|
|**Processo Cognitivo ↔ Processo Cognitivo**|Tipada — tipo não definido nesta Constituição|N:M|Obrigatório quando presente (força/peso da dependência)|Não — a relação pode ou não existir para um par dado|A escolha da taxonomia de tipos (pré-requisito, facilitação, analogia, contradição, e outras já cogitadas em etapas anteriores deste projeto sem convergência) permanece questão aberta, remetida ao Capítulo 12. O que esta Constituição fixa como restrição inegociável, independentemente de qual taxonomia for adotada: **quando esta relação existir, deve ser tipada e ponderada — nunca uma aresta única e não diferenciada tratada implicitamente como "pré-requisito"**, que foi a falha estrutural mais repetida identificada ao longo de todo este projeto.|
|**Tipo de Erro → Processo Cognitivo** _(nível catálogo)_|Erro indica falha conceitualmente possível em Processo|N:M|Não (é relação de possibilidade, não de evidência)|Sim — mínimo 1 Processo por Tipo de Erro|Distinção central desta seção: existe um nível **catálogo** (estático, ontológico — quais erros são conceitualmente possíveis para este processo, definido em tempo de construção) e um nível **instância** (dinâmico, diagnóstico — qual erro específico explica esta resposta específica, calculado em tempo de execução). Esta linha é catálogo.|
|**Tipo de Erro → Habilidade Observável** _(nível catálogo, opcional)_|Erro caracteristicamente observado nesta manifestação|N:M|Opcional|Não|Refinamento opcional do item anterior — especifica o contexto de manifestação em que um erro tende a aparecer, sem substituir a relação obrigatória com Processo Cognitivo.|
|**Resposta Observada → Tipo de Erro** _(nível instância)_|Evidencia, com peso|N:M, obrigatoriamente ponderado|Obrigatório — nunca determinístico|Não aplicável aqui|**Esta relação resolve diretamente a restrição de engenharia 4.** Não se cria um novo tipo de nó ("camada intermediária") entre resposta e erro — a multiplicidade de causas é propriedade da própria relação: uma resposta errada pode evidenciar múltiplos Tipos de Erro candidatos simultaneamente, cada um com peso/confiança distinto, exatamente como o Axioma da Crença Calibrada do White Paper 2.0 já exige para qualquer proposição sobre estado. Esta relação não é aresta estática da ontologia — é produzida em tempo de execução pelo motor diagnóstico; sua especificação de schema pertence à Especificação Técnica, não a este documento. Ela é listada aqui apenas para que o princípio que a governa fique registrado nesta Constituição, não apenas na engenharia.|
|**Tipo de Erro → Intervenção Pedagógica**|Erro indica necessidade de Intervenção|N:M|Opcional (força de recomendação)|Sim — mínimo 1 Intervenção por Tipo de Erro ativo|Fecha o ciclo diagnóstico–remediação (§3.6).|

> **`[Errata 1.1]` — três resoluções de remissão, sem alteração de nenhuma regra da tabela.**
> 
> **(a) `Resposta Observada → Tipo de Erro`.** A remissão a uma "Especificação Técnica" está resolvida: o schema é a **`Especificação do Error Trace v1.0`**. Ela cumpre integralmente a exigência desta linha — ponderação obrigatória, nunca determinística — e **acrescenta a ordem causal**, que esta tabela não exigia e cuja ausência havia degradado o ativo protegido. Registro de precisão: um **conjunto ponderado** e uma **cadeia ordenada** não são o mesmo objeto; esta linha garante o primeiro, e a Especificação acrescenta o segundo sem contrariá-la.
> 
> **(b) `Processo Cognitivo ↔ Habilidade Observável`.** A "formalização exata" remetida à Especificação Técnica é o **Schema Sapiens 2.2**, bloco `estrutura_cognitiva.processos[].habilidades[]`.
> 
> **(c) `Processo Cognitivo ↔ Processo Cognitivo`.** A taxonomia de tipos permanece **questão aberta**, agora registrada no Capítulo 12 §12.7, que existe. Dois tipos candidatos com proveniência documentada (`frequentemente_confundidas_com` e `frequentemente_mascaradas_por`, White Paper 1.0 §2.6) estão **registrados como candidatos, não adotados** — `EXT-WP1-1.0` item L6. A restrição inegociável desta linha permanece: se a relação existir, tipada e ponderada.

## 4.4 Relações proibidas

- **Competência → Domínio, como atribuição direta e independente.** O Domínio de uma Competência é sempre **derivado** — herdado da união dos Domínios de seus Processos constituintes — nunca atribuído à parte. Atribuir Domínio diretamente a uma Competência reintroduziria o risco de inconsistência que sua natureza de agrupamento derivado (§2.1, §3.2) existe precisamente para prevenir: um humano poderia, com o tempo, atribuir um Domínio à Competência que diverge do Domínio real de seus Processos, e nada detectaria a divergência.
- **Habilidade Observável → Domínio, como atribuição direta.** Mesmo princípio, um nível abaixo: herdado do Processo que a Habilidade manifesta, nunca atribuído de forma independente.
- **Qualquer nó → "Conteúdo Disciplinar".** Não existe tal tipo de nó nesta ontologia (§1.3); informação de conteúdo específico pertence à descrição textual da Habilidade Observável ou ao `ItemCognitiveMapping` da Especificação Técnica, nunca a uma aresta formal aqui. Qualquer proposta futura de adicionar essa aresta deve ser lida como tentativa de reintroduzir, por via lateral, a conflação processo/conteúdo que motiva este documento inteiro.
- **Intervenção Pedagógica → Item/Questão, como atribuição direta.** Intervenções são indexadas a Tipo de Erro (e, por herança, a Processo Cognitivo) — nunca a um item específico. Vincular diretamente destruiria a transferibilidade entre contextos avaliativos que é a própria razão de existir da Intervenção Pedagógica (§3.6).
- **Qualquer relação diagnóstica com cardinalidade determinística de valor único** onde mais de um candidato é plausível (ex.: uma Resposta Observada atribuída a exatamente um Tipo de Erro, sem peso, quando dois eram compatíveis com a evidência). Proibida por violação direta do Axioma da Crença Calibrada.

> **`[Errata 1.1]`** Registro de violação corrigida, para memória de auditoria: o **Schema Sapiens 2.1** violava a última proibição desta seção — seu campo `distratores[].erro` admitia exatamente um identificador de erro por alternativa. Corrigido no **Schema 2.2** (`erros_esperados[]`, lista ordenada com confiança obrigatória por elo). O campo "Conteúdo Disciplinar" mencionado na terceira proibição está corretamente implementado como metadado de manifestação em `fonte.disciplina` do Schema 2.2, com proibição explícita de inferência a partir dele.

## 4.5 Síntese de pesos e incerteza

Duas classes de relação, tratadas de forma deliberadamente diferente:

**Relações de classificação/organização** (Processo↔Domínio, Processo↔Competência) — set-membership simples; peso é opcional e reservado a refinamento futuro (ex.: centralidade), nunca obrigatório, porque a função destas relações é navegação e agrupamento, não evidência.

**Relações diagnósticas/evidenciais** (Processo↔Habilidade quando N>1, Processo↔Processo quando presente, Resposta→Erro, opcionalmente Erro→Intervenção) — peso é obrigatório sempre que a cardinalidade permitir múltiplos candidatos simultâneos, porque estas são exatamente as relações que alimentam o motor de crença do White Paper 2.0. Tratar qualquer uma delas como binária/determinística reproduziria, dentro desta ontologia, o mesmo erro que a v1.3 cometeu ao tratar `processos_cognitivos` como array plano sem indicação de papel central ou secundário.

---

# Capítulo 5 — Critérios de Inclusão

## 5.0 Natureza deste capítulo

Este capítulo era invocado por §1.2 e §2.3 e não existia. Sob GOV-1.0 §1.4, uma remissão a conteúdo inexistente **não confere autoridade** — de modo que, até agora, "o critério formal de admissibilidade é objeto do Capítulo 5" era uma regra sem conteúdo.

**Este capítulo não cria nenhum critério novo.** Ele consolida, em sequência aplicável, critérios que já existem dispersos nos Capítulos 1 a 4 e no Adendo 3.7. Cada teste abaixo remete à seção que o estabelece, e a tabela de rastreabilidade do §5.8 fecha essa correspondência item a item. Se alguma linha deste capítulo não puder ser rastreada a uma seção anterior, é defeito deste capítulo, não critério novo — e deve ser removida.

O que este capítulo **não** faz: não fixa limiares numéricos (Capítulo 7), não define protocolo de validação empírica (Capítulo 11), não resolve nenhuma questão diferida (Capítulo 12).

## 5.1 Admissibilidade de Processo Cognitivo

Testes aplicados **nesta ordem**. A reprovação em qualquer um encerra a análise: o candidato não é admissível.

1. **Teste de unidade organizadora** _(§2.2)_ — a razão de existir do candidato é uma operação mental exigida, ou é uma disciplina, série ou sequência de ensino? Se a única justificativa for "isso é ensinado em X", reprovado.
2. **Teste de não-procedimento** _(§3.3)_ — o candidato nomeia uma operação mental, ou uma técnica, fórmula ou lei nomeada? "Aplicar regra de três", "balancear equação química" e "aplicar teorema de Pitágoras" são reprovados, mesmo quando tecnicamente bem redigidos.
3. **Teste de transferibilidade como candidatura** _(§2.3)_ — o candidato é hipoteticamente instanciável em pelo menos duas superfícies disciplinares distintas, sem depender de vocabulário, fórmula ou procedimento de nenhuma delas? Duas precisões vinculantes da mesma seção: semelhança formal entre itens **não** demonstra transferibilidade, e dependência de conhecimento de conteúdo **não** a invalida — o que se exige é separabilidade conceitual.
4. **Teste de independência** _(§2.4)_ — existe razão para esperar que o candidato se comporte de forma distinguível, sob evidência, dos processos já catalogados? Na **ausência de evidência**, a mesma seção fixa o ônus: dois candidatos que descrevem a mesma operação aplicada a conteúdos diferentes são **um único** Processo com múltiplas manifestações. A fusão é o padrão; a separação é que precisa ser justificada.
5. **Teste de não-realismo** _(§2.1, §3.3)_ — a formulação do candidato reivindica módulo, circuito ou estrutura psicológica real? Se sim, reformule como regularidade comportamental postulada, ou reprove.
6. **Teste de granularidade** _(§3.7.2)_ — os dois gatilhos se aplicam: fragmentação excessiva (uma única Habilidade, sem segunda manifestação plausível descritível) e fusão excessiva (componentes internos com padrões de erro ou pré-requisitos distintos). Os **limiares** que decidiriam casos de fronteira estão diferidos ao Capítulo 7; até então vale a regra de ausência de evidência do teste 4.
7. **Teste de fechamento** _(§2.5)_ — o candidato é unidade explicativa ou administrativa? Um candidato que sobrevive apenas por constar em versão anterior, por corresponder a disciplina reconhecida ou por facilitar redação curricular é reprovado.

**Resultado de aprovação:** o candidato entra como **hipótese testável**, nunca como fato (§2.3). Aprovação neste capítulo não é validação de construto.

## 5.2 Admissibilidade de Domínio

1. **Teste de operação, não fenômeno** _(§3.7.1)_ — o que os Processos agrupados têm em comum é descritível em uma frase que nomeia um tipo de operação ou relação mental, e não um tipo de fenômeno ou entidade do mundo real?
2. **Teste da conjunção** _(§3.7.1)_ — a descrição do que é comum exige enumerar classes de fenômeno unidas por "e"? Se sim, reprovado, e o candidato é candidato a subdivisão.
3. **Teste de coesão** _(§3.1)_ — existe operação mental unificadora identificável, ou o Domínio é amplitude sem coesão?
4. **Teste de função** _(§3.1)_ — o Domínio serve à orientação humana no grafo? Domínio não é unidade consumida pelo motor de crença; um Domínio justificado por necessidade de cálculo está mal classificado.

## 5.3 Admissibilidade de Habilidade Observável

1. **Teste de não-sinonímia** _(§3.7.3)_ — a Habilidade acrescenta ao menos um de: (a) formato concreto de estímulo ou representação, (b) tipo específico de ação ou resposta esperada, (c) restrição contextual de aplicação?
2. **Teste de paráfrase** _(§3.7.3)_ — se a descrição da Habilidade for obtida apenas parafraseando a do Processo, é redundante e deve ser removida.
3. **Teste de concretude** _(§3.4)_ — a redação é concreta o suficiente para orientar a anotação de uma questão real?
4. **Teste de herança** _(§4.4)_ — a Habilidade não recebe Domínio por atribuição direta; herda do Processo que manifesta.

## 5.4 Admissibilidade de Competência

Competência **não é curada**: é **derivada** (§2.1, §3.2, §4.4). Portanto não há teste de admissibilidade de conteúdo, e sim de forma:

1. **Teste de derivação** _(§3.2)_ — a Competência é recalculável a partir dos Processos que agrupa?
2. **Teste de herança de Domínio** _(§4.4)_ — seu Domínio é a união dos Domínios de seus Processos, nunca atribuição independente? Atribuição direta é **relação proibida**.
3. **Teste de coocorrência** _(§3.2)_ — os Processos agrupados tendem a coocorrer na resolução de um mesmo tipo de situação?
4. **Teste de agregação** _(§2.5)_ — um agrupamento derivado que agrupa **um único** Processo, com o mesmo nome desse Processo, não agrega nada e é candidato a nó administrativo. Registrado como caso a examinar no Capítulo 12.

## 5.5 Admissibilidade de Tipo de Erro

1. **Teste de sujeito** _(§3.5)_ — o candidato descreve falha **do aluno** ou propriedade **do item**? "Distrator plausível" é propriedade do item e reprovado aqui; seu lugar é o contrato do item.
2. **Teste de mecanismo, não conteúdo** _(§3.5)_ — o candidato nomeia mecanismo cognitivo generalizável ou falha em procedimento específico? "Erro de estequiometria" é reprovado.
3. **Teste de ancoragem** _(§4.3)_ — existe pelo menos um Processo Cognitivo ao qual o erro se ancora em catálogo? A relação `Erro → Processo` tem mínimo 1 e é obrigatória.
4. **Teste de não-exclusividade** _(§3.5, §4.4)_ — o candidato é apresentado como a **única** explicação possível de uma resposta? Atribuição determinística de valor único onde mais de um candidato é plausível é **relação proibida**.
5. **Teste de nível** _(§4.3)_ — o candidato pertence ao nível **catálogo** (erro conceitualmente possível), não ao nível instância (qual erro explica esta resposta). O nível instância não é aresta desta ontologia.

## 5.6 Admissibilidade de Intervenção Pedagógica

1. **Teste de indexação** _(§3.6, §4.4)_ — a Intervenção é indexada a Tipo de Erro ou a estado de baixa confiança em Processo? Indexação direta a Item/Questão é **relação proibida**.
2. **Teste de independência disciplinar** _(§3.6)_ — a Intervenção é aplicável independentemente da disciplina em que o erro ocorreu?
3. **Teste de escopo** _(§3.6)_ — a Intervenção é ação ou recurso, e não plano de aula ou conteúdo didático completo?
4. **Teste de cobertura** _(§4.3)_ — todo Tipo de Erro ativo tem ao menos uma Intervenção. A relação é obrigatória.

## 5.7 O que nunca é critério de inclusão

Consolidação de proibições já vigentes. Nenhuma destas razões, isolada ou combinada, admite um candidato:

|Razão inadmissível|Seção que a proíbe|
|---|---|
|Constar em versão anterior da ontologia|§2.5|
|Corresponder a uma disciplina, série ou unidade curricular|§2.2, §1.3|
|Facilitar a redação de currículo ou material editorial|§2.5|
|Corresponder a conteúdo declarativo, fórmula ou lei nomeada|§1.3, §3.3|
|Ter nome distinto de um nó existente|§2.4|
|Aplicar-se a conteúdo distinto de um nó existente|§2.4|
|Aparecer em uma matriz de referência externa|§1.3, §2.2|
|Descrever estado motivacional, afetivo ou momentâneo|§1.3|
|Descrever propriedade do instrumento de medição|§1.3, §3.5|
|Completar simetria ou "completude" da estrutura|§4.1|

## 5.8 Rastreabilidade

|Teste|Origem|
|---|---|
|5.1.1 unidade organizadora|§2.2|
|5.1.2 não-procedimento|§3.3|
|5.1.3 transferibilidade|§2.3|
|5.1.4 independência e ônus da fusão|§2.4|
|5.1.5 não-realismo|§2.1, §3.3|
|5.1.6 granularidade|§3.7.2 (limiares → Cap. 7)|
|5.1.7 fechamento|§2.5|
|5.2.1–5.2.2|§3.7.1|
|5.2.3–5.2.4|§3.1|
|5.3.1–5.3.2|§3.7.3|
|5.3.3|§3.4|
|5.3.4|§4.4|
|5.4.1, 5.4.3|§3.2|
|5.4.2|§4.4|
|5.4.4|§2.5|
|5.5.1–5.5.2, 5.5.4|§3.5|
|5.5.3, 5.5.5|§4.3|
|5.6.1|§3.6, §4.4|
|5.6.2–5.6.3|§3.6|
|5.6.4|§4.3|
|5.7 (todas)|§1.3, §2.2, §2.4, §2.5, §3.3, §3.5, §4.1|

**Nenhuma linha deste capítulo carece de origem.** A verificação é reproduzível: cada teste é uma reformulação em forma de pergunta de uma regra já escrita.

---

# Capítulo 7 — Granularidade

## 7.0 Natureza deste capítulo: deferimento declarado

O §3.7.2 remete a este capítulo os **limiares numéricos** de granularidade. Este capítulo **não os fixa**, e a razão não é omissão: é a mesma que o §3.7.2 já declara — _"fixar um número aqui seria cristalização prematura… forma exigida agora, valor calibrado depois, empiricamente."_

O que este capítulo faz é converter uma **remissão pendente** (que, sob GOV-1.0 §1.4, é regra sem conteúdo) em um **deferimento explícito**, com a regra que vale no intervalo e a condição de fechamento. Inventar os limiares aqui seria produzir conteúdo normativo dependente de dados que não existem.

## 7.1 O que está fixado hoje

Integralmente o §3.7.2, sem acréscimo: os dois gatilhos qualitativos — **fragmentação excessiva** (Processo com uma única Habilidade, sem segunda manifestação plausível descritível) e **fusão excessiva** (componentes internos com padrões de erro ou dependências de pré-requisito distintos, mesmo informalmente). Ambos são gatilhos de **sinalização para revisão**, não de ação automática.

## 7.2 O que está diferido, e a quê

|Limiar|Diferido a|
|---|---|
|Quantas Habilidades bastam por Processo|Calibração empírica com dados de anotação piloto (§3.7.2)|
|Quão distinto um padrão de erro precisa ser para justificar separação|Idem, e à distinguibilidade empírica que o White Paper 2.0 §5.5 nomeia sem quantificar|
|Profundidade de decomposição de um Processo em subprocessos|GL-11a do White Paper 2.0, **aberto** e condicional a GL-12a|
|Se a fronteira Processo/Habilidade é ontológica ou redundante|Registrado no Capítulo 12 §12.1|

## 7.3 Regra vigente no intervalo

Enquanto os limiares não existirem, decide o §2.4: **na ausência de evidência, a fusão é o estado padrão e a separação é que precisa ser justificada.** Um caso de fronteira que os gatilhos do §7.1 sinalizem, e que os limiares ausentes não resolvam, é **registrado como observação de campo** (Manual §13) e **permanece como está** — nunca decidido por preferência do curador.

## 7.4 Condição de fechamento

Este capítulo passa de deferimento a conteúdo quando: (i) o protocolo do Capítulo 11 tiver sido executado; (ii) houver medição de concordância interavaliador que identifique processos de baixa separabilidade e processos excessivamente amplos, como o White Paper 2.0 Cap. 16 prevê; e (iii) o Curador abrir transação de emenda substantiva sob GOV-1.0 §3.4. Nenhuma das três condições está satisfeita.

---

# Capítulo 11 — Validação

## 11.0 Natureza deste capítulo: deferimento declarado

O §2.3 remete a este capítulo o **teste** de transferibilidade — a validação do que a candidatura apenas hipotetiza. Este capítulo **não define o protocolo operacional**, porque ele é objeto de documento próprio, e **não pode inventá-lo**, porque isso exigiria fixar parâmetros amostrais e limiares estatísticos que nenhum documento do corpus estabelece.

Como o Capítulo 7, este capítulo converte remissão pendente em deferimento explícito, declarando o que já é vinculante, o que não está fixado, e onde a forma operacional será fixada.

## 11.1 O que já é vinculante

Do White Paper 2.0, Cap. 16, que declara sua metodologia mínima como **condição de entrada para qualquer expansão de escopo, não recomendação**:

1. Banco-piloto de itens a partir de fontes existentes;
2. **Anotação dupla e independente** por especialistas;
3. Medição de **concordância interavaliador** (coeficiente kappa), com identificação de processos de baixa separabilidade e de processos excessivamente amplos;
4. Ajuste da ontologia com base nesses resultados;
5. **Apenas então**, expansão de escopo.

Do mesmo capítulo, e do §19 daquele documento: exigência de **proveniência independente** da evidência de referência — comparar julgamento humano contra dado que o próprio julgamento ajudou a produzir invalida a comparação.

Do Manual §12, regra 5: o anotador **não consulta** a anotação de outro antes de finalizar a sua. A independência é pré-condição de validade da medição.

## 11.2 O que não está fixado em nenhum documento

Amostra mínima por Processo; número de anotadores; limiar de kappa que distingue concordância aceitável de inaceitável; critério de decisão que liga um valor de kappa a uma ação específica sobre o catálogo; composição do banco-piloto por Domínio.

O Manual §12, regra 5, remetia essa fixação a um "Plano de Validação" que não existe no corpus — `G-CONF-13`.

## 11.3 Forma operacional diferida

A forma operacional pertence a um **Protocolo de Piloto e Concordância**, documento de camada C4 ainda não escrito. Ele consumirá o Manual (protocolo de anotação), o Schema Sapiens (formato do dado) e a Especificação do Error Trace (formato do diagnóstico) — os três já existem e estão mutuamente consistentes.

## 11.4 Efeito no intervalo, sobre transferibilidade

Consequência direta e vinculante do deferimento, já estabelecida em §2.3 e aqui apenas explicitada: **enquanto este capítulo for deferimento, transferibilidade permanece candidatura e nunca validação.** Nenhum Processo do catálogo tem validade de construto estabelecida — o próprio White Paper 2.0 §18 declara isso. Qualquer afirmação de que um Processo "é transferível" é, hoje, hipótese; a forma correta é "foi admitido sob o critério de candidatura do §2.3".

## 11.5 Condição de fechamento

Existência do Protocolo de Piloto, sua execução, e transação de emenda sob GOV-1.0. Sob GOV-1.0 §11.2, mudanças de estrutura do catálogo são Classe B ou C e **exigem** essa evidência; mudanças de fidelidade e forma são Classe A e não.

---

# Capítulo 12 — Questões Diferidas

## 12.0 Natureza deste capítulo

**Registro, não decisão.** Este capítulo consolida as questões que os Capítulos 1 a 4 declararam não decidir, mais as que outros documentos canônicos mantêm abertas e que incidem sobre esta Constituição. Nenhuma linha abaixo é resolvida aqui. Uma questão sai deste capítulo apenas por transação de emenda registrada.

## 12.1 Diferidas pela própria Constituição

|#|Questão|Onde foi diferida|
|---|---|---|
|12.1.1|**Processo e Habilidade são níveis ontologicamente distintos, ou um é redundante?** A auditoria da v1.3 encontrou correspondência 1:1 em proporção alta dos casos|§1.2, §3.4 — remetidas explicitamente a este capítulo. O §3.7.3 fornece um teste operacional de não-sinonímia, que **mitiga** a questão sem resolvê-la|
|12.1.2|**Taxonomia de tipos da aresta `Processo ↔ Processo`** — pré-requisito, facilitação, analogia, contradição, outros|§4.3, remetida a este capítulo. Candidatos com proveniência registrada em `EXT-WP1-1.0` L6: `frequentemente_confundidas_com`, `frequentemente_mascaradas_por`. **Registrados, não adotados.** Restrição que vale desde já: se a relação existir, tipada e ponderada|
|12.1.3|**Limiares numéricos de granularidade**|§3.7.2 → Capítulo 7|
|12.1.4|**Protocolo de teste de transferibilidade**|§2.3 → Capítulo 11|
|12.1.5|**Instanciação da dimensão transversal Conhecimento** — declarada em §2.1, nunca implementada|Registrada aqui pela errata 1.1. Recuperação recomendada em `EXT-WP1-1.0` L9 (seis tipos de conhecimento). Emenda aditiva, não decidida|
|12.1.6|**Indicador Comportamental** — sétimo nível do White Paper 1.0, ausente do fechamento em seis tipos de nó do §4.2|Registrada aqui pela errata 1.1. Recuperação recomendada em `EXT-WP1-1.0` L1, **como camada transversal, nunca como tipo de nó**|
|12.1.7|**Competência que agrupa um único Processo** com nome idêntico ao dele — agrupamento que não agrega|Registrada aqui, teste 5.4.4. Quatro casos no catálogo vigente|

## 12.2 Diferidas pelo White Paper (incidem sobre esta Constituição)

Nove Graus de Liberdade abertos, mais dois condicionais, na ordem do Programa de Pesquisa: **GL-10** (natureza da dependência entre fatores — condiciona §4.3 e o campo de grau de transferência), **GL-12a** (multiplicidade dentro vs. entre tarefas — condiciona §2.3 e toda a derivação de domínios), **GL-9** (curadoria vs. descoberta de fatores — condiciona o próprio Capítulo 5), **GL-14** (atribuição suave vs. dura de causa de erro — condiciona §4.3, linha de nível instância), **GL-7** e **GL-5a** (decaimento e regimes temporais), **GL-15** (verossimilhança fixa vs. aprendida), **GL-11a** (profundidade recursiva — condiciona o Capítulo 7), **GL-12b** (universalidade de categorias entre domínios — **condição declarada da expansão para Humanas e Linguagens**). Condicionais: **GL-8** = f(GL-16), **GL-13** = f(GL-10).

Também aberta: a **função objetivo da camada de decisão** (White Paper 2.0 §6.3 e §12.4). Duas políticas candidatas estão registradas como `rebaixadas` a decisão de engenharia não derivada dos axiomas (`EXT-WP1-1.0` L10); a função objetivo permanece ausente.

## 12.3 Diferidas pela Ontologia vigente

As sete questões da Ontologia v1.4.1 §10: limiares de granularidade; possível divisão de `PROC-INC-02`; cobertura parcial de Tipo de Erro (13 dos 25 processos); multiplicidade real de pertencimento Processo↔Domínio, hoje implementada majoritariamente 1:1; taxonomia de aresta Processo↔Processo; fronteira `DOM-CLASSIF` × estrutura-função; fronteira `DOM-CAUSAL` × `DOM-EXPERIMENTAL`.

As duas últimas são **fronteiras de domínio**, portanto matéria desta Constituição, e são o objeto do §12.4 abaixo.

## 12.4 Fronteiras sob convenção provisória de camada operacional

O Manual §11 adota regras de desempate para duas fronteiras que a Ontologia mantém em aberto: `DOM-CAUSAL` × `DOM-EXPERIMENTAL` e `PROC-CLASSIF-01` × `PROC-ESPACO-03`.

Estatuto, conforme GOV-1.0 §1.3: são **convenções provisórias de camada C4**, declaradas como tais, que **não vinculam** esta Constituição, e estão registradas como pendência de arbitragem no changelog da Ontologia. Existem para tornar a anotação executável, não para decidir a fronteira.

**A arbitragem definitiva é matéria desta Constituição** e depende de evidência de piloto (GOV-1.0 §11.2, Classe B). Não é feita aqui. Registrada como `G-CONF-06`, e como item `D-4` do Manual.

## 12.5 Incidentes de identidade

Registrados em `09 Mapa de Rastreabilidade de IDs` e reproduzidos aqui por incidirem sobre esta Constituição:

|Incidente|Descrição|Efeito sobre esta Constituição|
|---|---|---|
|`MAP-INC-01`|`DOM-CLASSIF` reutilizado após crítica nominal no §3.1|Esclarecido pela errata 1.1 no §3.1|
|`MAP-INC-03`|`PROC-ESTR-001` declarado preservado pelo White Paper 2.0 e **ausente** do catálogo vigente|É o nó cuja função declarada é a transferência estrutural — o mecanismo que o §2.3 usa para definir admissibilidade. Decisão pertence à próxima versão da ontologia|
|`MAP-INC-06`|`ERR-05` e `ERR-13` com significados diferentes entre v1.3 e v1.4|Vedado prospectivamente por GOV-1.0 §5.3|
|`MAP-INC-02`, `MAP-INC-05`, `MAP-INC-07`|Mapas de origem incompletos entre v1.3 e v1.4 (processos, habilidades, intervenções)|Dependem da v1.3, ausente|
|`MAP-INC-04`|White Paper 1.0 §4.5 declara 28 processos e enumera 29|Registro apenas|

## 12.6 Cadeia de proveniência rompida

`G-CONF-09`: os 25 processos da Ontologia v1.4.1 portam `origem_v1_3` apontando para identificadores de uma versão **ausente do corpus canônico**. As remissões desta Constituição a identificadores G2 (§1.1, §2.2, §2.4, §3.1) são igualmente pendentes. Sob GOV-1.0 §9.4, a cadeia está rompida e **toda equivalência entre gerações G0/G1 e G3 é `EQUIVALÊNCIA NÃO ESTABELECIDA`**.

Resolução possível: localizar a v1.3 e incorporá-la ao corpus em estado `superseded`, ou declarar formalmente a cadeia como irrecuperável. Nenhuma das duas foi feita.

## 12.7 Expansão de escopo — não autorizada

Registrado para que não seja lido como omissão: a expansão da ontologia para novas áreas do conhecimento é mudança de **Classe C** sob GOV-1.0 §11.2, e exige piloto concluído **mais** resolução registrada do Grau de Liberdade específico — no caso de Ciências Humanas e Linguagens, **GL-12b**, aberto.

Nenhuma das condições está satisfeita: não há piloto executado, não há kappa medido, GL-12b permanece aberto. A expansão **não está autorizada** por esta Constituição.

Registro adicional, sem efeito autorizante: a Matriz de Referência do ENEM é **material de apoio externo** (GOV-1.0 §1.1) e serve como instrumento de teste de cobertura. Aparecer em uma matriz externa **nunca** é critério de inclusão (§5.7).

---

# Changelog

|TX|Timestamp|Classe|Alteração|
|---|---|---|---|
|`TX-2026-08-17T184459Z-constituicao-v1.1`|2026-08-17T18:44:59Z|III — Emenda Aditiva, com itens de Classe II|**(1)** **Capítulo 5 criado** — consolidação de critérios de inclusão já dispersos nos Caps. 1–4 e no Adendo 3.7, com tabela de rastreabilidade (§5.8). Nenhum critério novo. **(2)** **Capítulo 7 criado** como deferimento declarado dos limiares de granularidade, com regra vigente no intervalo (§2.4) e condição de fechamento. Nenhum limiar fixado. **(3)** **Capítulo 11 criado** como deferimento declarado do protocolo de validação, com o que já é vinculante (White Paper 2.0 Cap. 16) e o que não está fixado. Nenhum parâmetro inventado. **(4)** **Capítulo 12 criado** como registro de questões diferidas. Nenhuma decisão. **(5)** `G-CONF-05` encerrado: as quatro remissões a capítulos inexistentes deixam de ser pendentes. **(6)** Erratas de remissão: §3.4, §3.5 e §4.3 remetiam a uma "Especificação Técnica" inexistente — agora resolvidas para `Especificação do Error Trace v1.0` e `Schema Sapiens 2.2`. `G-CONF-04` encerrado. **(7)** Errata no §3.1: esclarecida a reutilização dos identificadores `DOM-CLASSIF` e `DOM-SISTEMICO` na v1.4 com definições conformes (`MAP-INC-01`). **(8)** Erratas de geração de identificador em §1.1 e §12.6 (`G-CONF-09`). **(9)** Registro de questão aberta em §2.1 (dimensão Conhecimento) e §4.2 (Indicador Comportamental), sem alterar o fechamento em seis tipos de nó. **(10)** Cabeçalho canônico e changelog (GOV-1.0 §7.1, §7.3).|

**Capítulos 1 a 4 e Adendo 3.7 preservados na íntegra.** Nenhuma seção foi renumerada. Nenhum critério de admissibilidade foi criado, alterado ou removido. Nenhum Grau de Liberdade foi fechado. Nenhum elemento do catálogo ontológico foi tocado. A expansão para novas áreas permanece não autorizada.