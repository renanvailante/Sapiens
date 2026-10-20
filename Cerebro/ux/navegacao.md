---
tags: [ux, navegacao, layout]
atualizado: 2026-10-19
---

# Navegação — cinco áreas, uma lista

> [!warning] Esta é a área que mais mudou de opinião no produto
> Entre 09/09 e 18/09 a barra foi reorganizada **seis vezes**, e três dessas
> passadas desfizeram a anterior sem saber. Antes de propor mudança aqui, leia
> [[superado]] — o que já foi tentado e descartado.

## A arquitetura vigente (2026-09-18)

**Cinco áreas, idênticas no desktop e no celular.** Cada uma é uma PERGUNTA do
aluno, não um módulo do produto:

| Área | Pergunta | Rota |
|---|---|---|
| Hoje | e agora? | `/hoje` |
| Agenda | quando? | `/agenda` |
| **Estudar** | o que eu vou fazer? | `/estudar` |
| Progresso | estou evoluindo? | `/progresso` |
| Comunidade | quem me responde? | `/comunidade` |

Tudo mora em `aluno/frontend/src/lib/navegacao.js` (`AREAS`, `NOMES`, `MENU`) e
é desenhado por `components/Navegacao.jsx`, montado **uma vez** no `App.js`.

## O trilho do desktop (2026-10-19)

No desktop (`lg+`) a navegação é uma **coluna fixa à esquerda** — o trilho —, como
nos prints do Duolingo que o dono mandou: marca no topo, as cinco áreas com ícone
grande colorido e nome em maiúsculas, e no pé o saldo de Sparks e "Mais" (o
Menu). Substituiu a barra de cima. A composição e a ordem das áreas **não
mudaram** — só o desenho.

- 1024–1279px: 88px, só ícones (o nome vem no balão `nav-tip`, à direita).
  1280px+: 248px, ícone + nome. Um token só: `--trilho-w`.
- O conteúdo anda para a direita por `html[data-trilho] .App { padding-left }`;
  quem liga o atributo é o próprio `Trilho`, enquanto montado. Rota sem
  navegação (`temNavegacao`) não monta o trilho, então não ganha o recuo.
- **Tela cheia `fixed inset-0` não anda com o padding** (é medida contra a
  janela). O mapa 3D do Treino leva `.tela-cheia-com-trilho`, que começa depois
  do trilho; sem ela o trilho cobria a borda do mapa e o painel de missões.
  Tela cheia nova com navegação precisa da mesma classe.
- Peças que se alinhavam à barra de cima (`top-16`) ficaram com `lg:top-*`
  próprio — no desktop não existe mais barra de 64px no topo.

**Cada área tem cor** (`AREAS[].cor`): é a única exceção à regra "cor é
significado" — na navegação a cor é ENDEREÇO, o olho acha a área antes de ler.
Estudar é ciano porque é a ação. `navegacao.test.js` trava que as cinco cores
sejam distintas.

### O que isso substituiu

Havia **cinco sistemas de navegação simultâneos**, cada um com uma lista
diferente dos mesmos destinos: `PRIMARY_LINKS` (7 abas no desktop), `ABAS` da
`BarraInferior` (4 + Menu, outro conjunto), `ATALHOS` (8 pílulas só no
celular), `GRUPOS` do `LancadorDeFerramentas` (16 linhas) e `PortaisDaJornada`
(10 portas com OUTROS nomes). Os quatro primeiros foram apagados.

O comentário do `Nav.jsx` afirmava que as duas barras desenhavam "o MESMO
conjunto primário". **Não desenhavam** — Redação, Aulas e Mentis eram abas no
desktop e não existiam na barra do celular.

## As regras que governam o conjunto

**Área é PERGUNTA, não pódio.** Redação é o que mais vale ponto no ENEM e não é
área: ela responde "o que eu vou fazer", igual a resolver prova e ler curso.
Importância não é categoria navegacional.

**Estudar é o TERCEIRO de cinco, e isso é do polegar.** Ele é o alvo elevado da
barra do celular (`.aba-acao`, 22px acima das vizinhas) e precisa do meio
geométrico. Também preserva a posição que ele já ocupava: a barra era
`Painel · Semana · [Estudar] · Desempenho · Mais`, então o único alvo que mudou
de identidade foi o quinto — "Mais" virou Comunidade.

**Mentis não é aba.** Ela flutua em toda tela (`MentisWidget`) e `/mentis` é a
MESMA sessão em tela cheia. Uma aba para ela era a mesma porta duas vezes.

**Âmbar deixou de existir na barra.** A aula ao vivo era aba permanente em
âmbar para um evento de 60 minutos por semana — chamando atenção nos outros
seis dias sem ter o que dizer. Ela virou **evento datado** na Agenda e linha do
Menu. Ver [[decisoes-do-dono]], que registrava âmbar como recurso de uso único.

## A regra que define o Menu

> **O Menu não pode conter nada que o aluno precise para aprender a usar o
> produto.** Quem nunca o abrir não perde ferramenta pedagógica nenhuma.

`navegacao.test.js` trava isso. É essa regra que tornou seguro o Menu sair do
quinto alvo do polegar e subir para o canto da marca (que já o abria no desktop
desde 17/09), liberando aquele alvo para uma área de verdade.

Hoje o Menu guarda três grupos: **Com Vitor Lara** (aula ao vivo, mentoria),
**Minha conta** (Sparks, Mentis em tela cheia, falar com a equipe) e
**Sistema** (guia, instalar, admin, sair).

> O agrupamento antigo ("Estudar / Meu progresso / Com o 1º colocado / Quem te
> responde") estava certo **para uma gaveta que guardava metade do produto**.
> Esvaziá-la é o que resolveu o problema; reagrupar não resolvia.

## Um conceito, um nome

`lib/navegacao.NOMES` é o vocabulário único, e **toda superfície que nomeia um
destino lê de lá**: abas, portas do Hoje, chips da Mentis, Menu.

Antes disso, `/exams` tinha quatro nomes ao mesmo tempo ("Praticar" na porta,
"Estudar" na barra, `barra-praticar` no testid, "Provas do ENEM" no Menu) e
`/progresso` tinha três. Não é inconsistência de copy — é de **aprendizado**: o
aluno precisa ficar bom no Sapiens, não bom em decorar que quatro palavras
apontam para a mesma tela.

## O orçamento de largura (aposentado em 2026-10-19)

A barra de cima vivia em 1072px úteis e estourou duas vezes (sete primários deram
52px de folga; com cinco, 133px a 1024). O trilho empilha as áreas na vertical e
a conta deixou de existir. **O teto de cinco áreas continua**, agora pelo motivo
que sobrou: a barra do celular tem cinco alvos de polegar com o do meio elevado —
uma sexta não cabe sem encolher todos os rótulos. `lib/navegacao.test.js` trava
a contagem.

## A barra inferior do celular

Cinco alvos, e agora os cinco são **áreas** (antes eram quatro áreas + a
gaveta). O do meio é elevado e é o único objeto aceso — a navegação do telefone
responde "o que eu faço agora", não só "para onde eu vou". Os ícones levam a cor
de endereço de cada área, igual ao trilho.

Some em `/estudar/folhear`, `/bem-vindo`, `/completar-cadastro` e
`/estudar/provas/:id` — esta última porque é a única tela do produto com
**estado não salvo** dentro. A regra é uma só (`temNavegacao`), lida pelas duas
barras; antes eram duas listas que já divergiam (`/exam` numa, `/exam/` noutra).

> **`--barra-inferior-h` (4.25rem) em `index.css` é usado por TRÊS coisas:** a
> barra, o `padding-bottom` do `body` no celular e `.flutuante-mentis`.

**A 320px o rótulo mais longo era cortado.** "Comunidade" (10 caracteres)
substituiu "Painel" (6) como maior rótulo, e o `text-overflow: ellipsis` o
cortava em silêncio — sem estouro horizontal e sem quebra de linha, então nada
acusava. A cura é `@media (max-width: 359px)` no bloco de celular, com `:root`
na frente (ver [[mobile]] para por que a especificidade importa ali).

## Rotas: a fonte única

`lib/rotas.js` (frontend) e `rotas_do_app.py` (backend) são a tabela de rotas,
e `test_rotas_do_app.py` compara os dois arquivos.

**Ninguém escreve `"/..."` à mão.** O preço disso já foi pago sem ninguém ver:
`mentis_routes.DESTINOS` apontou para `/cognitive-profile` e `/cursos#live`
durante meses depois da renomeação, e não quebrou porque havia redirect — o
defeito ficou invisível **por existir uma rede de segurança**.

**`normalizar` preserva query e hash, e isso é dinheiro.** A chave de
idempotência do lembrete é `sha256(texto + rota)`: sem normalizar, o aluno que
guardou um trecho em `/redacao` pagaria os 10 Sparks de novo pelo mesmo trecho
em `/estudar/redacao`. Ver [[dados]].

E `/exams?area=Matemática` sem a query entrega um caderno genérico onde o aluno
pediu a questão que errou — falha silenciosa.

## Tooltip da barra

`.nav-tip` + `data-tip="X"` no `index.css` — CSS puro, sem JS. O `data-tip`
carrega a **pergunta** da área ("E agora?"). No trilho o balão nasce à direita
do ícone — é o que dá nome às áreas na faixa de 1024–1279px, em que o trilho só
mostra ícones.

> **Armadilha ao verificar no Browser pane:** `computer{action:"hover"}` espera
> coordenadas no frame do **último screenshot**, não em pixel CSS do viewport.

---
Relacionado: [[padroes-de-tela]] · [[mobile]] · [[superado]] · [[ambiente-local]]
