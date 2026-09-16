import {
  CheckCircle2, ListChecks, Layers, BookOpen, Crown, Flame, Rocket, Star, Gem,
  CalendarDays, Compass, Medal, Award, TrendingUp, Trophy, Flag, GraduationCap,
  Target, Network, PenLine,
} from "lucide-react";

/**
 * O catálogo de conquistas do Sapiens — antes era uma lista de rótulos dentro
 * de `Dashboard.jsx`, agora é um módulo porque três telas precisam dele
 * (Painel, `/conquistas` e o guia da Mentis).
 *
 * Duas regras que não mudaram ao sair do Painel:
 *
 * 1. **Tudo é computado de dado que já existe** — questões respondidas,
 *    ofensiva, domínio por frente, simulados, rodadas, redações corrigidas.
 *    Não há um contador paralelo de conquistas que pudesse divergir do real.
 * 2. **Nada de medalha de participação.** Cada linha aqui custa esforço de
 *    verdade.
 *
 * O que mudou: cada conquista agora sabe dizer QUANTO FALTA (`progresso` e
 * `alvo`), QUAL É A CONDIÇÃO em uma frase, e PARA ONDE IR para conseguir. Um
 * selo cinza que não explica o que fazer é enfeite; com essas três coisas ele
 * vira objetivo.
 *
 * Sobre recompensa: conquista aqui **não paga Sparks nem XP** — quem paga são
 * as missões diárias (`engajamento.py`). Dizer o contrário na interface seria
 * prometer um crédito que nunca cai na conta, então o detalhe fala do que a
 * conquista é de fato: a prova de um marco. Se um dia existir prêmio por
 * conquista, ele entra em `recompensa` e a tela já o mostra.
 */

/** Maior domínio estimado entre as frentes, 0 quando ainda não há mapa. */
const maiorDominio = (ctx) => (ctx.hubs || []).reduce((m, h) => Math.max(m, h.mastery || 0), 0);

const CATALOGO = [
  // ---- Volume de prática ----
  { id: "10q", icon: CheckCircle2, label: "10 questões", grupo: "Prática",
    descricao: "As dez primeiras. É a partir daqui que o Sapiens começa a enxergar como você erra.",
    alvo: 10, progresso: (c) => c.totalRespondidas, unidade: "questões",
    rota: "/exams", rotuloRota: "Praticar questões" },
  { id: "100q", icon: ListChecks, label: "100 questões", grupo: "Prática",
    descricao: "Cem questões já dão amostra para afirmar onde está a sua lacuna, e não só supor.",
    alvo: 100, progresso: (c) => c.totalRespondidas, unidade: "questões",
    rota: "/exams", rotuloRota: "Praticar questões" },
  { id: "250q", icon: Layers, label: "250 questões", grupo: "Prática",
    descricao: "Um quarto de milhar. Nesta altura o seu perfil cognitivo para de mudar a cada semana.",
    alvo: 250, progresso: (c) => c.totalRespondidas, unidade: "questões",
    rota: "/exams", rotuloRota: "Praticar questões" },
  { id: "500q", icon: BookOpen, label: "500 questões", grupo: "Prática",
    descricao: "Meio milhar de questões respondidas dentro do Sapiens.",
    alvo: 500, progresso: (c) => c.totalRespondidas, unidade: "questões",
    rota: "/exams", rotuloRota: "Praticar questões" },
  { id: "1000q", icon: Crown, label: "1000 questões", grupo: "Prática",
    descricao: "Mil. Quase seis provas inteiras do ENEM, questão por questão.",
    alvo: 1000, progresso: (c) => c.totalRespondidas, unidade: "questões",
    rota: "/exams", rotuloRota: "Praticar questões" },

  // ---- Constância ----
  { id: "streak3", icon: Flame, label: "3 dias seguidos", grupo: "Constância",
    descricao: "Três dias seguidos estudando. Consistência vale mais que maratona.",
    alvo: 3, progresso: (c) => c.streak, unidade: "dias",
    rota: "/exams", rotuloRota: "Manter a ofensiva" },
  { id: "streak7", icon: Flame, label: "7 dias seguidos", grupo: "Constância",
    descricao: "Uma semana inteira sem quebrar a ofensiva.",
    alvo: 7, progresso: (c) => c.streak, unidade: "dias",
    rota: "/exams", rotuloRota: "Manter a ofensiva" },
  { id: "streak14", icon: Rocket, label: "14 dias seguidos", grupo: "Constância",
    descricao: "Duas semanas. A partir daqui estudar deixa de ser decisão diária.",
    alvo: 14, progresso: (c) => c.streak, unidade: "dias",
    rota: "/exams", rotuloRota: "Manter a ofensiva" },
  { id: "streak30", icon: Star, label: "30 dias seguidos", grupo: "Constância",
    descricao: "Um mês sem falhar um dia.",
    alvo: 30, progresso: (c) => c.streak, unidade: "dias",
    rota: "/exams", rotuloRota: "Manter a ofensiva" },
  { id: "streak60", icon: Gem, label: "60 dias seguidos", grupo: "Constância",
    descricao: "Dois meses de ofensiva viva.",
    alvo: 60, progresso: (c) => c.streak, unidade: "dias",
    rota: "/exams", rotuloRota: "Manter a ofensiva" },
  { id: "semanaPerfeita", icon: CalendarDays, label: "Semana perfeita", grupo: "Constância",
    descricao: "Os sete dias da semana com atividade registrada.",
    alvo: 7, progresso: (c) => c.weekActiveDays, unidade: "dias na semana",
    rota: "/cronograma", rotuloRota: "Ver a minha semana" },

  // ---- Domínio ----
  { id: "mastery60", icon: Compass, label: "Domínio acima de 60%", grupo: "Domínio",
    descricao: "Uma frente com domínio estimado acima de 60% no seu mapa.",
    alvo: 61, progresso: maiorDominio, unidade: "% na melhor frente",
    rota: "/treino", rotuloRota: "Abrir o Mapa de Treino" },
  { id: "mastery80", icon: Medal, label: "Domínio acima de 80%", grupo: "Domínio",
    descricao: "Uma frente acima de 80%. Aqui o erro já é exceção, não padrão.",
    alvo: 81, progresso: maiorDominio, unidade: "% na melhor frente",
    rota: "/treino", rotuloRota: "Abrir o Mapa de Treino" },
  { id: "mastery90", icon: Award, label: "90% em um tópico", grupo: "Domínio",
    descricao: "Domínio estimado de 90% ou mais numa frente.",
    alvo: 90, progresso: maiorDominio, unidade: "% na melhor frente",
    rota: "/treino", rotuloRota: "Abrir o Mapa de Treino" },
  { id: "dominioTotal", icon: TrendingUp, label: "3 frentes acima de 80%", grupo: "Domínio",
    descricao: "Três frentes diferentes acima de 80% ao mesmo tempo.",
    alvo: 3, progresso: (c) => (c.hubs || []).filter((h) => (h.mastery || 0) > 80).length,
    unidade: "frentes",
    rota: "/treino", rotuloRota: "Abrir o Mapa de Treino" },

  // ---- Provas e treino ----
  { id: "firstExam", icon: Trophy, label: "1º simulado completo", grupo: "Provas",
    descricao: "Um caderno inteiro analisado, do gabarito ao diagnóstico.",
    alvo: 1, progresso: (c) => (c.analyses || []).length, unidade: "simulados",
    rota: "/exams", rotuloRota: "Escolher um caderno" },
  { id: "exam3", icon: Flag, label: "3 simulados completos", grupo: "Provas",
    descricao: "Três cadernos completos — é com três que a curva aparece.",
    alvo: 3, progresso: (c) => (c.analyses || []).length, unidade: "simulados",
    rota: "/exams", rotuloRota: "Escolher um caderno" },
  { id: "exam10", icon: GraduationCap, label: "10 simulados completos", grupo: "Provas",
    descricao: "Dez cadernos completos analisados pelo Sapiens.",
    alvo: 10, progresso: (c) => (c.analyses || []).length, unidade: "simulados",
    rota: "/exams", rotuloRota: "Escolher um caderno" },
  { id: "rounds10", icon: Target, label: "10 rodadas de treino", grupo: "Provas",
    descricao: "Dez rodadas de dez questões fechadas.",
    alvo: 10, progresso: (c) => (c.rounds || []).length, unidade: "rodadas",
    rota: "/exams", rotuloRota: "Fechar uma rodada" },
  { id: "rounds50", icon: Network, label: "50 rodadas de treino", grupo: "Provas",
    descricao: "Cinquenta rodadas fechadas: quinhentas questões em blocos.",
    alvo: 50, progresso: (c) => (c.rounds || []).length, unidade: "rodadas",
    rota: "/exams", rotuloRota: "Fechar uma rodada" },

  // ---- Redação ----
  { id: "primeiraRedacao", icon: PenLine, label: "1ª redação corrigida", grupo: "Redação",
    descricao: "Sua primeira redação corrigida nas cinco competências.",
    alvo: 1, progresso: (c) => c.redacoesCorrigidas, unidade: "redações",
    rota: "/redacao", rotuloRota: "Escrever uma redação" },
  { id: "redacao800", icon: Star, label: "800+ na redação", grupo: "Redação",
    descricao: "Uma redação de 800 pontos ou mais — um quinto da nota do ENEM em nível alto.",
    alvo: 800, progresso: (c) => c.melhorRedacao, unidade: "pontos (melhor nota)",
    rota: "/redacao", rotuloRota: "Escrever de novo" },
];

export const GRUPOS = ["Prática", "Constância", "Domínio", "Provas", "Redação"];

/** O contexto vazio — usado por telas que ainda estão carregando os dados. */
export const CONTEXTO_VAZIO = {
  totalRespondidas: 0, streak: 0, hubs: [], analyses: [], rounds: [],
  weekActiveDays: 0, redacoesCorrigidas: 0, melhorRedacao: 0,
};

/**
 * Avalia o catálogo inteiro contra o que o aluno fez.
 *
 * Devolve cada conquista com `atual`, `alvo`, `percentual` e `desbloqueada` —
 * a tela nunca recalcula nada, e `desbloqueada` é `atual >= alvo` em todas,
 * sem exceção pontual que só o Painel conhecesse.
 */
export function avaliarConquistas(contexto) {
  const ctx = { ...CONTEXTO_VAZIO, ...(contexto || {}) };
  return CATALOGO.map((c) => {
    const atual = Math.max(0, Math.round(c.progresso(ctx) || 0));
    const desbloqueada = atual >= c.alvo;
    return {
      ...c,
      atual,
      desbloqueada,
      percentual: Math.min(100, Math.round((atual / c.alvo) * 100)),
      condicao: `${c.alvo} ${c.unidade}`,
    };
  });
}

export default CATALOGO;
