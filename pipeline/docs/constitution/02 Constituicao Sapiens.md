
# Constituição da Ontologia Sapiens
# Capítulo 1 — Objetivo da Ontologia

## 1.1 O problema que ela resolve

A organização curricular por disciplina tem origem administrativa, não cognitiva — a "gramática da escolarização" documentada por Tyack & Cuban (1995) consolidou-se por razões de escala de gestão escolar, não por corresponder a como o conhecimento é estruturado na mente. A consequência prática já foi observada empiricamente, não apenas argumentada em abstrato, na própria auditoria da v1.3 deste projeto: o mesmo padrão cognitivo (estrutura→função, por exemplo) apareceu fragmentado em quatro lugares diferentes do dataset (COMP-19, COMP-21, PROC-41, PROC-46), sem que a arquitetura reconhecesse que era a mesma coisa manifestando-se em contextos distintos. E o inverso também ocorreu: rótulos que pareciam categorias cognitivas (PROC-29 a PROC-50) eram, no exame direto do dado, nomes de tópico disciplinar — o campo `categoria` mudava de natureza na metade exata da lista, sem que nenhum mecanismo estrutural detectasse a mudança de convenção.

O problema que esta ontologia existe para resolver é, portanto, específico e testável, não retórico: **fornecer um vocabulário e uma gramática estrutural para dimensões cognitivas latentes de desempenho que sejam (a) independentes da superfície disciplinar em que se manifestam, (b) reutilizáveis entre essas superfícies, e (c) empiricamente distinguíveis de dimensões adjacentes** — conhecimento de conteúdo, estratégia procedimental específica, estado momentâneo de desempenho.

Esta formulação não é nova a este documento: é exatamente a exigência de multidimensionalidade distinguível já estabelecida como parte da fundamentação teórica do Sapiens (Axioma da Fatoração). O que este documento acrescenta é a camada que faltava entre a exigência abstrata — "deve haver múltiplos fatores latentes distinguíveis" — e a prática de curadoria — "como um humano decide, de forma reproduzível, se um candidato a fator satisfaz essa exigência." A ontologia é a instância nomeada e auditável desses fatores; esta Constituição é o conjunto de regras que decide quais nomeações são admissíveis.

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

Ajustes incorporados ao Capítulo 2 (texto completo abaixo, não apenas o trecho alterado, para que o capítulo permaneça um artefato íntegro). Em seguida, o Capítulo 3.

---

# Capítulo 2 — Princípios Filosóficos _(revisado)_

## 2.1 As cinco categorias e o critério que as separa

A confusão mais cara encontrada na auditoria da v1.3 não foi falta de rigor — foi ausência de um critério explícito para saber a qual categoria um candidato pertence antes de nomeá-lo. Este capítulo fornece esse critério; o Capítulo 3 lhe dá forma de definição.

As cinco categorias não se distinguem por nível de generalidade (mais amplo/mais específico), mas por **função dentro do sistema**:

- **Conhecimento** não é um nível hierárquico — é uma dimensão transversal que classifica _como_ algo é sabido (declarativo, procedimental, condicional, estratégico/metacognitivo), aplicável a qualquer nó de qualquer nível. Tratar tipo de conhecimento como se fosse mais um degrau na hierarquia foi, precisamente, um dos mecanismos pelos quais a v1.3 perdeu coerência interna — a dimensão "o que se sabe" foi confundida com a dimensão "onde isso se organiza".
    
- **Competência** agrupa, para fins de comunicação curricular e navegação humana, um feixe recorrente de processos cognitivos que tendem a coocorrer na resolução de um mesmo tipo de situação. **Esta Constituição adota, como posição operativa a partir deste ponto — não como observação lateral —: Competência é tratada como agrupamento derivado, não como entidade ontológica fundamental.** Ela não possui poder explicativo próprio além do que herda dos processos cognitivos que agrupa; não é, portanto, rastreada pelo motor de crença como unidade independente de estado. Esta posição é adotada com grau de confiança parcial, não como fato estabelecido: o White Paper 2.0 registra a hipótese de rebaixamento de "Competência" a agrupamento derivado com confiança de 55% — insuficiente para tratar como conclusão fechada, suficiente para governar o trabalho de definição formal do Capítulo 3. Se evidência futura invalidar essa hipótese, é o Capítulo 4 (Relações) que precisará ser revisado — não os fundamentos deste capítulo.
    
- **Processo Cognitivo** é a unidade candidata a transferível — a operação mental cuja identidade não depende da superfície disciplinar em que aparece. **Nota de escopo, a ser mantida em toda expansão futura desta ontologia: "Processo Cognitivo" é uma unidade funcional de análise de desempenho, não uma afirmação neuropsicológica.** Nomear um processo não é reivindicar a existência de um módulo, circuito ou substrato neural correspondente — é postular uma regularidade suficientemente estável no comportamento observável para justificar rastreamento e intervenção. Esta distinção não é nova: estende ao nível operacional da ontologia a mesma fronteira que o White Paper 2.0 já declara em sua Parte I — a de que a arquitetura Sapiens é um sistema representacional funcional para fins de engenharia, não um modelo da mente real.
    
- **Habilidade Observável** é a manifestação mensurável de um processo em um contexto avaliativo determinado — o ponto em que a operação mental encontra um item real.
    
- **Conteúdo Disciplinar** não é uma categoria da ontologia cognitiva; é o material através do qual um processo se manifesta, e existe nesta Constituição apenas como o termo contra o qual a transferibilidade (2.3) é definida por contraste.
    

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

## 3.5 Tipo de Erro

**O que é.** Uma categoria diagnóstica que descreve um mecanismo de falha em um Processo Cognitivo, ou na aplicação deste a uma Habilidade Observável específica — a unidade que torna uma resposta errada informativa sobre _qual_ operação mental não ocorreu como esperado, não apenas sobre _que_ a resposta estava errada.

**O que não é.** Não é uma propriedade do item avaliativo — a auditoria da v1.3 identificou um caso claro dessa confusão ("distrator plausível", que descreve qualidade da alternativa incorreta, não falha do aluno). Não é um rótulo de conteúdo disciplinar ("erro de estequiometria", "confusão entre proporção direta e inversa") — a mesma auditoria encontrou pelo menos cinco tipos de erro, de treze catalogados, violando este critério ao nomear falha em procedimento específico em vez de mecanismo cognitivo generalizável. Não é, tampouco, a única explicação possível de uma resposta observada — o White Paper 2.0 trata atribuição de causa de erro como distribuição de confiança sobre múltiplas causas candidatas, não como rótulo único e determinístico (matéria da Especificação Técnica, não desta Constituição).

**Função na ontologia.** Alimenta o mecanismo de Error Trace, ativo protegido do projeto Sapiens desde o White Paper 2.0 — é o objeto que conecta evidência observada (a resposta errada) de volta à distribuição de crença sobre qual Processo Cognitivo falhou, e por qual mecanismo.

## 3.6 Intervenção Pedagógica

**O que é.** Uma ação ou recurso pedagógico indexado a um Tipo de Erro, ou a um estado de baixa confiança em um Processo Cognitivo específico — a resposta do sistema à pergunta "dado este diagnóstico, o que fazer".

**O que não é.** Não é um plano de aula nem conteúdo didático completo. Não é definida por disciplina ou tópico — uma intervenção indexada a "erro de leitura literal deficiente", por exemplo, deve ser aplicável independentemente de a leitura deficiente ter ocorrido em um enunciado de matemática ou de ciências.

**Função na ontologia.** Fecha o ciclo diagnóstico–remediação. É consumida por uma camada de decisão pedagógica que o White Paper 2.0 reconhece explicitamente como ainda não especificada (o "slot vazio" da função objetivo de decisão) — dentro desta ontologia, a Intervenção Pedagógica existe como candidata de ação associada a um diagnóstico, não como política de seleção automática entre candidatas.


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

## 4.4 Relações proibidas

- **Competência → Domínio, como atribuição direta e independente.** O Domínio de uma Competência é sempre **derivado** — herdado da união dos Domínios de seus Processos constituintes — nunca atribuído à parte. Atribuir Domínio diretamente a uma Competência reintroduziria o risco de inconsistência que sua natureza de agrupamento derivado (§2.1, §3.2) existe precisamente para prevenir: um humano poderia, com o tempo, atribuir um Domínio à Competência que diverge do Domínio real de seus Processos, e nada detectaria a divergência.
- **Habilidade Observável → Domínio, como atribuição direta.** Mesmo princípio, um nível abaixo: herdado do Processo que a Habilidade manifesta, nunca atribuído de forma independente.
- **Qualquer nó → "Conteúdo Disciplinar".** Não existe tal tipo de nó nesta ontologia (§1.3); informação de conteúdo específico pertence à descrição textual da Habilidade Observável ou ao `ItemCognitiveMapping` da Especificação Técnica, nunca a uma aresta formal aqui. Qualquer proposta futura de adicionar essa aresta deve ser lida como tentativa de reintroduzir, por via lateral, a conflação processo/conteúdo que motiva este documento inteiro.
- **Intervenção Pedagógica → Item/Questão, como atribuição direta.** Intervenções são indexadas a Tipo de Erro (e, por herança, a Processo Cognitivo) — nunca a um item específico. Vincular diretamente destruiria a transferibilidade entre contextos avaliativos que é a própria razão de existir da Intervenção Pedagógica (§3.6).
- **Qualquer relação diagnóstica com cardinalidade determinística de valor único** onde mais de um candidato é plausível (ex.: uma Resposta Observada atribuída a exatamente um Tipo de Erro, sem peso, quando dois eram compatíveis com a evidência). Proibida por violação direta do Axioma da Crença Calibrada.

## 4.5 Síntese de pesos e incerteza

Duas classes de relação, tratadas de forma deliberadamente diferente:

**Relações de classificação/organização** (Processo↔Domínio, Processo↔Competência) — set-membership simples; peso é opcional e reservado a refinamento futuro (ex.: centralidade), nunca obrigatório, porque a função destas relações é navegação e agrupamento, não evidência.

**Relações diagnósticas/evidenciais** (Processo↔Habilidade quando N>1, Processo↔Processo quando presente, Resposta→Erro, opcionalmente Erro→Intervenção) — peso é obrigatório sempre que a cardinalidade permitir múltiplos candidatos simultâneos, porque estas são exatamente as relações que alimentam o motor de crença do White Paper 2.0. Tratar qualquer uma delas como binária/determinística reproduziria, dentro desta ontologia, o mesmo erro que a v1.3 cometeu ao tratar `processos_cognitivos` como array plano sem indicação de papel central ou secundário.
