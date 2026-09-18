import {
  Compass, PenLine, CalendarClock, Users, Sparkles, Trophy, Radio, Rss,
} from "lucide-react";

/**
 * OS ATALHOS — a tira nomeada do celular.
 *
 * Eram duas barras lendo esta lista: a fileira de miniaturas do desktop
 * (círculos de 32px SEM rótulo) e a tira rolável do celular (pílulas COM o
 * nome escrito). As miniaturas saíram em 2026-09-17: um ícone que o aluno
 * precisa decifrar não é atalho, é charada, e o desktop já ganhou seis abas
 * nomeadas no lugar. A tira do celular fica, porque ela sempre teve nome.
 *
 * O que ela garante: o aluno de iPhone alcança em um toque o que o de
 * notebook alcança pelo Menu — a barra inferior tem cinco alvos fixos por
 * invariante de polegar, e sem esta tira o celular ficaria com cinco portas.
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
 * A ORDEM É PRIORIDADE: quem estiver no fim é o que o polegar alcança por
 * último, depois de rolar. Deixe na frente o que o aluno abre com mais
 * frequência — hoje, Redação e Revisões.
 *
 * A medição de largura (`quantasCabem`, `MAX_MINIATURAS`) saiu junto com as
 * miniaturas do desktop: não há mais nada a calcular em tempo de execução.
 */
export const ATALHOS = [
  { rota: "/treino", icone: Compass, nome: "Treino", label: "Mapa de treino" },
  { rota: "/redacao", icone: PenLine, nome: "Redação", label: "Redação" },
  { rota: "/revisoes", icone: CalendarClock, nome: "Revisões", label: "Revisões de hoje" },
  { rota: "/comunidade", icone: Users, nome: "Mural", label: "Mural de dúvidas" },
  { rota: "/minhas-questoes", icone: Sparkles, nome: "Minhas questões", label: "Questões geradas pela Mentis" },
  { rota: "/conquistas", icone: Trophy, nome: "Conquistas", label: "Conquistas e liga" },
  { rota: "/aula-ao-vivo", icone: Radio, nome: "Aula ao vivo", label: "Aula ao vivo de quinta" },
  { rota: "/feed", icone: Rss, nome: "Feed", label: "Feed de questões" },
];
