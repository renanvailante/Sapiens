---
course_id: matematica-basica
station_id: 14
title: "Equações do 2º grau"
difficulty: advanced
status: coming_soon
video: null
skills:
  - equacoes_do_2_grau
  - bhaskara
  - discriminante
prerequisites:
  - equacoes_do_1_grau
  - radiciacao
---

# mat basica 14 — Equações do 2º grau

## Objetivo

Você vai resolver equações do 2º grau por Bhaskara, fatoração e completamento de quadrados, e interpretar o discriminante.

## Pré-requisitos

Equações do 1º grau (Estação 11) e Radiciação (Estação 08).

## Conteúdo

Equação do 2º grau tem a forma:

`ax² + bx + c = 0`, com `a ≠ 0`

### Fórmula de Bhaskara

`Δ = b² − 4ac`

`x = (−b ± √Δ) / (2a)`

### Interpretação do discriminante

- `Δ > 0` → **duas raízes reais distintas**
- `Δ = 0` → **uma raiz real dupla**
- `Δ < 0` → **nenhuma raiz real**

### Relações de soma e produto

Quando `a = 1`:

- Soma: `x₁ + x₂ = −b`
- Produto: `x₁ × x₂ = c`

Generalizando: `x₁ + x₂ = −b/a` e `x₁ × x₂ = c/a`.

### Casos particulares

- `b = 0`: `ax² + c = 0` → `x = ±√(−c/a)`
- `c = 0`: `ax² + bx = 0` → `x(ax + b) = 0` → `x = 0` ou `x = −b/a`

## Exemplos resolvidos

**Exemplo 1.** Resolva `x² − 5x + 6 = 0`.
- `Δ = 25 − 24 = 1`
- `x = (5 ± 1)/2` → `x = 3` ou `x = 2`

**Exemplo 2.** Resolva `x² − 9 = 0`.
- `x² = 9`
- `x = ±3`

**Exemplo 3.** Resolva `2x² − 4x − 6 = 0`.
- Dividindo por 2: `x² − 2x − 3 = 0`
- `Δ = 4 + 12 = 16`
- `x = (2 ± 4)/2` → `x = 3` ou `x = −1`

**Exemplo 4.** Fatoração direta: `x² − 5x + 6 = (x − 2)(x − 3)`.
- Confirmando: `x² − 3x − 2x + 6 = x² − 5x + 6` ✓

## Estratégias

- Antes de aplicar Bhaskara, verifique se a equação é incompleta (`b = 0` ou `c = 0`). Aí é mais rápido isolar.
- Verifique se há fator comum. Divida tudo por ele.
- Em problemas contextualizados, apenas uma das raízes faz sentido físico (tempo, distância, idade).
- Soma e produto ajudam a **conferir** as raízes encontradas.

## Erros comuns

- **Esquecer o sinal de `b` em `−b`.**
- **Errar o sinal dentro de `Δ = b² − 4ac`.** `− 4ac`, não `+ 4ac`.
- **Dividir só o `−b` por `2a`.** A divisão se aplica a toda a expressão.
- **Aceitar duas respostas em problemas físicos.** Raiz negativa costuma ser descartada.

## Exercícios

### Questão 1
Resolva `x² − 5x + 6 = 0`.
A) x = 2 ou x = 3
B) x = −2 ou x = −3
C) x = 1 ou x = 6
D) x = −1 ou x = 6
**Resposta:** A
**Feedback:** `Δ = 1`, `x = (5 ± 1)/2`. B troca os sinais. C e D vêm de fatoração errada.

question_id: mb-14-q01
difficulty: basic
skill: equacoes_do_2_grau

### Questão 2
Qual o discriminante de `x² − 4x + 3 = 0`?
A) 4
B) 16
C) −4
D) 0
**Resposta:** A
**Feedback:** `Δ = 16 − 12 = 4`. B ignora o `4ac`. C troca o sinal. D iguala a zero.

question_id: mb-14-q02
difficulty: basic
skill: discriminante

### Questão 3
Resolva `x² − 9 = 0`.
A) x = 3 ou x = −3
B) x = 3 ou x = 0
C) x = 9 ou x = −9
D) x = ±√3
**Resposta:** A
**Feedback:** `x² = 9 → x = ±3`. B ignora a raiz negativa. C não extrai a raiz. D erra o radicando.

question_id: mb-14-q03
difficulty: basic
skill: equacoes_do_2_grau

### Questão 4
Resolva `x² − 6x + 9 = 0`.
A) x = 3 (raiz dupla)
B) x = −3 (raiz dupla)
C) x = 3 ou x = −3
D) sem raiz real
**Resposta:** A
**Feedback:** `Δ = 36 − 36 = 0`, `x = 6/2 = 3`. B troca o sinal. C considera duas raízes. D não reconhece o caso `Δ = 0`.

question_id: mb-14-q04
difficulty: intermediate
skill: discriminante

### Questão 5
Resolva `2x² − 8 = 0`.
A) x = 2 ou x = −2
B) x = 4 ou x = −4
C) x = 8 ou x = −8
D) x = √2 ou x = −√2
**Resposta:** A
**Feedback:** `x² = 4 → x = ±2`. B e C não dividem por 2. D erra a raiz.

question_id: mb-14-q05
difficulty: intermediate
skill: equacoes_do_2_grau

### Questão 6
Resolva `x² + x − 6 = 0`.
A) x = 2 ou x = −3
B) x = −2 ou x = 3
C) x = 1 ou x = −6
D) x = −1 ou x = 6
**Resposta:** A
**Feedback:** `Δ = 25`, `x = (−1 ± 5)/2`. B troca os sinais. C e D vêm de fatoração errada.

question_id: mb-14-q06
difficulty: intermediate
skill: equacoes_do_2_grau

### Questão 7
Na equação `x² − 7x + 10 = 0`, a soma e o produto das raízes são, respectivamente:
A) 7 e 10
B) −7 e 10
C) 7 e −10
D) 10 e 7
**Resposta:** A
**Feedback:** Soma `= −b/a = 7`, produto `= c/a = 10`. B troca o sinal. C e D invertem.

question_id: mb-14-q07
difficulty: advanced
skill: equacoes_do_2_grau

### Questão 8
Resolva `2x² − 4x − 6 = 0`.
A) x = 3 ou x = −1
B) x = −3 ou x = 1
C) x = 6 ou x = −2
D) x = 2 ou x = −3
**Resposta:** A
**Feedback:** Dividindo por 2: `x² − 2x − 3 = 0`, `Δ = 16`, `x = (2 ± 4)/2`. B troca os sinais. C e D vêm de não dividir antes.

question_id: mb-14-q08
difficulty: advanced
skill: equacoes_do_2_grau

### Questão 9
A fatoração de `x² − 5x + 6` é:
A) (x − 2)(x − 3)
B) (x + 2)(x + 3)
C) (x − 1)(x − 6)
D) (x + 1)(x − 6)
**Resposta:** A
**Feedback:** Raízes 2 e 3. B troca sinais. C e D usam raízes erradas.

question_id: mb-14-q09
difficulty: transfer
skill: equacoes_do_2_grau

### Questão 10
A área de um retângulo é 24 m². O comprimento é 2 m maior que a largura. Qual a largura?
A) 4 m
B) 6 m
C) 8 m
D) 3 m
**Resposta:** A
**Feedback:** `L(L + 2) = 24 → L² + 2L − 24 = 0`. `Δ = 4 + 96 = 100`, `L = (−2 + 10)/2 = 4`. B e C vêm de erros. D erra a conta.

question_id: mb-14-q10
difficulty: applied
skill: equacoes_do_2_grau

## Desafio final

Determine o valor de `m` para que a equação `x² − (m + 1)x + m = 0` tenha uma raiz dupla.

**Resposta:** m = 1

**Resolução:**
- Raiz dupla exige `Δ = 0`.
- `Δ = (m + 1)² − 4 × 1 × m = m² + 2m + 1 − 4m = m² − 2m + 1`
- `m² − 2m + 1 = (m − 1)² = 0`
- `m = 1`

## Vídeo
**Vídeo em breve**
Aula conduzida pelo 1º lugar em Medicina da USP.
`video_url: null`