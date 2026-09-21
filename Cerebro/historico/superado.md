---
tags: [historico, anti-regressao]
atualizado: 2026-09-18
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

## Coisas que nunca chegaram a existir

- **`VIDEO_BOAS_VINDAS`** em `pages/BemVindo.jsx` está **vazia de propósito** —
  enquanto estiver, a tela desenha o lugar do vídeo.
- **Conteúdo real de e-book** — a infraestrutura entrou vazia de propósito.
- **Revisão programada** — o bloco `agendamento` existe e ninguém o avança, para não
  haver migração quando for.
- **Ponte automática aluno → professor** — decisão do dono.
- **"site do Assad"** — referência visual pedida em 09/15 que nunca foi
  identificada com confiança. Ficou de fora, pendente do link.

## Um sintoma que já enganou

**"Não consigo responder de novo"** num exercício de curso: `travado` era
`jaAcertou && !resultado` e o botão só limpava `resultado`, que já era nulo. Hoje há
estado `refazendo`. Ver [[cursos-conteudo]].

---
Relacionado: [[navegacao]] · [[catalogo]] · [[decisoes-do-dono]] · [[padroes-de-tela]]
