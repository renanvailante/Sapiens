---
course_id: matematica-basica
station_id: 18
title: "Médias"
difficulty: intermediate
status: coming_soon
video: null
skills:
  - media_aritmetica
  - media_ponderada
  - mediana
prerequisites:
  - operacoes_fundamentais
  - fracoes
---

# mat basica 18 — Médias

## Objetivo

Você vai calcular média aritmética simples, média ponderada e mediana, e vai interpretar essas medidas em conjuntos de dados.

## Pré-requisitos

Operações fundamentais (Estação 01) e Frações (Estação 02).

## Conteúdo

### Média aritmética simples

`M = (x₁ + x₂ + ... + xₙ) / n`

Some todos os valores e divida pela quantidade.

### Média ponderada

Quando cada valor tem um **peso** diferente:

`M = (x₁·p₁ + x₂·p₂ + ... + xₙ·pₙ) / (p₁ + p₂ + ... + pₙ)`

Multiplique cada valor pelo seu peso, some, e divida pela soma dos pesos.

### Mediana

Valor central quando os dados estão **em ordem crescente**:

- Quantidade **ímpar** de dados → o valor do meio.
- Quantidade **par** de dados → média dos dois centrais.

### Comparação

- Média é sensível a **valores extremos**.
- Mediana resiste a valores extremos.
- Em salários, renda e imóveis, mediana costuma representar melhor o “típico”.

## Exemplos resolvidos

**Exemplo 1.** Média de `4, 6, 8`.
- `(4 + 6 + 8)/3 = 18/3 = 6`

**Exemplo 2.** Média ponderada: notas `8` (peso 2) e `6` (peso 3).
- `(8×2 + 6×3)/(2+3) = (16 + 18)/5 = 34/5 = 6,8`

**Exemplo 3.** Mediana de `{3, 5, 8, 9, 12}`.
- Ordem crescente, 5 valores, central é o 3º: `8`

**Exemplo 4.** Mediana de `{2, 4, 6, 8}`.
- 4 valores, central é a média do 2º e 3º: `(4 + 6)/2 = 5`

## Estratégias

- Antes de calcular, **conte quantos valores** existem. É o erro mais comum.
- Em média ponderada, sempre verifique a soma dos pesos.
- Para a mediana, **coloque em ordem primeiro**. Nunca trabalhe com dados fora de ordem.
- Em problemas com valor faltante, use a soma total implícita: `M × n = soma`.

## Erros comuns

- **Dividir pela soma dos pesos em vez da quantidade** na média simples, ou vice-versa.
- **Esquecer de ordenar** antes de achar a mediana.
- **Confundir mediana com moda.** Moda é o valor mais frequente.
- **Achar que a média é sempre o valor mais representativo.** Em dados assimétricos, a mediana representa melhor.

## Exercícios

### Questão 1
Calcule a média de 4, 6 e 8.
A) 6
B) 5
C) 7
D) 18
**Resposta:** A
**Feedback:** `18/3 = 6`. B, C erram a divisão. D não divide.

question_id: mb-18-q01
difficulty: basic
skill: media_aritmetica

### Questão 2
Calcule a média de 5, 7, 9 e 11.
A) 8
B) 7
C) 9
D) 32
**Resposta:** A
**Feedback:** `32/4 = 8`. B, C erram. D não divide.

question_id: mb-18-q02
difficulty: basic
skill: media_aritmetica

### Questão 3
Qual a mediana de `{3, 5, 8, 9, 12}`?
A) 8
B) 5
C) 9
D) 7
**Resposta:** A
**Feedback:** Já ordenado, 5 valores, central é 8. B é o 2º. C é o 4º. D é média indevida.

question_id: mb-18-q03
difficulty: basic
skill: mediana

### Questão 4
Média ponderada: notas `8` (peso 2) e `6` (peso 3).
A) 6,8
B) 7,0
C) 7,2
D) 6,5
**Resposta:** A
**Feedback:** `(16+18)/5 = 34/5 = 6,8`. B, C e D vêm de pesos errados.

question_id: mb-18-q04
difficulty: intermediate
skill: media_ponderada

### Questão 5
Mediana de `{2, 4, 6, 8}`.
A) 5
B) 4
C) 6
D) 4,5
**Resposta:** A
**Feedback:** `(4+6)/2 = 5`. B e C escolhem só um. D erra a média.

question_id: mb-18-q05
difficulty: intermediate
skill: mediana

### Questão 6
Um aluno tirou notas 6, 7, 8 e 9. Qual a média?
A) 7,5
B) 7
C) 8
D) 7,75
**Resposta:** A
**Feedback:** `(6+7+8+9)/4 = 30/4 = 7,5`. B, C e D vêm de erros.

question_id: mb-18-q06
difficulty: intermediate
skill: media_aritmetica

### Questão 7
A média de 4 números é 7. Se 3 deles são 5, 8 e 6, qual o quarto?
A) 9
B) 8
C) 10
D) 7
**Resposta:** A
**Feedback:** Soma total: `7 × 4 = 28`. `28 − (5+8+6) = 28 − 19 = 9`. B, C e D não fecham a soma.

question_id: mb-18-q07
difficulty: advanced
skill: media_aritmetica

### Questão 8
Média ponderada com valores 8, 7, 6 e pesos 1, 2, 3, respectivamente.
A) 6,67
B) 7
C) 7,33
D) 6
**Resposta:** A
**Feedback:** `(8·1 + 7·2 + 6·3)/(1+2+3) = (8+14+18)/6 = 40/6 ≈ 6,67`. B, C e D erram pesos.

question_id: mb-18-q08
difficulty: advanced
skill: media_ponderada

### Questão 9
Salários de 5 funcionários: 2.000, 2.000, 2.500, 3.000, 15.000. Qual a diferença entre média e mediana?
A) 1.900
B) 2.000
C) 1.500
D) 500
**Resposta:** A
**Feedback:** Média: `(2000+2000+2500+3000+15000)/5 = 24500/5 = 4.900`. Mediana: `2.500`. Diferença: `4.900 − 2.500 = 2.400`.

Correção: a diferença é **2.400**, valor não listado. Substituído abaixo.

### Questão 9 (versão corrigida)
Salários de 5 funcionários: 2.000, 2.000, 2.500, 3.000, 12.000. Qual a diferença entre média e mediana?
A) 1.900
B) 2.000
C) 1.500
D) 2.400
**Resposta:** A
**Feedback:** Média: `(2000+2000+2500+3000+12000)/5 = 21500/5 = 4.300`. Mediana: `2.500`. Diferença: `4.300 − 2.500 = 1.800`. Revisão: `1.800`, não listado. Nova versão abaixo.

### Questão 9 (versão final)
Dados os valores `{2, 4, 4, 5, 10}`, qual a diferença entre média e mediana?
A) 1
B) 2
C) 0,5
D) 1,5
**Resposta:** A
**Feedback:** Média: `25/5 = 5`. Mediana: `4`. Diferença: `1`. B, C e D vêm de erros.

question_id: mb-18-q09
difficulty: transfer
skill: media_aritmetica

### Questão 10
Um aluno tem notas 5, 6, 7 em três provas. Que nota precisa na quarta para ter média 6,5?
A) 8
B) 7
C) 9
D) 7,5
**Resposta:** A
**Feedback:** `5+6+7+x = 4 × 6,5 = 26`. `x = 26 − 18 = 8`. B, C e D não fecham.

question_id: mb-18-q10
difficulty: applied
skill: media_aritmetica

## Desafio final

Em uma turma, a média das notas dos 20 alunos é 7. Se um aluno com nota 5 sair da turma, qual a nova média?

**Resposta:** 7,1

**Resolução:**
- Soma total: `20 × 7 = 140`
- Após a saída: `140 − 5 = 135`
- Nova média: `135/19 ≈ 7,105` → aproximadamente `7,11`
- Aproximando para uma casa decimal: `7,1`

## Vídeo
**Vídeo em breve**
Aula conduzida pelo 1º lugar em Medicina da USP.
`video_url: null`