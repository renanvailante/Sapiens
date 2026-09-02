---

## id: WP-2.0.1 titulo: White Paper Sapiens versao: 2.0.1 estado: congelado camada: C1 criado_em: 2026-08-17T02:58:05Z atualizado_em: 2026-08-17T18:44:58Z supersedes: ["WP-1.0"] superseded_by: null derivado_de: null governado_por: GOV-1.0 aparato_de_referencias: "herdado do White Paper 1.0 (blocos de Referências dos Capítulos 1, 2 e 4). Ver §21." geracao_de_ids: "G0 e G1 — os identificadores citados na Parte V NÃO são resolvíveis contra o catálogo vigente. Ver §21.2." changelog_ref: TX-2026-08-17T184458Z-wp2-errata remissoes_pendentes: []

# White Paper Sapiens — v2.0.1

> **Natureza desta versão.** A 2.0.1 é uma **errata** (GOV-1.0 §3.3, Classes I e II) sobre a 2.0. **Nenhum axioma foi alterado. Nenhum grau de confiança foi reponderado. Nenhum Grau de Liberdade foi fechado ou aberto.** As correções incidem sobre afirmações de fato que a auditoria integral do corpus verificou como incorretas ou vencidas, sobre remissões, e sobre o aparato de referências. Cada uma aparece em bloco marcado **`[Errata 2.0.1]`**, sem remover o texto original — para que o registro do que foi afirmado, e quando, seja preservado. Detalhe em `TX-2026-08-17T184458Z-wp2-errata`.

# Estrutura Consolidada do Documento

## Axiomas

Dois, mais um espaço deliberadamente vazio. Axioma da Crença Calibrada (confiança: 90%); Axioma da Fatoração (confiança: 90%); independência mútua estabelecida por contraexemplo (confiança: 85%); nenhum axioma unificador encontrado após duas tentativas (confiança de inexistência: 70%); função objetivo da camada de decisão — não é um terceiro axioma, é lacuna reconhecida sem conteúdo.

> **`[Errata 2.0.1]`** A expressão "lacuna reconhecida **sem conteúdo**" é imprecisa e está corrigida em §6.3. O conteúdo existia no White Paper 1.0 e não foi examinado nesta consolidação. A lacuna é de **derivação axiomática**, não de conteúdo.

## Definições

- **Calibração**: confiança relatada corresponde a frequência real observada — aceita, nunca contestada.
- **Fatoração (tipo do objeto)**: tupla de fatores latentes parcialmente correlacionados — aceita quanto à forma. A instância específica (operação/domínio/subcomponente/contexto) permanece hipótese de trabalho (40%), não definição fechada.
- **Disciplina EC/IT/DE**, estendida aos próprios axiomas — aceita, nunca contestada em nenhuma rodada.
- **Correção necessária antes de congelar**: na consolidação anterior, "Competência como agrupamento derivado, não nível ontológico primário" apareceu listada como definição aceita. Isso estava errado. É uma hipótese sob auditoria (55%), condicionada a GL-12a e GL-9, e é corrigida aqui para essa categoria — não entra no documento como fato.

## Pressupostos epistemológicos

Quatro, nenhum derivado dos axiomas: unidade de análise = estudante individual; evidência primária = resposta a item; interpretabilidade simbólica = valor de projeto, não necessidade teórica; existência de estrutura cognitiva latente estável e nomeável = pressuposto representacionalista nunca testado contra alternativas (cognição situada/enativa). Um quinto item de escopo — se a camada de decisão pedagógica pertence a este documento — permanece decisão não tomada, não pressuposto silencioso.

## Graus de liberdade resolvidos

Sete: GL-4, GL-5b (família matemática — classe de equivalência demonstrada), GL-5c, GL-11b, GL-18 (parâmetros e critérios quantificados — deferidos por norma geral de teorização), GL-6 (herdado de GL-4), GL-17 (herdado do próprio escopo do Axioma da Crença).

## Graus de liberdade abertos

Nove, mais dois condicionais. Detalhe completo na Parte III.

## Limites declarados

Domínio: Matemática e Ciências da Natureza. Metade da teoria (crença) especificada; metade (decisão/ação) vazia. Causalidade, se existir, vale par a par — a forma geral da pergunta pode não ser respondível por experimento único. Unidade de análise e canal de evidência: individual, resposta a item — nunca testados contra alternativas.

---

# PARTE II — Os Axiomas

## 4. Axioma da Crença Calibrada

### 4.1 Definição formal e escopo

Para toda proposição Q sobre (i) o estado cognitivo de um estudante ou (ii) a validade de uma relação estrutural dentro do espaço de conhecimento representado, o sistema não armazena um valor de verdade fixo nem um escalar determinístico. Armazena uma distribuição de confiança P(Q | E_t), condicionada ao conjunto de evidência E_t acumulado até o instante t, sujeita a duas condições:

**(a) Revisão** — P(Q | E_t) muda quando E_t muda; nenhuma proposição no escopo do axioma é permanentemente verdadeira ou falsa. **(b) Calibração** — a confiança relatada corresponde, em algum sentido empiricamente mensurável, à frequência real: um evento ao qual o sistema atribui confiança x deve ocorrer, em amostra suficientemente grande de casos análogos, a taxa próxima de x.

_Grau de confiança: 90%._ Base: presente nos quatro capítulos do material examinado; identificado por fonte de crítica independente como a lacuna mais consequente do corpus original.

### 4.2 O que o axioma exige e o que não exige

Exige que existam pelo menos três escopos possíveis de proposição, com velocidades de revisão potencialmente distintas — estrutural (sobre o espaço de conhecimento), de traço individual (sobre o estado relativamente estável do estudante) e momentâneo (sobre condições transitórias) — sem fixar a priori quantos regimes distintos realmente existem nem onde ficam suas fronteiras (§4.4).

Não exige nenhuma família matemática específica. Bayesiano, frequentista com intervalo de confiança, lógica fuzzy/possibilística e conformal prediction satisfazem igualmente 4.1(a)/(b); nenhuma foi eliminada por qualquer teste realizado. _A associação deste axioma a inferência bayesiana especificamente foi revista e rebaixada: 35%._

Não exige decaimento temporal automático — um sistema que nunca "esquece" satisfaz formalmente (a)/(b) desde que ainda revise confiança à luz de evidência nova. Se decaimento é necessário na prática permanece em aberto (§4.4).

### 4.3 Família matemática de formalização — [Programa de Pesquisa, GL-4/GL-5b — classificado como Resolvido]

Equivalência funcional demonstrada entre quatro famílias candidatas para a versão do axioma descrita em 4.1–4.2, para a formulação despida de compromisso bayesiano. A escolha entre elas é decisão de implementação, não consequência axiomática.

### 4.4 Escalas temporais de atualização — [Programa de Pesquisa, GL-5a e GL-7 — abertos]

Em aberto: se existem regimes de velocidade genuinamente distintos e quantos (GL-5a); se decaimento é propriedade obrigatória ou apenas compatível com o axioma (GL-7). Nenhuma das duas perguntas decidida.

> **`[Errata 2.0.1]`** Registro de proveniência, sem efeito sobre o estado de GL-5a e GL-7, que **permanecem abertos**: o White Paper 1.0 §2.9.1 propunha uma resposta operacional candidata a ambos — um enum de estado de maestria com os valores `automatizado` e `esquecimento_provavel`, ancorado em Fitts & Posner (1967). Essa proposta não foi examinada nesta consolidação. Ela é **hipótese candidata a teste**, não resposta. Registrada em `EXT-WP1-1.0`, item L11.

---

## 5. Axioma da Fatoração

### 5.1 Definição formal e escopo

O desempenho observável de um estudante em uma tarefa T não é descrito adequadamente por uma única variável latente escalar "competência(T)". É descrito por uma tupla de fatores latentes distintos, parcialmente — não totalmente — correlacionados entre si.

_Grau de confiança: 90%._ Base: a crítica mais repetida por contagem bruta no corpus originalmente examinado, presente nos quatro capítulos.

### 5.2 O que o axioma exige e o que não exige

Exige: pluralidade de fatores latentes distinguíveis; um critério de distinguibilidade fundamentado em evidência, não em convenção editorial.

Não exige relação causal no sentido interventivo/contrafactual entre fatores. _Grau de confiança neste qualificador adicional: 35%_ — a maior parte do conteúdo do axioma é satisfeita por fatoração preditiva/associativa clássica.

Não exige que os fatores sejam simbólicos, nomeados ou auditáveis por humano — tipagem simbólica é escolha de valor de projeto (interpretabilidade), não consequência lógica (ver Pressupostos Epistemológicos, item de interpretabilidade).

### 5.3 Origem dos fatores — [Programa de Pesquisa, GL-9 — aberto]

Curadoria especialista vs. descoberta orientada a dados. Não decidido.

### 5.4 Natureza da dependência entre fatores — [Programa de Pesquisa, GL-10 — aberto]

**Nota de escopo obrigatória**: a pergunta em sua forma mais geral pode não ser respondível por um único experimento; qualquer evidência obtida provavelmente valerá par a par, não universalmente. Isto não é uma limitação de método a corrigir — é um limite declarado da própria pergunta.

### 5.5 Profundidade recursiva da fatoração — [Programa de Pesquisa, GL-11a — aberto, condicional a §5.6]

### 5.6 Multiplicidade dentro da tarefa vs. entre tarefas — [Questão Aberta central do Axioma da Fatoração, GL-12a]

Bifurcação de maior alcance dentro deste axioma: se múltiplos fatores coexistem na geração de uma única resposta (leitura forte) ou se a multiplicidade só aparece entre tarefas distintas, sendo cada tarefa bem-construída adequadamente explicada por um fator dominante (leitura fraca — compatível com arquiteturas psicométricas já estabelecidas na literatura). Não decidido. Toda a Parte V (aplicação a domínios) deve ser lida como condicionada a esta pergunta permanecer aberta.

### 5.7 Universalidade das categorias entre domínios — [Programa de Pesquisa, GL-12b — aberto]

---

## 6. Independência entre os axiomas e o slot vazio

### 6.1 Prova de independência mútua

Estabelecida por construção de contraexemplo em ambas as direções: existe sistema que satisfaz integralmente o Axioma da Crença Calibrada sem satisfazer o da Fatoração (representação probabilística completa de variável latente única); existe sistema que satisfaz integralmente o Axioma da Fatoração sem satisfazer o da Crença Calibrada (fatores tipados e distintos, cada um avaliado por valor fixo determinístico).

_Grau de confiança: 85%_ — não superior, porque a operacionalização da fronteira de granularidade dentro da Fatoração (§5.5/5.6) importa maquinário de teste estatístico próprio do Axioma da Crença Calibrada. A independência das afirmações centrais se sustenta; suas operacionalizações completas não são inteiramente autocontidas uma em relação à outra.

### 6.2 Tentativas de unificação e por que falharam

Duas tentativas de formular um axioma único mais fundamental foram exploradas e rejeitadas. Um candidato inspirado em parcimônia descritiva explica o Axioma da Crença Calibrada, mas não impõe a multidimensionalidade exigida pelo da Fatoração — um sistema poderia satisfazê-lo adicionando precisão numérica a um único fator, sem adicionar fator novo. Um segundo candidato ("o sistema deve ser um modelo gráfico probabilístico causal") foi rejeitado por não constituir derivação: nomeia uma classe de objetos que já possui as duas propriedades por construção, sem explicar por que deveriam coocorrer.

_Grau de confiança de que nenhum axioma unificador existe: 70%_ — busca limitada a duas tentativas; ausência de resultado positivo não é prova de inexistência.

### 6.3 A função objetivo da camada de decisão — slot deliberadamente vazio

Os dois axiomas especificam inteiramente a metade "representação de crença" de um sistema adaptativo. Nenhuma evidência no corpus examinado sustenta uma formulação de como o sistema deveria selecionar a próxima ação pedagógica a partir dessa crença. Este documento registra a ausência como lacuna reconhecida — não como axioma a inventar, nem como conteúdo implicitamente coberto pelos dois axiomas existentes.

> **`[Errata 2.0.1]` — correção de afirmação de fato.**
> 
> A frase _"nenhuma evidência no corpus examinado sustenta uma formulação de como o sistema deveria selecionar a próxima ação pedagógica"_ é **incorreta em relação ao White Paper 1.0**, e a auditoria integral do corpus (`AUD-2026-08-17T03:42:31Z`) a verificou como tal.
> 
> O White Paper 1.0 especificava duas políticas concretas, com ancoragem em literatura: o **motor de recomendação** (§2.9.3, item 5) — seleciona o próximo processo entre os nós cujos pré-requisitos estão acima do limiar de domínio e cujo próprio valor está abaixo, como proxy computacional explícito da Zona de Desenvolvimento Proximal, ancorado em Doignon & Falmagne (1985) e Vygotsky (1978) — e o **agendador de revisão espaçada** (§2.9.3, item 6), com curva de esquecimento parametrizada por Cepeda et al. (2006) e interleaving conforme Rohrer & Taylor (2007). As features de entrada estão em §2.9.7.
> 
> **A conclusão substantiva desta seção permanece válida e não muda**: essas políticas **não são deriváveis dos dois axiomas**. São `[DE]` — decisão de engenharia. O erro estava em declará-las inexistentes em vez de **rebaixadas**.
> 
> Sob GOV-1.0 §9.2, o status correto do elemento na transição 1.0 → 2.0 é **`rebaixado`**: deixou de ser especificação e passou a ser proposta de engenharia não derivada dos axiomas. Esse status não existia como categoria disponível na época da consolidação, e o elemento foi tratado como inexistente.
> 
> **Estado após esta errata:** o slot permanece vazio quanto à **função objetivo** — o critério pelo qual o sistema escolhe. Uma política particular não fornece uma função objetivo, e nada aqui a fornece. O que se corrige é a alegação de ausência de conteúdo. Registro completo em `EXT-WP1-1.0`, item L10.

---

# PARTE III — Do Axioma ao Espaço de Decisão

## 7. Mapa completo dos graus de liberdade

Vinte e duas unidades atômicas (dezoito perguntas originais; GL-5, GL-11 e GL-12 desdobrados por conterem mais de uma pergunta em nível lógico distinto).

|GL|Classificação|Localização no documento|
|---|---|---|
|GL-1|Decisão de escopo|Parte I §2.4|
|GL-2|Decisão de escopo|Parte I §2.1|
|GL-3|Decisão de escopo (com resíduo empírico menor, não priorizado)|Parte I §2.2|
|GL-4|Resolvido|Parte II §4.3|
|GL-5a|Programa de pesquisa|Parte II §4.4|
|GL-5b|Resolvido|Parte II §4.3|
|GL-5c|Resolvido (parâmetro)|—|
|GL-6|Resolvido (herdado de GL-4)|§8|
|GL-7|Programa de pesquisa|Parte II §4.4|
|GL-8|Condicional — f(GL-16)|§9|
|GL-9|Programa de pesquisa|Parte II §5.3|
|GL-10|Programa de pesquisa (nota de escopo: geral pode ser irresolúvel)|Parte II §5.4|
|GL-11a|Programa de pesquisa|Parte II §5.5|
|GL-11b|Resolvido (parâmetro)|—|
|GL-12a|Programa de pesquisa — questão aberta central|Parte II §5.6|
|GL-12b|Programa de pesquisa|Parte II §5.7|
|GL-13|Condicional — f(GL-10)|§9|
|GL-14|Programa de pesquisa (estatuto especial: ambiguidade de escopo do próprio axioma, não bifurcação limpa)|§10|
|GL-15|Programa de pesquisa|§10|
|GL-16|Decisão de escopo|Parte I §2.3|
|GL-17|Resolvido (herdado do escopo do axioma)|§8|
|GL-18|Resolvido (norma externa de teorização)|§8|

**Estrutura de dependência**:

```
NÍVEL 0 — Decisões de escopo, sem pai:           GL-1, GL-2, GL-3, GL-16
NÍVEL 1 — Raízes do programa de pesquisa:        GL-7, GL-5a, GL-9 (influenciado por GL-16), 
                                                   GL-10, GL-12a
NÍVEL 2 — Dependentes diretos:                    GL-11a (após GL-12a), GL-12b (filho de GL-12a),
                                                   GL-15 (paralelo a GL-9), GL-14 (pendente)
NÍVEL 3 — Condicionais, não livres:               GL-8 = f(GL-16),  GL-13 = f(GL-10)
NÍVEL 4 — Resolvidos por aplicação direta:        GL-6, GL-17
FORA DO NÍVEL TEÓRICO — deferidos:                GL-4, GL-5b, GL-5c, GL-11b, GL-18
```

## 8. Graus de liberdade resolvidos

**GL-4 / GL-5b** — classe de equivalência entre quatro famílias matemáticas de calibração demonstrada; escolha entre elas é implementação, não teoria. **GL-5c / GL-11b** — constantes e profundidade de parada; parâmetros, não conteúdo teórico. **GL-6** — regra de combinação é sintaxe da família escolhida em GL-4, não escolha adicional livre. **GL-17** — a existência de um fator como construto genuíno é, ela mesma, proposição sobre validade estrutural — já coberta pelo escopo declarado em 4.1(ii); não é extensão, é aplicação direta. **GL-18** — resolvido por norma geral de teorização: a forma de um critério quantificado é exigida pela teoria, seu valor é calibrado empiricamente depois — comportamento padrão de qualquer teoria com parâmetros livres, não peculiaridade deste corpus.

## 9. Decisões condicionais

**GL-8 (representação simbólica vs. sub-simbólica dos fatores) = f(GL-16).** Se interpretabilidade for exigida (GL-16 = sim), todo fator não nomeável por humano viola essa exigência por definição — GL-8 é forçado a simbólico. Se GL-16 = não, um sistema sub-simbólico satisfaz o Axioma da Fatoração sem problema — GL-8 permanece aberto nesse ramo.

**GL-13 (modelo gerativo vs. discriminativo) = f(GL-10).** Reivindicação causal no sentido interventivo exige, por resultado padrão da literatura de inferência causal, capacidade de simular intervenções — empurra GL-13 para gerativo/estrutural. Se GL-10 resolver para associativo, discriminativo basta e é mais parcimonioso.

Nenhum dos dois é grau de liberdade independente — cada um herda sua resposta do nó do qual depende.

## 10. Programa de pesquisa consolidado

Nove perguntas, ordenadas por valor de informação esperado sob critérios puramente metodológicos (custo, poder discriminativo, risco de falso positivo/negativo) — não por conveniência de projeto:

1. **GL-10** (estágio de revisão sistemática da literatura de transferência já publicada)
2. **GL-12a** (multiplicidade dentro do item vs. entre itens — raiz do bloco de Fatoração)
3. **GL-9** (curadoria vs. descoberta, com controle de viés de inicialização)
4. **GL-14** (atribuição suave vs. dura, ancorada em erros reais codificados por especialistas cegos, não simulação pura)
5. **GL-7** (decaimento, com dado de intervalo de repetição deliberadamente variado)
6. **GL-5a** (regimes de escala temporal, via meta-análise de efeito de espaçamento já publicada)
7. **GL-15** (verossimilhança fixa vs. aprendida, condicional a resolver proveniência não-circular)
8. **GL-11a** (fatoração recursiva vs. plana, subordinado ao resultado de #2)
9. **GL-12b** (universalidade de categorias entre domínios — menor poder discriminativo do conjunto, relevante sobretudo para expansão de escopo ainda não construída)

Um décimo item — GL-10 em sua forma de RCT local, por par de fatores — não entra nesta lista principal: é investimento condicionado ao resultado do item 1.

> **`[Errata 2.0.1]`** Nota de estado, sem alteração da lista nem de sua ordem: **GL-14 permanece aberto**. A `Especificação do Error Trace v1.0` exige atribuição ponderada e não determinística de causa de erro — mas essa exigência decorre da Constituição §4.4, não de GL-14 resolvido. Nenhum contrato operacional do corpus decide entre atribuição suave e dura no sentido de GL-14.

## 11. Decisões de escopo dentro do mapa

GL-1, GL-2, GL-3 e GL-16 não são graus de liberdade no mesmo sentido dos nove acima — nenhum experimento os resolve, porque nenhum deles é uma pergunta sobre como o mundo é. São escolhas sobre o que a teoria se propõe a modelar. Aparecem aqui apenas para completude do mapa; seu conteúdo e justificativa pertencem à Parte I.

---

# PARTE IV — Arquitetura Provisória

## 12. Componentes necessários dado o estado atual da teoria

**Nota editorial obrigatória, preservada integralmente**: uma derivação de cinco componentes foi produzida em rodada anterior a esta consolidação, antes de o mapa de graus de liberdade acima existir em sua forma auditada. Parte daquela derivação antecipou resoluções (especificamente, representação em grafo com tipagem simbólica) que o mapa mostra não estarem determinadas pelos axiomas — dependem de GL-8/GL-16, ambos em aberto. O que segue não é, portanto, "a arquitetura do Sapiens" — é o esboço mais concreto que a teoria permite hoje, com cada elemento rotulado quanto à sua natureza.

### 12.1 Camada de representação de crença

- **Consequência do axioma**: deve existir alguma representação de confiança revisável e calibrada, operando em pelo menos três escopos possíveis (estrutural, traço individual, momentâneo) — isto decorre diretamente de §4.1–4.2.
- **Escolha de engenharia**: qual família matemática instancia essa representação (GL-4/5b) — resolvido como classe de equivalência; a escolha entre as quatro famílias candidatas é livre.
- **Hipótese ainda aberta**: se decaimento é obrigatório (GL-7); se os três escopos correspondem a regimes de fato distintos ou a um contínuo artificialmente cortado (GL-5a).

### 12.2 Estrutura de fatoração

- **Consequência do axioma**: desempenho deve ser modelado como função de múltiplos fatores latentes distinguíveis, não de um único — decorre diretamente de §5.1–5.2.
- **Escolha de arquitetura, não consequência**: instanciar isso como grafo com nós e arestas tipadas é uma hipótese arquitetural contingente a GL-8/GL-16 resolverem na direção simbólica. Se GL-16 resolver para "interpretabilidade não exigida", uma representação distribuída (embeddings aprendidos, sem tipagem nomeável) satisfaz o mesmo axioma igualmente bem.
- **Hipóteses ainda abertas**: origem dos fatores — curada ou descoberta (GL-9); natureza da dependência entre eles — causal ou associativa, e apenas par a par (GL-10); profundidade recursiva (GL-11a); a questão central de multiplicidade dentro vs. entre tarefas (GL-12a); universalidade entre domínios (GL-12b).

### 12.3 Camada de evidência/verossimilhança

- **Consequência do axioma**: deve existir algum mecanismo conectando comportamento observado a atualizações de crença, fatorado segundo 12.2 — decorre da conjunção dos dois axiomas, não de nenhum isoladamente.
- **Escolha de engenharia**: forma funcional específica dessa verossimilhança.
- **Hipóteses ainda abertas**: se o modelo de evidência é fixado por julgamento especialista ou aprendido de dados (GL-15); se a atribuição de uma observação específica a múltiplas causas candidatas deve ser suave ou dura (GL-14 — estatuto especial: a própria pergunta depende de uma releitura de escopo do Axioma da Crença ainda não feita, não apenas de evidência empírica).

> **`[Errata 2.0.1]`** Registro de contrato existente, sem efeito sobre GL-14 nem GL-3: o objeto de saída desta camada — a cadeia causal de erro — passou a ter contrato canônico na `Especificação do Error Trace v1.0`, documento de camada C4. Antes desta errata, a Constituição §4.3 remetia sua especificação a uma "Especificação Técnica" inexistente no corpus.

### 12.4 Camada de decisão — vazia

Algo precisa consumir os estados de 12.1–12.3 para selecionar a próxima ação pedagógica. Sua existência é consequência prática de haver um sistema adaptativo; sua função objetivo não é. Este documento não propõe conteúdo para esta camada — é o slot vazio de §6.3, repetido aqui para que a lacuna apareça também no nível arquitetural, não apenas no axiomático.

> **`[Errata 2.0.1]`** Mesma correção de §6.3, aplicada ao nível arquitetural: **a camada não está vazia de conteúdo, está vazia de derivação axiomática**. Duas políticas concretas, ancoradas em literatura, existiam no White Paper 1.0 §2.9.3 (itens 5 e 6) e §2.9.7, e estão registradas como `rebaixadas` a `[DE]` não derivada dos axiomas em `EXT-WP1-1.0`, item L10. A **função objetivo** permanece ausente. Nota adicional de executabilidade: o motor de recomendação daquela proposta opera sobre arestas de pré-requisito, e a relação `Processo ↔ Processo` **não está populada** na ontologia vigente (Ontologia v1.4.1 §8) — portanto a política, mesmo recuperada como proposta, não é executável no estado atual do catálogo.

### 12.5 Camada de interface

Tradução entre linguagem natural e as estruturas formais de 12.1–12.4. Não é parte do modelo cognitivo — é tradução. Sua necessidade não decorre dos axiomas; decorre de o sistema precisar comunicar-se com humanos, o que é verdadeiro independentemente de qualquer resolução de GL.

---

# PARTE V — APLICAÇÃO EMPÍRICA PRELIMINAR

> **`[Errata 2.0.1]` — SUPERSESSÃO PARCIAL.**
> 
> Os Capítulos 13 e 14 desta Parte estão **`[SUPERSEDED por ONT-1.4.1 — TX-2026-08-17T184458Z-wp2-errata]`** quanto ao seu **inventário** de domínios, competências e processos cognitivos. Sob GOV-1.0 §8.3, a seção superada **deixa de ter força normativa imediatamente**, mesmo permanecendo no texto.
> 
> O inventário aqui apresentado — 8 domínios, 16 competências, 28 processos — é o da derivação-piloto original. O catálogo vigente é o da **Ontologia Cognitiva Sapiens v1.4.1**: 11 domínios, 12 competências, 25 processos, 56 habilidades, 13 tipos de erro, 11 intervenções. Divergências estruturais entre os dois, todas registradas em `09 Mapa de Rastreabilidade de IDs`: `DOM-ESTRUTURA` não existe no catálogo vigente; `DOM-LOGICO`, `DOM-SIMBOLICO`, `DOM-TEXTUAL` e `DOM-CLASSIF` não existem aqui; e **sete identificadores `DOM-*` são idênticos nos dois com extensão comprovadamente divergente** (colisão `NS-4`).
> 
> **O que permanece vigente nesta Parte:** a nota metodológica do §13.1 (a derivação é condicionada a GL-12a), a advertência do §13.4, as limitações do §14.2, e todo o Capítulo 15 (Ativos Protegidos), que não é inventário.

## 13. Domínios Derivados: Matemática

### 13.1 Natureza deste capítulo

Este capítulo apresenta a derivação-piloto de domínios matemáticos herdada da primeira versão deste documento. Ela é apresentada aqui sob uma condição explícita, não como conclusão fechada: sua validade depende inteiramente de como a Questão Central do Axioma da Fatoração (§5.6) — se múltiplos fatores latentes coexistem dentro de uma única tarefa avaliativa ou se a multiplicidade só se manifesta entre tarefas distintas — vier a ser respondida pelo item 2 do Programa de Pesquisa (Parte III, Capítulo 10). Nenhuma afirmação de validade de construto feita neste capítulo deve ser lida como estabelecida.

### 13.2 Domínios cognitivos

O raciocínio quantitativo, no espaço matemático, é organizado em quatro domínios [EC/IT — ancorados em PISA/OECD Mathematics Framework, Vergnaud e Dehaene]:

- **DOM-QUANT** — Raciocínio Quantitativo
- **DOM-ESPACO** — Raciocínio Espacial
- **DOM-MUDANCA** — Raciocínio sobre Mudança
- **DOM-INCERTEZA** — Raciocínio sob Incerteza

### 13.3 Processos ilustrativos e arestas cross-domínio

Os exemplos a seguir são apresentados como ilustração da estrutura pretendida, não como enumeração completa dos processos derivados — a lista integral permanece registrada no material de trabalho, não reproduzida por extenso neste capítulo (ver Pendências).

**RQ-PROP-003** — proporção como mecanismo cognitivo compartilhado [IT], manifestando-se como razão (matemática), escala em diagramas (física), relação estequiométrica (química) e taxa populacional (biologia). Esta é a aresta cross-domínio mais citada na derivação original e a que melhor ilustra a tese central da Parte II: que um processo cognitivo pode ser unidade cross-disciplinar, não uma abstração vazia.

**PROC-MUD-003** — reconhecimento de padrão de covariação [IT], manifestando-se em função exponencial (matemática), farmacocinética e crescimento populacional. A escolha de nomear o processo como "reconhecer que uma variável muda proporcionalmente à quantidade atual da outra" — em vez de "aprender função exponencial" — é [DE]: uma decisão de engenharia sobre qual nível de descrição maximiza transferência potencial, não uma dedução dos axiomas.

**PROC-MUD-004** — extrapolação/interpolação [IT]. Registrado aqui com uma advertência preservada de rodada anterior deste processo de revisão: extrapolação em contexto puramente matemático pode ser formalmente distinta de extrapolação em contexto empírico (que exige hipótese sobre mecanismo e limites do sistema observado) — distinção ainda não resolvida na arquitetura corrente (ver Capítulo 18).

**PROC-INC-004** — julgamento sob incerteza e heurísticas cognitivas [EC — ancorado na literatura de heurísticas e vieses]. Registrado com grau de transferência qualificado como baixo-médio: domínio formal de probabilidade condicional não garante, por si, resistência a heurísticas intuitivas de julgamento sob incerteza.

### 13.4 Limitação conhecida e não resolvida

Ao menos um processo da derivação original (distinção entre arranjo, combinação e permutação) mistura, de forma reconhecida, capacidade cognitiva geral com conteúdo procedural específico de domínio — o próprio tipo de confusão que o Axioma da Fatoração (§5.2) instrui a evitar. Este documento não corrige esse nó agora: fazê-lo exigiria resolver primeiro GL-9 (curadoria vs. descoberta) e a Questão Central §5.6, ambos em aberto. O nó permanece registrado como item pendente de revisão, não como erro silenciosamente reparado.

> **`[Errata 2.0.1]`** Registro de estado: a Ontologia v1.4.1 absorveu essa distinção em `PROC-INC-04` ("aplicar raciocínio probabilístico combinatório a processo gerador"), removendo o nó autônomo. A limitação apontada aqui foi, portanto, endereçada no catálogo vigente. Nenhuma decisão nova; registro de que a pendência mudou de estado.

## 14. Domínios Derivados: Ciências da Natureza

### 14.1 Domínios cognitivos

Quatro domínios [EC/IT — ancorados em NRC/NGSS Framework for K-12 Science Education]:

- **DOM-CAUSAL** — Raciocínio Causal-Mecanicista
- **DOM-SISTEMICO** — Raciocínio Sistêmico
- **DOM-EXPERIMENTAL** — Raciocínio Experimental e Investigativo
- **DOM-ESTRUTURA** — Raciocínio sobre Padrão, Escala e Estrutura-Função

### 14.2 Processos ilustrativos

**PROC-EXP-001** — identificação de variável independente, dependente e de controle [EC — diretamente ancorado em literatura de raciocínio científico/controle de variáveis]. Entre os processos derivados, este é o que a auditoria de graus de liberdade (Parte III) classifica como de maior facilidade operacional de mensuração — ação observável, erro identificável, item avaliável de forma relativamente inequívoca.

**PROC-CAUSAL-002** — encadeamento de etapas causais múltiplas [IT]. Candidato explícito, não decidido, a decomposição recursiva adicional (ordenar eventos; inferir mecanismo intermediário; detectar variável mediadora) — matéria de GL-11a, em aberto, subordinada à resolução de §5.6.

**PROC-SIST-003** — rastreamento de conservação de massa/energia [IT], com a mesma limitação estrutural registrada em 13.4: a operação cognitiva de "rastrear invariantes durante uma transformação" é distinta do conhecimento declarativo específico (primeira lei da termodinâmica, estequiometria de reação, fluxo trófico) necessário para aplicá-la a um caso concreto — distinção não resolvida por este documento, dependente de GL-10 (natureza da dependência entre fatores).

### 14.3 Arestas cross-domínio entre Matemática e Ciências

Duas conexões, preservadas da derivação original: (i) o eixo taxa de variação → interpretação estatística → interpretação experimental, ligando processos de mudança (Matemática), incerteza (Matemática) e investigação experimental (Ciências); (ii) reconhecimento de padrão como mecanismo de transferência, ligando PROC-MUD-003 a PROC-ESTR-001 — padrão matemático (linear, exponencial, quadrático) e padrão científico (estrutura recorrente entre fenômenos).

> **`[Errata 2.0.1]` — INCIDENTE ABERTO, correção de afirmação de fato.**
> 
> A aresta (ii) é apresentada como **preservada**. Verificação exaustiva sobre os 25 processos da Ontologia v1.4.1: **`PROC-ESTR-001` não tem correspondente no catálogo vigente.** Não existe processo cujo objeto seja o reconhecimento de padrão estrutural recorrente entre fenômenos de superfície distinta. O candidato mais próximo, `PROC-ESPACO-03`, é estrutura→função — que nesta Parte é `PROC-ESTR-002`, o outro nó.
> 
> A afirmação de preservação é, portanto, **incorreta quanto a (ii)**. Registrado como incidente `MAP-INC-03` em `09 Mapa de Rastreabilidade de IDs` §3.4.
> 
> Esta errata **não recria o nó** — isso seria mudança de estrutura do catálogo, Classe IV, que exige evidência de piloto (GOV-1.0 §11.2, Classe B). Ela apenas substitui uma afirmação falsa por um incidente registrado, para que a decisão seja tomada explicitamente na próxima versão da ontologia e não por omissão. Observação de relevância, registrada sem decidir: `PROC-ESTR-001` é o nó cuja função declarada é a transferência estrutural — o mecanismo que a Constituição §2.3 usa para definir a admissibilidade de um Processo Cognitivo.
> 
> A aresta (i) não foi verificada nesta errata.

### 14.4 Escopo total da derivação-piloto

A derivação original, somando Matemática e Ciências da Natureza, produziu 8 domínios, 16 competências e 28 processos cognitivos. Este capítulo e o anterior apresentam apenas subconjunto ilustrativo desse total (ver Pendências, item 2).

> **`[Errata 2.0.1]`** Duas correções de fato, sem efeito sobre o texto vigente desta Parte. **(a)** A "derivação original" é o **Capítulo 4 do White Paper 1.0**, documento que integra o corpus canônico. A atribuição de fonte, ausente na 2.0, fica aqui registrada. **(b)** O inventário daquele capítulo declara 28 processos e **enumera 29** — incidente `MAP-INC-04`. O número 28 é reproduzido acima como citação da fonte, não como contagem verificada.

## 15. Ativos Protegidos

Os elementos a seguir foram avaliados de forma consistentemente favorável em todas as rodadas de crítica que precederam esta consolidação, sem uma única ressalva contrária registrada. Nenhuma reformulação proposta nas Partes II–IV os contesta; qualquer arquitetura futura derivada deste documento deve preservá-los.

- **Error Trace** — modelagem de erro observado como estrutura causal, não etiqueta única. Identificado de forma independente, em múltiplas rodadas, como o elemento mais original de todo o corpus.
- **Falsa proficiência** — acerto sem domínio real do processo subjacente, tratado como categoria de primeira classe, não como ruído estatístico.
- **`ItemCognitiveMapping`** e a separação entre superfície disciplinar e estrutura cognitiva latente.
- **Cinco nós prioritários** (proporcionalidade, inferência textual, leitura de gráficos, causalidade, controle de variáveis) como estratégia de maior retorno para qualquer piloto inicial.
- **Inversão disciplinar** — disciplina tratada como metadado de manifestação, não como estrutura organizadora primária.
- **Derivação a partir de literatura estabelecida** (PISA/OECD, NRC/NGSS, Vergnaud, Dehaene, Siegler/Lamon), em vez de taxonomia inventada sem ancoragem.
- **Disciplina epistemológica [EC]/[IT]/[DE]**, agora estendida às afirmações centrais dos próprios axiomas (§3.2).
- **Campo de grau de transferência** — único ativo desta lista com ressalva anexada: a ideia de registrar transferência como propriedade explícita é preservada; sua formalização como categoria otimista fixa (alto/médio/baixo) permanece sob revisão, matéria de GL-10.

> **`[Errata 2.0.1]` — estado de preservação de cada ativo.**
> 
> A cláusula _"qualquer arquitetura futura derivada deste documento deve preservá-los"_ permanece integralmente em vigor. A auditoria integral verificou o estado real de preservação, e o registro abaixo existe porque **três destes ativos não estavam preservados** no momento da auditoria:
> 
> |Ativo|Estado verificado|
> |---|---|
> |**Error Trace**|**Restaurado.** Havia perdido sua propriedade definidora — a ordem causal — em dois saltos (Constituição §4.3 removeu a ordem; Schema 2.1 reduziu a um erro único por alternativa). A `Especificação do Error Trace v1.0` restabelece a cadeia ordenada com confiança obrigatória por elo|
> |**Falsa proficiência**|**Ativo sem implementação.** Preservado como categoria; o critério operacional que o torna detectável não existe em nenhum documento canônico. Registrado em `EXT-WP1-1.0` item L4, com o critério e o algoritmo originais preservados|
> |**Cinco nós prioritários**|**Um foi rebaixado.** "Leitura de gráficos" deixou de ser nó e passou a Habilidade na Ontologia v1.4 (`HAB-44`, `HAB-46`, sob `PROC-TEXT-01/02`). A decisão é defensável sob a Constituição §3.7.3, mas contraria a cláusula de preservação acima e não havia sido registrada. Registrada agora|
> |**Campo de grau de transferência**|**Não existe no catálogo vigente.** A Ontologia v1.4.1 não tem o campo em forma alguma. A ressalva desta seção — sobre a escala fixa — permanece válida e continua condicionada a GL-10. Registrado em `EXT-WP1-1.0` item L5|
> |`ItemCognitiveMapping`, Inversão disciplinar, Derivação a partir de literatura, Disciplina EC/IT/DE|Preservados|
> 
> Nenhuma decisão de conteúdo é tomada aqui. O quadro substitui uma afirmação genérica de preservação por um estado verificado, item a item.

---

# PARTE VI — PROTOCOLO DE VALIDAÇÃO

## 16. Critério de Validação Empírica Comparativa

Este documento declara, como condição para qualquer reivindicação de superioridade do Sapiens sobre arquiteturas educacionais alternativas, um critério de validação explícito: o modelo proposto (item → processo cognitivo → causa de erro → intervenção → trajetória de evolução) deve ser comparado, sobre a mesma população e os mesmos itens, ao modelo tradicional (item → disciplina → desempenho agregado), com a pergunta operacional sendo se o diagnóstico cognitivo produz recuperação de desempenho mensuravelmente superior à simples recomendação de mais exercícios do mesmo tema.

Esta exigência não é uma preferência metodológica externa aos Axiomas da Parte II — é corolário direto do Axioma da Crença Calibrada (§4.1b): reivindicar superioridade sem a evidência correspondente violaria a própria condição de calibração que o axioma impõe a todo o sistema.

**Metodologia mínima declarada**: (i) constituição de banco-piloto de itens a partir de fontes já existentes (exames padronizados, itens autorais); (ii) anotação dupla e independente por especialistas; (iii) medição de concordância interavaliador (coeficiente kappa), identificação de processos de baixa separabilidade e de processos excessivamente amplos; (iv) ajuste da ontologia com base nesses resultados; (v) apenas então, expansão de escopo. Esta sequência é condição de entrada para qualquer expansão de domínio (incluindo a agenda do Capítulo 20), não uma recomendação entre outras.

> **`[Errata 2.0.1]`** Duas notas de estado, sem alteração da exigência, que **permanece integralmente em vigor**. **(a)** A "trajetória de evolução" mencionada no modelo proposto depende de arestas de pré-requisito entre processos, e a relação `Processo ↔ Processo` não está populada na ontologia vigente (Ontologia v1.4.1 §8) — o quinto elo do modelo a comparar não é computável no estado atual do catálogo. **(b)** Este capítulo fixa os requisitos mínimos do protocolo, e não sua forma operacional: amostra por processo, número de anotadores e limiar de kappa não estão fixados em nenhum documento do corpus. O Manual §12, regra 5, remete a um "Plano de Validação" que não existe — remissão pendente `G-CONF-13`.

## 17. Sequência Ótima de Investigação

O Programa de Pesquisa (Parte III, Capítulo 10) cataloga nove questões abertas com suas hipóteses, experimentos e classificações de risco. Este capítulo formaliza sua ordem de execução, obtida por auditoria de valor de informação esperado sob critérios exclusivamente metodológicos — custo, poder discriminativo, risco de falso positivo e de falso negativo — não por conveniência de cronograma de projeto:

1. Natureza da dependência entre fatores, estágio de revisão sistemática (§5.4)
2. Multiplicidade dentro da tarefa vs. entre tarefas — questão central da Fatoração (§5.6)
3. Curadoria vs. descoberta de fatores, com controle de viés de inicialização (§5.3)
4. Atribuição suave vs. dura de causa de erro, ancorada em erros reais codificados por especialistas cegos (§4.4/§5.4, GL-14)
5. Obrigatoriedade de decaimento temporal (§4.4)
6. Existência de regimes de escala temporal distintos (§4.4)
7. Verossimilhança fixa vs. aprendida (§5.4)
8. Profundidade recursiva da fatoração (§5.5)
9. Universalidade de categorias entre domínios (§5.7)

Um décimo investimento — ensaio controlado local, par a par, sobre dependência causal — não integra esta sequência principal: é condicionado ao resultado do item 1 e só se justifica para os pares que aquele estágio identificar como de maior valor estratégico.

---

# PARTE VII — LIMITES E TRABALHO FUTURO

## 18. O Que Esta Teoria Não Afirma

Para uso por leitor externo avaliando o documento, esta lista é declarativa e exaustiva quanto ao que foi deliberadamente excluído do núcleo teórico:

- Não afirma que a dependência entre fatores latentes seja causal, no sentido interventivo, fora dos pares especificamente testados (§5.4; grau de confiança no qualificador causal geral: 35%).
- Não afirma que a formalização matemática deva ser bayesiana; quatro famílias distintas satisfazem igualmente os requisitos declarados (§4.3; grau de confiança na especificidade bayesiana: 35%).
- Não afirma que "Competência", como categoria, deixe de ser nível ontológico primário — esta é hipótese sob investigação (grau de confiança: 55%), não conclusão.
- Não especifica mecanismo de decisão pedagógica; a camada correspondente permanece deliberadamente vazia (§6.3, §12.4).
- Não afirma que representação simbólica/nomeável de fatores seja tecnicamente necessária — é valor de projeto declarado (§2.3), não requisito derivado.
- Não estabelece validade de construto para nenhum processo cognitivo específico apresentado na Parte V; toda a aplicação a domínios ali descrita é condicionada à Questão Central (§5.6) permanecer, por ora, em aberto.
- Não testou alternativas à unidade de análise individual (§2.1) nem a canais de evidência além de resposta a item (§2.2).

> **`[Errata 2.0.1]`** O quarto item é preciso quanto ao **mecanismo de decisão** e permanece como está. A leitura de que a camada é vazia **de conteúdo** é corrigida em §6.3 e §12.4: vazia de derivação axiomática e de função objetivo, não de conteúdo herdado.

## 19. Riscos Identificados

**Circularidade epistemológica no uso de inteligência artificial para autovalidação.** Identificado de forma independente em relação a dois nós distintos da arquitetura (origem dos fatores, §5.3; calibração da função de verossimilhança, §5.4) — em ambos os casos, comparar julgamento humano contra dado que o próprio julgamento ajudou a produzir invalida a comparação. Qualquer protocolo de validação executado sob o Capítulo 16 deve garantir proveniência independente da evidência de referência.

**Confusão entre taxonomia útil e taxonomia verdadeira.** Risco nomeado repetidamente ao longo de todo o processo de revisão que precedeu esta consolidação: uma estrutura pode parecer cientificamente rigorosa — categorias nomeadas, hierarquia elegante — sem que isso constitua evidência de que corresponde a estrutura cognitiva real, distinta de convenção útil de engenharia.

**Excesso de abstração sem critério operacional.** Identificado especificamente quanto a três pontos: o critério de distinguibilidade empírica que resolveria granularidade (§5.5) é nomeado sem quantificação; as escalas temporais de crença (§4.4) são nomeadas sem constante de tempo; a função objetivo da camada de decisão (§6.3) permanece inteiramente indefinida.

**Construção de teoria perfeita antes de validação de utilidade.** Risco estrutural do próprio processo que produziu este documento — quatro etapas de refinamento conceitual precederam qualquer contato com dado real de estudante. O Capítulo 16 existe precisamente para que esse risco não se estenda além deste ponto.

> **`[Errata 2.0.1]` — quinto risco, materializado e verificado.**
> 
> **Perda silenciosa entre documentos.** A auditoria integral do corpus identificou um mecanismo de falha recorrente e o verificou em três instâncias: **um documento declara preservar algo que o documento seguinte já havia removido, e nada no processo detecta a divergência.** As três instâncias estão nesta versão: o Error Trace (§15), `PROC-ESTR-001` (§14.3) e a camada de decisão (§6.3).
> 
> É o mesmo mecanismo que a Constituição §1.1 identifica como o defeito original da v1.3 — redundância e perda silenciosas por ausência de detecção estrutural — operando um nível acima: entre documentos, em vez de entre nós.
> 
> Registrado como risco porque não é um erro pontual já corrigido, e sim uma propriedade do processo. A mitigação adotada é `GOV-1.0`, cuja regra central (§8.2) proíbe marcar um documento como superado antes de existir registro do conteúdo que ele contém e que não foi transportado.

## 20. Agenda de Expansão

Itens que não integram o núcleo axiomático das Partes II–IV, mas que decisões futuras — empíricas ou de escopo — podem incorporar:

- Expansão de domínio para Humanas e Linguagens, condicionada à resolução de GL-12b (§5.7).
- Reexame da unidade de análise individual contra alternativas coletivas (§2.1, GL-2).
- Incorporação de canais de evidência além de resposta a item — latência já em posição secundária; autorrelato e observação docente ainda fora do escopo (§2.2, GL-3).
- Especificação da camada de decisão pedagógica e sua função objetivo — o único elemento explicitamente reconhecido como ausente, não meramente incompleto (§6.3).

**Registro de Notas para o White Paper 3.0.** A partir desta consolidação, qualquer ideia que emergir durante trabalho futuro sobre este documento — e que constitua melhoria conceitual, não correção factual, de redação, ou incorporação de evidência empírica já prevista pelo Programa de Pesquisa — deve ser lançada aqui, não incorporada ao núcleo congelado das Partes II–IV. Este registro está, neste momento da consolidação, vazio: nenhuma ideia dessa natureza surgiu durante a redação das Partes V–VII que não coubesse já em um dos vinte e dois graus de liberdade catalogados na Parte III.

> **`[Errata 2.0.1]`** A condição do primeiro item permanece integralmente em vigor: a expansão para Humanas e Linguagens está condicionada a GL-12b, **que continua aberto**, e à condição de entrada do Capítulo 16, **que não foi satisfeita** — não há piloto executado nem kappa medido. O Registro de Notas para o 3.0 permanece vazio: nada nesta errata é melhoria conceitual.

---

## 21. Aparato de Referências e Gerações de Identificador

_Seção acrescentada na 2.0.1._

### 21.1 Referências

A versão 2.0 cita autores em texto corrido e **não possui seção de referências**. Sob GOV-1.0 §10.2, regra 4, _"uma afirmação `[EC]` sem referência recuperável é rebaixada automaticamente a `[IT]` até que a referência seja restaurada"_ — o que, aplicado literalmente, rebaixaria toda afirmação `[EC]` deste documento.

**Resolução, sem duplicar aparato:** o aparato bibliográfico deste documento é o do **White Paper 1.0**, em seus três blocos de Referências (fim dos Capítulos 1, 2 e 4), preservado e integralmente recuperável no corpus canônico. Toda afirmação `[EC]` desta versão resolve por chave autor-ano naquele aparato.

Duas consequências, declaradas:

1. As afirmações `[EC]` deste documento são **`[EC]` herdada** — a referência é recuperável, mas não foi reverificada nesta errata contra a afirmação específica que a invoca. Uma referência prova que a literatura existe; não prova que ela sustenta a afirmação particular.
2. Reproduzir o aparato aqui seria **duplicação de contrato**, proibida por GOV-1.0 §12. A remissão por chave é a forma correta.

Registro em `EXT-WP1-1.0`, item L14.

### 21.2 Gerações de identificador

Todos os identificadores citados na Parte V pertencem às gerações **G0** (esquema mnemônico do Capítulo 2 do White Paper 1.0: `RQ-PROP-003`) e **G1** (esquema de três dígitos do Capítulo 4: `PROC-EXP-001`, `PROC-ESTR-001`). O catálogo vigente usa **G3** (`PROC-EXP-02`).

**Nenhum identificador citado na Parte V é resolvível contra o catálogo vigente.** Não por descuido de nomeação, mas porque a cadeia documental entre as gerações passa pela Ontologia v1.3, **ausente do corpus canônico** — `G-CONF-09`. Toda equivalência entre G0/G1 e G3 é, portanto, `EQUIVALÊNCIA NÃO ESTABELECIDA`.

Advertência operacional: truncar o zero à esquerda de um identificador G1 produz um identificador G3 **válido e errado**. Casos confirmados: `PROC-ESPACO-003` (semelhança/escala) → `PROC-ESPACO-03` (estrutura→função); `PROC-EXP-001` (controle de variáveis) → `PROC-EXP-01` (formular hipótese); `PROC-INC-004` (heurísticas) → `PROC-INC-04` (combinatório-probabilístico). Colisão `NS-3`. A conversão automática entre gerações é **proibida** por `09 Mapa de Rastreabilidade de IDs` §12.

---

**3. Pendências reais**

1. Apêndices A–D permanecem por compilar (Glossário; matriz de rastreabilidade 57 críticas → 8 princípios → 2 axiomas → 22 unidades de GL → 9 itens do Programa de Pesquisa; tabela de graus de confiança; protocolos experimentais detalhados) — todos dependem apenas de material já produzido, sem necessidade de nova análise.
2. Os Capítulos 13–14 apresentam subconjunto ilustrativo dos processos cognitivos (cerca de 10 dos 28 totais da derivação original); a reprodução integral do conjunto completo, se desejada para a versão publicável final, exigirá consulta ao material fonte original do Capítulo 4 do White Paper 1.0, não apenas ao que foi citado ao longo deste processo de revisão.
3. Nenhuma.

> **`[Errata 2.0.1]`** **Pendência 2 encerrada.** O White Paper 1.0 integra o corpus canônico e seu Capítulo 4 está integralmente disponível; a consulta que a pendência previa não é mais necessária. Ademais, a reprodução integral do inventário tornou-se **desnecessária e indesejável**: os Capítulos 13 e 14 estão superados quanto ao inventário pela Ontologia v1.4.1 (ver a nota de supersessão parcial no início da Parte V), e reproduzir aqui um catálogo superado recriaria a duplicação que `GOV-1.0` §12 proíbe. A **Pendência 1 permanece aberta**.

---

## 22. Changelog

|TX|Timestamp|Classe|Alteração|
|---|---|---|---|
|`TX-2026-08-17T184458Z-wp2-errata`|2026-08-17T18:44:58Z|I e II — Correção de Fidelidade e Errata|**(1)** §6.3 e §12.4: corrigida a afirmação de que nenhuma evidência sustentava a camada de decisão; status corrigido de inexistente para `rebaixado`. A conclusão substantiva (não derivável dos axiomas; função objetivo ausente) permanece. **(2)** Parte V, Capítulos 13 e 14: **supersessão parcial** quanto ao inventário, pela Ontologia v1.4.1 (GOV-1.0 §8.3). **(3)** §14.3: corrigida a afirmação de que `PROC-ESTR-001` está preservado; registrado incidente `MAP-INC-03`. **(4)** §15: acrescentado quadro de estado verificado de cada ativo protegido — três não estavam preservados. **(5)** §19: acrescentado o quinto risco, verificado. **(6)** §21 criada: aparato de referências resolvido por remissão ao White Paper 1.0, sem duplicação; gerações de identificador declaradas. **(7)** Pendência 2 encerrada. **(8)** Notas de estado em §4.4, §10, §12.3, §13.4, §14.4, §16, §18, §20. **(9)** Cabeçalho canônico e changelog (GOV-1.0 §7.1, §7.3).|

**Nenhum axioma foi alterado. Nenhum grau de confiança foi reponderado. Nenhum Grau de Liberdade foi fechado nem aberto. Nenhum elemento de catálogo ontológico foi criado, alterado ou removido.**

---

_Capítulos 13 a 20 (Partes V, VI e VII) consolidados na 2.0. Errata aplicada na 2.0.1._