import {
  PlayCircle, CalendarClock, Sparkles, Brain, Trophy, GraduationCap, Rss,
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
 * O que NÃO entra aqui: o que já é aba primária (Treino, Painel, Redação,
 * Semana, Mural, Mentis), o que já tem botão próprio na barra (Aulas, Sparks)
 * e o que é administrativo. Miniatura repetida a 40px de distância da aba com
 * o mesmo destino é ruído, não atalho.
 *
 A ORDEM É PRIORIDADE: a barra do desktop mede a si mesma e desenha só as
 * primeiras que couberem (ver `quantasCabem` abaixo e a nota em `Nav.jsx`),
 * então o que estiver no fim da lista é o primeiro a sumir num notebook de
 * 13". No celular a tira rola e mostra todas, sempre.
 */
export const ATALHOS = [
  { rota: "/exams", icone: PlayCircle, nome: "Provas", label: "Provas do ENEM" },
  { rota: "/revisoes", icone: CalendarClock, nome: "Revisões", label: "Revisões de hoje" },
  { rota: "/minhas-questoes", icone: Sparkles, nome: "Minhas questões", label: "Questões geradas pela Mentis" },
  { rota: "/cognitive-profile", icone: Brain, nome: "Desempenho", label: "Seu desempenho" },
  { rota: "/conquistas", icone: Trophy, nome: "Conquistas", label: "Conquistas e liga" },
  { rota: "/cursos", icone: GraduationCap, nome: "Cursos", label: "Cursos e e-books" },
  { rota: "/feed", icone: Rss, nome: "Feed", label: "Feed de questões" },
];

/** Cada miniatura ocupa 36px de ícone mais 4px de vão. */
export const LARGURA_DA_MINIATURA = 40;

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
export function quantasCabem(larguraDaBarra, obrigatorio, total = ATALHOS.length, respiro = 32) {
  const sobra = larguraDaBarra - obrigatorio - respiro;
  if (!Number.isFinite(sobra) || sobra <= 0) return 0;
  return Math.max(0, Math.min(total, Math.floor(sobra / LARGURA_DA_MINIATURA)));
}
