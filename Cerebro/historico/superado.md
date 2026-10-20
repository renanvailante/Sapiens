---
tags: [historico, anti-regressao]
atualizado: 2026-10-19
---

# O que já foi assim e não é mais

Nó **anti-regressão**. Cada linha aqui é uma coisa que uma sessão futura pode
"restaurar" achando que está consertando. Se você vai reintroduzir algo desta lista,
é uma decisão consciente — não um detalhe.

## Nomes e conceitos que mudaram

| Era | É | Quando |
|---|---|---|
| **Zinho** | **Mentis** — a rota `/api/firestore/students/me/zinho` deixou de existir | 09-03 |
| **Aula particular** (`/aulas`, produto 1:1) | **Mentoria** (`/mentoria`), lista de espera. A coleção Mongo continua `aulas_particulares` | 09-15 |
| `CognitiveProfile.jsx` (árvore real da ontologia) | `SkillsMap.jsx` (hexágono cosmético) | 08-24 |
| "o 1º colocado de Medicina da USP" | **Vitor Lara**, pelo nome | 09-17 |
| `/questoes` (quinta interface de questão, sem link de entrada) | `Navigate to="/exams"` | 09-17 |
| "Cronograma" | "Semana" (na barra) | 09-15 |
| `/live` | `/aula-ao-vivo` | 09-16 |

## Mastery do mapa de habilidades

Era **cobertura** (processos tocados / processos do domínio), passada por
`_diminishing_mastery`. Hoje é **volume de acertos** — ver [[decisoes-do-dono]].
Snapshot anterior a 2026-09-15 não tem `acertos`, volta zerado e marcado
`escala_antiga: true`.

## A barra de navegação — seis passadas

1. **09/09** — Painel · Treino · Redação · Mentis (4 abas).
2. **09/15** — Comunidade entrou como 6ª; o orçamento acabou.
3. **09/17** — convergência desktop↔celular: Painel · Treino · Praticar · Mentis + Menu.
4. **09/18** — Praticar + Cursos viraram **Estudar**; 6 abas.
5. **09/18** — Redação volta como primária; 7 abas, 52px de folga.
6. **09/18 (atual)** — **cinco áreas por PERGUNTA**: Hoje · Agenda · Estudar ·
   Progresso · Comunidade. Ver [[navegacao]].

Junto disso: a **auto-medição** (`quantasCabem` + `ResizeObserver`) nasceu em 17/09 e
**saiu** em 18/09, trocada por lista fixa + orçamento de projeto.

## Onze telas viraram seções (2026-09-18)

Nenhuma perdeu conteúdo; todas perderam o endereço próprio. Os redirects estão
em `lib/rotas.LEGADO` e **não devem ser removidos** — são links de WhatsApp e
favoritos de aluno.

| Era | Virou |
|---|---|
| `/revisoes` (fila + lembretes) | seções da **Agenda** |
| `/revisoes` (trajetória) | seção do **Progresso** |
| `/conquistas` + `/liga` | uma seção do Progresso |
| `/history` + `/trash` | Histórico do Progresso, lixeira como **filtro** |
| `/minhas-questoes` | fonte "geradas" do Treino (`?fonte=geradas`) |
| `/indicar` | seção da carteira (`/sparks#indicar`) |
| `/feed` | modo "folhear" de Estudar |
| `/map/:analysisId` | **eliminada** — redirect para `/analysis/:id` |

A `/revisoes` era o caso mais claro: o cronograma gerava blocos apontando para
ela, e ela desenhava a fila que o cronograma tinha acabado de agendar. Uma tela
apontando para a outra e de volta, com o aluno no meio.

## Componentes de navegação removidos (2026-09-18)

`Nav.jsx`, `BarraInferior.jsx`, `LancadorDeFerramentas.jsx`, `lib/atalhos.js` e
`lib/atalhos.test.js`. Os quatro foram substituídos por `components/Navegacao.jsx`
+ `components/Menu.jsx` + `lib/navegacao.js`.

**As 39 montagens manuais de `<Nav/>` sumiram junto**: a navegação é montada
uma vez no `App.js`, como a barra inferior e a camada de continuidade já eram.
Era essa montagem tela a tela que garantia que a próxima tela nova nasceria sem
barra — e foi assim que o celular passou meses sem navegação nenhuma.

`Tela.jsx` perdeu a prop `semNav` junto (ninguém a usava).

## O mapa radial de uma análise

`LearningMap.jsx` desenhava um grafo radial à mão sobre uma análise antiga,
alcançável por um único botão dentro de `/analysis/:id`. O produto já tem UM
mapa — o do Treino, que é vivo. Dois mapas com nomes parecidos e conteúdos
diferentes fazem o aluno duvidar do que está olhando.

## A Mentis sem movimento

Até 2026-10-09 a direção de arte proibia salto e euforia também no MOVIMENTO
("mentor confirma, não comemora"). Hoje ela flutua, fala, fica feliz e olha —
a proibição ficou só na fala (sem emoji, sem euforia). Ver [[mentis]].

## O tour de boas-vindas

22 balões → 5 (17/09) → **21** (cobrindo todas as ferramentas). Alvos antigos que
**não existem mais**: `nav-mobile-trigger`. Os atuais incluem `barra-inferior` e
`barra-mais`.

Frequência: toda montagem → 1× por sessão do navegador (15–17/09) → **só no primeiro
acesso**, marcado no servidor.

## A primeira dobra do Painel — três passadas em três dias

mapa → Próximo Passo → Portas, e a terceira deixou as duas últimas **empilhadas** —
duas respostas para "e agora?". Hoje: `ProximoPasso` primeiro, Portas em "Explorar",
fechada. **Travado em `ExplorarOSapiens.test.js`.** Ver [[padroes-de-tela]].

Saíram do Painel: o parágrafo de manifesto por seção, a tira de estatísticas, o card
"Próxima ação", três banners de largura total, a grade "Ferramentas" (7 azulejos), a
linha da Mentis e a linha "faltam X dias".

## O Hoje virou trilha (2026-10-09)

A quarta passada da primeira dobra. Saíram do Hoje: o `ProximoPasso` como peça
(com seus três botões lado a lado — passo, "Mapa de treino", "Provas do ENEM" —,
a trilha do mapa à direita e a tira de números), a grade de missões do
`PainelDeProgresso` (as missões viraram nós da trilha, `semMissoes`), o chip da
meta declarada no cabeçalho e, com ele, a leitura de `/onboarding` que só o
alimentava. **Não restaure nenhum como segunda resposta a "e agora?"** — a
regra é um nó aceso. Ver [[padroes-de-tela]].

O fim de série tinha até cinco botões do mesmo peso (praticar o ponto, mais do
ponto, "Ver o próximo passo", mapa, voltar); hoje tem UM grande, "Continuar a
trilha". O botão flutuante da Mentis era um ícone de brilho num disco; hoje é
a própria personagem.

## Direitos dos pacotes

`lives_inclusas` era do pacote de **1.500 para cima**; desde 16/09 é **só do de
4.000**. Quem comprou antes continua entrando — ver [[catalogo]].

`mentis_ilimitada`: em 16/09 a **loja** passou a anunciar "por um mês", mas o
backend nunca passou a expirar nada — ver a divergência aberta em [[catalogo]].
Memória antiga afirmava um `PRAZO_DOS_DIREITOS_DIAS` e um campo `_ate` que **não
existem no código**.

## Componentes removidos

- `PedirWhatsApp.jsx` — o cartão dispensável que pedia o telefone. Removido em 17/09
  **justamente por ser ignorável**; hoje quem entra pelo Google passa por
  `/completar-cadastro`, que é um portão.
- `<a href={pdf} download>` do e-book → `pages/EbookLeitor.jsx`. Ver [[inviolaveis]].
- As conquistas do **backend** (ficaram só no `Dashboard.jsx`).
- O card `resumoSessao` de página inteira e seu gatilho separado.

## Redesigns que se sobrepuseram

Três passadas grandes de UI/UX em ~3 semanas (08-24 "premium/gamificado", 09-15
"trilha Duolingo + /bem-vindo", 09-16 "Painel abre pelo Próximo Passo + primitivas
viram sistema"). **O estado atual é o de 09/18**; descrições das duas primeiras só
valem como arqueologia. A identidade visual **não** mudou em nenhuma delas.

## Coisas que existiram só pela metade

- **Revisão programada dos lembretes** — de 2026-09 a 2026-10-01 o bloco
  `agendamento` nascia pronto e ninguém o avançava. Hoje avança (ver [[mentis]]).
  Não "restaure" o estado `aguardando`: lembrete sem data é legado, lido como
  vencido no dia seguinte ao que foi guardado.
- **O fim de série "Você concluiu todas as questões! 🎉 / Voltar"** — virou o
  fechamento de série (ver [[padroes-de-tela]]).

## Coisas que nunca chegaram a existir

- **`VIDEO_BOAS_VINDAS`** em `pages/BemVindo.jsx` está **vazia de propósito** —
  enquanto estiver, a tela desenha o lugar do vídeo.
- **Conteúdo real de e-book** — a infraestrutura entrou vazia de propósito.
- **Ponte automática aluno → professor** — decisão do dono.
- **"site do Assad"** — referência visual pedida em 09/15 que nunca foi
  identificada com confiança. Ficou de fora, pendente do link.

## A identidade visual — bioluminescência → Clareza (2026-10-19)

De 2026-09-03 a 2026-10-19 o produto foi "bioluminescência tecnológica":
abismo quase preto, auroras animadas e uma malha de 1px atrás de tudo
(`body::before` / `body::after`), painéis de vidro com `backdrop-filter`, luz
ciano→azul→violeta em degradê nos botões, halos nos nós e nas bordas, Manrope no
texto e IBM Plex Mono nos rótulos. O dono a chamou de **poluída** e pediu a
simplicidade do Duolingo — ver [[sistema-visual]] e [[decisoes-do-dono]].

Não restaure por engano: vidro, aurora, halo, degradê de fundo em cartão,
`backdrop-blur` e a segunda família tipográfica. A regra "luz é informação"
sobreviveu como "uma ação acesa por tela".

Arqueologia que ainda explica código: as auroras **nunca apareceram** até
2026-09-16 porque o `background-color` do `body`/`#root` era pintado depois de um
filho com `z-index` negativo (CSS 2.1, apêndice E). Daí a regra, ainda válida, de
a cor da página morar só no `html`.

## A barra de cima do desktop → o trilho (2026-10-19)

A navegação do desktop era uma barra horizontal no topo (`BarraDeCima`), presa a
1072px úteis e a uma conta de largura medida a cada área nova. Virou o TRILHO, uma
coluna à esquerda (ver [[navegacao]]). As cinco áreas, a ordem e o Menu não
mudaram. **Não volte a barra de cima** sem refazer a conta de largura que ela
exigia — e sem rever as telas cheias que hoje começam depois do trilho.

## A Agenda em grade de horas → quadro da semana (2026-10-19)

A semana era uma grade de horas (06h–23h, 52px por hora, 760px de largura
mínima) na QUARTA seção da aba, que rolava de lado no celular, com clique no
horário vazio para anotar. Virou um quadro de sete colunas (desktop) e tira de
dias + lista (celular), no TOPO da aba — ver [[padroes-de-tela]]. Saíram junto:
a seção "O seu dia" (duplicava o hoje do cronograma), o cartão grande da aula ao
vivo (virou item do dia dela) e a faixa de prioridades aberta (foi para "Ajustar
a semana", fechado).

## A voz da Mentis

| Era | É | Quando |
|---|---|---|
| Síntese do aparelho (`speechSynthesis`), robótica no Windows e em muito Android | Frases **gravadas** uma vez (`public/voz/`), voz brasileira neural; a síntese ficou só de reserva | 10-19 |
| Voz gerada por fala no servidor (`/mentis/voz`, nunca publicada) | Descartada: Free Tier de 10 falas/dia e custo por fala — ver [[mentis]] | 10-19 |

## Um sintoma que já enganou

**"Não consigo responder de novo"** num exercício de curso: `travado` era
`jaAcertou && !resultado` e o botão só limpava `resultado`, que já era nulo. Hoje há
estado `refazendo`. Ver [[cursos-conteudo]].

---
Relacionado: [[navegacao]] · [[catalogo]] · [[decisoes-do-dono]] · [[padroes-de-tela]]
