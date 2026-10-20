---
tags: [ux, css, design]
atualizado: 2026-10-19
---

# Sistema visual — Clareza

Desde 2026-10-19. Página azul-tinta **chapada**, cartões sólidos com contorno de
2px, botões com **pé** sólido, uma família tipográfica (**Nunito**). Substituiu a
"bioluminescência tecnológica" (vidro, auroras, brilho ciano→violeta) — ver
[[superado]]. As quatro regras estão no cabeçalho de `aluno/frontend/src/index.css`:
**chapado; uma ação acesa por tela; cor é significado; tipografia gorda e curta**.

**Por quê:** pedido do dono com prints do Duolingo — *"o site está muito poluído
e pouco intuitivo (…) o Duolingo tem poucos botões e é tudo muito fácil de
mexer"*, sem copiar a identidade dele. Do Duolingo vieram princípios **medidos no
CSS público** (botão de 50px, pé de 4px, raio 12–16px, contorno de 2px, rótulo em
maiúsculas 700 com 0.04em, título de página ~32px). A fonte dele (Feather / DIN
Rounded) é proprietária e **não** entrou; nem o verde, nem a coruja.

## Os tokens — o que mudar e onde

Os nomes `--bio-*` ficaram (as telas leem `var(--bio-texto)` direto); os
**valores** são da Clareza. Mudar a paleta é mudar o `:root` do `index.css`, não
as telas.

- Contraste medido (página `#0F1A2C` / cartão `#15233A`): texto 16.1/14.6,
  suave 11.1/10.0, fraco 7.4/6.7, apagado 5.3/4.8. **Nenhum degrau de texto abaixo
  de 4.5:1** — confira com script antes de escurecer um.
- **Contorno ~2:1, e não 3:1.** A régua antiga pedia 3:1 porque a linha tinha 1px
  sobre vidro translúcido. Com 2px sobre cartão sólido (que já se separa da página
  pela cor) a borda aparece no sol sem pesar — o Duolingo usa 1.7:1.
- **Cor com significado:** ciano = ação, verde = feito/acerto, coral = erro,
  âmbar = Sparks/ofensiva, violeta = Plus. A exceção é a navegação, onde cada área
  tem uma cor de **endereço** (ver [[navegacao]]).

## Armadilhas da folha (ela vem DEPOIS de `@tailwind utilities`)

- **Classe própria com `font-weight` vence o `font-bold` da tela.** Por isso
  `.font-display` não tem peso — a tela decide. Mesma razão do aviso do cartão
  gordo abaixo.
- Os botões (`.btn-sapiens`, `.btn-vidro`, `.btn-contorno`, `.btn-calor`) têm raio
  de 14px por `:root .btn-*` (0,2,0), que **vence o `rounded-full`** escrito nas
  telas. Não "conserte" o botão pílula acrescentando utilitário.
- Pé de botão e `scale` no `:active` não se somam: `.pill` só encolhe o que não tem
  pé.
- Rótulo em maiúsculas com `tracking-[0.22em]` era assinatura da IBM Plex Mono; a
  camada "CLAREZA" no fim do arquivo apara para 0.06em e sobe 10px para 11px.
- **Animação que carrega o `transform` de posição:** `.no-dia-chamada` só ficava
  centrada pelo keyframe; com movimento reduzido caía meia largura para o lado. O
  centro mora na regra.

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

## A cor da página mora no `html`

O elemento raiz é pintado desde o primeiro quadro: sem lampejo branco antes do
React montar. Tela que precisa de fundo próprio pinta a **própria superfície**
(`.card-sapiens`, `.superficie`), nunca o `body` nem o `#root` — a regra nasceu
das auroras (ver [[superado]]) e continua sendo o jeito certo.

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
modos): cartão sólido, contorno de 2px com um toque da cor da matéria, **pé
sólido de 5px** que afunda no toque. A cor da matéria (`--de`, `--pe`, `--tinta`)
fica no ícone, na barra e na ação — não no fundo. Ver [[padroes-de-tela]].

> [!warning] Esta folha vem DEPOIS de `@tailwind utilities`
> Utilitário do Tailwind que conflita com uma classe própria **perde**:
> `flex-row` ao lado de `.cartao-gordo` (que é coluna) não pega, e `text-lg`
> ao lado de `.cartao-gordo-titulo` também não. Por isso existem os
> modificadores `--deitado`, `--modo`, `-titulo--p` e `-titulo--g`. Não
> "conserte" acrescentando utilitário: ele não vai pintar.

## As primitivas (camada "PRODUTO", no fim do arquivo)

Ritmo: `.pagina-entra`, `.cascata`, `.esqueleto`.
Superfície: `.card-sapiens`, `.superficie` / `.superficie-viva` — as três são
sólidas com contorno de 2px. **Não existe mais `backdrop-filter` no produto**: a
camada final zera `backdrop-blur-*` das telas.
Estrutura: `.secao-cabeca` / `.secao-titulo` / `.secao-olho`, `.titulo-tela` /
`.titulo-heroi`.
Peças: `.chip`, `.barra`, `.medida-n`, `.anel-traco`, `.alternativa`, `.veredito`,
`.recompensa` / `.ganho`.
Botões: `.btn-sapiens` (cheio, pé de 4px), `.btn-vidro` e `.btn-contorno`
(contorno, pé de 2px), `.btn-calor`; `.btn-grande` para a ação única da tela
("COMEÇAR" + subtítulo). Trilho e barra do celular: `.trilho*`, `.aba-*`.

`tailwind.config.js`: `sapiens.accent` = `#4FD9FF`, `accentDeep` = `#2E7FD6` — os 38
`border-sapiens-accent` do produto são estados de foco e precisam acender no escuro.

## Cor de gráfico é validada, não escolhida

`components/perfil/paleta.js` (oito séries, rampa ordinal, par divergente) passou por
checagem de daltonismo e contraste contra a superfície `#14203a`. **O ciano da marca
reprova** na faixa de luminosidade — dentro do gráfico entra um passo mais fundo.

> **Cor segue a MATÉRIA, nunca a posição no ranking.**

## Referências visuais e o que cada uma virou

- **Duolingo** → desde 2026-10-19, o sistema inteiro (Clareza) e o trilho
  lateral; antes disso já eram dele o caminho serpenteado
  (`TrilhaDeMissoes.jsx` / `CaminhoDoCurso.jsx`), o pé dos botões e a camada de
  comemoração (chama, combo, placar, som) — ver [[engajamento]].
- **Animal Crossing** → `.macio` e nós redondos: peça de interface como **objeto**,
  não retângulo de conteúdo.
- **Khan Academy** → `lib/dominio.js`: o domínio por frente tem **nome**
  (Iniciado/Familiar/Proficiente/Dominado), não só porcentagem.
- **Alura / Descomplica** → grade de ferramentas agrupada, manchete única e grande.

## Como escrever uma tela nova

`<Tela>` + Tailwind normal + `.superficie` / `.card-sapiens` / `.btn-sapiens`.
**Não invente raio, respiro nem tamanho de título.** Só toque em cor crua se for um
matiz que a camada ainda não traduz. O mais importante da tela vai **em cima**, e
só UMA coisa é ciano cheio.

---
Relacionado: [[padroes-de-tela]] · [[mobile]] · [[navegacao]] · [[ambiente-local]]
