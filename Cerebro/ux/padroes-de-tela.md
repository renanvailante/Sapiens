---
tags: [ux, padroes, componentes]
atualizado: 2026-10-20
---

# Padrões de tela

O que já é sistema. Se você está prestes a desenhar algo desta lista à mão, pare.

## A casca: `Tela.jsx`

Container + cabeçalho. Nasceu porque havia **4 larguras, 3 respiros e 2 tamanhos
de título** espalhados. Aceita `voltar`/`voltarLabel`.

> **A barra saiu daqui em 18/09.** `Tela` montava `<Nav/>` e as outras 38
> páginas montavam a delas à mão — era a razão estrutural de o produto ter
> quatro sistemas de navegação. Hoje `Tela` é só a moldura do conteúdo.

## Uma seção de área: `SecaoDaAba.jsx`

As cinco áreas absorveram onze telas, cada uma com o seu cabeçalho. Empilhá-los
como vieram reproduziria dentro de uma aba a mesma colcha de retalhos que a
arquitetura nova existe para acabar. `SecaoDaAba` dá olho, título, explicação e
**a âncora**.

> A âncora não é decoração: `/conquistas` redireciona para
> `/progresso#conquistas`, e um redirect que despeja a pessoa no topo de uma aba
> de cinco seções é o mesmo que não ter redirecionado. Quem executa o salto é
> `useAncora` — numa SPA o navegador não rola sozinho, porque o elemento com
> aquele `id` ainda não existe quando a URL muda.

## O que é global e mora no `App.js`

Montado uma vez, ao lado das rotas — **tela nova não precisa fazer nada**:

- `Navegacao` — as duas barras e o Menu (ver [[navegacao]])
- `LembrarComAMentis` — a captura global de trecho (ver [[mentis]])
- `MentisWidget` — a Mentis flutuante: guia, próximo passo e chat
- `ContinuidadeDaPagina` — a pista de continuidade
- `FronteiraDeErro` — o `ErrorBoundary` com `chave={pathname}`. Ele é UM em
  volta de todas as rotas, e até 2026-10-09 uma tela que quebrava deixava
  "Algo quebrou" em **todas as seguintes**: o aluno tocava nas abas e a
  navegação parecia morta até recarregar. Trocar de rota desfaz o erro.

## A camada de continuidade

`ContinuidadeDaPagina` publica `--pagina-restante` (0 a 1) na raiz do documento; o
CSS usa esse número como opacidade do véu do pé (`.veu-continua`). O **fecho**
(`.fim-da-pagina`, um traço só — a única peça autorizada a parecer um fim) é montado
por estado do React em página que rola mais de 200px.

> **O teto do véu é 0.58, e não 1.** A 0.88 ele apagava o par de botões do herói da
> Landing, que cai nos últimos 60px da dobra.

A matemática é pura e testada (`forcaDaPista`, `ondeContinua` em
`components/continuidade.test.js`) **porque regra que só se confere abrindo o
navegador não se confere.**

**Fileiras roláveis:** `TiraRolavel` / `useCortesDaRolagem` é o mesmo defeito
deitado — máscara que mostra o próximo card cortado e **sai quando a fileira
acaba**. `.corta-rolagem` é só a máscara (para grades e tabelas, que não sobrevivem
a `display:flex`); `.tira-rolavel` é a fileira.

> **Ao criar uma página nova, não desenhe pista de continuidade — ela já vem.**

## Responder questão tem UMA gramática

`components/questao/`: `Alternativas.jsx` (estado como **dado** em `data-estado`;
quem pinta é o CSS `.alternativa[data-estado]`) e `Veredito.jsx` (selo de 34px,
`.recompensa` só no acerto). Usam: `ExamSelect` (QuestionRunner), `TreinoHabilidades`
(Missao), `MinhasQuestoes` (CartaoQuestao). O teclado A–E vale em todas.

**Por quê:** o aluno toca essa interface ~45 vezes numa sessão. Provas e cursos
usavam `.alternativa`; treino e questões geradas montavam Tailwind na mão, com outro
verde, outro vermelho e outra letra. Isso não é inconsistência de estilo, é **de
aprendizado** — o aluno deve ficar bom no Sapiens, não bom em cinco telas do Sapiens.

> **Nunca desenhe alternativa nova à mão; importe `Alternativas`.**

O gabarito tem **dois formatos** no backend (`correta` string nas provas, `gabarito`
lista no treino) e `letrasCorretas()` é o único lugar que os reconcilia. **Nunca
afirme que uma letra é a correta sem saber** — ver [[inviolaveis]].

Não migrados de propósito: `Feed.jsx` e `components/curso/Blocos.jsx` (já usava o CSS
certo).

## O Hoje é a TRILHA DO DIA (2026-10-09)

Pedido do dono: *"tenho dificuldade de saber o que fazer, onde tenho que clicar.
Parece que eu tenho que aprender a usar a plataforma antes de realmente estudar
nela"* — Duolingo como referência total. O Hoje anterior já tinha "uma pergunta
por dobra" e mesmo assim abria com o Próximo Passo **e três botões ao lado**
(passo, mapa, provas), a trilha do mapa como segunda porta e as missões numa
grade lá embaixo: ~15 alvos na primeira rolagem, cada um certo sozinho.

Agora, de cima para baixo: **placar** (chama · nível · liga, `caminho/HudDoDia`)
→ **a Mentis falando** com UM botão grande (`caminho/BalaoDaMentis`) →
**a trilha** (`caminho/TrilhaDoDia`) → desafio do Plus → O que mudou → Seu
ritmo (o `PainelDeProgresso` com `semMissoes`) → mentor → Explorar.
`ExplorarOSapiens.test.js` trava essa ordem.

**A regra é pura e testada** (`lib/trilhaDoDia.js`, `montarTrilhaDoDia`):

    revisão vencida → blocos de hoje (até 3, pelo horário) → as 3 missões do
    dia → troféu → (dia completo) lição extra

- **Um nó aceso, sempre**: o primeiro prêmio pronto (baú dourado, abre no
  próprio nó) e, sem prêmio, o primeiro pendente. Os outros pendentes ficam
  tocáveis e quietos. Trilha vazia não existe — sem engajamento, o passo do
  motor vira o único nó.
- **Feito é o que o servidor contou** (contador da missão, `concluido` do
  bloco). A trilha anda sozinha porque o servidor conta, não porque a tela acha.
- **As missões de revisão e de cronograma se fundem** ao nó da coisa em si.
  Missão de revisão sem nada vencido vira `espera` (não acende, não conta no
  "N de M").
- **A revisão feita hoje não some.** Revisar esvazia a fila, e o nó sumiria
  justo quando devia ficar dourado. A trilha vista é gravada por aparelho e
  por dia (`gravarTrilhaVista`, com `presentes`); revisão presente antes e fila
  vazia agora = revisada. Só vale no mesmo dia.
- **Destino sem escolha no meio**: revisão abre direto `?item_ids=` das que
  voltaram; prática vai à prática dirigida do padrão (`escolherPasso` continua
  sendo a escada — ela virou o DESTINO das missões de prática e da lição
  extra) ou a `?area=` (a mais fraca do último gabarito, senão Matemática).
  **Nunca a lista de cadernos** — um nó da trilha não pede escolha.

**A volta é o Duolingo.** O fim de série (`FechamentoDaSerie`) e o desfecho de
missão do Treino têm **uma** saída grande, "Continuar a trilha" (eram até cinco
botões do mesmo peso); as outras ficam menores embaixo. De volta ao Hoje,
`novidadesDaTrilha` compara com a última visita DE HOJE: o nó cumprido salta,
solta confete, toca o som e a Mentis fica feliz ("Mais um passo feito: «X»").
Na primeira visita do dia nada é anunciado — seria comemorar o que não
aconteceu agora.

**O nó aceso é publicado para o resto do app** (`publicarPassoAtual`, do
aparelho, do dia): a Mentis flutuante e o "Na dúvida, siga a trilha" do
Estudar levam a ele **sem requisição nenhuma**. Sem passo publicado hoje, o
próximo passo é abrir o Hoje.

> **Armadilha de empilhamento:** cada filho de `.cascata` vira contexto de
> empilhamento durante a entrada, e a seção seguinte pintava POR CIMA do cartão
> aberto de um nó. A seção da trilha tem `relative z-20` por isso.

`components/OQueMudou.jsx` mostra **eventos**, não resumos: um resumo ("você
tem 12 blocos na semana") existe sempre e por isso não chama atenção; um
evento ("sua redação foi corrigida") só existe quando aconteceu. **Zero
requisição própria**, teto de quatro linhas, e nada genérico (toda linha cita
um número do próprio aluno).

A **microvitória** é o terceiro evento, antes das pendências (o teto a
cortaria no fim): o marco mais recente de `reteste_ok` ou `transferencia` da
trajetória (`/revisao/trajetoria`, uma leitura O(1) que o Hoje carrega), em
até 3 dias. Os dois marcos só nascem de acerto, e a frase descreve sem alegar
causa — `nexo_causal` é falso enquanto o portão de crença estiver desligado.
O catálogo de conquistas chama o nome de `label`; ler `nome || titulo` saiu
"Você desbloqueou "undefined"" em produção até 2026-09-30.

As 10 Portas (`PortaisDaJornada.jsx`) moram na seção **Explorar**
(`ExplorarOSapiens.jsx`), **fechada para todo mundo** desde 2026-10-20 — antes
abria sozinha para quem nunca tinha respondido nada e punha dez portas "NOVO"
embaixo do único botão que importava no dia 1. A seção do mentor (mentoria e
aula ao vivo) só aparece depois da primeira resposta. Medido no Hoje da conta
nova: 31 → 20 alvos, 4,4 → 2,5 telas de celular. A preferência do aluno vence e
mora em `localStorage`.

### A escada do Próximo Passo (ainda viva, agora como destino)

`escolherPasso` (em `ProximoPasso.jsx`, testada em `ProximoPasso.test.js`) não
desenha mais a primeira dobra, mas é ela que escolhe para onde vão a prática e
a lição extra:

    revisão vencida > bloco de hoje no cronograma > PADRÃO DE ERRO COM CAUSA
    > missão atual da trilha > ponto de medida mais baixa
    > "Continue de onde parou" (já respondeu) > "Seu primeiro passo" (conta nova)

**A trilha do mapa só enxerga o Treino** (`treino_agregado`): antes de
2026-09-28, quem tinha 200 questões de prova recebia "Seu primeiro passo" todo
dia. "Primeiro passo" é só para `totalRespondidas === 0`.

> [!warning] Antes de reordenar a primeira dobra de novo, leia
> `ExplorarOSapiens.test.js` — a regra está travada lá **de propósito**, porque cada
> uma das passadas anteriores desfez a anterior sem saber.

**Números das Portas só quando MEDIDOS:** fila é `revisoes.resumo.questoes` (não
existe `resumo.vencidas`), semana é `cronograma.total_concluidos/total_blocos`,
ofensiva é `engajamento.ofensiva.dias`, nota é `redacao.avaliacao.nota_total`.

`lib/trilha.js` existe para que a ordem da trilha seja **uma** função
(`ordenarMissoes`/`missaoAtual`), usada pelo desenho **e** pela frase do passo. Duas
cópias apontariam para nós diferentes na mesma dobra.

## O erro vira sequência: prática dirigida e fechamento

O degrau de padrão do Próximo Passo não leva a uma prova qualquer. O clique
busca `GET /motor/habilidade/:processo` (o plano do motor, que até 2026-09-28
nenhuma tela chamava) e abre `/estudar/provas?item_ids=…` com até 5 questões
**inéditas** daquele raciocínio. O porquê viaja no `state` da navegação, não
na URL — `lib/praticaDirigida.js` é a única ponte (pura, testada):

- **Cabeçalho** (`CabecalhoDirigido` em `Provas.jsx`): a Mentis explica a
  escolha sem chamar modelo — o ponto, o erro que mais se repete, e o
  enquadramento escrito à mão (`intervencoes._ENQUADRAMENTO`) **fechado num
  `<details>`**. Aberto, media 514px a 375px e empurrava o enunciado para fora
  da tela. O texto do caso sem catálogo (`_SEM_CATALOGO`) **nunca** viaja: ele
  fala "nesta versão da ontologia".
- **Fechamento** (`FechamentoDaSerie`): substituiu "Você concluiu todas as
  questões! 🎉 / Voltar". Acertos da série, comparação **descritiva** com o
  histórico do ponto (só com amostra ≥ 3 dos dois lados, e avisando que série
  curta não fecha a questão), o sinal de progresso, e uma saída concreta:
  mais do mesmo ponto, o ponto em que dois erros da série começaram
  (`pontoRepetido`, lendo a `causa_raiz` que já vem em cada resposta), ou o
  Próximo Passo.
- **O momento de recompensa** (`RecompensaDaSerie`, regra pura em
  `praticaDirigida.recompensaDaSerie`): o que o Duolingo faz no fim da lição,
  com a régua da linha ética — "+N XP nesta série" é a diferença REAL de
  `/engajamento/me` entre o começo e o fim; "Dia N da sua sequência garantido"
  só com `estudou_hoje`; a missão do dia cumprida é resgatada ali mesmo, com o
  prêmio fixo. Durante a série, "N seguidas" a partir de 3 acertos. Sem dado,
  a peça some. Não acrescente recompensa que o servidor não contou.
- Navegar para a **mesma rota** com outros ids não remonta a página: o filtro
  é refeito por `location.key` e o `QuestionRunner` leva `key={location.key}`.

Na devolutiva de rodada, o visto verde só aparece com ≥ 60%, e dois erros de
mesma raiz viram "Praticar esse ponto". A **última** rodada de lista sem bloco
(revisão, dirigida, área) não abre devolutiva: não paga Sparks e termina onde
o fechamento começa — mostrar as duas sugeria praticar o ponto que o aluno
estava praticando.

O desfecho de missão do Treino segue a mesma gramática: acertos da missão,
antes/depois da habilidade e a próxima missão a um clique
(`trilha.proximaMissaoNoMapa`: lacuna conhecida > vizinho que a missão abriu >
qualquer acessível, nunca a mesma). O efeito do deep-link `?hab=` **não age
com desfecho na tela** — o React Router limpa a URL numa renderização
posterior à que zera a missão, e nesse intervalo o briefing da missão que
acabou reabria por cima do desfecho.

**A ponte prova ↔ Treino.** O mapa e o motor usam os MESMOS 56 ids de habilidade
(`HAB-01`…), e o catálogo liga cada habilidade aos processos que ela exercita
(ver [[motor-cognitivo]]). O fechamento da série dirigida oferece "Treinar no mapa:
<rótulo>" (rótulo de `mapa3d/missoes.js`, o mesmo do mapa — a frase interna da
habilidade não aparece); o Treino lê `/motor/perfil`, marca no briefing a missão
ligada ao padrão de erro das provas e a prefere como próxima missão.

## Um checkpoint só para a devolutiva de prática

Em `ExamSelect.jsx` (`QuestionRunner`), o modal de Sparks e o resumo da sessão eram
dois contadores independentes e **derivavam** depois de retomar um bloco parcialmente
respondido — o aluno recebia o modal sem narrativa, ou o contrário.

Hoje ambos saem de `rodadaNaPosicao(posicao, itens.length)`, disparado de
`responder()` via `Promise.allSettled`, num Dialog só.

> **Não reintroduza um segundo contador independente.**

Prática por área (`filtro.area`, sem `banca`) não dá Sparks — por desenho, área não
tem identidade de bloco e uma chave de rodada ingênua colidiria entre sessões.

## O guia (`OnboardingTour`)

Abre **só no primeiro acesso**. A marca é permanente e mora no **servidor**:
`flags.guia_visto`. O `localStorage` é só atalho para não piscar o balão enquanto a
resposta não chega; o `sessionStorage` anterior morria com a aba.

Gravada tanto no "Começar" quanto no "Pular tour" — quem pulou decidiu não ver, e
reapresentar amanhã o que a pessoa dispensou hoje ignora a resposta dela.

Duas portas para rever, as duas com `?guia=1`, e **nenhuma mexe na marca**. O efeito
de `?guia=1` **ouve a URL** em vez de rodar só na montagem.

Cada passo aponta um elemento real por `data-tour="..."`. **Alvo ausente não quebra a
sequência: o balão centraliza.** `dash-agora` mora no nó aceso da trilha do dia
(muda de elemento conforme o dia; é sempre o próximo passo).

> **Ao acrescentar uma ferramenta, acrescente o passo no guia E a âncora `data-tour`
> no elemento.** O ponto único que decide se o guia abre é o segundo `useEffect` de
> `Dashboard.jsx`; quem grava é `finish()`.

## O Estudar é uma coluna de cartões gordos (2026-10-10)

Pedido do dono, com print: *"muito ruim e pouco atrativo… quero que tudo seja
simples e atrativo, assim como o Duolingo"*. De 2026-09-18 a 2026-10-10 o
`/estudar` tinha Aprender e Praticar em **duas colunas de meia tela**, e quase
todo defeito vinha disso: títulos cortados ("ENEM 20…", "Curso de
Matemática…"), cursos em ladrilhos de 150px que só mostravam nome e ação no
hover (`LadrilhoDeCatalogo`, removido), seis cadernos com a mesma cara.

Hoje, de cima para baixo: cabeçalho com o relógio do ENEM em linha → Siga a
trilha → os três modos (Redação, Treino, Folhear; três quadrados no celular)
→ **Provas do ENEM** → **Cursos** → E-books → pontes de venda. Cada seção abre
com `estudar/CabecaDeSecao` (ícone com pé + título + uma frase).

- **Caderno** (`estudar/CartaoDeCaderno`): o título é a **ÁREA**, não a
  edição — o aluno escolhe "vou fazer Matemática". A edição ("ENEM 2023 ·
  Caderno Azul") é o cabeçalho do grupo. A regra é pura e testada em
  `lib/cadernos.js`: área pela moda que o servidor manda em `disciplinas`,
  cor de caderno **só se a palavra está em `prova`** (nunca deduzida do
  número do caderno), dia pela numeração (1–90 / 91–180).
- **Curso / e-book** (`estudar/CartaoDeCurso`): capa com glifo grande, nome
  em até três linhas, **uma ação escrita**. Se é do aluno e tem conteúdo, o
  cartão inteiro é o link. Se não é, o botão de preço (número do servidor) —
  e o sino de "me avise" só existe para curso **em breve**, na capa: no pé
  ele espremia o preço em "350 S…" a 375px.
- **Destaque** (`curso/CartaoDestaque` + `CaminhoMini`): o curso mais avançado
  em andamento, com o trecho de caminho e um botão "Continuar". O
  `CaminhoMini` é desenhado só de `total`/`concluidas` (o `mapa_de_estados`
  completo só existe no endpoint de **um** curso). Janela de 6 nós.

> [!warning] `CapaDoCurso` recebe a largura por `largura`, nunca por `className`
> Ela tinha `w-full` fixo e o destaque passava `w-14`: duas larguras no mesmo
> elemento são decididas pela ordem do CSS do Tailwind, `w-full` vencia, e a
> capa virou uma barra da largura do card que empurrava o título para fora
> da tela — em produção por três semanas.

`/cursos` (página inteira) continua com os **cards completos** — é onde se
lê a ementa. As duas apresentações são deliberadas.

## A Agenda abre pelo cronograma (2026-10-19)

Pedido do dono: *"principalmente a aba agenda (…) quero que o cronograma seja a
primeira coisa que o aluno veja (…) tudo que é mais importante lá em cima e tudo
que for menos importante embaixo"*. Antes a semana era a QUARTA seção, depois de
um parágrafo, "O seu dia", a fila de revisões e os lembretes.

De cima para baixo: cabeçalho (nome + semana) → **o cronograma**, com o
progresso da semana no cabeçalho dele (anel + "N de M blocos" + barra) e o
próximo bloco como a única ação acesa → **Revisões** → **Guardado para rever** →
**Ajustar a semana** (`<details>` fechado: remontar, montar com a Mentis,
prioridades, "por que a semana ficou assim", compromissos fixos).

- **Quadro, não grade de horas.** No desktop, sete colunas com os itens em ordem
  de horário; no celular/tablet, a tira dos sete dias (pontinho por bloco, verde
  quando feito) e a lista do dia escolhido, que começa em hoje. A grade de horas
  desenhava a duração, que ninguém consulta, e rolava de lado no celular.
- **A aula ao vivo é um item do dia dela**, âmbar, vindo de `lib/live.js` (sem
  requisição) — o cartão grande que ela tinha saiu.
- Anotar compromisso é o "+" do dia (sem horário clicado, a sugestão é a próxima
  meia hora cheia hoje, 14h nos outros dias).
- "O seu dia" saiu: era o dia de hoje do cronograma repetido em cima dele.
- Fila de revisão vazia vira UMA linha, não um cartão com botão.

## O Progresso abre pelos números e gráficos (2026-10-19)

Mesmo pedido: *"os gráficos bem evidentes lá em cima, e não lá embaixo"*. A aba
abria com a leitura da Mentis e a seção de raciocínio (só texto); a primeira
curva aparecia na terceira dobra. Agora: os cinco números (`ResumoDoPainel`) →
**a curva de acerto em largura inteira** → os outros gráficos de evolução → "Onde
a sua nota está sendo decidida" → a leitura da Mentis (`MentisGuia`) → o
raciocínio (`Forcas`) → redação → hábitos → trajetória, conquistas, histórico. O
que se VÊ vem antes do que se lê; cada gráfico continua com a bolha da Mentis.

O balão "Para você" (`PainelDeSugestoes`) nasce **recolhido** abaixo de 1680px:
com o trilho no desktop não sobra canto, e aberto ele cobria os gráficos.

## A loja de Sparks (2026-10-19)

Ordem: título curto + saldo (chip, só no desktop — no celular a barra do topo já
mostra) → **a grade de pacotes** → painel de pagamento (abre logo abaixo) →
garantias → oferta do pacote que vende direitos + "A conta" → indicar → recarga
→ histórico. Decisão em [[decisoes-do-dono]].

**A grade se decide pela largura que ELA tem, não pela janela** (`@container`
em `.loja-casca` e em cada `.loja-pacote`, folha "A LOJA DE SPARKS" no
`index.css`). A régua antiga por janela (`lg:grid-cols-4`) dava quatro colunas
de 165px numa janela de ~1000px ao lado do trilho: o "1500" vazava do card e o
botão do cartão quebrava uma palavra por linha. Hoje: uma coluna abaixo de
520px, duas até 780px, quatro acima. O card **deita** (número e preço na mesma
linha) a partir de 260px de largura própria, e a pilha de moedas e os botões lado
a lado só voltam a partir de 300px — a 320px de tela os dois não cabem junto do
"1.500" e do "R$ 54,90".

- **O destaque é o de maior `destaque_tamanho`** do catálogo (hoje o de 1.500):
  sobe 14px na grade de quatro colunas, contorno e faixa em ciano, e é o
  **único Pix cheio** — os outros são `.btn-contorno`. O pacote com `beneficios`
  ganha violeta (cor do Plus).
- O selo é uma **faixa dentro do contorno**, não um selo pendurado por fora: o
  `overflow: hidden` do card cortava o de fora. Card sem selo guarda a altura da
  faixa (invisível) quando divide a fileira com quem tem.
- "Dá para" desce para o pé do card, junto dos botões: o vão que sobra num card
  mais baixo que o vizinho fica entre o preço e o rodapé, e os rodapés alinham.
- `.botao-cartao` (violeta-escuro da folha clara antiga, ilegível no azul-tinta)
  **não existe mais**; o cartão é `.loja-cartao`, inclusive dentro do painel do
  Pix.

Para ver a loja logada: o `servidor_falso.py` responde catálogo real
(`sparks_store` do backend), indicação e um Pix falso — ver [[ambiente-local]].

## Gráficos

`Grafico` tem uma caixa de **altura fixa** em volta do desenho. **Texto ou botão
depois do gráfico vai em `rodape`, nunca como filho** — como filho ele é espremido
POR CIMA do gráfico, e nenhum teste de render pega isso.

Margem esquerda negativa no recharts **corta o rótulo do eixo Y** ("100%" virava
"10%"). Use `left: 0` + `width` suficiente.

## PWA

`public/sw.js` existe **só** para tornar o app instalável (o Chromium exige um
handler de `fetch`). Ele **não faz cache, de propósito** — cache aqui transformaria
um deploy ruim em algo que nem recarregar resolve.

## Uma armadilha de edição por script

Uma edição em `SparksStore.jsx` deixou um `) : null}` órfão. **O build passou** e o
Babel do CRA aceitou — o texto virou LITERAL na tela. Depois de editar JSX por
script:

```bash
grep -o '"[^"]*) : null[^"]*"' build/static/js/*.js
```

---
Relacionado: [[sistema-visual]] · [[navegacao]] · [[mobile]] · [[mentis]]
