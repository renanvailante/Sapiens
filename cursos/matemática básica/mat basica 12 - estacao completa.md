---
course_id: matematica-basica
station_id: 12
title: "Sistemas de equações"
difficulty: intermediate
status: coming_soon
video: null
skills:
  - sistemas_de_equacoes
  - substituicao
  - adicao
prerequisites:
  - equacoes_do_1_grau
---

# mat basica 12 — Sistemas de equações

<!--
  ARQUIVO COMPLETADO EM 2026-09-16.

  O arquivo original desta estação (`deepseek_markdown_20260916_bf5774.md`)
  chegou TRUNCADO: 572 bytes, cortado no meio da primeira frase da seção
  `## Conteúdo`, sem exemplos, sem exercícios e sem desafio. Ele continua
  intacto na pasta — nada foi apagado nem renomeado.

  Esta é a versão completa, escrita na mesma estrutura das outras 23 estações
  (frontmatter idêntico, mesmas seções, dez questões na mesma escada de
  dificuldade, `question_id` no padrão `mb-12-qNN`). O ingestor escolhe entre
  as duas fontes pela mais completa e anuncia a escolha na saída.
-->

## Objetivo

Você vai resolver sistemas 2×2 pelos métodos da substituição e da adição, e usar sistemas para resolver problemas com duas incógnitas.

## Pré-requisitos

Equações do 1º grau (Estação 11).

## Conteúdo

Um sistema 2×2 tem duas equações e duas incógnitas:

`2x + y = 10`
`x − y = 2`

Resolver o sistema é encontrar o **par** `(x, y)` que torna as **duas** igualdades verdadeiras ao mesmo tempo. Um valor que serve só para uma das equações não é solução.

### Método da substituição

Isole uma incógnita em uma das equações e leve essa expressão para a outra.

1. Da segunda equação: `x = y + 2`.
2. Substitua na primeira: `2(y + 2) + y = 10`.
3. Resolva: `3y + 4 = 10`, então `y = 2`.
4. Volte: `x = 2 + 2 = 4`.

Prefira isolar a incógnita que já está quase sozinha — a que tem coeficiente 1.

### Método da adição

Some as duas equações de modo que uma das incógnitas desapareça. Se os coeficientes não forem opostos, multiplique uma das equações até que sejam.

1. `2x + y = 10`
2. `x − y = 2`
3. Somando, o `y` some: `3x = 12`, então `x = 4`.
4. Volte em qualquer equação: `y = 2`.

### Quantas soluções um sistema pode ter

| Situação | Quantas soluções | Como reconhecer |
|---|---|---|
| Retas que se cruzam | Uma só | Os coeficientes não são proporcionais |
| Retas iguais | Infinitas | Uma equação é múltipla da outra |
| Retas paralelas | Nenhuma | Mesmos coeficientes, resultados diferentes |

`x + y = 7` e `2x + 2y = 14` são a mesma reta escrita duas vezes: infinitas soluções. Já `x + y = 7` e `x + y = 9` se contradizem: nenhuma.

### Como conferir sem refazer a conta

Substitua o par encontrado nas **duas** equações originais. Se as duas fecham, acabou. Conferir custa dez segundos e pega quase todo erro de sinal.

## Exemplos resolvidos

**Exemplo 1.** Resolva `x + y = 9` e `x − y = 1` pela adição.
- Somando as duas: `2x = 10`, então `x = 5`
- Volte na primeira: `5 + y = 9`, então `y = 4`
- Confira na segunda: `5 − 4 = 1`

**Exemplo 2.** Resolva `y = 3x` e `x + y = 16` pela substituição.
- A segunda já entrega `y`: substitua direto
- `x + 3x = 16`, então `4x = 16` e `x = 4`
- `y = 3 × 4 = 12`

**Exemplo 3.** Resolva `3x + 2y = 16` e `x − y = 2`.
- Isole na segunda: `x = y + 2`
- Substitua na primeira: `3(y + 2) + 2y = 16`
- `5y + 6 = 16`, então `y = 2` e `x = 4`
- Confira: `3 × 4 + 2 × 2 = 16`

## Estratégias

- **Escolha o método pelo sistema, não por gosto.** Se alguma incógnita tem coeficiente 1, substituição é mais rápida. Se os coeficientes de uma incógnita já são opostos, adição resolve em uma linha.
- **Antes de multiplicar, olhe os sinais.** Multiplicar a equação certa por `−1` costuma poupar duas linhas de conta.
- **Multiplique a equação INTEIRA.** Todos os termos, inclusive o resultado do outro lado da igualdade.
- **Confira nas duas equações.** É o único jeito de saber que o par é solução do sistema, e não só de uma das equações.

## Erros comuns

- **Multiplicar só um lado da equação.** `2 × (x − y = 2)` é `2x − 2y = 4`, não `2x − 2y = 2`.
- **Trocar x por y na resposta.** O par `(4, 2)` não é o mesmo que `(2, 4)`.
- **Parar na primeira incógnita.** Achar `x` e esquecer de voltar para achar `y` deixa o sistema pela metade.
- **Errar o sinal ao somar.** Somar `x − y = 2` com `2x + y = 10` cancela o `y`; subtrair, não.
- **Conferir em uma equação só.** Todo par errado satisfaz alguma equação — é a outra que o denuncia.

## Exercícios

### Questão 1
Resolva o sistema `x + y = 10` e `x − y = 4`.
A) x = 7 e y = 3
B) x = 3 e y = 7
C) x = 5 e y = 5
D) x = 6 e y = 4
**Resposta:** A
**Feedback:** Somando as duas equações, o `y` se cancela: `2x = 14`, então `x = 7` e `y = 10 − 7 = 3`. B troca os valores das duas incógnitas. C divide a soma ao meio e ignora a diferença. D não satisfaz a segunda equação.

question_id: mb-12-q01
difficulty: basic
skill: sistemas_de_equacoes

### Questão 2
Resolva o sistema `x + y = 12` e `y = 2x`.
A) x = 4 e y = 8
B) x = 8 e y = 4
C) x = 6 e y = 6
D) x = 3 e y = 9
**Resposta:** A
**Feedback:** Substituindo `y = 2x` na primeira equação: `3x = 12`, então `x = 4` e `y = 8`. B troca os valores das duas incógnitas. C ignora a segunda equação. D usa `y = 3x` em vez de `y = 2x`.

question_id: mb-12-q02
difficulty: basic
skill: substituicao

### Questão 3
No sistema `2x + y = 9` e `y = 3`, qual é o valor de `x`?
A) 3
B) 6
C) 4,5
D) 1,5
**Resposta:** A
**Feedback:** Com `y = 3`, a primeira equação vira `2x + 3 = 9`, então `2x = 6` e `x = 3`. B esquece de dividir por 2. C divide 9 por 2 sem subtrair o 3. D subtrai o 3 duas vezes.

question_id: mb-12-q03
difficulty: basic
skill: substituicao

### Questão 4
Resolva o sistema `3x + 2y = 16` e `x − y = 2`.
A) x = 4 e y = 2
B) x = 2 e y = 4
C) x = 6 e y = −1
D) x = 3 e y = 1
**Resposta:** A
**Feedback:** Isolando `x = y + 2` e substituindo: `3(y + 2) + 2y = 16`, `5y = 10`, então `y = 2` e `x = 4`. B troca os valores das duas incógnitas. C satisfaz a primeira equação e não a segunda. D satisfaz a segunda e não a primeira.

question_id: mb-12-q04
difficulty: intermediate
skill: substituicao

### Questão 5
Resolva o sistema `2x + 3y = 12` e `4x − 3y = 6`.
A) x = 3 e y = 2
B) x = 2 e y = 3
C) x = 3 e y = 6
D) x = 1,5 e y = 3
**Resposta:** A
**Feedback:** Somando as duas equações, os termos em `y` se cancelam: `6x = 18`, então `x = 3`; voltando, `3y = 6` e `y = 2`. B troca os valores das duas incógnitas. C esquece de dividir por 3 ao isolar y. D divide o x por 2 sem motivo.

question_id: mb-12-q05
difficulty: intermediate
skill: adicao

### Questão 6
A soma de dois números é 30 e a diferença entre eles é 8. Quais são esses números?
A) 19 e 11
B) 22 e 8
C) 20 e 10
D) 18 e 12
**Resposta:** A
**Feedback:** O sistema é `x + y = 30` e `x − y = 8`. Somando, `2x = 38`, então `x = 19` e `y = 11`. B usa a diferença como se fosse um dos números. C e D somam 30, mas a diferença entre eles não é 8.

question_id: mb-12-q06
difficulty: intermediate
skill: sistemas_de_equacoes

### Questão 7
Resolva o sistema `5x − 2y = 4` e `3x + 4y = 18`.
A) x = 2 e y = 3
B) x = 3 e y = 2
C) x = 2 e y = −3
D) x = 4 e y = 8
**Resposta:** A
**Feedback:** Multiplicando a primeira equação por 2 e somando à segunda, o `y` se cancela: `13x = 26`, então `x = 2` e `y = 3`. B troca os valores das duas incógnitas. C erra o sinal ao isolar y. D satisfaz a primeira equação e não a segunda.

question_id: mb-12-q07
difficulty: advanced
skill: adicao

### Questão 8
Quantas soluções tem o sistema `x + y = 7` e `2x + 2y = 14`?
A) Infinitas, porque a segunda equação é a primeira multiplicada por 2.
B) Uma só, `x = 3,5` e `y = 3,5`.
C) Nenhuma, porque as duas equações se contradizem.
D) Exatamente duas.
**Resposta:** A
**Feedback:** A segunda equação é a primeira multiplicada por 2: as duas descrevem a mesma reta, e todo par que satisfaz uma satisfaz a outra. B escolhe um par entre infinitos. C descreveria `x + y = 7` com `x + y = 9`, que aí sim se contradizem. D não é possível: um sistema do 1º grau tem uma solução, nenhuma ou infinitas.

question_id: mb-12-q08
difficulty: advanced
skill: sistemas_de_equacoes

### Questão 9
Numa lanchonete, 2 sucos e 3 salgados custam R$ 26,00; 1 suco e 2 salgados custam R$ 15,00. Quanto custa um suco?
A) R$ 7,00
B) R$ 4,00
C) R$ 5,50
D) R$ 8,00
**Resposta:** A
**Feedback:** Com `s` de suco e `g` de salgado: `2s + 3g = 26` e `s + 2g = 15`. Isolando `s = 15 − 2g` e substituindo, `30 − g = 26`, então `g = 4` e `s = 7`. B responde o preço do salgado. C divide o total pelo número de itens. D não fecha a segunda compra.

question_id: mb-12-q09
difficulty: transfer
skill: sistemas_de_equacoes

### Questão 10
Numa prova de 30 questões, cada acerto vale 4 pontos e cada erro desconta 1 ponto. Um aluno respondeu todas e somou 70 pontos. Quantas ele acertou?
A) 20
B) 22
C) 18
D) 25
**Resposta:** A
**Feedback:** Com `a` acertos e `e` erros: `a + e = 30` e `4a − e = 70`. Somando, `5a = 100`, então `a = 20` acertos e 10 erros. B e D dariam mais de 70 pontos. C daria 60 pontos.

question_id: mb-12-q10
difficulty: applied
skill: sistemas_de_equacoes

## Desafio final

Resolva o sistema abaixo e informe o valor de `x + y`.

`3x + 2y = 19`
`5x − y = 10`

**Resposta:** 8

**Resolução:**
- Isole na segunda equação: `y = 5x − 10`
- Substitua na primeira: `3x + 2(5x − 10) = 19`
- `13x − 20 = 19`, então `13x = 39` e `x = 3`
- `y = 5 × 3 − 10 = 5`
- Confira: `3 × 3 + 2 × 5 = 19` e `5 × 3 − 5 = 10`
- `x + y = 3 + 5 = 8`

## Vídeo
**Vídeo em breve**
Aula conduzida pelo 1º lugar em Medicina da USP.
`video_url: null`
