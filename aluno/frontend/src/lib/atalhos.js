import {
  PenLine, CalendarClock, CalendarDays, Users, Sparkles, Brain, Trophy,
  GraduationCap, Rss,
} from "lucide-react";

/**
 * OS ATALHOS — as miniaturas que preenchem a barra.
 *
 * Uma lista só, lida por DUAS barras: a de cima no desktop (ícones redondos,
 * que aparecem conforme a largura permite) e a tira rolável do celular. É o
 * que garante que o aluno de iPhone alcance em um toque exatamente as mesmas
 * telas que o de notebook alcança em um clique — a barra inferior tem cinco
 * alvos fixos por invariante de polegar, e sem esta tira o celular ficava com
 * cinco portas contra as doze do desktop.
 *
 * O que NÃO entra aqui: o que já é aba primária, o que já tem botão próprio
 * na barra (Aulas, Sparks) e o que é administrativo. Miniatura repetida a
 * 40px de distância da aba com o mesmo destino é ruído, não atalho.
 *
 * **2026-09-17 — a lista mudou porque o conjunto primário mudou.** O desktop
 * tinha seis abas (Treino, Painel, Redação, Semana, Mural, Mentis) e o
 * celular tinha outras quatro (Painel, Treino, Praticar, Mentis): quem
 * estudava no telefone e voltava no notebook não encontrava o mesmo produto,
 * e "Praticar" — o botão elevado, por onde quase tudo começa no celular —
 * nem sequer era aba no desktop. Agora as duas barras desenham o MESMO
 * conjunto primário, e Redação, Semana e Mural desceram para cá, no topo da
 * prioridade, porque eram abas até ontem.
 *
 A ORDEM É PRIORIDADE: a barra do desktop mede a si mesma e desenha só as
 * primeiras que couberem (ver `quantasCabem` abaixo e a nota em `Nav.jsx`),
 * então o que estiver no fim da lista é o primeiro a sumir num notebook de
 * 13". No celular a tira rola e mostra todas, sempre.
 */
export const ATALHOS = [
  { rota: "/redacao", icone: PenLine, nome: "Redação", label: "Redação" },
  { rota: "/revisoes", icone: CalendarClock, nome: "Revisões", label: "Revisões de hoje" },
  { rota: "/cronograma", icone: CalendarDays, nome: "Semana", label: "Cronograma da semana" },
  { rota: "/comunidade", icone: Users, nome: "Mural", label: "Mural de dúvidas" },
  { rota: "/minhas-questoes", icone: Sparkles, nome: "Minhas questões", label: "Questões geradas pela Mentis" },
  { rota: "/cognitive-profile", icone: Brain, nome: "Desempenho", label: "Seu desempenho" },
  { rota: "/conquistas", icone: Trophy, nome: "Conquistas", label: "Conquistas e liga" },
  { rota: "/cursos", icone: GraduationCap, nome: "Cursos", label: "Cursos e e-books" },
  { rota: "/feed", icone: Rss, nome: "Feed", label: "Feed de questões" },
];

/** Cada miniatura ocupa 36px de ícone mais 4px de vão. */
export const LARGURA_DA_MINIATURA = 40;

/**
 * Quantas miniaturas o DESKTOP desenha, no máximo, por mais larga que seja a
 * tela.
 *
 * A barra media a si mesma e enchia a folga: num monitor de 1536px o aluno
 * via quatro abas com nome ao lado de NOVE círculos de 32px sem rótulo
 * nenhum. Nove destinos mudos disputando atenção com quatro nomeados não são
 * atalhos, são ruído — e o lugar certo da cauda longa é o Menu, que já agrupa
 * tudo por intenção ("Estudar", "Meu progresso", "Quem te responde") e mostra
 * o nome e a função de cada ferramenta.
 *
 * Quatro é o que cabe sem a fileira virar uma segunda barra.
 */
export const MAX_MINIATURAS = 4;

/** Quantas miniaturas cabem numa barra de `larguraDaBarra`, dado o que é
 *  OBRIGATÓRIO desenhar nela (marca, abas primárias, botões fixos).
 *
 *  Função pura, e separada do componente, porque é a única parte disto que dá
 *  para travar em teste: o jsdom não faz layout, então toda largura medida lá
 *  dentro é zero. `respiro` é a soma dos vãos entre os três blocos.
 *
 *  Nunca devolve número negativo nem mais do que a lista tem — uma barra
 *  apertada simplesmente não desenha miniatura nenhuma, e o que não coube
 *  continua no "Menu" e na tira do celular. */
export function quantasCabem(larguraDaBarra, obrigatorio, total = Math.min(ATALHOS.length, MAX_MINIATURAS), respiro = 32) {
  const sobra = larguraDaBarra - obrigatorio - respiro;
  if (!Number.isFinite(sobra) || sobra <= 0) return 0;
  return Math.max(0, Math.min(total, Math.floor(sobra / LARGURA_DA_MINIATURA)));
}
