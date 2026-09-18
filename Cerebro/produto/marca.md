---
tags: [produto, marca, copy, identidade]
atualizado: 2026-09-18
---

# Marca — narrativa, símbolo e mentor

## StoryBrand é a espinha de TODA a marca

Desde 2026-09-17 a estrutura de *Building a StoryBrand* (Donald Miller) organiza a
marca inteira, não só a landing:

> herói (o vestibulando) → problema (sem teoria individual embasada, sem método;
> vilão = **"estudar no escuro"**) → guia (a Mentis com empatia + autoridade
> bibliográfica, e Vitor Lara com rosto e credencial) → plano em 3 passos → convite
> à ação → fracasso evitado → sucesso (a lista com o nome).

A copy mora em `aluno/frontend/src/lib/historia.js` (`PROBLEMA`, `DOR_INTERNA`,
`EMBASAMENTO`, `PLANO`, `APOSTAS`, `DEPOIMENTOS`, `FAQ`, `VOZ`); `Landing.jsx` só
renderiza na ordem da história.

**Por quê:** a landing antiga abria com três elogios ao produto antes de qualquer
frase sobre a vida de quem lê. Quem chega por link de WhatsApp tem cinco segundos e
está com medo de não passar, não procurando recursos.

> **Seção nova que elogia a plataforma sem dizer o que muda para o aluno está no
> lugar errado.**

Aplicado além da landing: Login, BemVindo, ProximoPasso, SparksStore, Cronograma,
StudyPlan, Redacao, ExamSelect, Indicar, Liga, Cursos, OnboardingTour,
`manifest.json` e os prompts da Mentis. **Faltam: o app do professor e os
e-mails/notificações.**

Três armadilhas de copy:

- O bloco **FAQ é espelhado em JSON-LD** (FAQPage) dentro de `public/index.html` —
  mudou um, muda o outro, ou o rich result cai.
- O `<title>` que o Google mostra vem do `TituloDaPagina` da rota `/` em `App.js`,
  **não** do `index.html` — o buscador renderiza o JS.
- Os **DEPOIMENTOS são paráfrases sem nome, foto ou faculdade**: o dono tem as
  mensagens reais mas não as compilou, e atribuir paráfrase a pessoa identificável
  seria inventar depoimento.

## O símbolo: cérebro de frente com trilhas de circuito

`components/BrandMark.jsx`, em vetor. O pedido foi explícito: *"não redesenhe
arbitrariamente o símbolo"*, só adequar cor e resolução.

Cada hemisfério é a **união de 7 círculos** sobrepostos (`HEMISFERIO`), recortada
por um `clipPath` retangular em x=51.4 / x=48.6 (a fissura, 2.8 unidades num viewBox
de 100). O hemisfério esquerdo é **derivado** (`100 - cx`), nunca escrito à mão.

> **A regra que mantém os lóbulos visíveis:** a distância entre dois centros
> vizinhos tem de ser maior que o maior dos dois raios. Abaixo disso um lóbulo
> engole o outro e a forma vira nuvem.

> [!warning] O degradê PRECISA de `gradientUnits="userSpaceOnUse"`
> Sem isso ele é resolvido na caixa de cada forma, cada círculo ganha a escala de
> cor inteira, e a marca lê como **bolhas de sabão empilhadas**. A correção é pintar
> um `<rect>` do tamanho do viewBox recortado pela união, em vez de dar `fill` a
> cada círculo.

**Mexer na marca = mover um círculo em `HEMISFERIO`, não reescrever curva.** Depois
de qualquer mudança, **regerar os quatro PNGs e o favicon** (via `rsvg-convert`) —
senão a aba do navegador e o ícone do aparelho ficam com a marca antiga. Derivados:
`public/favicon.svg` (arquivo, não data URI — eram 5.5 kB num documento nunca
cacheado), `icon-192.png`, `icon-512.png`, `apple-touch-icon.png`, `og-image.png`.

## O lockup

`components/Logo.jsx` = símbolo + a palavra "Sapiens", sempre nesta ordem e com a
mesma relação. Antes, `Nav`, `Login`, `Landing` e o lançador montavam cada um a sua
combinação — **quatro lockups da mesma marca em telas que o aluno vê em sequência no
primeiro minuto**.

Três degraus: `p` (barra do celular), `m` (barra do desktop), `g` (protagonista — e
só em `g` o halo acende). Fica no canto superior esquerdo em **toda** largura,
inclusive no celular, por pedido explícito. Até 16/09, abaixo de 1024px **a marca não
existia**: aquele canto era o botão de menu.

> **Nunca escreva `<BrandMark/> Sapiens` à mão numa tela nova — use `<Logo/>`.** A
> responsividade da palavra é passada de fora (`classePalavra`), porque esconder a
> palavra é decisão de layout da barra, não da marca.

## O mentor: Vitor Lara

Aprovado em **1º lugar em Medicina na USP**. Uma pessoa só nos três produtos: grava
os cursos, dá a aula ao vivo e atende a mentoria. O nome passou a ser **dito** em
2026-09-17; até então o produto inteiro dizia "o 1º colocado de Medicina da USP".

Os dados moram em `lib/mentor.js` (`MENTOR`) — constante de módulo, não chamada de
API, porque isto é **copy** e aparece na landing, onde não há sessão. O backend tem
a própria cópia em `cursos.LIVE_APRESENTADOR`, e as duas mudam juntas.

> **Ao escrever qualquer texto que cite o mentor, use `MENTOR.nome`** em vez de
> digitar. Foi o que permitiu trocar a perífrase pelo nome em oito telas de uma vez.
> E ele é sempre "Vitor Lara", nunca "o Vitor" — ver [[decisoes-do-dono]].

### O vídeo de apresentação

`components/VideoDoMentor.jsx` é uma **fachada**: mostra a thumbnail e só monta o
`<iframe>` no clique — privacidade (a tela fala com menor de idade), peso (~1 MB de
JS de terceiro) e layout (o espaço 16:9 já nasce reservado). Usa
`youtube-nocookie.com`.

Duas armadilhas já pagas:

- **`maxresdefault.jpg` não existe para todo vídeo**, e quando falta o YouTube
  devolve uma imagem cinza de 120px **em vez de 404** — `onError` nunca dispara. A
  detecção é por `naturalWidth < 400` no `onLoad`, caindo para `hqdefault`.
- **O navegador embutido do Claude bloqueia `youtube-nocookie.com`**, então o player
  aparece preto ali. Não é bug: verifique o `src`, não a imagem.

### A foto

`public/mentor-usp.jpg`, recorte quadrado 900x900. Arquivo ausente cai na medalha de
propósito (fallback, não bug), e o selo "1º lugar em Medicina na USP" aparece
**também** quando a foto falta — antes o produto perdia foto e credencial juntas.

> **A foto original chega ESPELHADA** (a camisa lê "ANICIDEM"). Sempre inverter
> antes de salvar: `sips --flip horizontal <origem> --out <destino>`, depois cortar
> com `sips -c <alt> <alt> --cropOffset <deslocY> 0` (offset positivo desloca para
> cima/rosto; o `sips --help` documenta mal isso — testar visualmente).

---
Relacionado: [[mentis]] · [[catalogo]] · [[sistema-visual]] · [[decisoes-do-dono]]
