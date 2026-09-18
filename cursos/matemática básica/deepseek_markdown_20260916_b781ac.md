---
course_id: matematica-basica
station_id: 09
title: "Notação científica"
difficulty: intermediate
status: coming_soon
video: null
skills:
  - notacao_cientifica
  - ordem_de_grandeza
  - operacoes_com_potencias_de_dez
prerequisites:
  - potenciacao
---

# mat basica 9 — Notação científica

## Objetivo

Você vai representar números muito grandes e muito pequenos em notação científica, operá-los e estimar ordens de grandeza.

## Pré-requisitos

Potenciação (Estação 07).

## Conteúdo

Notação científica escreve qualquer número na forma:

`a × 10ⁿ`

com `1 ≤ a < 10` e `n` inteiro.

- `3.000 = 3 × 10³`
- `0,00025 = 2,5 × 10⁻⁴`

### Como converter

- Números grandes: mova a vírgula para a esquerda até sobrar um número entre 1 e 10. O número de casas movidas é o expoente (positivo).
- Números pequenos: mova a vírgula para a direita. O expoente é negativo.

### Operações

| Operação | Regra |
|---|---|
| Multiplicação | multiplique os coeficientes, **some** os expoentes |
| Divisão | divida os coeficientes, **subtraia** os expoentes |
| Soma/subtração | iguale os expoentes e depois some os coeficientes |
| Potência | eleve o coeficiente, **multiplique** o expoente |

Se após a operação o coeficiente sair de `[1, 10)`, ajuste o expoente.

### Ordem de grandeza

Ordem de grandeza é a potência de 10 mais próxima do valor.

- `2.500 = 2,5 × 10³` → ordem de grandeza `10³`
- `6.700 = 6,7 × 10³` → ordem de grandeza `10⁴`

Regra prática: se o coeficiente é `≥ √10 ≈ 3,16`, arredonda para cima.

## Exemplos resolvidos

**Exemplo 1.** Escreva `45.000` em notação científica.
- `4,5 × 10⁴`

**Exemplo 2.** Escreva `0,00032` em notação científica.
- `3,2 × 10⁻⁴`

**Exemplo 3.** Calcule `(3 × 10⁵) × (4 × 10³)`.
- `12 × 10⁸ = 1,2 × 10⁹`

**Exemplo 4.** Calcule `(8 × 10⁷) ÷ (2 × 10³)`.
- `4 × 10⁴`

## Estratégias

- Sempre confira se o coeficiente está entre 1 e 10. Se não, ajuste o expoente.
- Em produtos, multiplique primeiro os coeficientes, depois some expoentes.
- Em soma, é preciso igualar expoentes antes.
- Em problemas reais, ordem de grandeza serve para verificar se o resultado faz sentido.

## Erros comuns

- **Somar expoentes em produto sem ajustar o coeficiente.** `(3 × 10⁵)(4 × 10³) = 12 × 10⁸`, precisa virar `1,2 × 10⁹`.
- **Somar expoentes em soma de números.** Não se aplica.
- **Confundir expoente positivo com negativo** em números menores que 1.
- **Deixar o coeficiente fora do intervalo `[1, 10)`.**

## Exercícios

### Questão 1
Escreva `45.000` em notação científica.
A) 4,5 × 10⁴
B) 45 × 10³
C) 4,5 × 10⁵
D) 0,45 × 10⁵
**Resposta:** A
**Feedback:** Coeficiente entre 1 e 10 e expoente `4`. B e D têm coeficientes fora do intervalo. C desloca a vírgula para o lado errado.

question_id: mb-09-q01
difficulty: basic
skill: notacao_cientifica

### Questão 2
Escreva `0,00032`.
A) 3,2 × 10⁻⁴
B) 32 × 10⁻⁵
C) 3,2 × 10⁴
D) 0,32 × 10⁻³
**Resposta:** A
**Feedback:** Coeficiente `3,2`, expoente `−4`. B e D têm coeficientes fora do intervalo. C tem sinal errado.

question_id: mb-09-q02
difficulty: basic
skill: notacao_cientifica

### Questão 3
Qual é a ordem de grandeza de `2.500`?
A) 10³
B) 10⁴
C) 10²
D) 10⁵
**Resposta:** A
**Feedback:** `2,5 × 10³`, coeficiente `2,5 < 3,16`, então ordem `10³`. B arredonda para cima sem necessidade. C e D estão fora.

question_id: mb-09-q03
difficulty: basic
skill: ordem_de_grandeza

### Questão 4
Calcule `(3 × 10⁵) × (4 × 10³)`.
A) 1,2 × 10⁹
B) 12 × 10⁸
C) 7 × 10⁸
D) 1,2 × 10⁸
**Resposta:** A
**Feedback:** `12 × 10⁸ = 1,2 × 10⁹`. B tem coeficiente fora do intervalo. C soma. D erra expoente.

question_id: mb-09-q04
difficulty: intermediate
skill: operacoes_com_potencias_de_dez

### Questão 5
Calcule `(8 × 10⁷) ÷ (2 × 10³)`.
A) 4 × 10⁴
B) 4 × 10¹⁰
C) 6 × 10⁴
D) 4 × 10²¹
**Resposta:** A
**Feedback:** `8/2 = 4`, `10⁷⁻³ = 10⁴`. B soma expoentes. C subtrai coeficientes. D multiplica.

question_id: mb-09-q05
difficulty: intermediate
skill: operacoes_com_potencias_de_dez

### Questão 6
Calcule `(2 × 10⁴) + (3 × 10⁴)`.
A) 5 × 10⁴
B) 5 × 10⁸
C) 6 × 10⁴
D) 5 × 10²
**Resposta:** A
**Feedback:** Expoentes iguais: soma coeficientes. `5 × 10⁴`. B multiplica expoentes. C multiplica coeficientes. D subtrai.

question_id: mb-09-q06
difficulty: intermediate
skill: operacoes_com_potencias_de_dez

### Questão 7
Calcule `(6 × 10³)²`.
A) 3,6 × 10⁷
B) 36 × 10⁶
C) 6 × 10⁶
D) 3,6 × 10⁶
**Resposta:** A
**Feedback:** `6² = 36`, `10⁶`, resultado `36 × 10⁶ = 3,6 × 10⁷`. B coeficiente fora do intervalo. C não eleva o coeficiente. D erra expoente.

question_id: mb-09-q07
difficulty: advanced
skill: operacoes_com_potencias_de_dez

### Questão 8
Calcule `(4 × 10⁻³) × (5 × 10⁷)`.
A) 2 × 10⁵
B) 20 × 10⁴
C) 2 × 10⁴
D) 9 × 10⁴
**Resposta:** A
**Feedback:** `4 × 5 = 20`, `10⁻³⁺⁷ = 10⁴`, resultado `20 × 10⁴ = 2 × 10⁵`. B coeficiente fora do intervalo. C erra expoente. D soma coeficientes.

question_id: mb-09-q08
difficulty: advanced
skill: operacoes_com_potencias_de_dez

### Questão 9
A massa de um elétron é aproximadamente `9,1 × 10⁻³¹ kg`. Um aluno escreveu `91 × 10⁻³²`. Essa forma é:
A) equivalente, mas fora do padrão de notação científica
B) diferente do valor
C) impossível
D) um número negativo
**Resposta:** A
**Feedback:** `91 × 10⁻³² = 9,1 × 10⁻³¹`, mesma quantidade, mas o coeficiente não está entre 1 e 10.

question_id: mb-09-q09
difficulty: transfer
skill: notacao_cientifica

### Questão 10
A distância média da Terra ao Sol é `1,5 × 10¹¹ m`. Escreva esse valor em km.
A) 1,5 × 10⁸ km
B) 1,5 × 10¹⁴ km
C) 1,5 × 10⁹ km
D) 1,5 × 10¹⁰ km
**Resposta:** A
**Feedback:** `1 km = 10³ m`, então `1,5 × 10¹¹ / 10³ = 1,5 × 10⁸ km`. B multiplica em vez de dividir. C e D erram o expoente.

question_id: mb-09-q10
difficulty: applied
skill: notacao_cientifica

## Desafio final

Calcule e escreva em notação científica:

`(3 × 10⁸) × (4 × 10⁻⁵) ÷ (6 × 10⁻²)`

**Resposta:** 2 × 10⁵

**Resolução:**
- `(3 × 10⁸) × (4 × 10⁻⁵) = 12 × 10³ = 1,2 × 10⁴`
- `1,2 × 10⁴ ÷ (6 × 10⁻²) = (1,2/6) × 10⁴⁻⁽⁻²⁾ = 0,2 × 10⁶ = 2 × 10⁵`

## Vídeo
**Vídeo em breve**
Aula conduzida pelo 1º lugar em Medicina da USP.
`video_url: null`