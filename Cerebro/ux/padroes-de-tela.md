---
tags: [ux, padroes, componentes]
atualizado: 2026-09-18
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
- `MentisWidget` — o ícone flutuante
- `ContinuidadeDaPagina` — a pista de continuidade

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

## O Hoje abre pela AÇÃO

`ProximoPasso.jsx` é a primeira coisa: **uma** ação, escolhida numa escada de
prioridade sobre dados que a página **já carregou** (revisão vencida > bloco de hoje
no cronograma > missão atual da trilha > praticar). **Custa zero requisição.**

Ordem desde 18/09, cinco seções: **Próximo Passo → O que mudou → Sua sequência
→ Com o mentor → Explorar**.

Saíram quatro blocos que eram, cada um, o resumo de outra aba: a tira da semana
(Agenda), o aviso de revisão (Agenda de novo), a grade de focos e domínio
(Progresso) e a fileira de conquistas (Progresso de novo). Eram ~12 blocos
simultâneos e vitrines de vitrines — quem clicasse em qualquer uma achava a
MESMA informação maior do lado de lá.

`components/OQueMudou.jsx` os substituiu por **eventos**, não resumos: um
resumo ("você tem 12 blocos na semana") existe sempre e por isso não chama
atenção; um evento ("sua redação foi corrigida") só existe quando aconteceu.
Mesma disciplina do Próximo Passo — **zero requisição nova**, teto de quatro
linhas, e nada genérico (toda linha cita um número do próprio aluno).

As 10 Portas (`PortaisDaJornada.jsx`) moram na seção **Explorar**
(`ExplorarOSapiens.jsx`), **fechada por padrão** e aberta só para quem nunca
respondeu nada. A preferência do aluno vence e mora em `localStorage`.

> [!warning] Antes de reordenar a primeira dobra de novo, leia
> `ExplorarOSapiens.test.js` — a regra está travada lá **de propósito**, porque cada
> uma das três passadas anteriores desfez a anterior sem saber.

**Números das Portas só quando MEDIDOS:** fila é `revisoes.resumo.questoes` (não
existe `resumo.vencidas`), semana é `cronograma.total_concluidos/total_blocos`,
ofensiva é `engajamento.ofensiva.dias`, nota é `redacao.avaliacao.nota_total`.

`lib/trilha.js` existe para que a ordem da trilha seja **uma** função
(`ordenarMissoes`/`missaoAtual`), usada pelo desenho **e** pela frase do passo. Duas
cópias apontariam para nós diferentes na mesma dobra.

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
sequência: o balão centraliza.**

> **Ao acrescentar uma ferramenta, acrescente o passo no guia E a âncora `data-tour`
> no elemento.** O ponto único que decide se o guia abre é o segundo `useEffect` de
> `Dashboard.jsx`; quem grava é `finish()`.

## Duas apresentações de catálogo, de propósito

**Ladrilhos** quadrados (`LadrilhoDeCatalogo`, abrem no cursor) na coluna "Aprender" de `/estudar`;
**cards completos** em `/estudar/cursos`. O ladrilho cresce **só para baixo** — crescer para
os lados entra no respiro do contêiner e empurra a régua horizontal da página.

O curso em andamento ganha `curso/CartaoDestaque.jsx` + `curso/CaminhoMini.jsx` —
versão pequena e não-interativa do caminho serpenteado, desenhada só a partir de
`total`/`concluidas` (o `mapa_de_estados` completo só existe no endpoint de **um**
curso, não na listagem). Janela de 6 nós centrada em onde o aluno está.

O selo de % **substitui** o selo "Meu", não se soma a ele. E-books não têm essa noção
(sem tracking de leitura).

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
