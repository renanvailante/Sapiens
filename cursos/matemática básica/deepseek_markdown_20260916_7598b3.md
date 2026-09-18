---
course_id: matematica-basica
station_id: 22
title: "Matemática financeira básica"
difficulty: advanced
status: coming_soon
video: null
skills:
  - juros_simples
  - descontos
  - montante
prerequisites:
  - porcentagem
  - equacoes_do_1_grau
---

# mat basica 22 — Matemática financeira básica

## Objetivo

Você vai calcular juros simples, montantes, descontos e aumentos, e vai resolver problemas financeiros do cotidiano.

## Pré-requisitos

Porcentagem (Estação 05) e Equações do 1º grau (Estação 11).

## Conteúdo

### Juros simples

`J = C × i × t`

- `C` = capital inicial
- `i` = taxa (decimal, por período)
- `t` = tempo (no mesmo período da taxa)

### Montante

`M = C + J = C(1 + i·t)`

### Descontos e aumentos

- Desconto de `p%`: multiplicar por `(1 − p/100)`
- Aumento de `p%`: multiplicar por `(1 + p/100)`

### Cuidados com a taxa

A taxa e o tempo devem estar na **mesma unidade**. Se a taxa é “ao mês”, o tempo é em meses.

Se a taxa é “ao ano” e o tempo em meses, converta antes:

- 1 ano = 12 meses
- taxa ao mês = taxa ao ano / 12 (em juros simples)

## Exemplos resolvidos

**Exemplo 1.** Juros simples de R$ 1.000 a 2% ao mês por 6 meses.
- `J = 1000 × 0,02 × 6 = 120`
- `M = 1.120`

**Exemplo 2.** Um produto de R$ 500 com desconto de 10%.
- `500 × 0,90 = 450`

**Exemplo 3.** Qual a taxa mensal que faz R$ 500 render R$ 60 em 4 meses?
- `60 = 500 × i × 4`
- `i = 60/2000 = 0,03 = 3% ao mês`

**Exemplo 4.** Em quanto tempo R$ 1.000 a 1,5% ao mês rendem R$ 90?
- `90 = 1000 × 0,015 × t`
- `t = 90/15 = 6 meses`

## Estratégias

- Antes de usar a fórmula, **converta a taxa para decimal**.
- Sempre verifique se taxa e tempo estão no mesmo período.
- Em problemas de “qual o montante”, use `M = C(1 + i·t)`.
- Em problemas de “qual o capital”, isole `C`.

## Erros comuns

- **Usar a taxa em percentual sem dividir por 100.** `2%` → `0,02`.
- **Misturar período.** Taxa ao mês com tempo em anos.
- **Confundir juros com montante.** Juros é o rendimento; montante é o total.
- **Achar que juros simples e compostos dão o mesmo resultado.** Não dão.

## Exercícios

### Questão 1
Juros simples de R$ 1.000 a 2% ao mês por 6 meses. Qual o juro?
A) R$ 120
B) R$ 12
C) R$ 200
D) R$ 60
**Resposta:** A
**Feedback:** `J = 1000 × 0,02 × 6 = 120`. B erra fator. C usa 20%. D usa 3 meses.

question_id: mb-22-q01
difficulty: basic
skill: juros_simples

### Questão 2
Um produto de R$ 500 com desconto de 10%.
A) R$ 450
B) R$ 490
C) R$ 400
D) R$ 550
**Resposta:** A
**Feedback:** `500 × 0,90 = 450`. B subtrai 10 reais. C e D erram.

question_id: mb-22-q02
difficulty: basic
skill: descontos

### Questão 3
Um produto de R$ 800 com aumento de 20%.
A) R$ 960
B) R$ 820
C) R$ 1.000
D) R$ 900
**Resposta:** A
**Feedback:** `800 × 1,20 = 960`. B soma 20. C e D erram.

question_id: mb-22-q03
difficulty: basic
skill: descontos

### Questão 4
Qual o montante de R$ 1.000 a 2% ao mês por 6 meses (juros simples)?
A) R$ 1.120
B) R$ 1.200
C) R$ 1.100
D) R$ 1.150
**Resposta:** A
**Feedback:** `J = 120`, `M = 1.120`. B erra taxa. C e D são aproximações.

question_id: mb-22-q04
difficulty: intermediate
skill: montante

### Questão 5
Qual a taxa mensal que faz R$ 500 render R$ 60 em 4 meses?
A) 3%
B) 2%
C) 4%
D) 5%
**Resposta:** A
**Feedback:** `60 = 500 × i × 4`, `i = 60/2000 = 0,03 = 3%`. B, C e D erram.

question_id: mb-22-q05
difficulty: intermediate
skill: juros_simples

### Questão 6
Em quanto tempo R$ 1.000 a 1,5% ao mês rendem R$ 90?
A) 6 meses
B) 4 meses
C) 5 meses
D) 8 meses
**Resposta:** A
**Feedback:** `90 = 1000 × 0,015 × t`, `t = 90/15 = 6`. B, C e D erram.

question_id: mb-22-q06
difficulty: intermediate
skill: juros_simples

### Questão 7
Um produto tem preço final R$ 224 com 12% de aumento. Qual o preço original?
A) R$ 200
B) R$ 212
C) R$ 210
D) R$ 202
**Resposta:** A
**Feedback:** `224 = C × 1,12`, `C = 200`. B, C e D erram.

question_id: mb-22-q07
difficulty: advanced
skill: juros_simples

### Questão 8
Uma loja oferece 15% de desconto para pagamento à vista e 5% de desconto adicional sobre o valor já descontado para clientes fiéis. Qual o desconto acumulado sobre o preço original?
A) 19,25%
B) 20%
C) 18%
D) 19%
**Resposta:** A
**Feedback:** `0,85 × 0,95 = 0,8075` → desconto de `19,25%`. B soma. C e D são aproximações.

question_id: mb-22-q08
difficulty: advanced
skill: descontos

### Questão 9
Um investimento de R$ 2.000 a juros simples de 3% ao mês, durante 1 ano, gera juros de:
A) R$ 720
B) R$ 600
C) R$ 7200
D) R$ 60
**Resposta:** A
**Feedback:** `J = 2000 × 0,03 × 12 = 720`. B usa 10 meses. C erra expoente. D usa 1 mês.

question_id: mb-22-q09
difficulty: transfer
skill: juros_simples

### Questão 10
Uma loja anuncia “leve 3, pague 2”. Qual o desconto percentual efetivo por unidade?
A) Aproximadamente 33,3%
B) 50%
C) 25%
D) 30%
**Resposta:** A
**Feedback:** Pagando 2 de 3, o desconto é `1/3 ≈ 33,3%`. B, C e D erram.

question_id: mb-22-q10
difficulty: applied
skill: descontos

## Desafio final

Um capital de R$ 3.000 é aplicado a juros simples de 2% ao mês. Após quanto tempo o montante será R$ 3.720?

**Resposta:** 12 meses

**Resolução:**
- Juro: `3.720 − 3.000 = 720`
- `720 = 3000 × 0,02 × t`
- `720 = 60t`
- `t = 12` meses

## Vídeo
**Vídeo em breve**
Aula conduzida pelo 1º lugar em Medicina da USP.
`video_url: null`