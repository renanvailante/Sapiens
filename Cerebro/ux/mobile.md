---
tags: [ux, mobile, invariante]
atualizado: 2026-10-01
---

# Invariantes de celular

Auditado em 375 e 320px, com sessão logada e medição no navegador (12/09 e 17/09).
Estas quatro coisas são fáceis de quebrar sem perceber — e **os piores defeitos não
apareciam lendo classe nenhuma, só medindo**: o ícone da Mentis cobria "Comprar",
"Marcar como feito" e a área de escrita da Redação; fórmula em KaTeX fazia a página
inteira deslizar de lado.

## 1. Existe UM bloco de media query por largura no produto inteiro

`@media (max-width: 1023px)` no `index.css`. **Regra global de celular vai ali**;
o resto da responsividade é Tailwind. Ele faz três coisas: força **16px nos
campos** (senão o Safari amplia a página e não desfaz), reserva o
`padding-bottom` do `body` e encolhe os rótulos da barra inferior abaixo de
360px.

> [!warning] Esse bloco mora ANTES das definições que ele sobrescreve
> Ele está por volta da linha 1164; `.aba-inferior` é definida na 1341. Com a
> mesma especificidade (0,1,0), **quem vence é quem vem depois** — uma regra
> escrita ali casa a media query, aparece no `cssRules` e mesmo assim não
> pinta. É por isso que o bloco de campos usa `:root input` e não `input`, e
> por isso a regra de 320px usa `:root .aba-inferior`.
>
> Achado em 18/09 medindo no navegador: a regra estava lá, `matchMedia` dava
> `true`, e a fonte computada continuava a antiga.

## 2. Essa faixa no `body` é a zona morta do ícone da Mentis

O widget é `fixed bottom-5 right-5`, 56px. Página que rola herda a folga de graça.

> **Página em `fixed inset-0` NÃO herda** — tem de criar a própria folga (o
> `BriefingHUD` do mapa usa `pb-24 sm:p-4`) ou o widget precisa sumir na rota
> (`/mentis` e `/feed` já somem, em `MentisWidget.jsx`).

O botão de "lembrar" nasce **abaixo** da seleção no toque, onde iOS e Android não
desenham o balão nativo — e fora da zona morta da Mentis.

## 3. Alvo de toque abaixo de ~32px é bug

O jeito da casa é **crescer a área sem mover o desenho**:

- link dentro de linha → `py-2 -my-2`
- botão de ícone → `-m-2.5 p-2.5`
- quando o quadrado desenhado precisa continuar pequeno (checkbox do Cronograma) →
  `before:absolute before:-inset-2.5 before:content-['']`

## 4. `flex-wrap` NÃO salva uma faixa "texto + botão"

Descoberta de 17/09, e a mais contraintuitiva daqui.

> Um filho com `flex-1 min-w-0` tem **tamanho hipotético ZERO**, então ele nunca
> força a quebra de linha: o botão `shrink-0` fica ao lado e o texto é espremido até
> uma palavra por linha. Medido: **47px de largura por 945px de altura** no card da
> live do Painel.

A receita da casa, em Tailwind e sem CSS novo:

```
contêiner:  flex flex-col items-stretch gap-4 sm:flex-row sm:items-center
linha ANINHADA (ícone/rosto + texto):
            flex min-w-0 flex-1 items-start gap-4 sm:items-center
botão:      w-full justify-center sm:w-auto
```

Aninhar é o que evita um retrato solto no topo do card. E o tamanho do
retrato conta: `MentorUSP` "g" tem **160px** no celular, e na chamada da
mentoria do Hoje deixava ~130px para a frase (achado em 2026-09-30). Em linha
com texto, abaixo de `sm`, é "m". Onde o rosto divide a linha
com texto, `MentorUSP` já encolhe sozinho (`m` = 80px, `g` = 144px) — e `m` só cresce
a partir de `sm`, porque a 375px um retrato de 112px deixa 171px para a frase.

## A camada de toque

Desde 17/09, no `index.css` **fora de qualquer media query de largura**:

- `-webkit-tap-highlight-color: transparent` + `touch-action: manipulation` em
  `a`/`button`/`label`;
- `text-size-adjust: 100%` no `html`;
- os hovers de card (`.lift`, `.superficie`, `.macio`) **fechados em**
  `@media (hover: hover) and (pointer: fine)` — em tela de toque o `:hover` grudava
  no último card tocado;
- a resposta ao toque virou `@media (hover: none) { …:active { transform: scale(.985) } }`.

## iOS: `viewport-fit=cover` é obrigatório

Sem ele o iOS devolve **0px para TODO `env(safe-area-inset-*)`**, e o CSS de
safe-area escrito em 16/09 nunca valeu no iPhone. Junto entraram as metas
`apple-mobile-web-app-*`, `padding-top: env(safe-area-inset-top)` no
`.glass`/`.exam-shell`/`.topo-seguro`, e o manifest ganhou `id`, propósitos
`any`/`maskable` separados e `shortcuts`.

## 5. O rótulo mais longo da barra inferior

Medido a 320px em 18/09: **"Comunidade" era cortado** pelo `text-overflow:
ellipsis`, sem estouro horizontal e sem quebra de linha — nada acusava. Até
então o maior rótulo era "Painel" (6 caracteres) e o quinto alvo era "Mais";
com as cinco áreas, o maior tem 10.

Encurtar a palavra **não é opção**: o produto tem um nome por conceito
(`lib/navegacao.NOMES`), e "Mural" na barra contra "Comunidade" em toda outra
superfície reintroduz o problema que a arquitetura de 18/09 resolveu. A cura é
fonte de 9px abaixo de 360px.

> **O detector:** clonar a barra com as classes reais e comparar
> `rotulo.scrollWidth` com `getBoundingClientRect().width`. Um rótulo cortado
> não estoura nada e não quebra linha — as duas coisas que uma auditoria de
> layout normalmente procura.
>
> E **emule o viewport de verdade**: um clone de 320px dentro de uma janela de
> 375px não dispara a media query de 320px. Passar `preset` junto de
> `width`/`height` no `resize_window` faz o preset vencer.

## Como verificar

**Funcionalmente**, em produção, não lendo classe: `elementFromPoint`,
`getBoundingClientRect`. Cuidado — **`getBoundingClientRect` não enxerga área de
`::before`**, então ele não valida o item 3.

O detector que acha o defeito 4 de uma vez, rodado no navegador a 375px:

```js
// para cada elemento-folha com 40+ caracteres, acusar:
width < 150 && height / lineHeight > 3
```

No celular a coluna da prática sobe (`order`) em `/estudar`, e o trilho de progresso
do curso vira faixa no topo.

---
Relacionado: [[navegacao]] · [[sistema-visual]] · [[padroes-de-tela]] · [[ambiente-local]]
