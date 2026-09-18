---
course_id: matematica-basica
station_id: 01
title: "Operações fundamentais"
difficulty: beginner
status: coming_soon
video: null
skills:
  - operacoes_fundamentais
  - ordem_de_operacoes
  - calculo_mental
prerequisites: []
---

# Estação 01 — Operações fundamentais

## Objetivo

Ao final desta estação, você saberá resolver expressões numéricas respeitando a ordem correta das operações, e reconhecerá os erros mais comuns que fazem uma conta simples dar errado.

## Pré-requisitos

Nenhum.

## Conteúdo

Toda expressão numérica é resolvida em **quatro níveis de prioridade**, sempre de cima para baixo:

1. **Parênteses** — `( )`, depois `[ ]`, depois `{ }`
2. **Potências e raízes**
3. **Multiplicação e divisão** — na ordem em que aparecem, da esquerda para a direita
4. **Adição e subtração** — também na ordem em que aparecem

Dentro do mesmo nível, quem vem primeiro da esquerda tem prioridade. Isso é o que faz `100 ÷ 10 × 2 = 20` e não `5`.

### Por que essa ordem existe

A multiplicação é uma soma repetida. Escrever `3 × 4` é escrever `4 + 4 + 4`. Se resolvêssemos a soma antes, estaríamos somando quantidades que ainda não foram contadas. A ordem de operações preserva o significado da expressão.

### Sinal negativo

Um sinal de menos na frente de um parêntese troca o sinal de **tudo** que está dentro.

`−(3 − 5) = −3 + 5 = 2`

## Exemplos resolvidos

**Exemplo 1.** `7 + 3 × 4`
- Multiplicação primeiro: `3 × 4 = 12`
- Depois soma: `7 + 12 = 19`

**Exemplo 2.** `(7 + 3) × 4`
- Parêntese primeiro: `7 + 3 = 10`
- Depois multiplicação: `10 × 4 = 40`

**Exemplo 3.** `20 − 3 × 4 + 2`
- Multiplicação: `3 × 4 = 12`
- Esquerda para direita: `20 − 12 = 8`, depois `8 + 2 = 10`

**Exemplo 4.** `2 + 3 × {4 + 5 × [6 − 2 × (3 − 1)]}`
- `(3 − 1) = 2`
- `2 × 2 = 4`, então `[6 − 4] = 2`
- `5 × 2 = 10`, então `{4 + 10} = 14`
- `3 × 14 = 42`
- `2 + 42 = 44`

## Estratégias

- Antes de calcular, **marque visualmente** o que resolve primeiro. Circulue parênteses.
- Em expressões longas, reescreva a linha inteira após cada passo. Não tente resolver tudo de cabeça.
- Desconfie de resultados “bonitos demais”. Se `100 ÷ 10 × 2` deu `5`, provavelmente você aplicou uma prioridade que não existe.
- Quando houver dúvida entre duas leituras, teste com números pequenos.

## Erros comuns

- **Somar antes de multiplicar.** `6 + 4 × 5 = 50` está errado; o correto é `26`.
- **Tratar multiplicação e divisão como níveis diferentes.** Elas têm a mesma prioridade; vale a ordem da esquerda para a direita.
- **Esquecer o sinal de menos antes de parênteses.** `−(3 − 5)` não é `−3 − 5`.
- **Abandonar a expressão no meio.** Parar em `20 − 12 = 8` e não somar o `+2`.

## Exercícios

### Questão 1
Calcule `6 + 4 × 5`.
A) 50
B) 26
C) 30
D) 20
**Resposta:** B
**Feedback:** A multiplicação vem antes da soma: `4 × 5 = 20`, depois `6 + 20 = 26`. A alternativa A corresponde a somar primeiro (`10 × 5`). C ignora o 4 e multiplica só `6 × 5`. D ignora o 6 e para em `4 × 5`.

question_id: mb-01-q01
difficulty: basic
skill: ordem_de_operacoes

### Questão 2
Calcule `10 + 2 × 3 − 4`.
A) 12
B) 32
C) 0
D) 16
**Resposta:** A
**Feedback:** `2 × 3 = 6`, então `10 + 6 − 4 = 12`. A alternativa B resolve tudo da esquerda para a direita, ignorando a prioridade. C inverte o sinal da multiplicação. D esquece a subtração final.

question_id: mb-01-q02
difficulty: basic
skill: ordem_de_operacoes

### Questão 3
Calcule `3² + 4 × 2`.
A) 17
B) 26
C) 25
D) 72
**Resposta:** A
**Feedback:** `3² = 9`, `4 × 2 = 8`, soma: `9 + 8 = 17`. B soma primeiro dentro de um parêntese imaginário. C calcula `3² + 4²`, aplicando o expoente aos dois termos. D multiplica tudo.

question_id: mb-01-q03
difficulty: basic
skill: ordem_de_operacoes

### Questão 4
Calcule `20 ÷ 4 + 3 × (7 − 2)`.
A) 20
B) 40
C) 16
D) 10
**Resposta:** A
**Feedback:** `20 ÷ 4 = 5`. `(7 − 2) = 5`. `3 × 5 = 15`. `5 + 15 = 20`. B multiplica o resultado intermediário pelo parêntese inteiro. C usa `2` em vez de `5` dentro do parêntese. D trata a multiplicação como soma.

question_id: mb-01-q04
difficulty: intermediate
skill: ordem_de_operacoes

### Questão 5
Calcule `2 + 3 × 4 − 6 ÷ 2`.
A) 11
B) 7
C) 14
D) 17
**Resposta:** A
**Feedback:** `3 × 4 = 12`, `6 ÷ 2 = 3`, então `2 + 12 − 3 = 11`. B resolve tudo da esquerda para a direita. C esquece de subtrair o `3`. D soma o `3` em vez de subtrair.

question_id: mb-01-q05
difficulty: intermediate
skill: ordem_de_operacoes

### Questão 6
Calcule `(8 − 3)² ÷ 5 + 2 × 3`.
A) 11
B) 21
C) 5
D) 31
**Resposta:** A
**Feedback:** `(8 − 3) = 5`, `5² = 25`, `25 ÷ 5 = 5`, `2 × 3 = 6`, `5 + 6 = 11`. B soma `5 + 2` antes de multiplicar por 3. C para logo após a divisão. D soma 25 e 6 sem dividir.

question_id: mb-01-q06
difficulty: intermediate
skill: ordem_de_operacoes

### Questão 7
Calcule `20 − 2 × (3² − 4) + 8 ÷ 4`.
A) 12
B) 8
C) 14
D) 92
**Resposta:** A
**Feedback:** `3² = 9`, `9 − 4 = 5`, `2 × 5 = 10`, `8 ÷ 4 = 2`, então `20 − 10 + 2 = 12`. B troca o sinal do `+2` final. C usa `8 ÷ 2` em vez de `8 ÷ 4`. D multiplica o resultado do parêntese inteiro por `20 − 2`.

question_id: mb-01-q07
difficulty: advanced
skill: ordem_de_operacoes

### Questão 8
Se `a = 2`, `b = 3` e `c = 4`, calcule `a + b² − c × a`.
A) 3
B) 0
C) 11
D) 1
**Resposta:** A
**Feedback:** `b² = 9`, `c × a = 8`, então `2 + 9 − 8 = 3`. B calcula `3² = 6`, erro comum. C esquece de subtrair o produto. D troca o sinal do `9`.

question_id: mb-01-q08
difficulty: advanced
skill: ordem_de_operacoes

### Questão 9
Um estudante calculou `100 ÷ 10 × 2` e obteve 5. Outro obteve 20. Qual raciocínio está correto?
A) 5, porque a divisão tem prioridade sobre a multiplicação.
B) 20, porque multiplicação e divisão têm a mesma prioridade e resolvem-se da esquerda para a direita.
C) 5, porque devemos calcular `10 × 2 = 20` antes de dividir.
D) 20, porque a multiplicação tem prioridade sobre a divisão.
**Resposta:** B
**Feedback:** Multiplicação e divisão pertencem ao mesmo nível. Resolve-se `100 ÷ 10 = 10` primeiro e depois `10 × 2 = 20`. As alternativas A e D aplicam uma prioridade que não existe. C chega ao mesmo número por raciocínio incorreto.

question_id: mb-01-q09
difficulty: transfer
skill: ordem_de_operacoes

### Questão 10
Em uma compra, o valor total é dado por `3 × 12 + 5 × 8 − 10`. Qual o total?
A) 66
B) 76
C) 56
D) 46
**Resposta:** A
**Feedback:** `3 × 12 = 36`, `5 × 8 = 40`, `36 + 40 − 10 = 66`. B soma 10 em vez de subtrair. C e D subtraem valores errados.

question_id: mb-01-q10
difficulty: applied
skill: ordem_de_operacoes

## Desafio final

Calcule:

`2 + 3 × {4 + 5 × [6 − 2 × (3 − 1)]}`

**Resposta:** 44

**Resolução:**
- `(3 − 1) = 2`
- `2 × 2 = 4`, então `[6 − 4] = 2`
- `5 × 2 = 10`, então `{4 + 10} = 14`
- `3 × 14 = 42`
- `2 + 42 = 44`

## Vídeo
**Vídeo em breve**
Aula conduzida pelo 1º lugar em Medicina da USP.
`video_url: null`