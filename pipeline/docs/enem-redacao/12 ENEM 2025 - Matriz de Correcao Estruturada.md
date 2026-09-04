# 12 enem 2025 - matriz de correcao estruturada · MD

### Id

ENEM-MATRIZ-1.0

### Titulo

Matriz de Correção Estruturada — Interpretação Documental para Correção Automatizada de
Redações do Enem

### Versao

1.0.0

### Estado

apoio_externo

### Declaracao_de_nao_normatividade

Documento de **interpretação e estruturação**, não de fonte primária. Toda regra aqui
organizada cita seu identificador de origem em
`11 Cartilha ENEM 2025 - Extracao da Fonte Oficial.md` (ENEM-FONTE-1.0). Em qualquer
divergência entre este documento e o documento 11, **prevalece o documento 11**. Não é fonte
de categorias cognitivas do Sapiens (mesma declaração de ENEM-FONTE-1.0, GOV-1.0 §1.1).

### Criado_em

2026-08-24T15:18:20Z

### Atualizado_em

2026-08-25T15:39:50Z

### Camada

apoio_externo

### Deriva_de

ENEM-FONTE-1.0@1.0.0 (interpretação — não é regeneração automática; reorganização editorial
feita por leitura humana/IA da fonte, sujeita a revisão)

### Cni_membros

- `13 enem_regras_computaveis.json` (ENEM-REGRAS-JSON-1.0) — este par forma um **Conjunto
  Normativo Indivisível** sob GOV-1.0 §4.2: este documento (prosa) é autoridade sobre
  **justificativa, critério e fronteira**; o JSON é autoridade sobre **estrutura, cardinalidade e
  valores numéricos**. Qualquer alteração em um exige verificação de concordância no outro na
  mesma transação.

### Remissoes_pendentes

Nenhuma.

---

## 0. Propósito

Este documento organiza as regras extraídas em `11 Cartilha ENEM 2025 - Extracao da Fonte
Oficial.md` (doc 11) em um **pipeline de decisão** utilizável por um futuro corretor
(humano-assistido ou automatizado), e registra explicitamente as **ambiguidades e lacunas**
encontradas na fonte oficial — sem inventar resolução para nenhuma delas.

Não implementa o corretor. Não define arquitetura de software, prompt de IA nem schema de
banco de dados. É o elo entre a fonte oficial (doc 11) e uma futura camada operacional C4-like
(fora do escopo desta tarefa).

---

## 1. Pipeline de decisão em duas etapas

Uma redação do Enem não é simplesmente "a soma de 5 notas". A fonte estabelece uma
**ordem de precedência**: primeiro se decide se a redação é avaliável; só depois — e apenas se
for avaliável — as 5 competências são pontuadas independentemente.

```
Etapa 0 — Elegibilidade (produz: AVALIÁVEL | ANULADA=0 | EM_BRANCO=0)
   │
   ├─ checa ZERO-03..ZERO-09, ZERO-11 (doc 11 §2)         → se qualquer um disparar: nota final = 0,
   │                                                          não avalia nenhuma competência
   ├─ checa ZERO-01 (fuga total) e ZERO-02/ZERO-10          → se disparar: nota final = 0 (ZERO-EFEITO-01),
   │  (não-atendimento ao tipo textual, con predominância)     não avalia nenhuma competência
   │
   └─ se nenhum dos anteriores disparou → segue para Etapa 1

Etapa 1 — Pontuação por competência (só ocorre se Etapa 0 = AVALIÁVEL)
   │
   ├─ COMP-I   → nível 0/40/80/120/160/200 (doc 11 §4, tabela COMP-I)
   ├─ COMP-II  → nível 0/40/80/120/160/200 (doc 11 §4, tabela COMP-II)
   │             + aplica TEMA-02 (cap de tangenciamento) se detectado
   ├─ COMP-III → nível 0/40/80/120/160/200 (doc 11 §4, tabela COMP-III)
   │             + sujeito ao cap de TEMA-02
   ├─ COMP-IV  → nível 0/40/80/120/160/200 (doc 11 §4, tabela COMP-IV)
   ├─ COMP-V   → nível 0/40/80/120/160/200 (doc 11 §4, tabela COMP-V)
   │             + DH-ZERO-01: zera SÓ esta competência se a proposta de intervenção
   │               desrespeitar direitos humanos
   │             + sujeito ao cap de TEMA-02
   │
   └─ nota_total = COMP-I + COMP-II + COMP-III + COMP-IV + COMP-V   (máx. 1.000)
```

### 1.1 Por que a Etapa 0 precede a Etapa 1

`ZERO-EFEITO-01` (doc 11) é explícita: fuga ao tema e não-atendimento ao tipo textual não são
"zero pontos na competência relevante" — são "a redação não é avaliada em nenhuma
competência". Um corretor que pontuasse as 5 competências independentemente e apenas
depois zerasse o total produziria diagnósticos de I, III, IV e V que a própria fonte diz não
deverem existir. **A Etapa 0 precisa ser um curto-circuito, não um pós-processamento.**

### 1.2 Diferença de escopo entre os dois "zeros" de direitos humanos vs. tema

| Gatilho | Escopo do zero | Origem |
|---|---|---|
| `ZERO-01`, `ZERO-02`/`ZERO-10` (fuga/tipo textual) | Redação inteira (1.000 → 0) | `ZERO-EFEITO-01` |
| `DH-ZERO-01` (desrespeito a direitos humanos na proposta) | Apenas Competência V (200 → 0) | doc 11 §4, COMP-V |

Um corretor que confundir esses dois escopos zera a redação inteira por um problema que a
fonte trata como localizado, ou vice-versa. Este é o erro mais fácil de cometer ao implementar
a partir de uma leitura apressada da cartilha.

---

## 2. Metodologia de decomposição temática (padrão reutilizável, não os elementos concretos)

A fonte demonstra, para o tema de 2024, um método de decisão sobre fuga/tangenciamento
(doc 11 `TEMA-01`, `TEMA-02`): decompor a frase temática oficial da edição em vigor em seus
**elementos obrigatórios** (para 2024: Desafios + Valorização + Herança africana + Brasil) e
verificar quantos são desenvolvidos:

- nenhum elemento desenvolvido → fuga total (`ZERO-01`);
- apenas o assunto mais amplo, sem o recorte específico → tangenciamento (`TEMA-02`);
- todos os elementos desenvolvidos e articulados entre si → tema atendido.

**O que é portátil**: o método de decomposição em elementos obrigatórios da frase temática.
**O que NÃO é portátil**: os elementos concretos de 2024, e a lista de violações de direitos
humanos específicas a esse tema (`DH-03` no doc 11). Uma implementação que hardcode "Brasil"
ou "herança africana" como elementos temáticos universais está lendo a fonte errado — esses
são específicos à prova de 2024, usada pela cartilha apenas como exemplo didático.

**Consequência para o corretor**: a decomposição temática de uma prova futura exige o
**tema/proposta daquela edição específica**, que não está e não pode estar neste canon. Este
canon fornece o método; a proposta de cada edição fornece os elementos a decompor.

---

## 3. Registro de ambiguidades e lacunas

Nenhuma ambiguidade abaixo foi resolvida por inferência. Cada uma está registrada para
decisão humana futura (curadoria pedagógica), não para preenchimento silencioso por um
modelo de IA.

### AMB-01 — Limite inferior exato de "texto insuficiente"

A fonte diz "até 7 (sete) linhas manuscritas" configura texto insuficiente (`ZERO-04`), mas não
declara explicitamente que 8 linhas é o mínimo aceitável — apenas que a faixa "insuficiente"
vai até 7. É a leitura mais natural que 8+ linhas sai dessa faixa, mas isso é inferência do leitor,
não afirmação literal da cartilha. **Não resolvido.**

### AMB-02 — "Parte deliberadamente desconectada" exige julgamento de articulação argumentativa

`DESCONECTADA-02` (doc 11) deixa claro que a mesma categoria de conteúdo (ex.: mensagem de
protesto) pode ou não configurar anulação, dependendo de estar "articulada à argumentação".
Não há teste mecânico (palavra-chave, posição no texto) fornecido pela fonte. **Requer
julgamento semântico — não decidível por regra determinística simples.**

### AMB-03 — Rótulo "Enem 2024" na tabela de níveis da Competência II

A tabela de níveis de desempenho da Competência II (doc 11, física p.28) é rotulada no corpo do
texto como "...que serão utilizados para avaliar a Competência II **nas redações do Enem
2024**", enquanto as tabelas de Competência I, III, IV e V da mesma cartilha (2025) dizem
"Enem 2025" (Competência I) ou "Enem 2024" (III e IV, ver abaixo) de forma inconsistente entre
si. Isto é, muito provavelmente, resíduo de atualização incompleta do texto-base ano a ano
pelo Inep — a cartilha é anual e reaproveita parágrafos. **Não corrigido por este canon**:
reproduzido literalmente como está na fonte, com a inconsistência sinalizada aqui em vez de
silenciosamente normalizada. Ocorrências: COMP-I → "Enem 2025" (física p.15); COMP-II →
"Enem 2024" (física p.28); COMP-III → "Enem 2025" (física p.31); COMP-IV → "Enem 2024" (física
p.35); COMP-V → "Enem 2025" (física p.39).

### AMB-04 — "Repertório de bolso" não é lista fechada

`REPERTORIO-01` (doc 11) depende de julgamento sobre articulação, não de uma lista de
referências proibidas. A mesma citação (ex.: uma obra literária) pode ser produtiva em um
texto e decorativa em outro. **Não decidível sem avaliação semântica do texto completo.**

### AMB-05 — Lista de violações de direitos humanos específicas a tema é só exemplo

`DH-03` (doc 11) é uma instanciação do tema de 2024 dos princípios gerais `DH-01`/`DH-02`. Não
deve ser tratada como lista fechada válida para outras edições. Um corretor de produção
precisa reaplicar `DH-01`/`DH-02` ao tema vigente de cada edição — trabalho de interpretação
que este canon não pode antecipar.

### AMB-06 — Fronteira entre "predominância de outro tipo textual" (zero total) e "traços" (penalização em COMP-II)

`TIPO-02` (doc 11) distingue "predominância" (zero total, `ZERO-10`) de "muitas características,
mas ainda predominantemente dissertativo-argumentativo" (penalização em COMP-II, nível 40:
"traços constantes de outros tipos textuais"). A fonte não fornece um limiar quantitativo (ex.:
percentual de linhas narrativas) para diferenciar as duas situações. **Fronteira qualitativa,
não numérica.**

### AMB-07 — Silêncio sobre efeito do tangenciamento nas Competências I e IV

`TEMA-02` (doc 11) afirma expressamente que o tangenciamento limita III e V a no máximo 40
pontos, mas é silente sobre I e IV. Duas leituras possíveis:

1. o cap não se aplica a I e IV (leitura literal — a fonte só menciona II, III e V); ou
2. a omissão é lacuna editorial, e o espírito da regra (tangenciamento compromete a
   argumentação como um todo) se estenderia a I e IV.

**Este documento não escolhe entre as duas leituras.** GOV-1.0 §1.3 seria explícito sobre isso
se este fosse um documento C1–C4: "um documento de camada inferior não pode resolver uma
questão que a camada superior deixou em aberto". Aqui a "camada superior" é a própria fonte
oficial do Inep, que é quem teria de esclarecer. Uma implementação de corretor **precisa**
declarar explicitamente qual das duas leituras adotou, e marcar essa decisão como convenção
de engenharia, não como fato extraído da cartilha.

### AMB-08 — Patamar de cópia dos textos motivadores que leva à anulação

`COPIA-02` (doc 11) diz que cópia recorrente "fará com que sua redação tenha uma pontuação
mais baixa ou, até mesmo, seja anulada como cópia" — sem definir o patamar (percentual de
linhas copiadas? número de trechos?) que separa "pontuação mais baixa" de "anulada". **Não
quantificado pela fonte.**

### AMB-09 — Seção "Amostra de Redações" não gera dados de calibração numérica

Doc 11 §9 (`AMOSTRA-REF`) já registra que as 10 redações comentadas (física pp.42–72) não
recebem nota numérica explícita por competência no texto da cartilha — apenas comentário
qualitativo. Isso significa que **este canon não contém nenhum dado rotulado
(texto→nota) para treinar ou validar quantitativamente um modelo de correção**. Se uma etapa
futura do projeto precisar de dados rotulados, eles terão de vir de outra fonte (ex.: gabaritos
oficiais do Inep com notas publicadas, ou anotação humana especializada) — não desta
cartilha.

---

## 4. O que este documento explicitamente NÃO faz

1. Não decide nenhuma das ambiguidades do §3.
2. Não define prompt, modelo de IA, arquitetura de software ou schema de dados para o futuro
   corretor.
3. Não atribui as regras aqui organizadas a nenhum Domínio/Competência/Processo do catálogo
   C3 (Ontologia Cognitiva Sapiens) — são dois sistemas de categorização completamente
   distintos (Enem avalia redação; Sapiens categoriza cognição sobre questões objetivas).
   Qualquer ponte entre os dois é decisão de produto futura, não estabelecida aqui.
4. Não gera nem simula nota alguma para qualquer redação real ou hipotética.

---

## 5. Como este canon deve ser consumido por uma futura implementação

1. **Etapa 0 (elegibilidade)** deve ser implementada como função independente, executada
   **antes** de qualquer chamada de avaliação por competência, retornando um curto-circuito
   quando aplicável (§1.1–§1.2).
2. **As 5 tabelas de nível** (doc 11 §4) devem ser citadas literalmente como rubrica — não
   parafraseadas — na instrução de qualquer avaliador humano ou modelo de IA que vier a
   pontuar uma competência, para preservar o vocabulário oficial que ancora a decisão
   ("excelente", "bom", "mediano", "insuficiente", "precário", "desconhecimento" etc.).
3. **Toda ambiguidade do §3** que a implementação precisar resolver operacionalmente deve
   registrar sua escolha como convenção de engenharia explícita, citando o `AMB-xx`
   correspondente — nunca silenciosamente.
4. **O tema/proposta de cada edição do Enem** é insumo externo a este canon (§2) — precisa ser
   fornecido a cada correção, já que os elementos temáticos concretos não são portáteis entre
   edições.
5. **`13 enem_regras_computaveis.json`** (mesmo diretório) é o artefato de máquina que
   estrutura numericamente as tabelas e regras de zero/cap deste documento, para consumo
   direto por código — sem exigir reparsing deste Markdown.

---

## 6. Changelog

| TX | Timestamp | Classe | Alteração | Autoriza | Co-alterados |
|---|---|---|---|---|---|
| `TX-2026-08-24T151820Z-enem-canon-v1` | 2026-08-24T15:18:20Z | — (criação) | Criação do documento, interpretação derivada de ENEM-FONTE-1.0@1.0.0 | Pedido do usuário, 2026-08-24 | `11 Cartilha ENEM 2025 - Extracao da Fonte Oficial.md`, `13 enem_regras_computaveis.json`, `README.md` (mesmo diretório) |
| `TX-2026-08-25T153950Z-enem-canon-fidelity-v1.1` | 2026-08-25T15:39:50Z | I — Correção de Fidelidade (nenhum conteúdo deste documento alterado) | `13 enem_regras_computaveis.json` não portava `cap_por_tangenciamento` em `COMP-II`, embora este documento já registrasse a regra em §1 (linhas 91-92) e §3/AMB-07 (linha 207) desde a criação. JSON corrigido para refletir a decisão já registrada aqui; nenhuma leitura nova foi introduzida. Entrada registrada aqui apenas para manter os changelogs do CNI (GOV-1.0 §4.2) sincronizados | Identificação do usuário durante implementação de `aluno/backend/redacao/canon.py`, 2026-08-25 | `13 enem_regras_computaveis.json` (1.0.0 → 1.0.1; também corrigiu, na mesma transação, uma chave JSON `titulo` duplicada — Classe II, sem relação com este documento) |
