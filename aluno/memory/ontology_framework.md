# Sapiens — Framework Ontológico

**Documento de fundamentação epistemológica**  
*Versão 1.0 — Fev/2026*

## Preâmbulo

O Sapiens não é um corretor. É um sistema de inferência cognitiva. Como tal, precisa
de uma ontologia clara — não apenas para organizar dados, mas para separar aquilo que
já é conhecido pela ciência daquilo que só o próprio sistema pode descobrir.

A tentação usual em plataformas educacionais é montar taxonomias grandes e fechadas
antes de coletar dados. É elegante, mas cientificamente frágil: passa-se por
descoberta o que é apenas categorização. Preferimos o caminho oposto — formular
hipóteses bem fundadas e deixá-las sobreviver ao contato com a realidade.

Por isso o Sapiens organiza o conhecimento em **cinco níveis**, com **origens e
graus de evidência distintos**. Os três primeiros são curadoria científica. Os dois
últimos são engenharia empírica: nascem do sistema e refinam-se com o uso.

---

## Estrutura de cinco níveis

| Nível | Origem | Grau de evidência |
|---|---|---|
| 1 · Domínio Cognitivo | Derivado diretamente da literatura consolidada | Muito alto |
| 2 · Competência | Síntese ontológica baseada em múltiplos modelos teóricos | Alto |
| 3 · Processo Cognitivo | Decomposição operacional da competência apoiada pela literatura e refinada para engenharia do sistema | Médio-alto |
| 4 · Habilidade Observável | Derivação operacional voltada à mensuração | Médio |
| 5 · Indicador Comportamental | Definição empírica baseada em dados do sistema | Cresce com o tempo |

---

## Definições

### Domínio Cognitivo (Nível 1)
Categoria macro de funcionamento cognitivo estabelecida por décadas de pesquisa
psicométrica e neurocientífica (referenciais como Cattell-Horn-Carroll, Baddeley,
Sweller). Representa uma dimensão relativamente estável e amplamente aceita da
cognição humana. Servem como âncoras de mais alto nível para toda a hierarquia.

### Competência (Nível 2)
Entidade ontológica derivada por síntese de múltiplos referenciais da literatura
em cognição, aprendizagem e educação, representando conjuntos relativamente estáveis
de processos cognitivos relacionados.

### Processo Cognitivo (Nível 3)
Unidade operacional mínima de raciocínio utilizada para modelagem computacional e
mensuração de desempenho, derivada da decomposição funcional das competências
descritas na literatura.

### Habilidade Observável (Nível 4)
Manifestação comportamental mensurável de um Processo Cognitivo em uma tarefa
específica, definida para permitir avaliação objetiva em itens educacionais.

### Indicador Comportamental (Nível 5)
Evidência quantitativa produzida pelo comportamento do estudante durante a
resolução de tarefas, utilizada para inferir o estado de domínio da habilidade
observável. Indicadores podem ser inicialmente definidos por hipótese e
refinados continuamente a partir de dados empíricos coletados pelo sistema.

---

## Consequências arquiteturais

1. **Níveis 1 e 2 são estáveis.** São seed do sistema, versionados como conhecimento
   consolidado. Alterações exigem justificativa bibliográfica.

2. **Nível 3 é operacional.** Existe para permitir modelagem computacional — cada
   processo tem de ser mensurável em um item de prova. Pode ser refinado à luz de
   evidências, mas permanece ancorado na literatura.

3. **Nível 4 nasce como hipótese.** É a ponte entre a teoria e a mensuração. Cada
   habilidade é uma proposta operacional que só ganha status de fato quando
   respaldada por indicadores empíricos.

4. **Nível 5 é vivo.** Começa vazio (ou com hipóteses semente) e cresce à medida que
   milhares de tentativas são registradas. Cada indicador carrega:
   - `hipótese`: como a proposta foi originalmente definida
   - `definição refinada`: como o dado mudou a definição
   - `evidence_count`: número de tentativas em que o padrão foi observado
   - `total_observed`: quantidade total de tentativas analisadas
   - `confidence`: `evidence_count / total_observed`
   - `refined_at`: data da última atualização

5. **A camada de diagnóstico da IA deve saber qual nível está usando.** Quando o
   Sapiens afirma *"você domina proporcionalidade"*, essa afirmação usa
   competências (nível 2, alta evidência). Quando afirma *"você troca a ordem das
   grandezas quando o enunciado é longo"*, essa é uma inferência de nível 5, cuja
   confiança deve ser explicitada ao usuário.

---

## Por que isso importa

Um sistema que confunde os cinco níveis vira uma taxonomia bonita mas cientificamente
frágil. Um sistema que os separa é capaz de dizer, para cada afirmação, *onde essa
afirmação vive*. Isso é o que separa engenharia de conhecimento de mero design de
software educacional.

O Sapiens é escrito para essa segunda categoria.

---

## Referências principais

- McGrew, K. S. (2009). *CHC theory and the human cognitive abilities project*.
- Sweller, J. (1988). *Cognitive load during problem solving*.
- Baddeley, A. (2000). *The episodic buffer: a new component of working memory*.
- Karplus, R. (1980). *Teaching for the development of reasoning*.
- Anderson, L. W. & Krathwohl, D. R. (2001). *A taxonomy for learning, teaching, and assessing*.
