import {
  House, GraduationCap, CalendarDays, ChartColumn, Users,
  Zap, MessageSquareWarning, Radio, UserRoundCheck, Download, HelpCircle,
  ShieldCheck, Megaphone, LogOut, MessageCircle,
} from "lucide-react";
import { ROTAS } from "./rotas";

/**
 * A TAXONOMIA DA NAVEGAÇÃO — uma lista, os dois aparelhos.
 *
 * ---------------------------------------------------------------------------
 * O QUE ISTO SUBSTITUI, E POR QUE PRECISAVA SUBSTITUIR
 * ---------------------------------------------------------------------------
 *
 * O produto tinha CINCO sistemas de navegação, cada um com uma lista diferente
 * dos mesmos destinos:
 *
 *   1. `PRIMARY_LINKS` no `Nav.jsx`      — 7 abas (desktop)
 *   2. `ABAS` + `ACAO` na `BarraInferior` — 4 + Menu (celular), outro conjunto
 *   3. `ATALHOS` em `lib/atalhos.js`      — 8 pílulas, só no celular
 *   4. `GRUPOS` no `LancadorDeFerramentas`— 16 linhas em 4 grupos
 *   5. `PortaisDaJornada`                 — 10 portas, com OUTROS nomes
 *
 * O comentário do `Nav.jsx` afirmava que as duas barras desenhavam "o MESMO
 * conjunto primário". Não desenhavam: Redação, Aulas e Mentis eram abas no
 * desktop e não existiam na barra do celular, que compensava com a tira de
 * atalhos — um terceiro conjunto, numa quarta ordem de prioridade. Quem
 * estudava no telefone e voltava no notebook não encontrava o mesmo produto.
 *
 * E o mesmo destino chegava a ter quatro nomes: `/exams` era "Praticar" na
 * porta, "Estudar" na barra, `barra-praticar` no testid e "Provas do ENEM" no
 * Menu. Quatro nomes para um lugar é o jeito mais eficiente de impedir o aluno
 * de construir um modelo do produto — foi o preço já pago uma vez quando
 * `/cognitive-profile` tinha cinco nomes e virou `/desempenho`.
 *
 * Agora há **uma** lista. A barra de cima e a de baixo leem `AREAS`; o Menu lê
 * `MENU`; e nada aparece nos dois.
 *
 * ---------------------------------------------------------------------------
 * AS CINCO ÁREAS SÃO CINCO PERGUNTAS, NÃO CINCO MÓDULOS
 * ---------------------------------------------------------------------------
 *
 *   Hoje       — "e agora?"                 decidir
 *   Estudar    — "o que eu vou fazer?"      executar
 *   Agenda     — "quando?"                  planejar
 *   Progresso  — "estou evoluindo?"         conferir
 *   Comunidade — "quem me responde?"        perguntar
 *
 * O critério de entrada é a PERGUNTA, não a importância da ferramenta. Redação
 * é a coisa que mais vale ponto no ENEM e não é área: ela é uma resposta à
 * pergunta "o que eu vou fazer", igual a resolver prova e a ler um curso. Área
 * não é pódio.
 *
 * ---------------------------------------------------------------------------
 * A ORDEM, E POR QUE ESTUDAR FICA NO MEIO
 * ---------------------------------------------------------------------------
 *
 * `acao: true` marca Estudar como o alvo elevado do celular: 22px acima das
 * vizinhas (`.aba-acao`) e o único objeto aceso da barra. A navegação do
 * telefone responde "o que eu faço agora", não só "para onde eu vou".
 *
 * **Isso obriga Estudar a ser o terceiro de cinco**, e não o segundo. O alvo
 * elevado é o meio geométrico da barra — é onde o polegar chega sem esticar,
 * e é a posição que ele já ocupava antes desta passada (a barra era
 * `Painel · Semana · [Estudar] · Desempenho · Mais`). Pôr Estudar em segundo
 * empurraria o alvo elevado para fora do centro e trocaria a posição de quatro
 * abas de uma vez para quem já usa o produto.
 *
 * Com esta ordem, o único alvo que muda de identidade no celular é o quinto:
 * "Mais" (a gaveta) virou Comunidade. Hoje, Agenda, Estudar e Progresso ficam
 * exatamente onde o dedo já os procura.
 *
 * A leitura também fecha: abro o app (Hoje) → vejo o que me espera (Agenda) →
 * faço (Estudar) → confiro se rendeu (Progresso) → pergunto quando travo
 * (Comunidade). Decidir, planejar, executar, medir, pedir ajuda.
 *
 * `navegacao.test.js` trava a posição do alvo elevado.
 *
 * ---------------------------------------------------------------------------
 * O ORÇAMENTO DE LARGURA (a conta que já estourou duas vezes)
 * ---------------------------------------------------------------------------
 *
 * A barra de cima vive num `max-w-6xl` com `px-10`: **1072px úteis, e nenhum
 * monitor largo aumenta isso**. Com sete primários a conta dava 1020px — 52px
 * de folga, menos que um rótulo. Com cinco, sobra espaço real, e é isso que
 * paga o Menu ter saído da barra inferior do celular (ver abaixo).
 *
 * `lib/navegacao.test.js` trava a contagem. **Antes de acrescentar uma sexta
 * área, meça de novo** — a receita está em `Cerebro/ux/navegacao.md`, e a
 * intuição erra por dezenas de pixels.
 *
 * Desde 2026-10-19 (sistema CLAREZA) o desktop não tem mais barra de cima:
 * as áreas moram no TRILHO, uma coluna à esquerda, e o orçamento de largura
 * deixou de existir. A contagem continua travada pelo motivo que sobra — o
 * polegar no celular, onde cinco ainda é o teto.
 *
 * ---------------------------------------------------------------------------
 * A COR DE CADA ÁREA
 * ---------------------------------------------------------------------------
 *
 * `cor` pinta o ícone no trilho e na barra do celular. É a única exceção à
 * regra "cor é significado" do `index.css`: na navegação, a cor é
 * ENDEREÇO — o olho acha a área pela cor antes de ler o nome, como nos
 * ícones coloridos do Duolingo. Estudar é ciano porque é a ação.
 */
export const AREAS = [
  {
    chave: "hoje",
    rota: ROTAS.HOJE,
    icone: House,
    cor: "#FFB547",
    nome: "Hoje",
    pergunta: "E agora?",
    testid: "nav-hoje",
    tour: "nav-hoje",
  },
  {
    chave: "agenda",
    rota: ROTAS.AGENDA,
    icone: CalendarDays,
    cor: "#FF8FA3",
    nome: "Agenda",
    pergunta: "Quando?",
    testid: "nav-agenda",
    tour: "nav-agenda",
  },
  {
    chave: "estudar",
    rota: ROTAS.ESTUDAR,
    icone: GraduationCap,
    cor: "#4FD9FF",
    nome: "Estudar",
    pergunta: "O que eu vou fazer?",
    testid: "nav-estudar",
    tour: "nav-estudar",
    // O alvo elevado da barra do celular — e por isso o TERCEIRO de cinco.
    // Ver a nota acima: a posição é do polegar, não da narrativa.
    acao: true,
  },
  {
    chave: "progresso",
    rota: ROTAS.PROGRESSO,
    icone: ChartColumn,
    cor: "#A78BFA",
    nome: "Progresso",
    pergunta: "Estou evoluindo?",
    testid: "nav-progresso",
    tour: "nav-progresso",
  },
  {
    chave: "comunidade",
    rota: ROTAS.COMUNIDADE,
    icone: Users,
    cor: "#3DDC97",
    nome: "Comunidade",
    pergunta: "Quem me responde?",
    testid: "nav-comunidade",
    tour: "nav-comunidade",
  },
];

/**
 * O VOCABULÁRIO — um conceito, um nome, em toda superfície.
 *
 * O produto chamava o MESMO lugar por até quatro nomes ao mesmo tempo:
 * `/exams` era "Praticar" na porta da descoberta, "Estudar" na barra,
 * `barra-praticar` no testid e "Provas do ENEM" no Menu. `/desempenho` já
 * tinha tido cinco (foi por isso que a URL foi renomeada em 17/09) e voltou a
 * ter três: "Seu perfil" na porta, "Meu desempenho" no chip da Mentis,
 * "Desempenho" na aba.
 *
 * Isso não é inconsistência de copy — é de **aprendizado**. O aluno precisa
 * ficar bom no Sapiens, não bom em decorar que quatro palavras apontam para a
 * mesma tela.
 *
 * Toda superfície que nomeia um destino lê daqui: as portas do Hoje, os chips
 * da Mentis, o Menu e as abas. Uma chave sem entrada devolve `undefined`, e é
 * de propósito — quem acrescentar destino tem de nomeá-lo aqui.
 *
 * A PERGUNTA é outra coisa e não mora aqui: ela muda por superfície (a porta
 * pergunta "qual erro você repete sem perceber?", a aba pergunta "o que eu vou
 * fazer?"). O que não pode mudar é o NOME.
 */
export const NOMES = {
  [ROTAS.HOJE]: "Hoje",
  [ROTAS.ESTUDAR]: "Estudar",
  [ROTAS.PROVAS]: "Provas do ENEM",
  [ROTAS.CURSOS]: "Cursos e e-books",
  [ROTAS.REDACAO]: "Redação",
  [ROTAS.TREINO]: "Mapa de Treino",
  [ROTAS.FOLHEAR]: "Folhear",
  [ROTAS.AGENDA]: "Agenda",
  [ROTAS.PROGRESSO]: "Progresso",
  [ROTAS.COMUNIDADE]: "Comunidade",
  [ROTAS.MENTIS]: "Mentis",
  [ROTAS.SPARKS]: "Meus Sparks",
  [ROTAS.SUGESTOES]: "Fale com a equipe",
  [ROTAS.AULA_AO_VIVO]: "Aula ao vivo",
  [ROTAS.MENTORIA]: "Mentoria",
};

/** O nome de um destino, aceitando rota com âncora ou query. As seções têm
 *  nome próprio porque um link para `#conquistas` promete troféus, não
 *  "Progresso" — e quebrar essa promessa é o defeito que a âncora existe para
 *  evitar. */
export function nomeDoDestino(rota) {
  const base = (rota || "").split(/[?#]/)[0];
  const ancora = (rota || "").split("#")[1];
  const secoes = {
    conquistas: "Conquistas e liga",
    historico: "Histórico",
    trajetoria: "Trajetória",
    revisoes: "Revisões",
    lembretes: "Guardado para rever",
    indicar: "Indicar um amigo",
  };
  if (ancora && secoes[ancora]) return secoes[ancora];
  if (rota?.includes("fonte=geradas")) return "Questões da Mentis";
  return NOMES[base];
}

/** A área do meio, elevada no celular. Derivada, nunca uma segunda lista: uma
 *  constante à parte divergiria de `AREAS` no primeiro reordenamento. */
export const AREA_DE_ACAO = AREAS.find((a) => a.acao);

/**
 * OS ENDEREÇOS QUE NÃO SÃO ÁREA — e a regra que decide isso.
 *
 * > **O Menu não pode conter nada que o aluno precise para aprender a usar o
 * > produto.** Quem nunca o abrir não perde nenhuma ferramenta pedagógica.
 *
 * Esse é o teste, e é ele que torna seguro o Menu ter saído do quinto alvo da
 * barra do celular (onde ficava "Mais") e passado para o canto da marca. O
 * argumento que criou aquele alvo — "gaveta só abre quem já sabe que ela
 * existe" — era correto **enquanto a gaveta guardava metade do produto**:
 * mural, liga, revisões, questões geradas, perfil, histórico. Hoje ela guarda
 * carteira, suporte e sistema, e o quinto alvo virou uma área de verdade.
 *
 * Aula ao vivo e Mentoria moram aqui por um motivo diferente: são produtos do
 * mentor, com data e preço próprios. Eles não vivem só aqui — a aula aparece
 * como evento datado na Agenda e a mentoria na seção "Com o Vitor" do Hoje,
 * que é onde a informação é verdadeira. Aqui é o índice, não a vitrine.
 */
export const MENU = [
  {
    titulo: "Com Vitor Lara",
    itens: [
      {
        rota: ROTAS.AULA_AO_VIVO,
        icone: Radio,
        nome: "Aula ao vivo · quinta",
        nota: "60 min ao vivo, uma vez por semana",
        destaque: true,
        aoVivo: true,
      },
      {
        rota: ROTAS.MENTORIA,
        icone: UserRoundCheck,
        nome: "Mentoria",
        nota: "Um a um, com lista de espera",
        destaque: true,
      },
    ],
  },
  {
    titulo: "Minha conta",
    itens: [
      {
        rota: ROTAS.SPARKS,
        icone: Zap,
        nome: "Meus Sparks",
        nota: "Saldo, pacotes e o seu código para indicar um amigo",
      },
      {
        rota: ROTAS.MENTIS,
        icone: MessageCircle,
        nome: "Conversa com a Mentis",
        nota: "A conversa inteira em tela cheia",
        mascote: true,
      },
      {
        rota: ROTAS.SUGESTOES,
        icone: MessageSquareWarning,
        nome: "Fale com a equipe",
        nota: "Achou um erro? Tem uma ideia? A gente lê e responde",
      },
    ],
  },
];

/** Ações do rodapé do Menu: não são destino, são coisas que se fazem. */
export const MENU_ACOES = {
  guia: { icone: HelpCircle, nome: "Rever o guia da Mentis" },
  instalar: { icone: Download, nome: "Instalar o app" },
  sair: { icone: LogOut, nome: "Sair" },
};

/** Só para quem é da equipe. Fora de `MENU` porque a lista do aluno não pode
 *  depender de quem está logado — ela é a mesma para todo mundo. */
export const MENU_EQUIPE = [
  { rota: ROTAS.ADMIN, icone: ShieldCheck, nome: "Painel do admin", chave: "admin" },
  { rota: ROTAS.PROMOTER, icone: Megaphone, nome: "Painel do promoter", chave: "promoter" },
];

/**
 * Onde a navegação não entra, e por quê.
 *
 * `/estudar/folhear`  — sangria total, com controles próprios no rodapé.
 * `/bem-vindo`        — o primeiro acesso é uma conversa conduzida; sair dela
 *                       pelo meio é sair do onboarding sem ter terminado.
 * `/estudar/provas/:id` — a única tela do produto com **estado não salvo**
 *                       dentro. Uma barra permanente embaixo de um gabarito
 *                       pela metade é um convite a perdê-lo.
 * `/completar-cadastro` — é um portão, não uma tela: navegar para fora dela é
 *                       exatamente o que ela existe para impedir.
 */
export const SEM_NAVEGACAO = [
  ROTAS.FOLHEAR,
  ROTAS.BEM_VINDO,
  ROTAS.COMPLETAR_CADASTRO,
];

/** Prefixos (com filhas) em que a navegação também não entra. Hoje só um: o
 *  motor de prova, que roda em `/estudar/provas/:examId`. A LISTA de cadernos
 *  (`/estudar/provas`, sem id) continua com barra — é escolha, não prova. */
export const SEM_NAVEGACAO_PREFIXO = [
  `${ROTAS.PROVAS}/`,
  // As landings de anúncio (`/ads/*`). Elas não são tela do produto: recebem
  // tráfego externo e têm UMA ação. Uma barra com cinco áreas ali é a lista
  // das outras ações — e para um visitante logado que caiu num anúncio seria
  // a moldura do app em volta de uma peça de aquisição.
  `${ROTAS.ADS}/`,
];

/** A navegação aparece nesta rota? Uma regra, lida pela barra de cima e pela
 *  de baixo — eram duas listas (`SEM_BARRA` e `SEM_TIRA`) que já divergiam:
 *  a de cima escondia a tira em `/exam` e a de baixo em `/exam/`. */
export function temNavegacao(pathname) {
  const atual = (pathname || "/").replace(/\/+$/, "") || "/";
  if (SEM_NAVEGACAO.includes(atual)) return false;
  return !SEM_NAVEGACAO_PREFIXO.some((p) => atual.startsWith(p));
}
