---
tags: [ux, css, design]
atualizado: 2026-10-19
---

# Sistema visual — bioluminescência tecnológica

Abismo azul-quase-preto, painéis de vidro, luz ciano→azul→violeta. Três regras no
cabeçalho de `aluno/frontend/src/index.css`: **luz é informação; uma família de
matiz; borda fina + sombra longa**.

## A camada de tradução — a coisa mais importante deste nó

`index.css` tem, no fim, uma **camada que traduz utilitários claros do Tailwind**
para o equivalente escuro: `:root .bg-white`, `:root .text-zinc-900`,
`:root .bg-rose-50`… (especificidade 0,2,0 — vence o Tailwind sem `!important`). As
telas continuam escritas com Tailwind claro normal.

> [!danger] Não saia trocando `bg-white` por `bg-slate-900` tela a tela.
> Se uma cor está errada no escuro, **o conserto é uma linha nessa camada**.

### A camada NÃO traduz variantes `hover:`

Os seletores são `:root .text-zinc-600`, não `:root .hover\:text-zinc-600:hover`.
Então `hover:text-zinc-900` sobre superfície escura pinta o texto de `#18181B` e ele
**some no hover**; `hover:bg-zinc-50` clareia o fundo para branco.

Não aparece em revisão de código nem em screenshot parado: **só passando o mouse**.
O idiom seguro no escuro é `text-white/70 hover:text-white`, `hover:bg-white/10` ou
`hover:underline`. **Trate `hover:` como território não traduzido.**

## `.leitura-clara` e a armadilha da mesma tag

A única superfície clara que sobrou é `.leitura-clara` (enunciado + alternativas),
escolha do dono: prova de 45 questões em vidro escuro cansa. Dentro dela a camada é
**revertida** (mesmos seletores, declarados depois). **Toda cor nova precisa das
duas entradas.**

> [!warning] A reversão é escrita como DESCENDENTE
> Quando as duas classes estão no **mesmo elemento** — que é exatamente como os
> blocos de conteúdo de curso são escritos,
> `<section className="leitura-clara … text-zinc-800">` — o seletor descendente não
> casa, sobra o `:root`, e o resultado é **texto claro sobre papel branco**:
> ilegível.
>
> Garanta a forma **sem espaço** (`.leitura-clara.text-zinc-800`) além da
> descendente. As duas formas já existem para `text-zinc-400..950`,
> `text-amber/emerald/rose/sky-900` e os selos de recompensa.

### A volta cobria só metade da camada (achado em 2026-10-10)

Das 81 classes com `:root .x`, **44 não tinham `.leitura-clara .x`** — e cada
uma delas pinta ESCURO dentro da folha clara. O caso que o dono viu: o card da
Intervenção da Mentis (`bg-white/70`) recebia o vidro escuro de 50% por cima
do rosa do veredito, e o texto cinza ficava sobre cinza, justamente depois de
um erro. As caixas `bg-sky-50` da mesma tela também pintavam escuro.

Todas ganharam a volta, com a cor **original** do Tailwind. A conferência é um
script, não leitura: liste os seletores `:root (\.[\w\\/-]+)` e os
`.leitura-clara ?(\.[\w\\/-]+)` do `index.css` e compare. O que sobra na
diferença hoje (`text-white/*`, `aba-*`) não é da camada de tradução.

Achado em 17/09 com o curso já no ar: **o conteúdo inteiro de Matemática Básica
estava invisível**, e nenhum teste pega isso — o projeto não tem teste de
componente. Confira com `getComputedStyle`, não no código.

## Nada entre `html` e o conteúdo pode ter fundo opaco

As auroras, a malha e a vinheta (`body::before` / `body::after`, `z-index` -2 e -1)
existiam desde 03/09 e **o produto inteiro rodou sobre preto chapado até 16/09** —
nenhum aluno viu o ambiente que o sistema descreve.

Causa: a ordem de pintura do contexto de empilhamento raiz (CSS 2.1, apêndice E) é
`html` → **descendentes com z-index negativo** → **fundo dos descendentes em fluxo
normal** → conteúdo. Ou seja, o `background-color` do `body` (e do `#root`) é
pintado **depois** de um filho com `z-index: -2`, e o apaga.

Correção: a cor do abismo vive **só no `html`**. Não há lampejo branco, porque a cor
do elemento raiz é a cor da tela desde o primeiro quadro.

> **Regra:** tela que precisa de fundo próprio pinta a **própria superfície**
> (`.card-sapiens`, `.superficie`), nunca o `body` nem o `#root`.
> **Sintoma de regressão:** a página fica preta e lisa, sem brilho nos cantos.

## `.shimmer` apaga letra em tamanho de display

Medido em 2026-09-15: o gradiente animado sobre `background-clip: text` comeu a
barriga do "P" em "**USP**" a 60px no Chrome — a palavra lia "USF" em quase todo
quadro. Comprovado por eliminação.

> **Não use `.shimmer` em palavra curta que PRECISA ser lida** (sigla, nome,
> número). Ele foi feito para "Sapiens" no herói, onde errar uma letra não muda nada.

## Comemoração: revisto em 2026-10-08

Até essa data o arquivo dizia "não é confete" e tratava `.premio-pop` como a única
animação que celebrava algo. O dono pediu o oposto (Duolingo, muito mais
animação), e a camada "DUOLINGO" no fim do `index.css` existe por isso. O que
**sobreviveu** da regra antiga, e não deve cair:

- **nada bloqueia** — o confete é um canvas com `pointer-events: none` que se
  remove sozinho; o botão de seguir é clicável no meio da chuva;
- **o acerto que o aluno marcou salta, a certa revelada depois de um erro só
  acende** (`data-escolhida`) — comemorar ali seria falso;
- **questão que já chega respondida não anima** (`data-anima`, decidido na
  montagem de `Alternativas`) — dez cartões tremendo ao reabrir não dizem nada;
- "Sapiens Plus" usa degradê **parado** (`.texto-plus`), não `.shimmer`;
- `prefers-reduced-motion` desliga tudo no fim do bloco.

## O cartão gordo (2026-10-10)

`.cartao-gordo` é a peça do catálogo do Estudar (cadernos, cursos, e-books,
modos): borda de 2px, **pé sólido de 5px** que afunda no toque, cor da matéria
por variável (`--de`, `--para`, `--pe`, `--tinta`). Ver [[padroes-de-tela]].

> [!warning] Esta folha vem DEPOIS de `@tailwind utilities`
> Utilitário do Tailwind que conflita com uma classe própria **perde**:
> `flex-row` ao lado de `.cartao-gordo` (que é coluna) não pega, e `text-lg`
> ao lado de `.cartao-gordo-titulo` também não. Por isso existem os
> modificadores `--deitado`, `--modo`, `-titulo--p` e `-titulo--g`. Não
> "conserte" acrescentando utilitário: ele não vai pintar.

## As primitivas (camada "PRODUTO", no fim do arquivo)

Ritmo: `.pagina-entra`, `.cascata`, `.esqueleto`.
Superfície: `.superficie` / `.superficie-viva` (barata, **sem `backdrop-filter`** —
`.card-sapiens` é cara demais para vinte blocos numa rolagem).
Estrutura: `.secao-cabeca` / `.secao-titulo` / `.secao-olho`, `.titulo-tela` /
`.titulo-heroi`.
Peças: `.chip`, `.barra`, `.medida-n`, `.anel-traco`, `.alternativa`, `.veredito`,
`.recompensa` / `.ganho`.
Botões: `.btn-sapiens`, `.btn-vidro`, `.cta-calor`, com o "pé" sólido (`--btn-pe`)
que afunda no `:active`.

`tailwind.config.js`: `sapiens.accent` = `#4FD9FF`, `accentDeep` = `#2E7FD6` — os 38
`border-sapiens-accent` do produto são estados de foco e precisam acender no escuro.

## Cor de gráfico é validada, não escolhida

`components/perfil/paleta.js` (oito séries, rampa ordinal, par divergente) passou por
checagem de daltonismo e contraste contra a superfície `#14203a`. **O ciano da marca
reprova** na faixa de luminosidade — dentro do gráfico entra um passo mais fundo.

> **Cor segue a MATÉRIA, nunca a posição no ranking.**

## Referências visuais e o que cada uma virou

- **Duolingo** → `TrilhaDeMissoes.jsx` / `CaminhoDoCurso.jsx` (caminho serpenteado),
  o pé sólido dos botões e, desde 2026-10-08, a camada de comemoração (chama,
  combo, placar, som) — ver [[engajamento]].
- **Animal Crossing** → `.macio` e nós redondos: peça de interface como **objeto**,
  não retângulo de conteúdo.
- **Khan Academy** → `lib/dominio.js`: o domínio por frente tem **nome**
  (Iniciado/Familiar/Proficiente/Dominado), não só porcentagem.
- **Alura / Descomplica** → grade de ferramentas agrupada, manchete única e grande.

## Como escrever uma tela nova

`<Tela>` + Tailwind normal + `.superficie` / `.card-sapiens` / `.btn-sapiens`.
**Não invente raio, respiro nem tamanho de título.** Só toque em cor crua se for um
matiz que a camada ainda não traduz.

---
Relacionado: [[padroes-de-tela]] · [[mobile]] · [[navegacao]] · [[ambiente-local]]
