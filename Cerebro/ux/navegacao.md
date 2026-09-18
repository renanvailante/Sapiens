---
tags: [ux, navegacao, layout]
atualizado: 2026-09-18
---

# Navegação — e o orçamento de largura

> [!warning] Esta é a área que mais mudou de opinião no produto
> Entre 09/09 e 18/09 a barra foi reorganizada **cinco vezes**, e três dessas
> passadas desfizeram a anterior sem saber. Antes de propor mudança aqui, leia
> [[superado]] — o que já foi tentado e descartado.

## A lista vigente (verificada em `Nav.jsx`)

**Sete primários:** Painel · Redação · Estudar · Semana · Desempenho · Aulas ·
Mentis.

`PRIMARY_LINKS` é uma **lista fixa e nomeada**. O orçamento de largura é **de
projeto** e vive num comentário no fim do arquivo, atualizado a cada item novo.

> A auto-medição (`quantasCabem` + `ResizeObserver`) **existiu e saiu** em 18/09.
> Não a reintroduza sem conversa: ela foi trocada por decisão explícita de projeto.

**Âmbar é recurso de uso único**: só "Aulas", o único destino com hora marcada. Ver
[[decisoes-do-dono]].

## O orçamento: 1152px que nenhum monitor aumenta

O container interno é `max-w-6xl`. **Nenhum monitor largo compra espaço ali.**

Medição de 18/09 com sete primários: marca 110 + primários 688 + vão até o Menu 8 +
Menu/Sparks/Sair 214 = **1020px, 52px de folga em 1072px**. Com o padding antigo
(`px-3`, `gap-2`) o sétimo item estourava em ~17px; a pílula encolheu para `px-2.5` /
`gap-1.5`. `lib/atalhos.test.js` trava isso (`MEDIDO_COM_SETE`).

### Como medir — e por que a intuição erra

> **`scrollWidth - clientWidth` dá 0 sempre que cabe** (`justify-between` come a
> sobra). O número que importa é a **soma das larguras dos filhos** contra
> `clientWidth - padding`.

```js
const n = document.querySelector('.glass > div'), cs = getComputedStyle(n);
const soma = [...n.children].reduce((t,c) => t + c.getBoundingClientRect().width, 0);
n.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - soma
```

Rode com usuário **admin** (o pior caso — a pílula de Admin e o chip de promoter
existem) em **1024, 1280 e 1536**. Duas armadilhas: estimar larguras de texto erra
por dezenas de px (**meça no `main.*.css` do `yarn build`**), e as economias `2xl:`
não ajudam em `lg`, onde a barra é mais apertada em espaço útil (944px contra
1072px). Como medir sem login: ver [[ambiente-local]].

## Economias estruturais já aplicadas — mantenha

- A barra desktop começa em `lg` (1024), não em `md`; o menu deslizante cobre
  768–1024.
- Rótulos dos primários só a partir de `xl`. Entre 1024 e 1279 é **ícones puros**, e
  quem diz onde se está é o traço aceso da aba ativa (`.nav-elo[data-ativa]`), que
  antes não existia em largura nenhuma.
- "Sair" é ícone redondo sem rótulo em toda largura; "Admin" sem rótulo.
- "Tenha aulas conosco" → "Aulas"; "Cronograma" → "Semana".

> **Nenhum item novo deve entrar como largura FIXA.** Entre pela lista de atalhos
> (`lib/atalhos.js`), que some sozinha quando não cabe.

## A barra inferior do celular

`components/BarraInferior.jsx`, montada **uma vez** em `App.js` — não por tela. As 52
páginas montam a própria `<Nav/>`, e acrescentar uma linha em cada garantiria que a
próxima nasceria sem barra.

**O buraco que ela fechou:** abaixo de 1024px o app **não tinha navegação nenhuma**.
A barra de cima tinha um botão de menu e mais nada, e a maioria dos alunos entra pelo
celular.

Cinco alvos, e o do meio é **elevado** (`.aba-acao`, `margin-top: -22px`) e é o único
objeto aceso — a navegação também responde "o que eu faço agora". Ele aponta para
`/estudar`. "Mais" abre o mesmo `LancadorDeFerramentas` com `lado="bottom"`.

Some em `/feed`, `/bem-vindo` e `/exam/*` — esta última porque é a única tela do
produto com **estado não salvo** dentro.

> **`--barra-inferior-h` (4.25rem) em `index.css` é usado por TRÊS coisas:** a barra,
> o `padding-bottom` do `body` no celular e `.flutuante-mentis`. O ícone da Mentis
> era `bottom-5` e passou a pousar em cima das abas.

Medido a 320px: cabe com os 5 rótulos, sem estouro horizontal.

## Paridade celular ↔ desktop

A mesma lista de `lib/atalhos.js` vira tira rolável no celular
(`.rolagem-invisivel`, chips de 32px) logo abaixo da barra, escondida nas mesmas
telas em que a barra inferior some.

`atalhos.test.js` compara a tira do celular com a **barra inferior**, não com as abas
do desktop — elas **nunca aparecem juntas** (`lg:flex` × `lg:hidden`). E trava "nada
primário aparece também como miniatura".

## O Menu (cauda longa)

`LancadorDeFerramentas` agrupa **por intenção do aluno**: Estudar / Meu progresso /
Com o 1º colocado / Quem te responde. **Esse agrupamento está certo — não o refaça.**
Comunidade e Liga moram aqui, nunca nos links primários.

## Tooltip da barra

`.nav-tip` + `data-tip="X"` no `index.css` — CSS puro, sem JS, sem componente. O nome
vem de `content: attr(data-tip)` no `::after`. `:hover` e `:focus-visible` disparam a
mesma regra, então quem navega por Tab também vê o nome.

Todo `title="..."` que só repetia o `aria-label` foi **removido** nesses elementos —
o `title` nativo por cima duplicava a legenda. A tira de atalhos do **celular** não
recebeu a classe: ali o nome já aparece escrito ao lado do ícone.

> **Armadilha ao verificar no Browser pane:** `computer{action:"hover"}` espera
> coordenadas no frame do **último screenshot**, não em pixel CSS do viewport. Com
> `devicePixelRatio` 2 e viewport 1024×768, o screenshot sai 800×600. Confirme com
> `document.elementFromPoint(x, y)` ou leia `el.matches(':hover')` depois.

## Rotas que continuam existindo e não devem ser removidas

`/exams` e `/cursos` **não** morreram quando nasceu `/estudar`:

- `/exams` é aberta **com filtro na URL** pelo Painel, pelas Revisões e pela Mentis
  (`?area=`, `?item_ids=`), e é onde o motor de prova roda em tela cheia.
- `/cursos` mantém a vitrine completa, área por área, com a ementa.

`/estudar` compõe as duas em modo `embutido` (prop nova em `Cursos` e `ExamSelect`).
Quando o aluno escolhe um caderno, `ExamSelect` avisa por `onModo` e a página recolhe
a coluna da esquerda — **o `QuestionRunner` não foi tocado**.

---
Relacionado: [[padroes-de-tela]] · [[mobile]] · [[superado]] · [[ambiente-local]]
